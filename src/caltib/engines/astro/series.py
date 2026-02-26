from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, Mapping, Tuple, TypeVar

from .fundamental import ArgName, FundamentalContext, Backend
from .trans import SinAcosTurnProvider

Num = TypeVar("Num")  # Fraction or float, typically

@dataclass(frozen=True)
class LinComb:
    mult: Mapping[ArgName, int]  # integer multipliers

def eval_lincomb_turn(ctx: FundamentalContext[Num], lc: LinComb, B: Backend[Num]) -> Num:
    s = B.from_int(0)
    for a, k in lc.mult.items():
        if k:
            s = B.add(s, B.mul(B.from_int(k), ctx.ang[a]))
    return s

@dataclass(frozen=True)
class SinTerm(Generic[Num]):
    amp: Num     # amplitude in whatever unit x uses
    theta: LinComb

@dataclass(frozen=True)
class AffineSinSeries(Generic[Num]):
    """x(t) = A + B*t + Σ amp_i * sin(theta_i(t)) (theta in turns)."""
    A: Num
    B: Num
    terms: Tuple[SinTerm[Num], ...]

def eval_affine_sin(
    series: AffineSinSeries[Num],
    t: Num,
    ctx_builder,
    B: Backend[Num],
    Tr: SinAcosTurnProvider,
) -> Num:
    ctx = ctx_builder(t)
    total = B.add(series.A, B.mul(series.B, t))
    for term in series.terms:
        ang = eval_lincomb_turn(ctx, term.theta, B)
        total = B.add(total, B.mul(term.amp, Tr.sin_turn(ang)))
    return total
