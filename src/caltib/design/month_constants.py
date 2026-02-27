import argparse
import math
import sys
from datetime import date, timedelta
from typing import Optional, List

from caltib.reference.astro_args import (
    jde_mean_new_moon,
    T_centuries,
    solar_mean_elements
)
from caltib.reference.time_scales import (
    jd_tt_to_jd_utc,
    jd_utc_to_jd_tt,
    jd_to_jdn,
    jdn_to_date,
    date_to_jdn
)

def amod12(x: int) -> int:
    """Arithmetic mod giving 1..12."""
    return ((x - 1) % 12) + 1

def find_date_for_solar_longitude(year: int, target_deg: float) -> date:
    """Scans the given year to find the Gregorian date where the Mean Sun is closest to target_deg."""
    best_date = date(year, 1, 1)
    min_diff = 400.0
    for d in range(1, 367):
        test_date = date(year, 1, 1) + timedelta(days=d-1)
        if test_date.year != year:
            break
        
        target_jd_utc = float(date_to_jdn(test_date))
        target_jd_tt = jd_utc_to_jd_tt(target_jd_utc)
        T_target = T_centuries(target_jd_tt)
        l0 = solar_mean_elements(T_target).L0_deg
        
        # Shortest angular distance
        diff = abs((l0 - target_deg + 180.0) % 360.0 - 180.0)
        if diff < min_diff:
            min_diff = diff
            best_date = test_date
            
    return best_date

def compute_constants(P: int, Q: int, k: int, d1_deg: Optional[float], d1_date: Optional[str]) -> dict:
    # 1. Astronomical evaluation at epoch lunation (TT)
    jd_tt = jde_mean_new_moon(float(k))
    T = T_centuries(jd_tt)
    solar_elements = solar_mean_elements(T)
    s0 = solar_elements.L0_turn
    
    # Precise Civil Date conversion via time_scales stack
    jd_utc = jd_tt_to_jd_utc(jd_tt)
    jdn = jd_to_jdn(jd_utc)
    epoch_date = jdn_to_date(jdn)
    
    # 2. Resolve the mutually exclusive d1 / d1_date inputs
    derived_from_date = False
    
    # Apply standard fallback if neither is provided
    if d1_date is None and d1_deg is None:
        d1_date = "02/26"
        
    if d1_date is not None:
        # User gave a date, we derive exact d1_deg
        parts = d1_date.replace("/", "-").split("-")
        m_d1, d_d1 = int(parts[0]), int(parts[1])
        
        target_date = date(epoch_date.year, m_d1, d_d1)
        target_jd_utc = float(date_to_jdn(target_date)) 
        target_jd_tt = jd_utc_to_jd_tt(target_jd_utc)
        T_target = T_centuries(target_jd_tt)
        
        d1_deg = solar_mean_elements(T_target).L0_deg
        derived_from_date = True
        d1_date_str = d1_date
    else:
        # User gave a degree (or hit the 308.0 default), we derive approximate date
        best_date = find_date_for_solar_longitude(epoch_date.year, d1_deg)
        d1_date_str = best_date.strftime("%m-%d")
    
    # 3. Phase shift logic
    d0_deg = d1_deg - 30.0
    d0_turns = (d0_deg / 360.0) % 1.0
    
    # α = 12(s_0 - d_0)
    alpha = 12.0 * (s0 - d0_turns)
    
    # Fractional phase for alignment
    theta = alpha % 1.0
    
    # Find nearest integer r such that θ ≈ r/Q
    r = round(theta * Q)
    if r == Q:
        r = 0
        
    # Phase constant γ_0^* ≡ q - 1 - r (mod p)
    gamma_0_star = (Q - 1 - r) % P
    beta_star = gamma_0_star
    
    # 4. Determine Y0, M0, and leap/trigger status
    A0 = math.floor(alpha)
    M0 = amod12(A0)
    Y0 = epoch_date.year
    
    ell = Q - P
    is_trigger = beta_star < ell
        
    return {
        "k": k,
        "date": epoch_date,
        "s0": s0,
        "d1_deg": d1_deg,
        "d1_date_str": d1_date_str,
        "derived_from_date": derived_from_date,
        "alpha": alpha,
        "theta": theta,
        "r": r,
        "beta_star": beta_star,
        "tau": 0,
        "Y0": Y0,
        "M0": M0,
        "ell": ell,
        "is_trigger": is_trigger,
        "error_turns": abs(theta - (r / Q))
    }

def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
        
    parser = argparse.ArgumentParser(
        prog="caltib month-constants", 
        description="Design tool for rational month constants."
    )
    parser.add_argument("--P", type=int, default=1336, help="Numerator of mean motion")
    parser.add_argument("--Q", type=int, default=1377, help="Denominator of mean motion")
    parser.add_argument("--k", type=int, default=-157, help="Meeus lunation index (e.g. -157 for April 1987)")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--d1-date", type=str, default=None, help="Gregorian date (MM-DD or MM/DD) to anchor Month 1. (Default: 02/26)")
    group.add_argument("--d1", type=float, default=None, help="Definition point offset for Month 1 in degrees.")
    
    args = parser.parse_args(argv)
    
    res = compute_constants(args.P, args.Q, args.k, args.d1, args.d1_date)
    
    print("==================================================")
    print(" RATIONAL MONTH CONSTANT GENERATOR")
    print("==================================================")
    print(f"Inputs: P={args.P}, Q={args.Q}, Lunation={args.k}")
    
    if res["derived_from_date"]:
        print(f"Target Anchor Date: {res['d1_date_str']} -> Exact d1 = {res['d1_deg']:.6f}°")
    else:
        print(f"Target Anchor d1: {res['d1_deg']:.6f}° -> Approx Date = {res['d1_date_str']}")
        
    print(f"Epoch Date: {res['date'].strftime('%Y-%m-%d')} (Precise UTC)")
    print(f"Mean Sun Phase (s0): {res['s0']:.6f} turns")
    print("--------------------------------------------------")
    print(f"Alpha: {res['alpha']:.6f}")
    print(f"Theta (Fractional Phase): {res['theta']:.6f}")
    print(f"Nearest Rational Grid Point (r/Q): {res['r']} / {args.Q}")
    print(f"Approximation Error: {res['error_turns'] * 12 * 30:.4f} civil days")
    print("--------------------------------------------------")
    print("GENERATED SPECIFICATION CONSTANTS:")
    print(f"  beta_star  = {res['beta_star']}")
    print(f"  tau        = {res['tau']}")
    print(f"  Y0         = {res['Y0']}")
    print(f"  M0         = {res['M0']} (Rigidly derived from d1)")
    
    trigger_str = "YES (Epoch lunation is the 2nd occurrence)" if res['is_trigger'] else "NO"
    op_str = "<" if res['is_trigger'] else ">="
    print(f"  Epoch Leap = {trigger_str} (beta_star={res['beta_star']} {op_str} ell={res['ell']})")
    print("==================================================")
    return 0

if __name__ == "__main__":
    sys.exit(main())