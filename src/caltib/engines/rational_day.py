"""
caltib.engines.rational_day
---------------------------
High-precision rational day engine.
Maps absolute tithis (x) to physical time (t2000) using continuous 
fractional affine series and the Picard fixed-point iteration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple

from caltib.engines.interfaces import DayEngineProtocol, NumT
from caltib.engines.astro.sin_tables import OddPeriodicTable
from caltib.engines.astro.affine_series import TermDef, TabTermT, AffineTabSeriesT
from caltib.engines.astro.deltat import (
    DeltaTRationalDef, 
    ConstantDeltaTRationalDef, 
    QuadraticDeltaTRationalDef, 
    ConstantDeltaTRational, 
    QuadraticDeltaTRational
)
from caltib.engines.astro.sunrise import (
    LocationRational, 
    SunriseRationalDef, 
    ConstantSunriseRationalDef, 
    SphericalSunriseRationalDef, 
    ConstantSunriseRational, 
    SphericalSunriseRational
)

JD_J2000 = Fraction(2451545, 1)


def frac_turn(x: Fraction) -> Fraction:
    """Wraps a fractional turn to [0, 1)."""
    q = x.numerator // x.denominator
    return x - Fraction(q, 1)


@dataclass(frozen=True)
class RationalDayParams:
    epoch_k: int  # Required by Protocol
    
    A_sun: Fraction
    B_sun: Fraction
    solar_terms: Tuple[TermDef, ...]
    
    A_elong: Fraction
    B_elong: Fraction
    lunar_terms: Tuple[TermDef, ...]
    
    iterations: int
    delta_t: DeltaTRationalDef
    sunrise: SunriseRationalDef
    location: LocationRational
    moon_tab_quarter: Tuple[int, ...]
    sun_tab_quarter: Tuple[int, ...]


class RationalDayEngine(DayEngineProtocol):
    """
    Evaluates high-precision calendar kinematics via Picard iteration.
    Fully implements DayEngineProtocol.
    """
    def __init__(self, p: RationalDayParams):
        self.p = p
        
        # 1. Instantiate the tables
        moon_tab = OddPeriodicTable(quarter=p.moon_tab_quarter)
        sun_tab = OddPeriodicTable(quarter=p.sun_tab_quarter)
        
        # 2. Build Solar Series (Outputs True Sun)
        active_solar = tuple(
            TabTermT(amp=t.amp, phase=t.phase, table_eval_turn=sun_tab.eval_normalized_turn)
            for t in p.solar_terms
        )
        self.solar_series = AffineTabSeriesT(A=p.A_sun, B=p.B_sun, terms=active_solar)

        # 3. Build Lunar Series (Outputs True Moon: L_moon = Elong + L_sun)
        active_lunar = tuple(
            TabTermT(amp=t.amp, phase=t.phase, table_eval_turn=moon_tab.eval_normalized_turn)
            for t in p.lunar_terms
        )
        self.lunar_series = AffineTabSeriesT(
            A=p.A_elong + p.A_sun, 
            B=p.B_elong + p.B_sun, 
            terms=active_lunar
        )

        # 4. Build Elongation Series: E(t) = D_mean(t) + C_moon(t) - C_sun(t)
        # Solar perturbation amplitudes are negated because E = Moon - Sun
        active_elong_solar = tuple(
            TabTermT(amp=-t.amp, phase=t.phase, table_eval_turn=sun_tab.eval_normalized_turn)
            for t in p.solar_terms
        )
        self.elong_series = AffineTabSeriesT(
            A=p.A_elong, 
            B=p.B_elong, 
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

    # ---------------------------------------------------------
    # Protocol Properties
    # ---------------------------------------------------------
    @property
    def epoch_k(self) -> int:
        return self.p.epoch_k

    # ---------------------------------------------------------
    # Protocol Methods
    # ---------------------------------------------------------

    def mean_date(self, x: NumT) -> Fraction:
        """
        Returns the mean physical time (Days since J2000.0 TT) for absolute tithi x.
        Inverts the linear mean elongation system: E_mean(t) = A + B*t = x/30
        """
        target_turns = Fraction(x) / Fraction(30, 1)
        return (target_turns - self.p.A_elong) / self.p.B_elong

    def true_date(self, x: NumT) -> Fraction:
        """
        Returns the true physical time (Days since J2000.0 TT) for absolute tithi x.
        Uses Picard iteration to solve: E_true(t) = x/30.
        """
        target_turns = Fraction(x) / Fraction(30, 1)
        return self.elong_series.picard_solve(target_turns, iterations=self.p.iterations)

    def get_x_from_t2000(self, t2000: float) -> int:
        """
        Inverse kinematic lookup. Returns the active absolute tithi index (x).
        """
        # Series evaluates strictly in turns, so we scale by 30 at the end
        e_turns = self.elong_series.eval(Fraction(t2000))
        return math.floor(float(e_turns * 30))

    def mean_sun(self, x: NumT) -> Fraction:
        """Mean solar longitude (turns) at the physical moment of tithi x."""
        t_tt = self.true_date(x)
        return frac_turn(self.solar_series.base(t_tt))

    def true_sun(self, x: NumT) -> Fraction:
        """True solar longitude (turns) at the physical moment of tithi x."""
        t_tt = self.true_date(x)
        return frac_turn(self.solar_series.eval(t_tt))

    def local_civil_date(self, x: NumT) -> Fraction:
        t_utc = self.boundary_utc(x)
        abs_t_utc = t_utc + JD_J2000
        
        t_dawn_based = abs_t_utc + self.p.location.lon_turn + Fraction(1, 4)
        j_civil = t_dawn_based.numerator // t_dawn_based.denominator
        
        dawn_utc_approx = Fraction(j_civil, 1) - Fraction(1, 4) - self.p.location.lon_turn
        
        y_dawn = Fraction(2000, 1) + (dawn_utc_approx - JD_J2000) / Fraction(1461, 4)
        dt_sec = self.delta_t.delta_t_seconds(y_dawn)
        dawn_tt_approx = dawn_utc_approx + (dt_sec / Fraction(86400, 1))
        
        # Convert Dawn TT back to J2000 days for the solar series evaluation
        t_dawn_tt = dawn_tt_approx - JD_J2000
        
        # 1. Evaluate both True Sun and Mean Sun for the Sunrise Engine
        lambda_sun = self.solar_series.eval(t_dawn_tt)
        mean_sun = self.solar_series.base(t_dawn_tt)
        
        # 2. Call the purified Sunrise Engine
        dawn_frac_exact = self.sunrise.sunrise_utc_fraction(
            self.p.location, 
            lambda_sun, 
            mean_sun
        )
        
        dawn_utc_exact = Fraction(j_civil, 1) - Fraction(1, 2) + dawn_frac_exact
        
        return Fraction(j_civil, 1) + (abs_t_utc - dawn_utc_exact)


    # ---------------------------------------------------------
    # Civil Boundary & Time Extensions (Used by Orchestrator)
    # ---------------------------------------------------------
    def boundary_utc(self, x: NumT) -> Fraction:
        """Returns Days since J2000.0 UTC for absolute tithi x."""
        t_tt = self.true_date(x)
        dt_sec = self.delta_t.delta_t_seconds(t_tt)        
        return t_tt - (dt_sec / Fraction(86400, 1))
