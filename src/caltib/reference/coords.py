from __future__ import annotations

import math
from dataclasses import dataclass

from . import astro_args as aa

@dataclass(frozen=True)
class Equatorial:
    """Right Ascension and Declination (Degrees)."""
    ra_deg: float
    dec_deg: float

@dataclass(frozen=True)
class Horizontal:
    """Altitude and Azimuth (Degrees). Azimuth is 0° at North, 90° at East."""
    alt_deg: float
    az_deg: float

# ============================================================
# Core Coordinate Transformations
# ============================================================

def ecliptic_to_equatorial(L_deg: float, B_deg: float, jd_tt: float) -> Equatorial:
    """Converts Ecliptic (Longitude, Latitude) to Equatorial (RA, Dec) of Date."""
    T = aa.T_centuries(jd_tt)
    eps_rad = math.radians(aa.mean_obliquity_deg(T))
    
    L_rad = math.radians(L_deg)
    B_rad = math.radians(B_deg)
    
    sin_dec = math.sin(B_rad) * math.cos(eps_rad) + math.cos(B_rad) * math.sin(eps_rad) * math.sin(L_rad)
    dec_deg = math.degrees(math.asin(sin_dec))
    
    y = math.sin(L_rad) * math.cos(eps_rad) - math.tan(B_rad) * math.sin(eps_rad)
    x = math.cos(L_rad)
    ra_deg = aa.wrap_deg(math.degrees(math.atan2(y, x)))
    
    return Equatorial(ra_deg=ra_deg, dec_deg=dec_deg)

def equatorial_to_horizontal(eq: Equatorial, jd_utc: float, lat_deg: float, lon_east_deg: float) -> Horizontal:
    """Converts Equatorial (RA, Dec) to Local Sky (Altitude, Azimuth)."""
    lst_deg = local_sidereal_time(jd_utc, lon_east_deg)
    
    # Hour Angle
    ha_deg = aa.wrap_deg(lst_deg - eq.ra_deg)
    
    ha_rad = math.radians(ha_deg)
    dec_rad = math.radians(eq.dec_deg)
    lat_rad = math.radians(lat_deg)
    
    # Altitude
    sin_alt = math.sin(lat_rad) * math.sin(dec_rad) + math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad)
    alt_deg = math.degrees(math.asin(sin_alt))
    
    # Azimuth (Measuring from North = 0, East = 90)
    y = math.sin(ha_rad)
    x = math.cos(ha_rad) * math.sin(lat_rad) - math.tan(dec_rad) * math.cos(lat_rad)
    
    az_south_deg = math.degrees(math.atan2(y, x))
    az_north_deg = aa.wrap_deg(az_south_deg + 180.0)
    
    return Horizontal(alt_deg=alt_deg, az_deg=az_north_deg)

def geocentric_to_topocentric(
    eq: Equatorial, 
    R_au: float, 
    lat_deg: float, 
    elevation_m: float, 
    jd_utc: float, 
    lon_east_deg: float
) -> Equatorial:
    """
    Converts Geocentric Equatorial coordinates to Topocentric (Observer) coordinates.
    Corrects for parallax based on the WGS84 Earth ellipsoid.
    """
    if R_au > 1000.0:  # Ignore parallax for stars and deep space objects
        return eq
        
    # WGS84 Earth ellipsoid constants
    a = 6378137.0  # Equatorial radius in meters
    f = 1.0 / 298.257223563  # Flattening
    
    # Solar equatorial horizontal parallax in degrees (~8.794 arcseconds)
    pi_sun_deg = 8.794143 / 3600.0
    
    # Target's equatorial horizontal parallax
    sin_pi = math.sin(math.radians(pi_sun_deg)) / R_au
    
    lat_rad = math.radians(lat_deg)
    
    # 1. Calculate observer's geocentric latitude and distance from center
    u = math.atan((1.0 - f) * math.tan(lat_rad))
    rho_sin_phi_prime = (1.0 - f) * math.sin(u) + (elevation_m / a) * math.sin(lat_rad)
    rho_cos_phi_prime = math.cos(u) + (elevation_m / a) * math.cos(lat_rad)
    
    # 2. Local Sidereal Time and Hour Angle
    lst_deg = local_sidereal_time(jd_utc, lon_east_deg)
    H_rad = math.radians(lst_deg - eq.ra_deg)
    dec_rad = math.radians(eq.dec_deg)
    
    # 3. Apply Parallax Corrections (Meeus Ch. 40)
    num_ra = -rho_cos_phi_prime * sin_pi * math.sin(H_rad)
    den_ra = math.cos(dec_rad) - rho_cos_phi_prime * sin_pi * math.cos(H_rad)
    
    delta_ra_rad = math.atan2(num_ra, den_ra)
    ra_top_deg = aa.wrap_deg(eq.ra_deg + math.degrees(delta_ra_rad))
    
    num_dec = (math.sin(dec_rad) - rho_sin_phi_prime * sin_pi) * math.cos(delta_ra_rad)
    den_dec = math.cos(dec_rad) - rho_cos_phi_prime * sin_pi * math.cos(H_rad)
    
    dec_top_deg = math.degrees(math.atan2(num_dec, den_dec))
    
    return Equatorial(ra_top_deg, dec_top_deg)

# ============================================================
# Sidereal Time & Refraction Helpers
# ============================================================

def local_sidereal_time(jd_utc: float, lon_east_deg: float) -> float:
    """
    Computes Local Apparent Sidereal Time in degrees.
    Uses the continuous Meeus formulation for GMST at any UT instant.
    """
    t = (jd_utc - 2451545.0) / 36525.0
    
    # GMST at 0h UT + continuous rotation
    gmst_deg = 280.46061837 + 360.98564736629 * (jd_utc - 2451545.0) + 0.000387933 * t**2 - (t**3 / 38710000.0)
    
    return aa.wrap_deg(gmst_deg + lon_east_deg)

def apply_refraction(true_alt_deg: float) -> float:
    """
    Converts True geometric altitude to Apparent visual altitude.
    Uses the Bennett (1982) formula. Accurate to ~0.015 arcmin down to the horizon.
    """
    if true_alt_deg < -5.0:
        return true_alt_deg  # Do not refract objects well below the horizon
        
    # Refraction in arcminutes
    r_arcmin = 1.02 / math.tan(math.radians(true_alt_deg + 10.3 / (true_alt_deg + 5.11)))
    return true_alt_deg + (r_arcmin / 60.0)