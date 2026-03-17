"""
caltib.engines.astro.deltat
---------------------------
Calculates ΔT (TT - UT) to bridge absolute physical time and civil earth rotation.

*** CRITICAL TIME COORDINATE WARNING ***
The core physics methods evaluate `t2000_tt`:
    t2000_tt = (Julian Date TT) - 2451545.0

If you have a standard Julian Date (e.g., 2451545.0), DO NOT pass it to 
`delta_t_seconds()`. You must use the explicit thin wrapper:
    `delta_t_seconds_jd(jd_tt)`
"""

from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Union
from abc import ABC, abstractmethod

JD_J2000_FRAC = Fraction(2451545, 1)

# ============================================================
# Definitions (For specs.py)
# ============================================================
@dataclass(frozen=True)
class ConstantDeltaTDef:
    value: Fraction

@dataclass(frozen=True)
class QuadraticDeltaTDef:
    a: Fraction
    b: Fraction
    c: Fraction
    y0: Fraction

DeltaTDef = Union[ConstantDeltaTDef, QuadraticDeltaTDef]

# ============================================================
# Abstract Base Class
# ============================================================
class DeltaTModel(ABC):
    """Abstract base class for exact fractional ΔT models."""
    
    @abstractmethod
    def delta_t_seconds(self, t2000_tt: Fraction) -> Fraction: 
        """
        Calculates exact fractional ΔT. 
        Input `t2000_tt` MUST be Days since J2000.0 TT.
        """
        pass
        
    @abstractmethod
    def info(self) -> Dict[str, object]:
        pass

    def delta_t_seconds_jd(self, jd_tt: Fraction) -> Fraction:
        """
        Convenience wrapper. 
        Translates a standard fractional Julian Date to t2000_tt.
        """
        return self.delta_t_seconds(jd_tt - JD_J2000_FRAC)


# ============================================================
# Implementations
# ============================================================
@dataclass(frozen=True)
class ConstantDeltaT(DeltaTModel):
    value: Fraction
    
    def delta_t_seconds(self, t2000_tt: Fraction) -> Fraction:
        return self.value
        
    def info(self) -> Dict[str, object]:
        return {"type": "constant", "value": str(self.value)}


@dataclass(frozen=True)
class QuadraticDeltaT(DeltaTModel):
    """
    ΔT(year) = a + b*u + c*u^2, where u=(year-y0)/100, solved entirely in Fractions.
    """
    a: Fraction
    b: Fraction
    c: Fraction
    y0: Fraction = Fraction(1820, 1)
    
    def delta_t_seconds(self, t2000_tt: Fraction) -> Fraction:
        # yd = t2000_tt / 365.25 + 2000
        yd = t2000_tt / Fraction(1461, 4) + Fraction(2000, 1)
        u = (yd - self.y0) / Fraction(100, 1)
        # Horner's method applied to exact fractions
        return self.a + u * (self.b + u * self.c)

    def info(self) -> Dict[str, object]:
        return {"type": "quadratic", "a": str(self.a), "b": str(self.b), "c": str(self.c), "y0": str(self.y0)}


# ============================================================
# Float Delta T Models (For FloatDayEngine)
# ============================================================

@dataclass(frozen=True)
class FloatDeltaTDef:
    """Float representation of quadratic Delta T: a + b*u + c*u^2"""
    a: float
    b: float
    c: float
    y0: float

@dataclass(frozen=True)
class FloatDeltaT:
    a: float
    b: float
    c: float
    y0: float = 1820.0

    def delta_t_seconds_year(self, year: float) -> float:
        u = (year - self.y0) / 100.0
        # Horner's method for ax^2 + bx + c
        return self.a + u * (self.b + u * self.c)

    def delta_t_seconds(self, t2000_tt: float) -> float:
        # yd = t2000_tt / 365.25 + 2000
        return self.delta_t_seconds_year(t2000_tt / 365.25 + 2000.0)
