from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Tuple


def _mod_int(x: int, m: int) -> int:
    return x % m


def _frac_part(x: Fraction) -> Fraction:
    q = x.numerator // x.denominator
    return x - Fraction(q, 1)


@dataclass(frozen=True)
class OddPeriodicTable:
    """
    Odd periodic lookup table with sine-like symmetries, evaluated by linear interpolation
    between integer arguments, exactly as described around Fig. 5 and (3.34).:contentReference[oaicite:6]{index=6}

    The table is specified by its quarter-wave samples:
      quarter[i] = f(i) for i=0..N/4 (inclusive),
    where N is the full period in "grid units" (e.g. N=28 or 12).

    Evaluation:
      - reduce u mod N to [0,N)
      - odd symmetry around N/2 gives sign
      - mirror into [0,N/4]
      - linearly interpolate between integers
    """
    N: int
    quarter: Tuple[int, ...]  # length must be N/4 + 1

    def __post_init__(self) -> None:
        if self.N <= 0 or self.N % 4 != 0:
            raise ValueError("N must be positive and divisible by 4")
        if len(self.quarter) != self.N // 4 + 1:
            raise ValueError("quarter must have length N/4 + 1")

    def eval_u(self, u: Fraction) -> Fraction:
        """
        Evaluate at real argument u (in grid units), returning the table value (in table units).
        """
        # Reduce u mod N to [0, N)
        u0 = u - Fraction(self.N, 1) * Fraction((u.numerator // u.denominator) // self.N, 1)
        # The above uses floor(u) first; for safety do exact modulo via fractional part:
        # u = k + r, r in [0,1); but here u is in grid units. Better:
        # compute integer k=floor(u/N), then u0=u-kN.
        k = (u.numerator // u.denominator) // self.N
        u0 = u - Fraction(self.N * k, 1)

        # Map into [0, N)
        if u0 < 0:
            # ensure positivity
            k2 = (-u0.numerator // u0.denominator) // self.N + 1
            u0 = u0 + Fraction(self.N * k2, 1)

        # Odd symmetry about N/2: f(N - x) = -f(x)
        sign = 1
        if u0 > Fraction(self.N, 2):
            sign = -1
            u0 = Fraction(self.N, 1) - u0

        # Mirror into [0, N/4]: f(N/2 - x) = f(x)
        if u0 > Fraction(self.N, 4):
            u0 = Fraction(self.N, 2) - u0

        # Now u0 in [0, N/4]
        i = int(u0)  # floor
        if i >= self.N // 4:
            return Fraction(sign * self.quarter[self.N // 4], 1)

        t = u0 - i
        v0 = Fraction(self.quarter[i], 1)
        v1 = Fraction(self.quarter[i + 1], 1)
        v = v0 + t * (v1 - v0)
        return Fraction(sign, 1) * v

    def eval_turn(self, x_turn: Fraction) -> Fraction:
        """
        Evaluate at phase x in turns: u = N * x, then apply eval_u.
        """
        # reduce x mod 1
        x = _frac_part(x_turn)
        return self.eval_u(x * self.N)

    def asin_turn(self, y: Fraction) -> Fraction:
        """
        Inverse lookup: given table-unit y, return the phase in turns [-1/4, 1/4].
        Assumes the quarter table represents monotonically increasing values.
        """
        if y < 0:
            return -self.asin_turn(-y)
            
        v_max = Fraction(self.quarter[-1], 1)
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
        t = (y - y0) / (y1 - y0)
        
        # Grid index is lo + t. Turn fraction is (lo + t) / N.
        return (Fraction(lo, 1) + t) / Fraction(self.N, 1)

    def acos_turn(self, y: Fraction) -> Fraction:
        """arccos(y) in turns [0, 1/2]."""
        return Fraction(1, 4) - self.asin_turn(y)
