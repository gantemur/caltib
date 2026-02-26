from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from .astro.sin_tables import OddPeriodicTable
from .astro.affine_series import PhaseDN, TabTermDN, AffineTabSeriesDN, PhaseT, SinTermT, AffineSinSeriesT
from .astro.deltat import DeltaTRationalModel
from .astro.sunrise import SunriseRationalModel, LocationRational


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
class TermDef:
    """Pure data representation of a series term."""
    amp: Fraction
    phase: PhaseT
    table_id: str  # "moon" or "sun"

@dataclass(frozen=True)
class RationalDayParamsNew:
    """Pure data parameters. No Callables here!"""
    A: Fraction
    B: Fraction
    terms: Tuple[TermDef, ...]
    iterations: int
    delta_t: DeltaTRationalModel
    sunrise: SunriseRationalModel
    location: LocationRational
    moon_tab_quarter: Tuple[int, ...]
    sun_tab_quarter: Tuple[int, ...]


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



# ============================================================
# New-mode engine: fixed iteration inversion x(t)=x0
# (Used by L1–L3 once we plug in σ_* and extra perturbations.)
# ============================================================

class RationalDayEngineNew:
    def __init__(self, p: RationalDayParamsNew):
        self.p = p
        
        # 1. Instantiate the tables
        moon_tab = OddPeriodicTable(N=28, quarter=p.moon_tab_quarter)
        sun_tab = OddPeriodicTable(N=12, quarter=p.sun_tab_quarter)
        
        # 2. Create a lookup directory of their callables
        eval_map = {
            "moon": moon_tab.eval_turn,
            "sun": sun_tab.eval_turn
        }
        
        # 3. Construct the active series dynamically
        active_terms = tuple(
            TabTermT(
                amp=t_def.amp, 
                phase=t_def.phase, 
                table_eval_turn=eval_map[t_def.table_id]
            )
            for t_def in p.terms
        )
        
        self.series = AffineTabSeriesT(A=p.A, B=p.B, terms=active_terms)

    def boundary_tt(self, x0: Fraction) -> Fraction:
        return self.series.picard_solve(x0, iterations=self.p.iterations)

    def boundary_utc(self, x0: Fraction) -> Fraction:
        """Convert TT boundary to UTC using Rational Delta T."""
        t_tt = self.boundary_tt(x0)
        dt_sec = self.p.delta_t.delta_t_seconds(t_tt)
        return t_tt - (dt_sec / Fraction(86400, 1))

    def end_jd(self, x0: Fraction) -> int:
        """
        Determine the civil Julian Day Number on which this tithi ends.
        
        A tithi ends on civil day J if:  dawn_utc(J) <= t_utc < dawn_utc(J+1).
        Standard JD shifts to the next integer at noon UTC, meaning midnight is J - 0.5.
        Therefore, dawn_utc(J) = J - 0.5 + sunrise_utc_fraction.
        
        Solving for J yields: J = floor(t_utc + 0.5 - sunrise_utc_fraction).
        """
        t_utc = self.boundary_utc(x0)
        
        # Seed J to calculate the dawn fraction (crucial later for L3 variable dawn)
        seed_j = int(t_utc) 
        dawn_frac = self.p.sunrise.sunrise_utc_fraction(seed_j, self.p.location)
        
        j_exact = t_utc + Fraction(1, 2) - dawn_frac
        return j_exact.numerator // j_exact.denominator


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
        if self.mode == "trad":
            return self._trad.end_jd(d, n)
            
        x0 = Fraction(n * 30 + d, 1)
        return self._new.end_jd(x0)

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
        hits = self._month_end_hits(n)
        first_jd, last_jd = self.month_bounds_jd(n)

        out: List[CivilDay] = []
        prev_label: Optional[int] = None

        for jd in range(first_jd, last_jd + 1):
            ended = hits.get(jd, [])
            if not ended:
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
