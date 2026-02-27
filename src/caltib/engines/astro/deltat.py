from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Protocol, Union

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
    """ΔT = TT - UT, in seconds, float-based by default."""
    def delta_t_seconds(self, jd_tt: float) -> float: ...
    def info(self) -> Dict[str, object]: ...


@dataclass(frozen=True)
class ConstantDeltaT(DeltaTModel):
    value: float
    def delta_t_seconds(self, jd_tt: float) -> float:
        return float(self.value)
    def info(self) -> Dict[str, object]:
        return {"type": "constant", "value": self.value}


@dataclass(frozen=True)
class QuadraticDeltaT(DeltaTModel):
    """ΔT(year) = a + b*u + c*u^2, u=(year-y0)/100."""
    a: float
    b: float
    c: float
    y0: float = 1820.0
    
    def delta_t_seconds(self, jd_tt: float) -> float:
        # Convert JD_TT to decimal year (J2000 epoch = 2451545.0)
        year_decimal = (jd_tt - 2451545.0) / 365.25 + 2000.0
        u = (year_decimal - self.y0) / 100.0
        
        # Horner's method for strict reproducibility and minimal error
        return self.a + u * (self.b + u * self.c)
        
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
    def delta_t_seconds(self, jd_tt: Fraction) -> Fraction: ...
    def info(self) -> Dict[str, object]: ...


@dataclass(frozen=True)
class ConstantDeltaTRational(DeltaTRationalModel):
    value: Fraction
    def delta_t_seconds(self, jd_tt: Fraction) -> Fraction:
        return self.value
    def info(self) -> Dict[str, object]:
        return {"type": "constant-rational", "value": str(self.value)}


@dataclass(frozen=True)
class QuadraticDeltaTRational(DeltaTRationalModel):
    """
    ΔT(year) = a + b*u + c*u^2, u=(year-y0)/100, all Fractions.
    """
    a: Fraction
    b: Fraction
    c: Fraction
    y0: Fraction = Fraction(1820, 1)
    
    def delta_t_seconds(self, jd_tt: Fraction) -> Fraction:
        # yd = (jd_tt - J2000) / 365.25 + 2000
        yd = (jd_tt - Fraction(2451545, 1)) / Fraction(1461, 4) + Fraction(2000, 1)
        u = (yd - self.y0) / Fraction(100, 1)
        return self.a + u * (self.b + u * self.c)

    def info(self) -> Dict[str, object]:
        return {"type": "quadratic-rational", "a": str(self.a), "b": str(self.b), "c": str(self.c), "y0": str(self.y0)}