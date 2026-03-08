#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import math
from fractions import Fraction
from dataclasses import dataclass
from typing import List, Tuple, Optional

from caltib.api import get_calendar
from caltib.reference.time_scales import jd_utc_to_jd_tt, jd_tt_to_jd_utc
from caltib.reference.deltat import delta_t_seconds


def _need_numpy():
    try:
        import numpy as np
        return np
    except ImportError as e:
        raise RuntimeError('This script needs numpy. Install: pip install "caltib[tools]"') from e


def _need_matplotlib():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError as e:
        raise RuntimeError('This script needs matplotlib. Install: pip install "caltib[tools]"') from e


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
    jd1 = jd_guess + 0.1
    e0 = error(jd0)
    e1 = error(jd1)
    
    for _ in range(15):
        if abs(e1) < 1e-6:
            break
        if e1 == e0:
            break
        jd_next = jd1 - e1 * (jd1 - jd0) / (e1 - e0)
        jd0, e0 = jd1, e1
        jd1 = jd_next
        e1 = error(jd1)
        
    return jd1


def rolling_mean_std(x, y, window_pts: int):
    """
    Rolling mean/std on y, assuming x is sorted, using a fixed window in points.
    Returns (mean, std) arrays with NaN at ends (centered window).
    """
    import numpy as np
    n = len(y)
    if window_pts < 3 or window_pts > n:
        mean = np.full(n, np.nan)
        std = np.full(n, np.nan)
        return mean, std

    w = window_pts
    half = w // 2
    mean = np.full(n, np.nan)
    std = np.full(n, np.nan)
    for i in range(half, n - half):
        seg = y[i - half : i + half + 1]
        mean[i] = float(np.mean(seg))
        std[i] = float(np.std(seg, ddof=0))
    return mean, std


def binned_variance_fit(x, y, bin_years: float, min_count: int = 20):
    """
    Bin data in x (year coordinate) into bins of width bin_years.
    For each bin, compute variance of y. Fit quadratic to variance vs bin-center.
    """
    import numpy as np
    x0, x1 = float(np.min(x)), float(np.max(x))
    nb = int(max(5, (x1 - x0) / bin_years))
    edges = np.linspace(x0, x1, nb + 1)

    centers, variances, counts = [], [], []

    for i in range(nb):
        a, b = edges[i], edges[i + 1]
        m = (x >= a) & (x < b) if i < nb - 1 else (x >= a) & (x <= b)
        yy = y[m]
        if len(yy) < min_count:
            continue
        centers.append(0.5 * (a + b))
        variances.append(float(np.var(yy, ddof=0)))
        counts.append(int(len(yy)))

    if len(centers) < 6:
        raise RuntimeError(f"Too few variance bins for quadratic fit: {len(centers)} (increase range or bin size)")

    centers = np.array(centers, dtype=float)
    variances = np.array(variances, dtype=float)
    counts = np.array(counts, dtype=int)

    a2, a1, a0 = np.polyfit(centers, variances, 2)
    return centers, variances, counts, (a2, a1, a0)


def vertex_of_parabola(c2: float, c1: float, c0: float):
    if abs(c2) < 1e-20:
        return (float("nan"), float("nan"))
    x0 = -c1 / (2.0 * c2)
    y0 = c2 * x0 * x0 + c1 * x0 + c0
    return x0, y0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Single-Engine Deep Dive: Quadratic drift fit + spread band visualization.")
    p.add_argument("--engine", default="phugpa", help="phugpa|tsurphu|mongol|l1|l2|l3|l4")
    p.add_argument("--ephem", choices=("ref", "de422"), default="ref", help="Reference Ephemeris or DE422")
    p.add_argument("--time", choices=("true", "civil"), default="true", help="Evaluate continuous true_date or snapped local_civil_date")
    p.add_argument("--apply-delta-t", action="store_true", help="Apply rigorous ΔT to convert TT->UTC offset drift.")
    p.add_argument("--year-start", type=int, default=400)
    p.add_argument("--year-end", type=int, default=2000)
    p.add_argument("--filter-hours", type=float, default=50.0, help="Drop |offset| >= this many hours")
    p.add_argument("--out-png", default="drift_quad.png")

    # spread controls
    p.add_argument("--window-years", type=float, default=100.0, help="Rolling window in years for mean±σ band")
    p.add_argument("--bin-years", type=float, default=10.0, help="Bin width in years for variance fit")
    p.add_argument("--min-bin-count", type=int, default=40, help="Min samples per variance bin")
    p.add_argument("--show-fit-sigma", action="store_true", help="Overlay sigma band from variance-fit")

    # plotting controls
    p.add_argument("--alpha", type=float, default=0.35, help="Scatter alpha")
    p.add_argument("--marker-size", type=float, default=4.0, help="Scatter marker size")
    p.add_argument("--plot-subsample", type=int, default=1, help="Plot every k-th point (fit uses all).")
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    y0, y1 = args.year_start, args.year_end
    if y1 < y0:
        raise SystemExit("--year-end must be >= --year-start")

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

    # Parse the custom month suffix
    base_engine = args.engine
    use_month = False
    if base_engine.endswith("-m"):
        base_engine = base_engine[:-2]
        use_month = True

    eng = get_calendar(base_engine)
    
    jd_start = datetime.date(y0 if y0 > 0 else 1, 1, 1).toordinal() + 1721425.5
    if y0 <= 0: jd_start += (y0 - 1) * 365.25
    jd_end = datetime.date(y1, 12, 31).toordinal() + 1721425.5

    x_start = eng.day.get_x_from_t2000(jd_start - 2451545.0)
    x_end = eng.day.get_x_from_t2000(jd_end - 2451545.0)

    print(f"Deep dive analyzing {args.engine} [{args.time} time] vs {args.ephem.upper()}...")

    x_year_list, offsets_list = [], []

    for x in range(x_start, x_end + 1):
        if x % 30 != 0:
            continue
            
        n = (x // 30) - 1
        try:
            Y, M, _ = eng.month.label_from_lunation(n)
        except AttributeError:
            info = eng.month.get_month_info(n)
            Y, M = info["year"], info["month"]
            
        x_year = Y + (M - 0.5) / 12.0
        
        # 1. Engine's Physical Estimate
        if use_month:
            if not hasattr(eng, "month") or not hasattr(eng.month, "true_date"):
                raise SystemExit(f"Engine '{base_engine}' does not support month-level evaluation.")
            t_engine_tt = float(eng.month.true_date(Fraction(x, 30))) + 2451545.0
        elif args.time == "civil":
            t_engine_utc = float(eng.day.local_civil_date(x)) + 2451545.0
            t_engine_tt = jd_utc_to_jd_tt(t_engine_utc)
        else:
            try:
                t_engine_tt = float(eng.day.true_date(x)) + 2451545.0
            except AttributeError:
                t_engine_tt = float(eng.day.treu_date(x)) + 2451545.0
                
        # 2. Exact Ephemeris Truth
        t_truth_tt = find_exact_syzygy(x, t_engine_tt, evaluator)
        
        # 3. Delta (Bypass civil offset if using continuous month engine)
        if args.time == "civil" and not use_month:
            t_truth_utc = jd_tt_to_jd_utc(t_truth_tt)
            off_h = 24.0 * (t_engine_utc - t_truth_utc)
        else:
            off_h = 24.0 * (t_engine_tt - t_truth_tt)        
            
        x_year_list.append(x_year)
        offsets_list.append(off_h)

    years = np.array(x_year_list, dtype=float)
    raw_offsets = np.array(offsets_list, dtype=float)

    if args.apply_delta_t:
        dt = np.array([delta_t_seconds(y) / 3600.0 for y in years], dtype=float)
        offsets_h = raw_offsets + dt
    else:
        offsets_h = raw_offsets

    mask = np.abs(offsets_h) < float(args.filter_hours)
    years_f = years[mask]
    off_f = offsets_h[mask]
    
    if len(off_f) < 100:
        raise RuntimeError(f"Too few points after filtering: {len(off_f)}")

    order = np.argsort(years_f)
    years_f = years_f[order]
    off_f = off_f[order]

    # Rolling window logic
    diffs = np.diff(years_f)
    step = float(np.median(diffs[diffs > 0]))
    samples_per_year = max(1.0, 1.0 / step)
    window_pts = int(round(args.window_years * samples_per_year))
    if window_pts % 2 == 0:
        window_pts += 1

    roll_mean, roll_std = rolling_mean_std(years_f, off_f, window_pts=window_pts)

    # Quadratic drift fit
    c2, c1, c0 = np.polyfit(years_f, off_f, 2)
    drift_vertex_x, drift_vertex_y = vertex_of_parabola(c2, c1, c0)

    # Variance quadratic fit (binned)
    centers, var_bins, counts, (v2, v1, v0) = binned_variance_fit(
        years_f, off_f, bin_years=float(args.bin_years), min_count=int(args.min_bin_count)
    )
    var_vertex_x, var_vertex_y = vertex_of_parabola(v2, v1, v0)
    sigma_vertex = math.sqrt(var_vertex_y) if var_vertex_y > 0 else float("nan")

    # Print summary
    implied_tidal_coeff = -c2 * 3600.0 * 10000.0
    linear_drift_h_per_century = c1 * 100.0

    print("\n" + "=" * 75)
    print(f"ENGINE: {args.engine.upper()}")
    print(f"Drift fit: offset_h = {c2:.6e}*Y^2 + {c1:.6e}*Y + {c0:.3f}")
    print(f"  drift vertex: Y* = {drift_vertex_x:.0f}, offset* = {drift_vertex_y:.3f} h")
    print(f"  implied tidal coeff: {implied_tidal_coeff:.2f} s/cy^2")
    if args.apply_delta_t:
        print("  (Rigorous ΔT applied)")

    print(f"\nVariance fit: var = {v2:.6e}*Y^2 + {v1:.6e}*Y + {v0:.6e} (h^2)")
    print(f"  sigma vertex (min): Y* = {var_vertex_x:.0f}, min_sigma = {sigma_vertex:.4f} h")
    print("=" * 75 + "\n")

    # Plot
    plt.figure(figsize=(12, 7))

    color_map = {
        "phugpa": "tab:orange", "mongol": "tab:blue", "tsurphu": "tab:purple", 
        "bhutan": "tab:green", "karana": "tab:red", "l0": "tab:brown", 
        "l1": "tab:pink", "l2": "tab:cyan", "l3": "tab:olive", "l4": "gold"
    }
    c = color_map.get(base_engine, "tab:blue")

    # Raw scatter
    k = max(1, int(args.plot_subsample))
    plt.scatter(
        years_f[::k], off_f[::k],
        s=float(args.marker_size), alpha=float(args.alpha),
        marker=".", linewidths=0, rasterized=True, color=c,
        label="Raw Syzygy Offsets",
    )

    # Quadratic drift curve
    grid = np.linspace(float(years_f.min()), float(years_f.max()), 800)
    drift_fit_grid = c2 * grid**2 + c1 * grid + c0
    plt.plot(grid, drift_fit_grid, linewidth=2.5, color="black", label="Mean Drift Fit")

    # Rolling mean + sigma band
    ok = np.isfinite(roll_mean) & np.isfinite(roll_std)
    if ok.sum() > 10:
        plt.fill_between(
            years_f[ok],
            roll_mean[ok] - roll_std[ok],
            roll_mean[ok] + roll_std[ok],
            color=c, alpha=0.25, linewidth=0,
            label=f"±1σ Spread (rolling {args.window_years:g}y)",
        )

    # Grab the exact boundaries of your plotted data
    min_year = float(years_f.min())
    max_year = float(years_f.max())

    # Mark vertices only if they fall within the plotted range
    if math.isfinite(drift_vertex_x) and min_year <= drift_vertex_x <= max_year:
        plt.axvline(drift_vertex_x, linestyle="--", color="black", linewidth=1.5, alpha=0.7, label=f"Drift Vertex (~{drift_vertex_x:.0f})")
        
    if math.isfinite(var_vertex_x) and min_year <= var_vertex_x <= max_year:
        plt.axvline(var_vertex_x, linestyle=":", color="red", linewidth=2.0, alpha=0.8, label=f"Sigma Minimum (~{var_vertex_x:.0f})")
        
    engine_display = f"{base_engine.upper()} (Month Engine)" if use_month else f"{base_engine.upper()} [{args.time} time]"
    plt.title(f"Quadratic Fit & Variance Spread ({args.year_start}-{args.year_end}) — {engine_display}")
    plt.xlabel("Lunar Year Coordinate: Y + (M-0.5)/12")
    plt.ylabel(f"Offset (hours)")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=200)
    print(f"Saved {args.out_png}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())