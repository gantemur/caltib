from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Sequence, Tuple


def frac_turn(x: Fraction) -> Fraction:
    q = x.numerator // x.denominator
    return x - Fraction(q, 1)


# ============================================================
# Traditional DN-series: base affine date + table corrections
# ============================================================

@dataclass(frozen=True)
class PhaseDN:
    """θ(d,n) = c0 + n*c1 + d*c2  (turns), reduced mod 1."""
    c0: Fraction
    c1: Fraction
    c2: Fraction

    def eval(self, d: int, n: int) -> Fraction:
        return frac_turn(self.c0 + Fraction(n, 1) * self.c1 + Fraction(d, 1) * self.c2)


@dataclass(frozen=True)
class TabTermDN:
    """
    amp * table( phase(d,n) )
    amp has the output unit (days for true_date correction terms).
    table(phase) returns table-units (Fraction), so amp should absorb 1/60, signs, etc.
    """
    amp: Fraction
    phase: PhaseDN
    table_eval_turn: Callable[[Fraction], Fraction]


@dataclass(frozen=True)
class AffineTabSeriesDN:
    """
    t(d,n) = base(d,n) + Σ amp_i * table_i(phase_i(d,n))
    with base(d,n) affine in (d,n).
    """
    base_c0: Fraction
    base_cn: Fraction
    base_cd: Fraction
    terms: Tuple[TabTermDN, ...]

    def base(self, d: int, n: int) -> Fraction:
        return self.base_c0 + Fraction(n, 1) * self.base_cn + Fraction(d, 1) * self.base_cd

    def eval(self, d: int, n: int) -> Fraction:
        t = self.base(d, n)
        for term in self.terms:
            t += term.amp * term.table_eval_turn(term.phase.eval(d, n))
        return t


# ============================================================
# New-mode inverse: x(t) = A + B t + Σ amp*sin(phase(t))
# ============================================================

@dataclass(frozen=True)
class PhaseT:
    """θ(t) = c0 + c1*t + c2*t^2  (turns), reduced mod 1."""
    c0: Fraction
    c1: Fraction
    c2: Fraction = Fraction(0, 1)

    def eval(self, t: Fraction) -> Fraction:
        return frac_turn(self.c0 + self.c1 * t + self.c2 * t * t)


@dataclass(frozen=True)
class SinTermT:
    """
    amp * sin( phase(t) )
    amp is in turns (or same unit as x).
    sin_eval_turn returns Fraction in [-1,1] (table/poly approximation decides).
    """
    amp: Fraction
    phase: PhaseT


@dataclass(frozen=True)
class AffineSinSeriesT:
    """
    x(t) = A + B*t + C(t),  C(t)=Σ amp_i * sin(phase_i(t)).
    All arithmetic can be Fraction (L1–L3) or float (L4–L5), depending on the provider.
    """
    A: Fraction
    B: Fraction
    terms: Tuple[SinTermT, ...]

    def C(self, t: Fraction, sin_eval_turn: Callable[[Fraction], Fraction]) -> Fraction:
        s = Fraction(0, 1)
        for term in self.terms:
            s += term.amp * sin_eval_turn(term.phase.eval(t))
        return s

    def x(self, t: Fraction, sin_eval_turn: Callable[[Fraction], Fraction]) -> Fraction:
        return self.A + self.B * t + self.C(t, sin_eval_turn)

    def picard_solve(
        self,
        x0: Fraction,
        *,
        iterations: int,
        sin_eval_turn: Callable[[Fraction], Fraction],
        t_init: Fraction = None,
    ) -> Fraction:
        """
        Fixed iteration solver for x(t)=x0 in the contractive regime:
          t_{k+1} = t0 - C(t_k)/B,   t0=(x0-A)/B
        This is the D.4.1 style iteration with fixed count for reproducibility.:contentReference[oaicite:7]{index=7}
        """
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        t0 = (x0 - self.A) / self.B
        t = t0 if t_init is None else t_init
        invB = Fraction(1, 1) / self.B
        for _ in range(iterations):
            t = t0 - self.C(t, sin_eval_turn) * invB
        return t