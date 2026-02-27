from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from .astro.sin_tables import OddPeriodicTable
from .astro.affine_series import PhaseDN, TabTermDN, AffineTabSeriesDN, TermDef, PhaseT, TabTermT, AffineTabSeriesT
from .astro.deltat import DeltaTRationalDef, ConstantDeltaTRationalDef, QuadraticDeltaTRationalDef, ConstantDeltaTRational, QuadraticDeltaTRational
from .astro.sunrise import LocationRational, SunriseRationalDef, ConstantSunriseRationalDef, SphericalSunriseRationalDef, ConstantSunriseRational, SphericalSunriseRational



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
# New-mode parameters (L1–L3)
# ------------------------------------------------------------

@dataclass(frozen=True)
class RationalDayParamsNew:
    """Pure data parameters. Solar and Lunar definitions are explicitly separated."""
    A_sun: Fraction
    B_sun: Fraction
    solar_terms: Tuple[TermDef, ...]

    A_moon: Fraction
    B_moon: Fraction
    lunar_terms: Tuple[TermDef, ...]

    iterations: int
    delta_t: DeltaTRationalDef
    sunrise: SunriseRationalDef
    location: LocationRational
    moon_tab_quarter: Tuple[int, ...]
    sun_tab_quarter: Tuple[int, ...]


@dataclass(frozen=True)
class RationalDayParams:
    """
    Wrapper parameters perfectly balanced between traditional and new modes.
    """
    mode: str = "trad"
    trad: Optional[RationalDayParamsTrad] = None
    new: Optional[RationalDayParamsNew] = None

    def __post_init__(self):
        if self.mode == "trad" and self.trad is None:
            raise ValueError("mode='trad' requires params.trad")
        if self.mode == "new" and self.new is None:
            raise ValueError("mode='new' requires params.new")


# ============================================================
# Traditional engine: t(d,n)=t0 + 1/60 moon_tab - 1/60 sun_tab
# ============================================================

class RationalDayEngineTrad:
    def __init__(self, p: RationalDayParamsTrad):
        self.p = p

        self.moon_table = OddPeriodicTable(quarter=p.moon_tab_quarter)
        self.sun_table = OddPeriodicTable(quarter=p.sun_tab_quarter)

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
        moon_tab = OddPeriodicTable(quarter=p.moon_tab_quarter)
        sun_tab = OddPeriodicTable(quarter=p.sun_tab_quarter)
        
        # 2. Build Solar Series
        active_solar = tuple(
            TabTermT(amp=t.amp, phase=t.phase, table_eval_turn=sun_tab.eval_normalized_turn)
            for t in p.solar_terms
        )
        self.solar_series = AffineTabSeriesT(A=p.A_sun, B=p.B_sun, terms=active_solar)

        # 3. Build Lunar Series
        active_lunar = tuple(
            TabTermT(amp=t.amp, phase=t.phase, table_eval_turn=moon_tab.eval_normalized_turn)
            for t in p.lunar_terms
        )
        self.lunar_series = AffineTabSeriesT(A=p.A_moon, B=p.B_moon, terms=active_lunar)

        # 4. Build Elongation Series: E(t) = L_moon(t) - L_sun(t)
        # Solar amplitudes are negated in the combined series
        active_elong_solar = tuple(
            TabTermT(amp=-t.amp, phase=t.phase, table_eval_turn=sun_tab.eval_normalized_turn)
            for t in p.solar_terms
        )
        self.elong_series = AffineTabSeriesT(
            A=p.A_moon - p.A_sun, 
            B=p.B_moon - p.B_sun, 
            terms=active_lunar + active_elong_solar
        )

        # 5. Bind Active Physics Models
        if isinstance(p.delta_t, ConstantDeltaTRationalDef):
            self.delta_t = ConstantDeltaTRational(p.delta_t.value)
        elif isinstance(p.delta_t, QuadraticDeltaTRationalDef):
            self.delta_t = QuadraticDeltaTRational(p.delta_t.a, p.delta_t.b, p.delta_t.c)
        else:
            raise TypeError("Unknown DeltaTRationalDef")

        if isinstance(p.sunrise, ConstantSunriseRationalDef):
            self.sunrise = ConstantSunriseRational(p.sunrise.day_fraction)
        elif isinstance(p.sunrise, SphericalSunriseRationalDef):
            self.sunrise = SphericalSunriseRational(p.sunrise.h0_turn, p.sunrise.eps_turn, table=moon_tab)
        else:
            raise TypeError("Unknown SunriseDef")

    def boundary_tt(self, x0: Fraction) -> Fraction:
        """Find TT boundary by targeting elongation = x0 / 30 turns."""
        target_elongation = x0 / Fraction(30, 1)
        return self.elong_series.picard_solve(target_elongation, iterations=self.p.iterations)

    def boundary_utc(self, x0: Fraction) -> Fraction:
        t_tt = self.boundary_tt(x0)
        dt_sec = self.delta_t.delta_t_seconds(t_tt)
        return t_tt - (dt_sec / Fraction(86400, 1))

    def local_true_date(self, x0: Fraction) -> Fraction:
        """
        Calculates the exact ending time as a local Julian Date.
        The integer part is the civil JDN. 
        The fractional part is the elapsed time since that exact civil day's local sunrise.
        """
        t_utc = self.boundary_utc(x0)
        
        # 1. Directly find the target civil day (J) by shifting the epoch.
        #    A standard day rolls over at 6:00 AM LMT.
        #    t_lmt = t_utc + lon_turn
        #    t_dawn_based = t_lmt + 0.5 (midnight to int) - 0.25 (dawn to int)
        t_dawn_based = t_utc + self.p.location.lon_turn + Fraction(1, 4)
        j_civil = t_dawn_based.numerator // t_dawn_based.denominator
        
        # 2. Find approximate dawn TT for this specific civil day (to evaluate true sun)
        #    Approx dawn UTC = (J - 0.5) + (0.25 - lon_turn) = J - 0.25 - lon_turn
        dawn_utc_approx = Fraction(j_civil, 1) - Fraction(1, 4) - self.p.location.lon_turn
        
        dt_sec = self.delta_t.delta_t_seconds(dawn_utc_approx)
        dawn_tt_approx = dawn_utc_approx + (dt_sec / Fraction(86400, 1))
        
        # 3. Evaluate exact True Sun and exact Spherical Sunrise
        lambda_sun = self.solar_series.eval(dawn_tt_approx)
        dawn_frac_exact = self.sunrise.sunrise_utc_fraction(j_civil, self.p.location, lambda_sun)
        
        # 4. Assemble the local true date
        #    Exact UTC time of dawn = (Midnight UTC) + dawn_frac_exact
        dawn_utc_exact = Fraction(j_civil, 1) - Fraction(1, 2) + dawn_frac_exact
        
        #    True date = Civil JDN + exact fraction of the day since that exact dawn
        return Fraction(j_civil, 1) + (t_utc - dawn_utc_exact)

    def end_jd(self, x0: Fraction) -> int:
        """The civil Julian Day Number is simply the integer part of the local true date."""
        td = self.local_true_date(x0)
        return td.numerator // td.denominator


# ============================================================
# Unified wrapper used by rational.py
# ============================================================

class RationalDayEngine:
    def __init__(self, params: RationalDayParams):
        self.mode = params.mode
        
        if self.mode == "trad":
            self._trad = RationalDayEngineTrad(params.trad)
            self._new = None
        elif self.mode == "new":
            self._new = RationalDayEngineNew(params.new)
            self._trad = None
        else:
            raise ValueError("mode must be 'trad' or 'new'")

    def true_date(self, d: int, n: int) -> Fraction:
        """Exact fractional Julian Day offset to local dawn."""
        if self.mode == "trad":
            return self._trad.true_date(d, n)
            
        x0 = Fraction(n * 30 + d, 1)
        return self._new.local_true_date(x0)

    def true_sun(self, d: int, n: int) -> Fraction:
        """True solar longitude (in turns) at the moment the tithi ends."""
        if self.mode == "trad":
            return self._trad.true_sun(d, n)
            
        x0 = Fraction(n * 30 + d, 1)
        t_tt = self._new.boundary_tt(x0)
        return frac_turn(self._new.solar_series.eval(t_tt))

    def mean_sun(self, d: int, n: int) -> Fraction:
        """Mean solar longitude (in turns) at the moment the tithi ends."""
        if self.mode == "trad":
            return self._trad.mean_sun(d, n)
            
        x0 = Fraction(n * 30 + d, 1)
        t_tt = self._new.boundary_tt(x0)
        return frac_turn(self._new.solar_series.base(t_tt))

    # --- new continuous API ---
    def true_sun_tt(self, jd_tt: Fraction) -> Fraction:
        """Continuous evaluation of true sun by Julian Date."""
        if self.mode != "new":
            raise TypeError("true_sun_tt(jd_tt) is only available in new mode.")
        return frac_turn(self._new.solar_series.eval(jd_tt))

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
