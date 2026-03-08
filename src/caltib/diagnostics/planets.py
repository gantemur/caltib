#!/usr/bin/env python3
from __future__ import annotations

import argparse
from typing import List, Optional

from caltib.reference import astro_args as aa
from caltib.reference import planets

def _need_numpy():
    try:
        import numpy as np
        return np
    except ImportError as e:
        raise RuntimeError('Need numpy. Install: pip install "caltib[diagnostics]"') from e

def _need_matplotlib():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError as e:
        raise RuntimeError('Need matplotlib. Install: pip install "caltib[diagnostics]"') from e

def get_ayanamsha(jd: float, zero_year: float) -> float:
    """
    Calculates a linear Ayanamsha based on a historical zero-precession year.
    - ~285 CE: Lahiri (Modern standard)
    - ~499 CE: Aryabhata / Surya Siddhanta (Ancient Indian standard)
    """
    # Calculate the Ayanamsha base at exactly J2000.0
    years_since_zero = 2000.0 - zero_year
    base_j2000 = years_since_zero * 0.0139697 # 50.29 arcseconds per year in degrees
    
    # Calculate ongoing precession drift from J2000.0 to the requested JD
    days_since_j2000 = jd - 2451545.0
    years_since_j2000 = days_since_j2000 / 365.25
    precession_drift = years_since_j2000 * 0.0139697
    
    return base_j2000 + precession_drift

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Plot true longitude differences between Traditional Engines and Modern Kinematics.")
    
    # Renamed --spec to --engine
    p.add_argument("--engine", type=str, default="phugpa", help="Calendar engine key (e.g., phugpa, karana, mongol)")
    p.add_argument("--year-start", type=int, default=600)
    p.add_argument("--year-end", type=int, default=2000)
    p.add_argument("--step-days", type=int, default=30)
    
    # New parameter for historical Sidereal calibration
    p.add_argument("--zero", type=float, default=499.0, 
                   help="The year when Tropical and Sidereal Aries perfectly aligned (default: 499 for Aryabhata)")
    
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    from caltib.engines.factory import make_engine
    from caltib.engines.specs import ALL_SPECS

    if args.engine not in ALL_SPECS:
        raise ValueError(f"Engine '{args.engine}' not found in ALL_SPECS.")

    print(f"Initializing {args.engine.capitalize()} Calendar Engine...")
    engine = make_engine(ALL_SPECS[args.engine])

    # Generate Time Grid
    jd_start = aa.J2000_TT + (args.year_start - 2000) * 365.25
    jd_end = aa.J2000_TT + (args.year_end - 2000) * 365.25

    jds = np.arange(jd_start, jd_end, args.step_days)
    years = 2000 + (jds - aa.J2000_TT) / 365.25

    print(f"Validating {len(jds)} points from {years[0]:.0f} to {years[-1]:.0f}...")
    print(f"Using Sidereal Zero-Point Year: {args.zero} CE")

    planets_to_test = ["sun", "mercury", "venus", "mars", "jupiter", "saturn", "rahu"]
    
    errors_tropical = {p: [] for p in planets_to_test}
    errors_sidereal = {p: [] for p in planets_to_test}
    detrended_lon = {p: [] for p in planets_to_test}

    for jd in jds:
        trad_data = engine.get_planet_longitudes(jd)
        if trad_data is None:
            raise RuntimeError(f"The selected engine '{args.engine}' does not have a PlanetsEngine configured.")

        current_trop_errors = {}
        ayanamsha = get_ayanamsha(jd, args.zero)

        for p_name in planets_to_test:
            trad_deg = float(trad_data[p_name]["true"]) * 360.0
            mod_trop_deg = planets.geocentric_position(p_name, jd).L_true_deg
            mod_sid_deg = (mod_trop_deg - ayanamsha) % 360.0
            
            d_trop = (trad_deg - mod_trop_deg + 180.0) % 360.0 - 180.0
            current_trop_errors[p_name] = d_trop
            errors_tropical[p_name].append(d_trop)
            
            d_sid = (trad_deg - mod_sid_deg + 180.0) % 360.0 - 180.0
            errors_sidereal[p_name].append(d_sid)

        sun_trop_error = current_trop_errors["sun"]
        for p_name in planets_to_test:
            d_detrended = (current_trop_errors[p_name] - sun_trop_error + 180.0) % 360.0 - 180.0
            detrended_lon[p_name].append(d_detrended)

    # ---------------------------------------------------------
    # Plotting Architecture
    # ---------------------------------------------------------
    colors = {
        "sun": "gold", "mercury": "gray", "venus": "orange",
        "mars": "red", "jupiter": "brown", "saturn": "purple", "rahu": "black"
    }

    def generate_plot(data_dict, title, filename):
        fig, axs = plt.subplots(len(planets_to_test), 1, figsize=(12, 18), sharex=True)
        for i, p_name in enumerate(planets_to_test):
            axs[i].scatter(years, data_dict[p_name], s=2, alpha=0.7, color=colors[p_name])
            axs[i].set_title(f"{p_name.capitalize()} True Longitude Error")
            axs[i].set_ylabel("Error (Degrees)")
            axs[i].grid(True, alpha=0.3)
            axs[i].axhline(0, color='black', linewidth=1, alpha=0.8, linestyle='--')

        axs[-1].set_xlabel("Year")
        plt.suptitle(title, fontsize=14)
        plt.tight_layout(rect=[0, 0.03, 1, 0.98])
        plt.savefig(filename, dpi=200)
        print(f"Plot saved to {filename}")
        plt.close()

    generate_plot(
        errors_tropical, 
        f"TROPICAL (Raw): Traditional ({args.engine.capitalize()}) vs Modern Tropical", 
        f"planets_{args.engine}_tropical.png"
    )
    
    generate_plot(
        errors_sidereal, 
        f"SIDEREAL: Traditional ({args.engine.capitalize()}) vs Modern Sidereal (Ayanamsha Epoch {args.zero})", 
        f"planets_{args.engine}_sidereal.png"
    )
    
    generate_plot(
        detrended_lon, 
        f"DETRENDED (Sun Drift Removed): Pure Kālacakra Epicycle Mechanics", 
        f"planets_{args.engine}_detrended.png"
    )

    return 0

if __name__ == "__main__":
    raise SystemExit(main())