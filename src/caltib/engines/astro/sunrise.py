"""
caltib.engines.astro.sunrise
----------------------------
Calculates the fractional time of sunrise (UTC) for a given location.

This module is a pure geometric transformation. It has no concept of absolute 
time or dates. It relies on the calling engine to handle "backreaction" 
(iterating to find the exact solar coordinates at the precise moment of dawn).
"""

from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Protocol, Union

from .sin_tables import OddPeriodicTable


# ============================================================
# Float models (Future L4/L5)
# ============================================================
@dataclass(frozen=True)
class LocationFloat:
    lat_turn: float
    lon_turn: float
    elev_m: float = 0.0

@dataclass(frozen=True)
class SunriseFloatDef:
    """A single, flexible definition for float sunrise models."""
    h0_turn: float
    eps_turn: float

class SunriseFloatModel(Protocol):
    """Protocol for L4/L5 continuous float sunrise models."""
    def sunrise_utc_fraction(self, loc: LocationFloat, true_sun_turn: float, mean_sun_turn: float) -> float: ...

@dataclass(frozen=True)
class GenericSunriseFloat(SunriseFloatModel):
    p: SunriseFloatDef
    
    def sunrise_utc_fraction(self, loc: LocationFloat, true_sun_turn: float, mean_sun_turn: float) -> float:
        raise NotImplementedError("Float sunrise to be implemented in Phase 3.")


# ============================================================
# Rational models (L1-L3)
# ============================================================
@dataclass(frozen=True)
class LocationRational:
    lat_turn: Fraction    # latitude as turns (lat_deg/360)
    lon_turn: Fraction    # longitude as turns (positive East)
    elev_m: Fraction = Fraction(0, 1)

@dataclass(frozen=True)
class ConstantSunriseRationalDef:
    day_fraction: Fraction

@dataclass(frozen=True)
class SphericalSunriseRationalDef:
    h0_turn: Fraction      # e.g., -0.833 deg / 360
    eps_turn: Fraction     # e.g., 23.44 deg / 360

SunriseRationalDef = Union[ConstantSunriseRationalDef, SphericalSunriseRationalDef]

class SunriseRationalModel(Protocol):
    """Protocol for L1-L3 exact fractional sunrise models."""
    def sunrise_utc_fraction(self, loc: LocationRational, true_sun_turn: Fraction, mean_sun_turn: Fraction) -> Fraction: ...

@dataclass(frozen=True)
class ConstantSunriseRational(SunriseRationalModel):
    """L1/L2: Constant sunrise approximation (ignores seasonal variance)."""
    day_fraction: Fraction = Fraction(1, 4)
    
    def sunrise_utc_fraction(self, loc: LocationRational, true_sun_turn: Fraction, mean_sun_turn: Fraction) -> Fraction:
        return self.day_fraction - loc.lon_turn


@dataclass(frozen=True)
class SphericalSunriseRational(SunriseRationalModel):
    """
    L3: Spherical earth sunrise approximation. 
    Uses table-based inversions to remain strictly rational.
    Ignores Equation of Time (EOT); assumes Local Mean Time ≈ Local Apparent Time.
    """
    h0_turn: Fraction
    eps_turn: Fraction
    table: OddPeriodicTable
    
    def sunrise_utc_fraction(self, loc: LocationRational, true_sun_turn: Fraction, mean_sun_turn: Fraction) -> Fraction:
        # 1. Compute solar declination δ
        # sin δ = sin ε * sin λ_sun
        sin_eps = self.table.eval_normalized_turn(self.eps_turn)
        sin_lambda = self.table.eval_normalized_turn(true_sun_turn)
        sin_delta = sin_eps * sin_lambda
        
        # We need cos δ. To stay rational, we find δ via arcsin table lookup, 
        # then evaluate cosine (sine shifted by 1/4 turn).
        delta_turn = self.table.asin_normalized_turn(sin_delta)
        cos_delta = self.table.eval_normalized_turn(delta_turn + Fraction(1, 4))
        
        # 2. Compute latitude functions
        sin_phi = self.table.eval_normalized_turn(loc.lat_turn)
        cos_phi = self.table.eval_normalized_turn(loc.lat_turn + Fraction(1, 4))
        
        # 3. Compute altitude function
        sin_h0 = self.table.eval_normalized_turn(self.h0_turn)
        
        # 4. Spherical Law of Cosines for Hour Angle H_0
        # cos H_0 = (sin h_0 - sin φ sin δ) / (cos φ cos δ)
        numerator = sin_h0 - (sin_phi * sin_delta)
        denominator = cos_phi * cos_delta
        
        # Safety for polar day/night (clamp to [-1, 1])
        if numerator >= denominator:
            cos_H0 = Fraction(1, 1)   # Sun never rises
        elif numerator <= -denominator:
            cos_H0 = Fraction(-1, 1)  # Sun never sets
        else:
            cos_H0 = numerator / denominator
            
        # Hour angle in turns [0, 1/2]
        H0_turn = self.table.acos_normalized_turn(cos_H0)
        
        # 5. Local Apparent Time of sunrise
        # t_rise,app = 12h - H_0 (where 12h is 1/2 turn)
        t_rise_app = Fraction(1, 2) - H0_turn
        
        # 6. Convert to UTC (Assuming Mean Sun approximation per Remark C.5)
        # Note: Future models will apply EoT using mean_sun_turn here.
        t_rise_utc = t_rise_app - loc.lon_turn
        
        # Wrap to ensure a positive fraction of the day [0, 1)
        q = t_rise_utc.numerator // t_rise_utc.denominator
        return t_rise_utc - Fraction(q, 1)
