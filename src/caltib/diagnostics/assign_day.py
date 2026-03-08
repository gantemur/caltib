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
    p = argparse.ArgumentParser(description="Civil Day vs Lunar Day Assignment Diagram.")
    p.add_argument("--engine", default="phugpa", help="Engine to plot (e.g., l4, phugpa).")
    p.add_argument("--year", type=int, default=2026, help="Target lunar year.")
    p.add_argument("--month", type=int, default=1, help="Target lunar month (1-12).")
    p.add_argument("--focus-day", type=int, default=None, help="Zoom in on a specific lunar day (1-30).")
    p.add_argument("--buffer", type=int, default=1, help="Extra lunar days to pad on each side.")
    p.add_argument("--out", default="assign_day.png", help="Output PNG filename.")
    args = p.parse_args(argv)

    np = need_numpy()
    plt, mdates = need_matplotlib()

    base_engine = args.engine
    if base_engine.endswith("-m"):
        base_engine = base_engine[:-2]

    eng = get_calendar(base_engine)
    if not hasattr(eng, "day"):
        raise SystemExit(f"Engine '{base_engine}' does not have a day engine component.")

    title_scope = f"Year {args.year}, M{args.month}"
    if args.focus_day:
        title_scope += f", LD{args.focus_day}"
    print(f"Generating Lunar Day Diagram for {base_engine.upper()} ({title_scope})...")

    # 1. Determine absolute bounds
    try:
        target_lunations = eng.month.get_lunations(args.year, args.month)
        n = target_lunations[0]
    except Exception as e:
        raise SystemExit(f"Could not find Month {args.month} for year {args.year}: {e}")

    # Standard convention: x = 30n + d
    is_zoomed = args.focus_day is not None
    if is_zoomed:
        x_start = n * 30 + args.focus_day
        x_end = n * 30 + args.focus_day
    else:
        x_start = n * 30 + 1
        x_end = n * 30 + 30
        
    x_lo = x_start - args.buffer
    x_hi = x_end + args.buffer

    # 2. Map Civil Grid & Assure Complete Tithi Coverage
    J_start = eng.day.civil_jdn(x_lo)
    J_end = eng.day.civil_jdn(x_hi)
    
    civil_bounds = list(range(J_start, J_end + 2))
    
    jdn_to_x = {J: [] for J in range(J_start, J_end + 1)}
    for x in range(x_lo - 15, x_hi + 16):
        J = eng.day.civil_jdn(x)
        if J in jdn_to_x:
            jdn_to_x[J].append(x)

    integer_x_vals = list(range(x_lo, x_hi + 1))

    # Helper function to find the Tithi active at dawn (Dawn Inheritance Rule)
    def get_inherited_name(jdn: int) -> int:
        if jdn in jdn_to_x and len(jdn_to_x[jdn]) > 0:
            return sorted(jdn_to_x[jdn])[0]
        # If 0 endings, the active tithi is the one that ends on the NEXT day
        curr = jdn + 1
        while curr <= max(jdn_to_x.keys()) + 15:
            ends = sorted([x for x in range(x_lo - 15, x_hi + 16) if eng.day.civil_jdn(x) == curr])
            if ends:
                return ends[0]
            curr += 1
        return x_lo 

    # 3. Generate Continuous Elongation Curve
    t_jd = []
    y_val = []
    for x_fl in np.linspace(x_lo - 1, x_hi, max(500, (x_hi - x_lo + 1) * 50)):
        t_tt = float(eng.day.true_date(Fraction(float(x_fl))))
        t_jd.append(t_tt + 2451545.0)
        y_val.append(float(x_fl) - (n * 30))

    # 4. Build the Plot
    fig, ax = plt.subplots(figsize=(14, 6))
    dt_curve = [jd_to_datetime(t) for t in t_jd]
    dt_bounds = [jd_to_datetime(float(J)) for J in civil_bounds]

    # Plot continuous true elongation (thinned)
    ax.plot(dt_curve, y_val, color="#ff7f0e", linewidth=1.0, label="True Elongation (Continuous Phase)")

    # Draw Horizontal Boundaries
    y_lines = [float(x - (n * 30)) for x in integer_x_vals]
    for y in y_lines:
        ax.axhline(y, color="#888888", linestyle="-", linewidth=0.5, alpha=0.3)

    trans = ax.get_xaxis_transform()
    added_skip_legend = False
    added_dup_legend = False

    x_ticks = []
    x_labels = []

    # 5. Draw Vertical Civil Days, Conditionally Shade Anomalies, and Assign Inherited Labels
    for i in range(len(dt_bounds) - 1):
        J = civil_bounds[i]
        
        ax.axvline(dt_bounds[i], color="#1f77b4", linestyle="--", linewidth=0.8, alpha=0.6)
        
        mid_time = dt_bounds[i] + (dt_bounds[i+1] - dt_bounds[i]) / 2
        x_ticks.append(mid_time)
        
        date_str = dt_bounds[i].strftime('%b-%d')
        if is_zoomed:
            x_labels.append(date_str)
        else:
            x_labels.append(date_str if i % 2 == 0 else "")

        assigned_x = sorted(jdn_to_x.get(J, []))
        
        # Shade based on crossings with mathematically precise labels
        if len(assigned_x) == 0:
            lbl = "0 Lunar Boundaries (Triggers Duplicated Name / Lhag)" if not added_dup_legend else ""
            ax.axvspan(dt_bounds[i], dt_bounds[i+1], color="#ffd700", alpha=0.15, label=lbl)
            added_dup_legend = True
        elif len(assigned_x) == 2:
            lbl = "2 Lunar Boundaries (Triggers Skipped Name / Chad)" if not added_skip_legend else ""
            ax.axvspan(dt_bounds[i], dt_bounds[i+1], color="#ff9999", alpha=0.20, label=lbl)
            added_skip_legend = True

        # STRICT DAWN INHERITANCE: The Civil Day gets the name of the tithi active at Dawn
        inherited_x = get_inherited_name(J)
        d_name = (inherited_x - 1) % 30 + 1
        lbl_text = f"D{d_name}"

        ax.text(mid_time, 0.98, lbl_text, transform=trans, ha='center', va='top', 
                fontsize=10, color="#333333")

    # Final right border fence
    ax.axvline(dt_bounds[-1], color="#1f77b4", linestyle="--", linewidth=0.8, alpha=0.6)

    # 6. Format Y-Axis (Intervals)
    y_ticks = [y - 0.5 for y in y_lines]
    if is_zoomed:
        y_labels = [f"Lunar Day {int((x - 1) % 30) + 1}" for x in integer_x_vals]
    else:
        y_labels = [f"Lunar Day {int((x - 1) % 30) + 1}" if i % 2 == 0 else "" for i, x in enumerate(integer_x_vals)]
    
    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels, color="#555555", fontsize=9)
    ax.tick_params(axis='y', length=0)
    ax.set_ylim(y_lines[0] - 1.0, y_lines[-1] + 0.1)

    # 7. Format X-Axis (Intervals)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(x_labels, color="#555555", fontsize=9)
    ax.tick_params(axis='x', length=0)

    plt.title(f"Lunar Day vs Civil Day Assignment: {base_engine.upper()} ({title_scope})\nVertical: Civil Days (Dawn/Midnight)  |  Horizontal: True Lunar Day Boundaries (12° Elongation)", pad=20)
    plt.ylabel("Lunar Phase (Relative)", color="#444444")
    
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