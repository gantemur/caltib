from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Generic, Literal, Mapping, Optional, Protocol, TypeVar

from ._deltat import DeltaTModel, DeltaTRationalModel

Num = TypeVar("Num", Fraction, float)

# Angles measured in turns (1 turn = full circle).
ArgName = Literal["L0", "Lp", "D", "M", "Mp", "F", "Omega", "eps"]


@dataclass(frozen=True)
class Poly2(Generic[Num]):
    # a0 + a1*t + a2*t^2 (turns)
    a0: Num
    a1: Num
    a2: Num

    def deriv(self) -> "Poly2[Num]":
        # derivative: a1 + 2*a2*t ; store as Poly2(a1, 2*a2, 0)
        return Poly2(self.a1, self.a2 * 2, self.a2 * 0)  # works for Fraction/float


@dataclass(frozen=True)
class ArgDef(Generic[Num]):
    poly: Poly2[Num]
    wrap1: bool = True  # False for eps if desired


class Backend(Protocol[Num]):
    kind: Literal["rational", "float"]

    def add(self, a: Num, b: Num) -> Num: ...
    def sub(self, a: Num, b: Num) -> Num: ...
    def mul(self, a: Num, b: Num) -> Num: ...
    def div(self, a: Num, b: Num) -> Num: ...
    def floor(self, a: Num) -> int: ...
    def from_int(self, n: int) -> Num: ...


@dataclass(frozen=True)
class RationalBackend(Backend[Fraction]):
    kind: Literal["rational"] = "rational"

    def add(self, a: Fraction, b: Fraction) -> Fraction:
        return a + b

    def sub(self, a: Fraction, b: Fraction) -> Fraction:
        return a - b

    def mul(self, a: Fraction, b: Fraction) -> Fraction:
        return a * b

    def div(self, a: Fraction, b: Fraction) -> Fraction:
        return a / b

    def floor(self, a: Fraction) -> int:
        return a.numerator // a.denominator

    def from_int(self, n: int) -> Fraction:
        return Fraction(n, 1)


@dataclass(frozen=True)
class FloatBackend(Backend[float]):
    kind: Literal["float"] = "float"

    def add(self, a: float, b: float) -> float:
        return a + b

    def sub(self, a: float, b: float) -> float:
        return a - b

    def mul(self, a: float, b: float) -> float:
        return a * b

    def div(self, a: float, b: float) -> float:
        return a / b

    def floor(self, a: float) -> int:
        return int(a // 1.0)

    def from_int(self, n: int) -> float:
        return float(n)


def eval_poly2(poly: Poly2[Num], t: Num, B: Backend[Num]) -> Num:
    return B.add(poly.a0, B.add(B.mul(poly.a1, t), B.mul(poly.a2, B.mul(t, t))))


def wrap_turn(x: Num, B: Backend[Num]) -> Num:
    # x mod 1 into [0,1)
    k = B.floor(x)
    return B.sub(x, B.from_int(k))


@dataclass(frozen=True)
class FundamentalModel(Generic[Num]):
    """
    Fundamental angle polynomials (turns) plus optional ΔT models.

    - delta_t: float-based ΔT model (default)
    - delta_t_rational: rational toy ΔT model (optional, for L3-style rational workflows)
    """
    args: Mapping[ArgName, ArgDef[Num]]
    delta_t: Optional[DeltaTModel] = None
    delta_t_rational: Optional[DeltaTRationalModel] = None
    meta: Optional[Dict[str, object]] = None


@dataclass(frozen=True)
class FundamentalContext(Generic[Num]):
    """
    Evaluated fundamentals at parameter t.

    - ang: turns (Num)
    - delta_t_sec_float: float ΔT seconds, if requested
    - delta_t_sec_rational: Fraction ΔT seconds, if requested
    """
    t: Num
    ang: Mapping[ArgName, Num]
    delta_t_sec_float: Optional[float] = None
    delta_t_sec_rational: Optional[Fraction] = None
    meta: Optional[Dict[str, object]] = None


def make_context(
    model: FundamentalModel[Num],
    t: Num,
    B: Backend[Num],
    *,
    year_decimal: Optional[float] = None,
    year_decimal_rational: Optional[Fraction] = None,
) -> FundamentalContext[Num]:
    ang: Dict[ArgName, Num] = {}
    for name, adef in model.args.items():
        v = eval_poly2(adef.poly, t, B)
        if adef.wrap1:
            v = wrap_turn(v, B)
        ang[name] = v

    dt_f: Optional[float] = None
    dt_r: Optional[Fraction] = None

    if model.delta_t is not None and year_decimal is not None:
        dt_f = float(model.delta_t.delta_t_seconds(year_decimal))

    if model.delta_t_rational is not None and year_decimal_rational is not None:
        dt_r = model.delta_t_rational.delta_t_seconds(year_decimal_rational)

    return FundamentalContext(
        t=t,
        ang=ang,
        delta_t_sec_float=dt_f,
        delta_t_sec_rational=dt_r,
        meta=model.meta,
    )