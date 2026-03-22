"""
caltib.engines.rational_month
-----------------------------
High-precision rational month engine.
Maps absolute lunations (l) to physical time (t2000) using continuous 
fractional affine series and the Picard fixed-point iteration.

Assigns human calendar labels (Year, Month, Leap) dynamically using 
true astronomical solar transits (sgang) rather than fixed arithmetic cycles.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple, List, Dict, Any, Optional

from caltib.engines.interfaces import MonthEngineProtocol, NumT
from caltib.engines.astro.tables import QuarterWaveTable
from caltib.engines.astro.affine_series import TermDef, TabTermT, AffineTabSeriesT

def frac_turn(x: Fraction) -> Fraction:
    """Wraps a fractional turn to [0, 1)."""
    return x % 1


@dataclass(frozen=True)
class RationalMonthParams:
    epoch_k: int  # Required by Protocol
    
    A_sun: Fraction
    B_sun: Fraction
    C_sun: Fraction
    solar_terms: Tuple[TermDef, ...]
    
    A_elong: Fraction
    B_elong: Fraction
    C_elong: Fraction
    lunar_terms: Tuple[TermDef, ...]
    
    iterations: int
    moon_tab_quarter: Tuple[int, ...]
    sun_tab_quarter: Tuple[int, ...]
    
    # Human Labeling Anchors
    Y0: int
    sgang1_deg: Fraction = Fraction(307, 1)  # Tropical longitude (degrees) defining Month 1

    # Containment Rule Naming Conventions
    leap_naming: str = "following"      # "previous" (Bhutan/India) or "following" (Phugpa/Tsurphu)
    skipped_naming: str = "second"      # "first" or "second"

    # Preconditioned B-elong-inverse
    invB_elong_prec: Optional[Fraction] = None

    @property
    def sgang_base(self) -> Fraction:
        """Converts degrees to a normalized continuous zodiac offset in turns [0, 1)."""
        return (self.sgang1_deg / Fraction(360, 1)) % 1


class RationalMonthEngine(MonthEngineProtocol):
    """
    Evaluates high-precision month kinematics via Picard iteration.
    Assigns leap months astronomically based on solar transits.
    Fully implements MonthEngineProtocol.
    """
    def __init__(self, p: RationalMonthParams):
        self.p = p
        
        # 1. Instantiate the tables
        moon_tab = QuarterWaveTable(quarter=p.moon_tab_quarter)
        sun_tab = QuarterWaveTable(quarter=p.sun_tab_quarter)
        
        # 2. Build Solar Series (Outputs True Sun)
        active_solar = tuple(
            TabTermT(amp=t.amp, phase=t.phase, table_eval_turn=sun_tab.eval_normalized_turn)
            for t in p.solar_terms
        )
        self.solar_series = AffineTabSeriesT(A=p.A_sun, B=p.B_sun, C=p.C_sun, terms=active_solar)

        # 3. Build Lunar Series (Outputs True Moon)
        active_lunar = tuple(
            TabTermT(amp=t.amp, phase=t.phase, table_eval_turn=moon_tab.eval_normalized_turn)
            for t in p.lunar_terms
        )

        # 4. Build Elongation Series: E(t) = D_mean(t) + C_moon(t) - C_sun(t)
        active_elong_solar = tuple(
            TabTermT(amp=-t.amp, phase=t.phase, table_eval_turn=sun_tab.eval_normalized_turn)
            for t in p.solar_terms
        )
        self.elong_series = AffineTabSeriesT(
            A=p.A_elong, 
            B=p.B_elong, 
            C=p.C_elong,
            terms=active_lunar + active_elong_solar
        )

    # ---------------------------------------------------------
    # Protocol Properties
    # ---------------------------------------------------------
    @property
    def epoch_k(self) -> int:
        return self.p.epoch_k

    @property
    def sgang_base(self) -> Fraction:
        """Converts degrees to a normalized continuous zodiac offset in turns [0, 1)."""
        return self.p.sgang_base

    # ---------------------------------------------------------
    # Continuous Physics (The Diagnostic Interface)
    # ---------------------------------------------------------
    def mean_date(self, l: NumT) -> Fraction:
        """
        Returns the mean physical time (Days since J2000.0 TT) for absolute lunation l.
        Inverts the linear mean elongation system: E_mean(t) = A + B*t = l
        """
        return (Fraction(l) - self.p.A_elong) / self.p.B_elong

    def true_date(self, l: NumT) -> Fraction:
        """
        Returns the true physical time (Days since J2000.0 TT) for absolute lunation l.
        Uses Picard iteration to solve: E_true(t) = l.
        """
        return self.elong_series.picard_solve(Fraction(l), iterations=self.p.iterations,invB_prec=self.p.invB_elong_prec)

    def get_l_from_t2000(self, t2000: NumT) -> int:
        """
        Inverse kinematic lookup. Returns the active absolute lunation index (l) 
        that covers the given physical time (Days since J2000.0 TT).
        """
        from fractions import Fraction
        target = Fraction(t2000)
        
        # 1. Provide an extremely close starting guess based on the elongation series.
        # In this engine, 1 turn of elongation = 1 absolute lunation.
        e_turns = self.elong_series.eval(target)
        l_est = e_turns.numerator // e_turns.denominator
        
        # 2. Walk the physical Picard-iterated boundaries to find the exact lunation enclosure.
        # Lunation l is active if the target time falls strictly after lunation l-1 ends, 
        # and on or before lunation l ends.
        while self.true_date(l_est - 1) > target:
            l_est -= 1
        while self.true_date(l_est) <= target:
            l_est += 1
            
        return l_est

    def mean_sun(self, l: NumT) -> Fraction:
        """Mean solar longitude (turns) at the physical moment of lunation l."""
        t_tt = self.true_date(l)
        return frac_turn(self.solar_series.base(t_tt))

    def true_sun(self, l: NumT) -> Fraction:
        """True solar longitude (turns) at the physical moment of lunation l."""
        t_tt = self.true_date(l)
        return frac_turn(self.solar_series.eval(t_tt))

    def first_lunation(self, year: int) -> int:
        for m in range(1, 13):
            lunations = self.get_lunations(year, m)
            if lunations:
                return lunations[0]
        raise ValueError(f"No lunations found for year {year}")

    # ---------------------------------------------------------
    # Astronomical Transit Labeling (The Civil Interface)
    # ---------------------------------------------------------
    def sgang_index(self, n: int) -> int:
        """
        Returns the absolute zodiac/sgang transit index for a given lunation n.
        (Unchanged: Represents the raw background transit count).
        """
        from fractions import Fraction
        t_tt = self.true_date(n)
        abs_sun = self.solar_series.eval(t_tt) - self.p.sgang_base
        z_frac = abs_sun * Fraction(12, 1)
        return z_frac.numerator // z_frac.denominator

    def _absolute_name(self, n: int) -> int:
        """
        Internal helper: Evaluates the containment rule interval for lunation n.
        Returns the absolute continuous civil name N_n based on chosen conventions.
        """
        Z_n = self.sgang_index(n)
        Z_prev = self.sgang_index(n - 1)
        delta_Z = Z_n - Z_prev  # How many transits were contained in this lunation?
        
        if delta_Z == 1:
            return Z_n  # Standard month: contains exactly 1 transit
            
        elif delta_Z == 0:
            # Leap Month: Contains NO transits. Borrow a name from adjacent posts.
            if self.p.leap_naming == "previous":
                return Z_n
            else:  # "following"
                return Z_n + 1
                
        elif delta_Z == 2:
            # Skipped Month: Contains TWO transits. We must drop one name.
            if self.p.skipped_naming == "first":
                return Z_n - 1  # Keeps the first transit name, skips the second
            else:  # "second"
                return Z_n      # Keeps the second transit name, skips the first
                
        else:
            # Fallback for impossible astronomical deltas
            return Z_n

    def label_from_lunation(self, n: int) -> Tuple[int, int, int]:
        """
        Assigns civil labels strictly based on the sgang1_deg absolute anchor.
        """
        N_n = self._absolute_name(n)
        
        # 1. Absolute Month: N_n = 0 is strictly the interval starting at sgang1_deg
        M = (N_n % 12) + 1
        
        # 2. Year Anchoring: We tie Y0 to the year-cycle of lunation n=0.
        # N_n // 12 automatically increments exactly when M rolls over from 12 to 1.
        N_0 = self._absolute_name(0)
        year_of_N0 = N_0 // 12
        
        Y = self.p.Y0 + (N_n // 12) - year_of_N0
        
        # 3. Leap State (Unchanged, purely physical)
        N_prev = self._absolute_name(n - 1)
        N_next = self._absolute_name(n + 1)
        
        if N_n == N_prev:
            leap_state = 2
        elif N_n == N_next:
            leap_state = 1
        else:
            leap_state = 0
            
        return Y, M, leap_state

    def get_month_info(self, n: int) -> Dict[str, Any]:
        """Diagnostic dictionary wrapper for the civil month labels."""
        Y, M, leap_state = self.label_from_lunation(n)
        linear = n - self.first_lunation(Y)
        return {
            "year": Y,
            "month": M,
            "leap_state": leap_state,
            "linear_month": linear,
            "sgang_index": self.sgang_index(n)
        }

    def get_lunations(self, year: int, month: int) -> List[int]:
        from fractions import Fraction
        
        N_0 = self._absolute_name(0)
        year_of_N0 = N_0 // 12
        
        # Target absolute N based purely on the requested year and month
        N_target = 12 * (year - self.p.Y0 + year_of_N0) + (month - 1)
        
        # 1. Guessing step
        S_target = Fraction(N_target, 12) + self.p.sgang_base
        t_guess = (S_target - self.p.A_sun) / self.p.B_sun
        n_guess_frac = self.p.A_elong + self.p.B_elong * t_guess
        n = n_guess_frac.numerator // n_guess_frac.denominator
        
        # 2. Seek backward
        while self._absolute_name(n) >= N_target:
            n -= 1
            
        # 3. Seek forward
        while self._absolute_name(n) < N_target:
            n += 1
            
        # 4. Collect
        results = []
        while self._absolute_name(n) == N_target:
            results.append(n)
            n += 1
            
        return results

    # ---------------------------------------------------------
    # Astronomy / Debug
    # ---------------------------------------------------------
    
    def mean_sun_tt(self, t2000: NumT) -> Fraction:
        return self.solar_series.base(t2000)

    def true_sun_tt(self, t2000: NumT) -> Fraction:
        return self.solar_series.eval(t2000)

    def mean_elong_tt(self, t2000: NumT) -> Fraction:
        return self.elong_series.base(t2000)

    def true_elong_tt(self, t2000: NumT) -> Fraction:
        return self.elong_series.eval(t2000)

    def mean_moon_tt(self, t2000: NumT) -> Fraction:
        return self.elong_series.base(t2000) + self.solar_series.base(t2000)

    def true_moon_tt(self, t2000: NumT) -> Fraction:
        return self.elong_series.eval(t2000) + self.solar_series.eval(t2000)