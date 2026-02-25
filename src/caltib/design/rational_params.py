# design/rational_params.py

from __future__ import annotations

import argparse
import math
import sys
from typing import Callable, List, Optional, Tuple

from caltib.reference import astro_args as aa


def get_convergents(x: float, max_den: int = 2000000) -> List[Tuple[int, int]]:
    """
    Generates the continued fraction convergents (p, q) for a real number x.
    Stops when the denominator exceeds max_den or the remainder is indistinguishable from 0.
    """
    convergents = []
    a = math.floor(x)
    rem = x - a
    
    h_prev2, k_prev2 = 0, 1
    h_prev1, k_prev1 = 1, 0
    h, k = a, 1

    while k <= max_den:
        convergents.append((h, k))
        if rem < 1e-12:
            break
            
        inv = 1.0 / rem
        a = math.floor(inv)
        rem = inv - a
        
        h_new = a * h + h_prev1
        k_new = a * k + k_prev1
        
        h_prev1, k_prev1 = h, k
        h, k = h_new, k_new

    return convergents


class ParameterDefinition:
    def __init__(self, name: str, value: float, unit: str, error_func: Callable[[float, float], str]):
        self.name = name
        self.value = value
        self.unit = unit
        self.error_func = error_func


def _err_seconds_per_cycle(approx: float, exact: float) -> str:
    """Error converted to seconds per cycle (for days/cycle periods)."""
    err_sec = (approx - exact) * 86400.0
    return f"{err_sec:+.10f} s"

def _err_arcsec(approx: float, exact: float) -> str:
    """Error converted to arcseconds (for angular measurements in degrees)."""
    err_arcsec = (approx - exact) * 3600.0
    return f"{err_arcsec:+.10f} \""

def _err_ppm(approx: float, exact: float) -> str:
    """Error in Parts Per Million (for dimensionless ratios)."""
    err_ppm = ((approx - exact) / exact) * 1e6
    return f"{err_ppm:+.10f} ppm"

def _err_arcsec_per_day(approx: float, exact: float) -> str:
    """Error in arcseconds per day (for daily angular rates)."""
    err_arcsec = (approx - exact) * 3600.0
    return f"{err_arcsec:+.10f} \"/d"


def build_parameters(jd_tt: float) -> List[ParameterDefinition]:
    """Evaluates and builds the list of target astronomical parameters for the given epoch."""
    T = aa.T_centuries(jd_tt)
    E = aa.eccentricity_factor(T)
    
    # 1. Periods (Days)
    y_trop = aa.tropical_year_days(T)
    s_syn = aa.synodic_month_days(T)
    s_anom = aa.anomalistic_month_days(T)
    y_anom = aa.anomalistic_year_days(T)
    
    # 2. Ratios
    ratio_y_s = y_trop / s_syn
    
    # 3. Mean Angles at Epoch (Degrees)
    sm = aa.solar_mean_elements(T)
    fa = aa.fundamental_args(T)
    
    # 4. Rates at Epoch (Degrees per day)
    # Derivative of F = 93.272... + 483202.0175233*T - 0.0036539*T^2 ...
    rate_F_century = 483202.0175233 - 2 * 0.0036539 * T - 3 * (T**2 / 3526000.0)
    rate_F_day = rate_F_century / 36525.0
    
    # 5. Amplitudes at Epoch (Degrees)
    amp_solar_1 = 1.914602 - 0.004817 * T - 0.000014 * (T**2)
    amp_major_ineq = 6288774e-6
    amp_evection = 1274027e-6
    amp_variation = 658314e-6
    amp_2nd_elliptic = 213618e-6
    amp_annual_eq = 185116e-6 * E  # Applying the Eccentricity factor
    amp_reduction = 114332e-6
    
    return [
        ParameterDefinition("Tropical Year", y_trop, "days", _err_seconds_per_cycle),
        ParameterDefinition("Synodic Month", s_syn, "days", _err_seconds_per_cycle),
        ParameterDefinition("Anomalistic Month", s_anom, "days", _err_seconds_per_cycle),
        ParameterDefinition("Anomalistic Year", y_anom, "days", _err_seconds_per_cycle),
        ParameterDefinition("Ratio: Trop Year / Syn Month", ratio_y_s, "months", _err_ppm),
        ParameterDefinition("Solar Mean Longitude (L0)", sm.L0_deg, "deg", _err_arcsec),
        ParameterDefinition("Lunar Mean Longitude (L')", fa.Lp_deg, "deg", _err_arcsec),
        ParameterDefinition("Mean Elongation (D)", fa.D_deg, "deg", _err_arcsec),
        ParameterDefinition("Solar Mean Anomaly (M)", sm.M_deg, "deg", _err_arcsec),
        ParameterDefinition("Lunar Mean Anomaly (M')", fa.Mp_deg, "deg", _err_arcsec),
        ParameterDefinition("Mean F", fa.F_deg, "deg", _err_arcsec),
        ParameterDefinition("Rate of F", rate_F_day, "deg/d", _err_arcsec_per_day),
        ParameterDefinition("Amplitude: Solar Eq. of Center", amp_solar_1, "deg", _err_arcsec),
        ParameterDefinition("Amplitude: Lunar Major Ineq.", amp_major_ineq, "deg", _err_arcsec),
        ParameterDefinition("Amplitude: Lunar Evection", amp_evection, "deg", _err_arcsec),
        ParameterDefinition("Amplitude: Lunar Variation", amp_variation, "deg", _err_arcsec),
        ParameterDefinition("Amplitude: Lunar 2nd Elliptic", amp_2nd_elliptic, "deg", _err_arcsec),
        ParameterDefinition("Amplitude: Lunar Annual Eq.", amp_annual_eq, "deg", _err_arcsec),
        ParameterDefinition("Amplitude: Lunar Red. to Ecliptic", amp_reduction, "deg", _err_arcsec),
    ]


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Generate rational convergents for astronomical parameters.")
    p.add_argument("--jd-tt", type=float, default=2451545.0, help="Epoch in JD(TT). Default is J2000.0.")
    p.add_argument("--max-den", type=int, default=1000000, help="Maximum denominator for convergents.")
    p.add_argument("--out-txt", type=str, default="", help="Optional file to save the output table.")
    args = p.parse_args(argv)

    params = build_parameters(args.jd_tt)
    
    lines = []
    lines.append(f"Rational Approximants (Convergents) for Epoch JD(TT) = {args.jd_tt}")
    lines.append("=" * 90)
    
    for param in params:
        lines.append(f"\n--- {param.name} ---")
        lines.append(f"Target Value: {param.value:.10f} {param.unit}")
        lines.append(f"{'Fraction (p/q)':<25} | {'Decimal Approximation':<25} | {'Error'}")
        lines.append("-" * 90)
        
        convergents = get_convergents(param.value, max_den=args.max_den)
        
        for p, q in convergents:
            # Skip trivially inaccurate or overly simple early convergents 
            # unless the target itself is an integer.
            if q < 3 and len(convergents) > 3:
                continue
                
            approx = p / q
            error_str = param.error_func(approx, param.value)
            
            fraction_str = f"{p}/{q}"
            lines.append(f"{fraction_str:<25} | {approx:<25.12f} | {error_str}")
            
    output_text = "\n".join(lines)
    
    # Print to console
    print(output_text)
    
    # Save to file if requested
    if args.out_txt:
        with open(args.out_txt, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"\nSaved results to {args.out_txt}")

    return 0

if __name__ == "__main__":
    sys.exit(main())