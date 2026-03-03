#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
import datetime
from dataclasses import dataclass
from typing import List, Optional

from caltib.api import get_calendar


def need_numpy():
    try:
        import numpy as np
        return np
    except ImportError as e:
        raise RuntimeError('Need numpy. Install: pip install "caltib[tools]"') from e


def need_matplotlib():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError as e:
        raise RuntimeError('Need matplotlib. Install: pip install "caltib[tools]"') from e


def circular_mean_mod24(hours_mod24: List[float]) -> float:
    if not hours_mod24:
        return 0.0
    theta = [2.0 * math.pi * (x / 24.0) for x in hours_mod24]
    c = sum(math.cos(t) for t in theta) / len(theta)
    s = sum(math.sin(t) for t in theta) / len(theta)
    ang = math.atan2(s, c) % (2.0 * math.pi)
    return 24.0 * ang / (2.0 * math.pi)


def find_exact_syzygy(x: int, jd_guess: float, evaluator) -> float:
    """
    Finds the exact JD(TT) where elongation matches the absolute tithi x.
    Uses a highly efficient Secant root-finder seeded by the engine's time.
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
        # Secant step
        jd_next = jd1 - e1 * (jd1 - jd0) / (e1 - e0)
        jd0, e0 = jd1, e1
        jd1 = jd_next
        e1 = error(jd1)
        
    return jd1


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Histogram physical offsets: caltib Engine vs Truth Ephemeris.")
    p.add_argument("--engine", default="phugpa", help="phugpa|tsurphu|mongol|l0|l1|l2|l3|l4")
    p.add_argument("--ephem", choices=("ref", "de422"), default="ref", help="Reference Ephemeris or DE422")
    p.add_argument("--time", choices=("true", "civil"), default="civil", help="Evaluate continuous true_date or snapped local_civil_date")
    p.add_argument("--year-start", type=int, default=1900)
    p.add_argument("--year-end", type=int, default=2100)
    p.add_argument("--mode", choices=("newmoon", "tithi"), default="newmoon")
    p.add_argument("--days", default="1-30", help='For tithi mode: "1-30" or "1,2,15,30"')
    p.add_argument("--bins", type=int, default=100)
    p.add_argument("--out-csv", default="offsets.csv")
    p.add_argument("--out-png", default="offsets_hist.png")
    args = p.parse_args(argv)

    # Parse days
    day_list: List[int] = []
    if args.mode == "tithi":
        s = args.days.strip()
        if "-" in s:
            a, b = s.split("-", 1)
            day_list = list(range(int(a), int(b) + 1))
        else:
            day_list = [int(x) for x in s.split(",") if x.strip()]
        if not day_list:
            raise SystemExit("No days parsed")

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

    eng = get_calendar(args.engine)

    # Calculate approximate JD bounds for the requested years
    jd_start = datetime.date(args.year_start, 1, 1).toordinal() + 1721425.5
    jd_end = datetime.date(args.year_end, 12, 31).toordinal() + 1721425.5
    
    # Map JD bounds to Absolute Tithi indices (O(1) continuous resolution)
    x_start = eng.day.get_x_from_t2000(jd_start - 2451545.0)
    x_end = eng.day.get_x_from_t2000(jd_end - 2451545.0)

    print(f"Evaluating {args.engine} [{args.time} time] vs {args.ephem.upper()} from {args.year_start} to {args.year_end}...")
    
    x_vals, d_vals, t_engine_vals, t_truth_vals, diffs_raw = [], [], [], [], []

    for x in range(x_start, x_end + 1):
        d = x % 30
        if d == 0: 
            d = 30
            
        # Filter based on mode
        if args.mode == "newmoon" and d != 30:
            continue
        elif args.mode == "tithi" and d not in day_list:
            continue

        # 1. Engine's Physical Estimate
        if args.time == "civil":
            t_engine_tt = float(eng.day.local_civil_date(x)) + 2451545.0
        else:
            try:
                t_engine_tt = float(eng.day.true_date(x)) + 2451545.0
            except AttributeError:
                t_engine_tt = float(eng.day.treu_date(x)) + 2451545.0
            
        # 2. Exact Ephemeris Truth
        t_truth_tt = find_exact_syzygy(x, t_engine_tt, evaluator)
        
        # 3. Delta
        dh = 24.0 * (t_engine_tt - t_truth_tt)
        
        x_vals.append(x)
        d_vals.append(d)
        t_engine_vals.append(t_engine_tt)
        t_truth_vals.append(t_truth_tt)
        diffs_raw.append(dh)

    if not diffs_raw:
        raise SystemExit("No syzygies found in range.")

    np = need_numpy()
    arr_raw = np.array(diffs_raw, dtype=float)
    
    # Always calculate the circular mean so it can be printed
    mean_mod24 = float(circular_mean_mod24(list(arr_raw % 24.0)))
    
    # Only fold if it's a tight distribution suffering from a 24h dawn-snap
    if np.std(arr_raw) > 6.0 and np.std(arr_raw % 24.0) < 6.0:
        arr_final = mean_mod24 + ((arr_raw - mean_mod24 + 12.0) % 24.0) - 12.0
        fold_status = "(Folded)"
    else:
        arr_final = arr_raw
        fold_status = "(Raw)"

    mean_h = float(arr_final.mean())
    med_h = float(np.median(arr_final))
    std_h = float(np.std(arr_final))
    
    print(f"N={len(arr_final)} {fold_status} mean={mean_h:.4f}h  median={med_h:.4f}h  std={std_h:.4f}h  circmean_mod24={mean_mod24:.4f}h")

    # write CSV
    rows = zip(x_vals, d_vals, t_engine_vals, t_truth_vals, diffs_raw, arr_final)
    with open(args.out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["x_absolute", "tithi_d", f"t_engine_{args.time}", f"t_{args.ephem}_tt", "diff_raw_h", "diff_final_h"])
        w.writerows(rows)
    print(f"Wrote {args.out_csv}")

    # histogram
    plt = need_matplotlib()
    plt.figure(figsize=(10, 6))
    
    # Assign specific colors if testing reform engines, else default
    color_map = {"l4": "gold", "l3": "tab:olive", "l2": "tab:cyan", "l1": "tab:pink", "l0": "tab:brown", "phugpa": "tab:blue"}
    c = color_map.get(args.engine, "tab:blue")

    plt.hist(arr_final, bins=args.bins, alpha=0.75, color=c, edgecolor="black")
    plt.axvline(mean_h, linestyle="--", color="red", label=f"Mean: {mean_h:.2f}h")
    
    plt.xlabel(f"Folded Difference ({args.engine} Engine [{args.time}] - {args.ephem.upper()} Truth) [hours]")
    plt.ylabel("Count")
    plt.title(f"Physical Offset Distribution: {args.engine} vs {args.ephem.upper()} ({args.mode})")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=180)
    print(f"Wrote {args.out_png}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())