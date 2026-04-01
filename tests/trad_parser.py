from fractions import Fraction
import math
from caltib.core.time import m0_from_trad, s0_from_trad, a0_from_trad, m1_from_trad, s1_from_trad, a1_from_trad


# ============================================================================
# 1. TRADITIONAL RATES (Mean Motions per Lunar Month)
# ============================================================================
TRAD_RATES = {
    "Siddhanta Standard (Phugpa / Tsurphu / Bhutan)": {
        "m1": {"int": 1, "frac": (31, 50, 0, 480), "rad": (60, 60, 6, 707)},
        "s1": {"int": 2, "frac": (10, 58, 1, 17),  "rad": (60, 60, 6, 67)},
        "a1": {"int": 2, "frac": (1,),             "rad": (126,)}
    },
    "Karana Standard (Early Indian Base)": {
        "m1": {"int": 1, "frac": (31, 50),         "rad": (60, 60)},
        "s1": {"int": 2, "frac": (10, 58, 2, 10),  "rad": (60, 60, 6, 13)},
        "a1": {"int": 2, "frac": (1,),             "rad": (126,)}
    },
    "Tsurphu Combined Siddhanta-Karana (Kongtrul)": {
        "m1": {"int": 1, "frac": (31, 50, 0, 30),  "rad": (60, 60, 6, 44)},
        "s1": {"int": 2, "frac": (10, 58, 2, 20),  "rad": (60, 60, 6, 38)},
        "a1": {"int": 2, "frac": (1,),             "rad": (126,)}
    },
    "Sherab Ling Semi-Reform (Kojo Tsewang Namgyal)": {
        "m1": {"int": 1, "frac": (31, 50, 0, 480), "rad": (60, 60, 6, 707)},
        "s1": {"int": 2, "frac": (10, 58, 2, 564, 5546), "rad": (60, 60, 6, 707, 6811)},
        "a1": {"int": 2, "frac": (1,),             "rad": (126,)}
    }
}

# ============================================================================
# 2. TRADITIONAL EPOCH OFFSETS
# ============================================================================
TRAD_EPOCHS = [
    {
        "name": "Original Kalacakra (806)",
        "jd": 2015531, "gza": (30, 0), "nyi": (26, 58, 0, 0, 0), "ril": (5, 112),
        "rad_gza": (60, 60), "rad_nyi": (60, 60, 6, 13), "rad_ril": (126,)
    },
    {
        "name": "Sakya Sribhadra (1206)",
        "jd": 2161884, "gza": (2, 0), "nyi": (18, 27, 47, 4, 2), "ril": (17, 28),
        "rad_gza": (60, 60), "rad_nyi": (60, 60, 6, 13), "rad_ril": (126,)
    },
    {
        "name": "Minling Lochen Dharma Sri (1681)",
        "jd": 2335140, "gza": (55, 9, 0, 522), "nyi": (26, 57, 59, 0, 42), "ril": (9, 85)
    },
    {
        "name": "Garland of White Beryl (1687)",
        "jd": 2337326, "gza": (10, 57, 2, 692), "nyi": (26, 29, 46, 3, 27), "ril": (18, 33)
    },
    {
        "name": "Flask of Essentials / Early Tsurphu (1732)",
        # Unreduced traditional equivalent fractions used here: (13, 707) and (13, 67)
        "jd": 2353745, "gza": (14, 6, 2, 2, 666), "nyi": (25, 30, 42, 0, 36), "ril": (14, 99),
        "rad_gza": (60, 60, 6, 13, 707)
    },
    {
        "name": "New Genden / Sumpa Khenpo (1747)",
        # Unreduced traditional equivalent fraction used here: (67, 707)
        "jd": 2359237, "gza": (55, 13, 3, 31, 394), "nyi": (26, 39, 51, 0, 18), "ril": (24, 22),
        "rad_gza": (60, 60, 6, 67, 707)
    },
    {
        "name": "Bhutanese Calendar (1754)",
        # Drops the 6-part "dbugs" tier
        "jd": 2361807, "gza": (4, 24, 552), "nyi": (0, 24, 10, 50), "ril": (3, 30),
        "rad_gza": (60, 60, 707), "rad_nyi": (60, 60, 67)
    },
    {
        "name": "Tukwan Lobzang (1796)",
        "jd": 2377133, "gza": (24, 44, 1, 565), "nyi": (26, 27, 45, 4, 2), "ril": (8, 52)
    },
    {
        "name": "14th Karmapa Tsurphu (1824)",
        # Unreduced traditional equivalent fraction used here: (13, 707)
        "jd": 2387351, "gza": (2, 35, 0, 10, 678), "nyi": (25, 34, 43, 5, 19), "ril": (3, 103),
        "rad_gza": (60, 60, 6, 13, 707)
    },
    {
        "name": "Jamgon Kongtrul Tsurphu (1852)",
        # Unreduced traditional equivalent fraction used here: (13, 707) and (13, 67)
        "jd": 2397598, "gza": (9, 24, 2, 5, 417), "nyi": (0, 1, 22, 2, 4, 18), "ril": (0, 72),
        "rad_gza": (60, 60, 6, 13, 707), "rad_nyi": (60, 60, 6, 13, 67)
    },
    {
        "name": "Tsurphu Combined System (1852)",
        # Includes negative offset for lunar anomaly
        "jd": 2397598, "gza": (9, 46, 1, 10), "nyi": (0, 16, 51, 3, 18), "ril": (-27, 54),
        "rad_gza": (60, 60, 6, 44), "rad_nyi": (60, 60, 6, 38)
    },
    {
        "name": "Essence of the Kalki (1927)",
        "jd": 2424972, "gza": (57, 53, 2, 20), "nyi": (25, 9, 10, 4, 32), "ril": (13, 103)
    },
    {
        "name": "Sherab Ling Reform (1987)",
        "jd": 2446884, "gza": (42, 47, 3, 465), "nyi": (25, 41, 58, 2, 25, 6655), "ril": (19, 111),
        "rad_nyi": (60, 60, 6, 707, 6811)
    }
]

def format_trad(integer, fractions, radices):
    """Formats raw data back into the text string format used by Henning."""
    frac_str = ", ".join(map(str, fractions))
    rad_str = ", ".join(map(str, radices))
    return f"{integer}; {frac_str} ({rad_str})"

# ============================================================================
# 3. EXECUTION
# ============================================================================
def main():
    print("=" * 80)
    print(f"{'1. MEAN MOTIONS (RATES) TRADITIONAL CONVERSION':^80}")
    print("=" * 80)
    
    for name, data in TRAD_RATES.items():
        print(f"\n[{name}]")
        
        # M1 (Synodic Month)
        m_int, m_frac, m_rad = data["m1"]["int"], data["m1"]["frac"], data["m1"]["rad"]
        m1_val = m1_from_trad(m_int, m_frac, m_rad)
        print(f"  m1 (Weekday Rate): {format_trad(m_int, m_frac, m_rad):<35} "
              f"-> {str(m1_val):>12}  (~{float(m1_val):.6f} days)")
        
        # S1 (Mean Sun)
        s_int, s_frac, s_rad = data["s1"]["int"], data["s1"]["frac"], data["s1"]["rad"]
        s1_val = s1_from_trad(s_int, s_frac, s_rad)
        print(f"  s1 (Solar Rate)  : {format_trad(s_int, s_frac, s_rad):<35} "
              f"-> {str(s1_val):>12}  (~{float(s1_val):.6f} turns)")

        # A1 (Anomaly)
        a_int, a_frac, a_rad = data["a1"]["int"], data["a1"]["frac"], data["a1"]["rad"]
        a1_val = a1_from_trad(a_int, a_frac, a_rad)
        print(f"  a1 (Anomaly Rate): {format_trad(a_int, a_frac, a_rad):<35} "
              f"-> {str(a1_val):>12}  (~{float(a1_val):.6f} turns)")

    print("\n\n" + "=" * 80)
    print(f"{'2. EPOCH OFFSETS TRADITIONAL CONVERSION':^80}")
    print("=" * 80)
    
    for ep in TRAD_EPOCHS:
        name = ep["name"]
        jd = ep["jd"]
        
        # Parse Radices (Default to Siddhanta if not provided)
        r_gza = ep.get("rad_gza", (60, 60, 6, 707))
        r_nyi = ep.get("rad_nyi", (60, 60, 6, 67))
        r_ril = ep.get("rad_ril", (126,))
        
        # Evaluate Fractions
        m0 = m0_from_trad(jd, ep["gza"], radices=r_gza)
        s0 = s0_from_trad(ep["nyi"][0], ep["nyi"][1:], radices=r_nyi)
        a0 = a0_from_trad(ep["ril"][0], ep["ril"][1:], radices=r_ril)
        
        print(f"\n[{name}]")
        print(f"  m0 (Julian Day)  : {jd} + {format_trad(0, ep['gza'], r_gza):<30} -> {str(m0)}")
        print(f"  s0 (Mean Sun)    : {format_trad(ep['nyi'][0], ep['nyi'][1:], r_nyi):<39} -> {str(s0)}")
        print(f"  a0 (Lunar Anomaly): {format_trad(ep['ril'][0], ep['ril'][1:], r_ril):<39} -> {str(a0)}")

if __name__ == "__main__":
    main()