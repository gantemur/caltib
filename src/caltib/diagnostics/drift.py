#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from caltib.api import get_calendar


def _need_numpy():
    try:
        import numpy as np
        return np
    except ImportError as e:
        raise RuntimeError('Need numpy. Install: pip install "caltib[tools]"') from e


def _need_matplotlib():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError as e:
        raise RuntimeError('Need matplotlib. Install: pip install "caltib[tools]"') from e


def find_exact_syzygy(x: int, jd_guess: float, evaluator) -> float:
    """
    Finds the exact JD(TT) where elongation matches the absolute tithi x.
    Uses a highly efficient Secant root-finder seeded by the engine's true_date.
    """
    target_deg = (x % 30) * 12.0
    
    def error(jd: float) -> float:
        e = evaluator(jd)
        d = (e - target_deg) % 360.0
        if d > 180.0: d -= 360.0
        return d
        
    jd0 = jd_guess
    jd1 = jd_guess + 0.1  # Step forward 2.4 hours for the initial secant
    e0 = error(jd0)
    e1 = error(jd1)
    
    for _ in range(15):
        if abs(e1) < 1e-6:  # Converged to ~0.03 arcseconds
            break
        if e1 == e0:
            break
        jd_next = jd1 - e1 * (jd1 - jd0) / (e1 - e0)
        jd0, e0 = jd1, e1
        jd1 = jd_next
        e1 = error(jd1)
        
    return jd1


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Plot raw historical drift vs Truth Ephemeris for multiple engines.")
    p.add_argument("--engines", default="phugpa,tsurphu,mongol,bhutan,karana",
                   help="Comma list of engines (e.g., 'phugpa,mongol,l2,l4').")
    p.add_argument("--ephem", choices=("ref", "de422"), default="ref", help="Reference Ephemeris or DE422")
    p.add_argument("--time", choices=("true", "civil"), default="civil", help="Evaluate continuous true_date or snapped local_civil_date")
    p.add_argument("--year-start", type=int, default=700)
    p.add_argument("--year-end", type=int, default=2000)
    p.add_argument("--out-png", default="drift.png")
    p.add_argument("--filter-hours", type=float, default=50.0)
    p.add_argument("--alpha", type=float, default=0.15)
    p.add_argument("--marker-size", type=float, default=3.0)
    p.add_argument("--plot-subsample", type=int, default=2, help="Plot every k-th point (fit uses all).")
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    y0, y1 = args.year_start, args.year_end
    if y1 < y0:
        raise SystemExit("--year-end must be >= --year-start")

    engines_list = [x.strip() for x in args.engines.split(",") if x.strip()]

    # Load Evaluator
    if args.ephem == "de422":
        try:
            from caltib.ephemeris.de422 import DE422Elongation
            el = DE422Elongation.load()
            def evaluator(jd): return el.elong_deg(jd)
        except ImportError as e:
            raise SystemExit("DE422 ephemeris tools not available. Use --ephem ref") from e
    else:
        from caltib.reference.solar import solar_longitude
        from caltib.reference.lunar import lunar_position
        def evaluator(jd):
            s = solar_longitude(jd)
            m = lunar_position(jd)
            return (m.L_true_deg - s.L_true_deg) % 360.0

    # Calculate approximate JD bounds for the requested years
    # (Using a standard year start offset; exact boundaries are honed continuously)
    jd_start = datetime.date(y0, 1, 1).toordinal() + 1721425.5
    jd_end = datetime.date(y1, 12, 31).toordinal() + 1721425.5

    color_map = {
        "phugpa": "tab:orange", "mongol": "tab:blue", "tsurphu": "tab:purple", 
        "bhutan": "tab:green", "karana": "tab:red", "l0": "tab:brown", 
        "l1": "tab:pink", "l2": "tab:cyan", "l3": "tab:olive", "l4": "gold"
    }

    plt.figure(figsize=(12, 7))
    print(f"Evaluating historical drift ({y0}-{y1}) against {args.ephem.upper()}...")

    for eng_name in engines_list:
        eng = get_calendar(eng_name)
        c = color_map.get(eng_name, "black")
        
        x_start = eng.day.get_x_from_t2000(jd_start - 2451545.0)
        x_end = eng.day.get_x_from_t2000(jd_end - 2451545.0)
        
        years = []
        offsets = []
        
        for x in range(x_start, x_end + 1):
            if x % 30 != 0:  # Only evaluate new moons (end of day 30)
                continue
                
            # Convert continuous tithi to lunation index to find the human year coordinate
            n = (x // 30) - 1
            
            try:
                # O(1) Protocol lookup for civil labels
                Y, M, _ = eng.month.label_from_lunation(n)
            except AttributeError:
                # Fallback to diagnostic dictionary if protocol is not yet mapped
                info = eng.month.get_month_info(n)
                Y, M = info["year"], info["month"]
                
            x_year = Y + (M - 0.5) / 12.0
            
            if args.time == "civil":
                t_engine_tt = float(eng.day.local_civil_date(x)) + 2451545.0
            else:
                t_engine_tt = float(eng.day.true_date(x)) + 2451545.0

            t_truth_tt = find_exact_syzygy(x, t_engine_tt, evaluator)
            dh = 24.0 * (t_engine_tt - t_truth_tt)
            
            years.append(x_year)
            offsets.append(dh)

        if not offsets:
            print(f"  {eng_name}: no samples found.")
            continue

        arr_years = np.array(years, dtype=float)
        arr_off = np.array(offsets, dtype=float)

        # Filter extreme outliers (like missing intercalations causing massive jumps)
        mask = np.abs(arr_off) < float(args.filter_hours)
        years_f = arr_years[mask]
        off_f = arr_off[mask]

        if len(off_f) < 30:
            print(f"  {eng_name}: too few points after filtering ({len(off_f)}); skipping fit")
            continue

        # Quadratic fit to expose implied tidal friction
        c2, c1, c0 = np.polyfit(years_f, off_f, 2)
        implied_tidal = -c2 * 3600.0 * 10000.0

        print(f"\n{eng_name}")
        print(f"  samples: {len(off_f)}")
        print(f"  fit: offset_h = {c2:.6e}*Y^2 + {c1:.6e}*Y + {c0:.3f}")
        print(f"  implied tidal coeff: {implied_tidal:.2f} s/cy^2")

        # Scatter (subsample for aesthetics if plotting centuries of data)
        k = max(1, int(args.plot_subsample))
        plt.scatter(
            years_f[::k], off_f[::k],
            s=float(args.marker_size), alpha=float(args.alpha),
            marker=".", linewidths=0, rasterized=True, color=c
        )

        # Fit line on smooth grid
        grid = np.linspace(float(years_f.min()), float(years_f.max()), 600)
        fit = c2 * grid**2 + c1 * grid + c0
        plt.plot(grid, fit, color=c, linewidth=2.5, label=f"{eng_name} fit")

    plt.title(f"Raw Physical Drift vs {args.ephem.upper()} [{args.time} time] ({y0}-{y1})")
    plt.xlabel("Lunar Year Coordinate: Y + (M-0.5)/12")
    plt.ylabel("Offset hours (Engine - Truth TT)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=200)
    print(f"\nSaved {args.out_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())