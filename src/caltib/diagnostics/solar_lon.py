#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, List, Optional

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
        import matplotlib.dates as mdates
        return plt, mdates
    except ImportError as e:
        raise RuntimeError('Need matplotlib. Install: pip install "caltib[tools]"') from e

def jd_to_datetime(jd: float) -> datetime.datetime:
    """Rough conversion from JD to Gregorian datetime for plotting."""
    return datetime.datetime(2000, 1, 1, 12, 0, 0) + datetime.timedelta(days=(jd - 2451545.0))

def parse_engine_list(s: str) -> List[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


@dataclass(frozen=True)
class SeriesData:
    label: str
    times: "np.ndarray"      # JD (float)
    error_deg: "np.ndarray"  # degrees


def sun_error_series(np, engine: str, ephem_evaluator, jd_start: float, jd_end: float, step_days: float, use_month: bool = False, label: str = "") -> Optional[SeriesData]:
    """
    Evaluates the pure raw error: Engine True Sun - Reference True Sun.
    """
    eng = get_calendar(engine)
    ts = np.arange(jd_start, jd_end + 1e-12, step_days, dtype=float)
    
    errors: List[float] = []

    for jd in ts:
        t2000_frac = Fraction(jd) - Fraction(2451545)
        
        # 1. Get Engine True Sun
        if use_month:
            if not hasattr(eng, "month") or not hasattr(eng.month, "true_sun_tt"):
                return None
            eng_s_turns = float(eng.month.true_sun_tt(t2000_frac))
        else:
            if not hasattr(eng, "day") or not hasattr(eng.day, "true_sun_tt"):
                return None
            eng_s_turns = float(eng.day.true_sun_tt(t2000_frac))
            
        eng_deg = eng_s_turns * 360.0
        
        # 2. Get Reference True Sun
        ref_deg = ephem_evaluator(jd)
        
        # 3. Calculate Error (wrapped to shortest path [-180, 180])
        err_deg = (eng_deg - ref_deg) % 360.0
        if err_deg > 180.0:
            err_deg -= 360.0
            
        errors.append(err_deg)

    if not errors:
        return None

    e_arr = np.array(errors, dtype=float)
    final_label = label if label else engine
    return SeriesData(final_label, ts, e_arr)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Raw True Solar Longitude Error vs Truth Ephemeris.")
    p.add_argument("--engines", default="phugpa,mongol,l1,l3,l4",
                   help="Comma list of reform engines to plot.")
    p.add_argument("--ephem", choices=("ref", "de422"), default="ref", help="Reference Ephemeris or DE422")
    p.add_argument("--year-start", type=int, default=None, help="Start year (e.g., 1500). Overrides center/window.")
    p.add_argument("--year-end", type=int, default=None, help="End year (e.g., 2100).")
    p.add_argument("--date-start", type=str, default=None, help="Start date (YYYY-MM-DD) or (YYYY.MM.DD)")
    p.add_argument("--date-end", type=str, default=None, help="End date (YYYY-MM-DD) or (YYYY.MM.DD)")
    p.add_argument("--jd-start", type=float, default=None, help="Start JD (TT-like) as float.")
    p.add_argument("--jd-end", type=float, default=None, help="End JD (TT-like) as float.")
    p.add_argument("--center-jd", type=float, default=2461072.5, help="Center JD if start/end not given.")
    p.add_argument("--window", type=float, default=200.0, help="Half-window in days if start/end not given.")
    
    p.add_argument("--step", type=float, default=0.25, help="Sampling step in days (use larger values like 10 for deep-time).")
    p.add_argument("--out", default="error_sun.png", help="Output PNG filename.")
    args = p.parse_args(argv)

    np = need_numpy()
    plt, mdates = need_matplotlib()

    if args.date_start and args.date_end:
        ds_clean = args.date_start.replace(".", "-").replace("/", "-")
        de_clean = args.date_end.replace(".", "-").replace("/", "-")
        dt_start = datetime.datetime.strptime(ds_clean, "%Y-%m-%d")
        dt_end = datetime.datetime.strptime(de_clean, "%Y-%m-%d")
        jd_start = dt_start.toordinal() + 1721424.5
        jd_end = dt_end.toordinal() + 1721424.5
    elif args.jd_start is not None and args.jd_end is not None:
        jd_start = float(args.jd_start)
        jd_end = float(args.jd_end)
    else:
        jd_start = float(args.center_jd) - float(args.window)
        jd_end = float(args.center_jd) + float(args.window)

    engines = parse_engine_list(args.engines)
    span_days = jd_end - jd_start
    use_years_axis = span_days > 1500

    actual_step = float(args.step)
    if span_days / actual_step > 5000:
        actual_step = span_days / 5000.0
        print(f"Notice: Auto-scaled sampling step to {actual_step:.2f} days to prevent CPU overload.")
        
    print(f"Interval JD: [{jd_start:.3f}, {jd_end:.3f}]  (span {span_days:.1f} days)")
    print(f"Evaluating raw solar error vs {args.ephem.upper()}...")
    print(f"Engines: {engines}")

    # Set up the reference evaluator function dynamically
    if args.ephem == "de422":
        try:
            from caltib.ephemeris.de422 import DE422Sun
            sun_mod = DE422Sun.load()
            ephem_evaluator = sun_mod.sun_deg
        except ImportError:
            raise RuntimeError("DE422Sun wrapper not found. Please use --ephem ref")
    else:
        from caltib.reference.solar import solar_longitude
        def ephem_evaluator(jd):
            return solar_longitude(jd).L_true_deg

    series: List[SeriesData] = []

    # Calculate error series for requested engines
    for eng_str in engines:
        is_month = False
        base_eng = eng_str
        label = eng_str
        
        if eng_str.endswith("-m"):
            base_eng = eng_str[:-2]
            is_month = True
            label = f"{base_eng} (Month)"
            
        try:
            s = sun_error_series(np, base_eng, ephem_evaluator, jd_start, jd_end, actual_step, use_month=is_month, label=label)
            if s is None:
                print(f"  {eng_str}: no samples in interval or missing component")
            else:
                print(f"  {eng_str}: {len(s.times)} samples")
                series.append(s)
        except Exception as e:
            print(f"  {eng_str}: ERROR: {e}")

    # Plot
    colors: Dict[str, str] = {
        "phugpa": "tab:orange", "tsurphu": "tab:green", "mongol": "tab:purple",
        "bhutan": "tab:red", "karana": "tab:brown", 
        "l0": "tab:brown", "l1": "tab:pink", "l2": "tab:cyan", 
        "l3": "tab:olive", "l4": "gold"
    }

    plt.figure(figsize=(12, 5))

    # Add a bold dashed line exactly at Y=0 to represent the Reference Ephemeris Truth
    ref_label = "Reference (ELP2000)" if args.ephem == "ref" else "DE422 Ephemeris"
    plt.axhline(0, color="black", linestyle="--", linewidth=1.5, alpha=0.9, label=f"{ref_label} (0 Error)")

    fig, ax = plt.subplots(figsize=(12, 5))

    # Add a bold dashed line exactly at Y=0 to represent the Reference Ephemeris Truth
    ref_label = "Reference (ELP2000)" if args.ephem == "ref" else "DE422 Ephemeris"
    ax.axhline(0, color="black", linestyle="--", linewidth=1.5, alpha=0.9, label=f"{ref_label} (0 Error)")

    for s in series:
        # Convert JD to datetimes for Matplotlib's auto-formatter
        x_dates = [jd_to_datetime(jd) for jd in s.times]
        
        base_name = s.label.replace(" (Month)", "")
        c = colors.get(base_name, "tab:blue")
        
        l_style = ":" if " (Month)" in s.label else "-"
        l_width = 2.0 if " (Month)" in s.label else 1.2
        
        ax.plot(x_dates, s.error_deg, linestyle=l_style, color=c, linewidth=l_width, alpha=0.8, label=s.label)

    # Clean, horizontal, uncluttered Concise Date Formatter
    locator = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    engine_types = "Month Engines" if any("-m" in eng for eng in args.engines) else "Day Engines"
    plt.title(f"Raw True Solar Longitude Error ({engine_types} − Reference)\nContinuous Physical Time vs {args.ephem.upper()} Ephemeris")
    plt.xlabel("Gregorian Date (TT)")
    plt.ylabel("Error (degrees)")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(args.out, dpi=180)
    print(f"Saved: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())