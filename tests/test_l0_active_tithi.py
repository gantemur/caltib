from dataclasses import replace
from datetime import date
from fractions import Fraction
from math import floor

import pytest

from caltib import get_calendar
from caltib.engines.arithmetic_day import ArithmeticDayEngine
from caltib.web_diag import api as web


def probes(day, x):
    boundary = day.true_date(x)
    epsilon = Fraction(1, 10**6)
    return (boundary - epsilon, boundary, boundary + epsilon,
            (boundary + day.true_date(x + 1)) / 2)


@pytest.mark.parametrize("x", [-100, -1, 0, 1, 100])
@pytest.mark.parametrize("engine", ["l0", "custom", "l1", "phugpa"])
def test_physical_inverse_uses_half_open_tithi_intervals(engine, x):
    if engine == "custom":
        params = get_calendar("l0").day.p
        day = ArithmeticDayEngine(replace(params, U=61, V=59, m0_loc=Fraction(24515409, 10)))
    else:
        day = get_calendar(engine).day
    assert [day.get_x_from_t2000(t) for t in probes(day, x)] == [x, x + 1, x + 1, x + 1]


def test_l0_diagnostic_steps_still_use_the_completed_tithi():
    day = get_calendar("l0").day
    times = [t for x in (-100, -1, 0, 1, 100) for t in probes(day, x)]
    times.extend(Fraction(i, 7) for i in range(-2000, 2001, 19))
    for t in times:
        # 0.3.8 completed-index formula, independent of the inverse API.
        completed = floor((t - (day.p.m0_loc - 2451545)) * day.p.U / day.p.V)
        elongation = Fraction(completed, 30)
        sun = (day.p.s0 + completed * day.p.s1 / 30) % 1
        assert day.mean_elong_tt(t) == day.true_elong_tt(t) == elongation
        assert day.mean_sun_tt(t) == day.true_sun_tt(t) == sun
        assert day.mean_moon_tt(t) == day.true_moon_tt(t) == elongation + sun


@pytest.mark.parametrize("year", [1927, 2000, 2024])
def test_web_offsets_use_the_active_index_window(monkeypatch, year):
    day = get_calendar("l0").day
    start, end = (date(year, month, d).toordinal() + Fraction("1721425.5") - 2451545
                  for month, d in ((1, 1), (12, 31)))
    # Compute enclosing tithi from the old step formula plus one.
    lo, hi = (floor((t - day.true_date(0)) / day.p.m2) + 1 for t in (start, end))
    assert day.true_date(lo - 1) <= start < day.true_date(lo)
    assert day.true_date(hi - 1) <= end < day.true_date(hi)
    sampled = []

    def record(index, guess):
        sampled.append(index)
        return guess

    monkeypatch.setattr(web, "find_exact_syzygy", record)
    result = web.get_offsets_payload("l0", year, year, "physical", "tithi")
    assert sampled == [x for x in range(lo, hi + 1) if x % 5 == 0]
    assert len(result["traces"][0]["x"]) == len(sampled)
