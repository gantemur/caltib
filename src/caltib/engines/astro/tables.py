# engines/astro/tables.py
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple

def _frac_part(x: Fraction) -> Fraction:
    q = x.numerator // x.denominator
    return x - Fraction(q, 1)

@dataclass(frozen=True)
class QuarterWaveTable:
    """
    Quarter-wave periodic lookup table evaluated by linear interpolation.
    (Formerly OddPeriodicTable). Evaluates over 4 symmetric quadrants.
    This is almost exclusively a model of the sine function.
    """
    quarter: Tuple[int, ...]  # monotone 0..peak

    def __post_init__(self) -> None:
        if len(self.quarter) < 2:
            raise ValueError("quarter table must have at least 2 elements")
            
        object.__setattr__(self, "N", 4 * (len(self.quarter) - 1))
        object.__setattr__(self, "amplitude", self.quarter[-1])

    def eval_u(self, u: Fraction) -> Fraction:
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

@dataclass(frozen=True)
class HalfWaveTable:
    """
    Half-wave periodic lookup table for odd functions without quarter-symmetry.
    This is almost exclusively a model of the Equation of Conjunction C(x).
    Evaluates over 2 symmetric halves: f(N - u) = -f(u).
    """
    half: Tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.half) < 2:
            raise ValueError("table must have at least 2 elements")
            
        L = len(self.half)
        if self.half[-1] != 0:
            # Zero-crossing is assumed at half-grid step: L - 0.5
            object.__setattr__(self, "N", 2 * L - 1)
            # Append the reflected point so standard interpolation crosses 0 perfectly
            object.__setattr__(self, "half", self.half + (-self.half[-1],))
        else:
            # Zero-crossing is exactly on the last grid point
            object.__setattr__(self, "N", 2 * (L - 1))
            
        object.__setattr__(self, "amplitude", max(abs(x) for x in self.half))

    def eval_u(self, u: Fraction) -> Fraction:
        k = (u.numerator // u.denominator) // self.N
        u0 = u - Fraction(self.N * k, 1)

        if u0 < 0:
            k2 = (-u0.numerator // u0.denominator) // self.N + 1
            u0 = u0 + Fraction(self.N * k2, 1)

        sign = 1
        if u0 > Fraction(self.N, 2):
            sign = -1
            u0 = Fraction(self.N, 1) - u0

        i = int(u0)
        if i >= len(self.half) - 1:
            return Fraction(0, 1)  # Safeguard if floating exactly at N/2 bound

        t = u0 - Fraction(i, 1)
        v0 = Fraction(self.half[i], 1)
        v1 = Fraction(self.half[i + 1], 1)
        v = v0 + t * (v1 - v0)
        return Fraction(sign, 1) * v

    def eval_turn(self, x_turn: Fraction) -> Fraction:
        x = _frac_part(x_turn)
        return self.eval_u(x * Fraction(self.N, 1))

    def eval_normalized_turn(self, x_turn: Fraction) -> Fraction:
        return self.eval_turn(x_turn) / Fraction(self.amplitude, 1)


@dataclass(frozen=True)
class ArctanTable:
    """
    Lookup table for arctan(x) where the input ratio x is in [0, 1].
    The last element of the table corresponds to an input ratio of 1.0,
    and its output implicitly represents pi/4 (1/8 turn).
    """
    values: Tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.values) < 2:
            raise ValueError("Table must have at least 2 elements")
        if self.values[-1] == 0:
            raise ValueError("Last element cannot be 0 (represents pi/4)")

    def _eval_raw(self, r: Fraction) -> Fraction:
        """Evaluate ratio r in [0, 1] to raw table units."""
        L = len(self.values)
        u = r * Fraction(L - 1, 1)
        i = int(u)
        
        if i >= L - 1:
            return Fraction(self.values[-1], 1)
            
        t = u - Fraction(i, 1)
        v0 = Fraction(self.values[i], 1)
        v1 = Fraction(self.values[i + 1], 1)
        return v0 + t * (v1 - v0)

    def atan_turn(self, r: Fraction) -> Fraction:
        """arctan(r) returned in turns."""
        if r < 0:
            return -self.atan_turn(-r)
        
        # Argument reduction: arctan(x) = pi/2 - arctan(1/x) for x > 1
        if r > 1:
            return Fraction(1, 4) - self.atan_turn(Fraction(1, r))
        
        raw_val = self._eval_raw(r)
        
        # Scale to turns. values[-1] represents 1/8 turn.
        return raw_val / Fraction(self.values[-1] * 8, 1)

    def atan2_turn(self, y: Fraction, x: Fraction) -> Fraction:
        """atan2(y, x) returned in turns [-1/2, 1/2]."""
        if x > 0:
            return self.atan_turn(y / x)
        elif x < 0:
            if y >= 0:
                return Fraction(1, 2) + self.atan_turn(y / x)
            else:
                return Fraction(-1, 2) + self.atan_turn(y / x)
        else: # x == 0
            if y > 0:
                return Fraction(1, 4)
            elif y < 0:
                return Fraction(-1, 4)
            else:
                return Fraction(0, 1)