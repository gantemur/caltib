"""
caltib.engines.astro.sunrise
----------------------------
Calculates the fractional time of sunrise (UTC) for a given location.

This module is a pure geometric transformation. It has no concept of absolute 
time or dates. It relies on the calling engine to handle "backreaction".
"""

from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Union, Tuple
from abc import ABC, abstractmethod

from caltib.core.types import LocationSpec, SunriseState
from .tables import QuarterWaveTable, ArctanTable


# ============================================================
# Sunrise Definitions
# ============================================================
@dataclass(frozen=True)
class ConstantSunriseDef:
    day_fraction: Fraction = Fraction(1,4)  # Rough average LMT (e.g., 6:00 AM)

@dataclass(frozen=True)
class SphericalSunriseDef:
    h0_turn: Fraction      # e.g., -0.833 deg / 360
    eps_turn: Fraction     # e.g., 23.44 deg / 360
    sine_tab_quarter: Tuple[int, ...]
    day_fraction: Fraction = Fraction(39, 360)  # Baseline LMT guess (e.g., 5:56 AM)

@dataclass(frozen=True)
class TrueSunriseDef:
    """Configuration for a fully physical sunrise (Spherical + EoT)."""
    h0_turn: Fraction
    eps_turn: Fraction
    sine_tab_quarter: Tuple[int, ...]
    atan_tab_values: Tuple[int, ...]
    day_fraction: Fraction = Fraction(39, 360)  # Baseline LMT guess (e.g., 5:56 AM)

SunriseDef = Union[ConstantSunriseDef, SphericalSunriseDef, TrueSunriseDef]

# ============================================================
# Sunrise Abstract Base Class
# ============================================================
class SunriseModel(ABC):
    
    @abstractmethod
    def init_lmt_fraction(self) -> Fraction:
        pass
        
    @abstractmethod
    def sunrise_lmt_fraction(self, loc: LocationSpec, true_sun_turn: Fraction, mean_sun_turn: Fraction) -> Tuple[Fraction, SunriseState]:
        pass

    def sunrise_utc_fraction(self, loc: LocationSpec, true_sun_turn: Fraction, mean_sun_turn: Fraction) -> Tuple[Fraction, SunriseState]:
        lmt_frac, state = self.sunrise_lmt_fraction(loc, true_sun_turn, mean_sun_turn)
        utc_frac = lmt_frac - loc.lon_turn
        
        q = utc_frac.numerator // utc_frac.denominator
        return utc_frac - Fraction(q, 1), state

# ============================================================
# Implementations
# ============================================================
@dataclass(frozen=True)
class ConstantSunrise(SunriseModel):
    day_fraction: Fraction = Fraction(1, 4)
    
    def init_lmt_fraction(self) -> Fraction:
        return self.day_fraction
        
    def sunrise_lmt_fraction(self, loc: LocationSpec, true_sun_turn: Fraction, mean_sun_turn: Fraction) -> Tuple[Fraction, SunriseState]:
        return self.day_fraction, SunriseState.NORMAL


@dataclass(frozen=True)
class SphericalSunrise(SunriseModel):
    h0_turn: Fraction
    eps_turn: Fraction
    table: QuarterWaveTable
    day_fraction: Fraction = Fraction(1, 4)
    
    def init_lmt_fraction(self) -> Fraction:
        return self.day_fraction
        
    def sunrise_lmt_fraction(self, loc: LocationSpec, true_sun_turn: Fraction, mean_sun_turn: Fraction) -> Tuple[Fraction, bool]:
        if loc.lat_turn is None:
            raise ValueError("Spherical sunrise requires a defined lat_turn.")
            
        sin_eps = self.table.eval_normalized_turn(self.eps_turn)
        sin_lambda = self.table.eval_normalized_turn(true_sun_turn)
        sin_delta = sin_eps * sin_lambda
        
        delta_turn = self.table.asin_normalized_turn(sin_delta)
        cos_delta = self.table.eval_normalized_turn(delta_turn + Fraction(1, 4))
        
        sin_phi = self.table.eval_normalized_turn(loc.lat_turn)
        cos_phi = self.table.eval_normalized_turn(loc.lat_turn + Fraction(1, 4))
        
        sin_h0 = self.table.eval_normalized_turn(self.h0_turn)
        
        numerator = sin_h0 - (sin_phi * sin_delta)
        denominator = cos_phi * cos_delta
        
        # --- THE NEW 3-STATE LOGIC ---
        if numerator >= denominator:
            # cos(H0) >= 1 : Sun is always below the horizon
            return self.day_fraction, SunriseState.POLAR_NIGHT
        elif numerator <= -denominator:
            # cos(H0) <= -1 : Sun is always above the horizon
            return self.day_fraction, SunriseState.POLAR_DAY
            
        cos_H0 = numerator / denominator
        H0_turn = self.table.acos_normalized_turn(cos_H0)
        
        return Fraction(1, 2) - H0_turn, SunriseState.NORMAL

@dataclass(frozen=True)
class TrueSunrise(SunriseModel):
    """
    L4/L5: Fully physical sunrise approximation.
    Computes Local Apparent Time via spherical geometry, then perfectly 
    corrects to Local Mean Time using the Equation of Time (EoT).
    """
    h0_turn: Fraction
    eps_turn: Fraction
    sine_table: QuarterWaveTable
    atan_table: ArctanTable
    day_fraction: Fraction = Fraction(1, 4)
    
    def init_lmt_fraction(self) -> Fraction:
        return self.day_fraction
        
    def sunrise_lmt_fraction(self, loc: LocationSpec, true_sun_turn: Fraction, mean_sun_turn: Fraction) -> Tuple[Fraction, SunriseState]:
        if loc.lat_turn is None:
            raise ValueError("True sunrise requires a LocationSpec with a defined lat_turn.")
            
        # 1. Evaluate standard spherical components
        sin_eps = self.sine_table.eval_normalized_turn(self.eps_turn)
        cos_eps = self.sine_table.eval_normalized_turn(self.eps_turn + Fraction(1, 4))
        
        sin_lambda = self.sine_table.eval_normalized_turn(true_sun_turn)
        cos_lambda = self.sine_table.eval_normalized_turn(true_sun_turn + Fraction(1, 4))
        
        sin_delta = sin_eps * sin_lambda
        delta_turn = self.sine_table.asin_normalized_turn(sin_delta)
        cos_delta = self.sine_table.eval_normalized_turn(delta_turn + Fraction(1, 4))
        
        sin_phi = self.sine_table.eval_normalized_turn(loc.lat_turn)
        cos_phi = self.sine_table.eval_normalized_turn(loc.lat_turn + Fraction(1, 4))
        sin_h0 = self.sine_table.eval_normalized_turn(self.h0_turn)
        
        # 2. Spherical Law of Cosines for Hour Angle (H0)
        numerator = sin_h0 - (sin_phi * sin_delta)
        denominator = cos_phi * cos_delta
        
        if numerator >= denominator:
            return self.day_fraction, SunriseState.POLAR_NIGHT
        elif numerator <= -denominator:
            return self.day_fraction, SunriseState.POLAR_DAY
            
        cos_H0 = numerator / denominator
        H0_turn = self.sine_table.acos_normalized_turn(cos_H0)
        
        # Local Apparent Time (LAT) of Sunrise
        t_lat = Fraction(1, 2) - H0_turn
        
        # 3. Equation of Time Correction (C.13 & C.14)
        # alpha_sun = atan2(cos(eps) * sin(lambda), cos(lambda))
        y_alpha = cos_eps * sin_lambda
        x_alpha = cos_lambda
        alpha_turn = self.atan_table.atan2_turn(y_alpha, x_alpha)
        
        # LMT = LAT + (alpha_true - L_mean)
        eot_shift = alpha_turn - mean_sun_turn
        t_lmt = t_lat + eot_shift
        
        # Ensure strict wrapping to [0, 1)
        q = t_lmt.numerator // t_lmt.denominator
        return t_lmt - Fraction(q, 1), SunriseState.NORMAL