# tests/test_sunrise.py

import pytest
from unittest.mock import patch
import math

from caltib.reference import solar
from caltib.reference import astro_args as aa
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


@pytest.mark.parametrize("jd, latitude, state", [
    (2451716, 78, "polar_day"), (2451899, 78, "polar_night"),
    (2451716, -78, "polar_night"), (2451899, -78, "polar_day"),
])
def test_reference_polar_states(jd, latitude, state):
    result = solar.sunrise_sunset_utc(jd, latitude, 25)
    assert result.state.value == state
    assert math.isnan(result.rise_utc_hours) and math.isnan(result.set_utc_hours)


def test_noon_approximation_can_leave_both_events_unresolved():
    jd, lat, lon = 2451561, 70, 90
    assert solar.sunrise_apparent_time(ts.jd_utc_to_jd_tt(jd), lat).state.value == "normal"
    result = solar.sunrise_sunset_utc(jd, lat, lon)
    assert result.state.value == "transition"
    assert math.isnan(result.rise_utc_hours) and math.isnan(result.set_utc_hours)


def solar_altitude(jd, latitude, local_mean_noon):
    # Spherical altitude at an instant, evaluated without an event solver.
    tt = ts.jd_utc_to_jd_tt(jd)
    obliquity = aa.mean_obliquity_deg(aa.T_centuries(tt))
    declination = solar.solar_declination_deg(solar.solar_longitude(tt).L_app_deg, obliquity)
    hour_angle = math.tau * (jd - local_mean_noon + solar.equation_of_time_minutes(tt) / 1440)
    phi, delta = map(math.radians, (latitude, declination))
    return math.degrees(math.asin(math.sin(phi) * math.sin(delta)
                                  + math.cos(phi) * math.cos(delta) * math.cos(hour_angle)))


@pytest.mark.parametrize("jd, lat, rising", [(2451726, 66, False), (2451866, -70, True)])
def test_transition_retains_the_resolved_crossing(jd, lat, rising):
    lon = 90
    result = solar.sunrise_sunset_utc(jd, lat, lon)
    assert result.state.value == "transition"
    hours = result.rise_utc_hours if rising else result.set_utc_hours
    missing = result.set_utc_hours if rising else result.rise_utc_hours
    assert math.isnan(missing)
    assert 0 <= hours < 24

    midnight = jd - 0.5
    noon_hours = 12 - lon / 15
    crossing = midnight + (noon_hours + (hours - noon_hours + 12) % 24 - 12) / 24
    noon = midnight + noon_hours / 24
    before, at, after = [solar_altitude(crossing + minutes / 1440, lat, noon)
                          for minutes in (-5, 0, 5)]
    assert at == pytest.approx(-0.833, abs=0.01)
    if rising:
        assert before < -0.833 < after
    else:
        assert after < -0.833 < before


@pytest.mark.parametrize("longitude", [-179.9, 0, 179.9])
def test_moderate_latitude_utc_hours_wrap_at_date_line(longitude):
    jd = 2451545
    result = solar.sunrise_sunset_utc(jd, 35, longitude)
    assert result.state.value == "normal"
    for hours in (result.rise_utc_hours, result.set_utc_hours):
        assert 0 <= hours < 24
        noon_hours = 12 - longitude / 15
        unwrapped = noon_hours + (hours - noon_hours + 12) % 24 - 12
        assert solar_altitude(jd - 0.5 + unwrapped / 24, 35,
                              jd - 0.5 + noon_hours / 24) == pytest.approx(-0.833, abs=0.02)


def test_cli_reports_unresolved_clock_times(capsys):
    from caltib.cli import cmd_solar

    assert cmd_solar(["--jd-utc", "2451561", "--lat", "70", "--lon", "90"]) == 0
    output = capsys.readouterr().out
    assert "UTC Clock State    : transition" in output
    assert "UTC Clock Rise     : unavailable" in output
    assert "UTC Clock Set      : unavailable" in output
