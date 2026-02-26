from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Dict, Tuple


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
# New-mode inverse: x(t) = base(t) + Σ amp*table(phase(t))
# ============================================================

@dataclass(frozen=True)
class PhaseT:
    """θ(t) = c0 + c1*t  (turns), reduced mod 1. Strictly linear for L1-L3."""
    c0: Fraction
    c1: Fraction

    def eval(self, t: Fraction) -> Fraction:
        return frac_turn(self.c0 + self.c1 * t)


@dataclass(frozen=True)
class FundArg:
    """Base fundamental argument: c0 + c1*t"""
    c0: Fraction
    c1: Fraction


def build_phase(multipliers: Dict[str, int], funds: Dict[str, FundArg]) -> PhaseT:
    """Collapses fundamental arguments safely at initialization time."""
    c0 = sum((funds[k].c0 * Fraction(m, 1) for k, m in multipliers.items()), start=Fraction(0, 1))
    c1 = sum((funds[k].c1 * Fraction(m, 1) for k, m in multipliers.items()), start=Fraction(0, 1))
    return PhaseT(c0=c0, c1=c1)


@dataclass(frozen=True)
class TabTermT:
    """
    amp * table( phase(t) )
    amp is in turns (or same unit as x).
    table_eval_turn returns Fraction (table or poly approximation decides).
    """
    amp: Fraction
    phase: PhaseT
    table_eval_turn: Callable[[Fraction], Fraction]


@dataclass(frozen=True)
class AffineTabSeriesT:
    """
    x(t) = base(t) + C(t),  C(t)=Σ amp_i * table_i(phase_i(t)).
    All arithmetic can be Fraction (L1–L3) or float (L4–L5), depending on the provider.
    """
    A: Fraction
    B: Fraction
    terms: Tuple[TabTermT, ...]

    def base(self, t: Fraction) -> Fraction:
        return self.A + self.B * t

    def eval(self, t: Fraction) -> Fraction:
        s = self.base(t)
        for term in self.terms:
            s += term.amp * term.table_eval_turn(term.phase.eval(t))
        return s

    def picard_solve(
        self,
        x0: Fraction,
        *,
        iterations: int,
        t_init: Fraction = None,
    ) -> Fraction:
        """
        Fixed iteration solver for x(t)=x0 in the contractive regime:
          t_{k+1} = t0 - C(t_k)/B,   t0=(x0-A)/B
        This is the D.4.1 style iteration with fixed count for reproducibility.
        """
        if iterations <= 0:
            raise ValueError("iterations must be positive")
            
        t0 = (x0 - self.A) / self.B
        t = t0 if t_init is None else t_init
        invB = Fraction(1, 1) / self.B
        
        for _ in range(iterations):
            # Calculate the correction sum C(t)
            corr = Fraction(0, 1)
            for term in self.terms:
                corr += term.amp * term.table_eval_turn(term.phase.eval(t))
                
            # Apply iteration step
            t = t0 - corr * invB
            
        return t