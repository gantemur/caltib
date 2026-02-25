# tests/test_sunrise.py

import pytest
from unittest.mock import patch
import math

from caltib.reference import solar
from caltib.reference import time_scales as ts

# --- NREL SPA Test Case (Appendix A.5) ---
# Date: October 17, 2003
# Time Zone: -7 hours
# Longitude: -105.1786 deg (West)
# Latitude: 39.742476 deg (North)
# Delta T: 67 seconds
# 
# Targets:
# L_app = 204.008551 deg
# EOT = 14.641503 min
# Sunrise UT = 13:12:43.46
# Sunset UT = 00:20:19.19 (next day)

@pytest.fixture
def mock_delta_t():
    """
    Force the time_scales module to return exactly 67.0 seconds for Delta T,
    bypassing the internal IERS table/polynomial logic for this specific test.
    """
    with patch("caltib.reference.time_scales.delta_t_seconds") as mock:
        mock.return_value = 67.0
        yield mock

def test_nrel_spa_solar_longitude(mock_delta_t):
    # NREL Test: 2003-10-17 12:30:30 LST (UTC -7) -> 19:30:30 UTC
    jd_utc = 2452930.312847
    jd_tt = jd_utc + (67.0 / 86400.0)
    
    coords = solar.solar_longitude(jd_tt)
    
    # Our 3-term analytical series is designed to be accurate to ~0.01 deg
    target_l_app = 204.008551
    assert coords.L_app_deg == pytest.approx(target_l_app, abs=0.015)

def test_nrel_spa_equation_of_time(mock_delta_t):
    jd_utc = 2452930.312847
    jd_tt = jd_utc + (67.0 / 86400.0)
    
    eot_mins = solar.equation_of_time_minutes(jd_tt, eps_model="iau2000")
    
    # Tolerance of 0.1 minutes (6 seconds) due to truncation
    target_eot = 14.641503
    assert eot_mins == pytest.approx(target_eot, abs=0.1)

def test_nrel_spa_sunrise_sunset(mock_delta_t):
    # NREL Sunrise/Sunset iteration requires jd_utc at local noon.
    # October 17, 2003 at 12:00:00 UTC is exactly JD 2452930.0
    jd_utc_noon = 2452930.0
    
    lon_east = -105.1786  # NREL uses negative for West
    lat = 39.742476
    
    civil_times = solar.sunrise_sunset_utc(
        jd_utc_noon=jd_utc_noon, 
        lat_deg=lat, 
        lon_deg_east=lon_east, 
        eps_model="iau2000",
        h0_deg=-0.833
    )
    
    assert civil_times is not None
    
    # 1. Test Sunrise
    # NREL Target: 13:12:43.46
    target_rise_hours = 13.0 + (12.0 / 60.0) + (43.46 / 3600.0)
    
    # Tolerance of 0.03 hours (2 minutes) accounts for the truncation of the 
    # 3-term solar model and the lack of NREL's pressure/temperature topocentric refraction.
    assert civil_times.rise_utc_hours == pytest.approx(target_rise_hours, abs=0.03)
    
    # 2. Test Sunset
    # NREL Target: 00:20:19.19
    target_set_hours = 0.0 + (20.0 / 60.0) + (19.19 / 3600.0)
    
    assert civil_times.set_utc_hours == pytest.approx(target_set_hours, abs=0.03)