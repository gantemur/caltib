#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
        return plt
    except ImportError as e:
        raise RuntimeError('Need matplotlib. Install: pip install "caltib[tools]"') from e


def parse_engine_list(s: str) -> List[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


@dataclass(frozen=True)
class SeriesData:
    label: str
    times: "np.ndarray"        # JD (float)
    anomaly_deg: "np.ndarray"  # degrees


def detrended_anomaly(np, times: "np.ndarray", angles_deg: "np.ndarray") -> "np.ndarray":
    """
    Given monotone unwrapped angles_deg vs times, subtract best linear fit and mean.
    """
    coeffs = np.polyfit(times, angles_deg, 1)
    mean_line = np.polyval(coeffs, times)
    anom = angles_deg - mean_line
    anom = anom - float(np.mean(anom))
    return anom


def sun_anomaly_series(np, engine: str, jd_start: float, jd_end: float, step_days: float, use_month: bool = False, label: str = "") -> Optional[SeriesData]:
    """
    Evaluates the pure forward solar kinematic anomaly: True Sun - Mean Sun.
    """
    eng = get_calendar(engine)
    ts = np.arange(jd_start, jd_end + 1e-12, step_days, dtype=float)
    
    angles: List[float] = []

    for jd in ts:
        t2000_frac = Fraction(jd) - Fraction(2451545)
        
        if use_month:
            if not hasattr(eng, "month") or not hasattr(eng.month, "true_sun_tt"):
                return None
            true_s = float(eng.month.true_sun_tt(t2000_frac))
            mean_s = float(eng.month.mean_sun_tt(t2000_frac))
        else:
            if not hasattr(eng, "day") or not hasattr(eng.day, "true_sun_tt"):
                return None
            true_s = float(eng.day.true_sun_tt(t2000_frac))
            mean_s = float(eng.day.mean_sun_tt(t2000_frac))
        
        diff_turns = (true_s - mean_s) % 1.0
        if diff_turns > 0.5:
            diff_turns -= 1.0
            
        anom_deg = diff_turns * 360.0
        angles.append(anom_deg)
        
    if not angles:
        return None

    a_arr = np.array(angles, dtype=float)
    a_arr -= float(np.mean(a_arr))
    
    final_label = label if label else engine
    return SeriesData(final_label, ts, a_arr)


def reference_sun_series(np, jd_start: float, jd_end: float, step_days: float) -> SeriesData:
    """
    Sample analytical reference ephemeris true solar longitude (degrees), unwrap, detrend -> anomaly.
    """
    from caltib.reference.solar import solar_longitude
    
    ts = np.arange(jd_start, jd_end + 1e-12, step_days, dtype=float)
    angles: List[float] = []
    
    for jd in ts:
        s = solar_longitude(jd)
        angles.append(s.L_true_deg)

    ang = np.array(angles, dtype=float)

    # Unwrap in radians to prevent boundary jumps, then convert back
    ang_rad = np.radians(ang)
    ang_unw = np.degrees(np.unwrap(ang_rad))

    anom = detrended_anomaly(np, ts, ang_unw)
    return SeriesData("Reference", ts, anom)


def de422_sun_series(np, jd_start: float, jd_end: float, step_days: float) -> SeriesData:
    """
    Sample DE422 true solar longitude, unwrap, detrend -> anomaly.
    Requires a DE422 wrapper that provides solar longitude.
    """
    try:
        from caltib.ephemeris.de422 import DE422Sun
        sun_mod = DE422Sun.load()
        evaluator = sun_mod.sun_deg
    except ImportError:
        # Fallback if specific DE422 Sun wrapper doesn't exist yet
        raise RuntimeError("DE422Sun wrapper not found. Please use --ephem ref")

    ts = np.arange(jd_start, jd_end + 1e-12, step_days, dtype=float)
    ang = np.array([evaluator(float(t)) for t in ts], dtype=float)

    ang_rad = np.radians(ang)
    ang_unw = np.degrees(np.unwrap(ang_rad))

    anom = detrended_anomaly(np, ts, ang_unw)
    return SeriesData("DE422", ts, anom)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Forward solar kinematic anomaly vs Truth Ephemeris.")
    p.add_argument("--engines", default="phugpa,mongol,l1,l3,l4",
                   help="Comma list of reform engines to plot.")
    p.add_argument("--ephem", choices=("ref", "de422"), default="ref", help="Reference Ephemeris or DE422")
    p.add_argument("--jd-start", type=float, default=None, help="Start JD (TT-like) as float.")
    p.add_argument("--jd-end", type=float, default=None, help="End JD (TT-like) as float.")
    p.add_argument("--center-jd", type=float, default=2461072.5, help="Center JD if start/end not given.")
    p.add_argument("--window", type=float, default=200.0, help="Half-window in days if start/end not given.")
    p.add_argument("--step", type=float, default=0.25, help="Sampling step in days.")
    p.add_argument("--out", default="anomaly_sun.png", help="Output PNG filename.")
    args = p.parse_args(argv)

    np = need_numpy()
    plt = need_matplotlib()

    if (args.jd_start is None) != (args.jd_end is None):
        raise SystemExit("Provide both --jd-start and --jd-end, or neither (then center/window is used).")

    if args.jd_start is None:
        jd_start = float(args.center_jd) - float(args.window)
        jd_end = float(args.center_jd) + float(args.window)
    else:
        jd_start = float(args.jd_start)
        jd_end = float(args.jd_end)

    if jd_end <= jd_start:
        raise SystemExit("--jd-end must be > --jd-start")

    engines = parse_engine_list(args.engines)

    print(f"Interval JD: [{jd_start:.3f}, {jd_end:.3f}]  (span {jd_end - jd_start:.1f} days)")
    print(f"Evaluating solar anomaly vs {args.ephem.upper()}...")
    print(f"Engines: {engines}")

    series: List[SeriesData] = []

    # Forward proxy series for requested engines
    for eng_str in engines:
        is_month = False
        base_eng = eng_str
        label = eng_str
        
        # Parse the custom suffix!
        if eng_str.endswith("-m"):
            base_eng = eng_str[:-2]
            is_month = True
            label = f"{base_eng} (Month)"
            
        try:
            s = sun_anomaly_series(np, base_eng, jd_start, jd_end, float(args.step), use_month=is_month, label=label)
            if s is None:
                print(f"  {eng_str}: no samples in interval or missing component")
            else:
                print(f"  {eng_str}: {len(s.times)} samples")
                series.append(s)
        except Exception as e:
            print(f"  {eng_str}: ERROR: {e}")

    # Truth Ephemeris Series
    if args.ephem == "de422":
        try:
            s_truth = de422_sun_series(np, jd_start, jd_end, step_days=float(args.step))
            print(f"  DE422: {len(s_truth.times)} samples (step={args.step}d)")
            series.append(s_truth)
        except Exception as e:
            print(f"  DE422 ERROR: {e}")
    else:
        try:
            s_truth = reference_sun_series(np, jd_start, jd_end, step_days=float(args.step))
            print(f"  Reference: {len(s_truth.times)} samples (step={args.step}d)")
            series.append(s_truth)
        except Exception as e:
            print(f"  Reference ERROR: {e}")

    # Plot
    center = 0.5 * (jd_start + jd_end)
    colors: Dict[str, str] = {
        "phugpa": "tab:orange", "tsurphu": "tab:green", "mongol": "tab:purple",
        "bhutan": "tab:red", "karana": "tab:brown", 
        "l0": "tab:brown", "l1": "tab:pink", "l2": "tab:cyan", 
        "l3": "tab:olive", "l4": "gold",
        "Reference": "black", "DE422": "black",
    }

    plt.figure(figsize=(12, 5))

    for s in series:
        x_rel = s.times - center
        
        # Strip " (Month)" to find the correct base color in the dictionary
        base_name = s.label.replace(" (Month)", "")
        c = colors.get(base_name, "tab:blue")
        
        if s.label in ("Reference", "DE422"):
            label_name = "Reference (ELP2000)" if s.label == "Reference" else "DE422 Ephemeris"
            plt.plot(x_rel, s.anomaly_deg, linestyle="--", color=c, linewidth=1.5, alpha=0.9, label=label_name)
        else:
            # Dotted line for Month engines, solid line for Day engines
            l_style = ":" if " (Month)" in s.label else "-"
            l_width = 2.0 if " (Month)" in s.label else 1.2
            
            plt.plot(x_rel, s.anomaly_deg, linestyle=l_style, color=c, linewidth=l_width, alpha=0.8, label=s.label)

    plt.title(f"Solar Equation of Center (True Sun - Mean Sun)\nContinuous Physical Time vs {args.ephem.upper()} Ephemeris")
    plt.xlabel("Days relative to interval center")
    plt.ylabel("Anomaly (degrees)")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(args.out, dpi=180)
    print(f"Saved: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())