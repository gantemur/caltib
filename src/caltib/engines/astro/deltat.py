from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Protocol, Tuple, Sequence, Mapping, Optional


# ============================================================
# Float models (default): flexible, piecewise, tables, etc.
# ============================================================

class DeltaTModel(Protocol):
    """ΔT = TT - UT, in seconds, float-based by default."""
    def delta_t_seconds(self, year_decimal: float) -> float: ...
    def info(self) -> Dict[str, object]: ...


@dataclass(frozen=True)
class ConstantDeltaT(DeltaTModel):
    value: float
    def delta_t_seconds(self, year_decimal: float) -> float:
        return float(self.value)
    def info(self) -> Dict[str, object]:
        return {"type": "constant", "value": self.value}


@dataclass(frozen=True)
class QuadraticDeltaT(DeltaTModel):
    """ΔT(year) = a + b*u + c*u^2, u=(year-y0)/100."""
    a: float
    b: float
    c: float
    y0: float = 2000.0
    def delta_t_seconds(self, year_decimal: float) -> float:
        u = (year_decimal - self.y0) / 100.0
        return self.a + self.b*u + self.c*u*u
    def info(self) -> Dict[str, object]:
        return {"type": "quadratic", "a": self.a, "b": self.b, "c": self.c, "y0": self.y0}


@dataclass(frozen=True)
class PolyDeltaT(DeltaTModel):
    """
    ΔT(year) = Σ_{k=0}^{n} c[k] * u^k, where u=(year-y0)/scale.
    Default scale=100 gives 'per century' style.
    """
    coeff: Tuple[float, ...]   # c0, c1, ..., cn
    y0: float = 2000.0
    scale: float = 100.0
    def delta_t_seconds(self, year_decimal: float) -> float:
        u = (year_decimal - self.y0) / self.scale
        # Horner
        acc = 0.0
        for c in reversed(self.coeff):
            acc = acc * u + c
        return acc
    def info(self) -> Dict[str, object]:
        return {"type": "poly", "coeff": self.coeff, "y0": self.y0, "scale": self.scale}


@dataclass(frozen=True)
class PiecewiseQuadraticDeltaT(DeltaTModel):
    """
    segments: (year_min, year_max, QuadraticDeltaT)
    year_min <= year < year_max
    """
    segments: Tuple[Tuple[float, float, QuadraticDeltaT], ...]

    def delta_t_seconds(self, year_decimal: float) -> float:
        for y0, y1, m in self.segments:
            if y0 <= year_decimal < y1:
                return m.delta_t_seconds(year_decimal)
        # clamp
        if year_decimal < self.segments[0][0]:
            return self.segments[0][2].delta_t_seconds(self.segments[0][0])
        return self.segments[-1][2].delta_t_seconds(self.segments[-1][1] - 1e-9)

    def info(self) -> Dict[str, object]:
        return {"type": "piecewise_quadratic", "segments": [(a, b, m.info()) for a, b, m in self.segments]}


@dataclass(frozen=True)
class PiecewisePolyDeltaT(DeltaTModel):
    """
    segments: (year_min, year_max, PolyDeltaT)
    """
    segments: Tuple[Tuple[float, float, PolyDeltaT], ...]

    def delta_t_seconds(self, year_decimal: float) -> float:
        for y0, y1, m in self.segments:
            if y0 <= year_decimal < y1:
                return m.delta_t_seconds(year_decimal)
        # clamp
        if year_decimal < self.segments[0][0]:
            return self.segments[0][2].delta_t_seconds(self.segments[0][0])
        return self.segments[-1][2].delta_t_seconds(self.segments[-1][1] - 1e-9)

    def info(self) -> Dict[str, object]:
        return {"type": "piecewise_poly", "segments": [(a, b, m.info()) for a, b, m in self.segments]}


@dataclass(frozen=True)
class TableDeltaT(DeltaTModel):
    """
    Table of (year_decimal -> ΔT seconds), with piecewise linear interpolation.
    - Keys can be integer years or any sorted knots.
    """
    knots: Tuple[Tuple[float, float], ...]  # sorted by year_decimal: (x, y)

    def delta_t_seconds(self, year_decimal: float) -> float:
        xs = self.knots
        if year_decimal <= xs[0][0]:
            return xs[0][1]
        if year_decimal >= xs[-1][0]:
            return xs[-1][1]
        # binary search for interval
        lo, hi = 0, len(xs) - 1
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if xs[mid][0] <= year_decimal:
                lo = mid
            else:
                hi = mid
        x0, y0 = xs[lo]
        x1, y1 = xs[lo + 1]
        t = (year_decimal - x0) / (x1 - x0)
        return (1.0 - t) * y0 + t * y1

    def info(self) -> Dict[str, object]:
        return {"type": "table_linear", "n": len(self.knots), "min": self.knots[0][0], "max": self.knots[-1][0]}


# ============================================================
# Rational models (optional, "toy" for L3): only constant/quadratic
# ============================================================

class DeltaTRationalModel(Protocol):
    def delta_t_seconds(self, year_decimal: Fraction) -> Fraction: ...
    def info(self) -> Dict[str, object]: ...


@dataclass(frozen=True)
class ConstantDeltaTRational(DeltaTRationalModel):
    value: Fraction
    def delta_t_seconds(self, year_decimal: Fraction) -> Fraction:
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
    y0: Fraction = Fraction(2000, 1)

    def delta_t_seconds(self, year_decimal: Fraction) -> Fraction:
        u = (year_decimal - self.y0) / Fraction(100, 1)
        return self.a + self.b*u + self.c*u*u

    def info(self) -> Dict[str, object]:
        return {"type": "quadratic-rational", "a": str(self.a), "b": str(self.b), "c": str(self.c), "y0": str(self.y0)}