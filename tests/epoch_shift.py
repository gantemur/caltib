from fractions import Fraction
from caltib.core.time import m0_from_trad, s0_from_trad, a0_from_trad

# ============================================================================
# 1. CORE RATES (Mean Motions per Lunar Month)
# ============================================================================
# Siddhanta Standard (Phugpa, Tsurphu, Bhutan, Sherab Ling)
M1_TIB = Fraction(167025, 5656)
S1_TIB = Fraction(65, 804)
A1_TIB = Fraction(253, 3528)

# Karana Standard (Kalacakra 806, Sribhadra 1206)
M1_KAR = Fraction(10631, 360)
S1_KAR = Fraction(1277, 15795)
A1_KAR = Fraction(253, 3528)

# Tsurphu Combined Standard (Kongtrul Hybrid)
# m1 ends in /44, s1 ends in /38
M1_COMB = Fraction(1, 1) + Fraction(31, 60) + Fraction(50, 3600) + Fraction(30, 3600 * 6 * 44)
S1_COMB = Fraction(2, 27) + Fraction(10, 27*60) + Fraction(58, 27*3600) + Fraction(1, 27*3600*6) + Fraction(16, 27*3600*6*38)

# Sherab Ling Refined Solar Rate
S1_SHERAB = Fraction(2, 27) + Fraction(10, 27*60) + Fraction(58, 27*3600) + Fraction(2, 27*3600*6) + Fraction(564, 27*3600*6*707) + Fraction(5546, 27*3600*6*707*6811)


# ============================================================================
# 2. HISTORICAL DATA (Grouped by Lineage)
# ============================================================================
EPOCHS = [
    # --- GROUP 1: PHUGPA LINEAGE ---
    {
        "group": "1. Standard Phugpa Lineage", "name": "Minling Lochen Dharma Sri (1681)",
        "jd": 2335140, "gza": (55, 9, 0, 522), "nyi": (26, 57, 59, 0, 42), "ril": (9, 85),
        "rates": (M1_TIB, S1_TIB, A1_TIB)
    },
    {
        "group": "1. Standard Phugpa Lineage", "name": "Garland of White Beryl (1687)",
        "jd": 2337326, "gza": (10, 57, 2, 692), "nyi": (26, 29, 46, 3, 27), "ril": (18, 33),
        "rates": (M1_TIB, S1_TIB, A1_TIB)
    },
    {
        "group": "1. Standard Phugpa Lineage", "name": "New Genden / Sumpa Khenpo (1747)",
        "jd": 2359237, "gza": (55, 13, 3, 333), "nyi": (26, 39, 51, 0, 18), "ril": (24, 22),
        "rates": (M1_TIB, S1_TIB, A1_TIB)
    },
    {
        "group": "1. Standard Phugpa Lineage", "name": "Tukwan Lobzang (1796)",
        "jd": 2377133, "gza": (24, 44, 1, 565), "nyi": (26, 27, 45, 4, 2), "ril": (8, 52),
        "rates": (M1_TIB, S1_TIB, A1_TIB)
    },
    {
        "group": "1. Standard Phugpa Lineage", "name": "Essence of the Kalki (1927)",
        "jd": 2424972, "gza": (57, 53, 2, 20), "nyi": (25, 9, 10, 4, 32), "ril": (13, 103),
        "rates": (M1_TIB, S1_TIB, A1_TIB)
    },

    # --- GROUP 2: TSURPHU LINEAGE ---
    {
        "group": "2. Standard Tsurphu Lineage", "name": "Flask of Essentials (1732)",
        "jd": 2353745, "gza": (14, 6, 2, 160), "nyi": (25, 30, 42, 0, 36), "ril": (14, 99),
        "rates": (M1_TIB, S1_TIB, A1_TIB)
    },
    {
        "group": "2. Standard Tsurphu Lineage", "name": "14th Karmapa (1824)",
        "jd": 2387351, "gza": (2, 35, 0, 596), "nyi": (25, 34, 43, 5, 19), "ril": (3, 103),
        "rates": (M1_TIB, S1_TIB, A1_TIB)
    },
    {
        "group": "2. Standard Tsurphu Lineage", "name": "Jamgon Kongtrul (1852)",
        "jd": 2397598, "gza": (9, 24, 2, 304), "nyi": (0, 1, 22, 2, 22), "ril": (0, 72),
        "rates": (M1_TIB, S1_TIB, A1_TIB)
    },

    # --- GROUP 3: EARLY INDIAN BASE ---
    {
        "group": "3. Early Karana Base", "name": "Original Kalacakra (806)",
        "jd": 2015531, "gza": (30, 0), "nyi": (26, 58, 0, 0, 0), "ril": (5, 112),
        "rad_gza": (60, 60), "rad_nyi": (60, 60, 6, 13),
        "rates": (M1_KAR, S1_KAR, A1_KAR)
    },
    {
        "group": "3. Early Karana Base", "name": "Sakya Sribhadra (1206)",
        "jd": 2161884, "gza": (2, 0), "nyi": (18, 27, 47, 4, 2), "ril": (17, 28),
        "rad_gza": (60, 60), "rad_nyi": (60, 60, 6, 13),
        "rates": (M1_KAR, S1_KAR, A1_KAR)
    },

    # --- GROUP 4: REGIONAL / HYBRIDS ---
    {
        "group": "4. Regional & Hybrids", "name": "Bhutanese Calendar (1754)",
        "jd": 2361807, "gza": (4, 24, 552), "nyi": (0, 24, 10, 50), "ril": (3, 30),
        "rad_gza": (60, 60, 707), "rad_nyi": (60, 60, 67),
        "rates": (M1_TIB, S1_TIB, A1_TIB)
    },
    {
        "group": "4. Regional & Hybrids", "name": "Tsurphu Combined (1852)",
        "jd": 2397598, "gza": (9, 46, 1, 10), "nyi": (0, 16, 51, 3, 18), "ril": (-27, 54),
        "rad_gza": (60, 60, 6, 44), "rad_nyi": (60, 60, 6, 38),
        "rates": (M1_COMB, S1_COMB, A1_TIB) # Anomaly rate is standard
    },
    {
        "group": "4. Regional & Hybrids", "name": "Sherab Ling Reform (1987)",
        "jd": 2446884, "gza": (42, 47, 3, 465), "nyi": (25, 41, 58, 2, 25, 6655), "ril": (19, 111),
        "rad_nyi": (60, 60, 6, 707, 6811),
        "rates": (M1_TIB, S1_SHERAB, A1_TIB)
    }
]

def shift_to_epoch(data, target_jd=2446914):
    """
    Parses historical data into absolute rational fractions, calculates the 
    number of lunar months (dn) between the epoch and target_jd (E1987), 
    and shifts the coordinates to that target month.
    """
    # 1. Parse raw historical data into fractions
    r_gza = data.get("rad_gza", (60, 60, 6, 707))
    r_nyi = data.get("rad_nyi", (60, 60, 6, 67))
    r_ril = data.get("rad_ril", (126,))
    
    m0 = m0_from_trad(data["jd"], data["gza"], radices=r_gza)
    s0 = s0_from_trad(data["nyi"][0], data["nyi"][1:], radices=r_nyi)
    a0 = a0_from_trad(data["ril"][0], data["ril"][1:], radices=r_ril)
    
    # 2. Extract rates
    m1, s1, a1 = data["rates"]
    
    # 3. Calculate distance in lunar months to the E1987 target
    # target_jd is roughly March 1987 (Sherab Ling epoch)
    dn = round((Fraction(target_jd) - m0) / m1)
    
    # 4. Project forward/backward by dn months
    m0_shifted = m0 + (dn * m1)
    s0_shifted = (s0 + (dn * s1)) % 1
    a0_shifted = (a0 + (dn * a1)) % 1
    
    return {
        "m0": m0, "s0": s0, "a0": a0,
        "dn": dn,
        "m0_s": m0_shifted, "s0_s": s0_shifted, "a0_s": a0_shifted
    }

# ============================================================================
# 3. EXECUTION AND DISPLAY
# ============================================================================
def main():
    print("=" * 90)
    print(f"{'EPOCH EQUIVALENCE ANALYSIS (Target ≈ E1987)':^90}")
    print("=" * 90)
    
    grouped = {}
    for ep in EPOCHS:
        grouped.setdefault(ep["group"], []).append(ep)
        
    for group_name in sorted(grouped.keys()):
        print(f"\n{group_name.upper()}")
        print("-" * 90)
        print(f"{'Name':<35} | {'Shift (Δ Months)':<18} | {'Shifted m0 (Mean Weekday)':<25}")
        print("-" * 90)
        
        for ep in grouped[group_name]:
            res = shift_to_epoch(ep)
            name = ep["name"]
            
            # Print the shift info and m0 equivalence
            print(f"{name:<35} | {res['dn']:>8} months   | {str(res['m0_s']):<25}")
            
            # Print s0 and a0 equivalence indented
            print(f"{'':<35} | {'-> Shifted s0:':<18} | {str(res['s0_s']):<25}")
            print(f"{'':<35} | {'-> Shifted a0:':<18} | {str(res['a0_s']):<25}")
            print()

if __name__ == "__main__":
    main()