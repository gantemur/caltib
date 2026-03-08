"""
caltib.engines.arithmetic_day
-----------------------------
Discrete arithmetic engine for mapping absolute tithis (x) to civil days.
Uses the mean-elongation U/V slope model and modular chad indexing.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from caltib.core.types import LocationSpec
from caltib.engines.interfaces import DayEngineProtocol, NumT


def frac_turn(x: Fraction) -> Fraction:
    """Wraps a fractional turn to [0, 1)."""
    q = x.numerator // x.denominator
    return x - Fraction(q, 1)

@dataclass(frozen=True)
class ArithmeticDayParams:
    epoch_k: int
    location: LocationSpec  # The new standardized anchor
    U: int              # Numerator of elong rate (e.g. 11312)
    V: int              # Denominator of elong rate (e.g. 11135)
    delta_star: int     # Floor of the epoch phase shift (-V*Delta_0 - 1)
    m0_abs: Fraction    # Universal physical time (J2000.0 TT)
    m0_loc: Fraction    # Longitude-shifted time (Used for hot-loop arithmetic)
    s0: Fraction        # True sun (turns) at x=0
    s1: Fraction        # Solar advance per lunation (turns)

    def __post_init__(self):
        if self.U <= self.V:
            raise ValueError("Mean advance U/V must be > 1")

    @property
    def m2(self) -> Fraction:
        """Civil days per tithi (V / U)."""
        return Fraction(self.V, self.U)

    @property
    def s2(self) -> Fraction:
        """Solar advance per tithi (turns)."""
        return self.s1 / Fraction(30, 1)

    def with_location(self, new_loc: 'LocationSpec') -> 'ArithmeticDayParams':
        """Rebuilds the parameters for a new location, shifting the local time."""
        import dataclasses

        # Calculate the exact longitudinal shift between the old and new location
        lon_diff = new_loc.lon_turn - self.location.lon_turn
        new_m0_loc = self.m0_loc + lon_diff
        
        # Recompute the delta_star phase shift for the new local dawn
        jdn_floor = new_m0_loc.numerator // new_m0_loc.denominator
        f_loc = new_m0_loc - Fraction(jdn_floor, 1)
        
        # Calculate the exact phase shift fraction and extract the integer floor
        shift_frac = f_loc * self.U
        new_delta_star = (shift_frac.numerator // shift_frac.denominator) - 1
        
        return dataclasses.replace(
            self, 
            location=new_loc, 
            m0_loc=new_m0_loc, 
            delta_star=new_delta_star
        )

class ArithmeticDayEngine(DayEngineProtocol):
    """
    Evaluates day kinematics using pure discrete fractional arithmetic.
    Fully implements DayEngineProtocol.
    """
    def __init__(self, p: ArithmeticDayParams):
        self.p = p
        # The hot loop uses the localized physical time!
        self._m0_loc_t2000 = p.m0_loc - Fraction(2451545, 1)
        
        # Civil epoch dawn is just the floor of the local epoch time
        jdn_floor = p.m0_loc.numerator // p.m0_loc.denominator
        self._epoch_t2000 = Fraction(jdn_floor - 2451545, 1)

    # ---------------------------------------------------------
    # Protocol Properties
    # ---------------------------------------------------------
    @property
    def epoch_k(self) -> int:
        return self.p.epoch_k

    @property
    def location(self) -> 'LocationSpec':
        """Satisfies the new location-aware protocol."""
        return self.p.location

    # ---------------------------------------------------------
    # Protocol Methods
    # ---------------------------------------------------------
    def mean_date(self, x: NumT) -> Fraction:
        return self._m0_loc_t2000 + Fraction(x) * self.p.m2

    def true_date(self, x: NumT) -> Fraction:
        """In a purely arithmetic mean model, true syzygy IS mean syzygy."""
        return self.mean_date(x)

    def get_x_from_t2000(self, t2000: NumT) -> int:
        """Inverse lookup of active tithi using pure rational arithmetic."""
        # Calculate the exact fractional tithi index
        x_frac = (Fraction(t2000) - self._m0_loc_t2000) / self.p.m2
        
        # Pure rational floor via unbounded integer division
        return x_frac.numerator // x_frac.denominator

    def mean_sun(self, x: NumT) -> Fraction:
        return frac_turn(self.p.s0 + Fraction(x) * self.p.s2)

    def true_sun(self, x: NumT) -> Fraction:
        return self.mean_sun(x)

    def local_civil_date(self, x: NumT) -> Fraction:
        """
        Maps tithi x to the civil day J(x) using the continuous form of the inverse map.
        Taking floor(local_civil_date) will yield exact civil day bounds.
        """
        # Continuous equivalent of J(x) = floor((V*x + V + delta_star) / U)
        continuous_j = (Fraction(self.p.V) * Fraction(x) + self.p.V + self.p.delta_star) / self.p.U
        return self._epoch_t2000 + continuous_j

    def civil_jdn(self, x: NumT) -> int:
        """
        Returns the absolute discrete JDN using pure rational integer arithmetic.
        Completely bypasses FPU and math.floor.
        """
        from fractions import Fraction
        
        # 1. Get the continuous fraction (t2000) and add the exact J2000 offset
        abs_date = self.local_civil_date(x) + Fraction(2451545, 1)
        
        # 2. Pure rational floor via unbounded integer division
        return abs_date.numerator // abs_date.denominator

    # ---------------------------------------------------------
    # Diagnostic / Appendix E Helpers
    # ---------------------------------------------------------
    def chad_index(self, x: int) -> int:
        """
        Computes the day intercalation (chad) index for absolute tithi x.
        chi_day(K) = (VK + delta*) mod U
        """
        return (self.p.V * x + self.p.delta_star) % self.p.U

    def is_skipped(self, x: int) -> bool:
        """
        A tithi label is skipped iff its chad index is < (U - V).
        """
        kappa = self.p.U - self.p.V
        return self.chad_index(x) < kappa
