#!/usr/bin/env python3
"""
int_tables.py
-------------
Generates integer lookup tables for pure rational calendar engines.
Produces Quarter-Wave (Sine), Arctangent, and Half-Wave (Conjunction) tables.
"""

from __future__ import annotations

import argparse
import math
import sys
from typing import List, Optional, Callable


def generate_sine_table(nodes: int, amplitude: int) -> List[int]:
    """Quarter-period sine table for x in [0, pi/2]."""
    return [
        round(amplitude * math.sin((i / (nodes - 1)) * (math.pi / 2)))
        for i in range(nodes)
    ]


def generate_arctan_table(nodes: int, amplitude: int) -> List[int]:
    """
    Arctan table for inputs x in [0, 1].
    Amplitude represents exactly pi/4 (45 degrees).
    """
    return [
        round(amplitude * math.atan(i / (nodes - 1)) / (math.pi / 4))
        for i in range(nodes)
    ]


def generate_conjunction_table(nodes: int, amplitude: int, r: float) -> List[int]:
    """
    Half-wave table for the planetary anomaly: atan2(sin(x), r - cos(x)).
    Evaluated for x in [0, pi].
    Normalized so the mathematical peak (arcsin(1/r)) equals the integer amplitude.
    """
    r_eff = r if r > 1.0 else 1.0 / r
    max_angle = math.asin(1.0 / r_eff)
    
    table = []
    for i in range(nodes):
        x = (i / (nodes - 1)) * math.pi
        exact_angle = math.atan2(math.sin(x), r_eff - math.cos(x))
        table.append(round(amplitude * (exact_angle / max_angle)))
        
    return table


def eval_interp_error(table: List[int], exact_func: Callable[[float], float], 
                      domain_min: float, domain_max: float, norm_factor: float) -> float:
    """
    Evaluates the maximum relative error of the linearly interpolated integer table 
    compared to the exact continuous function over its defined domain.
    """
    nodes = len(table)
    max_abs_err = 0.0
    num_samples = 10000
    
    for k in range(num_samples + 1):
        t = k / float(num_samples)
        x = domain_min + t * (domain_max - domain_min)
        exact = exact_func(x)
        
        frac_idx = t * (nodes - 1)
        idx_low = math.floor(frac_idx)
        idx_high = math.ceil(frac_idx)
        
        if idx_low == idx_high:
            interp = table[idx_low]
        else:
            weight = frac_idx - idx_low
            interp = table[idx_low] * (1.0 - weight) + table[idx_high] * weight
            
        max_abs_err = max(max_abs_err, abs(interp - exact))
            
    return max_abs_err / norm_factor


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Generate integer tables for caltib.")
    p.add_argument("--nodes", type=int, default=8, help="Nodes per table (default: 8).")
    p.add_argument("--amp", type=int, default=1024, help="Peak amplitude (default: 1024).")
    p.add_argument("--r-conj", type=float, default=1.52368, help="Radius ratio for conjunction (default: Mars 1.52368).")
    p.add_argument("--out-txt", type=str, default="", help="Optional text file to save the output.")
    args = p.parse_args(argv)

    if args.nodes < 2 or args.amp < 1:
        print("Error: Nodes must be >= 2 and amplitude >= 1.", file=sys.stderr)
        return 1

    # 1. Sine Table
    sin_tab = generate_sine_table(args.nodes, args.amp)
    sin_err = eval_interp_error(
        sin_tab, 
        lambda x: args.amp * math.sin(x), 
        0.0, math.pi / 2, args.amp
    )

    # 2. Arctan Table
    atan_tab = generate_arctan_table(args.nodes, args.amp)
    atan_err = eval_interp_error(
        atan_tab, 
        lambda x: args.amp * math.atan(x) / (math.pi / 4), 
        0.0, 1.0, args.amp
    )

    # 3. Conjunction Table
    conj_tab = generate_conjunction_table(args.nodes, args.amp, args.r_conj)
    r_eff = args.r_conj if args.r_conj > 1.0 else 1.0 / args.r_conj
    max_angle = math.asin(1.0 / r_eff)
    conj_err = eval_interp_error(
        conj_tab, 
        lambda x: args.amp * (math.atan2(math.sin(x), r_eff - math.cos(x)) / max_angle), 
        0.0, math.pi, args.amp
    )

    # Output Formatting
    blocks = [
        f"SINE_TAB_QUARTER = {tuple(sin_tab)}\n# Max interpolation error: {sin_err:.6f} ({sin_err*100:.4f}% of amplitude)",
        f"ATAN_TAB_VALUES  = {tuple(atan_tab)}\n# Max interpolation error: {atan_err:.6f} ({atan_err*100:.4f}% of amplitude)",
        f"CONJ_TAB_HALF    = {tuple(conj_tab)}\n# Max interpolation error: {conj_err:.6f} ({conj_err*100:.4f}% of amplitude) | r = {args.r_conj}"
    ]

    full_output = "\n\n".join(blocks)
    print(full_output)

    if args.out_txt:
        with open(args.out_txt, "w", encoding="utf-8") as f:
            f.write(full_output + "\n")
        print(f"\nSaved results to {args.out_txt}")

    return 0

if __name__ == "__main__":
    sys.exit(main())