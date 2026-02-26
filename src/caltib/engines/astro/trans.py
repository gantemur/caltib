from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Protocol, Tuple

# Turn constants
ONE = Fraction(1, 1)
HALF = Fraction(1, 2)
QUARTER = Fraction(1, 4)

class SinAcosTurnProvider(Protocol):
    def sin_turn(self, x_turn): ...
    def asin_turn(self, y): ...
    def acos_turn(self, y): ...

@dataclass(frozen=True)
class QuarterSineTableTurn:
    """sin(theta) samples on theta ∈ [0, 1/4] turn."""
    step_turn: Fraction
    values: Tuple[Fraction, ...]  # monotone 0..1

def wrap1(x: Fraction) -> Fraction:
    k = x.numerator // x.denominator
    return x - Fraction(k, 1)

def reduce_quadrant_turn(x: Fraction) -> tuple[int, Fraction]:
    x = wrap1(x)
    if x < QUARTER:
        return 0, x
    if x < HALF:
        return 1, HALF - x
    if x < HALF + QUARTER:
        return 2, x - HALF
    return 3, ONE - x

def lerp(a: Fraction, b: Fraction, t: Fraction) -> Fraction:
    return a + (b - a) * t

def sin_quarter_turn(tab: QuarterSineTableTurn, theta: Fraction) -> Fraction:
    step = tab.step_turn
    i = int(theta / step)
    i = max(0, min(i, len(tab.values) - 2))
    t = (theta - step * i) / step
    return lerp(tab.values[i], tab.values[i+1], t)

def asin_quarter_inverse_turn(tab: QuarterSineTableTurn, y: Fraction) -> Fraction:
    if y <= tab.values[0]:
        return Fraction(0, 1)
    if y >= tab.values[-1]:
        return QUARTER
    vals = tab.values
    lo, hi = 0, len(vals) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if vals[mid] <= y:
            lo = mid
        else:
            hi = mid
    y0, y1 = vals[lo], vals[lo+1]
    t = (y - y0) / (y1 - y0)
    return tab.step_turn * lo + tab.step_turn * t

class TransTurnTable(SinAcosTurnProvider):
    """Table trig in turns: sin/asin/acos via quarter-sine table and inverse lookup."""
    def __init__(self, tab: QuarterSineTableTurn):
        self.tab = tab

    def sin_turn(self, x_turn: Fraction) -> Fraction:
        q, th = reduce_quadrant_turn(x_turn)
        s = sin_quarter_turn(self.tab, th)
        return s if q in (0, 1) else -s

    def asin_turn(self, y: Fraction) -> Fraction:
        if y < 0:
            return -self.asin_turn(-y)
        if y > 1:
            y = Fraction(1, 1)
        return asin_quarter_inverse_turn(self.tab, y)

    def acos_turn(self, y: Fraction) -> Fraction:
        return QUARTER - self.asin_turn(y)

    def cos_turn(self, x_turn: Fraction) -> Fraction:
        # cos(x) = sin(x + 1/4)
        return self.sin_turn(x_turn + QUARTER)

# Placeholder polynomial backend (L4/L5): to be filled with minimax + invsqrt + atan as needed.
class TransPolyTurn:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Polynomial transcendentals not implemented in skeleton.")
