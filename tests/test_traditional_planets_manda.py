"""Exact table checks for Janson, Tibetan Calendar Mathematics, Appendix D."""

from fractions import Fraction
from math import floor

import pytest

from caltib import get_calendar


PLANETS = ("mercury", "venus", "mars", "jupiter", "saturn")
OFFSETS = (-1200, -31, -1, 0, 137, 615, 1826)


def periodic_value(grid, phase):
    """Interpolate a full grid with a duplicate final node at one turn."""
    position = phase * (len(grid) - 1)
    index = floor(position)
    weight = position - index
    node = index % (len(grid) - 1)
    return (1 - weight) * grid[node] + weight * grid[node + 1]


def manda_grid(quarter):
    # D.11 reflects the three intervals to form the positive half-wave.
    positive = quarter + quarter[-2::-1]
    return positive + tuple(-value for value in positive[1:])


def sighra_grid(half):
    # D.14 reflects the 14 nodes across 13.5; no node lies at half a turn.
    return half + tuple(-value for value in half[:0:-1]) + (0,)


def reference_longitudes(params, body, jd):
    elapsed = jd - params.jd0
    sun, heliocentric = (
        params.p0[key] + elapsed * params.p_rate[key] for key in ("sun", body)
    )
    slow, step = (sun, heliocentric) if body in ("mercury", "venus") else (heliocentric, sun)
    # Work in table units (minutes of one of 27 lunar mansions). Janson D.12
    # subtracts the signed manda value before locating the sighra argument.
    anomaly = slow - params.birth_signs[body]
    manda = periodic_value(manda_grid(params.manda_tables[body]), anomaly)
    slow_units = 27 * 60 * slow - manda
    difference = step - slow_units / (27 * 60)
    sighra = periodic_value(sighra_grid(params.sighra_tables[body]), difference)
    return slow % 1, ((slow_units + sighra) / (27 * 60)) % 1


@pytest.mark.parametrize("name", ["phugpa", "mongol", "tsurphu", "bhutan", "karana"])
@pytest.mark.parametrize("offset", OFFSETS)
def test_traditional_longitudes_against_signed_tables(name, offset):
    engine = get_calendar(name).planets
    params = engine.p
    epoch = 2424972 if name == "phugpa" else params.jd0
    jd = epoch + offset
    bulk = engine.longitudes(jd)
    for body in PLANETS:
        mean, true = reference_longitudes(params, body, jd)
        assert bulk[body] == {"mean": mean, "true": true}, body
        assert engine.mean_longitude(body, jd) == mean, body
        assert engine.true_longitude(body, jd) == true, body
    for body in ("sun", "rahu"):
        expected = (params.p0[body] + offset * params.p_rate[body]) % 1
        assert bulk[body] == {"mean": expected, "true": expected}, body
        assert engine.mean_longitude(body, jd) == expected, body
        assert engine.true_longitude(body, jd) == expected, body


def test_signed_table_reflection_and_wrap():
    engine = get_calendar("phugpa").planets
    for body in PLANETS:
        for table, grid in (
            (engine.manda[body], manda_grid(engine.p.manda_tables[body])),
            (engine.sighra[body], sighra_grid(engine.p.sighra_tables[body])),
        ):
            assert len(grid) - 1 in (12, 27)
            for phase in (Fraction(1, 12), Fraction(1, 2), Fraction(17, 27), Fraction(215, 216)):
                expected = periodic_value(grid, phase)
                assert table.eval_turn(phase - 1000) == expected
                assert table.eval_turn(-phase) == -expected
