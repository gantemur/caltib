#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import List, Optional, Tuple

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
    color: str


DEFAULT_TRADS: List[Trad] = [
    Trad("Karana", "karana", "red"),
    Trad("Tsurphu", "tsurphu", "violet"),
    Trad("Mongol", "mongol", "blue"),
    Trad("Bhutan", "bhutan", "green"),
    Trad("Phugpa", "phugpa", "orange"),
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
    """
    Return (n_start, n_last) for lunar year Y, inclusive.

    n_start = n(Y,1,False)
    n_last  = new_year_day(Y+1)["n_last"]  (last month of year Y)
    """
    n_start = caltib.month_bounds(Y, 1, is_leap_month=False, engine=engine)["n"]
    n_last = caltib.new_year_day(Y + 1, engine=engine)["n_last"]
    return int(n_start), int(n_last)


def lunar_year_coordinate(engine: str, n: int) -> float:
    """
    Plot x-coordinate as Y + (M-0.5)/12 using engine month inversion.
    """
    info = caltib.month_from_n(n, engine=engine, debug=False)
    lab = info["label_from_true_month"]
    Y = int(lab["Y"])
    M = int(lab["M"])
    return Y + (M - 0.5) / 12.0


def collect_month_boundaries(engine: str, y0: int, y1: int, max_months: int) -> Tuple[List[float], List[float]]:
    """
    Return (x_year, t_tib) where:
      t_tib[i] = float(true_date(30, n-1)) for the i-th lunation n in [y0..y1]
      x_year[i] = Y + (M-0.5)/12 for that lunation's label
    """
    # Diagnostic-only: access raw true_date (Fraction) through internal engine object.
    from caltib import api as _api
    eng_obj = _api._reg().get(engine)

    xs: List[float] = []
    ts: List[float] = []

    count = 0
    for Y in range(y0, y1 + 1):
        n_start, n_last = iter_lunations_for_year(engine, Y)
        for n in range(n_start, n_last + 1):
            xs.append(lunar_year_coordinate(engine, n))
            ts.append(float(eng_obj.day.true_date(30, n - 1)))
            count += 1
            if max_months and count >= max_months:
                return xs, ts
    return xs, ts


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Plot raw drift vs DE422 for multiple traditions (no spread bands).")
    p.add_argument("--year-start", type=int, default=700)
    p.add_argument("--year-end", type=int, default=2000)
    p.add_argument("--out-png", default="traditions_drift.png")
    p.add_argument("--filter-hours", type=float, default=50.0)
    p.add_argument("--alpha", type=float, default=0.1)
    p.add_argument("--marker-size", type=float, default=2.0)
    p.add_argument("--plot-subsample", type=int, default=2, help="Plot every k-th point (fit uses all).")
    p.add_argument("--max-months", type=int, default=0, help="0 = no cap (debug: set e.g. 4000)")
    p.add_argument(
        "--traditions",
        default="",
        help='Optional override: comma list like "karana,phugpa,mongol" (default: all 5).',
    )
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    y0, y1 = args.year_start, args.year_end
    if y1 < y0:
        raise SystemExit("--year-end must be >= --year-start")

    # choose traditions
    if args.traditions.strip():
        wanted = [x.strip() for x in args.traditions.split(",") if x.strip()]
        trads = [t for t in DEFAULT_TRADS if t.engine in wanted]
        if not trads:
            raise SystemExit(f"No traditions matched {wanted}. Known engines: {[t.engine for t in DEFAULT_TRADS]}")
    else:
        trads = DEFAULT_TRADS

    # 1) collect all traditions data first (to get global time window for DE422 moons)
    data = []
    global_min = None
    global_max = None

    print(f"Collecting data for years {y0}..{y1} ...")
    for tr in trads:
        xs, ts = collect_month_boundaries(tr.engine, y0, y1, args.max_months)
        if not ts:
            print(f"  {tr.name}: no samples")
            continue
        tmin, tmax = min(ts), max(ts)
        global_min = tmin if global_min is None else min(global_min, tmin)
        global_max = tmax if global_max is None else max(global_max, tmax)
        data.append((tr, np.array(xs, dtype=float), np.array(ts, dtype=float)))
        print(f"  {tr.name}: {len(ts)} samples, JD ~ [{tmin:.1f}, {tmax:.1f}]")

    if global_min is None or global_max is None:
        raise SystemExit("No data collected.")

    # 2) build DE422 moons once over the global window
    el = DE422Elongation.load()
    print(f"Building DE422 new moons over JD ~ [{global_min:.1f}, {global_max:.1f}] ...")
    moons = build_new_moons(el, global_min - 60.0, global_max + 60.0)
    print(f"Built {len(moons)} DE422 new moons.")

    # 3) plot
    plt.figure(figsize=(12, 7))

    for tr, years, t_tib in data:
        # match
        k_match = match_monotone(list(t_tib), moons)
        t_de = np.array([moons[k] for k in k_match], dtype=float)
        offsets = 24.0 * (t_tib - t_de)

        # filter
        mask = np.abs(offsets) < float(args.filter_hours)
        years_f = years[mask]
        off_f = offsets[mask]
        if len(off_f) < 30:
            print(f"  {tr.name}: too few points after filtering ({len(off_f)}); skipping fit")
            continue

        # quadratic fit
        c2, c1, c0 = np.polyfit(years_f, off_f, 2)
        implied_tidal = -c2 * 3600.0 * 10000.0

        print(f"\n{tr.name} ({tr.engine})")
        print(f"  fit: offset_h = {c2:.6e}*Y^2 + {c1:.6e}*Y + {c0:.3f}")
        print(f"  implied tidal coeff: {implied_tidal:.2f} s/cy^2")

        # scatter (subsample for aesthetics)
        k = max(1, int(args.plot_subsample))
        plt.scatter(
            years_f[::k],
            off_f[::k],
            s=float(args.marker_size),
            alpha=float(args.alpha),
            marker=".",
            linewidths=0,
            rasterized=True,
            color=tr.color,
        )

        # fit line on smooth grid
        grid = np.linspace(float(years_f.min()), float(years_f.max()), 600)
        fit = c2 * grid**2 + c1 * grid + c0
        plt.plot(grid, fit, color=tr.color, linewidth=2.5, label=f"{tr.name} fit")

    plt.title(f"Raw Drift vs DE422 ({y0}-{y1}) — multiple traditions")
    plt.xlabel("Lunar year coordinate  Y + (M-0.5)/12")
    plt.ylabel("Offset hours  (Tib raw - DE422 TT)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=200)
    print(f"\nSaved {args.out_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())