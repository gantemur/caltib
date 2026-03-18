"""
caltib.engines.astro.float_series
---------------------------------
High-performance floating-point Fourier series evaluators.
Pre-collapses complex fundamental arguments into flat phase linearities
for ultra-fast Picard and Newton-Raphson iterations. Features split-tuple
routing to evaluate secular anomaly drifts with zero loop overhead.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Dict, Optional

from caltib.engines.astro.fp_math import QuarterWavePolynomial, FLOAT_TWO_PI

@dataclass(frozen=True)
class FloatTermDef:
    """Pure data representation of a pre-collapsed harmonic term."""
    amp: float
    c0: float
    c1: float
    amp1: float = 0.0  # Secular amplitude drift (e.g., per century)

@dataclass(frozen=True)
class FloatFourierSeries:
    """
    x(t) = base(t) + C(t)
    base(t) = A + B*t + C*t^2
    C(t) = Σ amp_i * poly(phase) + Σ (amp_j + amp1_j * t) * poly(phase)
    """
    A: float
    B: float
    static_terms: Tuple[FloatTermDef, ...]   # Evaluated without secular overhead
    dynamic_terms: Tuple[FloatTermDef, ...]  # Evaluated with linear T-drift
    poly: QuarterWavePolynomial
    C: float = 0.0

    def base(self, t: float) -> float:
        """Evaluates the base quadratic drift."""
        return self.A + t * (self.B + t * self.C)

    def eval(self, t: float) -> float:
        """Evaluates the complete series at continuous time t."""
        s = self.base(t)
        
        for term in self.static_terms:
            s += term.amp * self.poly.eval_normalized_turn(term.c0 + term.c1 * t)
            
        for term in self.dynamic_terms:
            current_amp = term.amp + term.amp1 * t
            s += current_amp * self.poly.eval_normalized_turn(term.c0 + term.c1 * t)
            
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
            
            # 1. Ultra-fast loop for static terms
            for term in self.static_terms:
                corr += term.amp * self.poly.eval_normalized_turn(term.c0 + term.c1 * t)
                
            # 2. Dynamic loop for secular drift terms
            for term in self.dynamic_terms:
                current_amp = term.amp + term.amp1 * t
                corr += current_amp * self.poly.eval_normalized_turn(term.c0 + term.c1 * t)
                
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
            # Evaluate x(t) and its derivative x'(t)
            x_val = self.A + t * (self.B + t * self.C)
            dx_dt = self.B + 2.0 * self.C * t
            
            # 1. Static terms (Standard derivative)
            for term in self.static_terms:
                phase = term.c0 + term.c1 * t
                
                x_val += term.amp * self.poly.eval_normalized_turn(phase)
                dx_dt += term.amp * term.c1 * FLOAT_TWO_PI * self.poly.cos_normalized_turn(phase)
                
            # 2. Dynamic terms (Product rule derivative)
            for term in self.dynamic_terms:
                phase = term.c0 + term.c1 * t
                current_amp = term.amp + term.amp1 * t
                
                sin_val = self.poly.eval_normalized_turn(phase)
                
                # Position: A(t) * sin(phase)
                x_val += current_amp * sin_val
                
                # Derivative: A'(t)*sin(phase) + A(t)*phase'*cos(phase)
                dx_dt += term.amp1 * sin_val 
                dx_dt += current_amp * term.c1 * FLOAT_TWO_PI * self.poly.cos_normalized_turn(phase)
                
            # Newton-Raphson Step: t_{k+1} = t_k - f(t_k) / f'(t_k)
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
    amp_scale: float = 1.0,
    amp1_scale: Optional[float] = None,
    include_drift: bool = False
) -> Tuple[Tuple[FloatTermDef, ...], Tuple[FloatTermDef, ...]]:
    """
    Matrix-multiplies fundamental arguments against JPL/Meeus tables at startup.
    Separates terms into static and dynamic (secular drift) tuples for ultra-fast evaluation.
    
    Example rows: ((d, m, mp, f, amp_microdeg, [amp_drift]), ...)
    
    Returns:
        (static_terms, dynamic_terms)
    """
    #  Resolve the dynamic default: assuming amp1 is given by */cy, convert to */day
    if amp1_scale is None:
        amp1_scale = amp_scale / 36525.0

    static_terms = []
    dynamic_terms = []
    num_keys = len(keys)
    
    for row in rows:
        mults = row[:num_keys]
        raw_amp = row[num_keys]
        
        # Check if the optional secular drift term exists AND should be included
        if include_drift and len(row) > (num_keys + 1):
            raw_amp_drift = row[num_keys + 1]
        else:
            raw_amp_drift = 0.0
            
        c0_sum = 0.0
        c1_sum = 0.0
        for key, m in zip(keys, mults):
            if m != 0:
                c0_sum += funds[key].c0 * m
                c1_sum += funds[key].c1 * m
                
        term = FloatTermDef(
            amp=raw_amp * amp_scale,
            c0=c0_sum % 1.0, # Pre-wrap the phase intercept!
            c1=c1_sum,
            amp1=raw_amp_drift * amp1_scale # Pre-scale the drift!
        )
        
        # Route the term to the correct execution loop
        if term.amp1 == 0.0:
            static_terms.append(term)
        else:
            dynamic_terms.append(term)
            
    return tuple(static_terms), tuple(dynamic_terms)