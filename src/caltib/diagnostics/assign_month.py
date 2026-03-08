#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from fractions import Fraction
from typing import List, Optional

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


def jd_to_datetime(jd: float) -> datetime:
    """Rough conversion from JD to Gregorian datetime for plotting."""
    return datetime(2000, 1, 1, 12, 0, 0) + timedelta(days=(jd - 2451545.0))


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Lunisolar Month Assignment & Sgang Transit Diagram.")
    p.add_argument("--engine", default="l4", help="Engine to plot (e.g., l4, phugpa, l4-m).")
    p.add_argument("--year", type=int, default=2026, help="Target lunar year.")
    p.add_argument("--focus-month", type=int, default=None, help="Zoom in on a specific month (1-12).")
    p.add_argument("--buffer", type=int, default=1, help="Extra months to pad on each side.")
    p.add_argument("--out", default="assign_month.png", help="Output PNG filename.")
    args = p.parse_args(argv)

    np = need_numpy()
    plt, mdates = need_matplotlib()

    base_engine = args.engine
    if base_engine.endswith("-m"):
        base_engine = base_engine[:-2]

    eng = get_calendar(base_engine)
    if not hasattr(eng, "month"):
        raise SystemExit(f"Engine '{base_engine}' does not have a month engine component.")

    # 1. Determine absolute lunation bounds based on zoom level
    if args.focus_month is not None:
        print(f"Generating Zoomed Transit Diagram for {base_engine.upper()} Year {args.year}, Month {args.focus_month}...")
        try:
            target_lunations = eng.month.get_lunations(args.year, args.focus_month)
            n_lo = target_lunations[0] - args.buffer
            n_hi = target_lunations[-1] + args.buffer + 1
        except Exception as e:
            raise SystemExit(f"Could not find Month {args.focus_month} for year {args.year}: {e}")
    else:
        print(f"Generating Full-Year Transit Diagram for {base_engine.upper()} Year {args.year}...")
        try:
            n_start_year = eng.month.first_lunation(args.year)
            n_end_year = eng.month.first_lunation(args.year + 1)
            n_lo = n_start_year - args.buffer
            n_hi = n_end_year + args.buffer
        except Exception as e:
            raise SystemExit(f"Could not find lunations for year {args.year}: {e}")

    # 2. Gather New Moon times and Civil Labels
    new_moons_jd = []
    labels = []
    for n in range(n_lo, n_hi + 1):
        t_tt = float(eng.month.true_date(n))
        jd = t_tt + 2451545.0
        new_moons_jd.append(jd)
        info = eng.month.get_month_info(n)
        labels.append(info)

    # 3. Generate Continuous Solar Longitude Curve
    t_start = new_moons_jd[0] - 2451545.0
    t_end = new_moons_jd[-1] - 2451545.0
    t_grid = np.linspace(t_start, t_end, 500)
    
    sun_turns = np.array([float(eng.month.true_sun_tt(Fraction(float(t)))) for t in t_grid])
    sun_unwrapped_turns = np.unwrap(sun_turns * 2 * np.pi) / (2 * np.pi)
    sun_deg_unwrapped = sun_unwrapped_turns * 360.0

    # 4. Determine Exact Horizontal Sgang Boundaries & Their Numbers
    sgang_base_deg = float(eng.sgang_base) * 360.0
    min_deg = sun_deg_unwrapped.min()
    max_deg = sun_deg_unwrapped.max()
    
    k_start = np.floor((min_deg - sgang_base_deg) / 30.0)
    k_end = np.ceil((max_deg - sgang_base_deg) / 30.0)
    
    ks = np.arange(k_start, k_end + 1)
    sgang_lines = sgang_base_deg + ks * 30.0

    # 5. Build the Plot
    fig, ax = plt.subplots(figsize=(12, 6))
    dt_grid = [jd_to_datetime(t + 2451545.0) for t in t_grid]
    dt_moons = [jd_to_datetime(jd) for jd in new_moons_jd]

    ax.plot(dt_grid, sun_deg_unwrapped, color="#ff7f0e", linewidth=1.8, label="True Solar Longitude")

    for deg in sgang_lines:
        ax.axhline(deg, color="#888888", linestyle="-", linewidth=0.5, alpha=0.3)

    trans = ax.get_xaxis_transform()
    added_leap_legend = False
    added_skip_legend = False

    # 6. Draw Moons, Count Transits, and Shade Backgrounds
    for i in range(len(dt_moons)):
        ax.axvline(dt_moons[i], color="#1f77b4", linestyle="--", linewidth=0.8, alpha=0.6)
        
        if i < len(dt_moons) - 1:
            info = labels[i]
            mid_time = dt_moons[i] + (dt_moons[i+1] - dt_moons[i]) / 2
            
            # Count physical sgang crossings in this interval
            y_start = np.interp(t_grid[0] + (dt_moons[i] - dt_grid[0]).total_seconds()/86400, t_grid, sun_deg_unwrapped)
            y_end = np.interp(t_grid[0] + (dt_moons[i+1] - dt_grid[0]).total_seconds()/86400, t_grid, sun_deg_unwrapped)
            crossings = len([y for y in sgang_lines if y_start <= y < y_end])
            
            # Shade based on crossings
            if crossings == 0:
                lbl = "Astronomical Leap (0 Transits)" if not added_leap_legend else ""
                ax.axvspan(dt_moons[i], dt_moons[i+1], color="#ffd700", alpha=0.15, label=lbl)
                added_leap_legend = True
            elif crossings == 2:
                lbl = "Astronomical Skip (2 Transits)" if not added_skip_legend else ""
                ax.axvspan(dt_moons[i], dt_moons[i+1], color="#ff9999", alpha=0.20, label=lbl)
                added_skip_legend = True

            # Engine Civil Label (Cleaned up, no "(Leap)" text)
            lbl_text = f"M{info['month']}"
            ax.text(mid_time, 0.98, lbl_text, transform=trans, ha='center', va='top', 
                    fontsize=11, color="#333333", fontweight="bold")

    # Format Left Y-Axis (Degrees)
    ax.set_yticks(sgang_lines)
    ax.set_yticklabels([f"{int(d % 360)}°" for d in sgang_lines], color="#555555", fontsize=9)
    ax.set_ylabel("Solar Longitude (Degrees)", color="#444444")

    # Format Right Y-Axis (Sgang Numbers)
    secax = ax.secondary_yaxis('right')
    secax.set_yticks(sgang_lines)
    secax.set_yticklabels([f"Sgang {int(k % 12) + 1}" for k in ks], color="#1f77b4", fontsize=9, fontweight="bold")
    secax.spines['right'].set_visible(False)
    secax.tick_params(right=False)

    # Format X-Axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%b-%d'))
    plt.xticks(rotation=0, ha='center', color="#555555", fontsize=9)

    title_scope = f"Month {args.focus_month}" if args.focus_month else f"Year {args.year}"
    plt.title(f"Lunisolar Intercalation Grid: {base_engine.upper()} ({title_scope})\nVertical: New Moons  |  Horizontal: Sgang Transits", pad=20)
    
    handles, legends = ax.get_legend_handles_labels()
    by_label = dict(zip(legends, handles))
    ax.legend(by_label.values(), by_label.keys(), loc="lower right", framealpha=0.9, edgecolor="#cccccc")

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cccccc')
    ax.spines['bottom'].set_color('#cccccc')

    plt.tight_layout()
    plt.savefig(args.out, dpi=200)
    print(f"Saved diagram to: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())