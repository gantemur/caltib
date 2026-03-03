#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

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
    times: "np.ndarray"      # JD (float)
    anomaly_deg: "np.ndarray"  # degrees (detrended)


def detrended_anomaly(np, times: "np.ndarray", angles_deg: "np.ndarray") -> "np.ndarray":
    """
    Given monotone (or unwrapped) angles_deg vs times, subtract best linear fit and mean.
    """
    coeffs = np.polyfit(times, angles_deg, 1)
    mean_line = np.polyval(coeffs, times)
    anom = angles_deg - mean_line
    anom = anom - float(np.mean(anom))
    return anom


def tib_anomaly_series(np, engine: str, jd_start: float, jd_end: float) -> Optional[SeriesData]:
    """
    Universal anomaly sampler. Evaluates the absolute tithi index (x) 
    using the standardized Day Engine pure astronomical boundaries.
    """
    from caltib.api import get_calendar
    eng = get_calendar(engine)

    # Convert JD to the internal t2000 coordinate
    t2000_start = jd_start - 2451545.0
    t2000_end = jd_end - 2451545.0

    # Get absolute continuous bounds in O(1) time
    x_lo = eng.day.get_x_from_t2000(t2000_start) - 2
    x_hi = eng.day.get_x_from_t2000(t2000_end) + 2

    times: List[float] = []
    angles: List[float] = []

    for x in range(x_lo, x_hi + 1):
        # Pure astronomical true date, bypassing all civil dawn and location adjustments!
        t_val = float(eng.day.true_date(x))
        jd_val = t_val + 2451545.0
        
        if jd_start <= jd_val <= jd_end:
            # 1 absolute tithi = exactly 12 degrees of elongation
            ang = float(x) * 12.0
            times.append(jd_val)
            angles.append(ang)

    if not times:
        return None

    t_arr = np.array(times, dtype=float)
    a_arr = np.array(angles, dtype=float)

    idx = np.argsort(t_arr)
    t_arr = t_arr[idx]
    a_arr = a_arr[idx]

    anom = detrended_anomaly(np, t_arr, a_arr)
    return SeriesData(engine, t_arr, anom)


def reference_anomaly_series(np, jd_start: float, jd_end: float, step_days: float) -> SeriesData:
    """
    Sample analytical reference ephemeris true elongation (degrees), unwrap, detrend -> anomaly.
    Replaces DE422 for self-contained execution without heavy ephemeris files.
    """
    from caltib.reference.solar import solar_longitude
    from caltib.reference.lunar import lunar_position
    
    ts = np.arange(jd_start, jd_end + 1e-12, step_days, dtype=float)
    angles: List[float] = []
    
    for jd in ts:
        # Evaluate true solar and lunar longitude at JD(TT)
        s = solar_longitude(jd)
        m = lunar_position(jd)
        
        # True elongation wrapped to [0, 360)
        elong_deg = (m.L_true_deg - s.L_true_deg) % 360.0
        angles.append(elong_deg)

    ang = np.array(angles, dtype=float)

    # Unwrap in radians to prevent boundary jumps, then convert back
    ang_rad = np.radians(ang)
    ang_unw = np.degrees(np.unwrap(ang_rad))

    anom = detrended_anomaly(np, ts, ang_unw)
    return SeriesData("Reference", ts, anom)


def de422_anomaly_series(np, jd_start: float, jd_end: float, step_days: float) -> SeriesData:
    """
    Sample DE422 elongation (degrees), unwrap, detrend -> anomaly.
    """
    from caltib.ephemeris.de422 import DE422Elongation
    el = DE422Elongation.load()

    ts = np.arange(jd_start, jd_end + 1e-12, step_days, dtype=float)
    ang = np.array([el.elong_deg(float(t)) for t in ts], dtype=float)

    # unwrap in radians then convert back
    ang_rad = np.radians(ang)
    ang_unw = np.degrees(np.unwrap(ang_rad))

    anom = detrended_anomaly(np, ts, ang_unw)
    return SeriesData("DE422", ts, anom)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Angular anomaly (equation-of-center style) vs Truth Ephemeris.")
    p.add_argument("--engines", default="mongol,l1,l2,l3,l4",
                   help="Comma list of traditions/reforms to plot.")
    p.add_argument("--ephem", choices=("ref", "de422"), default="ref", help="Reference Ephemeris or DE422")
    p.add_argument("--jd-start", type=float, default=None, help="Start JD (TT-like) as float.")
    p.add_argument("--jd-end", type=float, default=None, help="End JD (TT-like) as float.")
    p.add_argument("--center-jd", type=float, default=2461072.5, help="Center JD if start/end not given.")
    p.add_argument("--window", type=float, default=200.0, help="Half-window in days if start/end not given.")
    p.add_argument("--step", type=float, default=0.25, help="Sampling step in days.")
    p.add_argument("--out", default="anomaly_angular.png", help="Output PNG filename.")
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
    print(f"Evaluating engines vs {args.ephem.upper()}...")
    print(f"Engines: {engines}")

    series: List[SeriesData] = []

    # Universal engine proxy series
    for eng in engines:
        try:
            s = tib_anomaly_series(np, eng, jd_start, jd_end)
            if s is None:
                print(f"  {eng}: no samples in interval")
            else:
                print(f"  {eng}: {len(s.times)} samples")
                series.append(s)
        except Exception as e:
            print(f"  {eng}: ERROR: {e}")

    # Truth Ephemeris Series
    if args.ephem == "de422":
        try:
            s_truth = de422_anomaly_series(np, jd_start, jd_end, step_days=float(args.step))
            print(f"  DE422: {len(s_truth.times)} samples (step={args.step}d)")
            series.append(s_truth)
        except Exception as e:
            print(f"  DE422 ERROR (Check ephemeris files): {e}")
    else:
        try:
            s_truth = reference_anomaly_series(np, jd_start, jd_end, step_days=float(args.step))
            print(f"  Reference: {len(s_truth.times)} samples (step={args.step}d)")
            series.append(s_truth)
        except Exception as e:
            print(f"  Reference ERROR: {e}")

    # Plot
    center = 0.5 * (jd_start + jd_end)
    
    # Extended color palette to accommodate the reform engines
    colors: Dict[str, str] = {
        "phugpa": "tab:blue",
        "tsurphu": "tab:green",
        "mongol": "tab:purple",
        "bhutan": "tab:orange",
        "karana": "tab:red",
        "l0": "tab:brown",
        "l1": "tab:pink",
        "l2": "tab:cyan",
        "l3": "tab:olive",
        "l4": "gold",
        "Reference": "black",
        "DE422": "black",
    }

    plt.figure(figsize=(12, 5))

    for s in series:
        x_rel = s.times - center
        c = colors.get(s.label, "gray")
        if s.label in ("Reference", "DE422"):
            label_name = "Reference (ELP2000)" if s.label == "Reference" else "DE422 Ephemeris"
            plt.plot(x_rel, s.anomaly_deg, linestyle="--", color=c, linewidth=1.2, alpha=0.9, label=label_name)
        else:
            plt.plot(x_rel, s.anomaly_deg, linestyle="-", color=c, linewidth=1.3, alpha=0.75, label=s.label)

    plt.title(f"Universal Angular Anomaly: (Elongation Proxy) − (Mean Elongation)\n{args.ephem.upper()} Ephemeris vs caltib Unified Architecture")
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