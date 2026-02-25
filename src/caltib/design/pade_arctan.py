# design/pade_arctan.py

from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Tuple


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


def optimize_minimax_pade_arctan(
    interval: Tuple[float, float], 
    deg_num: int, 
    deg_den: int, 
    num_points: int = 5000
) -> Tuple[List[float], List[int], List[float], List[int], float]:
    """
    Finds the minimax rational approximation P(x)/Q(x) for arctan(x).
    P(x) has odd powers (x, x^3...).
    Q(x) has even powers (1, x^2...) with Q_0 = 1.0.
    """
    np = _need_numpy()
    opt = _need_scipy()

    # Determine powers
    num_powers = [2 * i + 1 for i in range((deg_num + 1) // 2)]
    den_powers = [2 * i for i in range(1, (deg_den // 2) + 1)]  # starts at x^2

    x = np.linspace(interval[0], interval[1], num_points)
    y = np.arctan(x)

    # 1. Initial Guess via Linear Least Squares
    # We want P(x)/Q(x) ≈ y => P(x) - y*Q_residual(x) ≈ y
    # Variables are [c1, c3, c5...] and [d2, d4...]
    A_num = np.vstack([x**p for p in num_powers]).T
    A_den = np.vstack([-y * (x**p) for p in den_powers]).T
    A = np.hstack([A_num, A_den])
    
    init_guess, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
    
    # 2. Minimax Objective Function (Maximum Absolute Error)
    def cost(params: np.ndarray) -> float:
        c = params[:len(num_powers)]
        d = params[len(num_powers):]
        
        P = sum(c[i] * (x**num_powers[i]) for i in range(len(c)))
        Q = 1.0 + sum(d[i] * (x**den_powers[i]) for i in range(len(d)))
        
        # Penalize if denominator crosses zero (pole in interval)
        if np.any(Q <= 0.05):
            return 1e6
            
        return float(np.max(np.abs(y - (P / Q))))

    # 3. Optimize with Powell
    res = opt.minimize(
        cost, 
        init_guess, 
        method='Powell', 
        options={'xtol': 1e-12, 'ftol': 1e-12, 'maxiter': 5000}
    )

    max_err = cost(res.x)
    c_final = list(res.x[:len(num_powers)])
    d_final = list(res.x[len(num_powers):])
    
    return c_final, num_powers, d_final, den_powers, max_err


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Compute minimax Padé (rational) approx for arctan.")
    p.add_argument("--deg-num", type=int, default=5, help="Max degree of numerator (odd, default: 5).")
    p.add_argument("--deg-den", type=int, default=4, help="Max degree of denominator (even, default: 4).")
    p.add_argument("--out-txt", type=str, default="", help="Optional text file to save the output.")
    args = p.parse_args(argv)

    # Force degrees to odd/even boundaries
    deg_num = args.deg_num if args.deg_num % 2 != 0 else args.deg_num - 1
    deg_den = args.deg_den if args.deg_den % 2 == 0 else args.deg_den - 1

    if deg_num < 1 or deg_den < 2:
        print("Error: Numerator must be >= 1, Denominator must be >= 2.", file=sys.stderr)
        return 1

    c_coeffs, c_powers, d_coeffs, d_powers, max_err = optimize_minimax_pade_arctan(
        (0.0, 1.0), deg_num, deg_den
    )

    lines = []
    lines.append(f"Minimax Padé Approximant for arctan(x) on [0, 1]")
    lines.append(f"P(x) degree {deg_num} (odd) / Q(x) degree {deg_den} (even)")
    lines.append("=" * 95)
    lines.append(f"Maximum Absolute Error: {max_err:.8e}")
    
    lines.append("\n--- Numerator P(x) ---")
    lines.append(f"{'Power':<8} | {'Hex-Float (IEEE 754)':<25} | {'Decimal Coefficient'}")
    lines.append("-" * 95)
    for c, p in zip(c_coeffs, c_powers):
        lines.append(f"x^{p:<6} | {float(c).hex():<25} | {c:+.18f}")

    lines.append("\n--- Denominator Q(x) ---")
    lines.append(f"{'Power':<8} | {'Hex-Float (IEEE 754)':<25} | {'Decimal Coefficient'}")
    lines.append("-" * 95)
    lines.append(f"x^0      | {float(1.0).hex():<25} | +1.000000000000000000")
    for d, p in zip(d_coeffs, d_powers):
        lines.append(f"x^{p:<6} | {float(d).hex():<25} | {d:+.18f}")

    output_text = "\n".join(lines)
    print(output_text)

    if args.out_txt:
        with open(args.out_txt, "w", encoding="utf-8") as f:
            f.write(output_text + "\n")
        print(f"\nSaved results to {args.out_txt}")

    return 0

if __name__ == "__main__":
    sys.exit(main())