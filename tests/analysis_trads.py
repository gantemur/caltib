#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import caltib
from caltib.ephemeris.de422 import DE422Elongation, build_new_moons


def _need_numpy():
    try:
        import numpy as np  # noqa: F401
        return np
    except ImportError as e:
        raise RuntimeError('Need numpy. Install: pip install "caltib[diagnostics]"') from e


def _need_matplotlib():
    try:
        import matplotlib.pyplot as plt  # noqa: F401
        return plt
    except ImportError as e:
        raise RuntimeError('Need matplotlib. Install: pip install "caltib[diagnostics]"') from e


@dataclass(frozen=True)
class Trad:
    name: str
    engine: str


DEFAULT_TRADS: List[Trad] = [
    Trad("Phugpa", "phugpa"),
    Trad("Tsurphu", "tsurphu"),
    Trad("Mongol", "mongol"),
    Trad("Bhutan", "bhutan"),
    # Trad("Karana", "karana"),  # optional
]


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
    n_start = caltib.month_bounds(Y, 1, is_leap_month=False, engine=engine, as_date=False)["n"]
    n_last = caltib.new_year_day(Y + 1, engine=engine, as_date=False)["n_last"]
    return int(n_start), int(n_last)


def lunar_year_coordinate(engine: str, n: int) -> float:
    info = caltib.month_from_n(n, engine=engine, debug=False)
    lab = info["label_from_true_month"]
    Y = int(lab["Y"])
    M = int(lab["M"])
    return Y + (M - 0.5) / 12.0


def delta_t_hours_simple(year_coord: float) -> float:
    """
    ΔT model in seconds: -20 + 32 u^2, where u=(year-1820)/100.
    Convert to hours.
    """
    u = (year_coord - 1820.0) / 100.0
    dt_sec = -20.0 + 32.0 * u * u
    return dt_sec / 3600.0


def rolling_std(y, window_pts: int):
    """
    Centered rolling std (ddof=0). Returns array with NaNs at ends.
    """
    import numpy as np
    n = len(y)
    out = np.full(n, np.nan)
    if window_pts < 3 or window_pts > n:
        return out
    w = window_pts
    half = w // 2
    for i in range(half, n - half):
        seg = y[i - half : i + half + 1]
        out[i] = float(np.std(seg, ddof=0))
    return out


def parabola_vertex(A: float, B: float, C: float) -> Tuple[float, float]:
    if abs(A) < 1e-20:
        return (float("nan"), float("nan"))
    x0 = -B / (2.0 * A)
    y0 = A * x0 * x0 + B * x0 + C
    return x0, y0


def drift_h_per_century(A: float, B: float, year: float) -> float:
    """
    If offset(y) = A y^2 + B y + C (hours), then d/dy = 2A y + B (hours/year).
    Return hours/century.
    """
    return (2.0 * A * year + B) * 100.0


def collect_for_trad(engine: str, y0: int, y1: int, max_months: int) -> Tuple[List[float], List[float], List[int]]:
    """
    Collect (year_coord, t_tib, n_list) for month-boundary samples:
      t_tib = true_date(30, n-1) as float JD-like
    """
    from caltib import api as _api
    eng_obj = _api._reg().get(engine)

    xs: List[float] = []
    ts: List[float] = []
    ns: List[int] = []

    count = 0
    for Y in range(y0, y1 + 1):
        n_start, n_last = iter_lunations_for_year(engine, Y)
        for n in range(n_start, n_last + 1):
            xs.append(lunar_year_coordinate(engine, n))
            ts.append(float(eng_obj.day.true_date(30, n - 1)))
            ns.append(n)
            count += 1
            if max_months and count >= max_months:
                return xs, ts, ns
    return xs, ts, ns


def analyze_one(np, moons: List[float], name: str, engine: str,
                y0: int, y1: int, sigma_window_years: float,
                filter_hours: float, max_months: int,
                apply_delta_t: bool) -> Dict[str, object]:
    xs, t_tib, ns = collect_for_trad(engine, y0, y1, max_months=max_months)

    years = np.array(xs, dtype=float)
    t_tib = np.array(t_tib, dtype=float)

    k_match = match_monotone(list(t_tib), moons)
    t_de = np.array([moons[k] for k in k_match], dtype=float)

    raw_offsets = 24.0 * (t_tib - t_de)  # hours (Tib raw - TT)

    if apply_delta_t:
        dt = np.array([delta_t_hours_simple(y) for y in years], dtype=float)
        offsets = raw_offsets + dt  # Tib - (TT-ΔT) = (Tib-TT)+ΔT
    else:
        offsets = raw_offsets

    mask = np.abs(offsets) < float(filter_hours)
    years_f = years[mask]
    off_f = offsets[mask]
    if len(off_f) < 200:
        raise RuntimeError(f"{name}: too few samples after filtering ({len(off_f)})")

    order = np.argsort(years_f)
    years_f = years_f[order]
    off_f = off_f[order]

    # Quadratic drift fit
    A, B, C = np.polyfit(years_f, off_f, 2)
    vx, vy = parabola_vertex(A, B, C)

    # Rolling sigma
    diffs = np.diff(years_f)
    step = float(np.median(diffs[diffs > 0]))
    samples_per_year = max(1.0, 1.0 / step)
    window_pts = int(round(sigma_window_years * samples_per_year))
    if window_pts % 2 == 0:
        window_pts += 1

    sig = rolling_std(off_f, window_pts=window_pts)
    ok = np.isfinite(sig)
    if ok.sum() == 0:
        sigma_min_year = float("nan")
        sigma_min_val = float("nan")
    else:
        j = int(np.nanargmin(sig))
        sigma_min_year = float(years_f[j])
        sigma_min_val = float(sig[j])

    return {
        "label": name,
        "engine": engine,
        "years": years_f,
        "offsets": off_f,
        "fit_coeffs": (float(A), float(B), float(C)),
        "vertex_year": float(vx),
        "vertex_offset": float(vy),
        "sigma_min_year": float(sigma_min_year),
        "sigma_min_val": float(sigma_min_val),
        "drift_0": float(drift_h_per_century(A, B, 0.0)),
        "drift_1000": float(drift_h_per_century(A, B, 1000.0)),
        "drift_2000": float(drift_h_per_century(A, B, 2000.0)),
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Final metrics: sigma minima + drift vertices + drift rates (DE422).")
    p.add_argument("--year-start", type=int, default=-500)
    p.add_argument("--year-end", type=int, default=2500)
    p.add_argument("--sigma-window", type=float, default=100.0, help="Rolling sigma window (years)")
    p.add_argument("--filter-hours", type=float, default=50.0)
    p.add_argument("--max-months", type=int, default=0, help="0 means no cap (debug: set e.g. 5000)")

    p.add_argument("--apply-delta-t", action="store_true",
                   help="Apply ΔT = (-20 + 32u^2) seconds to convert TT->UT approximately.")
    p.add_argument("--out-drift", default="final_metrics_drift.png")
    p.add_argument("--out-sigma", default="final_metrics_sigma.png")

    p.add_argument("--traditions", default="",
                   help='Comma list of engines, e.g. "phugpa,tsurphu,mongol,bhutan" (default: 4 traditions).')
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    y0, y1 = args.year_start, args.year_end
    if y1 < y0:
        raise SystemExit("--year-end must be >= --year-start")

    # choose traditions
    if args.traditions.strip():
        engines = [x.strip() for x in args.traditions.split(",") if x.strip()]
        trads = [Trad(e.capitalize(), e) for e in engines]
    else:
        trads = DEFAULT_TRADS

    # collect global window across traditions to build one DE422 moon list
    print(f"Preparing DE422 new moons for years {y0}..{y1} (global window) ...")
    global_min = None
    global_max = None

    from caltib import api as _api
    for tr in trads:
        eng_obj = _api._reg().get(tr.engine)
        xs, ts, ns = collect_for_trad(tr.engine, y0, y1, max_months=args.max_months)
        if not ts:
            continue
        tmin, tmax = min(ts), max(ts)
        global_min = tmin if global_min is None else min(global_min, tmin)
        global_max = tmax if global_max is None else max(global_max, tmax)
        print(f"  {tr.name}: {len(ts)} samples, JD ~ [{tmin:.1f}, {tmax:.1f}]")

    if global_min is None or global_max is None:
        raise SystemExit("No data collected.")

    el = DE422Elongation.load()
    moons = build_new_moons(el, global_min - 80.0, global_max + 80.0)
    print(f"Built {len(moons)} DE422 new moons.\n")

    # analyze each tradition
    results: List[Dict[str, object]] = []
    for tr in trads:
        try:
            res = analyze_one(
                np=np,
                moons=moons,
                name=tr.name,
                engine=tr.engine,
                y0=y0,
                y1=y1,
                sigma_window_years=float(args.sigma_window),
                filter_hours=float(args.filter_hours),
                max_months=int(args.max_months),
                apply_delta_t=bool(args.apply_delta_t),
            )
            results.append(res)
        except Exception as e:
            print(f"Failed {tr.name}: {e}")

    if not results:
        raise SystemExit("No successful results.")

    # print summary table
    print("\n" + "=" * 110)
    print(f"{'TRADITION':<12} | {'SIGMA MIN':<10} | {'VERTEX':<10} | {'DRIFT(0)':<10} | {'DRIFT(1000)':<11} | {'DRIFT(2000)':<11}")
    print(f"{'':<12} | {'(AD)':<10} | {'(AD)':<10} | {'(h/cy)':<10} | {'(h/cy)':<11} | {'(h/cy)':<11}")
    print("-" * 110)
    for r in results:
        print(
            f"{r['label']:<12} | "
            f"{r['sigma_min_year']:<10.0f} | "
            f"{r['vertex_year']:<10.0f} | "
            f"{r['drift_0']:<10.4f} | "
            f"{r['drift_1000']:<11.4f} | "
            f"{r['drift_2000']:<11.4f}"
        )
    print("-" * 110)
    print("NOTE: Drift is d/dY of the fitted offset curve, reported in hours/century.")
    if args.apply_delta_t:
        print("NOTE: ΔT correction applied: offsets ≈ (Tib - TT) + ΔT(year).")
    print("=" * 110 + "\n")

    # -----------------------
    # Plot 1: Drift fit curves
    # -----------------------
    plt.figure(figsize=(10, 6))
    for r in results:
        years = r["years"]
        A, B, C = r["fit_coeffs"]
        fit = A * years**2 + B * years + C
        plt.plot(years, fit, linewidth=2, label=f"{r['label']} (v~{r['vertex_year']:.0f})")
    plt.title("Mean Drift (Quadratic Fit)" + (" — ΔT corrected" if args.apply_delta_t else ""))
    plt.xlabel("Year coordinate  Y + (M-0.5)/12")
    plt.ylabel("Offset (hours)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.out_drift, dpi=200)
    print(f"Saved: {args.out_drift}")

    # -----------------------
    # Plot 2: Rolling sigma curves
    # -----------------------
    plt.figure(figsize=(10, 6))
    for r in results:
        years = r["years"]
        offsets = r["offsets"]
        diffs = np.diff(years)
        step = float(np.median(diffs[diffs > 0]))
        samples_per_year = max(1.0, 1.0 / step)
        window_pts = int(round(float(args.sigma_window) * samples_per_year))
        if window_pts % 2 == 0:
            window_pts += 1
        sig = rolling_std(offsets, window_pts=window_pts)
        plt.plot(years, sig, linewidth=2, label=f"{r['label']} (min~{r['sigma_min_year']:.0f})")

    plt.title(f"Spread / Sigma (rolling {args.sigma_window:g}y window)")
    plt.xlabel("Year coordinate  Y + (M-0.5)/12")
    plt.ylabel("Std dev (hours)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.out_sigma, dpi=200)
    print(f"Saved: {args.out_sigma}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())