#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional

import caltib
from caltib.ephemeris.de422 import DE422Elongation, build_new_moons


def _need_numpy():
    try:
        import numpy as np  # noqa: F401
        return np
    except ImportError as e:
        raise RuntimeError('This script needs numpy. Install: pip install "caltib[diagnostics]"') from e


def _need_matplotlib():
    try:
        import matplotlib.pyplot as plt  # noqa: F401
        return plt
    except ImportError as e:
        raise RuntimeError('This script needs matplotlib. Install: pip install "caltib[diagnostics]"') from e


def match_monotone(t_tib: List[float], moons: List[float]) -> List[int]:
    """Nearest-match with monotone moon index."""
    if not t_tib:
        return []
    k_prev = min(range(len(moons)), key=lambda j: abs(t_tib[0] - moons[j]))
    out = [k_prev]
    for t in t_tib[1:]:
        lo = max(0, k_prev - 1)
        hi = min(len(moons), k_prev + 6)
        k = min(range(lo, hi), key=lambda j: abs(t - moons[j]))
        if k < k_prev:
            k = k_prev
        out.append(k)
        k_prev = k
    return out


def iter_lunations_for_year(engine: str, Y: int) -> Tuple[int, int]:
    n_start = caltib.month_bounds(Y, 1, is_leap_month=False, engine=engine)["n"]
    n_last = caltib.new_year_day(Y + 1, engine=engine)["n_last"]
    return int(n_start), int(n_last)


def lunar_year_coordinate(engine: str, n: int) -> float:
    info = caltib.month_from_n(n, engine=engine, debug=False)
    lab = info["label_from_true_month"]
    Y = int(lab["Y"])
    M = int(lab["M"])
    return Y + (M - 0.5) / 12.0


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

    Returns: (centers, var, counts, coeffs_var) where coeffs_var are (a2,a1,a0).
    """
    import numpy as np
    x0, x1 = float(np.min(x)), float(np.max(x))
    nb = int(max(5, (x1 - x0) / bin_years))
    edges = np.linspace(x0, x1, nb + 1)

    centers = []
    variances = []
    counts = []

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

    # unweighted quadratic fit to variance
    a2, a1, a0 = np.polyfit(centers, variances, 2)
    return centers, variances, counts, (a2, a1, a0)


def vertex_of_parabola(c2: float, c1: float, c0: float):
    """Return (x*, y*) for y=c2 x^2 + c1 x + c0."""
    if abs(c2) < 1e-20:
        return (float("nan"), float("nan"))
    x0 = -c1 / (2.0 * c2)
    y0 = c2 * x0 * x0 + c1 * x0 + c0
    return x0, y0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Quadratic drift fit + spread visualization (DE422).")
    p.add_argument("--engine", default="mongol", help="phugpa|tsurphu|mongol|bhutan|karana")
    p.add_argument("--year-start", type=int, default=400)
    p.add_argument("--year-end", type=int, default=2000)
    p.add_argument("--max-months", type=int, default=0, help="0 means no cap (for quick tests set e.g. 2000)")
    p.add_argument("--filter-hours", type=float, default=50.0, help="Drop |offset| >= this many hours")
    p.add_argument("--out-png", default="drift_quadratic_fit.png")

    # spread controls
    p.add_argument("--window-years", type=float, default=100.0, help="Rolling window in years for mean±σ band")
    p.add_argument("--bin-years", type=float, default=10.0, help="Bin width in years for variance fit")
    p.add_argument("--min-bin-count", type=int, default=40, help="Min samples per variance bin")
    p.add_argument("--show-fit-sigma", action="store_true", help="Overlay sigma band from variance-fit (very light)")

    # plotting controls
    p.add_argument("--alpha", type=float, default=0.5, help="Scatter alpha")
    p.add_argument("--marker-size", type=float, default=2.0, help="Scatter marker size")
    p.add_argument("--plot-subsample", type=int, default=1, help="Plot every k-th point (fit uses all).")
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    engine = args.engine
    y0, y1 = args.year_start, args.year_end
    if y1 < y0:
        raise SystemExit("--year-end must be >= --year-start")

    # Internal engine object only to access raw true_date(d,n). Diagnostic-only.
    from caltib import api as _api
    eng_obj = _api._reg().get(engine)

    # 1) collect month-boundary samples
    n_list: List[int] = []
    t_tib: List[float] = []
    x_year: List[float] = []

    count = 0
    for Y in range(y0, y1 + 1):
        n_start, n_last = iter_lunations_for_year(engine, Y)
        for n in range(n_start, n_last + 1):
            n_list.append(n)
            t_tib.append(float(eng_obj.day.true_date(30, n - 1)))
            x_year.append(lunar_year_coordinate(engine, n))
            count += 1
            if args.max_months and count >= args.max_months:
                break
        if args.max_months and count >= args.max_months:
            break

    t_min, t_max = float(min(t_tib)), float(max(t_tib))
    print(f"Collected {len(t_tib)} samples; window JD ~ [{t_min:.1f}, {t_max:.1f}]")

    # 2) DE422 new moons
    el = DE422Elongation.load()
    print("Building DE422 new moons...")
    moons = build_new_moons(el, t_min - 60.0, t_max + 60.0)
    print(f"Built {len(moons)} DE422 new moons.")

    # 3) offsets
    k_match = match_monotone(t_tib, moons)
    t_de = np.array([moons[k] for k in k_match], dtype=float)
    offsets_h = 24.0 * (np.array(t_tib, dtype=float) - t_de)
    years = np.array(x_year, dtype=float)

    # 4) filter & sort
    mask = np.abs(offsets_h) < float(args.filter_hours)
    years_f = years[mask]
    off_f = offsets_h[mask]
    if len(off_f) < 100:
        raise RuntimeError(f"Too few points after filtering: {len(off_f)}")

    order = np.argsort(years_f)
    years_f = years_f[order]
    off_f = off_f[order]

    # Estimate samples per year for rolling window
    diffs = np.diff(years_f)
    step = float(np.median(diffs[diffs > 0]))  # ~ 1/12.37
    samples_per_year = max(1.0, 1.0 / step)
    window_pts = int(round(args.window_years * samples_per_year))
    if window_pts % 2 == 0:
        window_pts += 1

    roll_mean, roll_std = rolling_mean_std(years_f, off_f, window_pts=window_pts)

    # 5) drift quadratic fit
    c2, c1, c0 = np.polyfit(years_f, off_f, 2)
    drift_vertex_x, drift_vertex_y = vertex_of_parabola(c2, c1, c0)

    # 6) variance quadratic fit (binned)
    centers, var_bins, counts, (v2, v1, v0) = binned_variance_fit(
        years_f, off_f, bin_years=float(args.bin_years), min_count=int(args.min_bin_count)
    )
    var_vertex_x, var_vertex_y = vertex_of_parabola(v2, v1, v0)
    sigma_vertex = math.sqrt(var_vertex_y) if var_vertex_y > 0 else float("nan")

    # 7) print summary
    implied_tidal_coeff = -c2 * 3600.0 * 10000.0  # s/cy^2
    linear_drift_h_per_century = c1 * 100.0

    print("\n" + "=" * 72)
    print(f"ENGINE: {engine}")
    print(f"Drift fit: offset_h = {c2:.6e}*Y^2 + {c1:.6e}*Y + {c0:.3f}")
    print(f"  vertex: Y*={drift_vertex_x:.2f}, offset*={drift_vertex_y:.3f} h")
    print(f"  implied tidal coeff: {implied_tidal_coeff:.2f} s/cy^2")
    print(f"  linear drift: {linear_drift_h_per_century:.3f} h/century")

    print(f"Variance fit: var = {v2:.6e}*Y^2 + {v1:.6e}*Y + {v0:.6e}  (h^2)")
    print(f"  vertex (min): Y*={var_vertex_x:.2f}, var*={var_vertex_y:.6f} h^2, sigma*={sigma_vertex:.4f} h")
    print("=" * 72 + "\n")

    # 8) plot
    plt.figure(figsize=(12, 7))

    # raw scatter (subsample for aesthetics, fit uses all)
    k = max(1, int(args.plot_subsample))
    ys_plot = years_f[::k]
    off_plot = off_f[::k]
    plt.scatter(
        ys_plot, off_plot,
        s=float(args.marker_size),
        alpha=float(args.alpha),
        marker=".",
        linewidths=0,
        rasterized=True,
        label="raw offsets",
    )

    # quadratic drift curve on a smooth grid
    grid = np.linspace(float(years_f.min()), float(years_f.max()), 800)
    drift_fit_grid = c2 * grid**2 + c1 * grid + c0
    plt.plot(grid, drift_fit_grid, linewidth=3, label="quadratic fit")

    # rolling mean + sigma band (very light)
    ok = np.isfinite(roll_mean) & np.isfinite(roll_std)
    if ok.sum() > 10:
        plt.plot(years_f[ok], roll_mean[ok], linewidth=1.5, alpha=0.6, label=f"rolling mean ({args.window_years:g}y)")
        plt.fill_between(
            years_f[ok],
            roll_mean[ok] - roll_std[ok],
            roll_mean[ok] + roll_std[ok],
            alpha=0.08,  # very light
            linewidth=0,
            label="±1σ (rolling)",
        )

    # optional: sigma band from variance quadratic fit (even lighter)
    if args.show_fit_sigma:
        var_grid = v2 * grid**2 + v1 * grid + v0
        var_grid = np.maximum(var_grid, 0.0)
        sig_grid = np.sqrt(var_grid)
        plt.fill_between(
            grid,
            drift_fit_grid - sig_grid,
            drift_fit_grid + sig_grid,
            alpha=0.04,  # extremely light
            linewidth=0,
            label="±σ (var fit)",
        )

    # mark vertices
    if math.isfinite(drift_vertex_x):
        plt.axvline(drift_vertex_x, linestyle="--", linewidth=1, alpha=0.6)
    if math.isfinite(var_vertex_x):
        plt.axvline(var_vertex_x, linestyle=":", linewidth=1, alpha=0.6)

    plt.title(f"Quadratic Fit of Raw Drift ({args.year_start}-{args.year_end}) — {engine}")
    plt.xlabel("Lunar year coordinate  Y + (M-0.5)/12")
    plt.ylabel("Offset hours  (Tib raw - DE422 TT)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=200)
    print(f"Saved {args.out_png}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())