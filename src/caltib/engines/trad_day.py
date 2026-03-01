"""
caltib.engines.trad_day
-----------------------
Traditional discrete-table kinematic engine.
Maps absolute tithis (x) to true physical time (t2000) using historical 
affine equations and piecewise linear periodic tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Optional, Tuple

from caltib.engines.interfaces import DayEngineProtocol, NumT
from caltib.engines.astro.sin_tables import OddPeriodicTable
from caltib.engines.astro.affine_series import PhaseDN, TabTermDN, AffineTabSeriesDN

JD_J2000 = Fraction(2451545, 1)


def frac_turn(val: Fraction) -> Fraction:
    """Wraps a fractional turn to [0, 1)."""
    q = val.numerator // val.denominator
    return val - Fraction(q, 1)


@dataclass(frozen=True)
class TraditionalDayParams:
    epoch_k: int
    
    # Base affine mean-date coefficients (absolute Julian Days)
    m0: Fraction
    m1: Fraction
    m2: Fraction

    # Mean sun phases (turns)
    s0: Fraction
    s1: Fraction
    s2: Fraction

    # Moon anomaly phases (turns)
    a0: Fraction
    a1: Fraction
    a2: Fraction

    # Tables given as quarter-wave samples in table-units (integers)
    moon_tab_quarter: Tuple[int, ...]
    sun_tab_quarter: Tuple[int, ...]

    # Independent solar anomaly constants (turns). 
    # Defaults strictly to s - 1/4, s1, and s2 if not provided.
    r0: Optional[Fraction] = None
    r1: Optional[Fraction] = None
    r2: Optional[Fraction] = None

    def __post_init__(self):
        # Workaround to dynamically set default fields in a frozen dataclass
        if self.r0 is None:
            object.__setattr__(self, 'r0', self.s0 - Fraction(1, 4))
        if self.r1 is None:
            object.__setattr__(self, 'r1', self.s1)
        if self.r2 is None:
            object.__setattr__(self, 'r2', self.s2)


class TraditionalDayEngine(DayEngineProtocol):
    """
    Evaluates historical calendar kinematics.
    Fully implements DayEngineProtocol.
    """
    def __init__(self, p: TraditionalDayParams):
        self.p = p

        self.moon_table = OddPeriodicTable(quarter=p.moon_tab_quarter)
        self.sun_table = OddPeriodicTable(quarter=p.sun_tab_quarter)

        # Build phases (turns) using the decoupled anomalies
        self.phase_moon = PhaseDN(p.a0, p.a1, p.a2)
        self.phase_sun_anomaly = PhaseDN(p.r0, p.r1, p.r2)

        # Build true date series: t(d,n) = mean_date + moon_eq - sun_eq
        self.series = AffineTabSeriesDN(
            base_c0=p.m0,
            base_cn=p.m1,
            base_cd=p.m2,
            terms=(
                TabTermDN(
                    amp=Fraction(1, 60), 
                    phase=self.phase_moon, 
                    table_eval_turn=self.moon_table.eval_turn
                ),
                TabTermDN(
                    amp=Fraction(-1, 60), 
                    phase=self.phase_sun_anomaly, 
                    table_eval_turn=self.sun_table.eval_turn
                ),
            ),
        )

        # Build solar longitude series (turns)
        self.sun_series = AffineTabSeriesDN(
            base_c0=p.s0,
            base_cn=p.s1,
            base_cd=p.s2,
            terms=(
                TabTermDN(
                    amp=Fraction(1, 720),  # 1/720 turn per table unit (60 * 12)
                    phase=self.phase_sun_anomaly,
                    table_eval_turn=self.sun_table.eval_turn,
                ),
            ),
        )

    # ---------------------------------------------------------
    # Internal Coordinate Mapper
    # ---------------------------------------------------------
    def _to_nd(self, x: NumT) -> tuple[Fraction, Fraction]:
        """
        Splits the continuous 1D kinematic coordinate x into (n, d)
        so it can be ingested by the legacy 2D AffineTabSeriesDN solver.
        """
        x_frac = Fraction(x)
        n = int(x_frac // 30)
        d = x_frac - 30 * n
        return Fraction(n), d

    # ---------------------------------------------------------
    # Protocol Properties
    # ---------------------------------------------------------
    @property
    def epoch_k(self) -> int:
        return self.p.epoch_k

    # ---------------------------------------------------------
    # Protocol Methods (Strictly t2000 output)
    # ---------------------------------------------------------
    def mean_date(self, x: NumT) -> Fraction:
        n, d = self._to_nd(x)
        jd_abs = self.p.m0 + self.p.m1 * n + self.p.m2 * d
        return jd_abs - JD_J2000

    def true_date(self, x: NumT) -> Fraction:
        n, d = self._to_nd(x)
        jd_abs = self.series.eval(d, n)
        return jd_abs - JD_J2000

    def local_civil_date(self, x: NumT) -> Fraction:
        """For traditional engines, the affine true_date is already civil-aligned."""
        return self.true_date(x)

    def mean_sun(self, x: NumT) -> Fraction:
        n, d = self._to_nd(x)
        s = self.p.s0 + self.p.s1 * n + self.p.s2 * d
        return frac_turn(s)

    def true_sun(self, x: NumT) -> Fraction:
        n, d = self._to_nd(x)
        return frac_turn(self.sun_series.eval(d, n))

    def get_x_from_t2000(self, t2000: float) -> int:
        """
        Inverse kinematic lookup. Returns the active absolute tithi index (x) 
        that covers the given physical time (Days since J2000.0).
        """
        target = Fraction(t2000)
        
        # 1. Provide an extremely close starting guess based on the mean linear rate
        # m2 is days per tithi.
        m0_t2000 = self.p.m0 - JD_J2000
        x_est = int((target - m0_t2000) / self.p.m2)
        
        # 2. Walk the physical boundaries to find the exact tithi enclosure
        while self.true_date(x_est - 1) > target:
            x_est -= 1
        while self.true_date(x_est) <= target:
            x_est += 1
            
        return x_est