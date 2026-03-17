# design/minimax_polys.py

from __future__ import annotations

import argparse
import math
import sys
from typing import Callable, List, Optional, Tuple


def _need_numpy():
    try:
        import numpy as np
        return np
    except ImportError as e:
        raise RuntimeError('Need numpy. Install: pip install "caltib[tools]"') from e


def _need_scipy():
    try:
        import scipy.optimize as opt
        return opt
    except ImportError as e:
        raise RuntimeError('Need scipy. Install: pip install "caltib[tools]"') from e


def optimize_minimax_odd(
    func: Callable, 
    interval: Tuple[float, float], 
    degree: int, 
    num_points: int = 10000
) -> Tuple[List[float], List[int], float]:
    """
    Finds the minimax polynomial approximation using ONLY odd powers.
    Returns (coefficients, powers, max_error).
    """
    np = _need_numpy()
    opt = _need_scipy()

    n_terms = (degree + 1) // 2
    powers = [2 * i + 1 for i in range(n_terms)]

    x = np.linspace(interval[0], interval[1], num_points)
    y = func(x)
    A = np.vstack([x**p for p in powers]).T

    c_init, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

    def cost(c: np.ndarray) -> float:
        return float(np.max(np.abs(y - A @ c)))

    res = opt.minimize(
        cost, 
        c_init, 
        method='Powell', 
        options={'xtol': 1e-12, 'ftol': 1e-12, 'maxiter': 5000}
    )

    return list(res.x), powers, cost(res.x)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Compute minimax odd-polynomial approximations.")
    p.add_argument("--degree", type=int, default=7, help="Maximum polynomial degree (default: 7).")
    p.add_argument("--arctan-max", type=float, default=1.0, 
                   help="Maximum evaluation boundary for arctan (default: 1.0). Use ~0.267949 for aggressive reduction.")
    p.add_argument("--out-txt", type=str, default="", help="Optional text file to save the output.")
    args = p.parse_args(argv)

    np = _need_numpy()

    max_degree = args.degree if args.degree % 2 != 0 else args.degree - 1
    if max_degree < 1:
        print("Error: Degree must be at least 1.", file=sys.stderr)
        return 1

    lines = []
    lines.append(f"Minimax Odd-Polynomial Approximations (Max Degree: {max_degree})")
    lines.append("=" * 95)

    # --- 1. Sine Approximation ---
    sin_func = lambda x: np.sin(2.0 * np.pi * x)
    sin_interval = (0.0, 0.25)
    sin_coeffs, sin_powers, sin_err = optimize_minimax_odd(sin_func, sin_interval, max_degree)

    lines.append("\n--- Function: sin(2*pi*x) on [0, 0.25] (Input: Turns) ---")
    lines.append(f"Maximum Absolute Error: {sin_err:.8e}")
    lines.append("-" * 95)
    lines.append(f"{'Power':<8} | {'Hex-Float (IEEE 754)':<25} | {'Decimal Coefficient'}")
    lines.append("-" * 95)
    for c, p in zip(sin_coeffs, sin_powers):
        lines.append(f"x^{p:<6} | {float(c).hex():<25} | {c:+.18f}")

    # --- 2. Arctan Approximation ---
    arctan_func = lambda x: np.arctan(x) / (2.0 * np.pi)
    arctan_max = args.arctan_max
    arctan_interval = (0.0, arctan_max)
    arctan_coeffs, arctan_powers, arctan_err = optimize_minimax_odd(arctan_func, arctan_interval, max_degree)

    lines.append(f"\n\n--- Function: arctan(x)/(2*pi) on [0, {arctan_max:.6f}] (Output: Turns) ---")
    lines.append(f"Maximum Absolute Error: {arctan_err:.8e}")
    lines.append("-" * 95)
    lines.append(f"{'Power':<8} | {'Hex-Float (IEEE 754)':<25} | {'Decimal Coefficient'}")
    lines.append("-" * 95)
    for c, p in zip(arctan_coeffs, arctan_powers):
        lines.append(f"x^{p:<6} | {float(c).hex():<25} | {c:+.18f}")

    # --- 3. Dynamic Argument Reduction Instructions ---
    turn_4 = 1.0 / 4.0
    
    if args.arctan_max < 1.0:
        sqrt3 = math.sqrt(3.0)
        turn_12 = 1.0 / 12.0
        instructions = f"""
\n--- Arctan Argument Reduction Instructions ---
To use this polynomial to calculate arctan(x) in TURNS for ANY x in (-inf, inf):

1. Handle negative inputs:
   If x < 0:
       sign = -1.0
       x = -x
   Else:
       sign = 1.0

2. Reduce from (1, inf) to [0, 1]:
   If x > 1.0:
       invert = True
       x = 1.0 / x
   Else:
       invert = False

3. Reduce from ({arctan_max:.6f}, 1.0] to [0, {arctan_max:.6f}]:
   If x > {arctan_max:.6f}:
       offset = True
       # Apply identity: arctan(x) = pi/6 + arctan((x*sqrt(3) - 1) / (x + sqrt(3)))
       x = (x * {float(sqrt3).hex()} - 1.0) / (x + {float(sqrt3).hex()})
   Else:
       offset = False

4. Evaluate Polynomial:
   y = P(x)   # Using the coefficients from the table above (outputs turns!)

5. Reconstruct the Angle (in turns):
   If offset == True:
       y = {float(turn_12).hex()} + y   # Add 1/12 turn
   If invert == True:
       y = {float(turn_4).hex()} - y    # Subtract from 1/4 turn

   Return sign * y

--- Required Constants ---
sqrt(3)      = {float(sqrt3).hex():<25} ({sqrt3:.18f})
1/12 turn    = {float(turn_12).hex():<25} ({turn_12:.18f})
1/4 turn     = {float(turn_4).hex():<25} ({turn_4:.18f})
"""
    else:
        instructions = f"""
\n--- Arctan Argument Reduction Instructions ---
To use this polynomial to calculate arctan(x) in TURNS for ANY x in (-inf, inf):

1. Handle negative inputs:
   If x < 0:
       sign = -1.0
       x = -x
   Else:
       sign = 1.0

2. Reduce from (1, inf) to [0, 1]:
   If x > 1.0:
       invert = True
       x = 1.0 / x
   Else:
       invert = False

3. Evaluate Polynomial:
   y = P(x)   # Using the coefficients from the table above (outputs turns!)

4. Reconstruct the Angle (in turns):
   If invert == True:
       y = {float(turn_4).hex()} - y    # Subtract from 1/4 turn

   Return sign * y

--- Required Constants ---
1/4 turn     = {float(turn_4).hex():<25} ({turn_4:.18f})
"""
    
    lines.append(instructions)

    output_text = "\n".join(lines)
    print(output_text)

    if args.out_txt:
        with open(args.out_txt, "w", encoding="utf-8") as f:
            f.write(output_text + "\n")
        print(f"\nSaved results to {args.out_txt}")

    return 0


if __name__ == "__main__":
    sys.exit(main())