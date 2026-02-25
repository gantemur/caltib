# tests/test_astro_args.py

import pytest
from caltib.reference import astro_args as aa

def test_meeus_example_47a_lunar_fundamentals():
    """
    Test against Jean Meeus, Astronomical Algorithms (2nd Ed), Example 47.a.
    Date: 1992 April 12, 0h TD (TT).
    JD: 2448724.5
    """
    jd_tt = 2448724.5
    T = aa.T_centuries(jd_tt)
    
    # Assert Julian centuries
    assert T == pytest.approx(-0.077221081451, abs=1e-12)

    fa = aa.fundamental_args(T)
    
    # Meeus provides these exact targets for the mean elements
    assert fa.Lp_deg == pytest.approx(134.290182, abs=1e-6)
    assert fa.D_deg  == pytest.approx(113.842304, abs=1e-6)
    assert fa.M_deg  == pytest.approx(97.643514, abs=1e-6)
    assert fa.Mp_deg == pytest.approx(5.150833, abs=1e-6)
    assert fa.F_deg  == pytest.approx(219.889721, abs=1e-6)

    # Eccentricity factor E for this date
    E = aa.eccentricity_factor(T)
    assert E == pytest.approx(1.000194, abs=1e-6)

def test_meeus_example_25a_solar_mean_elements():
    """
    Test against Jean Meeus, Astronomical Algorithms (2nd Ed), Example 25.a.
    Date: 1992 October 13, 0h TD (TT).
    JD: 2448908.5
    """
    jd_tt = 2448908.5
    T = aa.T_centuries(jd_tt)
    
    assert T == pytest.approx(-0.072183436, abs=1e-9)

    sm = aa.solar_mean_elements(T)
    
    assert sm.L0_deg == pytest.approx(201.80720, abs=1e-5)
    assert sm.M_deg  == pytest.approx(278.99397, abs=1e-5)

def test_meeus_example_22a_obliquity_and_node():
    """
    Test against Jean Meeus, Astronomical Algorithms (2nd Ed), Example 22.a.
    Date: 1987 April 10, 0h TD (TT).
    JD: 2446895.5
    """
    jd_tt = 2446895.5
    T = aa.T_centuries(jd_tt)
    
    assert T == pytest.approx(-0.127296372348, abs=1e-12)

    # The IAU 1980 mean obliquity target is 23° 26' 27.407"
    target_eps0 = 23.0 + 26.0 / 60.0 + 27.407 / 3600.0
    
    eps0_1980 = aa.mean_obliquity_deg(T, model="iau1980")
    assert eps0_1980 == pytest.approx(target_eps0, abs=1e-6)

    fa = aa.fundamental_args(T)
    # Longitude of ascending node
    assert fa.Omega_deg == pytest.approx(11.2531, abs=1e-4)

def test_mean_periods_consistency():
    """
    Sanity check the mean periods around J2000.0 (T=0)
    to ensure the constants are correctly transcribed.
    """
    T = 0.0
    
    # Tropical year should be roughly 365.24219 days
    assert aa.tropical_year_days(T) == pytest.approx(365.242189, abs=1e-6)
    
    # Synodic month should be roughly 29.530588 days
    assert aa.synodic_month_days(T) == pytest.approx(29.5305888, abs=1e-7)
    
    # Anomalistic month should be roughly 27.55455 days
    assert aa.anomalistic_month_days(T) == pytest.approx(27.5545498, abs=1e-7)