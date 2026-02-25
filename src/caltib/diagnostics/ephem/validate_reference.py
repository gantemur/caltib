#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
from typing import List, Optional

from caltib.reference import astro_args as aa
from caltib.reference import solar
from caltib.reference import lunar
from caltib.ephemeris.de422 import DE422Elongation


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


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Validate analytical solar/lunar models against DE422.")
    p.add_argument("--year-start", type=int, default=-3000)
    p.add_argument("--year-end", type=int, default=3000)
    p.add_argument("--step-days", type=int, default=50)
    p.add_argument("--out-png", default="reference_validation.png")
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    print("Loading DE422 Ephemeris...")
    el = DE422Elongation.load()
    eph = el.eph
    emrat = el.emrat

    # Generate Time Grid
    jd_start = aa.J2000_TT + (args.year_start - 2000) * 365.25
    jd_end = aa.J2000_TT + (args.year_end - 2000) * 365.25
    
    min_jd = 625648.5
    max_jd = 2816816.5

    # Strictly clip to ephemeris bounds
    jd_start_clipped = max(jd_start, min_jd + 1.0)
    jd_end_clipped = min(jd_end, max_jd - 1.0)

    if jd_start_clipped > jd_end_clipped:
        raise ValueError(f"Requested range is outside valid ephemeris range [{min_jd}, {max_jd}]")

    jds = np.arange(jd_start_clipped, jd_end_clipped, args.step_days)
    years = 2000 + (jds - aa.J2000_TT) / 365.25

    print(f"Validating {len(jds)} points from {years[0]:.0f} to {years[-1]:.0f}...")

    err_solar_lon = []
    err_lunar_lon = []
    err_lunar_lat = []

    for jd in jds:
        T = aa.T_centuries(jd)
        
        # 1. Exact DE422 Coordinates (Native output is Equatorial J2000)
        r_emb = eph.compute("earthmoon", jd)[:3]
        r_em = eph.compute("moon", jd)[:3]
        r_sun = eph.compute("sun", jd)[:3]

        r_earth = r_emb - r_em / (emrat + 1.0)
        r_es = r_sun - r_earth

        # 2. Rotate DE422 vectors to Ecliptic of Date
        rot_matrix = aa.matrix_eq_j2000_to_ecl_date(T)
        
        v_sun_date = aa.apply_matrix(rot_matrix, r_es)
        v_moon_date = aa.apply_matrix(rot_matrix, r_em)

        # 3. Extract Spherical Coordinates (DE422 True of Date)
        de_lon_sun = math.degrees(math.atan2(v_sun_date[1], v_sun_date[0])) % 360.0
        
        de_lon_moon = math.degrees(math.atan2(v_moon_date[1], v_moon_date[0])) % 360.0
        r_moon_xy = math.hypot(v_moon_date[0], v_moon_date[1])
        de_lat_moon = math.degrees(math.atan2(v_moon_date[2], r_moon_xy))

        # 4. Analytical Coordinates (Mean Equinox of Date)
        sol = solar.solar_longitude(jd)
        lun = lunar.lunar_position(jd)

        # 5. Calculate Residuals in Arcseconds
        d_sun_lon = ((sol.L_true_deg - de_lon_sun + 180.0) % 360.0 - 180.0) * 3600.0
        d_moon_lon = ((lun.L_true_deg - de_lon_moon + 180.0) % 360.0 - 180.0) * 3600.0
        d_moon_lat = (lun.B_true_deg - de_lat_moon) * 3600.0

        err_solar_lon.append(d_sun_lon)
        err_lunar_lon.append(d_moon_lon)
        err_lunar_lat.append(d_moon_lat)

    # 6. Plotting
    fig, axs = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    
    axs[0].scatter(years, err_solar_lon, s=1, alpha=0.5, color='orange')
    axs[0].set_title("Solar True Longitude Error (Analytical - DE422)")
    axs[0].set_ylabel("Error (arcsec)")
    axs[0].grid(True, alpha=0.3)

    axs[1].scatter(years, err_lunar_lon, s=1, alpha=0.5, color='blue')
    axs[1].set_title("Lunar True Longitude Error (Analytical - DE422)")
    axs[1].set_ylabel("Error (arcsec)")
    axs[1].grid(True, alpha=0.3)

    axs[2].scatter(years, err_lunar_lat, s=1, alpha=0.5, color='green')
    axs[2].set_title("Lunar True Latitude Error (Analytical - DE422)")
    axs[2].set_ylabel("Error (arcsec)")
    axs[2].set_xlabel("Year")
    axs[2].grid(True, alpha=0.3)

    plt.suptitle(f"Reference Model Validation against DE422 ({years[0]:.0f} to {years[-1]:.0f})", fontsize=14)
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=200)
    print(f"Validation complete. Plot saved to {args.out_png}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())