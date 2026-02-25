#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import caltib
from caltib.ephemeris.de422 import DE422Elongation


def need_numpy():
    try:
        import numpy as np
        return np
    except ImportError as e:
        raise RuntimeError('Need numpy. Install: pip install "caltib[diagnostics]"') from e


def need_matplotlib():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError as e:
        raise RuntimeError('Need matplotlib. Install: pip install "caltib[diagnostics]"') from e


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
    Sample Tibetan "cumulative elongation" angle_cum = 12*(30*n + d) at true_date(d,n),
    then detrend angle_cum vs time to get an anomaly-like curve.
    """
    # diagnostic-only access to raw true_date(d,n)
    from caltib import api as _api
    eng = _api._reg().get(engine)

    # Seed lunation index n from mean motion
    p = eng.day.p
    m0 = float(p.m0)
    m1 = float(p.m1)

    center = 0.5 * (jd_start + jd_end)
    n_mid = int((center - m0) // m1)

    # How many lunations to cover the interval (+ margin)
    span = jd_end - jd_start
    n_span = int(span / m1) + 8
    n_lo = n_mid - n_span
    n_hi = n_mid + n_span

    times: List[float] = []
    angles: List[float] = []

    for n in range(n_lo, n_hi + 1):
        for d in range(1, 31):  # 1..30 boundaries
            t = float(eng.day.true_date(d, n))  # Fraction -> float JD-like
            if jd_start <= t <= jd_end:
                # cumulative "true elongation" proxy, monotone by construction
                ang = 12.0 * (30.0 * n + float(d))
                times.append(t)
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


def de422_anomaly_series(np, jd_start: float, jd_end: float, step_days: float) -> SeriesData:
    """
    Sample DE422 elongation (degrees), unwrap, detrend -> anomaly.
    """
    el = DE422Elongation.load()

    ts = np.arange(jd_start, jd_end + 1e-12, step_days, dtype=float)
    ang = np.array([el.elong_deg(float(t)) for t in ts], dtype=float)

    # unwrap in radians then convert back
    ang_rad = np.radians(ang)
    ang_unw = np.degrees(np.unwrap(ang_rad))

    anom = detrended_anomaly(np, ts, ang_unw)
    return SeriesData("DE422", ts, anom)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Angular anomaly (equation-of-center style) vs DE422.")
    p.add_argument("--engines", default="phugpa,tsurphu,mongol,bhutan",
                   help="Comma list of traditions to plot.")
    p.add_argument("--jd-start", type=float, default=None, help="Start JD (TT-like) as float.")
    p.add_argument("--jd-end", type=float, default=None, help="End JD (TT-like) as float.")
    p.add_argument("--center-jd", type=float, default=2461072.5, help="Center JD if start/end not given.")
    p.add_argument("--window", type=float, default=150.0, help="Half-window in days if start/end not given.")
    p.add_argument("--step", type=float, default=0.25, help="DE422 sampling step in days.")
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
    print(f"Engines: {engines}")

    series: List[SeriesData] = []

    # Tibetan proxy series
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

    # DE422 series
    s_de = de422_anomaly_series(np, jd_start, jd_end, step_days=float(args.step))
    print(f"  DE422: {len(s_de.times)} samples (step={args.step}d)")
    series.append(s_de)

    # Plot
    center = 0.5 * (jd_start + jd_end)
    colors: Dict[str, str] = {
        "phugpa": "tab:blue",
        "tsurphu": "tab:green",
        "mongol": "tab:purple",
        "bhutan": "tab:orange",
        "karana": "tab:red",
        "DE422": "black",
    }

    plt.figure(figsize=(12, 5))

    for s in series:
        x_rel = s.times - center
        c = colors.get(s.label, "gray")
        if s.label == "DE422":
            plt.plot(x_rel, s.anomaly_deg, linestyle="--", color=c, linewidth=1.2, alpha=0.9, label=s.label)
        else:
            plt.plot(x_rel, s.anomaly_deg, linestyle="-", color=c, linewidth=1.3, alpha=0.75, label=s.label)

    plt.title("Angular anomaly: (elongation proxy) − (mean elongation)\nDE422 vs traditional month/tithi boundary sampling")
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