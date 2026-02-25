# design/sine_tables.py

from __future__ import annotations

import argparse
import math
import sys
from typing import List, Optional


def generate_sine_table(nodes: int, amplitude: int) -> List[int]:
    """
    Generates an integer table for a quarter-period of the sine function.
    """
    table = []
    for i in range(nodes):
        # Map index i to angle theta in [0, pi/2]
        theta = (i / (nodes - 1)) * (math.pi / 2)
        val = round(amplitude * math.sin(theta))
        table.append(val)
    return table


def evaluate_relative_error(table: List[int], amplitude: int) -> float:
    """
    Evaluates the maximum relative error of the linearly interpolated integer table 
    compared to the exact continuous sine function over the quarter period.
    """
    nodes = len(table)
    max_abs_err = 0.0
    
    # Use a dense grid to find the maximum deviation
    num_samples = 10000
    for k in range(num_samples + 1):
        # theta in [0, pi/2]
        theta = (k / num_samples) * (math.pi / 2)
        exact = amplitude * math.sin(theta)
        
        # Map theta to fractional table index
        frac_idx = (theta / (math.pi / 2)) * (nodes - 1)
        idx_low = math.floor(frac_idx)
        idx_high = math.ceil(frac_idx)
        
        if idx_low == idx_high:
            interp = table[idx_low]
        else:
            weight = frac_idx - idx_low
            interp = table[idx_low] * (1.0 - weight) + table[idx_high] * weight
            
        err = abs(interp - exact)
        if err > max_abs_err:
            max_abs_err = err
            
    # Relative error as a fraction of the amplitude
    return max_abs_err / amplitude


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Generate integer sine tables for calendar engines.")
    p.add_argument("--nodes", type=int, default=8, help="Number of nodes in the quarter period (default: 8).")
    p.add_argument("--amplitude", type=int, default=48, help="Peak amplitude of the sine table (default: 48).")
    p.add_argument("--out-txt", type=str, default="", help="Optional text file to save the output.")
    args = p.parse_args(argv)

    if args.nodes < 2:
        print("Error: Number of nodes must be at least 2.", file=sys.stderr)
        return 1
    if args.amplitude < 1:
        print("Error: Amplitude must be at least 1.", file=sys.stderr)
        return 1

    table = generate_sine_table(args.nodes, args.amplitude)
    rel_error = evaluate_relative_error(table, args.amplitude)

    # Format the output string
    tuple_str = str(tuple(table))
    output_line = f"SINE_TAB_QUARTER = {tuple_str:<40} # length {args.nodes}"
    
    error_pct = rel_error * 100.0
    error_line = f"# Maximum interpolation error: {rel_error:.6f} ({error_pct:.4f}% of amplitude)"

    full_output = f"{output_line}\n{error_line}"

    # Print to console
    print(full_output)

    # Save to file if requested
    if args.out_txt:
        with open(args.out_txt, "w", encoding="utf-8") as f:
            f.write(full_output + "\n")
        print(f"\nSaved results to {args.out_txt}")

    return 0

if __name__ == "__main__":
    sys.exit(main())