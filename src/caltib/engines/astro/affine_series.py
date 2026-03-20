from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Dict, Tuple, Any


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

@dataclass(frozen=True)
class TermDef:
    """Pure data representation of a continuous series term (for specs.py)."""
    amp: Fraction
    phase: PhaseT
    amp1: Fraction = Fraction(0, 1)

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
    amp1: Fraction = Fraction(0, 1)


@dataclass(frozen=True)
class AffineTabSeriesT:
    """
    x(t) = base(t) + Σ amp_i * table_i(phase_i(t)), where base(t) = A + B*t + C*t^2.
    """
    A: Fraction
    B: Fraction
    terms: Tuple[TabTermT, ...]
    C: Fraction = Fraction(0,1)

    def base(self, t: Fraction) -> Fraction:
        return self.A + t * (self.B + t * self.C)

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
        invB_prec: Fraction = None,
    ) -> Fraction:
        """
        Fixed iteration solver for x(t)=x0 in the contractive regime:
          t_{k+1} = t0 - C(t_k)/B,   t0=(x0-A)/B
        This is the D.4.1 style iteration with fixed count for reproducibility.
        """
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
            
        # Step 1: The Exact Physical Anchor
        # t0 MUST use the exact B to anchor the true J2000 physical rate.
        # This injects the wild prime into the denominator exactly once (Power 1).
        t0 = (x0 - self.A) / self.B
        
        # O(1) baseline bypass
        if iterations == 0:
            return t0
            
        t = t0 if t_init is None else t_init

        # Step 2: The Preconditioner
        # Use the harmonic preconditioner if provided, else fallback to exact 1/B
        multiplier = invB_prec if invB_prec is not None else Fraction(1, 1) / self.B
        
        # Step 3: The Contractive Loop
        for _ in range(iterations):
            # Calculate the correction sum C(t)
            corr = self.C * t * t
            for term in self.terms:
                current_amp = term.amp + term.amp1 * t
                corr += current_amp * term.table_eval_turn(term.phase.eval(t))
                
            # Apply iteration step
            # By using the harmonic multiplier, the wild prime safely stays at Power 1
            t = t0 - corr * multiplier
            
        return t

def make_funds(
    m0: Fraction, 
    fund_rates: Dict[str, Fraction],  # <--- Injected dependency
    jd_base: Fraction,                # <--- Injected dependency (e.g., JD_J2000)
    s0: Fraction = Fraction(0),
    a0: Fraction = Fraction(0),
    r0: Fraction = Fraction(0),
    f0: Fraction = Fraction(0),
) -> Dict[str, Any]: # Returns mixed dict (Fraction for m0, FundArg for the rest)
    """
    Binds epoch phases (at absolute JD) to the standard fundamental rates (c1),
    projecting them back to t=0 (e.g. J2000.0) for the absolute time solver.
    """
    
    # Shift absolute JD to internal coordinate system (Days since jd_base)
    m0_offset = m0 - jd_base
    
    # Elongation is exactly 0 at the epoch: D(m0_offset) = c0 + c1*m0_offset = 0
    c0_D = -fund_rates["D"] * m0_offset
    
    # Sun longitude is s0 at the epoch: S(m0_offset) = c0 + c1*m0_offset = s0
    c0_S = s0 - fund_rates["S"] * m0_offset
    
    c0_M = r0 - fund_rates["M"] * m0_offset
    c0_Mp = a0 - fund_rates["Mp"] * m0_offset
    c0_F = f0 - fund_rates["F"] * m0_offset
    
    return {
        "m0": m0,
        "S":  FundArg(c0=c0_S, c1=fund_rates["S"]),
        "D":  FundArg(c0=c0_D, c1=fund_rates["D"]),
        "M":  FundArg(c0=c0_M, c1=fund_rates["M"]),
        "Mp": FundArg(c0=c0_Mp, c1=fund_rates["Mp"]),
        "F":  FundArg(c0=c0_F, c1=fund_rates["F"]),
    }

def compile_affine_terms(
    funds: Dict[str, FundArg],
    keys: Tuple[str, ...],
    rows: Tuple[Tuple[Any, ...], ...],
    include_drift: bool = False
) -> Tuple[TermDef, ...]:
    """
    Matrix-multiplies fundamental arguments against rational tables at startup.
    Analogous to build_collapsed_terms, but returns pure TermDefs since the 
    affine loop natively handles amp1 without a static/dynamic list split.
    """
    compiled = []
    num_keys = len(keys)
    
    # 36525 days in a Julian Century
    century_days = Fraction(36525, 1)
    
    for row in rows:
        mults = row[:num_keys]
        raw_amp = row[num_keys]
        
        # 1. Extract drift if requested
        if include_drift and len(row) > (num_keys + 1):
            raw_amp_drift = row[num_keys + 1]
        else:
            raw_amp_drift = Fraction(0, 1)
            
        # 2. Collapse fundamental arguments
        c0 = Fraction(0, 1)
        c1 = Fraction(0, 1)
        for key, m in zip(keys, mults):
            if m != 0:
                c0 += funds[key].c0 * Fraction(m, 1)
                c1 += funds[key].c1 * Fraction(m, 1)
            
        # 3. Return the pure data blueprint!
        compiled.append(TermDef(
            amp=raw_amp,
            phase=PhaseT(c0=c0, c1=c1),
            amp1=raw_amp_drift
        ))
        
    return tuple(compiled)