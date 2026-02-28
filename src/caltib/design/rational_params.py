#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import sys
from typing import List, Optional, Tuple

from caltib.reference import astro_args as aa


def get_convergents(x: float, max_den: int = 100000) -> List[Tuple[int, int]]:
    """
    Generates the continued fraction convergents (p, q) for a real number x.
    Stops when the denominator exceeds max_den or the remainder is indistinguishable from 0.
    Cleanly handles negative values by running the algorithm on the absolute value.
    """
    sign = -1 if x < 0 else 1
    x_abs = abs(x)
    convergents = []
    a = math.floor(x_abs)
    rem = x_abs - a
    
    h_prev1, k_prev1 = 1, 0
    h, k = a, 1

    while k <= max_den:
        convergents.append((sign * h, k))
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
    def __init__(self, name: str, value: float, unit: str, scale: float = 1.0):
        self.name = name
        self.value = value
        self.unit = unit
        self.scale = scale  # 1.0 for turns, 30.0 for tithis


def build_parameters(k: int) -> Tuple[List[ParameterDefinition], List[ParameterDefinition]]:
    """Evaluates and builds the main and appendix parameters."""
    jd_tt = aa.jde_mean_new_moon(float(k))
    T = aa.T_centuries(jd_tt)
    E = aa.eccentricity_factor(T)
    
    # Elements at Epoch
    sm_epoch = aa.solar_mean_elements(T)
    fa_epoch = aa.fundamental_args(T)
    
    # Elements at J2000.0 (T = 0) for the c0 Appendix
    sm_j2000 = aa.solar_mean_elements(0.0)
    fa_j2000 = aa.fundamental_args(0.0)
    
    main_params = []
    appx_params = []
    
    # ---------------------------------------------------------
    # MAIN 1: Traditional Epoch Constants (Evaluated at m0)
    # ---------------------------------------------------------
    main_params.append(ParameterDefinition("m0 (Epoch Mean New Moon JD_TT)", jd_tt, "days"))
    main_params.append(ParameterDefinition("s0 (Mean Sun L0 at epoch)", sm_epoch.L0_turn % 1.0, "turns"))
    main_params.append(ParameterDefinition("a0 (Lunar Anomaly at epoch)", fa_epoch.Mp_turn % 1.0, "turns"))
    main_params.append(ParameterDefinition("r0 (Solar Anomaly at epoch)", sm_epoch.M_turn % 1.0, "turns"))
    main_params.append(ParameterDefinition("f0 (Arg of Latitude at epoch)", fa_epoch.F_turn % 1.0, "turns"))
    
    # ---------------------------------------------------------
    # MAIN 2: Solar & Lunar Amplitudes
    # ---------------------------------------------------------
    amp_solar_eq = (1.914602 - 0.004817 * T - 0.000014 * (T**2)) / 360.0
    main_params.append(ParameterDefinition("Solar Eq of Center", amp_solar_eq, "turns"))
    
    amp_moon_1 = (6.288774 / 360.0) * 30.0
    main_params.append(ParameterDefinition("Lunar 1: Major Ineq (Mp)", amp_moon_1, "tithis", scale=30.0))
    
    amp_moon_2 = (1.274027 / 360.0) * 30.0
    main_params.append(ParameterDefinition("Lunar 2: Evection (2D - Mp)", amp_moon_2, "tithis", scale=30.0))
    
    amp_moon_3 = (0.658314 / 360.0) * 30.0
    main_params.append(ParameterDefinition("Lunar 3: Variation (2D)", amp_moon_3, "tithis", scale=30.0))
    
    amp_moon_4 = (-0.185116 * E / 360.0) * 30.0
    main_params.append(ParameterDefinition("Lunar 4: Annual Eq (M)", amp_moon_4, "tithis", scale=30.0))
    
    amp_moon_5 = (0.213618 / 360.0) * 30.0
    main_params.append(ParameterDefinition("Lunar 5: 2nd Elliptic (2Mp)", amp_moon_5, "tithis", scale=30.0))
    
    amp_moon_6 = (-0.114332 / 360.0) * 30.0
    main_params.append(ParameterDefinition("Lunar 6: Reduction (2F)", amp_moon_6, "tithis", scale=30.0))

    # ---------------------------------------------------------
    # APPENDIX: J2000.0 Reference Constants (Evaluated at T=0)
    # ---------------------------------------------------------
    appx_params.append(ParameterDefinition("c0_S (Mean Sun L0 at J2000.0)", sm_j2000.L0_turn % 1.0, "turns"))
    appx_params.append(ParameterDefinition("c0_Mp (Lunar Anomaly at J2000.0)", fa_j2000.Mp_turn % 1.0, "turns"))
    appx_params.append(ParameterDefinition("c0_M (Solar Anomaly at J2000.0)", sm_j2000.M_turn % 1.0, "turns"))
    appx_params.append(ParameterDefinition("c0_F (Arg of Latitude at J2000.0)", fa_j2000.F_turn % 1.0, "turns"))
    
    return main_params, appx_params


def print_param_list(params: List[ParameterDefinition], max_den: int):
    """Helper to cleanly format and print a block of parameters."""
    for param in params:
        print(f"\n--- {param.name} ---")
        print(f"Target Value: {param.value:.12f} {param.unit}")
        print(f"{'Fraction (p/q)':<20} | {'Decimal Approx':<15} | {'Error (arcsec)'}")
        print("-" * 65)
        
        convergents = get_convergents(param.value, max_den=max_den)
        
        display_convs = []
        thresholds = [20, 200, 2000, 20000, max_den]
        t_idx = 0
        for num, den in convergents:
            if den >= thresholds[t_idx]:
                display_convs.append((num, den))
                while t_idx < len(thresholds) and den >= thresholds[t_idx]:
                    t_idx += 1
        
        if convergents and convergents[-1] not in display_convs:
            display_convs.append(convergents[-1])
            
        if len(convergents) <= 3:
            display_convs = convergents
            
        for num, den in display_convs:
            approx = num / den
            err_turns = (approx - param.value) / param.scale
            err_arcsec = err_turns * 360.0 * 3600.0
            
            fraction_str = f"{num}/{den}"
            print(f"{fraction_str:<20} | {approx:<15.8f} | {err_arcsec:+.8f}\"")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Generate epoch constants and amplitudes for L1-L3 engines.")
    p.add_argument("--k", type=int, default=-157, help="Absolute lunation index (Default: -157 for April 1987).")
    p.add_argument("--max-den", type=int, default=100000, help="Maximum denominator for convergents.")
    args = p.parse_args(argv)

    jd_tt = aa.jde_mean_new_moon(float(args.k))
    main_params, appx_params = build_parameters(args.k)
    
    print("==========================================================================================")
    print(f" EPOCH PARAMETER GENERATOR | Epoch Lunation k = {args.k} (JD_TT = {jd_tt:.5f})")
    print("==========================================================================================")
    
    print_param_list(main_params, args.max_den)
            
    print("\n==========================================================================================")
    print(" NOTE: Mean Elongation Phase (D) is strictly 0.0 by definition, since")
    print(" every epoch is anchored precisely to a mean new moon.")
    print("==========================================================================================")
    
    print("\n==========================================================================================")
    print(" APPENDIX: J2000.0 Reference Constants (c0)")
    print("==========================================================================================")
    print(" These represent the absolute phases at T=0 (J2000.0). When using make_funds() ")
    print(" with a traditional m0, the engine linearly back-projects phases. These values ")
    print(" provide the exact polynomial reference at J2000.0 for deep validation.")
    
    print_param_list(appx_params, args.max_den)
    
    print("\n==========================================================================================\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())