#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone

from caltib.reference import planets, lunar, coords, stars
from caltib.reference import time_scales as ts

def print_body(name: str, eq: coords.Equatorial, jd_utc: float, lat: float, lon: float):
    """Helper to compute horizontal coordinates and print the output."""
    # Equatorial to Horizontal
    horiz = coords.equatorial_to_horizontal(eq, jd_utc, lat, lon)
    
    # Apply Atmospheric Refraction
    app_alt = coords.apply_refraction(horiz.alt_deg)
    
    print(f"--- {name} ---")
    print(f"  Right Ascension: {eq.ra_deg:.2f}°")
    print(f"  Declination:     {eq.dec_deg:.2f}°")
    print(f"  Azimuth:         {horiz.az_deg:.2f}° (North=0, East=90)")
    print(f"  Apparent Alt:    {app_alt:.2f}°")
    
    if app_alt > 0:
        print(f"  Status: Visible above horizon")
    else:
        print(f"  Status: Below horizon")
    print("")

def print_local_sky(jd_utc: float, lat: float, lon: float):
    # Dynamically compute TT from UTC using the time_scales module
    jd_tt = ts.jd_utc_to_jd_tt(jd_utc)
    
    # Format the time for display
    dt_utc = ts.jd_to_datetime_utc(jd_utc)
    
    print(f"=== Local Sky Viewer ===")
    print(f"Location:  Lat {lat:.4f}°, Lon {lon:.4f}°")
    print(f"Date UTC:  {dt_utc.strftime('%Y-%m-%d %H:%M:%S')} (JD {jd_utc:.5f})")
    print(f"Date TT:   JD {jd_tt:.5f}")
    print("========================\n")
    
    # 1. Ecliptic Solar System Bodies
    solar_system_bodies = [
        ("Sun", "sun"),
        ("Moon", "moon"),
        ("Mercury", "mercury"),
        ("Venus", "venus"),
        ("Mars", "mars"),
        ("Jupiter", "jupiter"),
        ("Saturn", "saturn")
    ]
    
    for display_name, body_name in solar_system_bodies:
        # Fetch Ecliptic Coordinates
        if body_name == "moon":
            geo = lunar.lunar_position(jd_tt)
        else:
            geo = planets.geocentric_position(body_name, jd_tt)
            
        # Convert Ecliptic to Equatorial
        eq = coords.ecliptic_to_equatorial(geo.L_true_deg, geo.B_true_deg, jd_tt)
        print_body(display_name, eq, jd_utc, lat, lon)

    # 2. Equatorial Stellar Bodies (Stars)
    try:
        sirius_id = stars.get_star_id("sirius")
        # stars module yields Equatorial directly
        eq_sirius = stars.get_star_equatorial(sirius_id, jd_tt)
        # Convert returned object to the coords.Equatorial dataclass format for our helper
        eq_sirius_formatted = coords.Equatorial(ra_deg=eq_sirius.ra_deg, dec_deg=eq_sirius.dec_deg)
        print_body("Sirius", eq_sirius_formatted, jd_utc, lat, lon)
    except Exception as e:
        print(f"--- Sirius ---\n  Status: Could not load star data ({e})\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate local sky coordinates for celestial bodies.")
    
    # Default to current Montreal coordinates
    parser.add_argument("--lat", type=float, default=45.5017, help="Observer Latitude (Degrees). Default: Montreal (45.5017).")
    parser.add_argument("--lon", type=float, default=-73.5673, help="Observer Longitude (Degrees East). Default: Montreal (-73.5673).")
    
    # Default to current time
    parser.add_argument("--jd", type=float, default=None, help="Specific Julian Date (UTC). Defaults to current system time.")
    
    args = parser.parse_args()

    # Determine Time
    if args.jd is not None:
        jd_utc = args.jd
    else:
        dt_now = datetime.now(timezone.utc)
        jd_utc = ts.datetime_utc_to_jd(dt_now)

    print_local_sky(jd_utc, args.lat, args.lon)