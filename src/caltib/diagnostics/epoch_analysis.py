import argparse
import math
from fractions import Fraction
from typing import Iterable, Sequence, Tuple, Optional

# Optional dependency. If caltib is unavailable, use exact local fallbacks.
try:
    from caltib.core.time import m0_from_trad as _m0_from_trad
    from caltib.core.time import s0_from_trad as _s0_from_trad
    from caltib.core.time import a0_from_trad as _a0_from_trad
except Exception:  # pragma: no cover - fallback path is intentional
    _m0_from_trad = _s0_from_trad = _a0_from_trad = None


# ============================================================================
# 1. CORE CONSTANTS & RATES
# ============================================================================
M1_TIB = Fraction(167025, 5656)
S1_TIB = Fraction(65, 804)
A1_TIB = Fraction(253, 3528)

M1_KAR = Fraction(10631, 360)
S1_KAR = Fraction(1277, 15795)
A1_KAR = Fraction(253, 3528)

M1_COMB = Fraction(311843, 10560)
S1_COMB = Fraction(553, 6840)

S1_SHERAB = Fraction(3114525, 38523016)

# Base epoch for Meeus Lunations
MEEUS_L0_JD = Fraction("2451550.09766")
MEEUS_LUNATION_DAYS = Fraction("29.530588861")


# ============================================================================
# 2. HISTORICAL EPOCHS
# ============================================================================
EPOCHS = [
    {
        "group": "Non-Standard & Early Models", "name": "Karana (Original Kalacakra 806)",
        "jd": 2015531, "gza": (30, 0), "nyi": (26, 58, 0, 0, 0), "ril": (5, 112),
        "rad_gza": (60, 60), "rad_nyi": (60, 60, 6, 13), "rad_ril": (126,),
        "rates": (M1_KAR, S1_KAR, A1_KAR), "rad_m1": (60, 60), "rad_s1": (60, 60, 6, 13),
        "y0": 806, "m0_month": 3, "beta_star": 0, "P": 65, "Q": 67, "ell": 2, "tau_ref": 63
    },
    {
        "group": "Non-Standard & Early Models", "name": "Sakya Sribhadra (1206)",
        "jd": 2161884, "gza": (2, 0), "nyi": (18, 27, 47, 4, 2), "ril": (17, 28),
        "rad_gza": (60, 60), "rad_nyi": (60, 60, 6, 13), "rad_ril": (126,),
        "rates": (M1_KAR, S1_KAR, A1_KAR), "rad_m1": (60, 60), "rad_s1": (60, 60, 6, 13),
        "y0": 1206, "m0_month": 3, "beta_star": 0, "P": 65, "Q": 67, "ell": 2, "tau_ref": 63
    },
    {
        "group": "Non-Standard & Early Models", "name": "Tukwan Lobzang (1796)",
        "jd": 2377133, "gza": (24, 44, 1, 565), "nyi": (26, 27, 45, 4, 2), "ril": (8, 52),
        "rates": (M1_TIB, S1_TIB, A1_TIB), "rad_m1": (60, 60, 6, 707), "rad_s1": (60, 60, 6, 67),
        "y0": 1796, "m0_month": 3, "beta_star": 16, "P": 65, "Q": 67, "ell": 2, "tau_ref": 0
    },
    {
        "group": "Non-Standard & Early Models", "name": "Tsurphu Combined Siddhanta-Karana (1852)",
        "jd": 2397598, "gza": (9, 46, 1, 10), "nyi": (0, 16, 51, 3, 18), "ril": (-27, 54),
        "rad_gza": (60, 60, 6, 44), "rad_nyi": (60, 60, 6, 38), "rad_ril": (126,),
        "rates": (M1_COMB, S1_COMB, A1_TIB), "rad_m1": (60, 60, 6, 44), "rad_s1": (60, 60, 6, 38),
        "y0": 1852, "m0_month": 3, "beta_star": -51, "P": 65, "Q": 67, "ell": 2, "tau_ref": 0
    },
    {
        "group": "Non-Standard & Early Models", "name": "Sherab Ling Reform (1987)",
        "jd": 2446884, "gza": (42, 47, 3, 465), "nyi": (25, 41, 58, 2, 25, 6655), "ril": (19, 111),
        "rad_nyi": (60, 60, 6, 707, 6811), "rad_m1": (60, 60, 6, 707), "rad_s1": (60, 60, 6, 707, 6811),
        "rates": (M1_TIB, S1_SHERAB, A1_TIB),
        "y0": 1987, "m0_month": 2, "beta_star": 38, "P": 65, "Q": 67, "ell": 2, "tau_ref": 0
    },
    {
        "group": "Equivalence Classes: Standard", "name": "Phugpa: Minling Lochen Dharma Sri (1681)",
        "jd": 2335140, "gza": (55, 9, 0, 522), "nyi": (26, 57, 59, 0, 42), "ril": (9, 85),
        "rates": (M1_TIB, S1_TIB, A1_TIB), "rad_m1": (60, 60, 6, 707), "rad_s1": (60, 60, 6, 67),
        "y0": 1681, "m0_month": 3, "beta_star": 1, "P": 65, "Q": 67, "ell": 2, "tau_ref": 48
    },
    {
        "group": "Equivalence Classes: Standard", "name": "Phugpa: Garland of White Beryl (1687)",
        "jd": 2337326, "gza": (10, 57, 2, 692), "nyi": (26, 29, 46, 3, 27), "ril": (18, 33),
        "rates": (M1_TIB, S1_TIB, A1_TIB), "rad_m1": (60, 60, 6, 707), "rad_s1": (60, 60, 6, 67),
        "y0": 1687, "m0_month": 3, "beta_star": 15, "P": 65, "Q": 67, "ell": 2, "tau_ref": 48
    },
    {
        "group": "Equivalence Classes: Standard", "name": "Phugpa: Essence of the Kalki (1927)",
        "jd": 2424972, "gza": (57, 53, 2, 20), "nyi": (25, 9, 10, 4, 32), "ril": (13, 103),
        "rates": (M1_TIB, S1_TIB, A1_TIB), "rad_m1": (60, 60, 6, 707), "rad_s1": (60, 60, 6, 67),
        "y0": 1927, "m0_month": 3, "beta_star": 55, "P": 65, "Q": 67, "ell": 2, "tau_ref": 48
    },
    {
        "group": "Equivalence Classes: Standard", "name": "Phugpa: Base Epoch (1987)",
        "jd": 2446914, "gza": (11, 27, 2, 332), "nyi": (0, 0, 0, 0, 0), "ril": (21, 90),
        "rates": (M1_TIB, S1_TIB, A1_TIB), "rad_m1": (60, 60, 6, 707), "rad_s1": (60, 60, 6, 67),
        "y0": 1987, "m0_month": 3, "beta_star": 0, "P": 65, "Q": 67, "ell": 2, "tau_ref": 48
    },
    {
        "group": "Equivalence Classes: Standard", "name": "Tsurphu: Flask of Essentials (1732)",
        "jd": 2353745, "gza": (14, 6, 2, 2, 666), "nyi": (25, 30, 42, 0, 36), "ril": (14, 99),
        "rad_gza": (60, 60, 6, 13, 707),
        "rates": (M1_TIB, S1_TIB, A1_TIB), "rad_m1": (60, 60, 6, 707), "rad_s1": (60, 60, 6, 67),
        "y0": 1732, "m0_month": 3, "beta_star": 59, "P": 65, "Q": 67, "ell": 2, "tau_ref": 0
    },
    {
        "group": "Equivalence Classes: Standard", "name": "Tsurphu: 14th Karmapa (1824)",
        "jd": 2387351, "gza": (2, 35, 0, 10, 678), "nyi": (25, 34, 43, 5, 19), "ril": (3, 103),
        "rad_gza": (60, 60, 6, 13, 707),
        "rates": (M1_TIB, S1_TIB, A1_TIB), "rad_m1": (60, 60, 6, 707), "rad_s1": (60, 60, 6, 67),
        "y0": 1824, "m0_month": 3, "beta_star": 57, "P": 65, "Q": 67, "ell": 2, "tau_ref": 0
    },
    {
        "group": "Equivalence Classes: Standard", "name": "Tsurphu: Jamgon Kongtrul (1852)",
        "jd": 2397598, "gza": (9, 24, 2, 5, 417), "nyi": (0, 1, 22, 2, 4, 18), "ril": (0, 72),
        "rad_gza": (60, 60, 6, 13, 707), "rad_nyi": (60, 60, 6, 13, 67),
        "rates": (M1_TIB, S1_TIB, A1_TIB), "rad_m1": (60, 60, 6, 707), "rad_s1": (60, 60, 6, 67),
        "y0": 1852, "m0_month": 3, "beta_star": 14, "P": 65, "Q": 67, "ell": 2, "tau_ref": 0
    },
    {
        "group": "Equivalence Classes: Standard", "name": "Bhutanese Calendar (1754)",
        "jd": 2361807, "gza": (4, 24, 552), "nyi": (0, 24, 10, 50), "ril": (3, 30),
        "rad_gza": (60, 60, 707), "rad_nyi": (60, 60, 67), "rad_ril": (126,),
        "rates": (M1_TIB, S1_TIB, A1_TIB), "rad_m1": (60, 60, 6, 707), "rad_s1": (60, 60, 6, 67),
        "y0": 1754, "m0_month": 3, "beta_star": 2, "P": 65, "Q": 67, "ell": 2, "tau_ref": 57
    },
    {
        "group": "Equivalence Classes: Standard", "name": "Mongol / Sumpa Khenpo (1747)",
        "jd": 2359237, "gza": (55, 13, 3, 31, 394), "nyi": (26, 39, 51, 0, 18), "ril": (24, 22),
        "rad_gza": (60, 60, 6, 67, 707),
        "rates": (M1_TIB, S1_TIB, A1_TIB), "rad_m1": (60, 60, 6, 707), "rad_s1": (60, 60, 6, 67),
        "y0": 1747, "m0_month": 3, "beta_star": 10, "P": 65, "Q": 67, "ell": 2, "tau_ref": 46
    }
]


# ============================================================================
# 3. DATE & MATH UTILITIES
# ============================================================================
def as_fraction(x) -> Fraction:
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x, 1)
    return Fraction(str(x))


def mixed_to_fraction(parts: Sequence[int], radices: Sequence[int]) -> Fraction:
    if len(parts) == 0:
        return Fraction(0, 1)
    if len(parts) - 1 > len(radices):
        raise ValueError("Not enough radices for mixed-radix value")
    out = Fraction(parts[0], 1)
    denom = 1
    for p, r in zip(parts[1:], radices):
        denom *= r
        out += Fraction(p, denom)
    return out


def m0_from_trad(jd: int, gza: Sequence[int], radices: Sequence[int]) -> Fraction:
    if _m0_from_trad is not None:
        return _m0_from_trad(jd, gza, radices=tuple(radices))
    return Fraction(jd, 1) + mixed_to_fraction(gza, radices) / 60


def s0_from_trad(head: int, tail: Sequence[int], radices: Sequence[int]) -> Fraction:
    if _s0_from_trad is not None:
        return _s0_from_trad(head, tail, radices=tuple(radices))
    return (mixed_to_fraction((head, *tail), radices) / 27) % 1


def a0_from_trad(head: int, tail: Sequence[int], radices: Sequence[int]) -> Fraction:
    if _a0_from_trad is not None:
        return _a0_from_trad(head, tail, radices=tuple(radices))
    return (mixed_to_fraction((head, *tail), radices) / 28) % 1


def greg_to_jd(year: int, month: int, day: int) -> Fraction:
    if month <= 2:
        year -= 1
        month += 12
    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    jd = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5
    return as_fraction(jd)


def parse_target(target_str: str) -> Fraction:
    s = target_str.strip()
    if "/" in s or "-" in s:
        s = s.replace("/", "-")
        y, m, d = map(int, s.split("-"))
        return greg_to_jd(y, m, d)

    if s.lower().startswith(("k:", "lun:", "meeus:")):
        val = as_fraction(s.split(":", 1)[1])
        return MEEUS_L0_JD + val * MEEUS_LUNATION_DAYS

    val = as_fraction(s)
    # Preserve original heuristic, but make it exact.
    if abs(val) < 50000:
        return MEEUS_L0_JD + val * MEEUS_LUNATION_DAYS
    return val


def format_trad(val: Fraction, multiplier: int, radices: Tuple[int, ...], show_residue: bool = False) -> str:
    """Format a rational value in mixed radix. multiplier=1 uses weekday-style mod 7."""
    if multiplier > 1:
        v = (val % 1) * multiplier
    else:
        v = val % 7

    int_part = math.floor(v)
    rem = v - int_part
    fracs = []
    for r in radices:
        rem *= r
        part = math.floor(rem)
        fracs.append(part)
        rem -= part

    rad_str = ", ".join(map(str, radices))
    frac_str = ", ".join(map(str, fracs))
    res = f"{int_part}; {frac_str} ({rad_str})"
    if show_residue and rem != 0:
        res += f" [+{float(rem):.6f} rem]"
    return res


# ============================================================================
# 4. ASTRO-ARITHMETIC
# ============================================================================


def _effective_beta_for_sgang(beta_star: int, month_offset: int, P: int, ell: int) -> int:
    """
    Remove the source-specific displayed-month override.

    month_offset is computed ONCE from the original source epoch and then preserved
    under shifting. Example:
        Phugpa 1927: month_offset = -1
        most others: month_offset = 0
    """
    return (beta_star + ell * month_offset) % P

def compute_tau(
    s0: Fraction,
    sgang1_deg: float,
    beta_star: int,
    M0: int,
    month_offset: int = 0,
    P: int = 65,
    Q: int = 67,
    ell: int = 2,
) -> int:
    """
    Compute tau from s0 and sgang1, using the preserved source-specific month offset.
    """
    d1 = (as_fraction(sgang1_deg) - 30) / 360
    beta_eff = _effective_beta_for_sgang(beta_star, month_offset, P, ell)
    M_true = M0 + month_offset

    for test_tau in range(P):
        gamma_shift = (P - test_tau) % P
        beta_int = beta_eff + gamma_shift

        d_n0 = (d1 + Fraction(M_true - 1, 12)) % 1
        alpha = (12 * (s0 - d_n0)) % 1
        gamma = math.floor(Q * alpha) + 1
        calc_tau = int((beta_eff + gamma - ell) % P)

        if calc_tau == test_tau:
            return test_tau
    return -1


def compute_sgang1_range(
    s0: Fraction,
    tau: int,
    beta_star: int,
    M0: int,
    month_offset: int = 0,
    P: int = 65,
    Q: int = 67,
    ell: int = 2,
) -> Tuple[float, float]:
    """
    Compute the valid sgang1 interval implied by tau, using the preserved source-specific
    month offset rather than trying to infer it again from the shifted displayed state.
    """
    beta_eff = _effective_beta_for_sgang(beta_star, month_offset, P, ell)
    M_true = M0 + month_offset

    gamma = (ell + tau - beta_eff) % P
    if gamma == 0:
        gamma = P

    denom = 12 * Q
    d_n0_min = s0 - Fraction(gamma, denom)
    d_n0_max = s0 - Fraction(gamma - 1, denom)

    d1_min = (d_n0_min - Fraction(M_true - 1, 12)) % 1
    d1_max = (d_n0_max - Fraction(M_true - 1, 12)) % 1

    sgang1_min = (float(d1_min) * 360.0 + 30.0) % 360.0
    sgang1_max = (float(d1_max) * 360.0 + 30.0) % 360.0
    if sgang1_max < sgang1_min:
        sgang1_max += 360.0

    return sgang1_min, sgang1_max


# ============================================================================
# 5. CORE SHIFT LOGIC
# ============================================================================


def _solve_display_state(
    y0: int,
    m0_month: int,
    beta_star: int,
    mstar_0: int,
    delta_mstar: int,
    tau_ref: int,
    P: int,
    Q: int,
    ell: int,
) -> Tuple[int, int, int]:
    """Recover the displayed (Y0, M0, β*) state after shifting.

    The arithmetic month shift naturally propagates the *effective* month geometry. Some published
    epochs, however, keep the displayed M0 one sign ahead of the actual civil month current at n=0,
    and compensate by using a correspondingly shifted raw β*. To preserve that convention under
    epoch shifting, we reconstruct the displayed state from the shifted effective geometry.
    """
    beta_eff_target = (beta_star + ell * (delta_mstar + mstar_0)) % P
    actual_abs = (y0 * 12 + (m0_month - 1)) + delta_mstar + mstar_0

    candidates = []
    for k in range(-3, 4):
        beta_raw = (beta_eff_target - ell * k) % P
        mstar_check = math.floor((-(beta_raw + (P - tau_ref) % P) - 1) / Q) + 1
        if mstar_check == k:
            disp_abs = actual_abs - k
            y_out = disp_abs // 12
            m_out = (disp_abs % 12) + 1
            candidates.append((abs(k), y_out, m_out, beta_raw))

    if not candidates:
        # Fallback to the normalized form if no displayed override is needed/found.
        disp_abs = (y0 * 12 + (m0_month - 1)) + delta_mstar
        return disp_abs // 12, (disp_abs % 12) + 1, (beta_star + delta_mstar * ell) % P

    _, y_out, m_out, beta_raw = min(candidates)
    return y_out, m_out, beta_raw

def shift_epoch(data, target_jd: Optional[Fraction]):
    r_gza = data.get("rad_gza", (60, 60, 6, 707))
    r_nyi = data.get("rad_nyi", (60, 60, 6, 67))
    r_ril = data.get("rad_ril", (126,))

    m0 = m0_from_trad(data["jd"], data["gza"], radices=r_gza)
    s0 = s0_from_trad(data["nyi"][0], data["nyi"][1:], radices=r_nyi)
    a0 = a0_from_trad(data["ril"][0], data["ril"][1:], radices=r_ril)
    m1, s1, a1 = data["rates"]

    dn = 0 if target_jd is None else round((as_fraction(target_jd) - m0) / m1)

    P = data.get("P", 65)
    Q = data.get("Q", 67)
    ell = data.get("ell", 2)
    tau_ref = data.get("tau_ref", 0)

    gamma_shift = (P - tau_ref) % P
    beta_int = data["beta_star"] + gamma_shift
    # Source-specific displayed-month offset:
    # actual month at n=0 is M0 + month_offset_src
    month_offset_src = math.floor((-(beta_int) - 1) / Q) + 1

    mstar_dn = math.floor((P * dn - beta_int - 1) / Q) + 1
    mstar_0 = math.floor((-(beta_int) - 1) / Q) + 1
    delta_mstar = mstar_dn - mstar_0

    y0_s, m0_month_s, beta_star_s = _solve_display_state(
        data["y0"], data["m0_month"], data["beta_star"], mstar_0, delta_mstar,
        tau_ref, P, Q, ell,
    )

    m0_s = m0 + dn * m1
    s0_s = (s0 + dn * s1) % 1
    a0_s = (a0 + dn * a1) % 1

    return {
    "m0_s": m0_s, "s0_s": s0_s, "a0_s": a0_s, "dn": dn,
    "m1": m1, "s1": s1, "a1": a1,
    "y0_s": y0_s, "m0_month_s": m0_month_s, "beta_star_s": beta_star_s,
    "P": P, "Q": Q, "ell": ell,
    "month_offset_src": month_offset_src,
    }


# ============================================================================
# 6. CLI EXECUTION
# ============================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Tibetan Epoch Shifting & Diagnostics Tool")
    parser.add_argument("-t", "--target", help="Target date (YYYY-MM-DD), JD, or Meeus lunation index.")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--sgang1", type=float, help="Solar term anchor (sgang1_deg) to compute tau")
    grp.add_argument("--tau", type=int, help="Solar phase shift (tau) to compute valid sgang1_deg ranges")
    args = parser.parse_args()

    target_jd = parse_target(args.target) if args.target is not None else None

    print(f"\n{'=' * 85}")
    if target_jd is not None:
        print(f" TARGET RESOLVED TO JULIAN DAY: {float(target_jd):.8f}")
    else:
        print(" NO TARGET PROVIDED. DISPLAYING ORIGINAL EPOCH CONSTANTS.")
    print(f"{'=' * 85}\n")

    grouped = {}
    for ep in EPOCHS:
        grouped.setdefault(ep["group"], []).append(ep)

    for group_name, eps in grouped.items():
        print(f" {group_name.upper()}")
        print("-" * 85)
        for ep in eps:
            res = shift_epoch(ep, target_jd)
            r_m = ep.get("rad_m1", (60, 60, 6, 707))
            r_s = ep.get("rad_s1", (60, 60, 6, 67))
            r_a = ep.get("rad_ril", (126,))

            print(f" ❖ {ep['name']}  |  Shift (Δn) = {res['dn']} months")
            
            eff_beta = _effective_beta_for_sgang(
                res['beta_star_s'],
                res['month_offset_src'],
                res['P'],
                res['ell'],
            )
            eff_month = res['m0_month_s'] + res['month_offset_src']

            print(f"    ├─ Published State: Y0 = {res['y0_s']} | M0 = {res['m0_month_s']} | β* = {res['beta_star_s']}")
            if res['month_offset_src'] != 0:
                print(f"    ├─ Sgang Geometry : M_true = {eff_month} | β_eff = {eff_beta} | offset = {res['month_offset_src']} month(s)")
            
            print(f"    ├─ m0: {str(res['m0_s']):<22} ->  {format_trad(res['m0_s'], 1, r_m)}")
            print(f"    ├─ s0: {str(res['s0_s']):<22} ->  {format_trad(res['s0_s'], 27, r_s)}")
            print(f"    ├─ a0: {str(res['a0_s']):<22} ->  {format_trad(res['a0_s'], 28, r_a)}")
            print(f"    ├─ m1: {str(res['m1']):<22} ->  {format_trad(res['m1'], 1, r_m)}")
            print(f"    ├─ s1: {str(res['s1']):<22} ->  {format_trad(res['s1'], 27, r_s)}")
            print(f"    ├─ a1: {str(res['a1']):<22} ->  {format_trad(res['a1'], 28, r_a)}")

            if args.sgang1 is not None:
                tau_calc = compute_tau(
                    res['s0_s'],
                    args.sgang1,
                    res['beta_star_s'],
                    res['m0_month_s'],
                    month_offset=res['month_offset_src'],
                    P=res['P'],
                    Q=res['Q'],
                    ell=res['ell'],
                )
                print(f"    └─ ⮑ [Given sgang1 = {args.sgang1}°] Calculated τ = {tau_calc}")

            else:
                tau_use = args.tau if args.tau is not None else ep.get("tau_ref", None)
                if tau_use is not None:
                    sg_min, sg_max = compute_sgang1_range(
                        res['s0_s'],
                        tau_use,
                        res['beta_star_s'],
                        res['m0_month_s'],
                        month_offset=res['month_offset_src'],
                        P=res['P'],
                        Q=res['Q'],
                        ell=res['ell'],
                    )
                    tag = "Given" if args.tau is not None else "Reference"
                    print(f"    └─ ⮑ [{tag} τ = {tau_use}] implies sgang1_deg ∈ ({sg_min:.4f}°, {sg_max:.4f}°]")
            print()


if __name__ == "__main__":
    main()
