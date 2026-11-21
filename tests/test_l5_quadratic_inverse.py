import math
from dataclasses import replace

import pytest

from caltib import get_calendar
from caltib.engines.fp_day import FloatDayEngine


@pytest.mark.parametrize("years", [-2000, -1000, -500, -100, 0, 100, 500, 1000, 2000])
def test_l5_mean_inverse_round_trip(years):
    day = get_calendar("l5").day
    p = day.p
    t = years * 365.25
    target = math.fsum((p.A_elong, p.B_elong * t, p.C_elong * t * t))
    x = 30 * target - day.epoch_offset_x
    # Formation of the rounded target and its conversion to a tithi
    # coordinate allow a few ulps at the time scale of each probe.
    assert day.mean_date(x) == pytest.approx(t, abs=3e-10, rel=0)


def synthetic(rate, quadratic):
    p = get_calendar("l5").day.p
    return FloatDayEngine(replace(p, epoch_k=0, A_elong=0, B_elong=rate, C_elong=quadratic))


@pytest.mark.parametrize("rate", [0.03125, -0.03125])
@pytest.mark.parametrize("quadratic", [0.0, 1e-16, -1e-16, 2e-5])
@pytest.mark.parametrize("t", [-17.0, -1e-9, 0.0, 1e-9, 17.0])
def test_inverse_stays_on_branch_continuous_with_linear_solution(rate, quadratic, t):
    day = synthetic(rate, quadratic)
    target = rate * t + quadratic * t * t
    assert day.mean_date(30 * target) == pytest.approx(t, rel=2e-15, abs=1e-23)


@pytest.mark.parametrize("rate, quadratic, target", [
    (0, 1, 0), (0, 0, 1), (2, -1, 2), (2, -1, 1), (1, 1, math.inf),
])
def test_inverse_rejects_unsupported_targets(rate, quadratic, target):
    with pytest.raises(ValueError):
        synthetic(rate, quadratic).mean_date(30 * target)


def test_l5_true_date_still_uses_three_picard_steps_from_mean_root():
    day = get_calendar("l5").day
    series = day.elong_series
    x = 30 * series.base(365250.0) - day.epoch_offset_x
    target = (x + day.epoch_offset_x) / 30
    q = target - series.A
    seed = 2 * q / (series.B + math.sqrt(series.B**2 + 4 * series.C * q))
    assert day.p.iterations == 3
    t = seed
    for _ in range(3):
        perturbation = series.eval(t) - series.base(t)
        t = (q - series.C * t * t - perturbation) / series.B
    assert day.true_date(x) == pytest.approx(t, abs=3e-10, rel=0)
