from __future__ import annotations

import math
import logging
from typing import Callable, Union, List, Dict, Any

from . import astro_args as aa
from . import time_scales as ts
from . import coords
from . import planets
from . import stars

logger = logging.getLogger(__name__)

# ============================================================
# Unified Coordinate Fetchers
# ============================================================

def _get_ecliptic(body: Union[str, int], jd_tt: float) -> tuple[float, float, float]:
    """Returns Ecliptic (Longitude, Latitude, Radius) of date."""
    if isinstance(body, int):
        ecl = stars.get_star_ecliptic(body, jd_tt)
        return ecl.L_deg, ecl.B_deg, 1e6  # Dummy infinite distance for stars
        
    geo = planets.geocentric_position(body, jd_tt)
    return geo.L_true_deg, geo.B_true_deg, geo.R_true_au

def _get_equatorial(body: Union[str, int], jd_tt: float) -> tuple[float, float]:
    """Returns Equatorial (Right Ascension, Declination) of date."""
    if isinstance(body, int):
        eq = stars.get_star_equatorial(body, jd_tt)
        return eq.ra_deg, eq.dec_deg
        
    geo = planets.geocentric_position(body, jd_tt)
    eq = coords.ecliptic_to_equatorial(geo.L_true_deg, geo.B_true_deg, jd_tt)
    return eq.ra_deg, eq.dec_deg

# ============================================================
# Direction-Aware Bisection Solver
# ============================================================

def _solve_bisection(
    func: Callable[[float], float], 
    jd_start: float, 
    step_days: float, 
    max_days: float, 
    direction: int = 0
) -> float | None:
    """
    Steps forward to bracket a root, then bisects to ~1 second precision.
    direction: 1 (requires positive slope), -1 (requires negative slope), 0 (any).
    """
    jd = jd_start
    f1 = func(jd)
    
    while jd < jd_start + max_days:
        jd_next = jd + step_days
        f2 = func(jd_next)
        
        # Check if function crossed 0 (ignoring artificial 360-degree wrapping jumps)
        if (f1 * f2 <= 0.0) and abs(f1 - f2) < 180.0:
            
            # Filter by slope direction if requested
            is_increasing = f2 > f1
            if (direction == 1 and not is_increasing) or (direction == -1 and is_increasing):
                jd = jd_next
                f1 = f2
                continue
                
            a, b = jd, jd_next
            
            # Bisect down to ~1 second (1e-5 days)
            for _ in range(30):
                mid = (a + b) / 2.0
                f_mid = func(mid)
                
                if f_mid == 0.0 or (b - a) < 1e-5:
                    return mid
                    
                if f1 * f_mid < 0:
                    b = mid
                else:
                    a = mid
                    f1 = f_mid
            return (a + b) / 2.0
            
        jd = jd_next
        f1 = f2
        
    return None

# ============================================================
# 1. Local Sky Events (Rise, Set, Transit)
# ============================================================

def find_transit(body: Union[str, int], jd_utc_start: float, lon_east_deg: float, target_ha_deg: float = 0.0) -> float | None:
    """Finds the next time the body crosses the specified Hour Angle (default 0 is meridian transit)."""
    def transit_func(jd_utc: float) -> float:
        jd_tt = ts.jd_utc_to_jd_tt(jd_utc)
        ra_deg, _ = _get_equatorial(body, jd_tt)
        lst_deg = coords.local_sidereal_time(jd_utc, lon_east_deg)
        ha_deg = aa.wrap_deg(lst_deg - ra_deg)
        return ((ha_deg - target_ha_deg + 180.0) % 360.0) - 180.0
        
    return _solve_bisection(transit_func, jd_utc_start, step_days=1/24, max_days=2.0)

def find_altitude_event(
    body: Union[str, int], 
    jd_utc_start: float, 
    lat_deg: float, 
    lon_east_deg: float, 
    target_alt_deg: float = 0.0, 
    apply_refraction: bool = True, 
    rising: bool = True
) -> float | None:
    """Finds the next time the body crosses a specific altitude (Rise/Set)."""
    def alt_func(jd_utc: float) -> float:
        jd_tt = ts.jd_utc_to_jd_tt(jd_utc)
        ra_deg, dec_deg = _get_equatorial(body, jd_tt)
        eq = coords.Equatorial(ra_deg=ra_deg, dec_deg=dec_deg)
        horiz = coords.equatorial_to_horizontal(eq, jd_utc, lat_deg, lon_east_deg)
        
        alt = horiz.alt_deg
        if apply_refraction:
            alt = coords.apply_refraction(alt)
            
        return alt - target_alt_deg

    direction = 1 if rising else -1
    return _solve_bisection(alt_func, jd_utc_start, step_days=1/24, max_days=2.0, direction=direction)

# ============================================================
# 2. Orbital Events (Conjunctions, Phases, Equinoxes)
# ============================================================

def find_conjunction(body1: Union[str, int], body2: Union[str, int], jd_utc_start: float) -> float | None:
    """Finds the next exact conjunction in Ecliptic Longitude."""
    def conjunction_func(jd_utc: float) -> float:
        jd_tt = ts.jd_utc_to_jd_tt(jd_utc)
        L1, _, _ = _get_ecliptic(body1, jd_tt)
        L2, _, _ = _get_ecliptic(body2, jd_tt)
        return ((L1 - L2 + 180.0) % 360.0) - 180.0
        
    return _solve_bisection(conjunction_func, jd_utc_start, step_days=1.0, max_days=40.0)

def find_solar_longitude(jd_utc_start: float, target_lon_deg: float) -> float | None:
    """Finds equinoxes (0, 180) and solstices (90, 270)."""
    def sun_lon_func(jd_utc: float) -> float:
        jd_tt = ts.jd_utc_to_jd_tt(jd_utc)
        L_sun, _, _ = _get_ecliptic("sun", jd_tt)
        return ((L_sun - target_lon_deg + 180.0) % 360.0) - 180.0
        
    return _solve_bisection(sun_lon_func, jd_utc_start, step_days=5.0, max_days=380.0)

def find_lunar_phase(jd_utc_start: float, target_elongation_deg: float) -> float | None:
    """Finds exact lunar phases. 0=New, 90=First Qtr, 180=Full, 270=Last Qtr."""
    def phase_func(jd_utc: float) -> float:
        jd_tt = ts.jd_utc_to_jd_tt(jd_utc)
        L_sun, _, _ = _get_ecliptic("sun", jd_tt)
        L_moon, _, _ = _get_ecliptic("moon", jd_tt)
        elongation = aa.wrap_deg(L_moon - L_sun)
        return ((elongation - target_elongation_deg + 180.0) % 360.0) - 180.0
        
    return _solve_bisection(phase_func, jd_utc_start, step_days=1.0, max_days=35.0)

# ============================================================
# 3. Eclipse Prediction
# ============================================================

def find_next_eclipse(jd_utc_start: float, eclipse_type: str = "solar") -> Dict[str, Any] | None:
    """
    Scans forward to find the next eclipse.
    Warning: The solar eclipse path is a highly simplified sub-lunar point proxy.
    """
    if eclipse_type not in ["solar", "lunar"]:
        raise ValueError("eclipse_type must be 'solar' or 'lunar'")
        
    target_elongation = 0.0 if eclipse_type == "solar" else 180.0
    lat_limit = 1.5 if eclipse_type == "solar" else 1.2
    
    jd = jd_utc_start
    while jd < jd_utc_start + 400.0:  # Scan up to ~1 year
        jd_syzygy = find_lunar_phase(jd, target_elongation)
        if not jd_syzygy:
            break
            
        jd_tt = ts.jd_utc_to_jd_tt(jd_syzygy)
        _, B_moon, _ = _get_ecliptic("moon", jd_tt)
        
        # Check if Moon is close enough to the ecliptic node
        if abs(B_moon) <= lat_limit:
            result = {
                "jd_utc": jd_syzygy,
                "type": eclipse_type,
                "moon_lat_deg": B_moon
            }
            
            if eclipse_type == "solar":
                logger.warning("Solar eclipse path is a rough Sub-Lunar proxy. Do not use for local observation planning.")
                
                # Approximate the center of the eclipse path using the Sub-Lunar Point
                ra_moon, dec_moon = _get_equatorial("moon", jd_tt)
                gmst_deg = coords.local_sidereal_time(jd_syzygy, 0.0)
                
                # Longitude = RA - GMST (wrapped to -180 to 180)
                sub_lunar_lon = ((ra_moon - gmst_deg + 180.0) % 360.0) - 180.0
                
                result["rough_path_center"] = {
                    "lat_deg": dec_moon,
                    "lon_deg": sub_lunar_lon
                }
                
            return result
            
        jd = jd_syzygy + 15.0  # Skip ahead past this syzygy
        
    return None