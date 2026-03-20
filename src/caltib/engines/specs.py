from __future__ import annotations

from typing import Tuple, Any, Optional
from fractions import Fraction
import math

# 1. New Core Types
from caltib.core.types import EngineId, CalendarSpec, LocationSpec
from caltib.core.time import k_from_epoch_jd

# 2. New Pure Data Parameters
from caltib.engines.arithmetic_month import ArithmeticMonthParams
from caltib.engines.rational_month import RationalMonthParams
from caltib.engines.arithmetic_day import ArithmeticDayParams
from caltib.engines.trad_day import TraditionalDayParams
from caltib.engines.rational_day import RationalDayParams
from caltib.engines.fp_day import FloatDayParams
from caltib.engines.trad_planets import TraditionalPlanetsParams

# 3. Physics / Astro dependencies
from caltib.engines.astro.affine_series import TermDef, FundArg, make_funds, compile_affine_terms
from caltib.engines.astro.float_series import build_collapsed_terms, FloatFundArg, FloatTermDef
from caltib.engines.astro.deltat import DeltaTDef, ConstantDeltaTDef, QuadraticDeltaTDef, FloatDeltaTDef
from caltib.engines.astro.sunrise import SunriseDef, ConstantSunriseDef, SphericalSunriseDef, TrueSunriseDef, FloatSunriseDef

# ============================================================
# TRADITIONAL CONSTANTS
# ============================================================

# Shared “Tibetan” month ratio in paper convention p<q:
#   P=65, Q=67, ell=2
P_TIB = 65
Q_TIB = 67

# Shared mean motions for the Tibetan traditions
M1_TIB = Fraction(167025, 5656)
S1_TIB = Fraction(65, 804)
A1_TIB = Fraction(253, 3528)

# Karana mean motions
M1_KAR = Fraction(10631, 360)
S1_KAR = Fraction(1277, 15795)
A1_KAR = Fraction(253, 3528)

A2_STD = Fraction(1, 28)

# Shared traditional tables (Appendix A style)
MOON_TAB_QUARTER = (0, 5, 10, 15, 19, 22, 24, 25)   # length 8 = 28/4+1
SUN_TAB_QUARTER  = (0, 6, 10, 11)                   # length 4 = 12/4+1


# ============================================================
# RATIONAL REFORM CONSTANTS
# ============================================================

JD_J2000 = Fraction(2451545, 1)

# Shared month ratio in paper convention p<q:
#   P=1336, Q=1377, ell=41
P_NEW = 1336
Q_NEW = 1377

# ============================================================================
# SET 1: THE OPTIMIZED RATES (Default)
# ============================================================================
# Derived from highly optimized rational approximations of the Meeus per-lunation 
# rates. This set mathematically locks the continuous day-engine to the exact 
# same foundational constants as the discrete month-engine, ensuring perfect 
# internal consistency (no "tearing" between months and days over millennia).

OPTIMIZED_PER_LUNATION_RATES = {
    "M1": Fraction(283346, 9595),   # Synodic month (days)
    "S1": Fraction(334, 4131),      # Sun longitude (turns)
    "A1": Fraction(4583, 63907),    # Moon anomaly (turns)
    "R1": Fraction(1689, 20891),    # Sun anomaly (turns, "sigma")
    "F1": Fraction(324, 3803),      # Moon latitude (turns)
}

_OPT = OPTIMIZED_PER_LUNATION_RATES

FUND_RATES_OPTIMIZED = {
    "S":  _OPT["S1"] / _OPT["M1"],
    "D":  Fraction(1, 1) / _OPT["M1"],
    "M":  _OPT["R1"] / _OPT["M1"],
    "Mp": (Fraction(1, 1) + _OPT["A1"]) / _OPT["M1"],
    "F":  (Fraction(1, 1) + _OPT["F1"]) / _OPT["M1"],
    "M1": _OPT["M1"],
    "S1": _OPT["S1"]
}

# ============================================================================
# SET 2: THE EXACT J2000 HARMONIC RATES (Astronomical Pure)
# ============================================================================
# Evaluated directly from the exact J2000 floating-point baseline.
# Denominators are strictly composed of harmonic primes (487, 2, 3, 5).
# Users prioritizing absolute astronomical precision over discrete month 
# synchronization can inject this set into the calendar engines.

_MEAN = {
    "S":  Fraction(3600076983,  1314900000000),   
    "D":  Fraction(4452671114,  131490000000),    
}

FUND_RATES_EXACT = {
    "S":  _MEAN["S"],   
    "D":  _MEAN["D"],    
    "M":  Fraction(3599905029,  1314900000000),   
    "Mp": Fraction(47719886751, 1314900000000),   
    "F":  Fraction(48320201752, 1314900000000),
    "M1": Fraction(1, 1) / _MEAN["D"],
    "S1": _MEAN["S"] / _MEAN["D"]
}

# Default choice for the standard L1-L5 specs.
FUND_RATES = FUND_RATES_OPTIMIZED

# ============================================================================
# PRECONDITIONER (For the Decoupled Solver)
# ============================================================================
# Used in L3-L5 to prevent LCM inflation during the Picard iteration loop.
# This acts solely as an iteration multiplier. Because secular drift changes the 
# true M1 over centuries, ultra-high precision here is mathematically unnecessary. 
# Fraction(295306, 10000) provides ~29.5306 days, guaranteeing sub-second 
# convergence in 3 iterations while keeping the LCM pool microscopic (2^4 * 5^4).
M1_PREC = Fraction(295306, 10000)

# Constant Delta T: 55.3s in 1987, 63.8s in 2000, 69.2s in early 2026
DT_CONSTANT_DEF = ConstantDeltaTDef(Fraction(69, 1))
# Quadratic Delta T: -20 + 32 * ((year - 1820) / 100)^2
DT_QUADRATIC_DEF = QuadraticDeltaTDef(
    a=Fraction(-20, 1), 
    b=Fraction(0, 1), 
    c=Fraction(32, 1), 
    y0=Fraction(1820, 1)
)

# New tables
SINE_TAB_QUARTER = (0, 228, 444, 638, 801, 923, 998, 1024)
# Max interpolation error: 0.006408 (0.6408% of amplitude)
ATAN_TAB_VALUES  = (0, 185, 363, 528, 677, 809, 924, 1024)
# Max interpolation error: 0.001956 (0.1956% of amplitude)

# Constant sunrise (1/4 for 6:00am, 89/360 for 5:56am)
DAWN_600AM_DEF = ConstantSunriseDef(Fraction(1, 4))
DAWN_556AM_DEF = ConstantSunriseDef(Fraction(89, 360))

# Spherical sunrise constants (h0 = -50 arcminutes, eps = 23° 26' 20.00")
DAWN_SPHERICAL_DEF = SphericalSunriseDef(
    h0_turn=Fraction(-1, 432), 
    eps_turn=Fraction(4219, 64800), # Base-60 harmonious, 1.4" error
    sine_tab_quarter=SINE_TAB_QUARTER,
    day_fraction=Fraction(89, 360),
)

# True sunrise constants
DAWN_TRUE_DEF = TrueSunriseDef(
    h0_turn=Fraction(-1, 432), 
    eps_turn=Fraction(4219, 64800),
    sine_tab_quarter=SINE_TAB_QUARTER,
    atan_tab_values=ATAN_TAB_VALUES,
    day_fraction=Fraction(89, 360)
)

# ============================================================
# APPROXIMATE LOCATIONS (For Traditional Arithmetic Engines)
# ============================================================

LOC_TIBET_APPROX = LocationSpec(
    name="Tibetan Plateau (Approximate)",
    lon_turn=Fraction(91, 360),      # ~91° E
    lat_turn=None,
    elev_m=None
)

LOC_MONGOLIA_APPROX = LocationSpec(
    name="Mongolian Plateau (Approximate)",
    lon_turn=Fraction(105, 360),     # ~105° E
    lat_turn=None,
    elev_m=None
)

LOC_BHUTAN_APPROX = LocationSpec(
    name="Bhutan (Approximate)",
    lon_turn=Fraction(90, 360),      # ~90° E
    lat_turn=None,
    elev_m=None
)

# ============================================================
# PRECISE LOCATIONS (For Rational / Float Engines)
# ============================================================

LOC_LHASA = LocationSpec(
    name="Lhasa",
    lat_turn=Fraction(2965, 36000),    # 29.65° N
    lon_turn=Fraction(9110, 36000),    # 91.10° E
    elev_m=Fraction(3650, 1)
)

LOC_ULAANBAATAR = LocationSpec(
    name="Ulaanbaatar",
    lat_turn=Fraction(4792, 36000),    # 47.92° N
    lon_turn=Fraction(10692, 36000),   # 106.92° E
    elev_m=Fraction(1350, 1)
)

LOC_THIMPHU = LocationSpec(
    name="Thimphu",
    lat_turn=Fraction(2747, 36000),    # 27.47° N
    lon_turn=Fraction(8964, 36000),    # 89.64° E
    elev_m=Fraction(2320, 1)
)

LOC_HOHHOT = LocationSpec(
    name="Hohhot",
    lat_turn=Fraction(4082, 36000),    # 40.82° N
    lon_turn=Fraction(11167, 36000),   # 111.67° E
    elev_m=Fraction(1040, 1)
)

LOC_BEIJING = LocationSpec(
    name="Beijing",
    lat_turn=Fraction(3990, 36000),    # 39.90° N
    lon_turn=Fraction(11640, 36000),   # 116.40° E
    elev_m=Fraction(44, 1)
)

LOC_ULAN_UDE = LocationSpec(
    name="Ulan-Ude",
    lat_turn=Fraction(5183, 36000),    # 51.83° N
    lon_turn=Fraction(10758, 36000),   # 107.58° E
    elev_m=Fraction(500, 1)
)

LOC_ELISTA = LocationSpec(
    name="Elista",
    lat_turn=Fraction(4630, 36000),    # 46.30° N
    lon_turn=Fraction(4426, 36000),    # 44.26° E
    elev_m=Fraction(120, 1)
)

LOC_MONTREAL = LocationSpec(
    name="Montreal",
    lat_turn=Fraction(4550, 36000),    # 45.50° N
    lon_turn=Fraction(-7357, 36000),   # 73.57° W
    elev_m=Fraction(30, 1)
)

# ============================================================
# Data constants for attributes and calendar specifications.
# ============================================================

# Standard 0-indexed arrays for modular lookups
ANIMALS: Tuple[str, ...] = ("Mouse", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Sheep", "Monkey", "Bird", "Dog", "Pig")
ELEMENTS: Tuple[str, ...] = ("Wood", "Fire", "Earth", "Iron", "Water")
GENDERS: Tuple[str, ...] = ("Male", "Female") # 0 = Yang (Pho), 1 = Yin (Mo)
TRIGRAMS: Tuple[str, ...] = ("Li", "Khon", "Dwa", "Khen", "Kham", "Gin", "Zin", "Zon")
DIRECTIONS: Tuple[str, ...] = ("S", "SW", "W", "NW", "N", "NE", "E", "SE")

# Mewa numbers are 1-9 mathematically. This array matches Mewa 1 to index 0.
MEWA_COLORS: Tuple[str, ...] = ("White", "Black", "Blue", "Green", "Yellow", "White", "Red", "White", "Red")

# ============================================================
# Tables and constants for traditional planets.
# ============================================================

PLANETS = ("mercury", "venus", "mars", "jupiter", "saturn")

# Shared across all Tibetan traditions (Table 12 & 13 from [Janson])
TAB_MANDA = {
    "mercury": (0, 10, 17, 20),
    "venus": (0, 5, 9, 10),
    "mars": (0, 25, 43, 50),
    "jupiter": (0, 11, 20, 23),
    "saturn": (0, 22, 37, 43)
}

TAB_SIGHRA = {
    "mercury": (0, 16, 32, 47, 61, 74, 85, 92, 97, 97, 93, 82, 62, 34),
    "venus": (0, 25, 50, 75, 99, 123, 145, 167, 185, 200, 208, 202, 172, 83),
    "mars": (0, 24, 47, 70, 93, 114, 135, 153, 168, 179, 182, 171, 133, 53),
    "jupiter": (0, 10, 20, 29, 37, 43, 49, 51, 52, 49, 43, 34, 23, 7),
    "saturn": (0, 6, 11, 16, 20, 24, 26, 28, 28, 26, 22, 17, 11, 3)
}

#Base Rahu rate, turns in lunar-days
RAHU_LUN = Fraction(-30, 6900)

# Kālacakra specific rates (turns in solar days)
P_RATES = {
        "mercury": Fraction(100, 8797),
        "venus": Fraction(10, 2247),
        "mars": Fraction(1, 687),
        "jupiter": Fraction(1, 4332),
        "saturn": Fraction(1, 10766),
        "sun": S1_TIB / M1_TIB,   
        "rahu": RAHU_LUN / M1_TIB
    }

BIRTH_SIGNS = {
    "mercury": Fraction(11, 18),
    "venus": Fraction(2, 9),
    "mars": Fraction(19, 54),
    "jupiter": Fraction(4, 9),
    "saturn": Fraction(2, 3)
}


# ============================================================
# Float engine constants
# ============================================================

# ============================================================
# Absolute J2000.0 Astronomical Constants (Meeus / JPL)
# Evaluated strictly as (Degrees / 360) and (Degrees / 360 / Days)
# ============================================================

# J2000.0 Linear Phases (c0 = intercept, c1 = turns/day)
J2000_FUNDS = {
    "S":  FloatFundArg(c0=280.46646 / 360.0, c1=36000.76983 / 360.0 / 36525.0),
    "D":  FloatFundArg(c0=297.85020 / 360.0, c1=445267.11140 / 360.0 / 36525.0),
    "M":  FloatFundArg(c0=357.52911 / 360.0, c1=35999.05029 / 360.0 / 36525.0),
    "Mp": FloatFundArg(c0=134.96340 / 360.0, c1=477198.86751 / 360.0 / 36525.0),
    "F":  FloatFundArg(c0=93.27209 / 360.0,  c1=483202.01752 / 360.0 / 36525.0)
}

# Coefficients for sine approximation (Input: turns, Output: amplitude)
# Domain: [0, 0.25]
SINE_POLY_5_COEFFS = (
    float.fromhex("0x1.9204e06298ee5p+2"),   # c1
    float.fromhex("-0x1.4911303618770p+5"),  # c3
    float.fromhex("0x1.28af31a2c633ep+6"),   # c5
)

SINE_POLY_7_COEFFS = (
    float.fromhex("0x1.921f7b2a8caaap+2"),   # c1
    float.fromhex("-0x1.4ab430edb388ep+5"),  # c3
    float.fromhex("0x1.457ce7f0c0b57p+6"),   # c5
    float.fromhex("-0x1.1d438fda450c4p+6"),  # c7
)

# Coefficients for arctangent approximation (Input: ratio, Output: turns)
# Domain: [0, 1.0]
ATAN_POLY_5_COEFFS = (
    float.fromhex("0x1.4482618478638p-3"),   # c1
    float.fromhex("-0x1.7d119bc1df0c0p-5"),  # c3
    float.fromhex("0x1.b0f17a7c7df9bp-7"),   # c5
)

ATAN_POLY_7_COEFFS = (
    float.fromhex("0x1.45befa84fe3f6p-3"),   # c1
    float.fromhex("-0x1.a431f6c59c177p-5"),  # c3
    float.fromhex("0x1.849c4c475fd16p-6"),   # c5
    float.fromhex("-0x1.aa34c2cb444dbp-8"),  # c7
)

# Float sunrise model
DAWN_FLOAT_DEF = FloatSunriseDef(
    h0_turn=float.fromhex("-0x1.2000000000000p-9"),  # -1/432
    eps_turn=float.fromhex("0x1.0aaaa0260481ap-4"),  # 2344/36000
    sine_poly_coeffs=SINE_POLY_5_COEFFS,
    atan_poly_coeffs=ATAN_POLY_5_COEFFS,
    day_fraction=float.fromhex("0x1.fa4fa4fa4fa50p-3") # 89/360 (5:56 AM)
)

# Quadratic Delta T: -20 + 32 * ((year - 1820) / 100)^2
DT_FLOAT_DEF = FloatDeltaTDef(
    a=-20.0,
    b=0.0,
    c=32.0,
    y0=1820.0
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def arith_month(
    *, 
    Y0: int = 1987, 
    M0: int = 3, 
    P: int = P_TIB, 
    Q: int = Q_TIB, 
    beta_star: int = 57,
    tau: int = 0,
    m0: Fraction,
    m1: Fraction = M1_TIB,
    s0: Fraction = Fraction(0, 1),
    sgang1_deg: Fraction = Fraction(307,1)
) -> ArithmeticMonthParams:
    return ArithmeticMonthParams(
        epoch_k=k_from_epoch_jd(m0),  # Deduce Day epoch_k directly from m0
        sgang1_deg=sgang1_deg,
        Y0=Y0, M0=M0, P=P, Q=Q, beta_star=beta_star, tau=tau,
        m0=m0, m1=m1, s0=s0
    )

def trad_day(
    *, 
    m0: Fraction, s0: Fraction, a0: Fraction, 
    m1: Fraction = M1_TIB, s1: Fraction = S1_TIB, a1: Fraction = A1_TIB, a2: Fraction = A2_STD, 
    location: LocationSpec = LOC_TIBET_APPROX
) -> TraditionalDayParams:
    return TraditionalDayParams(
        epoch_k=k_from_epoch_jd(m0),  # Deduce Day epoch_k directly from m0
        m0=m0, m1=m1, m2=m1 / 30,
        s0=s0, s1=s1, s2=s1 / 30,
        a0=a0, a1=a1, a2=a2,
        moon_tab_quarter=MOON_TAB_QUARTER,
        sun_tab_quarter=SUN_TAB_QUARTER,
        location=location        
    )

def rational_day(
    *,
    funds: dict[str, FundArg],
    location: LocationSpec = LOC_LHASA,
    solar_table: Tuple[Tuple[Any, ...], ...] = (),
    lunar_table: Tuple[Tuple[Any, ...], ...] = (),
    iterations: int = 1,
    delta_t: DeltaTDef = DT_CONSTANT_DEF,
    sunrise: SunriseDef = DAWN_600AM_DEF,
    moon_tab_quarter: Tuple[int, ...] = MOON_TAB_QUARTER,
    sun_tab_quarter: Tuple[int, ...] = SUN_TAB_QUARTER,
    invB_prec: Optional[Fraction] = None,
    C_sun: Fraction = Fraction(0,1), 
    C_elong: Fraction = Fraction(0,1),
    include_drift: bool = False
) -> RationalDayParams:
    
    # Compile the pure data TermDefs
    solar_terms = compile_affine_terms(
        funds=funds, keys=("D", "M", "Mp", "F"), rows=solar_table, include_drift=include_drift
    )
    lunar_terms = compile_affine_terms(
        funds=funds, keys=("D", "M", "Mp", "F"), rows=lunar_table, include_drift=include_drift
    )
    
    return RationalDayParams(
        epoch_k=k_from_epoch_jd(funds["m0"]),
        A_sun=funds["S"].c0, B_sun=funds["S"].c1, solar_terms=solar_terms,
        A_elong=funds["D"].c0, B_elong=funds["D"].c1, lunar_terms=lunar_terms,
        iterations=iterations, delta_t=delta_t, sunrise=sunrise, location=location,
        moon_tab_quarter=moon_tab_quarter, sun_tab_quarter=sun_tab_quarter,
        invB_elong_prec=invB_prec,
        C_sun=C_sun, C_elong=C_elong
    )

def fp_day(
    *,
    epoch_k: int,
    location: LocationSpec = LOC_LHASA,
    solar_table: Tuple[Tuple[float, ...], ...] = (),
    lunar_table: Tuple[Tuple[float, ...], ...] = (),
    iterations: int = 3,
    delta_t: FloatDeltaTDef = DT_FLOAT_DEF,
    sunrise: FloatSunriseDef = DAWN_FLOAT_DEF, 
    sine_poly_coeffs: Tuple[float, ...] = SINE_POLY_5_COEFFS,
    C_sun: float = 0.0, C_elong: float = 0.0,
    include_drift: bool = False
) -> FloatDayParams:
    """Builds pure-data FloatDayParams using exact J2000.0 astronomical constants."""
    
    # 1. Bulk-build the solar and lunar Fourier terms (Data tuples)
    # Unpack the returned (static_terms, dynamic_terms)
    solar_static, solar_dynamic = build_collapsed_terms(
        funds=J2000_FUNDS, keys=("D", "M", "Mp", "F"), rows=solar_table, 
        amp_scale=(1e-6 / 360.0), include_drift=include_drift
    )
    lunar_static, lunar_dynamic = build_collapsed_terms(
        funds=J2000_FUNDS, keys=("D", "M", "Mp", "F"), rows=lunar_table, 
        amp_scale=(1e-6 / 360.0), include_drift=include_drift
    )
    
    # 2. Build Elongation terms (Moon - Sun)
    # We must negate BOTH static and dynamic amplitudes (including amp1 drift!)
    neg_solar_static = tuple(
        FloatTermDef(amp=-t.amp, c0=t.c0, c1=t.c1, amp1=-t.amp1) for t in solar_static
    )
    neg_solar_dynamic = tuple(
        FloatTermDef(amp=-t.amp, c0=t.c0, c1=t.c1, amp1=-t.amp1) for t in solar_dynamic
    )
    
    elong_static = lunar_static + neg_solar_static
    elong_dynamic = lunar_dynamic + neg_solar_dynamic

    # 3. Return the fully configured, pure-data parameter object
    return FloatDayParams(
        epoch_k=epoch_k,
        location=location,
        A_sun=J2000_FUNDS["S"].c0, B_sun=J2000_FUNDS["S"].c1, C_sun=C_sun,
        solar_static=solar_static,     # <--- Updated
        solar_dynamic=solar_dynamic,   # <--- Updated
        A_elong=J2000_FUNDS["D"].c0, B_elong=J2000_FUNDS["D"].c1, C_elong=C_elong,
        elong_static=elong_static,     # <--- Updated
        elong_dynamic=elong_dynamic,   # <--- Updated
        iterations=iterations,
        delta_t=delta_t,
        sunrise=sunrise,
        sine_poly_coeffs=sine_poly_coeffs
    )

def rational_month(
    *,
    funds: dict[str, FundArg],
    solar_table: Tuple[Tuple[Any, ...], ...] = (),
    lunar_table: Tuple[Tuple[Any, ...], ...] = (),
    iterations: int = 1,
    moon_tab_quarter: Tuple[int, ...] = MOON_TAB_QUARTER,
    sun_tab_quarter: Tuple[int, ...] = SUN_TAB_QUARTER,
    Y0: int = 1987,
    M0: int = 3,
    sgang1_deg: Fraction = Fraction(307, 1),
    invB_prec: Optional[Fraction] = None,
    C_sun: Fraction = Fraction(0,1), 
    C_elong: Fraction = Fraction(0,1),
    include_drift: bool = False
) -> RationalMonthParams:

    # Compile the pure data TermDefs
    solar_terms = compile_affine_terms(
        funds=funds, keys=("D", "M", "Mp", "F"), rows=solar_table, include_drift=include_drift
    )
    lunar_terms = compile_affine_terms(
        funds=funds, keys=("D", "M", "Mp", "F"), rows=lunar_table, include_drift=include_drift
    )

    return RationalMonthParams(
        epoch_k=k_from_epoch_jd(funds["m0"]),
        A_sun=funds["S"].c0, B_sun=funds["S"].c1, C_sun=C_sun, solar_terms=solar_terms,
        A_elong=funds["D"].c0, B_elong=funds["D"].c1, C_elong=C_elong, lunar_terms=lunar_terms,
        iterations=iterations, 
        moon_tab_quarter=moon_tab_quarter, sun_tab_quarter=sun_tab_quarter,
        Y0=Y0, M0=M0, sgang1_deg=sgang1_deg,
        invB_elong_prec=invB_prec
    )

def arith_day(
    *,
    location: LocationSpec,
    m0_abs: Fraction | None = None,
    m0_loc: Fraction | None = None,
    s0: Fraction,
    s1: Fraction = S1_TIB,
    U: int = 11312,
    V: int = 11135,
    dawn_time: Fraction = Fraction(1, 4),  # 6:00 AM (1/4 of a day past midnight)
) -> ArithmeticDayParams:
    """Auto-computes delta_star phase shifts natively for either absolute or local m0."""
    
    # JD starts at noon (.0). To make floor() roll over at local dawn, 
    # we need to offset the fractional day. 
    # For 6:00 AM (dawn_time = 1/4), dawn_shift becomes 1/4 (0.25 days).
    dawn_shift = Fraction(1, 2) - dawn_time
    
    # Path 1: Initialized with absolute time
    if m0_loc is None and m0_abs is not None:
        m0_loc = m0_abs + location.lon_turn + dawn_shift
    
    # Path 2: Initialized with local time
    elif m0_abs is None and m0_loc is not None:
        m0_abs = m0_loc - location.lon_turn - dawn_shift
        
    else:
        raise ValueError("Must provide exactly one of m0_abs or m0_loc")

    # The civil day boundary is local, so delta_star MUST use local fractional time
    jdn_floor = m0_loc.numerator // m0_loc.denominator
    f_loc = m0_loc - Fraction(jdn_floor, 1)
    delta_star = math.floor(f_loc * U) - 1

    return ArithmeticDayParams(
        epoch_k=k_from_epoch_jd(m0_abs),
        location=location,
        U=U, V=V, delta_star=delta_star,
        m0_abs=m0_abs, m0_loc=m0_loc, s0=s0, s1=s1
    )
    
def trad_planets(
    *,
    m0: Fraction,           # Absolute Julian Day Epoch
    s0: Fraction,           # Epoch Mean Sun (at m0)
    pd0: dict[str, int],    # Elapsed days since planet was at 0 (pd0["rahu"] is Henning's rd0)
    p_rates=P_RATES,
    birth_signs=BIRTH_SIGNS,
    manda_tables=TAB_MANDA,
    sighra_tables=TAB_SIGHRA
) -> TraditionalPlanetsParams:
    """Builds the traditional planetary engine configuration for a given epoch."""
    
    # 1. Base civil epoch (integer Julian Day) which is the planetary epoch
    jd0 = Fraction(m0.numerator // m0.denominator, 1)
    
    # 2. The fractional time gap between the lunar epoch and planetary epoch
    dt_shift = m0 - jd0
    
    # 3. Calculate pure angular positions at m0
    rahu0_m0 = Fraction(-30 * pd0["rahu"], 6900) % 1
    
    # 4. Shift Sun and Rahu from m0 backwards to jd0!
    # This automatically derives Janson's D.9 constant from Henning's data.
    s0_jd0 = (s0 - p_rates["sun"] * dt_shift) % 1
    rahu0_jd0 = (rahu0_m0 - p_rates["rahu"] * dt_shift) % 1
    
    # 5. Build the unified p0 dictionary (all values now anchored to jd0)
    p0 = {
        k: Fraction(pd0[k], p_rates[k].denominator) for k in PLANETS
    }
    p0["sun"] = s0_jd0
    p0["rahu"] = rahu0_jd0
    
    return TraditionalPlanetsParams(
        epoch_k=k_from_epoch_jd(m0),
        jd0=jd0,
        m0=m0,
        p0=p0,
        p_rate=p_rates,
        birth_signs=birth_signs,
        manda_tables=manda_tables,
        sighra_tables=sighra_tables
    )

# ============================================================
# TRADITIONAL ENGINE SPECIFICATIONS
# ============================================================

# ------------------------------------------------------------
# PHUGPA (E1927)
# ------------------------------------------------------------
PHUGPA_E1927_M0 = Fraction(13715647089, 5656)
PHUGPA_E1927_S0 = Fraction(749,804)

PHUGPA_SPEC = CalendarSpec(
    id=EngineId("trad", "phugpa", "0.1"),
    month_params=arith_month(
        Y0=1927, beta_star=55, tau=48, 
        m0=PHUGPA_E1927_M0, s0=PHUGPA_E1927_S0,
        sgang1_deg=Fraction(308, 1)
    ),
    day_params=trad_day(
        m0=PHUGPA_E1927_M0,
        s0=PHUGPA_E1927_S0,
        a0=Fraction(1741,3528),
    ),
    planets_params=trad_planets(
        m0=PHUGPA_E1927_M0,
        s0=PHUGPA_E1927_S0,
        pd0={"mars": 157, "jupiter": 3964, "saturn": 6286, "mercury": 4639, "venus": 301, "rahu": 187}
    ),
    leap_labeling="first_is_leap",
    meta={"epoch": "E1927", "tradition": "phugpa"},
)

# ------------------------------------------------------------
# PHUGPA (E1987)
# ------------------------------------------------------------
PHUGPA_E1987_M0 = Fraction(1729968333, 707)
PHUGPA_E1987_S0 = Fraction(0, 1)

PHUGPA_E1987_SPEC = CalendarSpec(
    id=EngineId("trad", "phugpa", "0.1"),
    month_params=arith_month(
        Y0=1987, beta_star=0, tau=48, 
        m0=PHUGPA_E1987_M0, s0=PHUGPA_E1987_S0,
        sgang1_deg=Fraction(308, 1)
    ),
    day_params=trad_day(
        m0=PHUGPA_E1987_M0,
        s0=PHUGPA_E1987_S0,
        a0=Fraction(38, 49),
    ),
    planets_params=trad_planets(
        m0=PHUGPA_E1927_M0,
        s0=PHUGPA_E1927_S0,
        pd0={"mars": 157, "jupiter": 3964, "saturn": 6286, "mercury": 4639, "venus": 301, "rahu": 187}
    ),
    leap_labeling="first_is_leap",
    meta={"epoch": "E1987", "tradition": "phugpa"},
)

# ------------------------------------------------------------
# TSURPHU (E1852)
# ------------------------------------------------------------
TSURPHU_E1852_M0 = Fraction(18307100485903, 7635600)
TSURPHU_E1852_S0 = Fraction(23, 27135)

TSURPHU_SPEC = CalendarSpec(
    id=EngineId("trad", "tsurphu", "0.1"),
    month_params=arith_month(
        Y0=1852, beta_star=14, tau=0, 
        m0=TSURPHU_E1852_M0, s0=TSURPHU_E1852_S0,
        sgang1_deg=Fraction(307, 1)
    ),
    day_params=trad_day(
        m0=TSURPHU_E1852_M0,
        s0=TSURPHU_E1852_S0,
        a0=Fraction(1, 49),
    ),
    planets_params=trad_planets(
        m0=TSURPHU_E1852_M0,
        s0=TSURPHU_E1852_S0,
        pd0={"mars": 262, "jupiter": 2583, "saturn": 437, "mercury": 3003, "venus": 686, "rahu": 180}
    ),
    leap_labeling="first_is_leap",
    meta={"epoch": "E1852", "tradition": "tsurphu"},
)

# ------------------------------------------------------------
# MONGOL (E1747)
# ------------------------------------------------------------
MONGOL_E1747_M0 = Fraction(6671924839, 2828)
MONGOL_E1747_S0 = Fraction(397, 402)

MONGOL_SPEC = CalendarSpec(
    id=EngineId("trad", "mongol", "0.1"),
    month_params=arith_month(
        Y0=1747, beta_star=10, tau=46, 
        m0=MONGOL_E1747_M0, s0=MONGOL_E1747_S0,
        sgang1_deg=Fraction(308, 1)+Fraction(2, 3)
    ),
    day_params=trad_day(
        m0=MONGOL_E1747_M0,
        s0=MONGOL_E1747_S0,
        a0=Fraction(1523, 1764),
        location=LOC_MONGOLIA_APPROX
    ),
    planets_params=trad_planets(
        m0=MONGOL_E1747_M0,
        s0=MONGOL_E1747_S0,
        pd0={"mars": 375, "jupiter": 3213, "saturn": 5147, "mercury": 2518, "venus": 1329, "rahu": 32}
    ),
    leap_labeling="first_is_leap",
    meta={"epoch": "E1747", "tradition": "mongol"},
)

# ------------------------------------------------------------
# BHUTAN (E1754)
# ------------------------------------------------------------
BHUTAN_E1754_M0 = Fraction(1669797601, 707)
BHUTAN_E1754_S0 = Fraction(1, 67)

BHUTAN_SPEC = CalendarSpec(
    id=EngineId("trad", "bhutan", "0.1"),
    month_params=arith_month(
        Y0=1754, beta_star=2, tau=57, 
        m0=BHUTAN_E1754_M0, s0=BHUTAN_E1754_S0,
        sgang1_deg=Fraction(309, 1)
    ),
    day_params=trad_day(
        m0=BHUTAN_E1754_M0,
        s0=BHUTAN_E1754_S0,
        a0=Fraction(17, 147),
        location=LOC_BHUTAN_APPROX
    ),
    planets_params=trad_planets(
        m0=BHUTAN_E1754_M0,
        s0=BHUTAN_E1754_S0,
        pd0={"mars": 197, "jupiter": 1448, "saturn": 7710, "mercury": 447, "venus": 65, "rahu": 118} 
        #There is a note by Hennning on Mercury figure
    ),
    leap_labeling="second_is_leap",
    meta={"epoch": "E1754", "tradition": "bhutan", "leap_labeling": "second_is_leap (simplified)"},
)

# ------------------------------------------------------------
# KARANA (E806)
# ------------------------------------------------------------
KARANA_E806_M0 = Fraction(4031063, 2)
KARANA_E806_S0 = Fraction(809, 810)

KARANA_P_RATES = dict(P_RATES)
KARANA_P_RATES["sun"] = S1_KAR / M1_KAR
KARANA_P_RATES["rahu"] = RAHU_LUN / M1_KAR

KARANA_SPEC = CalendarSpec(
    id=EngineId("trad", "karana", "0.1"),
    month_params=arith_month(
        Y0=806, beta_star=0, tau=63, 
        m0=KARANA_E806_M0, s0=KARANA_E806_S0, m1=M1_KAR,
        sgang1_deg=Fraction(300, 1)
    ),
    day_params=trad_day(
        m0=KARANA_E806_M0,
        s0=KARANA_E806_S0,
        a0=Fraction(53, 252),
        m1=M1_KAR, s1=S1_KAR, a1=A1_KAR,
    ),
    planets_params=trad_planets(
        m0=KARANA_E806_M0,
        s0=KARANA_E806_S0,
        pd0={"mars": 167, "jupiter": 1732, "saturn": 5946, "mercury": 1674, "venus": 2163, "rahu": 122},
        p_rates=KARANA_P_RATES
    ),
    leap_labeling="second_is_leap",
    meta={"epoch": "E806", "tradition": "karana"},
)

# ------------------------------------------------------------

TRAD_SPECS = {
    "phugpa": PHUGPA_SPEC,
    "tsurphu": TSURPHU_SPEC,
    "mongol": MONGOL_SPEC,
    "bhutan": BHUTAN_SPEC,
    "karana": KARANA_SPEC,
}


# ============================================================
# REFORMED RATIONAL (AND ARITHMETIC) ENGINE SPECIFICATIONS
# ============================================================

# The epoch fundamentals (E1987)
L_FUNDS = make_funds(
    # m0 absolute JD epoch. Base 100M strips wild primes (11, 13, 23) from 
    # the original 65780 denominator. Error vs Meeus is ~43 microseconds.
    m0=Fraction(244691379521131, 100000000),
    
    fund_rates=FUND_RATES,
    jd_base=JD_J2000,
    
    # Phase offsets mapped to the Harmonic Arcsecond Grid (1,296,000)
    # This prevents the initial make_funds calculation from polluting the LCM.
    s0=Fraction(128634, 1296000), 
    a0=Fraction(389900, 1296000),
    r0=Fraction(406845, 1296000),
    f0=Fraction(91591, 1296000)
)

# Non-harmonized version:
L_FUNDS_V1 = make_funds(
    m0=Fraction(160957989449, 65780),
    fund_rates=FUND_RATES,
    jd_base=JD_J2000,
    s0=Fraction(3609, 36361), 
    a0=Fraction(7690, 25561),
    r0=Fraction(27144, 86467),
    f0=Fraction(4596, 65033)
)

# ============================================================================
# SOLAR ANOMALY SERIES (Harmonized Arcsecond Grid)
# Base Denominator = 1,296,000 (2**7 * 3**4 * 5**3)
# ============================================================================
# # (d, m, mp, f, amp_fraction, [amp1_fraction_per_day])

# 1-Term Solar Series (Primary Equation of Center: 6893 arcseconds)
# Includes secular drift: -4817 microdeg/cy mapped to harmonic primes
# Leaves ~30-minute residual error in pure solar position, ~2.4m in lunar phase.
L_SOLAR_TABLE_1 = (
    (0, 1, 0, 0, Fraction(6893, 1296000), Fraction(-1, 487 * 2**9 * 3**7 * 5)), 
)
# 2-Term Solar Series (Corrects elliptical flattening: 72 arcseconds)
# Drops residual error to ~26s for the Sun, and ~2s for the Moon.
L_SOLAR_TABLE_2 = L_SOLAR_TABLE_1 + (
    (0, 2, 0, 0, Fraction(72, 1296000)), 
)

# ============================================================================
# LUNAR ANOMALY SERIES (Harmonized Arcsecond Grid)
# Base Denominator = 1,296,000 (2**7 * 3**4 * 5**3)
# ============================================================================
# # (d, m, mp, f, amp_fraction, [amp1_fraction_per_day])

# 1-Term Lunar Series (Major Equation of Center: ~6.29° -> 22,640 arcseconds)
L_LUNAR_TABLE_1 = (
    (0, 0, 1, 0, Fraction(22640, 1296000)),               # Major Eq
)
# 3-Term Lunar Series (Adds the major solar perturbations)
L_LUNAR_TABLE_3 = L_LUNAR_TABLE_1 + (
    (2, 0, -1, 0, Fraction(4586, 1296000)),               # Evection (~1.27°)
    (2, 0, 0, 0, Fraction(2370, 1296000)),                # Variation (~0.66°)
)
# 6-Term Lunar Series (High-precision historical emulation)
L_LUNAR_TABLE_6 = L_LUNAR_TABLE_3 + (
    (0, 0, 2, 0, Fraction(769, 1296000)),                 # 2nd Elliptic
    (0, 1, 0, 0, Fraction(-666, 1296000)),                # Annual Eq, Drift: Fraction(1, 2**6 * 3**2 * 5**11)
    (0, 0, 0, 2, Fraction(-412, 1296000)),                # Reduction to Ecliptic
)

# ============================================================================
# Secular Accelerations (turns / day^2)
# ============================================================================
# These J2000.0 quadratic drift coefficients represent the physical acceleration 
# of the Sun and the Moon's elongation (e.g., the ~13.3s/cy^2 lunar brake).
#
# The exact fractional forms are strictly synchronized with the Delta-T 
# time-scale denominator. Their prime factors contain only 2, 3, and 5,
# ensuring that Python's rational LCM additions never balloon into massive,
# un-factorable prime numbers during continuous engine evaluations.
FUND_ACC_SUN = Fraction(1, 2**7 * 3**4 * 5**16)
FUND_ACC_ELONG = Fraction(-1, 2**11 * 3**13 * 5**7)
# Alternaitve version:
# Explicitly factorized to the fundamental time-harmonic primes (487, 2, 3, 5).
# 36525 days/cy * 360 deg = 13,149,000 = 487 * 2^3 * 3^3 * 5^3
FUND_ACC_SUN_V1   = Fraction(1,  487 * 2**8 * 3**3 * 5**8) # 1 / 131,490,000,000
FUND_ACC_ELONG_V1 = Fraction(-1, 487 * 2**9 * 3**7 * 5**4) # ~ -13.3 s/cy^2


# ============================================================
# L0 REFORM: Pure Arithmetic Baseline
# ============================================================

L0_SPEC = CalendarSpec(
    id=EngineId("reform", "l0", "0.1"),
    month_params=arith_month(
        P=P_NEW, Q=Q_NEW, beta_star=57, 
        sgang1_deg=Fraction(307, 1), 
        m0=L_FUNDS["m0"], s0=L_FUNDS["S"].c0, m1=FUND_RATES["M1"]
    ),
    day_params=arith_day(
        location=LOC_LHASA,
        m0_abs=L_FUNDS["m0"],   # Passes absolute, arith_day auto-shifts for Lhasa!
        s0=L_FUNDS["S"].c0, 
        s1=FUND_RATES["S1"],
        U=143925, 
        V=141673
    ),
    leap_labeling="first_is_leap",
    meta={"epoch": "E1987", "description": "L0 Reform: Pure Arithmetic with Meeus constants"}
)

# ============================================================
# L1 REFORM: Single Anomaly Model ("Modernized traditional")
# ============================================================
L1_SPEC = CalendarSpec(
    id=EngineId("reform", "l1", "0.1"),
    month_params=arith_month(
        P=P_NEW, Q=Q_NEW, beta_star=57, 
        sgang1_deg=Fraction(307, 1), 
        m0=L_FUNDS["m0"], s0=L_FUNDS["S"].c0, m1=FUND_RATES["M1"]
    ),
    day_params=rational_day(
        funds=L_FUNDS,
        solar_table=L_SOLAR_TABLE_1,
        lunar_table=L_LUNAR_TABLE_1, 
    ),
    leap_labeling="first_is_leap",
    meta={"epoch": "E1987", "description": "L1 Reform: Single anomaly terms, constant sunrise"}
)

# ============================================================
# L2 REFORM: Evection and Variation Added
# ============================================================
L2_SPEC = CalendarSpec(
    id=EngineId("reform", "l2", "0.1"),
    month_params=arith_month(
        P=P_NEW, Q=Q_NEW, beta_star=57, 
        sgang1_deg=Fraction(307, 1), 
        m0=L_FUNDS["m0"], s0=L_FUNDS["S"].c0, m1=FUND_RATES["M1"]
    ),
    day_params=rational_day(
        funds=L_FUNDS,
        solar_table=L_SOLAR_TABLE_1,
        lunar_table=L_LUNAR_TABLE_3, 
        iterations=1,
    ),
    leap_labeling="first_is_leap",
    meta={"epoch": "E1987", "description": "L2 Reform: 3 lunar terms, constant sunrise"}
)

# ============================================================
# L3 REFORM: Full 6-Term Orbit, Spherical Dawn, Quadratic Delta T
# ============================================================
L3_SPEC = CalendarSpec(
    id=EngineId("reform", "l3", "0.1"),
    month_params=arith_month(
        P=P_NEW, Q=Q_NEW, beta_star=57, 
        sgang1_deg=Fraction(307, 1), 
        m0=L_FUNDS["m0"], s0=L_FUNDS["S"].c0, m1=FUND_RATES["M1"]
    ),
    day_params=rational_day(
        funds=L_FUNDS,
        solar_table=L_SOLAR_TABLE_1,
        lunar_table=L_LUNAR_TABLE_6, 
        iterations=3,
        invB_prec=M1_PREC,
        delta_t=DT_QUADRATIC_DEF,
        sunrise=DAWN_SPHERICAL_DEF,
        moon_tab_quarter=SINE_TAB_QUARTER,
        sun_tab_quarter=SINE_TAB_QUARTER,
        include_drift=True
    ),
    leap_labeling="first_is_leap",
    meta={"epoch": "E1987", "description": "L3 Reform: 6 lunar terms, spherical dawn, quadratic delta T"}
)

# ============================================================================
# FLOAT ENGINE FOURIER TABLES (JPL / Meeus)
# ============================================================================
# Format: (d, m, m', f, amplitude_microdegrees, [secular_drift_microdegrees])
#
# Note on Determinism: The amplitudes and drifts below are defined strictly as 
# whole integers (represented as float literals, e.g., 6288774.0) measuring 
# microdegrees. Under the IEEE 754 64-bit standard, all integers up to 2^53 
# have an exact, bit-perfect binary representation. By avoiding base-10 
# fractional decimals in the source code, we guarantee 100% deterministic 
# parsing across all hardware architectures and compilers. The scaling division 
# (converting microdegrees into turns) is performed strictly internally during 
# engine initialization.

# 1-Term Solar Series (Primary Keplerian anomaly; leaves ~30-minute error in solar position, ~2.4m in lunar phase)
# Includes secular drift (-4817 microdeg/cy) to fix the 70-min millennial error.
FLOAT_SOLAR_TABLE_1 = (
    (0, 1, 0, 0, 1914602.0, -4817.0), 
)
# 2-Term Solar Series (Corrects elliptical flattening; leaves ~26s error in solar position, ~2s in lunar phase)
FLOAT_SOLAR_TABLE_2 = FLOAT_SOLAR_TABLE_1 + (
    (0, 2, 0, 0,   19993.0), # 2M (Equation of Center, 2nd term: 0.019993 deg)
)
# 3-Term Solar Series (Full JPL/Meeus high-precision solar center)
FLOAT_SOLAR_TABLE_3 = FLOAT_SOLAR_TABLE_2 + (
    (0, 3, 0, 0,     289.0), # 3M (Equation of Center, 3rd term: 0.000289 deg)
)

# Basic lunar series (6 terms). Accuracy: ~ 15 min.
FLOAT_LUNAR_TABLE_6 = (
    # d,  m, m',  f,   C(microdeg)
    ( 0,  0,  1,  0,  6288774.0),  # Major Inequality
    ( 2,  0, -1,  0,  1274027.0),  # Evection
    ( 2,  0,  0,  0,   658314.0),  # Variation
    ( 0,  0,  2,  0,   213618.0),  # 2nd Elliptic
    ( 0,  1,  0,  0,  -185116.0),  # Annual Equation, drift: 465.8
    ( 0,  0,  0,  2,  -114332.0)   # Reduction to Ecliptic
)

# Primary lunar series (24 terms). Accuracy: ~ 3-4 min.
FLOAT_LUNAR_TABLE_24 = FLOAT_LUNAR_TABLE_6 + (
    # d,  m, m',  f,   C(microdeg)
    ( 2,  0, -2,  0,    58793.0),  # 3rd Elliptic / Evection Harmonic
    ( 2, -1, -1,  0,    57066.0),  # drift: -143.6
    ( 2,  0,  1,  0,    53322.0),
    ( 2, -1,  0,  0,    45758.0),  # drift: -115.1
    ( 0,  1, -1,  0,   -40923.0),  # drfit: 103.0
    ( 1,  0,  0,  0,   -34720.0),  # Parallactic Inequality (Solar parallax effect)
    ( 0,  1,  1,  0,   -30383.0),  # drift: 76.4
    ( 2,  0,  0, -2,    15327.0),  #
    ( 0,  0,  1,  2,   -12528.0),
    ( 0,  0,  1, -2,    10980.0),
    ( 4,  0, -1,  0,    10675.0),
    ( 0,  0,  3,  0,    10034.0),
    ( 4,  0, -2,  0,     8548.0),
    ( 2,  1, -1,  0,    -7888.0),
    ( 2,  1,  0,  0,    -6766.0),
    ( 1,  0, -1,  0,    -5163.0),
    ( 1,  1,  0,  0,     4987.0),
    ( 2, -1,  1,  0,     4036.0)
)

# Supplementary series (40 terms). Improves accuracy to ~ 30 sec.
FLOAT_LUNAR_TABLE_64 = FLOAT_LUNAR_TABLE_24 + (
    # d,  m, m',  f,   C(microdeg)
    ( 2,  0,  2,  0,     3994.0),
    ( 4,  0,  0,  0,     3861.0),
    ( 2,  0, -3,  0,     3665.0),
    ( 0,  1, -2,  0,    -2689.0),
    ( 2,  0, -1,  2,    -2602.0),
    ( 2, -1, -2,  0,     2390.0),
    ( 1,  0,  1,  0,    -2348.0),
    ( 2, -2,  0,  0,     2236.0),
    ( 0,  1,  2,  0,    -2120.0),
    ( 0,  2,  0,  0,    -2069.0),
    ( 2, -2, -1,  0,     2011.0),
    ( 2,  0,  1, -2,    -1977.0),
    ( 4,  0, -3,  0,    -1736.0),
    ( 4, -1, -1,  0,    -1671.0),
    ( 2,  1,  1,  0,    -1557.0),
    ( 2,  1, -2,  0,     1492.0),
    ( 2,  0, -4,  0,    -1422.0),
    ( 4, -1, -2,  0,    -1205.0),
    ( 2,  1,  0, -2,    -1111.0),
    ( 2, -1,  1, -2,    -1100.0),
    ( 2, -1,  2,  0,     -811.0),
    ( 0,  0,  4,  0,      769.0),
    ( 2,  0, -2,  2,      717.0),
    ( 0,  0,  2,  2,     -712.0),
    ( 1,  0,  2,  0,     -663.0),
    ( 1,  1, -1,  0,     -565.0),
    ( 1,  0, -2,  0,     -523.0),
    ( 4,  0, -4,  0,      492.0),
    ( 4, -2, -1,  0,     -488.0),
    ( 2,  2, -1,  0,     -469.0),
    ( 2,  2,  0,  0,     -440.0),
    ( 0,  1,  3,  0,     -425.0),
    ( 4,  0,  1,  0,     -418.0),
    ( 0,  0,  2, -2,      386.0),
    ( 2,  0, -5,  0,      371.0),
    ( 2,  2, -2,  0,      362.0),
    ( 1,  1,  1,  0,      317.0),
    ( 2,  0, -3,  2,     -310.0),
    ( 0,  2, -1,  0,     -307.0),
    ( 2,  0,  3,  0,     -293.0)
)

# ============================================================================
# FLOAT ACCELERATIONS
# ============================================================================
# Derived strictly from Fraction(1, 2**7 * 3**4 * 5**16) and 
# Fraction(-1, 2**11 * 3**13 * 5**7)
FLOAT_ACC_SUN   = float.fromhex("0x1.6c6150309e816p-51")   # ~ 6.32098e-16
FLOAT_ACC_ELONG = float.fromhex("-0x1.1a7a2c7be9067p-48")  # ~ -3.92015e-15

# Alternatice version
# Derived strictly from Fraction(1, 487 * 2**8 * 3**3 * 5**8) and 
# Fraction(-1, 487 * 2**9 * 3**7 * 5**4)
FLOAT_ACC_SUN_V1   = float.fromhex("0x1.6bedadfcc8d0dp-51") 
FLOAT_ACC_ELONG_V1 = float.fromhex("-0x1.1a5a8662ee151p-48")

# ============================================================
# L4 REFORM: Rational Month + Rational Day
# ============================================================
L4_SPEC = CalendarSpec(
    id=EngineId("reform", "l4", "0.1"),
    month_params=rational_month(
        funds=L_FUNDS,
        solar_table=L_SOLAR_TABLE_1,
        lunar_table=L_LUNAR_TABLE_1, 
        iterations=1,
        Y0=1987,
        M0=3,
        sgang1_deg=Fraction(337, 1),
        include_drift=True
    ),
    day_params=fp_day(
        epoch_k=k_from_epoch_jd(L_FUNDS["m0"]), # Uses the exact same rational anchor!
        location=LOC_LHASA,
        solar_table=FLOAT_SOLAR_TABLE_2,
        lunar_table=FLOAT_LUNAR_TABLE_24[:14],
        iterations=3,
        include_drift=True
    ),
    leap_labeling="first_is_leap",
    meta={"epoch": "E1987", "description": "L4 Reform: Primary Astronomical Engine (24-Term Float Day)"}
)

# ============================================================
# L5 REFORM: Pure Float Engine (64-Bit FPU)
# ============================================================

L5_SPEC = CalendarSpec(
    id=EngineId("reform", "l5", "0.1"),
    month_params=rational_month(
        funds=L_FUNDS,
        solar_table=L_SOLAR_TABLE_2,
        lunar_table=L_LUNAR_TABLE_6, 
        iterations=2,
        invB_prec=M1_PREC,
        moon_tab_quarter=SINE_TAB_QUARTER,
        sun_tab_quarter=SINE_TAB_QUARTER,
        Y0=1987,
        M0=3,
        sgang1_deg=Fraction(307, 1),
        C_elong=FUND_ACC_ELONG,
        include_drift=True
    ),
    day_params=fp_day(
        epoch_k=k_from_epoch_jd(L_FUNDS["m0"]), # Uses the exact same rational anchor!
        location=LOC_LHASA,
        solar_table=FLOAT_SOLAR_TABLE_2,
        lunar_table=FLOAT_LUNAR_TABLE_64,
        iterations=3,
        C_elong=FLOAT_ACC_ELONG,
        include_drift=True
    ),
    leap_labeling="first_is_leap",
    meta={"epoch": "E1987", "description": "L5 Reform: High-Precision Astronomical Engine (64-Term Float Day)"}
)

# ------------------------------------------------------------

REFORM_SPECS = {
    "reform-l0": L0_SPEC, 
    "reform-l1": L1_SPEC, 
    "reform-l2": L2_SPEC, 
    "reform-l3": L3_SPEC,
    "reform-l4": L4_SPEC,
    "reform-l5": L5_SPEC,
}

ALIASES = {
    "l0": L0_SPEC,
    "l1": L1_SPEC,
    "l2": L2_SPEC,
    "l3": L3_SPEC,
    "l4": L4_SPEC,
    "l5": L5_SPEC,
}

# ------------------------------------------------------------
 
ALL_SPECS = {**TRAD_SPECS, **REFORM_SPECS, **ALIASES}

# ------------------------------------------------------------

