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
        raise RuntimeError('Need numpy. Install: pip install numpy') from e


def _need_scipy():
    try:
        import scipy.optimize as opt
        return opt
    except ImportError as e:
        raise RuntimeError('Need scipy. Install: pip install scipy') from e


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

    # Determine the odd powers to use
    n_terms = (degree + 1) // 2
    powers = [2 * i + 1 for i in range(n_terms)]

    # Create a dense grid over the interval
    x = np.linspace(interval[0], interval[1], num_points)
    y = func(x)

    # Build the Vandermonde-like matrix for the odd powers
    A = np.vstack([x**p for p in powers]).T

    # 1. Initial Guess: Least Squares Fit
    c_init, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

    # 2. Objective Function: Maximum Absolute Error (L-infinity norm)
    def cost(c: np.ndarray) -> float:
        return float(np.max(np.abs(y - A @ c)))

    # 3. Optimize to find the Minimax coefficients
    res = opt.minimize(
        cost, 
        c_init, 
        method='Powell', 
        options={'xtol': 1e-12, 'ftol': 1e-12, 'maxiter': 5000}
    )

    max_err = cost(res.x)
    return list(res.x), powers, max_err


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Compute minimax odd-polynomial approximations.")
    p.add_argument("--degree", type=int, default=5, help="Maximum polynomial degree (default: 5).")
    p.add_argument("--arctan-max", type=float, default=2.0 - math.sqrt(3.0), 
                   help="Maximum evaluation boundary for arctan (default: 2 - sqrt(3) ~ 0.2679).")
    p.add_argument("--out-txt", type=str, default="", help="Optional text file to save the output.")
    args = p.parse_args(argv)

    np = _need_numpy()

    # Ensure degree is odd for labeling
    max_degree = args.degree if args.degree % 2 != 0 else args.degree - 1
    if max_degree < 1:
        print("Error: Degree must be at least 1.", file=sys.stderr)
        return 1

    lines = []
    lines.append(f"Minimax Odd-Polynomial Approximations (Max Degree: {max_degree})")
    lines.append("=" * 95)

    # --- 1. Sine Approximation ---
    sin_func = np.sin
    sin_interval = (0.0, math.pi / 2.0)
    sin_coeffs, sin_powers, sin_err = optimize_minimax_odd(sin_func, sin_interval, max_degree)

    lines.append("\n--- Function: sin(x) on [0, pi/2] ---")
    lines.append(f"Maximum Absolute Error: {sin_err:.8e}")
    lines.append("-" * 95)
    lines.append(f"{'Power':<8} | {'Hex-Float (IEEE 754)':<25} | {'Decimal Coefficient'}")
    lines.append("-" * 95)
    for c, p in zip(sin_coeffs, sin_powers):
        lines.append(f"x^{p:<6} | {float(c).hex():<25} | {c:+.18f}")

    # --- 2. Arctan Approximation ---
    arctan_func = np.arctan
    arctan_max = args.arctan_max
    arctan_interval = (0.0, arctan_max)
    arctan_coeffs, arctan_powers, arctan_err = optimize_minimax_odd(arctan_func, arctan_interval, max_degree)

    lines.append(f"\n\n--- Function: arctan(x) on [0, {arctan_max:.6f}] ---")
    lines.append(f"Maximum Absolute Error: {arctan_err:.8e}")
    lines.append("-" * 95)
    lines.append(f"{'Power':<8} | {'Hex-Float (IEEE 754)':<25} | {'Decimal Coefficient'}")
    lines.append("-" * 95)
    for c, p in zip(arctan_coeffs, arctan_powers):
        lines.append(f"x^{p:<6} | {float(c).hex():<25} | {c:+.18f}")

    # --- 3. Argument Reduction Instructions ---
    sqrt3 = math.sqrt(3.0)
    pi_6 = math.pi / 6.0
    pi_2 = math.pi / 2.0
    
    instructions = f"""
\n--- Arctan Argument Reduction Instructions ---
To use this polynomial to calculate arctan(x) for ANY x in (-inf, inf):

1. Handle negative inputs:
   If x < 0:
       sign = -1
       x = -x
   Else:
       sign = 1

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
   y = P(x)   # Using the coefficients from the table above

5. Reconstruct the Angle:
   If offset == True:
       y = {float(pi_6).hex()} + y
   If invert == True:
       y = {float(pi_2).hex()} - y

   Return sign * y

--- Required Constants ---
sqrt(3)      = {float(sqrt3).hex():<25} ({sqrt3:.18f})
pi / 6       = {float(pi_6).hex():<25} ({pi_6:.18f})
pi / 2       = {float(pi_2).hex():<25} ({pi_2:.18f})
"""
    lines.append(instructions)

    output_text = "\n".join(lines)

    # Print to console
    print(output_text)

    # Save to file if requested
    if args.out_txt:
        with open(args.out_txt, "w", encoding="utf-8") as f:
            f.write(output_text + "\n")
        print(f"\nSaved results to {args.out_txt}")

    return 0


if __name__ == "__main__":
    sys.exit(main())