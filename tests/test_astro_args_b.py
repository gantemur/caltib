from __future__ import annotations

from math import isfinite

from caltib.reference.astro_args import (
    T_centuries,
    fundamental_args,
    mean_obliquity_deg,
    solar_mean_elements,
    jde_mean_new_moon,
    tropical_year_days,
)

def test_basic_ranges():
    jd = 2451545.0  # J2000
    T = T_centuries(jd)
    assert abs(T) < 1e-12

    fa = fundamental_args(T)
    for x in [fa.Lp_turn, fa.D_turn, fa.M_turn, fa.Mp_turn, fa.F_turn, fa.Omega_turn]:
        assert 0.0 <= x < 1.0

    eps = mean_obliquity_deg(T, model="iau2000")
    assert 23.0 < eps < 24.0

    sm = solar_mean_elements(T)
    assert 0.0 <= sm.L0_turn < 1.0
    assert 0.0 <= sm.M_turn < 1.0

def test_mean_new_moon_is_finite():
    # k=0 should be near early Jan 2000
    jde0 = jde_mean_new_moon(0.0)
    assert isfinite(jde0)
    assert 2451500.0 < jde0 < 2451600.0

def test_tropical_year_reasonable():
    T = 0.0
    y = tropical_year_days(T)
    assert 365.24 < y < 365.25