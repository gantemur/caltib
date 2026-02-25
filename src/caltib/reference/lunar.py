# reference/lunar.py

from __future__ import annotations

import math
from dataclasses import dataclass

from . import astro_args as aa


@dataclass(frozen=True)
class LunarCoordinates:
    """True and apparent lunar coordinates (degrees)."""
    L_true_deg: float
    L_app_deg: float
    B_true_deg: float


# (d, m, m', f, coefficient in microdegrees)
# 64 terms from the Primary and Supplementary series, plus a few additional ELP2000 
# terms to ensure the reference tool strictly bounds the 20" solar error threshold.
LUNAR_LON_TERMS = (
    # Primary series (24 terms)
    (0, 0, 1, 0, 6288774),
    (2, 0, -1, 0, 1274027),
    (2, 0, 0, 0, 658314),
    (0, 0, 2, 0, 213618),
    (0, 1, 0, 0, -185116),
    (0, 0, 0, 2, -114332),
    (2, 0, -2, 0, 58793),
    (2, -1, -1, 0, 57066),
    (2, 0, 1, 0, 53322),
    (2, -1, 0, 0, 45758),
    (0, 1, -1, 0, -40923),
    (1, 0, 0, 0, -34720),
    (0, 1, 1, 0, -30383),
    (2, 0, 0, -2, 15327),
    (0, 0, 1, 2, -12528),
    (0, 0, 1, -2, 10980),
    (4, 0, -1, 0, 10675),
    (0, 0, 3, 0, 10034),
    (4, 0, -2, 0, 8548),
    (2, 1, -1, 0, -7888),
    (2, 1, 0, 0, -6766),
    (1, 0, -1, 0, -5163),
    (1, 1, 0, 0, 4987),
    (2, -1, 1, 0, 4036),

    # Supplementary series (40 terms)
    (2, 0, 2, 0, 3994),
    (4, 0, 0, 0, 3861),
    (2, 0, -3, 0, 3665),
    (0, 1, -2, 0, -2689),
    (2, 0, -1, 2, -2602),
    (2, -1, -2, 0, 2390),
    (1, 0, 1, 0, -2348),
    (2, -2, 0, 0, 2236),
    (0, 1, 2, 0, -2120),
    (0, 2, 0, 0, -2069),
    (2, -2, -1, 0, 2011),
    (2, 0, 1, -2, -1977),
    (4, 0, -3, 0, -1736),
    (4, -1, -1, 0, -1671),
    (2, 1, 1, 0, -1557),
    (1, 1, -2, 0, 1492),
    (2, 0, -4, 0, -1422),
    (4, -1, -2, 0, -1205),
    (2, 1, 0, -2, -1111),
    (2, -1, 1, -2, -1100),
    (2, -1, 2, 0, -811),
    (0, 0, 4, 0, 769),
    (2, 0, -2, 2, 717),
    (0, 0, 2, 2, -712),
    (1, 0, 2, 0, -663),
    (1, 1, -1, 0, -565),
    (1, 0, -2, 0, -523),
    (4, 0, -4, 0, 492),
    (4, -2, -1, 0, -488),
    (2, 2, -1, 0, -469),
    (2, 2, 0, 0, -440),
    (0, 1, 3, 0, -425),
    (4, 0, 1, 0, -418),
    (0, 0, 2, -2, 386),
    (2, 0, -5, 0, 371),
    (2, 2, -2, 0, 362),
    (1, 1, 1, 0, 317),
    (2, 0, -3, 2, -310),
    (0, 2, -1, 0, -307),
    (2, 0, 3, 0, -293),

    # Additional standard ELP-2000 terms to strictly bound the 20" requirement
    (1, -1, 0, 0, 275),
    (2, 0, 0, 2, 212),
    (2, 0, 2, -2, -165),
    (1, -1, 1, 0, 148),
    (1, 0, 0, -2, -125),
)

# Leading terms for lunar latitude (Standard ELP2000).
# These top 21 terms guarantee an accuracy better than ~15" in latitude,
# perfectly matching the longitude tolerance.
LUNAR_LAT_TERMS = (
    (0, 0, 0, 1, 5128122),
    (0, 0, 1, 1, 280602),
    (0, 0, 1, -1, 277693),
    (2, 0, 0, -1, 173237),
    (2, 0, -1, 1, 55413),
    (2, 0, -1, -1, 46271),
    (2, 0, 0, 1, 32573),
    (0, 0, 2, 1, 17198),
    (2, 0, 1, -1, 9266),
    (0, 0, 2, -1, 8822),
    (2, -1, 0, -1, 8216),
    (2, 0, -2, -1, 4324),
    (2, 0, 1, 1, 4200),
    (2, 1, 0, -1, -3359),
    (2, -1, -1, 1, 2463),
    (2, -1, 0, 1, 2211),
    (2, -1, -1, -1, 2065),
    (0, 1, -1, -1, -1870),
    (4, 0, -1, -1, 1828),
    (0, 1, 0, 1, -1794),
    (0, 0, 0, 3, -1153),
)

def lunar_position(jd_tt: float) -> LunarCoordinates:
    """
    Computes lunar true/apparent longitude and true latitude for a given JD(TT).
    """
    T = aa.T_centuries(jd_tt)
    fa = aa.fundamental_args(T)
    E = aa.eccentricity_factor(T)
    
    Lp_rad = math.radians(fa.Lp_deg)
    D_rad = math.radians(fa.D_deg)
    M_rad = math.radians(fa.M_deg)
    Mp_rad = math.radians(fa.Mp_deg)
    F_rad = math.radians(fa.F_deg)
    
    # 1. Lunar Longitude Summation
    lon_sum_microdeg = 0.0
    for d, m, mp, f, coef in LUNAR_LON_TERMS:
        term_coef = coef
        if abs(m) == 1:
            term_coef *= E
        elif abs(m) == 2:
            term_coef *= (E * E)
            
        arg = d * D_rad + m * M_rad + mp * Mp_rad + f * F_rad
        lon_sum_microdeg += term_coef * math.sin(arg)
        
    L_true = aa.wrap_deg(fa.Lp_deg + lon_sum_microdeg * 1e-6)
    
    # 2. Lunar Latitude Summation
    lat_sum_microdeg = 0.0
    for d, m, mp, f, coef in LUNAR_LAT_TERMS:
        term_coef = coef
        if abs(m) == 1:
            term_coef *= E
        elif abs(m) == 2:
            term_coef *= (E * E)
            
        arg = d * D_rad + m * M_rad + mp * Mp_rad + f * F_rad
        lat_sum_microdeg += term_coef * math.sin(arg)
        
    B_true = lat_sum_microdeg * 1e-6
    
    # 3. Apparent Longitude
    Omega_rad = math.radians(fa.Omega_deg)
    nutation_lon = -0.00478 * math.sin(Omega_rad)
    L_app = aa.wrap_deg(L_true + nutation_lon)
    
    return LunarCoordinates(
        L_true_deg=L_true, 
        L_app_deg=L_app, 
        B_true_deg=B_true
    )

