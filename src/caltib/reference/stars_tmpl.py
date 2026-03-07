from __future__ import annotations

import math
from dataclasses import dataclass

from . import astro_args as aa

@dataclass(frozen=True)
class Star:
    hip_id: int
    mag: float
    ra_j2000_deg: float
    dec_j2000_deg: float
    pm_ra_mas_yr: float
    pm_dec_mas_yr: float

@dataclass(frozen=True)
class EquatorialCoords:
    ra_deg: float
    dec_deg: float

@dataclass(frozen=True)
class EclipticCoords:
    L_deg: float
    B_deg: float

# ============================================================
# Hipparcos Catalog (Generated)
# ============================================================

STAR_CATALOG = {
{stars_dict_str}
}

# Star names to hip_id
COMMON_STARS = {
    "sirius": 32349,
    "canopus": 30438,
    "arcturus": 69673,
    "vega": 91262,
    "capella": 24608,
    "rigel": 24436,
    "betelgeuse": 27989,
    "polaris": 11767,
    # Primary Lunar Mansion Reference Stars (Yogataras)
    "aldebaran": 21421,  # Rohini / snar ma
    "pleiades": 17702,   # Alcyone (Krittika / smin drug)
    "regulus": 49669,    # Magha / mchu
    "spica": 65474,      # Chitra / nag pa
    "antares": 80763,    # Jyeshtha / snrubs
}

def get_star_id(name: str) -> int:
    """Safely retrieves the HIP ID for a common star name."""
    clean_name = name.lower().strip()
    if clean_name not in COMMON_STARS:
        raise ValueError(f"Star '{name}' not found in COMMON_STARS mapping.")
    return COMMON_STARS[clean_name]

def get_star_ecliptic(hip_id: int, jd_tt: float) -> EclipticCoords:
    """Computes Apparent Geocentric Ecliptic coordinates of Date."""
    star = STAR_CATALOG[hip_id]
    
    # 1. Apply Proper Motion (Linear drift from J2000.0)
    # pm_ra_mas_yr in Hipparcos is pm_RA * cos(Dec), so we divide out the cos(Dec).
    years_since_2000 = (jd_tt - 2451545.0) / 365.25
    
    pm_ra_deg_yr = (star.pm_ra_mas_yr / 1000.0 / 3600.0) / math.cos(math.radians(star.dec_j2000_deg))
    pm_dec_deg_yr = (star.pm_dec_mas_yr / 1000.0 / 3600.0)
    
    ra_j2000_now = star.ra_j2000_deg + pm_ra_deg_yr * years_since_2000
    dec_j2000_now = star.dec_j2000_deg + pm_dec_deg_yr * years_since_2000
    
    ra_rad = math.radians(ra_j2000_now)
    dec_rad = math.radians(dec_j2000_now)
    
    # 2. Convert to 3D Rectangular Coordinates (Equatorial J2000)
    x = math.cos(dec_rad) * math.cos(ra_rad)
    y = math.cos(dec_rad) * math.sin(ra_rad)
    z = math.sin(dec_rad)
    
    # 3. Rotate from Equatorial J2000 directly to Ecliptic of Date
    T = aa.T_centuries(jd_tt)
    rot_matrix = aa.matrix_eq_j2000_to_ecl_date(T)
    x_ecl, y_ecl, z_ecl = aa.apply_matrix(rot_matrix, (x, y, z))
    
    # 4. Extract Spherical Ecliptic Coordinates
    L_deg = aa.wrap_deg(math.degrees(math.atan2(y_ecl, x_ecl)))
    B_deg = math.degrees(math.asin(z_ecl))
    
    return EclipticCoords(L_deg=L_deg, B_deg=B_deg)

def get_star_equatorial(hip_id: int, jd_tt: float) -> EquatorialCoords:
    """Computes Apparent Geocentric Equatorial coordinates of Date (for Rise/Set)."""
    # Get the ecliptic of date, then tilt by Obliquity of Date
    ecl = get_star_ecliptic(hip_id, jd_tt)
    
    T = aa.T_centuries(jd_tt)
    eps_rad = math.radians(aa.mean_obliquity_deg(T))
    
    L_rad = math.radians(ecl.L_deg)
    B_rad = math.radians(ecl.B_deg)
    
    sin_dec = math.sin(B_rad) * math.cos(eps_rad) + math.cos(B_rad) * math.sin(eps_rad) * math.sin(L_rad)
    dec_deg = math.degrees(math.asin(sin_dec))
    
    y = math.sin(L_rad) * math.cos(eps_rad) - math.tan(B_rad) * math.sin(eps_rad)
    x = math.cos(L_rad)
    ra_deg = aa.wrap_deg(math.degrees(math.atan2(y, x)))
    
    return EquatorialCoords(ra_deg=ra_deg, dec_deg=dec_deg)