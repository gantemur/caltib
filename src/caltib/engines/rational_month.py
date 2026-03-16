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
from typing import Tuple, List, Dict, Any

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
    solar_terms: Tuple[TermDef, ...]
    
    A_elong: Fraction
    B_elong: Fraction
    lunar_terms: Tuple[TermDef, ...]
    
    iterations: int
    moon_tab_quarter: Tuple[int, ...]
    sun_tab_quarter: Tuple[int, ...]
    
    # Human Labeling Anchors
    Y0: int
    M0: int
    sgang1_deg: Fraction = Fraction(0, 1)  # Input in exact degrees (e.g., 0 for Vernal Equinox)

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
        self.solar_series = AffineTabSeriesT(A=p.A_sun, B=p.B_sun, terms=active_solar)

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
        return (self.p.sgang1_deg / Fraction(360, 1)) % 1

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
        return self.elong_series.picard_solve(Fraction(l), iterations=self.p.iterations)

    def get_l_from_t2000(self, t2000: NumT) -> Fraction:
        """Inverse kinematic lookup: Returns true elongation (in turns) at physical time t."""
        return self.elong_series.eval(Fraction(t2000))

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

    def get_month_info(self, n: int) -> Dict[str, Any]:
        Z_n = self.sgang_index(n)
        Z_prev = self.sgang_index(n - 1)
        Z_0 = self.sgang_index(0)
        M_linear = self.p.M0 + (Z_n - Z_0)
        M = ((M_linear - 1) % 12) + 1
        Y = self.p.Y0 + (M_linear - M) // 12
        if Z_n == Z_prev:
            leap_state = 2
        else:
            Z_next = self.sgang_index(n + 1)
            if Z_n == Z_next:
                leap_state = 1
            else:
                leap_state = 0
        linear = n - self.first_lunation(Y)
        return {
            "year": Y,
            "month": M,
            "leap_state": leap_state,
            "linear_month": linear,
            "sgang_index": Z_n
        }

# ---------------------------------------------------------
    # Astronomical Transit Labeling (The Civil Interface)
    # ---------------------------------------------------------
    def sgang_index(self, n: int) -> int:
        """
        Returns the absolute zodiac/sgang transit index for a given lunation n.
        The sun advances through one sgang every 1/12 of a turn.
        Evaluates using pure rational integer arithmetic to prevent transit snapping.
        """
        from fractions import Fraction
        t_tt = self.true_date(n)
        
        # Use absolute unrolled solar longitude to prevent wrap-around bugs
        abs_sun = self.solar_series.eval(t_tt) - self.p.sgang_base
        
        # Multiply by 12 natively and extract the integer floor
        z_frac = abs_sun * Fraction(12, 1)
        return z_frac.numerator // z_frac.denominator

    def label_from_lunation(self, n: int) -> Tuple[int, int, int]:
        """
        Protocol method: Assigns civil Year, Month, and Leap State 
        dynamically based on true astronomical solar transits.
        """
        Z_n = self.sgang_index(n)
        Z_prev = self.sgang_index(n - 1)
        Z_0 = self.sgang_index(0)
        
        # The human calendar month advances every time the sgang index advances
        M_linear = self.p.M0 + (Z_n - Z_0)
        
        # Adjust to 1-12 bounds
        M = ((M_linear - 1) % 12) + 1
        Y = self.p.Y0 + (M_linear - M) // 12
        
        # Astronomical leap logic: If no transit occurred, it is a leap month!
        if Z_n == Z_prev:
            leap_state = 2  # Second occurrence of this month label
        else:
            Z_next = self.sgang_index(n + 1)
            if Z_n == Z_next:
                leap_state = 1  # First occurrence (regular month, but leap follows)
            else:
                leap_state = 0  # Regular month (no leap follows)
                
        return Y, M, leap_state

    def get_month_info(self, n: int) -> Dict[str, Any]:
        """Diagnostic dictionary wrapper for the civil month labels."""
        Y, M, leap_state = self.label_from_lunation(n)
        return {
            "year": Y,
            "month": M,
            "leap_state": leap_state,
            "sgang_index": self.sgang_index(n)
        }

    def get_lunations(self, year: int, month: int) -> List[int]:
        """
        Returns the absolute lunation indices for a given Year and Month number.
        Uses a local search against the sgang transit boundaries, with an O(1) 
        pure rational affine inverse for the initial guess.
        """
        from fractions import Fraction
        
        M_linear_target = 12 * (year - self.p.Y0) + month
        Z_0 = self.sgang_index(0)
        Z_target = (M_linear_target - self.p.M0) + Z_0
        
        # 1. Provide an extremely close starting guess based on the exact linear rates
        # Target continuous solar longitude (in turns) at the start of the transit
        S_target = Fraction(Z_target, 12) + self.p.sgang_base
        
        # Approximate physical time (t2000) when the sun reaches this longitude
        t_guess = (S_target - self.p.A_sun) / self.p.B_sun
        
        # Approximate continuous lunation index at this time
        n_guess_frac = self.p.A_elong + self.p.B_elong * t_guess
        
        # Pure rational integer floor
        n = n_guess_frac.numerator // n_guess_frac.denominator
        
        # 2. Seek backward to find the absolute FIRST n of the target month.
        # We must overshoot (>=) to guarantee we drop below any leap month clusters!
        while self.sgang_index(n) >= Z_target:
            n -= 1
            
        # 3. Step forward to the exact lower boundary
        while self.sgang_index(n) < Z_target:
            n += 1
            
        # 4. Collect all n's that share this transit target
        results = []
        while self.sgang_index(n) == Z_target:
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