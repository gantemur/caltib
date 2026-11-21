"""
caltib.engines.fp_day
---------------------
High-performance floating-point day engine.
Strictly deterministic, FMA-free execution relying purely on J2000.0 hex-floats.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Tuple

from caltib.core.types import LocationSpec
from caltib.engines.interfaces import DayEngineProtocol, NumT
from caltib.engines.astro.deltat import FloatDeltaT, FloatDeltaTDef
from caltib.engines.astro.sunrise import SunriseState, FloatSunrise, FloatSunriseDef
from caltib.engines.astro.float_series import FloatFourierSeries, FloatTermDef
from caltib.engines.astro.fp_math import float_sqrt

JD_J2000_FLOAT = 2451545.0
PicardSeed = Literal["linear", "quadratic_mean"]

@dataclass(frozen=True)
class FloatDayParams:
    epoch_k: int
    location: LocationSpec
    
    A_sun: float; B_sun: float; C_sun: float
    solar_static: Tuple[FloatTermDef, ...]
    solar_dynamic: Tuple[FloatTermDef, ...]
    
    A_elong: float; B_elong: float; C_elong: float
    elong_static: Tuple[FloatTermDef, ...]
    elong_dynamic: Tuple[FloatTermDef, ...]
    
    iterations: int
    delta_t: FloatDeltaTDef       
    sunrise: FloatSunriseDef      
    sine_poly_coeffs: Tuple[float, ...]
    picard_seed: PicardSeed = "linear"

    def __post_init__(self) -> None:
        if self.picard_seed not in ("linear", "quadratic_mean"):
            raise ValueError(f"Unknown Picard seed: {self.picard_seed!r}")

    def with_location(self, new_loc: LocationSpec) -> FloatDayParams:
        """Creates a new params instance calibrated for a different location."""
        import dataclasses
        return dataclasses.replace(self, location=new_loc)


class FloatDayEngine(DayEngineProtocol):
    def __init__(self, p: FloatDayParams):
        self.p = p
        
        # 1. Instantiate the active polynomial evaluator
        from caltib.engines.astro.fp_math import QuarterWavePolynomial
        sine_poly = QuarterWavePolynomial(coeffs=p.sine_poly_coeffs)
        
        # 2. Build the execution objects from the pure data (UPDATED)
        self.solar_series = FloatFourierSeries(
            A=p.A_sun, 
            B=p.B_sun, 
            C=p.C_sun, 
            static_terms=p.solar_static,
            dynamic_terms=p.solar_dynamic,
            poly=sine_poly
        )
        self.elong_series = FloatFourierSeries(
            A=p.A_elong, 
            B=p.B_elong, 
            C=p.C_elong, 
            static_terms=p.elong_static,
            dynamic_terms=p.elong_dynamic,
            poly=sine_poly
        )
        
        # 3. Build the Sunrise and DeltaT models from their pure Defs
        from caltib.engines.astro.sunrise import FloatSunrise
        from caltib.engines.astro.fp_math import ArctanPolynomial
        self.sunrise = FloatSunrise(
            h0_turn=p.sunrise.h0_turn, 
            eps_turn=p.sunrise.eps_turn, 
            sine_poly=QuarterWavePolynomial(coeffs=p.sunrise.sine_poly_coeffs),
            atan_poly=ArctanPolynomial(coeffs=p.sunrise.atan_poly_coeffs),
            day_fraction=p.sunrise.day_fraction
        )
        
        from caltib.engines.astro.deltat import FloatDeltaT
        self.delta_t = FloatDeltaT(a=p.delta_t.a, b=p.delta_t.b, c=p.delta_t.c, y0=p.delta_t.y0)

    @property
    def epoch_k(self) -> int:
        return self.p.epoch_k

    @property
    def epoch_offset_x(self) -> int: 
        return self.p.epoch_k * 30

    @property
    def location(self) -> LocationSpec: 
        return self.p.location

    def mean_date(self, x: NumT) -> float:
        """Invert the base series on the branch through t=0 with slope B.

        Raise ValueError outside the finite, strictly monotone branch.
        """
        target_turns = (float(x) + self.epoch_offset_x) / 30.0
        A, B, C = self.elong_series.A, self.elong_series.B, self.elong_series.C
        q = target_turns - A
        if B == 0.0 or not all(map(math.isfinite, (B, C, q))):
            raise ValueError("Mean elongation inverse needs finite inputs and a nonzero linear rate")
        if q == 0.0:
            return 0.0
        if C == 0.0:
            t = q / B
        else:
            discriminant = B * B + 4.0 * (C * q)
            if discriminant <= 0.0 or not math.isfinite(discriminant):
                raise ValueError("Mean elongation target is outside the supported monotone branch")

            # Binary scaling and one fixed Newton step give a full-precision
            # root here without changing the shared FMA-free square root.
            mantissa, exponent = math.frexp(discriminant)
            if exponent % 2:
                mantissa *= 2.0
                exponent -= 1
            root = float_sqrt(mantissa)
            root = math.ldexp(0.5 * (root + mantissa / root), exponent // 2)

            # Rationalize the branch continuous at C=0. Halve each term
            # instead of doubling q or subtracting nearly equal numbers.
            t = q / (0.5 * B + 0.5 * math.copysign(root, B))
        if not math.isfinite(t):
            raise ValueError("Mean elongation inverse is outside the finite time range")
        return t

    def true_date(self, x: NumT) -> float:
        """Apply the profile's fixed Picard steps from its selected seed."""
        target_turns = (float(x) + self.epoch_offset_x) / 30.0
        t_init = self.mean_date(x) if self.p.picard_seed == "quadratic_mean" else None
        return self.elong_series.picard_solve(target_turns, iterations=self.p.iterations, t_init=t_init)

    def get_x_from_t2000(self, t2000: float) -> int:
        """Inverse lookup mapping physical time back to the active tithi index."""
        target = float(t2000)
        e_turns = self.elong_series.eval(target)
        
        # math.floor ensures negative numbers correctly round down to the previous lunation boundary
        x_est = math.floor(e_turns * 30.0) - self.epoch_offset_x
        
        while self.true_date(x_est - 1) > target: 
            x_est -= 1
        while self.true_date(x_est) <= target: 
            x_est += 1
            
        return x_est

    def mean_sun(self, x: NumT) -> float:
        t_tt = self.true_date(x)
        return self.solar_series.base(t_tt) % 1.0

    def true_sun(self, x: NumT) -> float:
        t_tt = self.true_date(x)
        return self.solar_series.eval(t_tt) % 1.0

    def local_civil_date(self, x: NumT) -> float:
        t_utc = self.boundary_utc(x)
        abs_t_utc = t_utc + JD_J2000_FLOAT
        
        lmt_baseline = self.sunrise.init_lmt_fraction()
        # Safe, strict 1-way cast from LocationSpec Fraction to float
        lon_turn = float(self.p.location.lon_turn)
        
        t_dawn_based = abs_t_utc + lon_turn + lmt_baseline
        j_civil = math.floor(t_dawn_based)
        
        dawn_utc_approx = float(j_civil) - lmt_baseline - lon_turn
        
        # delta_t_seconds takes days since J2000.0 (it converts to a year itself).
        dt_sec = self.delta_t.delta_t_seconds(dawn_utc_approx - JD_J2000_FLOAT)
        dawn_tt_approx = dawn_utc_approx + (dt_sec / 86400.0)
        
        t_dawn_tt = dawn_tt_approx - JD_J2000_FLOAT
        
        lambda_sun = self.solar_series.eval(t_dawn_tt)
        mean_sun = self.solar_series.base(t_dawn_tt)
        
        # Pure float API call!
        dawn_frac_exact, polar = self.sunrise.sunrise_utc_fraction(
            self.p.location, 
            lambda_sun, 
            mean_sun
        )
        
        dawn_utc_exact = float(j_civil) - 0.5 + dawn_frac_exact
        # sunrise_utc_fraction is reduced mod 1, so when sunrise falls near 0h UTC
        # (e.g. Lhasa or Ulaanbaatar) it can land on the wrong UTC day. Take the
        # sunrise nearest the approximate dawn.
        dawn_utc_exact -= math.floor(dawn_utc_exact - dawn_utc_approx + 0.5)
        abs_jdn = float(j_civil) + (abs_t_utc - dawn_utc_exact)
        
        return abs_jdn - JD_J2000_FLOAT

    def civil_jdn(self, x: NumT) -> int:
        abs_date = self.local_civil_date(x) + JD_J2000_FLOAT
        return math.floor(abs_date)

    def boundary_utc(self, x: NumT) -> float:
        t_tt = self.true_date(x)
        dt_sec = self.delta_t.delta_t_seconds(t_tt)   # days since J2000.0 TT
        return t_tt - (dt_sec / 86400.0)

    # ---------------------------------------------------------
    # Astronomy / Debug Functions
    # ---------------------------------------------------------
    def mean_sun_tt(self, t2000: NumT) -> float:
        return self.solar_series.base(float(t2000)) % 1.0
        
    def true_sun_tt(self, t2000: NumT) -> float:
        return self.solar_series.eval(float(t2000)) % 1.0
        
    def mean_elong_tt(self, t2000: NumT) -> float:
        return self.elong_series.base(float(t2000)) % 1.0
        
    def true_elong_tt(self, t2000: NumT) -> float:
        return self.elong_series.eval(float(t2000)) % 1.0

    def mean_moon_tt(self, t2000: NumT) -> float:
        # Implicitly recovered via Sun + Elongation
        return self.elong_series.base(float(t2000)) + self.solar_series.base(float(t2000))

    def true_moon_tt(self, t2000: NumT) -> float:
        # Implicitly recovered via Sun + Elongation
        return self.elong_series.eval(float(t2000)) + self.solar_series.eval(float(t2000))
        
    def eval_sunrise_lmt(self, t2000_tt: NumT) -> Tuple[float, SunriseState]:
        t_tt = float(t2000_tt)
        lambda_sun = self.solar_series.eval(t_tt)
        mean_sun = self.solar_series.base(t_tt)
        
        return self.sunrise.sunrise_lmt_fraction(
            float(self.p.location.lat_turn), 
            lambda_sun, 
            mean_sun
        )
