from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from . import astro_args as aa
from . import lunar
from . import solar

@dataclass(frozen=True)
class HeliocentricCoords:
    L_mean_deg: float
    L_true_deg: float
    B_true_deg: float
    R_mean_au: float
    R_true_au: float

@dataclass(frozen=True)
class GeocentricCoords:
    L_mean_deg: float
    L_true_deg: float
    B_true_deg: float
    R_mean_au: float
    R_true_au: float

# ============================================================
# Micro-VSOP87D Constants (Generated)
# ============================================================

PLANET_DATA = {planet_data_str}

def _eval_vsop(tau: float, series_data: dict[int, tuple[tuple[float, float, float], ...]]) -> float:
    total = 0.0
    for alpha, terms in series_data.items():
        tau_pow = tau ** alpha
        subtotal = 0.0
        for a, b, c in terms:
            subtotal += a * math.cos(b + c * tau)
        total += subtotal * tau_pow
    return total

def heliocentric_position(
    planet: Literal["mercury", "venus", "earth", "mars", "jupiter", "saturn"], 
    jd_tt: float
) -> HeliocentricCoords:
    T = aa.T_centuries(jd_tt)
    tau = T / 10.0
    
    if planet == "earth":
        sm = aa.solar_mean_elements(T)
        sun_coords = solar.solar_longitude(jd_tt)
        
        L_mean = aa.wrap_deg(sm.L0_deg + 180.0)
        L_true = aa.wrap_deg(sun_coords.L_true_deg + 180.0)
        B_true = 0.0
        
        R_true = _eval_vsop(tau, PLANET_DATA["earth"]["R"])
        R_mean = PLANET_DATA["earth"]["R"].get(0, ((1.00000011, 0.0, 0.0),))[0][0]
        
        return HeliocentricCoords(L_mean, L_true, B_true, R_mean, R_true)
        
    p_data = PLANET_DATA[planet]
    
    L_rad = _eval_vsop(tau, p_data["L"])
    B_rad = _eval_vsop(tau, p_data["B"])
    R_au = _eval_vsop(tau, p_data["R"])
    
    L0_mean_rad = p_data["L"].get(0, ((0.0, 0.0, 0.0),))[0][0]
    L1_mean_rad = p_data["L"].get(1, ((0.0, 0.0, 0.0),))[0][0]
    L_mean_rad = L0_mean_rad + L1_mean_rad * tau
    
    R_mean = p_data["R"].get(0, ((1.0, 0.0, 0.0),))[0][0]
    
    return HeliocentricCoords(
        aa.wrap_deg(math.degrees(L_mean_rad)),
        aa.wrap_deg(math.degrees(L_rad)), 
        math.degrees(B_rad), 
        R_mean,
        R_au
    )

def geocentric_position(
    planet: Literal["sun", "moon", "rahu", "mercury", "venus", "mars", "jupiter", "saturn"], 
    jd_tt: float
) -> GeocentricCoords:
    T = aa.T_centuries(jd_tt)
    fa = aa.fundamental_args(T)
    
    if planet == "sun":
        earth = heliocentric_position("earth", jd_tt)
        sun_coords = solar.solar_longitude(jd_tt)
        L_mean = aa.wrap_deg(earth.L_mean_deg - 180.0)
        return GeocentricCoords(L_mean, sun_coords.L_true_deg, 0.0, earth.R_mean_au, earth.R_true_au)

    if planet == "moon":
        moon = lunar.lunar_position(jd_tt)
        return GeocentricCoords(fa.Lp_deg, moon.L_true_deg, moon.B_true_deg, 0.00257, 0.00257)

    if planet == "rahu":
        mean_node = fa.Omega_deg
        D_rad, M_rad, F_rad = map(math.radians, (fa.D_deg, fa.M_deg, fa.F_deg))
        true_node = mean_node \
            - 1.4979 * math.sin(2.0 * D_rad - 2.0 * F_rad) \
            - 0.1500 * math.sin(M_rad) \
            - 0.1226 * math.sin(2.0 * D_rad)
        return GeocentricCoords(mean_node, aa.wrap_deg(true_node), 0.0, 0.00257, 0.00257)

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
    
    return GeocentricCoords(L_geo_mean, L_geo_true, B_geo_true, R_geo_mean, R_geo_true)