"""Traditional solar longitude in turns, following Janson (7.19)-(7.23).

The raw solar table has quarter-wave values 0, 6, 10, 11. Its angular
correction is in 1/(27*60) turns, while its date correction is in 1/60 days.
Reference: https://arxiv.org/pdf/1401.6285, p. 24.
"""

from dataclasses import replace
from fractions import Fraction

import pytest

from caltib.api import get_calendar
from caltib.engines.trad_day import TraditionalDayEngine


@pytest.mark.parametrize("engine", ["phugpa", "tsurphu", "mongol", "bhutan", "karana"])
@pytest.mark.parametrize(
    "mean_sun, expected_true_sun",
    [
        pytest.param(Fraction(0), Fraction(11, 1620), id="negative-equation-peak"),
        pytest.param(Fraction(1, 4), Fraction(1, 4), id="zero-equation"),
        pytest.param(Fraction(1, 2), Fraction(799, 1620), id="positive-equation-peak"),
        pytest.param(Fraction(3, 4), Fraction(3, 4), id="second-zero-equation"),
        # Anomaly 1/24 turn is halfway through the first table interval: E = 3.
        pytest.param(Fraction(7, 24), Fraction(313, 1080), id="interpolation"),
        # Here E = -549/50, so the corrected longitude passes through one turn.
        pytest.param(Fraction(599, 600), Fraction(23, 4500), id="wraparound"),
    ],
)
def test_true_sun_matches_reference_table(engine, mean_sun, expected_true_sun):
    day = get_calendar(engine).day
    # The standard traditions have s1 = 30*s2, so this selects the mean phase
    # directly without using the implementation's solar correction or table.
    x = (mean_sun - day.p.s0) / day.p.s2
    assert day.mean_sun(x) == mean_sun
    assert day.true_sun(x) == expected_true_sun


def test_phugpa_integer_tithi_solar_peak():
    # Phugpa 2026 month 3, day 12: mean Sun = 0 and raw solar equation = -11.
    # The former /720 conversion produced 5.5 degrees instead of 22/9 degrees.
    day = get_calendar("phugpa").day
    assert day.mean_sun(36762) == 0
    assert day.true_sun(36762) == Fraction(11, 1620)


@pytest.mark.parametrize(
    "mean_sun, expected_date_correction",
    [
        (Fraction(0), Fraction(11, 60)),
        (Fraction(1, 2), Fraction(-11, 60)),
    ],
)
def test_true_date_keeps_its_separate_solar_units(mean_sun, expected_date_correction):
    # Suppress the lunar equation so the time-unit conversion is tested alone.
    params = replace(get_calendar("phugpa").day.p, moon_tab_quarter=(0,) * 8)
    day = TraditionalDayEngine(params)
    x = (mean_sun - day.p.s0) / day.p.s2
    assert day.true_date(x) - day.mean_date(x) == expected_date_correction
