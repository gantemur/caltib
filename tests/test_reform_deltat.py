"""Delta T in the reform day engines takes days since J2000.0.

Regression tests for a slip where the float engine (L4, L5) and the exact
engine's dawn step (L3) passed a calendar year instead, so that Delta T was
evaluated near the year 2005 for every date.
"""
from fractions import Fraction

import pytest

import caltib


class RecordingDeltaT:
    """Wraps an engine's Delta T model and records every argument."""

    def __init__(self, inner):
        self.inner = inner
        self.args = []

    def delta_t_seconds(self, t2000):
        self.args.append(t2000)
        return self.inner.delta_t_seconds(t2000)

    def delta_t_seconds_year(self, year):
        return self.inner.delta_t_seconds_year(year)


def tithi_in_year(cal, year):
    n = cal.month.get_lunations(year, 1)[0]
    return 30 * (n + cal.delta_k) + 15


@pytest.mark.parametrize("name", ["l3", "l4", "l5"])
@pytest.mark.parametrize("year", [-1000, 1600, 3000])
def test_delta_t_receives_days_near_the_boundary(name, year):
    cal = caltib.get_calendar(name)
    rec = RecordingDeltaT(cal.day.delta_t)
    cal.day.delta_t = rec
    x = tithi_in_year(cal, year)
    t_tt = cal.day.true_date(x)
    cal.day.civil_jdn(x)
    assert rec.args, "Delta T was not consulted"
    for a in rec.args:
        # The boundary and the dawn near it: within two days of the boundary.
        assert abs(a - t_tt) < 2, (name, year, a, t_tt)


@pytest.mark.parametrize("name", ["l3", "l4", "l5"])
def test_delta_t_is_hours_around_1000_bce(name):
    cal = caltib.get_calendar(name)
    x = tithi_in_year(cal, -1000)
    t_tt = cal.day.true_date(x)
    dt_days = t_tt - cal.day.boundary_utc(x)
    # Quadratic model -20 + 32 u^2 with u = (year - 1820) / 100: about 25,000 s.
    assert 20000 < float(dt_days) * 86400 < 30000
