from __future__ import annotations

from fractions import Fraction

from ..core.types import EngineId
from .menu import EngineSpec
from .rational import RationalSpec
from .rational_month import RationalMonthParams
from .rational_day import RationalDayParams
from .fp import FPSpec

from .astro.deltat import ConstantDeltaTRational
from .astro.sunrise import ConstantSunriseRational, LocationRational
from .astro.affine_series import PhaseT, SinTermT, AffineSinSeriesT, FundArg, build_phase



# Shared traditional tables (Appendix A style)
MOON_TAB_QUARTER = (0, 5, 10, 15, 19, 22, 24, 25)   # length 8 = 28/4+1
SUN_TAB_QUARTER  = (0, 6, 10, 11)                   # length 4 = 12/4+1

# New tables
SINE_TAB_QUARTER = (0, 228, 444, 638, 801, 923, 998, 1024)   # length 8 = 28/4+1

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
# REFORM FUNDAMENTAL ARGUMENTS (JD_TT -> turns)
# Placeholders: c0 (epoch phase) and c1 (turns per day)
# ============================================================
FUNDS_REF = {
    "D": FundArg(c0=Fraction(0, 1), c1=Fraction(10000, 295306)),  # ~ 1/29.53 turns/day
    "M": FundArg(c0=Fraction(0, 1), c1=Fraction(10000, 365242)),  # ~ 1/365.24 turns/day
    "Mp": FundArg(c0=Fraction(0, 1), c1=Fraction(10000, 275545)), # ~ 1/27.55 turns/day
    "F": FundArg(c0=Fraction(0, 1), c1=Fraction(10000, 272122)),  # ~ 1/27.21 turns/day
}

# Standard observer location (e.g., Lhasa placeholder)
LOC_LHASA = LocationRational(
    lat_turn=Fraction(2965, 36000),  # ~ 29.65 deg
    lon_turn=Fraction(9110, 36000),  # ~ 91.10 deg
    elev_m=Fraction(3650, 1)
)

# Standard rational time conversions
DT_CONSTANT = ConstantDeltaTRational(Fraction(70, 1))         # ~70 seconds Delta T
DAWN_CONSTANT = ConstantSunriseRational(Fraction(1, 4))       # 6:00 AM LMT

# ============================================================
# L1 REFORM: Single Anomaly Model
# ============================================================
# B is the mean elongation rate (turns per day). Target x0 is in 1/30 turns.
# In specs.py
L1_SPEC = RationalSpec(
    id=EngineId("reform", "l1", "0.1"),
    month=trad_month(Y0=2026, M0=3, beta_star=0, tau=0, leap_labeling="first_is_leap"),
    day=RationalDayParams(
        mode="new",
        new=RationalDayParamsNew(
            A=Fraction(0, 1),
            B=FUNDS_REF["D"].c1, 
            terms=(
                # Equation of Center proxy using the Sun table
                TermDef(
                    amp=Fraction(1, 60), 
                    phase=build_phase({"M": 1}, FUNDS_REF), 
                    table_id="sun"
                ),
            ),
            iterations=3,
            delta_t=DT_CONSTANT,
            sunrise=DAWN_CONSTANT,
            location=LOC_LHASA,
            moon_tab_quarter=SINE_TAB_QUARTER,  # Plugs directly into p.moon_tab_quarter
            sun_tab_quarter=SUN_TAB_QUARTER     # Plugs directly into p.sun_tab_quarter
        )
    ),
    meta={"description": "L1 Reform: Pure declarative data"}
)

REFORM_L1 = EngineSpec(kind="rational", id=L1_SPEC.id, payload=L1_SPEC)


# ============================================================
# L2 REFORM: Evection and Variation Added
# ============================================================
L2_SERIES = AffineSinSeriesT(
    A=Fraction(0, 1),
    B=FUNDS_REF["D"].c1, 
    terms=(
        # Solar Anomaly
        SinTermT(amp=Fraction(1, 60), phase=build_phase({"M": 1}, FUNDS_REF)),
        # Lunar Evection: 2D - M'
        SinTermT(amp=Fraction(15, 1000), phase=build_phase({"D": 2, "Mp": -1}, FUNDS_REF)),
        # Lunar Variation: 2D
        SinTermT(amp=Fraction(11, 1000), phase=build_phase({"D": 2}, FUNDS_REF)),
    )
)

L2_SPEC = RationalSpec(
    id=EngineId("reform", "l2", "0.1"),
    month=trad_month(Y0=2026, M0=3, beta_star=0, tau=0, leap_labeling="first_is_leap"),
    day=RationalDayParams(
        mode="new",
        new=RationalDayParamsNew(
            series=L2_SERIES,
            iterations=4,  # Extra iteration for stability with more terms
            delta_t=DT_CONSTANT,
            sunrise=DAWN_CONSTANT,
            location=LOC_LHASA,
            sine_tab_quarter=SINE_TAB_QUARTER
        )
    ),
    meta={"description": "L2 Reform: Multi-term Picard inversion"}
)

REFORM_L2 = EngineSpec(kind="rational", id=L2_SPEC.id, payload=L2_SPEC)




# (still stub)
REFORM_L5 = EngineSpec(
    kind="fp",
    id=EngineId("reform", "l5", "0.1"),
    payload=FPSpec(
        id=EngineId("reform", "l5", "0.1"),
        meta={"note": "placeholder; fp/minimax to be implemented"},
    ),
)

REFORM_SPECS = {"reform-l1": REFORM_L1, "reform-l2": REFORM_L2, "reform-l5": REFORM_L5}

ALL_SPECS = {**TRAD_SPECS, **REFORM_SPECS}