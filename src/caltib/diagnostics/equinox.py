#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Dict, List, Optional

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


def mean_vernal_equinox_jd(year: int) -> float:
    """Meeus mean vernal equinox (JDE, TT) used as a baseline guess."""
    t = (year - 2000.0) / 1000.0
    return 2451623.80984 + 365242.37404 * t + 0.05169 * (t * t) - 0.00411 * (t * t * t)


def find_true_vernal_equinox(year: int, evaluator) -> float:
    """
    Finds the exact JD(TT) where true/apparent solar longitude is exactly 0 degrees.
    Uses a highly efficient Secant root-finder seeded by the mean equinox.
    """
    if evaluator is None:
        return mean_vernal_equinox_jd(year)
        
    jd_guess = mean_vernal_equinox_jd(year)
    
    def error(jd: float) -> float:
        e = evaluator(jd)
        d = (e - 0.0) % 360.0
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


def build_global_grid(np, engine: str, jd_min: float, jd_max: float):
    """
    Builds a robust, continuous interpolation grid of (jd, sun_deg_unwrapped)
    using the absolute continuous tithi (x) architecture.
    """
    eng = get_calendar(engine)

    if not hasattr(eng.day, "true_sun"):
        raise RuntimeError(f"Engine '{engine}' has no true_sun(x) property.")

    # Expand boundaries slightly to ensure safe interpolation
    x_start = eng.day.get_x_from_t2000(jd_min - 30.0 - 2451545.0)
    x_end = eng.day.get_x_from_t2000(jd_max + 30.0 - 2451545.0)

    jds: List[float] = []
    suns_deg: List[float] = []

    # Sample strictly every 15 tithis (New Moon and Full Moon) to build a tight grid
    for x in range(x_start, x_end + 1, 15):
        jd = float(eng.day.true_date(x)) + 2451545.0
            
        s = float(eng.day.true_sun(x))
        sd = 360.0 * s if 0.0 <= s <= 1.5 else s

        jds.append(jd)
        suns_deg.append(sd)

    # Sort, deduplicate, and unwrap safely
    idx = np.argsort(jds)
    jds = np.array(jds, dtype=float)[idx]
    suns_deg = np.array(suns_deg, dtype=float)[idx]

    jds_u, uidx = np.unique(jds, return_index=True)
    suns_deg_u = suns_deg[uidx]

    rad = np.radians(suns_deg_u)
    rad_u = np.unwrap(rad)
    deg_u = np.degrees(rad_u)

    return jds_u, deg_u


def equinox_longitudes(np, engine: str, years: "np.ndarray", evaluator):
    # Find exact equinox JD boundaries to constrain our sampling grid
    jd_eq_list = [find_true_vernal_equinox(int(y), evaluator) for y in years]
    
    jds_grid, sun_unwrapped_deg = build_global_grid(np, engine, min(jd_eq_list), max(jd_eq_list))
    vals = np.zeros(len(years), dtype=float)

    for i, jd_eq in enumerate(jd_eq_list):
        sun_eq = float(np.interp(jd_eq, jds_grid, sun_unwrapped_deg))
        vals[i] = normalize_pm180(sun_eq)

    return years, vals


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Plot Engine true solar longitude at the Vernal Equinox.")
    p.add_argument("--year-start", type=int, default=450)
    p.add_argument("--year-end", type=int, default=2000)
    p.add_argument("--engines", default="karana,phugpa,tsurphu,mongol,l1",
                   help="Comma-separated engine list.")
    p.add_argument("--ephem", choices=("ref", "de422", "mean"), default="ref", 
                   help="Method for defining the exact equinox time (Default: True Apparent Vernal Equinox via REF).")
    p.add_argument("--out", default="equinox.png")
    p.add_argument("--smooth", type=int, default=11, help="Rolling mean window (years) for trendline.")
    p.add_argument("--ref", default="0,-8", help="Comma list of horizontal reference lines in degrees.")
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    if args.year_end < args.year_start:
        raise SystemExit("--year-end must be >= --year-start")

    engines = [x.strip() for x in args.engines.split(",") if x.strip()]
    ref_lines = [float(x.strip()) for x in args.ref.split(",") if x.strip()]

    # Setup Evaluator
    evaluator = None
    if args.ephem == "de422":
        try:
            from caltib.ephemeris.de422 import DE422Solar
            sol = DE422Solar.load()
            def evaluator(jd): return sol.app_lon_deg(jd)
        except ImportError as e:
            raise SystemExit("DE422 ephemeris tools not available. Use --ephem ref") from e
    elif args.ephem == "ref":
        from caltib.reference.solar import solar_longitude
        def evaluator(jd): return solar_longitude(jd).L_app_deg

    colors: Dict[str, str] = {
        "karana": "tab:red", "phugpa": "tab:blue", "tsurphu": "tab:green",
        "mongol": "tab:orange", "bhutan": "tab:purple", "l1": "tab:pink",
        "l2": "tab:cyan", "l3": "tab:olive", "l4": "gold"
    }

    plt.figure(figsize=(12, 8))
    for r in ref_lines:
        plt.axhline(r, linestyle="--" if abs(r) > 1e-9 else ":", alpha=0.4, linewidth=1)

    years = np.arange(args.year_start, args.year_end + 1, dtype=int)
    
    eq_type_label = "Mean Meeus" if args.ephem == "mean" else f"True Apparent ({args.ephem.upper()})"
    print(f"Evaluating solar longitude at {eq_type_label} Vernal Equinox...")

    for eng in engines:
        _, suns = equinox_longitudes(np, eng, years, evaluator)

        c = colors.get(eng, "gray")
        plt.scatter(years, suns, s=3, alpha=0.25, color=c)

        if args.smooth and args.smooth >= 3:
            sm = rolling_mean(np, suns, int(args.smooth))
            ok = np.isfinite(sm)
            plt.plot(years[ok], sm[ok], linewidth=2, color=c, label=eng)
        else:
            plt.plot(years, suns, linewidth=1.5, color=c, label=eng)

    plt.title(f"Engine Solar Longitude vs Seasons\nEvaluated precisely at the {eq_type_label} Vernal Equinox")
    plt.xlabel("Year AD")
    plt.ylabel("Engine True Solar Longitude (deg)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.out, dpi=200)
    print(f"\nSaved: {args.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())