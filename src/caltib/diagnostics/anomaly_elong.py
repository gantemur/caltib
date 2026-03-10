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

def parse_engine_list(s: str) -> List[str]:
    return [x.strip() for x in s.split(",") if x.strip()]

def jd_to_datetime(jd: float) -> datetime.datetime:
    """Rough conversion from JD to Gregorian datetime for plotting."""
    return datetime.datetime(2000, 1, 1, 12, 0, 0) + datetime.timedelta(days=(jd - 2451545.0))

@dataclass(frozen=True)
class SeriesData:
    label: str
    times: "np.ndarray"  # Julian Dates
    anomaly_deg: "np.ndarray"

def elong_anomaly_series(np, engine: str, jd_start: float, jd_end: float, step_x: float, use_month: bool = False, label: str = "") -> Optional[SeriesData]:
    eng = get_calendar(engine)
    comp = eng.month if use_month else eng.day
    
    if not hasattr(comp, "true_date") or not hasattr(comp, "mean_date"):
        return None

    # Dynamically find the engine's absolute tithi epoch (t2000 offset for x=0)
    epoch_offset_t2000 = float(comp.mean_date(Fraction(0)))
    
    t2000_start = jd_start - 2451545.0
    t2000_end = jd_end - 2451545.0
    mean_tithi_len = 29.530588853 / 30.0
    
    # Calculate bounds relative to the engine's true epoch
    x_start = int((t2000_start - epoch_offset_t2000) / mean_tithi_len) - 2
    x_end = int((t2000_end - epoch_offset_t2000) / mean_tithi_len) + 2
    x_grid = np.arange(x_start, x_end, step_x)
    
    jd_times: List[float] = []
    anomalies: List[float] = []
    
    mean_rate_deg_per_day = 360.0 / 29.530588853

    for x in x_grid:
        frac_x = Fraction(float(x))
        
        t_true = float(comp.true_date(frac_x))
        t_mean = float(comp.mean_date(frac_x))
        
        jd_times.append(t_true + 2451545.0)
        
        # True Elongation minus Mean Elongation
        anomaly_deg = - (t_true - t_mean) * mean_rate_deg_per_day
        anomalies.append(anomaly_deg)

    # Filter strictly to the requested JD window
    filtered_times = []
    filtered_anomalies = []
    for jd, anom in zip(jd_times, anomalies):
        if jd_start <= jd <= jd_end:
            filtered_times.append(jd)
            filtered_anomalies.append(anom)

    if not filtered_times:
        return None

    # Removed dynamic np.mean() subtraction to preserve absolute drift values
    e_arr = np.array(filtered_anomalies, dtype=float)
    
    final_label = label if label else engine
    return SeriesData(final_label, np.array(filtered_times), e_arr)


def ref_elong_anomaly_series(np, jd_start: float, jd_end: float, step_days: float, ephem_evaluator=None) -> SeriesData:
    from caltib.reference.lunar import lunar_position
    from caltib.reference.solar import solar_longitude
    from caltib.reference.astro_args import fundamental_args, T_centuries
    
    ts = np.arange(jd_start, jd_end + 1e-12, step_days, dtype=float)
    anomalies: List[float] = []

    for jd in ts:
        if ephem_evaluator:
            # Use your custom DE422 loader directly!
            true_elong = ephem_evaluator.elong_deg(float(jd))
        else:
            moon = lunar_position(jd).L_true_deg
            sun = solar_longitude(jd).L_true_deg
            true_elong = (moon - sun) % 360.0
            
        T = T_centuries(jd)
        mean_elong = fundamental_args(T).D_deg
        
        diff = (true_elong - mean_elong) % 360.0
        if diff > 180.0: diff -= 360.0
        anomalies.append(diff)
        
    e_arr = np.array(anomalies, dtype=float)
    label = "DE422 Ephemeris" if ephem_evaluator else "Reference (ELP2000)"
    return SeriesData(label, ts, e_arr)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Absolute Angular Anomaly via Time Inversion.")
    p.add_argument("--engines", default="phugpa,mongol,l1,l3,l4", help="Comma list of reform engines.")
    p.add_argument("--ephem", choices=["ref", "de422"], default="ref", help="Reference ephemeris (ref=ELP2000, de422=JPL DE422).")
    
    p.add_argument("--date-start", type=str, default=None, help="Start date (YYYY-MM-DD) or (YYYY.MM.DD)")
    p.add_argument("--date-end", type=str, default=None, help="End date (YYYY-MM-DD) or (YYYY.MM.DD)")
    p.add_argument("--jd-start", type=float, default=None, help="Start JD as float.")
    p.add_argument("--jd-end", type=float, default=None, help="End JD as float.")
    p.add_argument("--center-jd", type=float, default=2461072.5, help="Center JD if start/end not given.")
    p.add_argument("--window", type=float, default=200.0, help="Half-window in days if start/end not given.")
    p.add_argument("--step", type=float, default=0.25, help="Sampling step (in continuous tithi).")
    p.add_argument("--out", default="anomaly_elong.png", help="Output PNG filename.")
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

    ephem_evaluator = None
    if args.ephem == "de422":
        try:
            from caltib.ephemeris.de422 import DE422Elongation
            ephem_evaluator = DE422Elongation.load()
        except Exception as e:
            raise SystemExit(f"\n[!] Failed to load DE422 Ephemeris: {e}\nDid you download the ephemeris files?")

    engines = parse_engine_list(args.engines)

    print(f"Evaluating inverted elongation anomaly for {engines} against {args.ephem.upper()}...")

    series: List[SeriesData] = []
    
    ref_s = ref_elong_anomaly_series(np, jd_start, jd_end, float(args.step), ephem_evaluator=ephem_evaluator)
    series.append(ref_s)
    print(f"  Reference ({args.ephem.upper()}): {len(ref_s.times)} samples")

    for eng_str in engines:
        is_month = False
        base_eng = eng_str
        label = eng_str
        if eng_str.endswith("-m"):
            base_eng = eng_str[:-2]
            is_month = True
            label = f"{base_eng} (Month)"
            
        try:
            s = elong_anomaly_series(np, base_eng, jd_start, jd_end, float(args.step), use_month=is_month, label=label)
            if s:
                print(f"  {eng_str}: {len(s.times)} samples")
                series.append(s)
            else:
                print(f"  {eng_str}: No data fell in window.")
        except Exception as e:
            print(f"  {eng_str}: ERROR: {e}")

    colors: Dict[str, str] = {
        "phugpa": "tab:orange", "tsurphu": "tab:green", "mongol": "tab:purple",
        "l1": "tab:pink", "l2": "tab:cyan", "l3": "tab:olive", "l4": "gold"
    }

    fig, ax = plt.subplots(figsize=(12, 5))

    for s in series:
        x_dates = [jd_to_datetime(jd) for jd in s.times]
        
        if s.label in ("Reference (ELP2000)", "DE422 Ephemeris"):
            ax.plot(x_dates, s.anomaly_deg, color="black", linestyle="--", linewidth=1.5, alpha=0.9, label=s.label)
            continue
            
        base_name = s.label.replace(" (Month)", "")
        c = colors.get(base_name, "tab:blue")
        l_style = ":" if " (Month)" in s.label else "-"
        
        ax.plot(x_dates, s.anomaly_deg, linestyle=l_style, color=c, linewidth=1.2, alpha=0.8, label=s.label)

    locator = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    ephem_str = "DE422" if args.ephem == "de422" else "ELP2000"
    plt.title(f"Absolute Angular Anomaly via Engine Inversion\n{ephem_str} Ephemeris vs caltib Unified Architecture")
    plt.xlabel("Gregorian Date (TT)")
    plt.ylabel("Anomaly (degrees)")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(args.out, dpi=180)
    print(f"Saved: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())