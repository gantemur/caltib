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
    
    # Standard input
    p.add_argument("--year", type=int, default=2026, help="Target lunar year.")
    p.add_argument("--month", type=int, default=1, help="Target lunar month (1-12).")
    p.add_argument("--focus-day", type=int, default=None, help="Zoom in on a specific lunar day (1-30).")
    
    # Date window input
    p.add_argument("--date-start", type=str, default=None, help="Start date (YYYY-MM-DD) or (YYYY.MM.DD)")
    p.add_argument("--date-end", type=str, default=None, help="End date (YYYY-MM-DD) or (YYYY.MM.DD)")
    
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

    # 1. Determine absolute bounds (Civil JDN and Rough Tithi coverage)
    if args.date_start and args.date_end:
        ds_clean = args.date_start.replace(".", "-").replace("/", "-")
        de_clean = args.date_end.replace(".", "-").replace("/", "-")
        dt_start = datetime.strptime(ds_clean, "%Y-%m-%d")
        dt_end = datetime.strptime(de_clean, "%Y-%m-%d")
        
        # JDN for civil dates (1721425 is JDN of 0001-01-01)
        J_start_target = dt_start.toordinal() + 1721425
        J_end_target = dt_end.toordinal() + 1721425
        
        J_start = J_start_target - args.buffer
        J_end = J_end_target + args.buffer
        
        # Approximate the Tithi bounds to make sure we cast a wide enough net
        epoch_offset_t2000 = float(eng.day.mean_date(Fraction(0)))
        mean_tithi_len = 29.530588853 / 30.0
        
        x_start_approx = int((J_start - 0.5 - 2451545.0 - epoch_offset_t2000) / mean_tithi_len)
        x_end_approx   = int((J_end - 0.5 - 2451545.0 - epoch_offset_t2000) / mean_tithi_len)
        
        x_lo = x_start_approx - 5
        x_hi = x_end_approx + 5
        
        n = x_lo // 30  # Align Y-axis visually to the local month
        title_scope = f"{ds_clean} to {de_clean}"
    else:
        try:
            target_lunations = eng.month.get_lunations(args.year, args.month)
            n = target_lunations[0]
        except Exception as e:
            raise SystemExit(f"Could not find Month {args.month} for year {args.year}: {e}")

        if args.focus_day is not None:
            x_start = n * 30 + args.focus_day
            x_end = n * 30 + args.focus_day
        else:
            x_start = n * 30 + 1
            x_end = n * 30 + 30
            
        x_lo = x_start - args.buffer
        x_hi = x_end + args.buffer
        
        J_start = eng.day.civil_jdn(x_lo)
        J_end = eng.day.civil_jdn(x_hi)
        
        title_scope = f"Year {args.year}, M{args.month}"
        if args.focus_day:
            title_scope += f", LD{args.focus_day}"

    print(f"Generating Lunar Day Diagram for {base_engine.upper()} ({title_scope})...")

    # Determine adaptive label density to prevent text overlap
    num_days = J_end - J_start + 1
    label_step_x = 1
    label_step_y = 1
    if num_days > 60:
        label_step_x = 5
        label_step_y = 5
    elif num_days > 35:
        label_step_x = 3
        label_step_y = 2
    elif num_days > 15:
        label_step_x = 2
        label_step_y = 2

    # 2. Map Civil Grid & Assure Complete Tithi Coverage
    civil_bounds = list(range(J_start, J_end + 2))
    
    jdn_to_x = {J: [] for J in range(J_start, J_end + 1)}
    for x in range(x_lo - 15, x_hi + 16):
        J = eng.day.civil_jdn(x)
        if J in jdn_to_x:
            jdn_to_x[J].append(x)

    # Trim the vertical plot bounds cleanly to exactly what falls in the viewable window
    active_xs = []
    for J in range(J_start, J_end + 1):
        active_xs.extend(jdn_to_x.get(J, []))
    
    if active_xs:
        plot_x_min = min(active_xs) - 1
        plot_x_max = max(active_xs) + 1
    else:
        plot_x_min = x_lo
        plot_x_max = x_hi

    integer_x_vals = list(range(plot_x_min, plot_x_max + 1))

    # Helper function to find the Tithi active at dawn (Dawn Inheritance Rule)
    def get_inherited_name(jdn: int) -> int:
        if jdn in jdn_to_x and len(jdn_to_x[jdn]) > 0:
            return sorted(jdn_to_x[jdn])[0]
        curr = jdn + 1
        while curr <= max(jdn_to_x.keys()) + 15:
            ends = sorted([x for x in range(x_lo - 15, x_hi + 16) if eng.day.civil_jdn(x) == curr])
            if ends:
                return ends[0]
            curr += 1
        return plot_x_min 

    # 3. Generate Continuous Elongation Curve strictly over the trimmed bounds
    t_jd = []
    y_val = []
    for x_fl in np.linspace(plot_x_min - 1, plot_x_max + 1, max(500, (plot_x_max - plot_x_min + 1) * 50)):
        t_tt = float(eng.day.true_date(Fraction(float(x_fl))))
        t_jd.append(t_tt + 2451545.0)
        y_val.append(float(x_fl) - (n * 30))

    # 4. Build the Plot
    fig, ax = plt.subplots(figsize=(14, 6))
    dt_curve = [jd_to_datetime(t) for t in t_jd]
    dt_bounds = [jd_to_datetime(float(J)) for J in civil_bounds]

    ax.plot(dt_curve, y_val, color="#ff7f0e", linewidth=1.0, label="True Elongation (Continuous Phase)")

    y_lines = [float(x - (n * 30)) for x in integer_x_vals]
    for y in y_lines:
        ax.axhline(y, color="#888888", linestyle="-", linewidth=0.5, alpha=0.3)

    trans = ax.get_xaxis_transform()
    added_skip_legend = False
    added_dup_legend = False

    x_ticks = []
    x_labels = []

    # 5. Draw Vertical Civil Days, Shade Anomalies, and Assign Inherited Labels
    for i in range(len(dt_bounds) - 1):
        J = civil_bounds[i]
        ax.axvline(dt_bounds[i], color="#1f77b4", linestyle="--", linewidth=0.8, alpha=0.6)
        
        mid_time = dt_bounds[i] + (dt_bounds[i+1] - dt_bounds[i]) / 2
        x_ticks.append(mid_time)
        
        # Adaptive X-axis label spacing
        date_str = dt_bounds[i].strftime('%b-%d')
        if i % label_step_x == 0:
            x_labels.append(date_str)
        else:
            x_labels.append("")

        assigned_x = sorted(jdn_to_x.get(J, []))
        
        # Shade based on crossings
        if len(assigned_x) == 0:
            lbl = "0 Lunar Boundaries (Triggers Duplicated Name / Lhag)" if not added_dup_legend else ""
            ax.axvspan(dt_bounds[i], dt_bounds[i+1], color="#ffd700", alpha=0.15, label=lbl)
            added_dup_legend = True
        elif len(assigned_x) == 2:
            lbl = "2 Lunar Boundaries (Triggers Skipped Name / Chad)" if not added_skip_legend else ""
            ax.axvspan(dt_bounds[i], dt_bounds[i+1], color="#ff9999", alpha=0.20, label=lbl)
            added_skip_legend = True

        # STRICT DAWN INHERITANCE
        inherited_x = get_inherited_name(J)
        d_name = (inherited_x - 1) % 30 + 1
        
        # Only print civil label text if we are not skipping labels due to density
        if i % label_step_x == 0 or len(assigned_x) != 1:
            lbl_text = f"D{d_name}"
            ax.text(mid_time, 0.98, lbl_text, transform=trans, ha='center', va='top', 
                    fontsize=10, color="#333333")

    ax.axvline(dt_bounds[-1], color="#1f77b4", linestyle="--", linewidth=0.8, alpha=0.6)

    # 6. Format Y-Axis (Intervals with adaptive spacing)
    y_ticks = [y - 0.5 for y in y_lines]
    y_labels = [f"Lunar Day {int((x - 1) % 30) + 1}" if i % label_step_y == 0 else "" for i, x in enumerate(integer_x_vals)]
    
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