from __future__ import annotations
from typing import TypeVar

from ._series import AffineSinSeries, eval_lincomb_turn
from ._fundamental import Backend
from ._trans import SinAcosTurnProvider

Num = TypeVar("Num")

def solve_picard(
    series: AffineSinSeries[Num],
    *,
    target: Num,
    t0: Num,
    iters: int,
    ctx_builder,
    B: Backend[Num],
    Tr: SinAcosTurnProvider,
) -> Num:
    """Picard specialized to affine+sin structure:
        t_{n+1} = (target - A - Σ amp*sin(theta(t_n))) / B
    """
    t = t0
    for _ in range(iters):
        ctx = ctx_builder(t)
        corr = B.from_int(0)
        for term in series.terms:
            ang = eval_lincomb_turn(ctx, term.theta, B)
            corr = B.add(corr, B.mul(term.amp, Tr.sin_turn(ang)))
        t = B.div(B.sub(B.sub(target, series.A), corr), series.B)
    return t

def steffensen_root(f, *, t0: float, iters: int) -> float:
    """Steffensen method for f(t)=0 (float lane)."""
    t = t0
    for _ in range(iters):
        ft = f(t)
        denom = f(t + ft) - ft
        t = t - (ft * ft) / denom
    return t
