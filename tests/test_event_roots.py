from types import SimpleNamespace

import pytest

from caltib.reference import coords, events
from caltib.reference import time_scales as ts


solve = events._solve_bisection


@pytest.mark.parametrize("step", [1 / 24, 1, 5])
@pytest.mark.parametrize("slope", [-1, 1])
@pytest.mark.parametrize("direction", [-1, 0, 1])
def test_inclusive_exact_start_with_direction(step, slope, direction):
    expected = 0 if direction in (0, slope) else None
    assert solve(lambda t: slope * t, 0, step, 2 * step, direction) == expected


@pytest.mark.parametrize("start", [-2451545.0, -2.0, 0.0, 2451545.0])
def test_exact_right_endpoint_and_midpoint(start):
    for delta in (0.5, 1.0):
        root = start + delta
        assert solve(lambda t: t - root, start, 1, 2, 1) == root
        assert solve(lambda t: t - root, start, 1, 2, -1) is None


def test_rejected_exact_start_can_be_followed_by_qualifying_root():
    assert solve(lambda t: t * (1 - t), 0, 1, 3, -1) == 1


def test_zero_plateaus_and_tangency_do_not_report_crossings():
    assert solve(lambda t: 0, 0, 1, 2) is None
    assert solve(lambda t: max(0, t - 0.25), 0, 1, 2) is None
    assert solve(lambda t: min(0, t - 1), 0, 1, 3) is None
    assert solve(lambda t: t + 0.25 if t < -0.25 else max(0, t - 0.25), -1, 2, 2) is None
    assert solve(lambda t: (t - 1)**2, 0, 1, 2) is None
    assert solve(lambda t: t + 1, 0, 1, 2) is None


@pytest.mark.parametrize("direction", [-1, 0, 1])
@pytest.mark.parametrize("sign", [-1, 1])
def test_exact_start_tangency_is_not_a_crossing(direction, sign):
    assert solve(lambda t: sign * t * t, 0, 1, 2, direction) is None


@pytest.mark.parametrize("direction", [-1, 0, 1])
def test_local_start_direction_with_two_crossings_in_one_step(direction):
    expected = 0 if direction <= 0 else pytest.approx(0.3, abs=1e-5)
    assert solve(lambda t: t * (t - 0.3), 0, 1, 2, direction) == expected


def test_wrap_guards_keep_a_real_zero_crossing():
    wrap = lambda x: (x + 180) % 360 - 180
    assert solve(lambda t: wrap(179 + 3*t), 0, 1, 2) is None
    assert solve(lambda t: 0 if t == 0 else wrap(180 + 3*t), 0, 1, 2) is None
    assert solve(lambda t: wrap(180*t), 0, 1, 2) == 0
    assert solve(lambda t: wrap(359 + 3*t), 0, 1, 2, 1) == pytest.approx(1/3, abs=1e-5)


def test_real_astronomical_targets_derived_from_exact_start():
    jd = 2451545.0
    tt = ts.jd_utc_to_jd_tt(jd)
    sun = events._get_ecliptic("sun", tt)[0]
    moon = events._get_ecliptic("moon", tt)[0]
    ra = events._get_equatorial("sun", tt)[0]
    ha = (coords.local_sidereal_time(jd, 0) - ra) % 360
    assert events.find_solar_longitude(jd, sun) == jd
    assert events.find_lunar_phase(jd, (moon - sun) % 360) == jd
    assert events.find_transit("sun", jd, 0, ha) == jd


def test_exact_conjunction_with_controlled_moving_geometry(monkeypatch):
    jd = 2451545.0
    tt = ts.jd_utc_to_jd_tt(jd)
    monkeypatch.setattr(events, "_get_ecliptic", lambda body, t: (
        29 + (t - tt) * (13 if body == "moon" else 1), 0, 1,
    ))
    assert events.find_conjunction("moon", "sun", jd) == jd


@pytest.mark.parametrize("rising", [True, False])
def test_exact_altitude_event_respects_direction(monkeypatch, rising):
    jd = 2451545.0
    slope = 1 if rising else -1
    monkeypatch.setattr(events, "_get_equatorial", lambda *args: (0, 0))
    monkeypatch.setattr(coords, "equatorial_to_horizontal", lambda eq, t, *args:
                        SimpleNamespace(alt_deg=slope * (t - jd)))
    assert events.find_altitude_event("sun", jd, 0, 0, apply_refraction=False, rising=rising) == jd
    assert events.find_altitude_event("sun", jd, 0, 0, apply_refraction=False, rising=not rising) is None
