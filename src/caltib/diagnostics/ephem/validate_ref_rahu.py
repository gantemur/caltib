#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
from typing import List, Optional

from caltib.reference import astro_args as aa
from caltib.reference import planets
from caltib.ephemeris.de422 import DE422Elongation

def _need_numpy():
    try:
        import numpy as np
        return np
    except ImportError as e:
        raise RuntimeError('Need numpy. Install: pip install "caltib[diagnostics]"') from e

def _need_matplotlib():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError as e:
        raise RuntimeError('Need matplotlib. Install: pip install "caltib[diagnostics]"') from e

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Validate Analytical Rahu against DE422 Osculating Node.")
    p.add_argument("--year-start", type=int, default=0)
    p.add_argument("--year-end", type=int, default=3000)
    p.add_argument("--step-days", type=int, default=5)
    p.add_argument("--out-png", default="val_rahu.png")
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    print("Loading DE422 Ephemeris...")
    el = DE422Elongation.load()
    eph = el.eph

    # Generate Time Grid
    jd_start = aa.J2000_TT + (args.year_start - 2000) * 365.25
    jd_end = aa.J2000_TT + (args.year_end - 2000) * 365.25
    
    jds = np.arange(jd_start, jd_end, args.step_days)
    years = 2000 + (jds - aa.J2000_TT) / 365.25

    print(f"Validating {len(jds)} points from {years[0]:.0f} to {years[-1]:.0f}...")

    errors_node = []

    for jd in jds:
        T = aa.T_centuries(jd)
        
        # 1. Extract Geocentric Moon Position AND Velocity from DE422
        # jplephem's native method for state vectors is position_and_velocity
        state = eph.position_and_velocity("moon", jd)
        r_geo_eq = state[0].flatten()  # Position vector (x, y, z)
        v_geo_eq = state[1].flatten()  # Velocity vector (dx, dy, dz)

        # 2. Rotate both vectors to the Ecliptic of Date
        rot_matrix = aa.matrix_eq_j2000_to_ecl_date(T)
        r_geo_ecl = aa.apply_matrix(rot_matrix, r_geo_eq)
        v_geo_ecl = aa.apply_matrix(rot_matrix, v_geo_eq)

        # 3. Compute Orbital Angular Momentum Vector (h = r x v)
        # This vector is perfectly perpendicular to the Moon's instantaneous orbital plane
        hx = r_geo_ecl[1] * v_geo_ecl[2] - r_geo_ecl[2] * v_geo_ecl[1]
        hy = r_geo_ecl[2] * v_geo_ecl[0] - r_geo_ecl[0] * v_geo_ecl[2]
        hz = r_geo_ecl[0] * v_geo_ecl[1] - r_geo_ecl[1] * v_geo_ecl[0]

        # 4. Extract Longitude of the Ascending Node (Omega)
        # The ascending node vector n = (0,0,1) x h = (-hy, hx, 0)
        # Omega = atan2(y, x) = atan2(hx, -hy)
        de_node_deg = math.degrees(math.atan2(hx, -hy)) % 360.0

        # 5. Analytical True Node (Rahu) from your library
        rahu = planets.geocentric_position("rahu", jd)

        # 6. Calculate Residuals
        diff_deg = ((rahu.L_true_deg - de_node_deg + 180.0) % 360.0 - 180.0)
        errors_node.append(diff_deg)

    # 7. Plotting
    fig, ax = plt.subplots(1, 1, figsize=(12, 5))
    
    ax.scatter(years, errors_node, s=1, alpha=0.6, color='black')
    ax.set_title("Rahu (True Lunar Node) Error: Analytical vs DE422 Osculating Geometry")
    ax.set_ylabel("Error (degrees)")
    ax.set_xlabel("Year")
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color='red', linewidth=1.0)
    
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=200)
    print(f"Validation complete. Plot saved to {args.out_png}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())