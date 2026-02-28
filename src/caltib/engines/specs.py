from __future__ import annotations

from typing import Tuple
from fractions import Fraction

from ..core.types import EngineId
from .menu import EngineSpec
from .rational import RationalSpec
from .rational_month import RationalMonthParams
from .arithmetic_month import ArithmeticMonthParams
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

JD_J2000 = Fraction(2451545, 1)

# Shared month ratio in paper convention p<q:
#   P=1336, Q=1377, ell=41
P_NEW = 1336
Q_NEW = 1377

# Mean motions derived from Meeus ELP2000 linear rates (per lunation)
M1_NEW = Fraction(283346, 9595)   # Synodic month (days)
S1_NEW = Fraction(334, 4131)    # Sun longitude (turns)
A1_NEW = Fraction(4583, 63907)    # Moon anomaly (turns)
R1_NEW = Fraction(1689, 20891)    # Sun anomaly (turns, "sigma")
F1_NEW = Fraction(324, 3803)    # Moon latitude (turns)

# Fundamental rates evaluated natively at t = JD (c1 in turns per day)
FUND_RATES = {
    "S": S1_NEW / M1_NEW,
    "D": Fraction(1, 1) / M1_NEW,
    "M": R1_NEW / M1_NEW,
    "Mp": A1_NEW / M1_NEW,
    "F": F1_NEW / M1_NEW,
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

def trad_month(
    *, 
    Y0: int, 
    M0: int = 3, 
    beta_star: int, 
    tau: int, 
    m0_jd: Fraction,  # The exact m0 from your Day Engine specs
    sgang1: Fraction = Fraction(0)
) -> ArithmeticMonthParams:
    """
    Initializes an Arithmetic Month Engine for a traditional epoch.
    Automatically deduces the absolute epoch_k from the physical m0 anchor.
    """
    return ArithmeticMonthParams(
        epoch_k=k_from_epoch_jd(m0_jd),
        sgang1=sgang1,
        Y0=Y0,
        M0=M0,
        P=P_TIB,
        Q=Q_TIB,
        beta_star=beta_star,
        tau=tau,
    )


def trad_month(*, Y0: int, M0: int = 3, beta_star: int, tau: int, leap_labeling: str = "first_is_leap") -> RationalMonthParams:
    return RationalMonthParams(
        Y0=Y0,
        M0=M0,
        P=P_TIB,
        Q=Q_TIB,
        beta_star=beta_star,
        tau=tau,
        leap_labeling=leap_labeling,
    )

def trad_day(*, m0: Fraction, s0: Fraction, a0: Fraction, m1: Fraction = M1_TIB, s1: Fraction = S1_TIB, a1: Fraction = A1_TIB, a2: Fraction = A2_STD) -> RationalDayParams:
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
            a2=a2,
            moon_tab_quarter=MOON_TAB_QUARTER,
            sun_tab_quarter=SUN_TAB_QUARTER,
        )
    )

def reform_month(
    *, 
    Y0: int = 1987,
    M0: int = 3, 
    P: int = P_NEW, 
    Q: int = Q_NEW, 
    beta_star: int = 57, #d1=307 (Jan 28)
#    beta_star: int = 103, #d1=308 (Jan 29)
    tau: int = 0, 
    leap_labeling: str = "first_is_leap"
) -> RationalMonthParams:
    """Fully parameterized month engine for L1-L3 reforms."""
    return RationalMonthParams(
        Y0=Y0, M0=M0, P=P, Q=Q, beta_star=beta_star, tau=tau, leap_labeling=leap_labeling
    )

def make_funds(
    m0_abs: Fraction,  # Epoch JD_TT (Absolute Julian Day)
    s0: Fraction = Fraction(0),
    a0: Fraction = Fraction(0),
    r0: Fraction = Fraction(0),
    f0: Fraction = Fraction(0),
) -> dict[str, FundArg]:
    """Binds epoch phases (at absolute JD) to the standard fundamental rates (c1),
    projecting them back to t=0 (J2000.0) for the absolute time solver."""
    
    # Shift absolute JD to internal coordinate system (Days since J2000.0)
    m0_j2000 = m0_abs - JD_J2000
    
    # Elongation is exactly 0 at the epoch: D(m0_j2000) = c0 + c1*m0_j2000 = 0
    c0_D = -FUND_RATES["D"] * m0_j2000
    
    # Sun longitude is s0 at the epoch: S(m0_j2000) = c0 + c1*m0_j2000 = s0
    c0_S = s0 - FUND_RATES["S"] * m0_j2000
    
    c0_M = r0 - FUND_RATES["M"] * m0_j2000
    c0_Mp = a0 - FUND_RATES["Mp"] * m0_j2000
    c0_F = f0 - FUND_RATES["F"] * m0_j2000
    
    return {
        "S": FundArg(c0=c0_S, c1=FUND_RATES["S"]),
        "D": FundArg(c0=c0_D, c1=FUND_RATES["D"]),
        "M": FundArg(c0=c0_M, c1=FUND_RATES["M"]),
        "Mp": FundArg(c0=c0_Mp, c1=FUND_RATES["Mp"]),
        "F": FundArg(c0=c0_F, c1=FUND_RATES["F"]),
    }

def reform_day(
    *,
    funds: dict[str, FundArg],
    solar_terms: Tuple[TermDef, ...] = (),
    lunar_terms: Tuple[TermDef, ...] = (),
    iterations: int = 1,
    delta_t: DeltaTRationalDef = DT_CONSTANT_DEF,
    sunrise: SunriseRationalDef = DAWN_CONSTANT_DEF,
    location: LocationRational = LOC_LHASA,
    moon_tab_quarter: Tuple[int, ...] = MOON_TAB_QUARTER,
    sun_tab_quarter: Tuple[int, ...] = SUN_TAB_QUARTER,
) -> RationalDayParams:
    """Cleanly builds L1-L3 continuous engine parameters directly from resolved fundamentals."""
    return RationalDayParams(
        mode="new",
        new=RationalDayParamsNew(
            A_sun=funds["S"].c0,
            B_sun=funds["S"].c1,
            solar_terms=solar_terms,
            
            # Scale elongation base from turns to tithis
            A_elong=funds["D"].c0 * 30,
            B_elong=funds["D"].c1 * 30,
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
# TRADITIONAL ENGINE SPECIFICATIONS
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
    month=trad_month(Y0=806, M0=3, beta_star=0, tau=63, leap_labeling="second_is_leap"),
    day=trad_day(
        m0=Fraction(4031063, 2),
        s0=Fraction(809, 810),
        a0=Fraction(53, 252),
        m1=M1_KAR, s1=S1_KAR, a1=A1_KAR,
    ),
    meta={"epoch": "E806", "tradition": "karana"},
)

KARANA = EngineSpec(kind="rational", id=KARANA_SPEC.id, payload=KARANA_SPEC)


# ------------------------------------------------------------

TRAD_SPECS = {
    "phugpa": PHUGPA,
    "tsurphu": TSURPHU,
    "mongol": MONGOL,
    "bhutan": BHUTAN,
    "karana": KARANA,
}


# ============================================================
# REFORMED ENGINE SPECIFICATIONS
# ============================================================


# The epoch fundamentals (E1987)

L_FUNDS = make_funds(
    m0_abs=Fraction(160957989449, 65780),
    s0=Fraction(3609, 36361), 
    a0=Fraction(7690, 25561),
    r0=Fraction(27144, 86467),
    f0=Fraction(4596, 65033)
)

# ============================================================
# L1 REFORM: Single Anomaly Model
# ============================================================

L1_SPEC = RationalSpec(
    id=EngineId("reform", "l1", "0.1"),
    month=reform_month(),
    day=reform_day(
        funds=L_FUNDS,
        solar_terms=(
            TermDef(amp=Fraction(32, 6015), phase=build_phase({"M": 1}, L_FUNDS)),
        ),
        lunar_terms=(
            TermDef(amp=Fraction(8515, 16248), phase=build_phase({"Mp": 1}, L_FUNDS)),
        ),
    ),
    meta={"description": "L1 Reform: Single anomaly terms, constant sunrise"}
)

REFORM_L1 = EngineSpec(kind="rational", id=L1_SPEC.id, payload=L1_SPEC)


# ============================================================
# L2 REFORM: Evection and Variation Added
# ============================================================

L2_SPEC = RationalSpec(
    id=EngineId("reform", "l2", "0.1"),
    month=reform_month(),
    day=reform_day(
        funds=L_FUNDS,
        solar_terms=(
            TermDef(amp=Fraction(32, 6015), phase=build_phase({"M": 1}, L_FUNDS)),
        ),
        lunar_terms=(
            TermDef(amp=Fraction(8515, 16248), phase=build_phase({"Mp": 1}, L_FUNDS)),
            TermDef(amp=Fraction(401, 3777), phase=build_phase({"D": 2, "Mp": -1}, L_FUNDS)),
            TermDef(amp=Fraction(1064, 19395), phase=build_phase({"D": 2}, L_FUNDS)),
        ),
        iterations=2,  
    ),
    meta={"description": "L2 Reform: 3 lunar terms, constant sunrise"}
)

REFORM_L2 = EngineSpec(kind="rational", id=L2_SPEC.id, payload=L2_SPEC)


# ============================================================
# L3 REFORM: Full 5-Term Orbit, Spherical Dawn, Quadratic Delta T
# ============================================================

L3_SPEC = RationalSpec(
    id=EngineId("reform", "l3", "0.1"),
    month=reform_month(),
    day=reform_day(
        funds=L_FUNDS,
        solar_terms=(
            TermDef(amp=Fraction(32, 6015), phase=build_phase({"M": 1}, L_FUNDS)),
        ),
        lunar_terms=(
            TermDef(amp=Fraction(8515, 16248), phase=build_phase({"Mp": 1}, L_FUNDS)),
            TermDef(amp=Fraction(401, 3777), phase=build_phase({"D": 2, "Mp": -1}, L_FUNDS)),
            TermDef(amp=Fraction(1064, 19395), phase=build_phase({"D": 2}, L_FUNDS)),
            TermDef(amp=Fraction(-56, 3629), phase=build_phase({"M": 1}, L_FUNDS)),
            TermDef(amp=Fraction(40, 2247), phase=build_phase({"Mp": 2}, L_FUNDS)),
            TermDef(amp=Fraction(-447, 46916), phase=build_phase({"F": 2}, L_FUNDS)),
        ),
        iterations=2,  
        delta_t=DT_QUADRATIC_DEF,
        sunrise=DAWN_SPHERICAL_DEF,  
        moon_tab_quarter=SINE_TAB_QUARTER,
        sun_tab_quarter=SINE_TAB_QUARTER

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