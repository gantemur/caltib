#!/usr/bin/env python3
"""
compare_sunrise.py

Plots the difference between the sunrise calculated by caltib Day Engines
and the high-precision reference calculator (reference.solar).
Supports up to 4 engines simultaneously and highlights polar gaps.
"""

from __future__ import annotations

import argparse
import math
from datetime import datetime, date, timedelta
from fractions import Fraction
import matplotlib.pyplot as plt

import caltib
from caltib.core.types import LocationSpec, SunriseState
from caltib.reference import solar as ref_solar
from caltib.reference import time_scales as ref_ts


def get_jd_utc_noon(d: date) -> float:
    """Returns the Julian Date at 12:00 UTC for a given Gregorian date."""
    diff = d - date(2000, 1, 1)
    return 2451544.5 + diff.days + 0.5


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare engine sunrises with reference.")
    parser.add_argument("--engines", type=str, default="phugpa,l3", help="Comma-separated engine names (max 4).")
    parser.add_argument("--lat", type=float, default=29.65, help="Latitude (default: Lhasa 29.65)")
    parser.add_argument("--lon", type=float, default=91.1, help="Longitude (default: Lhasa 91.1)")
    parser.add_argument("--start", type=str, default="2026-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default="2026-12-31", help="End date (YYYY-MM-DD)")
    
    args = parser.parse_args(argv)

    # 1. Setup Location
    loc = LocationSpec(
        name="Custom",
        lat_turn=Fraction(args.lat) / 360,
        lon_turn=Fraction(args.lon) / 360
    )
    
    # 2. Setup Engines (Limit to 4 for visual clarity)
    engine_names = [e.strip() for e in args.engines.split(",")][:4]
    engines = {}
    for name in engine_names:
        try:
            engines[name] = caltib.get_calendar(name, location=loc)
        except Exception as e:
            print(f"Failed to load engine '{name}': {e}")
            return
            
    # 3. Setup Time Range
    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
    total_days = (end_date - start_date).days
    
    if total_days <= 0:
        print("Error: End date must be after start date.")
        return

    dates = []
    engine_errors = {name: [] for name in engine_names}
    
    # Masks for shading
    is_polar_day = []
    is_polar_night = []

    print(f"Comparing {', '.join(engine_names).upper()} to reference for Lat: {args.lat}, Lon: {args.lon}")
    print(f"Calculating {total_days} days...")

    # 4. Main Evaluation Loop
    for i in range(total_days):
        current_date = start_date + timedelta(days=i)
        jd_utc_noon = get_jd_utc_noon(current_date)
        
        # A. Reference Sunrise (UTC)
        ref_sunrise = ref_solar.sunrise_sunset_utc(
            jd_utc_noon, 
            lat_deg=args.lat, 
            lon_deg_east=args.lon
        )
        
        dates.append(current_date)
        
        # Track the polar state for shading
        state = ref_sunrise.state
        is_polar_day.append(state == SunriseState.POLAR_DAY)
        is_polar_night.append(state == SunriseState.POLAR_NIGHT)

        # If reference model hits Polar Day/Night, skip calculating math errors today
        if state != SunriseState.NORMAL:
            for name in engine_names:
                engine_errors[name].append(float('nan'))
            continue
            
        ref_utc_hours = ref_sunrise.rise_utc_hours
        jd_tt = ref_ts.jd_utc_to_jd_tt(jd_utc_noon)
        t2000_tt = jd_tt - 2451545.0

        # B. Calculate Engine Sunrises
        for name, engine in engines.items():
            try:
                lmt_frac, eng_state = engine.eval_sunrise_lmt(t2000_tt)
            except AttributeError:
                print(f"Error: Engine '{name}' does not implement eval_sunrise_lmt().")
                return
                
            # If the engine itself hit a polar fallback, skip plotting its error
            if eng_state != SunriseState.NORMAL:
                engine_errors[name].append(float('nan'))
                continue

            lon_turn = args.lon / 360.0
            engine_utc_frac = (float(lmt_frac) - lon_turn) % 1.0
            engine_utc_hours = engine_utc_frac * 24.0

            # Calculate wrapped difference
            diff_hours = engine_utc_hours - ref_utc_hours
            diff_hours = (diff_hours + 12.0) % 24.0 - 12.0
            engine_errors[name].append(diff_hours * 60.0)

    # 5. Plotting
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Standard color palette for up to 4 engines
    colors = ['#2563eb', '#dc2626', '#16a34a', '#d97706'] 
    
    for idx, name in enumerate(engine_names):
        ax.plot(dates, engine_errors[name], label=f'{name.upper()}', color=colors[idx], linewidth=1.5, alpha=0.9)
    
    # Shade polar regions dynamically
    if any(is_polar_day):
        ax.fill_between(dates, 0, 1, where=is_polar_day, color='#fef08a', alpha=0.4, 
                        transform=ax.get_xaxis_transform(), label='Polar Day (Midnight Sun)')
    if any(is_polar_night):
        ax.fill_between(dates, 0, 1, where=is_polar_night, color='#1e3a8a', alpha=0.2, 
                        transform=ax.get_xaxis_transform(), label='Polar Night (No Sunrise)')

    ax.set_title(f"Sunrise Error: Engine vs Reference Calculator\n(Lat: {args.lat}°, Lon: {args.lon}°)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Error (Minutes)\n[Engine - Reference]")
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.axhline(0, color='black', linewidth=1)
    
    # Shade the target acceptable region for the Equation of Time (±16 mins)
    ax.fill_between(dates, -16, 16, color='gray', alpha=0.1, label='±16 min (EoT bound)')
    
    ax.legend()
    plt.tight_layout()
    
    # 6. Save to file instead of showing
    filename = f"sunrise_err_lat{args.lat}_lon{args.lon}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Success! Plot saved to: {filename}")

    return 0

if __name__ == "__main__":
    main()