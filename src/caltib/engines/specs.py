from __future__ import annotations

from typing import Tuple
from fractions import Fraction

from ..core.types import EngineId
from .menu import EngineSpec
from .rational import RationalSpec
from .rational_month import RationalMonthParams
from .rational_day import RationalDayParams, RationalDayParamsNew, RationalDayParamsTrad
from .fp import FPSpec

from .astro.deltat import DeltaTRationalDef, ConstantDeltaTRationalDef, QuadraticDeltaTRationalDef
from .astro.affine_series import TermDef, FundArg, build_phase
from .astro.sunrise import LocationRational, ConstantSunriseRationalDef, SunriseRationalDef, SphericalSunriseRationalDef

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
# REFORM CONSTANTS & LOCATIONS
# ============================================================

# Shared month ratio in paper convention p<q:
#   P=1336, Q=1377, ell=123
P_NEW = 1336
Q_NEW = 1377

# Fundamental arguments
FUNDS_REF = {
    "D": FundArg(c0=Fraction(0, 1), c1=Fraction(10000, 295306)),
    "M": FundArg(c0=Fraction(0, 1), c1=Fraction(10000, 365242)),
    "Mp": FundArg(c0=Fraction(0, 1), c1=Fraction(10000, 275545)),
    "F": FundArg(c0=Fraction(0, 1), c1=Fraction(10000, 272122)),
}

# Standard locatinos
LOC_LHASA = LocationRational(
    lat_turn=Fraction(2965, 36000), 
    lon_turn=Fraction(9110, 36000), 
    elev_m=Fraction(3650, 1)  # Converted to Fraction
)

# Constant Delta T: 55.3s in 1987, 63.8s in 2000, 69.2s in early 2026
DT_CONSTANT_DEF = ConstantDeltaTRationalDef(Fraction(69, 1))
# Quadratic Delta T: -20 + 32 * ((year - 1820) / 100)^2
DT_QUADRATIC_DEF = QuadraticDeltaTRationalDef(
    a=Fraction(-20, 1), 
    b=Fraction(0, 1), 
    c=Fraction(32, 1), 
    y0=Fraction(1820, 1)
)

# Constant sunrise (89/360 for 5:56am,  1/4 for 6:00am)
DAWN_CONSTANT_DEF = ConstantSunriseRationalDef(Fraction(90, 360))
# Spherical sunrise constants (h0 = -0.833 deg, eps = 23.44 deg)
DAWN_SPHERICAL_DEF = SphericalSunriseRationalDef(
    h0_turn=Fraction(-1, 432), 
    eps_turn=Fraction(2344, 36000)
)

# New tables
SINE_TAB_QUARTER = (0, 228, 444, 638, 801, 923, 998, 1024)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def trad_month(*, Y0: int, M0: int, beta_star: int, tau: int, leap_labeling: str) -> RationalMonthParams:
    return RationalMonthParams(
        Y0=Y0,
        M0=M0,
        P=P_TIB,
        Q=Q_TIB,
        beta_star=beta_star,
        tau=tau,
        leap_labeling=leap_labeling,
    )

def trad_day(*, m0: Fraction, s0: Fraction, a0: Fraction, m1: Fraction, s1: Fraction, a1: Fraction) -> RationalDayParams:
    return RationalDayParams(
        mode="trad",
        trad=RationalDayParamsTrad(
            m0=m0,
            m1=m1,
            m2=m1 / 30,
            s0=s0,
            s1=s1,
            s2=s1 / 30,
            a0=a0,
            a1=a1,
            a2=A2_STD,
            moon_tab_quarter=MOON_TAB_QUARTER,
            sun_tab_quarter=SUN_TAB_QUARTER,
        )
    )

def reform_month(*, Y0: int, M0: int, P: int, Q: int, beta_star: int, tau: int, leap_labeling: str) -> RationalMonthParams:
    """Fully parameterized month engine for L1-L3 reforms."""
    return RationalMonthParams(
        Y0=Y0, M0=M0, P=P, Q=Q, beta_star=beta_star, tau=tau, leap_labeling=leap_labeling
    )

def reform_day(
    *,
    A_sun: Fraction,
    B_sun: Fraction,
    solar_terms: Tuple[TermDef, ...],
    A_moon: Fraction,
    B_moon: Fraction,
    lunar_terms: Tuple[TermDef, ...],
    iterations: int = 1,
    delta_t: DeltaTRationalDef = DT_CONSTANT_DEF,
    sunrise: SunriseRationalDef = DAWN_CONSTANT_DEF,
    location: LocationRational = LOC_LHASA,
    moon_tab_quarter: Tuple[int, ...] = MOON_TAB_QUARTER,
    sun_tab_quarter: Tuple[int, ...] = SUN_TAB_QUARTER,
) -> RationalDayParams:
    """Helper to cleanly build L1-L3 continuous engine parameters with standard defaults."""
    return RationalDayParams(
        mode="new",
        new=RationalDayParamsNew(
            A_sun=A_sun,
            B_sun=B_sun,
            solar_terms=solar_terms,
            A_moon=A_moon,
            B_moon=B_moon,
            lunar_terms=lunar_terms,
            iterations=iterations,
            delta_t=delta_t,
            sunrise=sunrise,
            location=location,
            moon_tab_quarter=moon_tab_quarter,
            sun_tab_quarter=sun_tab_quarter
        )
    )


# ============================================================
# ENGINE SPECIFICATIONS
# ============================================================


# ------------------------------------------------------------
# PHUGPA (E1987)
# ------------------------------------------------------------
PHUGPA_SPEC = RationalSpec(
    id=EngineId("trad", "phugpa", "0.1"),
    month=trad_month(Y0=1987, M0=3, beta_star=0, tau=48, leap_labeling="first_is_leap"),
    day=trad_day(
        m0=Fraction(1729968333, 707),
        s0=Fraction(0, 1),
        a0=Fraction(38, 49),
        m1=M1_TIB, s1=S1_TIB, a1=A1_TIB,
    ),
    meta={"epoch": "E1987", "tradition": "phugpa"},
)

PHUGPA = EngineSpec(kind="rational", id=PHUGPA_SPEC.id, payload=PHUGPA_SPEC)


# ------------------------------------------------------------
# TSURPHU (E1852)
# leap block {0,1} -> tau=0, standard leap labeling
# ------------------------------------------------------------
TSURPHU_SPEC = RationalSpec(
    id=EngineId("trad", "tsurphu", "0.1"),
    month=trad_month(Y0=1852, M0=3, beta_star=14, tau=0, leap_labeling="first_is_leap"),
    day=trad_day(
        m0=Fraction(18307100485903, 7635600),
        s0=Fraction(23, 27135),
        a0=Fraction(1, 49),
        m1=M1_TIB, s1=S1_TIB, a1=A1_TIB,
    ),
    meta={"epoch": "E1852", "tradition": "tsurphu"},
)

TSURPHU = EngineSpec(kind="rational", id=TSURPHU_SPEC.id, payload=TSURPHU_SPEC)


# ------------------------------------------------------------
# MONGOL (E1747)
# leap block {46,47} -> tau=46
# ------------------------------------------------------------
MONGOL_SPEC = RationalSpec(
    id=EngineId("trad", "mongol", "0.1"),
    month=trad_month(Y0=1747, M0=3, beta_star=10, tau=46, leap_labeling="first_is_leap"),
    day=trad_day(
        m0=Fraction(6671924839, 2828),
        s0=Fraction(397, 402),
        a0=Fraction(1523, 1764),
        m1=M1_TIB, s1=S1_TIB, a1=A1_TIB,
    ),
    meta={"epoch": "E1747", "tradition": "mongol"},
)

MONGOL = EngineSpec(kind="rational", id=MONGOL_SPEC.id, payload=MONGOL_SPEC)


# ------------------------------------------------------------
# BHUTAN (E1754)
# leap block {57,58} -> tau=57
# NOTE: uses simplified convention: second copy of triggered label is repeated (Remark 2.4, Janson A.23).
# Traditional trigger set is {59,60}, but the preceding month label would be repeated.
# ------------------------------------------------------------
BHUTAN_SPEC = RationalSpec(
    id=EngineId("trad", "bhutan", "0.1"),
    month=trad_month(Y0=1754, M0=3, beta_star=2, tau=57, leap_labeling="second_is_leap"),
    day=trad_day(
        m0=Fraction(1669797601, 707),
        s0=Fraction(1, 67),
        a0=Fraction(17, 147),
        m1=M1_TIB, s1=S1_TIB, a1=A1_TIB,
    ),
    meta={"epoch": "E1754", "tradition": "bhutan", "leap_labeling": "second_is_leap (simplified)"},
)

BHUTAN = EngineSpec(kind="rational", id=BHUTAN_SPEC.id, payload=BHUTAN_SPEC)


# ------------------------------------------------------------
# KARANA (E806)
# leap block {63,64} -> tau=63
# uses karana mean motions for day layer
# NOTE: uses simplified convention: second copy of triggered label is repeated (Remark 2.4, Janson A.37).
# ------------------------------------------------------------
KARANA_SPEC = RationalSpec(
    id=EngineId("trad", "karana", "0.1"),
    month=trad_month(Y0=806, M0=3, beta_star=0, tau=63, leap_labeling="first_is_leap"),
    day=trad_day(
        m0=Fraction(4031063, 2),
        s0=Fraction(809, 810),
        a0=Fraction(53, 252),
        m1=M1_KAR, s1=S1_KAR, a1=A1_KAR,
    ),
    meta={"epoch": "E806", "tradition": "karana"},
)

KARANA = EngineSpec(kind="rational", id=KARANA_SPEC.id, payload=KARANA_SPEC)


TRAD_SPECS = {
    "phugpa": PHUGPA,
    "tsurphu": TSURPHU,
    "mongol": MONGOL,
    "bhutan": BHUTAN,
    "karana": KARANA,
}



# ============================================================
# L1 REFORM: Single Anomaly Model
# ============================================================
L1_SPEC = RationalSpec(
    id=EngineId("reform", "l1", "0.1"),
    month=reform_month(Y0=2026, M0=3, P=10000, Q=10368, beta_star=0, tau=0, leap_labeling="first_is_leap"),
    day=reform_day(
        # Solar Series (Outputs True Sun)
        A_sun=Fraction(0, 1),
        B_sun=FUNDS_REF["M"].c1, 
        solar_terms=(
            TermDef(amp=Fraction(1, 60), phase=build_phase({"M": 1}, FUNDS_REF)),
        ),
        
        # Lunar Series (Outputs True Moon)
        A_moon=Fraction(0, 1),
        B_moon=FUNDS_REF["D"].c1 + FUNDS_REF["M"].c1, 
        lunar_terms=(),
    ),
    meta={"description": "L1 Reform: Single anomaly, split physical series"}
)


REFORM_L1 = EngineSpec(kind="rational", id=L1_SPEC.id, payload=L1_SPEC)


# ============================================================
# L2 REFORM: Evection and Variation Added
# ============================================================
L2_SPEC = RationalSpec(
    id=EngineId("reform", "l2", "0.1"),
    month=reform_month(Y0=2026, M0=3, P=10000, Q=10368, beta_star=0, tau=0, leap_labeling="first_is_leap"),
    day=reform_day(
        # Solar Series
        A_sun=Fraction(0, 1),
        B_sun=FUNDS_REF["M"].c1, 
        solar_terms=(
            # Equation of Center
            TermDef(amp=Fraction(1, 60), phase=build_phase({"M": 1}, FUNDS_REF)),
        ),
        
        # Lunar Series (3 Terms)
        A_moon=Fraction(0, 1),
        B_moon=FUNDS_REF["D"].c1 + FUNDS_REF["M"].c1, 
        lunar_terms=(
            # Principal Anomaly (Placeholder amplitude)
            TermDef(amp=Fraction(17, 1000), phase=build_phase({"Mp": 1}, FUNDS_REF)),
            # Evection: 2D - M'
            TermDef(amp=Fraction(15, 1000), phase=build_phase({"D": 2, "Mp": -1}, FUNDS_REF)),
            # Variation: 2D
            TermDef(amp=Fraction(11, 1000), phase=build_phase({"D": 2}, FUNDS_REF)),
        ),
        iterations=2,  # Extra iteration for stability with 3 lunar terms
        sunrise=DAWN_CONSTANT_DEF,  # L2 still uses constant dawn
    ),
    meta={"description": "L2 Reform: 3 lunar terms, constant sunrise"}
)

REFORM_L2 = EngineSpec(kind="rational", id=L2_SPEC.id, payload=L2_SPEC)


# ============================================================
# L3 REFORM: Full 5-Term Orbit, Spherical Dawn, Quadratic Delta T
# ============================================================
L3_SPEC = RationalSpec(
    id=EngineId("reform", "l3", "0.1"),
    month=reform_month(Y0=2026, M0=3, P=10000, Q=10368, beta_star=0, tau=0, leap_labeling="first_is_leap"),
    day=reform_day(
        # Solar Series
        A_sun=Fraction(0, 1),
        B_sun=FUNDS_REF["M"].c1, 
        solar_terms=(
            TermDef(amp=Fraction(1, 60), phase=build_phase({"M": 1}, FUNDS_REF)),
        ),
        
        # Lunar Series (5 Terms)
        A_moon=Fraction(0, 1),
        B_moon=FUNDS_REF["D"].c1 + FUNDS_REF["M"].c1, 
        lunar_terms=(
            TermDef(amp=Fraction(17, 1000), phase=build_phase({"Mp": 1}, FUNDS_REF)),
            TermDef(amp=Fraction(15, 1000), phase=build_phase({"D": 2, "Mp": -1}, FUNDS_REF)),
            TermDef(amp=Fraction(11, 1000), phase=build_phase({"D": 2}, FUNDS_REF)),
            TermDef(amp=Fraction(2, 1000), phase=build_phase({"M": 1}, FUNDS_REF)),
            TermDef(amp=Fraction(-1, 1000), phase=build_phase({"F": 2}, FUNDS_REF)),
        ),
        iterations=2,
        delta_t=DT_QUADRATIC_DEF,
        sunrise=DAWN_SPHERICAL_DEF,  
    ),
    meta={"description": "L3 Reform: 5 lunar terms, spherical dawn, quadratic time correction"}
)

REFORM_L3 = EngineSpec(kind="rational", id=L3_SPEC.id, payload=L3_SPEC)


# ============================================================
# L5 REFORM: Float
# ============================================================

# (still stub)
REFORM_L5 = EngineSpec(
    kind="fp",
    id=EngineId("reform", "l5", "0.1"),
    payload=FPSpec(
        id=EngineId("reform", "l5", "0.1"),
        meta={"note": "placeholder; fp/minimax to be implemented"},
    ),
)

REFORM_SPECS = {
    "reform-l1": REFORM_L1, 
    "reform-l2": REFORM_L2, 
    "reform-l3": REFORM_L3, 
    "reform-l5": REFORM_L5
}

ALL_SPECS = {**TRAD_SPECS, **REFORM_SPECS}