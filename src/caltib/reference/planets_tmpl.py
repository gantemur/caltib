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

def fast_lunar_position(jd_tt: float, fa: Optional[aa.FundamentalArgs] = None) -> tuple[float, float, float]:
    """
    Calculates a low-precision lunar position (Mean + Principal Anomaly).
    Accurate to about ~1.5 degrees in longitude.
    Perfect for the EMB offset or as a fast/rough lunar tracker.
    Returns: (L_true_deg, B_true_deg, R_au)
    """
    if fa is None:
        T = aa.T_centuries(jd_tt)
        fa = aa.fundamental_args(T)

    M_rad = math.radians(fa.M_deg)
    F_rad = math.radians(fa.F_deg)

    # 1 major term for longitude (Equation of Center: ~6.289 degrees)
    L_true = aa.wrap_deg(fa.Lp_deg + 6.289 * math.sin(M_rad))

    # 1 major term for latitude (~5.128 degrees)
    B_true = 5.128 * math.sin(F_rad)

    # Constant mean distance
    R_au = 0.00257

    return L_true, B_true, R_au

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
    jd_tt: float,
    fast_emb: bool = True
) -> GeocentricCoords:
    T = aa.T_centuries(jd_tt)
    fa = aa.fundamental_args(T)
    
    if planet == "moon":
        moon = lunar.lunar_position(jd_tt)
        return GeocentricCoords(fa.Lp_deg, moon.L_true_deg, moon.B_true_deg, 0.00257, moon.R_true_au)

    if planet == "rahu":
        mean_node = fa.Omega_deg
        D_rad, M_rad, F_rad = map(math.radians, (fa.D_deg, fa.M_deg, fa.F_deg))
        true_node = mean_node \
            - 1.4979 * math.sin(2.0 * D_rad - 2.0 * F_rad) \
            - 0.1500 * math.sin(M_rad) \
            - 0.1226 * math.sin(2.0 * D_rad)
        return GeocentricCoords(mean_node, aa.wrap_deg(true_node), 0.0, 0.00257, 0.00257)

    # 1. Obtain Earth-Moon Barycenter (EMB) and Moon Geocentric vector
    emb = heliocentric_position("earth", jd_tt)
    
    # Toggle between the rough 1-term moon and the full 64-term moon
    if fast_emb:
        mL_true, mB_true, mR_true = fast_lunar_position(jd_tt, fa)
    else:
        moon = lunar.lunar_position(jd_tt)
        mL_true, mB_true, mR_true = moon.L_true_deg, moon.B_true_deg, moon.R_true_au
    
    # Earth-Moon Mass Ratio (IAU standard DE422 emrat)
    EMRAT = 81.300569 
    mu = 1.0 / (1.0 + EMRAT)

    def _to_cart(L, B, R):
        L_rad, B_rad = math.radians(L), math.radians(B)
        return (
            R * math.cos(B_rad) * math.cos(L_rad),
            R * math.cos(B_rad) * math.sin(L_rad),
            R * math.sin(B_rad)
        )

    def _to_sph(x, y, z):
        dist_xy = math.hypot(x, y)
        R = math.hypot(dist_xy, z)
        L = aa.wrap_deg(math.degrees(math.atan2(y, x)))
        B = math.degrees(math.atan2(z, dist_xy))
        return L, B, R

    # 2. Calculate True Earth Heliocentric Vector (EMB - lunar offset)
    mx, my, mz = _to_cart(mL_true, mB_true, mR_true)
    emb_x, emb_y, emb_z = _to_cart(emb.L_true_deg, emb.B_true_deg, emb.R_true_au)
    
    e_x = emb_x - mx * mu
    e_y = emb_y - my * mu
    e_z = emb_z - mz * mu
    
    if planet == "sun":
        # Sun Geocentric is the exact inverse of True Earth Heliocentric
        L_true, B_true, R_true = _to_sph(-e_x, -e_y, -e_z)
        L_mean = aa.wrap_deg(emb.L_mean_deg + 180.0)
        return GeocentricCoords(L_mean, L_true, B_true, emb.R_mean_au, R_true)

    # 3. For other planets, get target heliocentric vector
    target = heliocentric_position(planet, jd_tt)
    
    emb_m_x, emb_m_y, emb_m_z = _to_cart(emb.L_mean_deg, 0.0, emb.R_mean_au)
    t_m_x, t_m_y, t_m_z = _to_cart(target.L_mean_deg, 0.0, target.R_mean_au)
    L_mean, _, R_mean = _to_sph(t_m_x - emb_m_x, t_m_y - emb_m_y, t_m_z - emb_m_z)
    
    tx, ty, tz = _to_cart(target.L_true_deg, target.B_true_deg, target.R_true_au)
    L_true, B_true, R_true = _to_sph(tx - e_x, ty - e_y, tz - e_z)
    
    return GeocentricCoords(L_mean, L_true, B_true, R_mean, R_true)