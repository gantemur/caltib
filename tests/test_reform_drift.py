"""The solar equation's secular drift in the exact reform engines.

The paper specifies it for the L3 day module and the L4 month module
(caltib paper, sections 5.5-5.6 and Appendix F.1.2): -1/(487 2^9 3^7 5)
turns per day on the 1-term solar equation of centre. The specs carried it
as amp1, but RationalDayEngine and RationalMonthEngine dropped it and
AffineTabSeriesT.eval ignored amp1.
"""
from fractions import Fraction

import pytest

import caltib
from caltib.engines.astro.affine_series import AffineTabSeriesT, PhaseT, TabTermT

DRIFT = Fraction(-1, 487 * 2**9 * 3**7 * 5)


def test_eval_uses_amplitude_drift():
    one = lambda phase: Fraction(1)
    term = TabTermT(amp=Fraction(3), phase=PhaseT(Fraction(0), Fraction(0)), table_eval_turn=one,
                    amp1=Fraction(1, 7))
    s = AffineTabSeriesT(A=Fraction(1), B=Fraction(2), terms=(term,))
    t = Fraction(10)
    assert s.eval(t) == 1 + 2 * t + (3 + t / 7)


@pytest.mark.parametrize("name,engine", [("l3", "day"), ("l4", "month"), ("l5", "month")])
def test_engines_carry_the_solar_drift(name, engine):
    eng = getattr(caltib.get_calendar(name), engine)
    solar = eng.solar_series.terms
    assert solar[0].amp == Fraction(6893, 1296000)
    assert solar[0].amp1 == DRIFT
    # In the elongation (moon minus sun) the solar terms enter negated, drift included.
    neg = [t for t in eng.elong_series.terms if t.amp == -solar[0].amp]
    assert len(neg) == 1 and neg[0].amp1 == -DRIFT


@pytest.mark.parametrize("name,engine", [("l3", "day"), ("l4", "month")])
def test_true_sun_includes_drift_far_from_j2000(name, engine):
    eng = getattr(caltib.get_calendar(name), engine)
    t = Fraction(-1_100_000)                       # about 1000 BCE
    term = eng.solar_series.terms[0]
    no_drift = eng.solar_series.eval(t) - term.amp1 * t * term.table_eval_turn(term.phase.eval(t))
    base_plus_terms = eng.solar_series.base(t) + sum(
        tt.amp * tt.table_eval_turn(tt.phase.eval(t)) for tt in eng.solar_series.terms)
    assert no_drift == base_plus_terms
    assert eng.solar_series.eval(t) != base_plus_terms
