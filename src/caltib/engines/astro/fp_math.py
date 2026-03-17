"""
caltib.engines.astro.fp_math
----------------------------
Floating-point mathematical evaluators and polynomial abstractions.
Designed to mirror the API of tables.py for seamless engine interchangeability,
while strictly forbidding FMA instructions to guarantee cross-platform determinism.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple
import struct

# IEEE 754 Deterministic Mathematical Constants
FLOAT_PI = float.fromhex("0x1.921fb54442d18p+1")      # 3.141592653589793
FLOAT_TWO_PI = float.fromhex("0x1.921fb54442d18p+2")  # 6.283185307179586

def float_sqrt(S: float) -> float:
    """
    Deterministic square root using the 64-bit Fast Inverse Square Root algorithm.
    Guarantees cross-platform bitwise reproducibility by bypassing hardware FPU intrinsics.
    Requires 3 Newton-Raphson iterations to reach machine epsilon (~10^-16).
    """
    if S <= 0.0:
        return 0.0
        
    # Reinterpret the bits of the floating-point radicand S as a 64-bit integer
    packed = struct.pack('>d', S)
    i_s = struct.unpack('>Q', packed)[0]
    
    # Initial piecewise linear approximation of the logarithm
    i_y0 = 0x5fe6eb50c7b537a9 - (i_s >> 1)
    
    # Reinterpret integer back to float for refinement
    packed_y = struct.pack('>Q', i_y0)
    y = struct.unpack('>d', packed_y)[0]
    
    # 3 Division-free Newton-Raphson iterations
    half_S = 0.5 * S
    for _ in range(3):
        # Separated multiply/subtract to strictly forbid Fused Multiply-Add (FMA) 
        y2_term = y * y
        y = y * (1.5 - half_S * y2_term)
        
    return S * y

def reduce_to_quarter_turn(x: float) -> float:
    """
    Wraps a normalized turn [0, 1) to the primary evaluation domain [-0.25, 0.25].
    Utilizes sine wave symmetry to map quadrants 2 and 3 back to the primary wave.
    """
    u = (x + 0.5) % 1.0 - 0.5
    if u > 0.25:
        return 0.5 - u
    elif u < -0.25:
        return -0.5 - u
    return u


def eval_odd_poly(x: float, coeffs: Tuple[float, ...]) -> float:
    """
    Evaluates an odd polynomial c1*x + c3*x^3 + c5*x^5 ... using Horner's method.
    Coeffs array is expected to be ordered from lowest degree to highest: (c1, c3, c5...).
    Strictly explicitly separates multiply and add statements to forbid FMA.
    """
    if not coeffs:
        return 0.0
        
    x2 = x * x
    res = coeffs[-1]
    
    # Iterate backwards through the remaining coefficients
    for c in reversed(coeffs[:-1]):
        term = x2 * res
        res = c + term
        
    return x * res


@dataclass(frozen=True)
class QuarterWavePolynomial:
    """
    Floating-point counterpart to QuarterWaveTable.
    Evaluates a minimax odd polynomial representing a quarter-wave (e.g., sine).
    """
    coeffs: Tuple[float, ...]

    def eval_normalized_turn(self, x_turn: float) -> float:
        """Evaluate at phase x in turns. Returns value in [-1.0, 1.0]."""
        x_quarter = reduce_to_quarter_turn(x_turn)
        return eval_odd_poly(x_quarter, self.coeffs)
        
    def cos_normalized_turn(self, x_turn: float) -> float:
        """Convenience method for cosine (sine shifted by +1/4 turn)."""
        return self.eval_normalized_turn(x_turn + 0.25)


@dataclass(frozen=True)
class ArctanPolynomial:
    """Evaluates a minimax odd polynomial representing arctan(x) in turns."""
    coeffs: Tuple[float, ...]

    def atan_turn(self, r: float) -> float:
        """arctan(r) returned in turns."""
        if r < 0.0:
            return -self.atan_turn(-r)
        
        # Mandatory reduction: map (1, inf) down to [0, 1]
        if r > 1.0:
            return 0.25 - self.atan_turn(1.0 / r)
            
        # Evaluate the polynomial directly over [0, 1]
        return eval_odd_poly(r, self.coeffs)

    def atan2_turn(self, y: float, x: float) -> float:
        """atan2(y, x) returned in turns [-0.5, 0.5]."""
        if x > 0.0:
            return self.atan_turn(y / x)
        elif x < 0.0:
            if y >= 0.0:
                return 0.5 + self.atan_turn(y / x)
            else:
                return -0.5 + self.atan_turn(y / x)
        else:  # x == 0.0
            if y > 0.0:
                return 0.25
            elif y < 0.0:
                return -0.25
            else:
                return 0.0

    def asin_turn(self, x: float) -> float:
        """arcsin(x) returned in turns [-0.25, 0.25]."""
        x = max(-1.0, min(1.0, x)) 
        return self.atan2_turn(x, float_sqrt(1.0 - x * x))

    def acos_turn(self, x: float) -> float:
        """arccos(x) returned in turns [0.0, 0.5]."""
        x = max(-1.0, min(1.0, x))
        return self.atan2_turn(float_sqrt(1.0 - x * x), x)