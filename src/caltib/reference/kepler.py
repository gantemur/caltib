from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from . import astro_args as aa
from . import lunar
from . import solar

# ============================================================
# Coordinate Data Structures
# ============================================================

@dataclass(frozen=True)
class HeliocentricCoords:
    """Heliocentric Ecliptic Coordinates of Date."""
    L_mean_deg: float
    L_true_deg: float
    B_true_deg: float
    R_mean_au: float
    R_true_au: float

@dataclass(frozen=True)
class GeocentricCoords:
    """True Geocentric Coordinates of Date."""
    L_mean_deg: float
    L_true_deg: float
    B_true_deg: float
    R_mean_au: float
    R_true_au: float


# ============================================================
# JPL Secular Keplerian Elements (J2000)
# ============================================================
# Valid for high-accuracy historical approximations.
# Format: (a, e0, e1, I0, I1, L0, L1, w0, w1, Omega0, Omega1)
# Angles are in degrees, rates in degrees per Julian Century (T).

KEPLER_ELEMENTS = {
    "mercury": (0.38709927, 0.20563593, 0.00001906, 7.00497902, 0.00594749, 252.25032350, 149472.674111, 77.45779628, 0.16047689, 48.33076593, 1.18570883),
    "venus": (0.72333199, 0.00677323, -0.00004107, 3.39467605, -0.00078890, 181.97909950, 58517.8153860, 131.53298000, 0.00120505, 76.67984255, -0.27769418),
    "earth": (1.00000261, 0.01671123, -0.00004392, 0.00001531, -0.01294668, 100.46435, 36000.76983, 102.93768193, 0.32327364, 0.0, 0.0),
    "mars": (1.52367934, 0.09339410, 0.00007882, 1.84969142, -0.00813131, -4.55343205, 19140.302684, -23.94362959, 0.44441088, 49.55953891, -0.29257343),
    "jupiter": (5.20288700, 0.04838624, -0.00013253, 1.30439695, -0.00183714, 34.39644051, 3034.74612775, 14.72847983, 0.21252668, 100.47390909, 0.20469106),
    "saturn": (9.53667594, 0.05386179, -0.00050991, 2.48599187, 0.00193609, 50.07744430, 1222.49362201, 92.43194139, -0.41897216, 113.66242448, -0.28867794)
}

def _solve_kepler(M_rad: float, e: float) -> float:
    """Solves Kepler's Equation E - e*sin(E) = M using Newton-Raphson."""
    E = M_rad + e * math.sin(M_rad) * (1.0 + e * math.cos(M_rad))
    for _ in range(5):
        E1 = E - (E - e * math.sin(E) - M_rad) / (1.0 - e * math.cos(E))
        if abs(E1 - E) < 1e-8:
            break
        E = E1
    return E

def _heliocentric_j2000_vector(planet: str, T: float) -> tuple[float, float, float]:
    """Computes the 3D Heliocentric vector (x, y, z) in Ecliptic J2000."""
    a, e0, e1, I0, I1, L0, L1, w0, w1, W0, W1 = KEPLER_ELEMENTS[planet]
    
    e = e0 + e1 * T
    I = math.radians(I0 + I1 * T)
    L = math.radians(L0 + L1 * T)
    w = math.radians(w0 + w1 * T)
    W = math.radians(W0 + W1 * T)
    
    # Mean Anomaly
    M = L - w
    E = _solve_kepler(M, e)
    
    # 2D Coordinates in the orbital plane
    x_prime = a * (math.cos(E) - e)
    y_prime = a * math.sqrt(1.0 - e*e) * math.sin(E)
    
    # 3D Rotation to Ecliptic J2000 (Argument of perihelion w_arg = w - W)
    w_arg = w - W
    cos_w, sin_w = math.cos(w_arg), math.sin(w_arg)
    cos_W, sin_W = math.cos(W), math.sin(W)
    cos_I, sin_I = math.cos(I), math.sin(I)
    
    x = x_prime * (cos_w*cos_W - sin_w*sin_W*cos_I) + y_prime * (-sin_w*cos_W - cos_w*sin_W*cos_I)
    y = x_prime * (cos_w*sin_W + sin_w*cos_W*cos_I) + y_prime * (-sin_w*sin_W + cos_w*cos_W*cos_I)
    z = x_prime * (sin_w*sin_I) + y_prime * (cos_w*sin_I)
    
    return x, y, z

# ============================================================
# Master API
# ============================================================

def heliocentric_position(
    planet: Literal["mercury", "venus", "earth", "mars", "jupiter", "saturn"], 
    jd_tt: float
) -> HeliocentricCoords:
    """Computes True Heliocentric Coordinates in the Mean Ecliptic of Date."""
    T = aa.T_centuries(jd_tt)
    x, y, z = _heliocentric_j2000_vector(planet, T)
    
    # 1. Rotate Ecliptic J2000 -> Equatorial J2000 (tilt by obliquity of J2000)
    eps_j2000 = math.radians(23.4392911)
    x_eq = x
    y_eq = y * math.cos(eps_j2000) - z * math.sin(eps_j2000)
    z_eq = y * math.sin(eps_j2000) + z * math.cos(eps_j2000)
    
    # 2. Rotate Equatorial J2000 -> Ecliptic of Date
    rot_matrix = aa.matrix_eq_j2000_to_ecl_date(T)
    x_date, y_date, z_date = aa.apply_matrix(rot_matrix, (x_eq, y_eq, z_eq))
    
    # Extract Spherical Coordinates
    L_true = aa.wrap_deg(math.degrees(math.atan2(y_date, x_date)))
    R_true = math.hypot(x_date, y_date, z_date)
    B_true = math.degrees(math.atan2(z_date, math.hypot(x_date, y_date)))
    
    # Compute Mean Longitude of Date (Precess the L0 base term)
    p = 1.396971 * T + 0.0003086 * T * T
    L_mean = aa.wrap_deg(KEPLER_ELEMENTS[planet][5] + KEPLER_ELEMENTS[planet][6] * T + p)
    
    return HeliocentricCoords(
        L_mean_deg=L_mean, L_true_deg=L_true, 
        B_true_deg=B_true, R_mean_au=KEPLER_ELEMENTS[planet][0], R_true_au=R_true
    )

def geocentric_position(
    planet: Literal["sun", "moon", "rahu", "mercury", "venus", "mars", "jupiter", "saturn"], 
    jd_tt: float
) -> GeocentricCoords:
    """Computes True Geocentric Coordinates of Date."""
    T = aa.T_centuries(jd_tt)
    fa = aa.fundamental_args(T)
    
    if planet == "sun":
        earth = heliocentric_position("earth", jd_tt)
        sun_coords = solar.solar_longitude(jd_tt)
        return GeocentricCoords(
            L_mean_deg=aa.wrap_deg(earth.L_mean_deg - 180.0), 
            L_true_deg=sun_coords.L_true_deg,
            B_true_deg=0.0, R_mean_au=earth.R_mean_au, R_true_au=earth.R_true_au
        )

    if planet == "moon":
        moon_coords = lunar.lunar_position(jd_tt)
        return GeocentricCoords(
            L_mean_deg=fa.Lp_deg, L_true_deg=moon_coords.L_true_deg, 
            B_true_deg=moon_coords.B_true_deg, R_mean_au=0.00257, R_true_au=0.00257
        )

    if planet == "rahu":
        mean_node = fa.Omega_deg
        D_rad, M_rad, F_rad = map(math.radians, (fa.D_deg, fa.M_deg, fa.F_deg))
        true_node = mean_node \
            - 1.4979 * math.sin(2.0 * D_rad - 2.0 * F_rad) \
            - 0.1500 * math.sin(M_rad) \
            - 0.1226 * math.sin(2.0 * D_rad)
        return GeocentricCoords(
            L_mean_deg=mean_node, L_true_deg=aa.wrap_deg(true_node),
            B_true_deg=0.0, R_mean_au=0.00257, R_true_au=0.00257
        )

    # Planetary Vector Reduction
    earth = heliocentric_position("earth", jd_tt)
    target = heliocentric_position(planet, jd_tt)
    
    def _vector_diff(L_e, B_e, R_e, L_t, B_t, R_t) -> tuple[float, float, float]:
        x0 = R_e * math.cos(math.radians(B_e)) * math.cos(math.radians(L_e))
        y0 = R_e * math.cos(math.radians(B_e)) * math.sin(math.radians(L_e))
        z0 = R_e * math.sin(math.radians(B_e))
        
        x1 = R_t * math.cos(math.radians(B_t)) * math.cos(math.radians(L_t))
        y1 = R_t * math.cos(math.radians(B_t)) * math.sin(math.radians(L_t))
        z1 = R_t * math.sin(math.radians(B_t))
        
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        
        dist_xy = math.hypot(dx, dy)
        R_geo = math.hypot(dist_xy, dz)
        L_geo = aa.wrap_deg(math.degrees(math.atan2(dy, dx)))
        B_geo = math.degrees(math.atan2(dz, dist_xy))
        
        return L_geo, B_geo, R_geo

    L_geo_mean, B_geo_mean, R_geo_mean = _vector_diff(
        earth.L_mean_deg, 0.0, earth.R_mean_au, target.L_mean_deg, 0.0, target.R_mean_au
    )
    L_geo_true, B_geo_true, R_geo_true = _vector_diff(
        earth.L_true_deg, earth.B_true_deg, earth.R_true_au, target.L_true_deg, target.B_true_deg, target.R_true_au
    )
    
    return GeocentricCoords(
        L_mean_deg=L_geo_mean, L_true_deg=L_geo_true,
        B_true_deg=B_geo_true, R_mean_au=R_geo_mean, R_true_au=R_geo_true
    )