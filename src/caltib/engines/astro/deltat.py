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
from typing import Dict, Protocol, Union

JD_J2000_FLOAT = 2451545.0
JD_J2000_FRAC = Fraction(2451545, 1)

# ============================================================
# Float models (default): flexible, piecewise, tables, etc.
# ============================================================

# Pure Data Definitions (For specs.py)
@dataclass(frozen=True)
class ConstantDeltaTFloatDef:
    value: float

@dataclass(frozen=True)
class QuadraticDeltaTFloatDef:
    a: float
    b: float
    c: float
    y0: float

DeltaTFloatDef = Union[ConstantDeltaTFloatDef, QuadraticDeltaTFloatDef]

class DeltaTModel(Protocol):
    """ΔT = TT - UT, in seconds."""
    
    def delta_t_seconds(self, t2000_tt: float) -> float: 
        """
        Calculates ΔT. 
        Input `t2000_tt` MUST be Days since J2000.0 TT.
        """
        ...
        
    def delta_t_seconds_jd(self, jd_tt: float) -> float:
        """
        Convenience wrapper. 
        Input `jd_tt` is a standard Julian Date TT.
        """
        ...
        
    def info(self) -> Dict[str, object]: ...


@dataclass(frozen=True)
class ConstantDeltaT(DeltaTModel):
    value: float
    
    def delta_t_seconds(self, t2000_tt: float) -> float:
        return float(self.value)

    def delta_t_seconds_jd(self, jd_tt: float) -> float:
        return self.delta_t_seconds(jd_tt - JD_J2000_FLOAT)
        
    def info(self) -> Dict[str, object]:
        return {"type": "constant", "value": self.value}


@dataclass(frozen=True)
class QuadraticDeltaT(DeltaTModel):
    """
    ΔT(year) = a + b*u + c*u^2, where u=(year-y0)/100.
    """
    a: float
    b: float
    c: float
    y0: float = 1820.0
    
    def delta_t_seconds(self, t2000_tt: float) -> float:
        # Convert Days since J2000.0 into a decimal Gregorian year
        year_decimal = (t2000_tt / 365.25) + 2000.0
        u = (year_decimal - self.y0) / 100.0
        
        # Horner's method for strict reproducibility and minimal floating-point error
        return self.a + u * (self.b + u * self.c)

    def delta_t_seconds_jd(self, jd_tt: float) -> float:
        """Convenience wrapper for standard Julian Dates."""
        return self.delta_t_seconds(jd_tt - JD_J2000_FLOAT)
        
    def info(self) -> Dict[str, object]:
        return {"type": "quadratic", "a": self.a, "b": self.b, "c": self.c, "y0": self.y0}


# ============================================================
# Rational models (L1-L3): Only constant or quadratic
# ============================================================

# Pure Data Definitions (For specs.py)
@dataclass(frozen=True)
class ConstantDeltaTRationalDef:
    value: Fraction

@dataclass(frozen=True)
class QuadraticDeltaTRationalDef:
    a: Fraction
    b: Fraction
    c: Fraction
    y0: Fraction

DeltaTRationalDef = Union[ConstantDeltaTRationalDef, QuadraticDeltaTRationalDef]


class DeltaTRationalModel(Protocol):
    """Rational implementation of ΔT for exact L1-L3 kinematics."""
    
    def delta_t_seconds(self, t2000_tt: Fraction) -> Fraction: 
        """
        Calculates exact fractional ΔT. 
        Input `t2000_tt` MUST be Days since J2000.0 TT.
        """
        ...

    def delta_t_seconds_jd(self, jd_tt: Fraction) -> Fraction:
        """
        Convenience wrapper. 
        Input `jd_tt` is a standard Julian Date TT.
        """
        ...
        
    def info(self) -> Dict[str, object]: ...


@dataclass(frozen=True)
class ConstantDeltaTRational(DeltaTRationalModel):
    value: Fraction
    
    def delta_t_seconds(self, t2000_tt: Fraction) -> Fraction:
        return self.value

    def delta_t_seconds_jd(self, jd_tt: Fraction) -> Fraction:
        return self.delta_t_seconds(jd_tt - JD_J2000_FRAC)
        
    def info(self) -> Dict[str, object]:
        return {"type": "constant-rational", "value": str(self.value)}


@dataclass(frozen=True)
class QuadraticDeltaTRational(DeltaTRationalModel):
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

    def delta_t_seconds_jd(self, jd_tt: Fraction) -> Fraction:
        """Convenience wrapper for standard fractional Julian Dates."""
        return self.delta_t_seconds(jd_tt - JD_J2000_FRAC)

    def info(self) -> Dict[str, object]:
        return {"type": "quadratic-rational", "a": str(self.a), "b": str(self.b), "c": str(self.c), "y0": str(self.y0)}