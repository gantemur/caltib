#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
from typing import List, Optional

from caltib.reference import astro_args as aa
from caltib.reference import planets
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
    p = argparse.ArgumentParser(description="Validate Micro-VSOP Heliocentric models against DE422.")
    p.add_argument("--year-start", type=int, default=-1000)
    p.add_argument("--year-end", type=int, default=3000)
    p.add_argument("--step-days", type=int, default=50)
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    print("Loading DE422 Ephemeris...")
    el = DE422Elongation.load()
    eph = el.eph
    emrat = el.emrat  # Needed to extract exact Earth vector

    # Generate Time Grid
    jd_start = aa.J2000_TT + (args.year_start - 2000) * 365.25
    jd_end = aa.J2000_TT + (args.year_end - 2000) * 365.25
    
    min_jd = 625648.5
    max_jd = 2816816.5

    jd_start_clipped = max(jd_start, min_jd + 1.0)
    jd_end_clipped = min(jd_end, max_jd - 1.0)

    jds = np.arange(jd_start_clipped, jd_end_clipped, args.step_days)
    years = 2000 + (jds - aa.J2000_TT) / 365.25

    print(f"Validating {len(jds)} points from {years[0]:.0f} to {years[-1]:.0f}...")

    planets_to_test = ["mercury", "venus", "earth", "mars", "jupiter", "saturn"]

    errors_lon = {p: [] for p in planets_to_test}
    errors_lat = {p: [] for p in planets_to_test}
    errors_dist = {p: [] for p in planets_to_test}

    for jd in jds:
        T = aa.T_centuries(jd)
        
        # 1. Exact DE422 Sun Vector (ICRF / Equatorial J2000)
        r_sun = eph.compute("sun", jd).flatten()[:3]
        
        # Earth is a special case in DE422 (extract from Earth-Moon Barycenter)
        r_emb = eph.compute("earthmoon", jd).flatten()[:3]
        r_em = eph.compute("moon", jd).flatten()[:3]
        r_earth = r_emb - r_em / (emrat + 1.0)
        
        # Matrix to rotate vectors from Equatorial J2000 to Ecliptic of Date
        rot_matrix = aa.matrix_eq_j2000_to_ecl_date(T)

        for p_name in planets_to_test:
            # 2. Target planet vector 
            if p_name == "earth":
                r_target = r_earth
            else:
                r_target = eph.compute(p_name, jd).flatten()[:3]

            # 3. Pure Heliocentric Vector in J2000 Equatorial
            r_helio_eq = r_target - r_sun

            # 4. Rotate to Ecliptic of Date
            v_helio_date = aa.apply_matrix(rot_matrix, r_helio_eq)

            # 5. Extract Spherical Coordinates (DE422 True Heliocentric of Date)
            de_lon = math.degrees(math.atan2(float(v_helio_date[1]), float(v_helio_date[0]))) % 360.0
            r_xy = math.hypot(float(v_helio_date[0]), float(v_helio_date[1]))
            de_lat = math.degrees(math.atan2(float(v_helio_date[2]), r_xy))
            de_dist_km = math.sqrt(sum(float(v)**2 for v in v_helio_date))
            de_dist_au = de_dist_km / 149597870.7

            # 6. Analytical Heliocentric Coordinates (Micro-VSOP)
            helio = planets.heliocentric_position(p_name, jd)

            # 7. Calculate Residuals
            d_lon = ((helio.L_true_deg - de_lon + 180.0) % 360.0 - 180.0) * 3600.0
            d_lat = (helio.B_true_deg - de_lat) * 3600.0
            d_dist = (helio.R_true_au - de_dist_au) * 149597870700.0  # distance error in meters
            
            errors_lon[p_name].append(d_lon)
            errors_lat[p_name].append(d_lat)
            errors_dist[p_name].append(d_dist)

    # 8. Plotting
    colors = {
        "mercury": "gray", "venus": "orange", "earth": "blue", 
        "mars": "red", "jupiter": "brown", "saturn": "purple"
    }

    def generate_plot(error_dict, title_desc, ylabel, filename):
        fig, axs = plt.subplots(len(planets_to_test), 1, figsize=(12, 16), sharex=True)
        for i, p_name in enumerate(planets_to_test):
            axs[i].scatter(years, error_dict[p_name], s=1, alpha=0.5, color=colors[p_name])
            axs[i].set_title(f"{p_name.capitalize()} {title_desc}")
            axs[i].set_ylabel(ylabel)
            axs[i].grid(True, alpha=0.3)
            axs[i].axhline(0, color='black', linewidth=0.8, alpha=0.8)

        axs[-1].set_xlabel("Year")
        plt.suptitle(f"Heliocentric Validation against DE422 ({years[0]:.0f} to {years[-1]:.0f})", fontsize=14)
        plt.tight_layout(rect=[0, 0.03, 1, 0.98])
        plt.savefig(filename, dpi=200)
        print(f"Plot saved to {filename}")
        plt.close()

    # Generate 3 Separate PNGs
    generate_plot(errors_lon, "True Heliocentric Longitude Error (Analytical - DE422)", "Error (arcsec)", "val_helio_lon.png")
    generate_plot(errors_lat, "True Heliocentric Latitude Error (Analytical - DE422)", "Error (arcsec)", "val_helio_lat.png")
    generate_plot(errors_dist, "Heliocentric Distance Error (Analytical - DE422)", "Error (meters)", "val_helio_dist.png")

    print("All validations complete.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())