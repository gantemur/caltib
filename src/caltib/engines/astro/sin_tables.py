from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple


def _frac_part(x: Fraction) -> Fraction:
    q = x.numerator // x.denominator
    return x - Fraction(q, 1)


@dataclass(frozen=True)
class OddPeriodicTable:
    """
    Odd periodic lookup table evaluated by linear interpolation.
    N (full period nodes) and amplitude are automatically deduced.
    """
    quarter: Tuple[int, ...]  # monotone 0..peak

    def __post_init__(self) -> None:
        if len(self.quarter) < 2:
            raise ValueError("quarter table must have at least 2 elements")
            
        # Deduce N and amplitude directly from the table shape
        object.__setattr__(self, "N", 4 * (len(self.quarter) - 1))
        object.__setattr__(self, "amplitude", self.quarter[-1])

    def eval_u(self, u: Fraction) -> Fraction:
        """Evaluate at real argument u (in grid units). Returns raw table units."""
        k = (u.numerator // u.denominator) // self.N
        u0 = u - Fraction(self.N * k, 1)

        if u0 < 0:
            k2 = (-u0.numerator // u0.denominator) // self.N + 1
            u0 = u0 + Fraction(self.N * k2, 1)

        sign = 1
        if u0 > Fraction(self.N, 2):
            sign = -1
            u0 = Fraction(self.N, 1) - u0

        if u0 > Fraction(self.N, 4):
            u0 = Fraction(self.N, 2) - u0

        i = int(u0)
        if i >= self.N // 4:
            return Fraction(sign * self.amplitude, 1)

        t = u0 - Fraction(i, 1)
        v0 = Fraction(self.quarter[i], 1)
        v1 = Fraction(self.quarter[i + 1], 1)
        v = v0 + t * (v1 - v0)
        return Fraction(sign, 1) * v

    def eval_turn(self, x_turn: Fraction) -> Fraction:
        """Evaluate at phase x in turns. Returns raw table units."""
        x = _frac_part(x_turn)
        return self.eval_u(x * Fraction(self.N, 1))

    def eval_normalized_turn(self, x_turn: Fraction) -> Fraction:
        """Evaluate at phase x in turns. Returns scaled fraction in [-1, 1]."""
        return self.eval_turn(x_turn) / Fraction(self.amplitude, 1)

    def asin_turn(self, y: Fraction) -> Fraction:
        """
        Inverse lookup: given table-unit y, return the phase in turns [-1/4, 1/4].
        Assumes the quarter table represents monotonically increasing values.
        """
        if y < 0:
            return -self.asin_turn(-y)
            
        v_max = Fraction(self.amplitude, 1)
        if y >= v_max:
            return Fraction(1, 4)
            
        # Locate the interval
        lo, hi = 0, len(self.quarter) - 1
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if Fraction(self.quarter[mid], 1) <= y:
                lo = mid
            else:
                hi = mid
                
        y0 = Fraction(self.quarter[lo], 1)
        y1 = Fraction(self.quarter[lo + 1], 1)
        
        # Safeguard against flat spots in the table
        diff = y1 - y0
        if diff == 0:
            t = Fraction(0, 1)
        else:
            t = (y - y0) / diff
        
        # Grid index is lo + t. Turn fraction is (lo + t) / N.
        return (Fraction(lo, 1) + t) / Fraction(self.N, 1)

    def acos_turn(self, y: Fraction) -> Fraction:
        """arccos(y) for raw table-units y. Returns phase in turns [0, 1/2]."""
        return Fraction(1, 4) - self.asin_turn(y)

    def asin_normalized_turn(self, y_norm: Fraction) -> Fraction:
        """
        Inverse lookup for normalized input y in [-1, 1].
        Returns phase in turns [-1/4, 1/4].
        """
        return self.asin_turn(y_norm * Fraction(self.amplitude, 1))

    def acos_normalized_turn(self, y_norm: Fraction) -> Fraction:
        """
        arccos for normalized input y in [-1, 1].
        Returns phase in turns [0, 1/2].
        """
        return Fraction(1, 4) - self.asin_normalized_turn(y_norm)