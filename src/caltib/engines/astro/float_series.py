"""
caltib.engines.astro.float_series
---------------------------------
High-performance floating-point Fourier series evaluators.
Pre-collapses complex fundamental arguments into flat phase linearities
for ultra-fast Picard iterations.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Dict

from caltib.engines.astro.fp_math import QuarterWavePolynomial, FLOAT_TWO_PI

@dataclass(frozen=True)
class FloatTermDef:
    """Pure data representation of a pre-collapsed harmonic term."""
    amp: float
    c0: float
    c1: float

@dataclass(frozen=True)
class FloatFourierSeries:
    """
    x(t) = base(t) + C(t)
    base(t) = A + B*t + C*t^2
    C(t) = Σ amp_i * poly(c0_i + c1_i * t)
    """
    A: float
    B: float
    terms: Tuple[FloatTermDef, ...]
    poly: QuarterWavePolynomial
    C: float = 0.0

    def base(self, t: float) -> float:
        """Evaluates the base quadratic drift."""
        return self.A + t * (self.B + t * self.C)

    def eval(self, t: float) -> float:
        """Evaluates the complete series at continuous time t."""
        s = self.base(t)
        for term in self.terms:
            s += term.amp * self.poly.eval_normalized_turn(term.c0 + term.c1 * t)
        return s

    def picard_solve(self, x0: float, iterations: int, t_init: float = None) -> float:
        """Solves x(t) = x0 via fixed-point iteration."""
        if iterations == 0:
            return (x0 - self.A) / self.B
            
        t0 = (x0 - self.A) / self.B
        t = t0 if t_init is None else t_init
        invB = 1.0 / self.B
        
        for _ in range(iterations):
            corr = 0.0
            for term in self.terms:
                corr += term.amp * self.poly.eval_normalized_turn(term.c0 + term.c1 * t)
                
            t2_term = self.C * (t * t)
            t = ((x0 - self.A) - t2_term - corr) * invB
            
        return t

    def nr_solve(self, x0: float, iterations: int, t_init: float = None) -> float:
        """
        Solves x(t) = x0 via Newton-Raphson iteration.
        Yields quadratic convergence, requiring fewer iterations than Picard.
        """
        if iterations == 0:
            return (x0 - self.A) / self.B
            
        t = ((x0 - self.A) / self.B) if t_init is None else t_init
        
        for _ in range(iterations):
            # 1. Evaluate x(t) and its derivative x'(t)
            x_val = self.A + t * (self.B + t * self.C)
            dx_dt = self.B + 2.0 * self.C * t
            
            for term in self.terms:
                phase = term.c0 + term.c1 * t
                
                # Add position term: A * sin(phase)
                x_val += term.amp * self.poly.eval_normalized_turn(phase)
                
                # Add derivative term: A * c1 * 2π * cos(phase)
                dx_dt += term.amp * term.c1 * FLOAT_TWO_PI * self.poly.cos_normalized_turn(phase)
                
            # 2. Newton-Raphson Step: t_{k+1} = t_k - f(t_k) / f'(t_k)
            t = t - (x_val - x0) / dx_dt
            
        return t

# --- Initialization Helpers (For specs.py) ---

@dataclass(frozen=True)
class FloatFundArg:
    c0: float
    c1: float

def build_collapsed_terms(
    funds: Dict[str, FloatFundArg],
    keys: Tuple[str, ...],
    rows: Tuple[Tuple[float, ...], ...],
    amp_scale: float = 1.0
) -> Tuple[FloatTermDef, ...]:
    """
    Matrix-multiplies fundamental arguments against JPL/Meeus tables at startup.
    Example rows: ((d, m, mp, f, amp_microdeg), ...)
    """
    terms = []
    for row in rows:
        mults = row[:-1]
        raw_amp = row[-1]
        
        c0_sum = 0.0
        c1_sum = 0.0
        for key, m in zip(keys, mults):
            if m != 0:
                c0_sum += funds[key].c0 * m
                c1_sum += funds[key].c1 * m
                
        terms.append(FloatTermDef(
            amp=raw_amp * amp_scale,
            c0=c0_sum % 1.0, # Pre-wrap the phase intercept!
            c1=c1_sum
        ))
    return tuple(terms)