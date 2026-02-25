# reference/solar.py

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple, Literal

from . import astro_args as aa
from . import time_scales as ts


@dataclass(frozen=True)
class SolarCoordinates:
    """True and apparent solar coordinates (degrees)."""
    L_true_deg: float
    L_app_deg: float


def solar_longitude(jd_tt: float) -> SolarCoordinates:
    """
    Computes true and apparent solar longitude for a given JD(TT)
    using truncated series expansions (accurate to ~0.01 deg).
    """
    T = aa.T_centuries(jd_tt)
    sm = aa.solar_mean_elements(T)
    fa = aa.fundamental_args(T)
    
    L0_deg = sm.L0_deg
    M_rad = math.radians(sm.M_deg)
    
    # (C.6) Equation of Center (C_sun)
    C_sun = (
        (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_rad)
        + (0.019993 - 0.000101 * T) * math.sin(2.0 * M_rad)
        + 0.000289 * math.sin(3.0 * M_rad)
    )
    
    L_true = aa.wrap_deg(L0_deg + C_sun)
    
    # (C.8) Apparent Longitude with aberration and leading nutation
    Omega_rad = math.radians(fa.Omega_deg)
    L_app = aa.wrap_deg(L_true - 0.00569 - 0.00478 * math.sin(Omega_rad))
    
    return SolarCoordinates(L_true_deg=L_true, L_app_deg=L_app)


def solar_declination_deg(L_app_deg: float, eps_deg: float) -> float:
    """
    (C.10) Solar declination from apparent longitude and obliquity.
    """
    sin_delta = math.sin(math.radians(eps_deg)) * math.sin(math.radians(L_app_deg))
    return math.degrees(math.asin(sin_delta))


def equation_of_time_minutes(jd_tt: float, eps_model: Literal["iau2000", "iau1980"] = "iau2000") -> float:
    """
    (C.13) Computes the Equation of Time (EOT) in minutes.
    """
    T = aa.T_centuries(jd_tt)
    sm = aa.solar_mean_elements(T)
    eps_deg = aa.mean_obliquity_deg(T, model=eps_model)
    coords = solar_longitude(jd_tt)
    
    L0_deg = sm.L0_deg
    L_app_rad = math.radians(coords.L_app_deg)
    eps_rad = math.radians(eps_deg)
    
    # (C.14) Right Ascension
    # Use atan2(y, x) to preserve the correct quadrant
    y = math.cos(eps_rad) * math.sin(L_app_rad)
    x = math.cos(L_app_rad)
    alpha_sun_deg = aa.wrap_deg(math.degrees(math.atan2(y, x)))
    
    # Wrap the difference to keep it tightly bounded around 0
    # Equivalent to EOT = 4 * (L0 - alpha_sun)
    diff_deg = aa.wrap_deg(L0_deg - alpha_sun_deg + 180.0) - 180.0
    
    return 4.0 * diff_deg


@dataclass(frozen=True)
class SunriseApparent:
    """Output for the Local Apparent Time of sunrise/sunset."""
    rise_app_hours: float
    set_app_hours: float


def sunrise_apparent_time(
    jd_tt: float, 
    lat_deg: float, 
    h0_deg: float = -0.833, 
    eps_model: Literal["iau2000", "iau1980"] = "iau2000"
) -> Optional[SunriseApparent]:
    """
    (C.11 & C.12) Computes sunrise and sunset in Local Apparent Solar Time (hours).
    Returns None if the sun does not rise or set (polar day/night).
    """
    coords = solar_longitude(jd_tt)
    eps_deg = aa.mean_obliquity_deg(aa.T_centuries(jd_tt), model=eps_model)
    delta_deg = solar_declination_deg(coords.L_app_deg, eps_deg)
    
    lat_rad = math.radians(lat_deg)
    delta_rad = math.radians(delta_deg)
    h0_rad = math.radians(h0_deg)
    
    cos_H0 = (math.sin(h0_rad) - math.sin(lat_rad) * math.sin(delta_rad)) / (math.cos(lat_rad) * math.cos(delta_rad))
    
    if cos_H0 < -1.0 or cos_H0 > 1.0:
        return None  # Sun never rises or never sets
        
    H0_deg = math.degrees(math.acos(cos_H0))
    
    # 15 degrees per hour
    rise_app = 12.0 - (H0_deg / 15.0)
    set_app = 12.0 + (H0_deg / 15.0)
    
    return SunriseApparent(rise_app_hours=rise_app, set_app_hours=set_app)


@dataclass(frozen=True)
class SunriseCivil:
    """Output for the uniform civil clock time (UTC) of sunrise/sunset."""
    rise_utc_hours: float
    set_utc_hours: float


def sunrise_sunset_utc(
    jd_utc_noon: float,
    lat_deg: float,
    lon_deg_east: float,
    eps_model: Literal["iau2000", "iau1980"] = "iau2000",
    h0_deg: float = -0.833
) -> Optional[SunriseCivil]:
    """
    (C.15) Iterative approach to compute accurate sunrise/sunset times in UTC hours.
    Expects jd_utc_noon to be the UTC JD of local noon (or 12:00 UTC for approximation).
    """
    # 1. Base approximation at noon
    jd_tt_base = ts.jd_utc_to_jd_tt(jd_utc_noon)
    app_times = sunrise_apparent_time(jd_tt_base, lat_deg, h0_deg, eps_model)
    if not app_times:
        return None
        
    # Standard time zone offset in hours
    dt_zone = ts.lmt_offset_hours(lon_deg_east)
    
    # Helper to refine a specific event (rise or set)
    def refine_event(app_time_hours: float) -> float:
        # Initial guess of the event's UTC time
        eot_base = equation_of_time_minutes(jd_tt_base, eps_model)
        utc_hours_guess = app_time_hours - (eot_base / 60.0) - dt_zone
        
        # Shift our JD(UTC) to the exact moment of the event
        jd_utc_event = math.floor(jd_utc_noon - 0.5) + 0.5 + (utc_hours_guess / 24.0)
        jd_tt_event = ts.jd_utc_to_jd_tt(jd_utc_event)
        
        # Recalculate parameters exactly at the event time
        refined_app = sunrise_apparent_time(jd_tt_event, lat_deg, h0_deg, eps_model)
        if not refined_app:
            return utc_hours_guess # Fallback if boundary shifts over pole
            
        eot_event = equation_of_time_minutes(jd_tt_event, eps_model)
        
        # If refining rise, use the refined rise H0; if setting, use the refined set H0
        if app_time_hours < 12.0:
            final_app = refined_app.rise_app_hours
        else:
            final_app = refined_app.set_app_hours
            
        return final_app - (eot_event / 60.0) - dt_zone
        
    rise_utc = refine_event(app_times.rise_app_hours) % 24.0
    set_utc = refine_event(app_times.set_app_hours) % 24.0
    
    return SunriseCivil(rise_utc_hours=rise_utc, set_utc_hours=set_utc)