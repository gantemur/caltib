from __future__ import annotations

from dataclasses import dataclass
from math import fmod
from typing import Literal

import math


# ------------------------------------------------------------
# Units & helpers
# ------------------------------------------------------------

TAU = 6.283185307179586  # 2*pi, not used directly unless you want radians later

def frac01(x: float) -> float:
    """Return fractional part in [0,1)."""
    return x - float(int(x // 1))

def wrap_turn(x_turn: float) -> float:
    """Wrap turns to [0,1)."""
    return frac01(x_turn)

def wrap_deg(x_deg: float) -> float:
    """Wrap degrees to [0,360)."""
    # avoid slow % for huge values; fmod is fine
    y = fmod(x_deg, 360.0)
    if y < 0:
        y += 360.0
    return y

def wrap180(deg: float) -> float:
    """Wraps an angle in degrees to the range [-180.0, 180.0)."""
    return (deg + 180.0) % 360.0 - 180.0

def deg_to_turn(deg: float) -> float:
    return deg / 360.0

def turn_to_deg(turn: float) -> float:
    return 360.0 * turn

def arcsec_to_deg(arcsec: float) -> float:
    return arcsec / 3600.0

def arcsec_to_turn(arcsec: float) -> float:
    return arcsec_to_deg(arcsec) / 360.0

def arcsec_to_rad(arcsec: float) -> float:
    return math.radians(arcsec_to_deg(arcsec))

# ------------------------------------------------------------
# Time variable (TT)
# ------------------------------------------------------------

J2000_TT = 2451545.0  # JD(TT) at J2000.0


def T_centuries(jd_tt: float) -> float:
    """Julian centuries from J2000.0 in TT."""
    return (jd_tt - J2000_TT) / 36525.0


# ------------------------------------------------------------
# Mean periods & secular trends (days)
# Use Laskar-style expressions (good over millennia around J2000).
# ------------------------------------------------------------

def tropical_year_days(T: float) -> float:
    """
    Mean tropical year length in ephemeris days (86400 SI seconds), Laskar-style.

    Matches the commonly cited polynomial:
      365.2421896698 - 6.15359e-6 T - 7.29e-10 T^2 + 2.64e-10 T^3
    with T in Julian centuries from J2000.0.
    """
    return (
        365.2421896698
        - 6.15359e-6 * T
        - 7.29e-10 * (T * T)
        + 2.64e-10 * (T * T * T)
    )

def synodic_month_days(T: float) -> float:
    """
    Mean synodic month length in days.

    Uses the ELP2000/Meeus polynomial for strict consistency with 
    the fundamental argument D (mean elongation):
      29.5305888531 + 2.1621e-7 T - 3.64e-10 T^2
    """
    return 29.5305888531 + 2.1621e-7 * T - 3.64e-10 * (T * T)


def anomalistic_month_days(T: float) -> float:
    """
    Mean anomalistic month length in days.
    
    Uses the ELP2000/Meeus polynomial for consistency with 
    the fundamental argument M' (Moon's mean anomaly):
      27.554549878 - 1.0092e-6 T - 3.48e-9 T^2
    """
    return 27.554549878 - 1.0092e-6 * T - 3.48e-9 * (T * T)


def anomalistic_year_days(T: float) -> float:
    """
    Mean anomalistic year length in days.

    Uses the standard Laskar/Meeus polynomial for consistency with 
    the fundamental argument M (Sun's mean anomaly):
      365.259635864 + 3.04e-6 T + 1.52e-8 T^2
    """
    return 365.259635864 + 3.04e-6 * T + 1.52e-8 * (T * T)


# ------------------------------------------------------------
# Fundamental arguments (Meeus / ELP2000-style; degrees)
# We expose as turns and degrees.
# ------------------------------------------------------------

@dataclass(frozen=True)
class FundamentalArgs:
    """Fundamental arguments in turns and degrees."""
    Lp_turn: float
    D_turn: float
    M_turn: float
    Mp_turn: float
    F_turn: float
    Omega_turn: float

    @property
    def Lp_deg(self) -> float: return turn_to_deg(self.Lp_turn)
    @property
    def D_deg(self) -> float: return turn_to_deg(self.D_turn)
    @property
    def M_deg(self) -> float: return turn_to_deg(self.M_turn)
    @property
    def Mp_deg(self) -> float: return turn_to_deg(self.Mp_turn)
    @property
    def F_deg(self) -> float: return turn_to_deg(self.F_turn)
    @property
    def Omega_deg(self) -> float: return turn_to_deg(self.Omega_turn)


def fundamental_args(T: float) -> FundamentalArgs:
    """
    Fundamental arguments (mean elements) in turns, wrapped to [0,1).

    Coefficients match the standard Meeus/ELP-style polynomials:
      L' = 218.3164477 + 481267.88123421 T - 0.0015786 T^2 + T^3/538841 - T^4/65194000
      D  = 297.8501921 + 445267.1114034  T - 0.0018819 T^2 + T^3/545868  - T^4/113065000
      M  = 357.5291092 + 35999.0502909  T - 0.0001536 T^2 + T^3/24490000
      M' = 134.9633964 + 477198.8675055 T + 0.0087414 T^2 + T^3/69699   - T^4/14712000
      F  = 93.2720950  + 483202.0175233 T - 0.0036539 T^2 - T^3/3526000 + T^4/863310000

    (The exact higher-order terms are usually negligible for your L1–L5 target,
    but included here since you asked for “more accurate” fundamentals.)
    """
    T2 = T * T
    T3 = T2 * T
    T4 = T2 * T2

    Lp = (
        218.3164477
        + 481267.88123421 * T
        - 0.0015786 * T2
        + (T3 / 538841.0)
        - (T4 / 65194000.0)
    )
    D = (
        297.8501921
        + 445267.1114034 * T
        - 0.0018819 * T2
        + (T3 / 545868.0)
        - (T4 / 113065000.0)
    )
    M = (
        357.5291092
        + 35999.0502909 * T
        - 0.0001536 * T2
        + (T3 / 24490000.0)
    )
    Mp = (
        134.9633964
        + 477198.8675055 * T
        + 0.0087414 * T2
        + (T3 / 69699.0)
        - (T4 / 14712000.0)
    )
    F = (
        93.2720950
        + 483202.0175233 * T
        - 0.0036539 * T2
        - (T3 / 3526000.0)
        + (T4 / 863310000.0)
    )

    # Lunar ascending node longitude Ω (Meeus-style)
    # Often given as:
    #   Ω = 125.04452 - 1934.136261 T + 0.0020708 T^2 + T^3/450000
    Omega = 125.04452 - 1934.136261 * T + 0.0020708 * T2 + (T3 / 450000.0)

    return FundamentalArgs(
        Lp_turn=wrap_turn(deg_to_turn(Lp)),
        D_turn=wrap_turn(deg_to_turn(D)),
        M_turn=wrap_turn(deg_to_turn(M)),
        Mp_turn=wrap_turn(deg_to_turn(Mp)),
        F_turn=wrap_turn(deg_to_turn(F)),
        Omega_turn=wrap_turn(deg_to_turn(Omega)),
    )


# ------------------------------------------------------------
# Mean obliquity epsilon (turns or degrees)
# ------------------------------------------------------------

def mean_obliquity_deg(T: float, model: Literal["iau2000", "iau1980"] = "iau2000") -> float:
    """
    Mean obliquity of the ecliptic (degrees).

    - 'iau2000' (often cited IAU2000/2006 form):
        eps = 84381.406"
            - 46.836769"T - 0.0001831"T^2 + 0.00200340"T^3
            - 0.000000576"T^4 - 0.0000000434"T^5
    - 'iau1980' (Lieske/IAU1980 cubic seen in your screenshot):
        eps = 23°26'21.448" - 46.8150"T - 0.00059"T^2 + 0.001813"T^3
    """
    if model == "iau2000":
        T2 = T * T
        T3 = T2 * T
        T4 = T2 * T2
        T5 = T4 * T
        eps_arcsec = (
            84381.406
            - 46.836769 * T
            - 0.0001831 * T2
            + 0.00200340 * T3
            - 0.000000576 * T4
            - 0.0000000434 * T5
        )
        return arcsec_to_deg(eps_arcsec)

    if model == "iau1980":
        # 23°26'21.448" = 23 + 26/60 + 21.448/3600
        eps0 = 23.0 + 26.0 / 60.0 + 21.448 / 3600.0
        return eps0 - arcsec_to_deg(46.8150 * T + 0.00059 * (T * T) - 0.001813 * (T * T * T))

    raise ValueError("model must be one of: iau2000, iau1980")


def mean_obliquity_turn(T: float, model: Literal["iau2000", "iau1980"] = "iau2000") -> float:
    return deg_to_turn(mean_obliquity_deg(T, model=model))


# ------------------------------------------------------------
# Sun mean elements (Meeus-style)
# ------------------------------------------------------------

@dataclass(frozen=True)
class SolarMean:
    L0_turn: float  # mean longitude of Sun
    M_turn: float   # mean anomaly of Sun

    @property
    def L0_deg(self) -> float: return turn_to_deg(self.L0_turn)
    @property
    def M_deg(self) -> float: return turn_to_deg(self.M_turn)


def solar_mean_elements(T: float) -> SolarMean:
    """
    Meeus-style geometric mean longitude L0 and mean anomaly M (degrees -> turns).
    """
    T2 = T * T
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T2
    M = 357.52911 + 35999.05029 * T - 0.0001537 * T2
    return SolarMean(
        L0_turn=wrap_turn(deg_to_turn(L0)),
        M_turn=wrap_turn(deg_to_turn(M)),
    )


# ------------------------------------------------------------
# Mean new moon (Meeus mean phases)
# ------------------------------------------------------------

def jde_mean_new_moon(k: float) -> float:
    """
    Mean Julian Ephemeris Day (TT) of the k-th new moon relative to 2000.

    Commonly cited Meeus mean-phase polynomial:
      JDE = 2451550.09766 + 29.530588861 k
            + 0.00015437 T^2 - 0.000000150 T^3 + 0.00000000073 T^4,
      T = k / 1236.85.
    """
    T = k / 1236.85
    T2 = T * T
    T3 = T2 * T
    T4 = T2 * T2
    return (
        2451550.09766
        + 29.530588861 * k
        + 0.00015437 * T2
        - 0.000000150 * T3
        + 0.00000000073 * T4
    )

# ------------------------------------------------------------
# Eccentricity factor
# ------------------------------------------------------------

def eccentricity_factor(T: float) -> float:
    """
    Eccentricity factor E for the Earth's orbit.
    Used to scale analytical lunar perturbations that depend on 
    the Sun's mean anomaly.
    """
    return 1.0 - 0.002516 * T - 0.0000074 * (T * T)


# ------------------------------------------------------------
# Precession matrix
# ------------------------------------------------------------

def matrix_eq_j2000_to_ecl_date(T: float) -> tuple[tuple[float, ...], ...]:
    """
    Computes the rigorous 3x3 rotation matrix to transform a vector from 
    the Equatorial J2000 frame (ICRF) to the Mean Ecliptic of Date.
    """
    # 1. IAU 1976 Equatorial Precession Angles
    zeta = arcsec_to_rad(2306.2181 * T + 0.30188 * (T**2) + 0.017998 * (T**3))
    z    = arcsec_to_rad(2306.2181 * T + 1.09468 * (T**2) + 0.018203 * (T**3))
    theta= arcsec_to_rad(2004.3109 * T - 0.42665 * (T**2) - 0.041833 * (T**3))

    # 2. Obliquity of Date
    eps_date = math.radians(mean_obliquity_deg(T, model="iau2000"))

    # Matrix multiplication helper
    def matmul(A, B):
        return tuple(
            tuple(sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3))
            for i in range(3)
        )

    # Rotation matrices (Standard passive coordinate rotations)
    def R_x(a):
        c, s = math.cos(a), math.sin(a)
        return ((1, 0, 0), (0, c, s), (0, -s, c))

    def R_y(a):
        c, s = math.cos(a), math.sin(a)
        return ((c, 0, -s), (0, 1, 0), (s, 0, c))

    def R_z(a):
        c, s = math.cos(a), math.sin(a)
        return ((c, s, 0), (-s, c, 0), (0, 0, 1))

    # 3. Transform: Eq J2000 -> Eq Date -> Ecl Date
    eq_precession = matmul(R_z(-z), matmul(R_y(theta), R_z(-zeta)))
    
    # CRITICAL FIX: The rotation to the ecliptic requires a positive epsilon
    eq_to_ecl_date = R_x(eps_date) 

    return matmul(eq_to_ecl_date, eq_precession)

def apply_matrix(M: tuple[tuple[float, ...], ...], v: tuple[float, float, float]) -> tuple[float, float, float]:
    """Applies a 3x3 matrix to a 3D vector."""
    return (
        M[0][0]*v[0] + M[0][1]*v[1] + M[0][2]*v[2],
        M[1][0]*v[0] + M[1][1]*v[1] + M[1][2]*v[2],
        M[2][0]*v[0] + M[2][1]*v[1] + M[2][2]*v[2]
    )

# ============================================================
# Convenience wrappers that accept JD(TT)
# ============================================================

def tropical_year_days_jd(jd_tt: float) -> float:
    return tropical_year_days(T_centuries(jd_tt))


def synodic_month_days_jd(jd_tt: float) -> float:
    return synodic_month_days(T_centuries(jd_tt))


def anomalistic_month_days_jd(jd_tt: float) -> float:
    return anomalistic_month_days(T_centuries(jd_tt))


def anomalistic_year_days_jd(jd_tt: float) -> float:
    return anomalistic_year_days(T_centuries(jd_tt))


def fundamental_args_jd(jd_tt: float) -> FundamentalArgs:
    return fundamental_args(T_centuries(jd_tt))


def mean_obliquity_deg_jd(jd_tt: float, model: Literal["iau2000", "iau1980"] = "iau2000") -> float:
    return mean_obliquity_deg(T_centuries(jd_tt), model=model)


def solar_mean_elements_jd(jd_tt: float) -> SolarMean:
    return solar_mean_elements(T_centuries(jd_tt))
