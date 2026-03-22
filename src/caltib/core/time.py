from __future__ import annotations
from datetime import date
from fractions import Fraction
from typing import Tuple

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

def m0_from_k(k: int) -> Fraction:
    """
    Derives the exact epoch Mean New Moon JD (m0) from a Meeus lunation index k.
    Evaluated purely in fractions to preserve determinism in rational engines.
    """
    base_jd = Fraction(245155009766, 100000)
    synodic_month = Fraction(29530588861, 1000000000)
    return base_jd + (k * synodic_month)

def y0_from_epoch_jd(m0: float | Fraction) -> int:
    """
    Infers the human calendar year (Y0) from an epoch's Julian Date.
    Because Tibetan epochs (m0) always fall in the Spring (Months 1-3),
    we can safely map the JD to the Gregorian/Julian year without edge-case rollover.
    Evaluated purely in fractions to preserve absolute determinism.
    """
    # J2000.0 (Jan 1, 2000) is exactly JD 2451545.
    # A mean Gregorian year is exactly 365.2425 days (146097 / 400).
    j2000_jd = Fraction(2451545, 1)
    greg_year = Fraction(146097, 400)
    
    y_frac = Fraction(2000, 1) + (Fraction(m0) - j2000_jd) / greg_year
    
    # Integer floor division safely handles both positive (CE) and negative (BCE) years
    return y_frac.numerator // y_frac.denominator

def advance_sun_to_epoch(
    s0_j2000: Fraction, 
    m0: Fraction, 
    m1: Fraction, 
    P: int, 
    Q: int
) -> Fraction:
    """
    Advances the J2000 Mean Sun to the epoch m0.
    Returns the true Mean Sun at the epoch (s_epoch).
    """
    j2000_jd = Fraction(2451545, 1)
    delta_days = m0 - j2000_jd
    sun_speed_per_day = Fraction(P, 12 * Q) / m1
    return (s0_j2000 + delta_days * sun_speed_per_day) % 1

def deduce_epoch_constants(s_epoch: Fraction, sgang1_deg: Fraction, P: int, Q: int) -> tuple[int, int, int]:
    """
    Deduces M0, beta_star, and tau from the unified discrete P/Q grid.
    Evaluated purely in fractions to preserve absolute determinism.
    """
    # 1. Start of Month 0
    d0_turns = (sgang1_deg - Fraction(30, 1)) / Fraction(360, 1)
    
    # 2. Continuous Phase
    alpha = Fraction(12, 1) * (s_epoch - d0_turns)
    
    # 3. Project alpha onto the discrete Q-grid
    alpha_Q = alpha * Fraction(Q, 1)
    
    # 4. Snap to the nearest integer grid point (Half-to-even)
    # This safely handles the r=Q rollover for BOTH the phase and the month!
    alpha_Q_int = round(alpha_Q)
    
    # 5. Extract the aligned interval (A0) and fractional phase (r)
    A0 = alpha_Q_int // Q
    r = alpha_Q_int % Q
    
    # 6. Calculate Civil Month
    M0 = (A0 % 12) + 1
    
    # 7. Calculate Phase Constants
    beta_star = (Q - 1 - r) % P
    tau = 0
    
    return M0, beta_star, tau