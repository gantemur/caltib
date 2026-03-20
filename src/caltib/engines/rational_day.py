"""
caltib.engines.rational_day
---------------------------
High-precision rational day engine.
Maps absolute tithis (x) to physical time (t2000) using continuous 
fractional affine series and the Picard fixed-point iteration.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple, Optional

from caltib.core.types import LocationSpec
from caltib.engines.interfaces import DayEngineProtocol, NumT
from caltib.engines.astro.tables import ArctanTable, QuarterWaveTable
from caltib.engines.astro.affine_series import TermDef, TabTermT, AffineTabSeriesT
from caltib.engines.astro.deltat import (
    DeltaTDef, 
    ConstantDeltaTDef, 
    QuadraticDeltaTDef, 
    ConstantDeltaT, 
    QuadraticDeltaT
)
# Updated Sunrise imports (No "Rational" adjectives, float models eliminated)
from caltib.engines.astro.sunrise import (
    SunriseState,
    SunriseDef, 
    ConstantSunriseDef, 
    SphericalSunriseDef, 
    TrueSunriseDef,
    ConstantSunrise, 
    SphericalSunrise,
    TrueSunrise
)

JD_J2000 = Fraction(2451545, 1)


def frac_turn(x: Fraction) -> Fraction:
    """Wraps a fractional turn to [0, 1)."""
    q = x.numerator // x.denominator
    return x - Fraction(q, 1)


@dataclass(frozen=True)
class RationalDayParams:
    epoch_k: int  # Required by Protocol
    location: LocationSpec
    
    A_sun: Fraction
    B_sun: Fraction
    C_sun: Fraction
    solar_terms: Tuple[TermDef, ...]
    
    A_elong: Fraction
    B_elong: Fraction
    C_elong: Fraction
    lunar_terms: Tuple[TermDef, ...]
    
    iterations: int
    delta_t: DeltaTDef
    sunrise: SunriseDef
    moon_tab_quarter: Tuple[int, ...]
    sun_tab_quarter: Tuple[int, ...]

    invB_elong_prec: Optional[Fraction] = None

    def with_location(self, new_loc: LocationSpec) -> RationalDayParams:
        """Rebuilds the parameters for a new location."""
        import dataclasses
        return dataclasses.replace(self, location=new_loc)

class RationalDayEngine(DayEngineProtocol):
    """
    Evaluates high-precision calendar kinematics via Picard iteration.
    Fully implements DayEngineProtocol.
    """
    def __init__(self, p: RationalDayParams):
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

        # 3. Build Lunar Anomaly Series
        active_lunar = tuple(
            TabTermT(amp=t.amp, phase=t.phase, table_eval_turn=moon_tab.eval_normalized_turn)
            for t in p.lunar_terms
        )

        # 4. Build Elongation Series: E(t) = D_mean(t) + A_moon(t) - A_sun(t)
        # Solar perturbation amplitudes are negated because E = Moon - Sun
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

        # 5. Bind Active Physics Models
        if isinstance(p.delta_t, ConstantDeltaTDef):
            self.delta_t = ConstantDeltaT(p.delta_t.value)
        elif isinstance(p.delta_t, QuadraticDeltaTDef):
            self.delta_t = QuadraticDeltaT(p.delta_t.a, p.delta_t.b, p.delta_t.c,p.delta_t.y0)
        else:
            raise TypeError("Unknown DeltaTDef")

        if isinstance(p.sunrise, ConstantSunriseDef):
            self.sunrise = ConstantSunrise(p.sunrise.day_fraction)
        elif isinstance(p.sunrise, SphericalSunriseDef):
            self.sunrise = SphericalSunrise(
                h0_turn=p.sunrise.h0_turn, 
                eps_turn=p.sunrise.eps_turn, 
                table=QuarterWaveTable(quarter=p.sunrise.sine_tab_quarter),
                day_fraction=p.sunrise.day_fraction,
            )
        elif isinstance(p.sunrise, TrueSunriseDef):
            self.sunrise = TrueSunrise(
                h0_turn=p.sunrise.h0_turn, 
                eps_turn=p.sunrise.eps_turn, 
                sine_table=QuarterWaveTable(quarter=p.sunrise.sine_tab_quarter),
                atan_table=ArctanTable(values=p.sunrise.atan_tab_values),
                day_fraction=p.sunrise.day_fraction,
            )
        else:
            raise TypeError("Unknown SunriseDef")

    # ---------------------------------------------------------
    # Protocol Properties
    # ---------------------------------------------------------
    @property
    def epoch_k(self) -> int:
        return self.p.epoch_k

    @property
    def location(self) -> LocationSpec:
        """Satisfies the new location-aware protocol."""
        return self.p.location

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
        return self.elong_series.picard_solve(target_turns, iterations=self.p.iterations, invB_prec=self.p.invB_elong_prec)

    def get_x_from_t2000(self, t2000: float) -> int:
        """
        Inverse kinematic lookup. Returns the active absolute tithi index (x) 
        that covers the given physical time (Days since J2000.0).
        """
        from fractions import Fraction
        target = Fraction(t2000)
        
        # 1. Provide an extremely close starting guess based on the elongation series.
        e_turns = self.elong_series.eval(target)
        x_est_frac = e_turns * Fraction(30, 1)
        x_est = x_est_frac.numerator // x_est_frac.denominator
        
        # 2. Walk the physical boundaries to find the exact tithi enclosure.
        # Tithi x is active if the target time falls strictly after tithi x-1 ends, 
        # and on or before tithi x ends.
        while self.true_date(x_est - 1) > target:
            x_est -= 1
        while self.true_date(x_est) <= target:
            x_est += 1
            
        return x_est

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
        
        # Dynamically ask the sunrise model for its LMT baseline (e.g., 6:00 AM)
        lmt_baseline = self.sunrise.init_lmt_fraction()
        
        t_dawn_based = abs_t_utc + self.p.location.lon_turn + lmt_baseline
        j_civil = t_dawn_based.numerator // t_dawn_based.denominator
        
        # Compute exact UTC approximation using the dynamic baseline
        dawn_utc_approx = Fraction(j_civil, 1) - lmt_baseline - self.p.location.lon_turn
        
        y_dawn = Fraction(2000, 1) + (dawn_utc_approx - JD_J2000) / Fraction(1461, 4)
        dt_sec = self.delta_t.delta_t_seconds(y_dawn)
        dawn_tt_approx = dawn_utc_approx + (dt_sec / Fraction(86400, 1))
        
        # Convert Dawn TT back to J2000 days for the solar series evaluation
        t_dawn_tt = dawn_tt_approx - JD_J2000
        
        # 1. Evaluate both True Sun and Mean Sun for the Sunrise Model
        lambda_sun = self.solar_series.eval(t_dawn_tt)
        mean_sun = self.solar_series.base(t_dawn_tt)
        
        # 2. Call the purified Sunrise Model and unpack the flag
        dawn_frac_exact, polar = self.sunrise.sunrise_utc_fraction(
            self.p.location, 
            lambda_sun, 
            mean_sun
        )
        
        dawn_utc_exact = Fraction(j_civil, 1) - Fraction(1, 2) + dawn_frac_exact
        # Calculate the absolute JDN coordinate seamlessly using fallback if triggered
        abs_jdn = Fraction(j_civil, 1) + (abs_t_utc - dawn_utc_exact)
        
        # Return t2000 to match the protocol!
        return abs_jdn - JD_J2000

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
    # Civil Boundary & Time Extensions (Used by Orchestrator)
    # ---------------------------------------------------------
    def boundary_utc(self, x: NumT) -> Fraction:
        """Returns Days since J2000.0 UTC for absolute tithi x."""
        t_tt = self.true_date(x)
        dt_sec = self.delta_t.delta_t_seconds(t_tt)        
        return t_tt - (dt_sec / Fraction(86400, 1))

    # ---------------------------------------------------------
    # Astronomy / Debug
    # ---------------------------------------------------------
    
    def mean_sun_tt(self, t2000: NumT) -> Fraction:
        return self.solar_series.base(t2000)

    def true_sun_tt(self, t2000: NumT) -> Fraction:
        return self.solar_series.eval(t2000)

    def mean_moon_tt(self, t2000: NumT) -> Fraction:
        return self.elong_series.base(t2000) + self.solar_series.base(t2000)

    def true_moon_tt(self, t2000: NumT) -> Fraction:
        return self.elong_series.eval(t2000) + self.solar_series.eval(t2000)

    def mean_elong_tt(self, t2000: NumT) -> Fraction:
        return self.elong_series.base(t2000)

    def true_elong_tt(self, t2000: NumT) -> Fraction:
        return self.elong_series.eval(t2000)

    def eval_sunrise_lmt(self, t2000_tt: NumT) -> Tuple[Fraction, SunriseState]:
        """
        Debug/Validation Wrapper: Evaluates the Local Mean Time (LMT) fraction 
        of dawn for the solar coordinates at the given continuous physical time.
        (e.g., 0.25 = exactly 6:00 AM LMT).
        Returns a tuple: (LMT Fraction, sunrise_state).
        """
        from fractions import Fraction
        t_tt = Fraction(t2000_tt)
        
        # 1. Evaluate the sun's position at the requested physical time
        lambda_sun = self.solar_series.eval(t_tt)
        mean_sun = self.solar_series.base(t_tt)
        
        # 2. Pass it through the sunrise geometry engine to get Local Time
        return self.sunrise.sunrise_lmt_fraction(
            self.p.location, 
            lambda_sun, 
            mean_sun
        )