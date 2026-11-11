"""Regression tests for three fixes (2026-11):

1. Tithi 30 of true month n is evaluated as (n, 30), not as (n + 1, 0); the
   lunar anomaly differs between the two because a1 != 30*a2 (mod 1).
   Expected values come from an independent older implementation (the
   author's zurhai.js), which evaluates day 30 traditionally.
2. PHUGPA_E1987_SPEC uses its own lunar anomaly epoch value.
3. The reform tiers take the sunrise nearest the approximate dawn; before,
   sunrise near 0h UTC (Lhasa) could be placed on the wrong UTC day.
"""
import math
import warnings
from datetime import date

import pytest

warnings.simplefilter("ignore")

import caltib  # noqa: E402
from caltib.engines import specs  # noqa: E402


@pytest.mark.parametrize(
    "engine, year, month, leap, jdn30",
    [
        ("bhutan", 2020, 2, False, 2458962),
        ("phugpa", 2099, 8, False, 2487991),
        ("karana", 2038, 6, True, 2465666),
        ("mongol", -446, 9, False, 1558397),
        ("tsurphu", 1287, 4, False, 2191267),
    ],
)
def test_day_30_uses_traditional_anomaly(engine, year, month, leap, jdn30):
    cal = caltib.get_calendar(engine)
    assert cal.to_jdn(year, month, leap, 30) == jdn30


def test_phugpa_e1987_matches_phugpa_e1927():
    e1927 = caltib.get_calendar("phugpa")
    e1987 = caltib.make_engine(specs.PHUGPA_E1987_SPEC)
    for year in range(1980, 2041):
        for month in range(1, 13):
            leaps = [True, False] if len(e1927.month.get_lunations(year, month)) == 2 else [False]
            for leap in leaps:
                for day in (1, 15, 30):
                    assert e1987.to_jdn(year, month, leap, day) == e1927.to_jdn(year, month, leap, day)


@pytest.mark.parametrize("engine", ["l0", "l1", "l2", "l3", "l4", "l5"])
def test_reform_new_year_2026(engine):
    # Astronomical new moon 2026-02-17 12:01 UTC (18:05 Lhasa mean time):
    # tithi 30 is current at dawn on 17 February, tithi 1 on 18 February.
    assert caltib.day_info(date(2026, 2, 17), engine=engine).tibetan.tithi == 30
    assert caltib.day_info(date(2026, 2, 18), engine=engine).tibetan.tithi == 1


@pytest.mark.parametrize("engine", ["l1", "l2"])
def test_constant_dawn_civil_day(engine):
    # L1 and L2 use a constant dawn at 06:00 local mean time: a tithi ending at
    # local mean time T belongs to the civil date of T - 6h.
    day = caltib.get_calendar(engine).day
    lon = float(day.p.location.lon_turn)
    for x in range(-1500, -1500 + 120):
        t_lmt = float(day.boundary_utc(x)) + 2451545 + lon
        assert day.civil_jdn(x) == math.floor(t_lmt - 0.25 + 0.5)
