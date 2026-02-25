#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import caltib


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


# Meeus-like mean vernal equinox (JDE, TT). Adequate for this diagnostic.
def mean_vernal_equinox_jd(year: int) -> float:
    t = (year - 2000.0) / 1000.0
    return 2451623.80984 + 365242.37404 * t + 0.05169 * (t * t) - 0.00411 * (t * t * t)


def normalize_pm180(deg: float) -> float:
    return (deg + 180.0) % 360.0 - 180.0


def rolling_mean(np, y, win: int):
    """Centered rolling mean with NaN ends. win must be odd."""
    n = len(y)
    out = np.full(n, np.nan)
    if win < 3 or win > n:
        return out
    if win % 2 == 0:
        win += 1
    half = win // 2
    for i in range(half, n - half):
        out[i] = float(np.mean(y[i - half : i + half + 1]))
    return out


def iter_lunations_for_year(engine: str, Y: int) -> Tuple[int, int]:
    # JDN->date conversion not needed here; keep it JDN-only.
    n_start = caltib.month_bounds(Y, 1, is_leap_month=False, engine=engine, as_date=False)["n"]
    n_last = caltib.new_year_day(Y + 1, engine=engine, as_date=False)["n_last"]
    return int(n_start), int(n_last)


def build_global_grid(np, engine: str, year_start: int, year_end: int, sample_days: List[int]):
    """
    Build a robust interpolation grid of (jd, sun_deg_unwrapped) over an extended year range,
    by sampling true_date(d,n) and true_sun(d,n) for d in sample_days.
    """
    # Diagnostic-only access to raw true_date/true_sun
    from caltib import api as _api
    eng = _api._reg().get(engine)

    if not hasattr(eng.day, "true_sun"):
        raise RuntimeError(
            f"Engine '{engine}' day layer has no true_sun(d,n). "
            "Add it (returning true solar longitude in turns 0..1, or in degrees)."
        )

    jds: List[float] = []
    suns_deg: List[float] = []

    # extend range so equinox interpolation is safe at ends
    for Y in range(year_start - 1, year_end + 2):
        n0, n1 = iter_lunations_for_year(engine, Y)
        for n in range(n0, n1 + 1):
            for d in sample_days:
                jd = float(eng.day.true_date(d, n))
                s = eng.day.true_sun(d, n)  # expected turns (0..1) or degrees

                sf = float(s)
                # heuristic: if it's in [0,1.5], treat as turns
                if 0.0 <= sf <= 1.5:
                    sd = 360.0 * sf
                else:
                    sd = sf

                jds.append(jd)
                suns_deg.append(sd)

    # sort by JD, deduplicate exact ties, unwrap in radians
    idx = np.argsort(jds)
    jds = np.array(jds, dtype=float)[idx]
    suns_deg = np.array(suns_deg, dtype=float)[idx]

    # remove exact duplicate JD points (rare, but safe)
    jds_u, uidx = np.unique(jds, return_index=True)
    suns_deg_u = suns_deg[uidx]

    # unwrap
    rad = np.radians(suns_deg_u)
    rad_u = np.unwrap(rad)
    deg_u = np.degrees(rad_u)

    return jds_u, deg_u


def equinox_longitudes(np, engine: str, year_start: int, year_end: int, sample_days: List[int]):
    jds_grid, sun_unwrapped_deg = build_global_grid(np, engine, year_start, year_end, sample_days)

    years = np.arange(year_start, year_end + 1, dtype=int)
    vals = np.zeros(len(years), dtype=float)

    for i, Y in enumerate(years):
        jd_eq = mean_vernal_equinox_jd(int(Y))
        sun_eq = float(np.interp(jd_eq, jds_grid, sun_unwrapped_deg))
        vals[i] = normalize_pm180(sun_eq)

    return years, vals


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Plot Tibetan true solar longitude at (mean) vernal equinox (Meeus JDE), per tradition."
    )
    p.add_argument("--year-start", type=int, default=450)
    p.add_argument("--year-end", type=int, default=2000)
    p.add_argument("--engines", default="karana,phugpa,tsurphu,mongol,bhutan",
                   help="Comma-separated engine list.")
    p.add_argument("--out", default="raw_equinox_longitude.png")
    p.add_argument("--sample-days", default="15,30",
                   help="Comma list of tithi boundaries d to sample for interpolation grid (default: 15,30).")
    p.add_argument("--smooth", type=int, default=11,
                   help="Rolling mean window (years) for trendline (odd recommended).")
    p.add_argument("--ref", default="0,-8",
                   help="Comma list of horizontal reference lines in degrees (default: 0,-8).")
    p.add_argument("--print-years", default="1027,1318,1350,1447,1747",
                   help="Comma list of years to print 'inception' values for (default: common ones).")
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    if args.year_end < args.year_start:
        raise SystemExit("--year-end must be >= --year-start")

    engines = [x.strip() for x in args.engines.split(",") if x.strip()]
    sample_days = [int(x.strip()) for x in args.sample_days.split(",") if x.strip()]
    ref_lines = [float(x.strip()) for x in args.ref.split(",") if x.strip()]
    print_years = [int(x.strip()) for x in args.print_years.split(",") if x.strip()]

    colors: Dict[str, str] = {
        "karana": "tab:red",
        "phugpa": "tab:blue",
        "tsurphu": "tab:green",
        "mongol": "tab:orange",
        "bhutan": "tab:purple",
    }

    plt.figure(figsize=(12, 8))

    for r in ref_lines:
        plt.axhline(r, linestyle="--" if abs(r) > 1e-9 else ":", alpha=0.4, linewidth=1)

    results: Dict[str, Dict[int, float]] = {}

    for eng in engines:
        print(f"Processing {eng} ...")
        years, suns = equinox_longitudes(np, eng, args.year_start, args.year_end, sample_days)
        results[eng] = {int(y): float(v) for y, v in zip(years, suns)}

        c = colors.get(eng, "gray")
        plt.scatter(years, suns, s=3, alpha=0.25, color=c)

        if args.smooth and args.smooth >= 3:
            sm = rolling_mean(np, suns, int(args.smooth))
            ok = np.isfinite(sm)
            plt.plot(years[ok], sm[ok], linewidth=2, color=c, label=eng)
        else:
            plt.plot(years, suns, linewidth=1.5, color=c, label=eng)

    # Print selected years
    print("\nSolar longitude at (mean) vernal equinox (deg, normalized to [-180,180)):")
    for Y in print_years:
        parts = []
        for eng in engines:
            v = results.get(eng, {}).get(Y, float("nan"))
            parts.append(f"{eng}:{v:6.1f}")
        print(f"{Y}:  " + "  ".join(parts))

    plt.title("Raw Tibetan true solar longitude at mean vernal equinox (Meeus JDE)\n(no target subtraction)")
    plt.xlabel("Year AD")
    plt.ylabel("True solar longitude (deg) normalized to [-180,180)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.out, dpi=200)
    print(f"\nSaved: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())