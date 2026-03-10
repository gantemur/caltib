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
    
    # Standard input
    p.add_argument("--year", type=int, default=2026, help="Target lunar year.")
    p.add_argument("--focus-month", type=int, default=None, help="Zoom in on a specific month (1-12).")
    
    # Date window input
    p.add_argument("--month-start", type=str, default=None, help="Start Gregorian month (YYYY-MM)")
    p.add_argument("--month-end", type=str, default=None, help="End Gregorian month (YYYY-MM)")
    
    # Macro year-mode input
    p.add_argument("--year-start", type=int, default=None, help="Start lunar year for macro-mode")
    p.add_argument("--year-end", type=int, default=None, help="End lunar year for macro-mode")

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

    # 1. Determine absolute lunation bounds using the engine's native structural mapping
    if args.month_start and args.month_end:
        jd_s = datetime.strptime(args.month_start, "%Y-%m").toordinal() + 1721425
        jd_e = datetime.strptime(args.month_end, "%Y-%m").toordinal() + 1721425
        d_s = eng.from_jdn(jd_s)
        d_e = eng.from_jdn(jd_e)
        n_lo = eng.month.get_lunations(d_s.year, d_s.month)[0] - args.buffer
        n_hi = eng.month.get_lunations(d_e.year, d_e.month)[-1] + args.buffer
        title_scope = f"{args.month_start} to {args.month_end}"
        
    elif args.year_start and args.year_end:
        n_lo = eng.month.first_lunation(args.year_start) - args.buffer
        n_hi = eng.month.first_lunation(args.year_end + 1) + args.buffer
        title_scope = f"Years {args.year_start} to {args.year_end}"
        
    elif args.focus_month is not None:
        try:
            target_lunations = eng.month.get_lunations(args.year, args.focus_month)
            n_lo = target_lunations[0] - args.buffer
            n_hi = target_lunations[-1] + args.buffer + 1
            title_scope = f"Year {args.year}, Month {args.focus_month}"
        except Exception as e:
            raise SystemExit(f"Could not find Month {args.focus_month} for year {args.year}: {e}")
            
    else:
        try:
            n_lo = eng.month.first_lunation(args.year) - args.buffer
            n_hi = eng.month.first_lunation(args.year + 1) + args.buffer
            title_scope = f"Year {args.year}"
        except Exception as e:
            raise SystemExit(f"Could not find lunations for year {args.year}: {e}")

    print(f"Generating Transit Diagram for {base_engine.upper()} ({title_scope})...")

    # Adaptive density: clean up the chart if we are plotting many years
    total_months = n_hi - n_lo
    is_macro_view = total_months > 36
    is_ultra_macro = total_months > 600  # Triggers at ~50+ years

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
    t_grid = np.linspace(t_start, t_end, max(500, total_months * 10))
    
    sun_turns = np.array([float(eng.month.true_sun_tt(Fraction(float(t)))) for t in t_grid])
    sun_unwrapped_turns = np.unwrap(sun_turns * 2 * np.pi) / (2 * np.pi)
    sun_deg_unwrapped = sun_unwrapped_turns * 360.0

    # 4. Determine Exact Horizontal Sgang Boundaries
    sgang_base_deg = float(eng.sgang_base) * 360.0
    min_deg = sun_deg_unwrapped.min()
    max_deg = sun_deg_unwrapped.max()
    
    k_start = np.floor((min_deg - sgang_base_deg) / 30.0)
    k_end = np.ceil((max_deg - sgang_base_deg) / 30.0)
    
    ks = np.arange(k_start, k_end + 1)
    sgang_lines = sgang_base_deg + ks * 30.0

    # 5. Build the Plot
    fig, ax = plt.subplots(figsize=(14, 6))
    dt_grid = [jd_to_datetime(t + 2451545.0) for t in t_grid]
    dt_moons = [jd_to_datetime(jd) for jd in new_moons_jd]

    # Make the sawtooth line thinner if we are rendering 50+ years
    lw_sun = 0.5 if is_ultra_macro else 1.5
    ax.plot(dt_grid, sun_deg_unwrapped, color="#ff7f0e", linewidth=lw_sun, label="True Solar Longitude")

   # Draw Sgang lines (Adaptive reduction of clutter)
    for k, deg in zip(ks, sgang_lines):
        if is_ultra_macro and k % 120 != 0:
            continue  # Only draw a horizontal line every 10 years
        elif is_macro_view and not is_ultra_macro and k % 12 != 0:
            continue  # Only draw a horizontal line every 1 year
            
        is_major = (k % 12 == 0)
        alpha_val = 0.5 if is_major else 0.3
        line_w = 1.0 if is_major else 0.5
        ax.axhline(deg, color="#888888", linestyle="-", linewidth=line_w, alpha=alpha_val)

    trans = ax.get_xaxis_transform()
    added_leap_legend = False
    added_skip_legend = False

    year_bounds = []

    # 6. Draw Moons, Count Transits, and Shade Backgrounds
    for i in range(len(dt_moons)):
        is_year_start = (i < len(labels)) and (labels[i]['month'] == 1) and (labels[i]['leap_state'] != 2)
        
        if is_year_start:
            yr = labels[i]['year']
            year_bounds.append((dt_moons[i], yr))
            
            # Draw vertical lines: all months (standard), year boundaries (macro), or decade boundaries (ultra-macro)
            if not is_ultra_macro:
                ax.axvline(dt_moons[i], color="#1f77b4", linestyle="-", linewidth=0.8, alpha=0.5)
            elif yr % 10 == 0:
                ax.axvline(dt_moons[i], color="#1f77b4", linestyle="-", linewidth=1.0, alpha=0.3)
                
        elif not is_macro_view:
            ax.axvline(dt_moons[i], color="#1f77b4", linestyle="--", linewidth=0.5, alpha=0.4)
        
        if i < len(dt_moons) - 1:
            info = labels[i]
            mid_time = dt_moons[i] + (dt_moons[i+1] - dt_moons[i]) / 2
            
            y_start = np.interp(t_grid[0] + (dt_moons[i] - dt_grid[0]).total_seconds()/86400, t_grid, sun_deg_unwrapped)
            y_end = np.interp(t_grid[0] + (dt_moons[i+1] - dt_grid[0]).total_seconds()/86400, t_grid, sun_deg_unwrapped)
            crossings = len([y for y in sgang_lines if y_start <= y < y_end])
            
            # Boost alpha heavily in ultra-macro so the sliver-thin strips don't vanish
            alpha_leap = 1.0 if is_ultra_macro else (0.6 if is_macro_view else 0.15)
            alpha_skip = 1.0 if is_ultra_macro else (0.6 if is_macro_view else 0.20)
            
            if crossings == 0:
                lbl = "Astronomical Leap (0 Transits)" if not added_leap_legend else ""
                ax.axvspan(dt_moons[i], dt_moons[i+1], color="#ffd700", alpha=alpha_leap, linewidth=0, label=lbl)
                added_leap_legend = True
            elif crossings == 2:
                lbl = "Astronomical Skip (2 Transits)" if not added_skip_legend else ""
                ax.axvspan(dt_moons[i], dt_moons[i+1], color="#ff9999", alpha=alpha_skip, linewidth=0, label=lbl)
                added_skip_legend = True

            if not is_macro_view:
                lbl_text = f"M{info['month']}"
                ax.text(mid_time, 0.98, lbl_text, transform=trans, ha='center', va='top', 
                        fontsize=10, color="#333333", fontweight="bold")

    # Format Y-Axes adaptively (Only left axis in macro view)
    y_ticks, y_labels, y_sec_labels = [], [], []
    for k, deg in zip(ks, sgang_lines):
        if is_ultra_macro:
            if k % 120 != 0:
                continue
            lbl = ""  # Remove repeating degree labels completely
        elif is_macro_view:
            if k % 12 != 0:
                continue
            lbl = f"{int(deg % 360)}°"
        else:
            lbl = f"{int(deg % 360)}°"
            
        y_ticks.append(deg)
        y_labels.append(lbl)
        y_sec_labels.append(f"Sgang {int(k % 12) + 1}")

    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels, color="#555555", fontsize=9)
    
    # Always show the Y-axis title
    ax.set_ylabel("Solar Longitude (Degrees)", color="#444444")
    
    # Hide the physical tick marks in ultra-macro view for maximum minimalism
    if is_ultra_macro:
        ax.tick_params(axis='y', length=0)

    # Only show the right-hand Sgang text labels if we are zoomed in
    if not is_macro_view:
        secax = ax.secondary_yaxis('right')
        secax.set_yticks(y_ticks)
        secax.set_yticklabels(y_sec_labels, color="#1f77b4", fontsize=9, fontweight="bold")
        secax.spines['right'].set_visible(False)
        secax.tick_params(right=False)

    # Format X-Axis: Intervals for Macro View, ConciseDates for Zoomed View
    if is_macro_view and len(year_bounds) > 0:
        x_ticks = []
        x_labels = []
        for j in range(len(year_bounds)):
            start_dt, yr = year_bounds[j]
            
            # In ultra-macro mode, only label decades to prevent text overlapping
            if is_ultra_macro and yr % 10 != 0:
                continue
                
            end_dt = year_bounds[j+1][0] if j < len(year_bounds) - 1 else dt_moons[-1]
            mid_dt = start_dt + (end_dt - start_dt) / 2
            
            x_ticks.append(mid_dt)
            x_labels.append(str(yr))
            
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_labels, color="#555555", fontsize=10, fontweight="bold")
        ax.tick_params(axis='x', length=0)
    else:
        locator = mdates.AutoDateLocator()
        formatter = mdates.ConciseDateFormatter(locator)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)

    plt.title(f"Lunisolar Intercalation Grid: {base_engine.upper()} ({title_scope})\nVertical: Year Boundaries  |  Horizontal: Equinox/Solstice Transits", pad=20)
    
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