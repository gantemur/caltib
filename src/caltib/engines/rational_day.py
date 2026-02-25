from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from .sin_tables import OddPeriodicTable
from .affine_series import PhaseDN, TabTermDN, AffineTabSeriesDN, PhaseT, SinTermT, AffineSinSeriesT


def frac_turn(x: Fraction) -> Fraction:
    q = x.numerator // x.denominator
    return x - Fraction(q, 1)


@dataclass(frozen=True)
class CivilDay:
    jd: int
    label: int
    repeated: bool = False
    skipped: bool = False


# ------------------------------------------------------------
# Traditional-mode parameters (Appendix A / §3.3.2)
# ------------------------------------------------------------

@dataclass(frozen=True)
class RationalDayParamsTrad:
    # base affine mean-date coefficients (days)
    m0: Fraction
    m1: Fraction
    m2: Fraction

    # anomaly phases in turns (3.33):contentReference[oaicite:9]{index=9}
    s0: Fraction
    s1: Fraction
    s2: Fraction

    a0: Fraction
    a1: Fraction
    a2: Fraction

    # tables given as quarter-wave samples in table-units (integers)
    moon_tab_quarter: Tuple[int, ...]  # length 28/4+1 = 8
    sun_tab_quarter: Tuple[int, ...]   # length 12/4+1 = 4


# ------------------------------------------------------------
# New-mode parameters (L1–L3 forward-looking)
# ------------------------------------------------------------

@dataclass(frozen=True)
class RationalDayParamsNew:
    """
    New-mode solver parameters for x(t)=x0 using fixed Picard iterations.

    - series: x(t)=A+B*t+Σ amp*sin(phase(t)).
    - iterations: fixed iteration count (reproducibility):contentReference[oaicite:10]{index=10}.
    - sin_eval_turn: to be supplied by caller/engine (table or minimax poly).
    """
    series: AffineSinSeriesT
    iterations: int


@dataclass(frozen=True)
class RationalDayParams:
    """
    Wrapper parameters selecting either:
      mode='trad' : use hard-coded true_date(d,n) (no inversion language)
      mode='new'  : use iteration solver (L1–L3)
    """
    mode: str = "trad"
    trad: Optional[RationalDayParamsTrad] = None
    new: Optional[RationalDayParamsNew] = None

    # Back-compat convenience: allow constructing the trad params directly
    # by passing the traditional fields (used by your current phugpa builder).
    m0: Fraction = Fraction(0, 1)
    s0: Fraction = Fraction(0, 1)
    a0: Fraction = Fraction(0, 1)
    m1: Fraction = Fraction(0, 1)
    m2: Fraction = Fraction(0, 1)
    s1: Fraction = Fraction(0, 1)
    s2: Fraction = Fraction(0, 1)
    a1: Fraction = Fraction(0, 1)
    a2: Fraction = Fraction(0, 1)
    moon_tab_quarter: Tuple[int, ...] = ()
    sun_tab_quarter: Tuple[int, ...] = ()


# ============================================================
# Traditional engine: t(d,n)=t0 + 1/60 moon_tab - 1/60 sun_tab
# ============================================================

class RationalDayEngineTrad:
    def __init__(self, p: RationalDayParamsTrad):
        self.p = p

        self.moon_table = OddPeriodicTable(N=28, quarter=p.moon_tab_quarter)
        self.sun_table = OddPeriodicTable(N=12, quarter=p.sun_tab_quarter)

        # phases Amoon, Asun (turns)
        self.phase_moon = PhaseDN(p.a0, p.a1, p.a2)
        self.phase_sun = PhaseDN(p.s0 - Fraction(1, 4), p.s1, p.s2)

        # build t(d,n) as an affine+table series (still “hard-coded”, no inversion)
        # (3.34)–(3.35):contentReference[oaicite:11]{index=11}
        self.series = AffineTabSeriesDN(
            base_c0=p.m0,
            base_cn=p.m1,
            base_cd=p.m2,
            terms=(
                TabTermDN(amp=Fraction(1, 60), phase=self.phase_moon, table_eval_turn=self.moon_table.eval_turn),
                TabTermDN(amp=Fraction(-1, 60), phase=self.phase_sun, table_eval_turn=self.sun_table.eval_turn),
            ),
        )
        # ------------------------------------------------------------
        # Solar longitude series (turns), for diagnostics/season checks.
        #
        # Assumption: solar table units represent "solar arcminutes of a sign",
        # so 60 units = 1 sign = 1/12 turn. Hence correction in turns is
        #   (table_value) / (60*12) = table_value / 720.
        #
        # This is intentionally separated from the time-series usage where
        # the same table is used with amplitude 1/60 days.
        # ------------------------------------------------------------
        self.sun_series = AffineTabSeriesDN(
            base_c0=p.s0,
            base_cn=p.s1,
            base_cd=p.s2,
            terms=(
                TabTermDN(
                    amp=Fraction(1, 60 * 12),  # 1/720 turn per table unit
                    phase=self.phase_sun,
                    table_eval_turn=self.sun_table.eval_turn,
                ),
            ),
        )

    def mean_sun(self, d: int, n: int) -> Fraction:
        """
        Mean solar longitude in turns, wrapped to [0,1).
        """
        s = self.p.s0 + self.p.s1 * Fraction(n, 1) + self.p.s2 * Fraction(d, 1)
        return frac_turn(s)

    def true_sun(self, d: int, n: int) -> Fraction:
        """
        True solar longitude in turns, wrapped to [0,1).
        """
        return frac_turn(self.sun_series.eval(d, n))

    def sun_equ_units(self, d: int, n: int) -> Fraction:
        """
        Raw table output (dimensionless) at the solar anomaly phase.
        Useful for diagnostics.
        """
        return self.sun_table.eval_turn(self.phase_sun.eval(d, n))

    def true_date(self, d: int, n: int) -> Fraction:
        return self.series.eval(d, n)

    def end_jd(self, d: int, n: int) -> int:
        t = self.true_date(d, n)
        return t.numerator // t.denominator

    def month_bounds_jd(self, n: int) -> tuple[int, int]:
        """(first_jd, last_jd) for lunation n in the civil-day numbering."""
        first_jd = self.end_jd(30, n - 1) + 1
        last_jd = self.end_jd(30, n)
        return first_jd, last_jd

    def _month_end_hits(self, n: int) -> Dict[int, List[int]]:
        hits: Dict[int, List[int]] = {}
        for d in range(1, 31):
            j = self.end_jd(d, n)
            hits.setdefault(j, []).append(d)
        return hits

    def civil_month(self, n: int) -> List[CivilDay]:
        """
        Civil-day labeling for lunation n over the *true* month interval:
        jd in [ end_jd(30,n-1)+1 , end_jd(30,n) ].

        If no tithi ends on a civil day, the day number repeats (repeated=True).
        If >=2 tithis end on a civil day, earlier one(s) are skipped; we mark skipped=True
        on the civil day whose label is the last-ended tithi.
        """
        hits = self._month_end_hits(n)
        first_jd, last_jd = self.month_bounds_jd(n)

        out: List[CivilDay] = []
        prev_label: Optional[int] = None  # <- change from 1 to None

        for jd in range(first_jd, last_jd + 1):
            ended = hits.get(jd, [])
            if not ended:
                # month start: default label 1, but NOT repeated
                if prev_label is None:
                    out.append(CivilDay(jd, 1, repeated=False))
                    prev_label = 1
                else:
                    out.append(CivilDay(jd, prev_label, repeated=True))
            else:
                label = ended[-1]
                out.append(CivilDay(jd, label, skipped=(len(ended) >= 2)))
                prev_label = label

        return out

    def lookup_civil_day(self, jd: int, n: int) -> Optional[CivilDay]:
        for cd in self.civil_month(n):
            if cd.jd == jd:
                return cd
        return None


# ============================================================
# New-mode engine: fixed iteration inversion x(t)=x0
# (Used by L1–L3 once we plug in σ_* and extra perturbations.)
# ============================================================

class RationalDayEngineNew:
    def __init__(self, p: RationalDayParamsNew, *, sin_eval_turn):
        self.p = p
        self._sin = sin_eval_turn

    def boundary_time(self, x0: Fraction) -> Fraction:
        return self.p.series.picard_solve(x0, iterations=self.p.iterations, sin_eval_turn=self._sin)


# ============================================================
# Unified wrapper used by _rational.py
# ============================================================

class RationalDayEngine:
    """
    Wrapper that preserves the existing interface used by your Phugpa engine:
      - true_date(d,n), end_jd(d,n), civil_month(n), lookup_civil_day(jd,n)
    In new-mode, you will call boundary_time(x0) instead (L1–L3 pipeline).
    """

    def __init__(self, params: RationalDayParams):
        # If params.trad is not provided, build it from the legacy fields.
        if params.mode == "trad":
            if params.trad is None:
                params = RationalDayParams(
                    mode="trad",
                    trad=RationalDayParamsTrad(
                        m0=params.m0,
                        m1=params.m1,
                        m2=params.m2,
                        s0=params.s0,
                        s1=params.s1,
                        s2=params.s2,
                        a0=params.a0,
                        a1=params.a1,
                        a2=params.a2,
                        moon_tab_quarter=params.moon_tab_quarter,
                        sun_tab_quarter=params.sun_tab_quarter,
                    ),
                )
            self.mode = "trad"
            self._trad = RationalDayEngineTrad(params.trad)
            self.p = params.trad  # for existing uses (m0,m1 etc.)
            self._new = None
            return

        if params.mode == "new":
            if params.new is None:
                raise ValueError("mode='new' requires params.new")
            self.mode = "new"
            self._new = params.new
            self._trad = None
            self.p = None
            return

        raise ValueError("mode must be 'trad' or 'new'")

    # --- traditional API ---
    def true_sun(self, d: int, n: int) -> Fraction:
        if self.mode != "trad":
            raise TypeError("true_sun(d,n) is only available in trad mode")
        return self._trad.true_sun(d, n)
        
    def true_date(self, d: int, n: int) -> Fraction:
        if self.mode != "trad":
            raise TypeError("true_date(d,n) is only available in trad mode")
        return self._trad.true_date(d, n)

    def end_jd(self, d: int, n: int) -> int:
        if self.mode != "trad":
            raise TypeError("end_jd(d,n) is only available in trad mode")
        return self._trad.end_jd(d, n)

    def civil_month(self, n: int) -> List[CivilDay]:
        if self.mode != "trad":
            raise TypeError("civil_month(n) is only available in trad mode")
        return self._trad.civil_month(n)

    def lookup_civil_day(self, jd: int, n: int) -> Optional[CivilDay]:
        if self.mode != "trad":
            raise TypeError("lookup_civil_day is only available in trad mode")
        return self._trad.lookup_civil_day(jd, n)

    # --- new-mode API ---
    def boundary_time(self, x0: Fraction, *, sin_eval_turn) -> Fraction:
        if self.mode != "new":
            raise TypeError("boundary_time is only available in new mode")
        eng = RationalDayEngineNew(self._new, sin_eval_turn=sin_eval_turn)
        return eng.boundary_time(x0)