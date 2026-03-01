from __future__ import annotations
from datetime import date
from fractions import Fraction


def to_jdn(d: date) -> int:
    """Convert Gregorian date to Julian Day Number (JDN)."""
    y, m, day = d.year, d.month, d.day
    a = (14 - m) // 12
    y2 = y + 4800 - a
    m2 = m + 12 * a - 3
    jdn = day + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - y2 // 100 + y2 // 400 - 32045
    return jdn

def from_jdn(jdn: int) -> date:
    """Fliegel-Van Flandern inverse of to_jdn (Gregorian)."""
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + (m // 10)
    return date(year, month, day)

def year_decimal_approx(d: date) -> float:
    """Approximate decimal year as float: year + doy/span."""
    start = date(d.year, 1, 1)
    end = date(d.year + 1, 1, 1)
    doy = (d - start).days
    span = (end - start).days
    return d.year + doy / span


def year_decimal_fraction(d: date) -> Fraction:
    """Decimal year as Fraction: year + doy/span."""
    start = date(d.year, 1, 1)
    end = date(d.year + 1, 1, 1)
    doy = (d - start).days
    span = (end - start).days
    return Fraction(d.year, 1) + Fraction(doy, span)

def k_from_epoch_jd(m0: float | Fraction) -> int:
    """
    Derives the absolute Meeus lunation index k from an epoch's Mean New Moon JD.
    """
    # 2451550.09766 is the exact JD of the Meeus k=0 mean new moon.
    # 29.530588861 is the mean synodic month length.
    return round((float(m0) - 2451550.09766) / 29.530588861)
