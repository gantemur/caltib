# tests/test_time_scales.py

import pytest
import random
from datetime import date, datetime, timezone

from caltib.reference import time_scales as ts

def test_jdn_date_roundtrip():
        random.seed(42)
        # Constrain to year 1 - 9999 to avoid datetime out of range
        for _ in range(10000):
            jdn_in = random.randint(1721426, 5373484)
            d = ts.jdn_to_date(jdn_in)
            jdn_out = ts.date_to_jdn(d)
            assert jdn_in == jdn_out

def test_jd_datetime_roundtrip():
    """
    Test sub-day UTC round-tripping between continuous Julian Dates 
    and timezone-aware datetime objects.
    """
    random.seed(42)
    for _ in range(1000):
        # Constrain to standard Unix timestamp range to avoid datetime overflow
        jd_in = random.uniform(2400000.5, 2500000.5) 
        dt = ts.jd_to_datetime_utc(jd_in)
        jd_out = ts.datetime_utc_to_jd(dt)
        # 1e-8 days is roughly a millisecond
        assert jd_in == pytest.approx(jd_out, abs=1e-8)

def test_known_epochs():
    """
    Validate standard J2000.0 and Unix epochs.
    """
    # J2000.0 civil date is January 1, 2000
    assert ts.date_to_jdn(date(2000, 1, 1)) == 2451545
    
    # Unix epoch is 1970-01-01 00:00:00 UTC
    unix_dt = datetime(1970, 1, 1, tzinfo=timezone.utc)
    assert ts.datetime_utc_to_jd(unix_dt) == 2440587.5

def test_tt_utc_conversion_stability():
    """
    Test that the fixed-point iteration for TT -> UTC conversion
    successfully inverts the UTC -> TT conversion.
    """
    jd_utc_initial = 2451545.0
    jd_tt = ts.jd_utc_to_jd_tt(jd_utc_initial)
    jd_utc_recovered = ts.jd_tt_to_jd_utc(jd_tt)
    
    # Check recovery to within a millisecond
    assert jd_utc_initial == pytest.approx(jd_utc_recovered, abs=1e-8)