#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import sys
from typing import List, Optional

from caltib.reference import astro_args as aa
from caltib.reference import stars


def _need_package(name: str, pip_name: str = "") -> any:
    try:
        if name == "matplotlib.pyplot":
            import matplotlib.pyplot as plt
            return plt
        return __import__(name)
    except ImportError as e:
        pip_name = pip_name or name
        raise RuntimeError(f'Need {name}. Install: pip install {pip_name}') from e


def run_basic_validation(hip_id: int, star_name: str):
    """Runs the quick, dependency-free text validation."""
    star = stars.STAR_CATALOG[hip_id]
    
    print(f"=== Validation: {star.hip_id} ({star_name.capitalize()}) ===")
    print(f"Base Catalog (J2000.0):")
    print(f"  RA:  {star.ra_j2000_deg:.4f}°")
    print(f"  Dec: {star.dec_j2000_deg:.4f}°")
    print(f"  Proper Motion: {star.pm_ra_mas_yr} mas/yr (RA), {star.pm_dec_mas_yr} mas/yr (Dec)\n")

    test_epochs = [
        ("J2000.0", 2451545.0),
        ("March 2026", 2461106.5), 
        ("Year -3000", aa.J2000_TT + (-5000 * 365.25))
    ]

    for name, jd in test_epochs:
        print(f"--- Epoch: {name} (JD {jd}) ---")
        eq = stars.get_star_equatorial(hip_id, jd)
        ecl = stars.get_star_ecliptic(hip_id, jd)
        print(f"  Apparent Equatorial: RA {eq.ra_deg:.4f}°, Dec {eq.dec_deg:.4f}°")
        print(f"  Apparent Ecliptic:   Lon {ecl.L_deg:.4f}°, Lat {ecl.B_deg:.4f}°\n")


def run_astropy_validation(args, hip_id: int):
    """Runs the rigorous Astropy kinematic validation and plots the residuals."""
    np = _need_package("numpy")
    plt = _need_package("matplotlib.pyplot", "matplotlib")
    _need_package("astropy")
    
    # Import everything needed inside the function scope
    from astropy.coordinates import SkyCoord, GeocentricTrueEcliptic, FK5
    from astropy.time import Time
    import astropy.units as u
    import warnings
    from astropy.utils.exceptions import AstropyWarning
    import erfa

    star = stars.STAR_CATALOG[hip_id]
    print(f"Initializing Astropy validation for {args.star.capitalize()}...")

    # Suppress Astropy's warnings about missing radial velocity and deep historical dates
    warnings.simplefilter('ignore', category=AstropyWarning)
    warnings.simplefilter('ignore', category=erfa.core.ErfaWarning)

    # 1. Initialize the Star in Astropy (ICRS frame at J2000.0)
    # We supply a default distance and 0 radial velocity to force Astropy 
    # to treat proper motion purely as linear angular drift.
    astropy_star = SkyCoord(
        ra=star.ra_j2000_deg * u.deg,
        dec=star.dec_j2000_deg * u.deg,
        distance=1000 * u.pc,
        radial_velocity=0 * u.km/u.s,
        pm_ra_cosdec=star.pm_ra_mas_yr * u.mas/u.yr,
        pm_dec=star.pm_dec_mas_yr * u.mas/u.yr,
        frame='icrs',
        obstime=Time('J2000.0')
    )

    # 2. Generate Time Grid
    years = np.arange(args.year_start, args.year_end + 1, args.step_years)
    jds = aa.J2000_TT + (years - 2000) * 365.25
    
    print(f"Validating {len(jds)} epochs from Year {args.year_start} to {args.year_end}...")

    err_ra, err_dec = [], []
    err_lon, err_lat = [], []

    for jd, year in zip(jds, years):
        # --- Analytical Engine ---
        eq = stars.get_star_equatorial(hip_id, jd)
        ecl = stars.get_star_ecliptic(hip_id, jd)
        
        # --- Astropy Engine ---
        t = Time(jd, format='jd', scale='tt')
        star_at_t = astropy_star.apply_space_motion(t)
        
        # Astropy Apparent Equatorial (Mean of Date)
        fk5_t = star_at_t.transform_to(FK5(equinox=t))
        
        # Astropy Apparent Ecliptic (True of Date)
        ecl_t = star_at_t.transform_to(GeocentricTrueEcliptic(equinox=t))
        
        # --- Residuals in Arcseconds ---
        d_ra = ((eq.ra_deg - fk5_t.ra.deg + 180.0) % 360.0 - 180.0) * 3600.0
        d_dec = (eq.dec_deg - fk5_t.dec.deg) * 3600.0
        
        d_lon = ((ecl.L_deg - ecl_t.lon.deg + 180.0) % 360.0 - 180.0) * 3600.0
        d_lat = (ecl.B_deg - ecl_t.lat.deg) * 3600.0
        
        err_ra.append(d_ra)
        err_dec.append(d_dec)
        err_lon.append(d_lon)
        err_lat.append(d_lat)

    # 3. Plotting
    fig, axs = plt.subplots(4, 1, figsize=(10, 12), sharex=True)
    
    plot_configs = [
        (axs[0], err_ra, 'Equatorial Right Ascension', 'blue'),
        (axs[1], err_dec, 'Equatorial Declination', 'cyan'),
        (axs[2], err_lon, 'Ecliptic Longitude', 'orange'),
        (axs[3], err_lat, 'Ecliptic Latitude', 'red')
    ]
    
    for ax, data, title, color in plot_configs:
        ax.plot(years, data, marker='.', linestyle='-', markersize=4, alpha=0.7, color=color)
        ax.set_title(f"{title} Error (Analytical - Astropy)")
        ax.set_ylabel("Error (arcsec)")
        ax.grid(True, alpha=0.3)
        ax.axhline(0, color='black', linewidth=1.0)
        
    axs[-1].set_xlabel("Year")
    plt.suptitle(f"{args.star.capitalize()} Positional Validation ({args.year_start} to {args.year_end})", fontsize=14)
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=200)
    print(f"Validation complete. Plot saved to {args.out_png}")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Validate Stars analytical engine.")
    p.add_argument("--star", type=str, default="sirius", help="Name of the star to validate (e.g., sirius, pleiades).")
    p.add_argument("--year-start", type=int, default=-3000, help="Start year for plot (default: -3000).")
    p.add_argument("--year-end", type=int, default=3000, help="End year for plot (default: 3000).")
    p.add_argument("--step-years", type=int, default=50, help="Step size in years (default: 50).")
    p.add_argument("--astropy", action="store_true", help="Run Astropy validation and generate plot.")
    p.add_argument("--out-png", type=str, default="val_stars.png", help="Output plot filename.")
    
    args = p.parse_args(argv)
    
    try:
        hip_id = stars.get_star_id(args.star)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
        
    if args.astropy:
        run_astropy_validation(args, hip_id)
    else:
        run_basic_validation(hip_id, args.star)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())