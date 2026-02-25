# design/float_params.py

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from caltib.reference import astro_args as aa
from caltib.reference import lunar


class FloatParam:
    def __init__(self, category: str, name: str, value: float, unit: str):
        self.category = category
        self.name = name
        self.value = value
        self.unit = unit
        self.hex_str = float(value).hex()


def build_float_parameters(jd_tt: float) -> List[FloatParam]:
    """Evaluates and builds the list of floating-point parameters for the given epoch."""
    T = aa.T_centuries(jd_tt)
    E = aa.eccentricity_factor(T)
    params = []

    # ---------------------------------------------------------
    # 1. Fundamental Arguments: Values and Rates
    # ---------------------------------------------------------
    fa = aa.fundamental_args(T)
    sm = aa.solar_mean_elements(T)
    
    # Calculate exact instantaneous daily rates using a highly accurate 
    # central difference (since polynomials only go up to T^3 or T^4)
    dt_days = 1.0
    dT = dt_days / 36525.0
    fa_plus = aa.fundamental_args(T + dT)
    fa_minus = aa.fundamental_args(T - dT)
    sm_plus = aa.solar_mean_elements(T + dT)
    sm_minus = aa.solar_mean_elements(T - dT)
    
    def calc_rate(plus: float, minus: float) -> float:
        return aa.wrap180(plus - minus) / (2.0 * dt_days)

    rates = {
        "L0 (Solar Mean Lon)": calc_rate(sm_plus.L0_deg, sm_minus.L0_deg),
        "M (Solar Mean Anom)": calc_rate(sm_plus.M_deg, sm_minus.M_deg),
        "L' (Lunar Mean Lon)": calc_rate(fa_plus.Lp_deg, fa_minus.Lp_deg),
        "D (Mean Elongation)": calc_rate(fa_plus.D_deg, fa_minus.D_deg),
        "M' (Lunar Mean Anom)": calc_rate(fa_plus.Mp_deg, fa_minus.Mp_deg),
        "F (Arg of Latitude)": calc_rate(fa_plus.F_deg, fa_minus.F_deg),
        "Omega (Mean Node)": calc_rate(fa_plus.Omega_deg, fa_minus.Omega_deg),
    }
    
    values = {
        "L0 (Solar Mean Lon)": sm.L0_deg,
        "M (Solar Mean Anom)": sm.M_deg,
        "L' (Lunar Mean Lon)": fa.Lp_deg,
        "D (Mean Elongation)": fa.D_deg,
        "M' (Lunar Mean Anom)": fa.Mp_deg,
        "F (Arg of Latitude)": fa.F_deg,
        "Omega (Mean Node)": fa.Omega_deg,
    }

    for key in values:
        params.append(FloatParam("Fundamental Arguments", f"{key} [Value]", values[key], "deg"))
        params.append(FloatParam("Fundamental Arguments", f"{key} [Rate]", rates[key], "deg/day"))


    # ---------------------------------------------------------
    # 2. Solar Term Amplitudes
    # ---------------------------------------------------------
    sol_amp_1 = 1.914602 - 0.004817 * T - 0.000014 * (T * T)
    sol_amp_2 = 0.019993 - 0.000101 * T
    sol_amp_3 = 0.000289
    
    params.append(FloatParam("Solar Amplitudes", "Term 1 (sin M)", sol_amp_1, "deg"))
    params.append(FloatParam("Solar Amplitudes", "Term 2 (sin 2M)", sol_amp_2, "deg"))
    params.append(FloatParam("Solar Amplitudes", "Term 3 (sin 3M)", sol_amp_3, "deg"))


    # ---------------------------------------------------------
    # 3. Lunar Term Amplitudes (Primary and Supplemental)
    # ---------------------------------------------------------
    try:
        # Dynamically load the terms if they exist in the module
        lunar_terms = lunar.LUNAR_LON_TERMS
    except AttributeError:
        lunar_terms = []

    for idx, (d, m, mp, f, coef_microdeg) in enumerate(lunar_terms):
        # Scale coefficient by the Earth's eccentricity factor E based on M's multiplier
        term_coef = float(coef_microdeg)
        if abs(m) == 1:
            term_coef *= E
        elif abs(m) == 2:
            term_coef *= (E * E)
            
        amp_deg = term_coef * 1e-6
        name = f"Term {idx+1:02d} [D:{d:2d}, M:{m:2d}, M':{mp:2d}, F:{f:2d}]"
        
        category = "Lunar Amplitudes (Primary)" if idx < 24 else "Lunar Amplitudes (Supplemental)"
        params.append(FloatParam(category, name, amp_deg, "deg"))

    return params


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Generate full-precision hex-float astronomical parameters.")
    p.add_argument("--jd-tt", type=float, default=2451545.0, help="Epoch in JD(TT). Default is J2000.0.")
    p.add_argument("--out-txt", type=str, default="", help="Optional file to save the output table.")
    args = p.parse_args(argv)

    params = build_float_parameters(args.jd_tt)
    
    lines = []
    lines.append(f"High-Precision Floating-Point Parameters for Epoch JD(TT) = {args.jd_tt}")
    lines.append("=" * 110)
    
    current_category = ""
    for p_obj in params:
        if p_obj.category != current_category:
            lines.append(f"\n--- {p_obj.category} ---")
            lines.append(f"{'Parameter Name':<35} | {'Hex-Float (IEEE 754)':<25} | {'Decimal Value'}")
            lines.append("-" * 110)
            current_category = p_obj.category
            
        # Format the decimal to 15 digits to show nearly all available float64 precision
        lines.append(f"{p_obj.name:<35} | {p_obj.hex_str:<25} | {p_obj.value:<25.15f} {p_obj.unit}")
            
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