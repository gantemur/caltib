import math
from dataclasses import replace

import pytest

from caltib import get_calendar, make_engine
from caltib.engines.fp_day import FloatDayEngine
from caltib.engines.specs import L5_SPEC, LOC_MONTREAL, fp_day


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


def reference_vector(p, x):
    """Independent fixed-order evaluation using the profile's coefficients."""
    q = (float(x) + 30 * p.epoch_k) / 30 - p.A_elong
    if p.picard_seed == "linear":
        t = q / p.B_elong
    else:
        root = math.sqrt(p.B_elong * p.B_elong + 4 * (p.C_elong * q))
        t = q / (0.5 * p.B_elong + 0.5 * root)
    vector = [t]
    reciprocal = 1.0 / p.B_elong
    for _ in range(3):
        harmonics = 0.0
        for terms, drift in ((p.elong_static, False), (p.elong_dynamic, True)):
            for term in terms:
                phase = (term.c0 + term.c1 * t + 0.5) % 1.0 - 0.5
                if phase > 0.25:
                    phase = 0.5 - phase
                elif phase < -0.25:
                    phase = -0.5 - phase
                square = phase * phase
                poly = p.sine_poly_coeffs[-1]
                for c in reversed(p.sine_poly_coeffs[:-1]):
                    poly = c + square * poly
                amplitude = term.amp + term.amp1 * t if drift else term.amp
                harmonics += amplitude * (phase * poly)
        t = (q - p.C_elong * (t * t) - harmonics) * reciprocal
        vector.append(t)
    return vector


@pytest.mark.parametrize("x", [-370000, 4735, 674149])
@pytest.mark.parametrize("seed", ["linear", "quadratic_mean"])
def test_l5_fixed_picard_vectors(x, seed):
    p = replace(L5_SPEC.day_params, picard_seed=seed)
    t0, *steps = reference_vector(p, x)
    day = FloatDayEngine(p)
    assert p.iterations == 3
    if seed == "quadratic_mean":
        assert day.mean_date(x) == t0
    else:
        assert FloatDayEngine(replace(p, iterations=0)).true_date(x) == t0
    for iteration, value in enumerate(steps, 1):
        assert FloatDayEngine(replace(p, iterations=iteration)).true_date(x) == value
    assert day.true_date(x) == steps[-1]


def test_seed_selector_is_validated_and_preserved_by_location_clone():
    assert fp_day(epoch_k=0).picard_seed == "linear"
    assert fp_day(epoch_k=0, picard_seed="quadratic_mean").picard_seed == "quadratic_mean"
    with pytest.raises(ValueError, match="Unknown Picard seed"):
        fp_day(epoch_k=0, picard_seed="unknown")
    with pytest.raises(ValueError, match="Unknown Picard seed"):
        replace(L5_SPEC.day_params, picard_seed="unknown")
    spec = replace(L5_SPEC, id=replace(L5_SPEC.id, name="l5-quadratic-mean"),
                   day_params=replace(L5_SPEC.day_params, picard_seed="quadratic_mean"))
    clone = make_engine(spec).with_location(LOC_MONTREAL)
    assert clone.id == spec.id
    assert clone.day.location == LOC_MONTREAL
    assert clone.day.p.picard_seed == "quadratic_mean"
    assert get_calendar("l5").day.p.picard_seed == "linear"
    assert get_calendar("l4").day.p.picard_seed == "linear"


def test_lhasa_label_near_dawn_depends_on_the_explicit_seed():
    default = get_calendar("l5")
    quadratic = make_engine(replace(L5_SPEC, day_params=replace(L5_SPEC.day_params,
                                                               picard_seed="quadratic_mean")))
    x, jdn = 674150, 3110486
    assert default.day.true_date(x) == 658940.66898931
    assert quadratic.day.true_date(x) == 658940.6690305865
    assert default.day.civil_jdn(x) == 3110485
    assert quadratic.day.civil_jdn(x) == 3110486
    keys = ("year", "month", "day", "occ")
    assert tuple(default.from_jdn(jdn)[key] for key in keys) == (3803, 12, 21, 1)
    assert tuple(quadratic.from_jdn(jdn)[key] for key in keys) == (3803, 12, 20, 2)
