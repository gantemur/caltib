#!/usr/bin/env python3
import argparse
import sys
import urllib.request
import urllib.parse
import json
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    print("CRITICAL: Python 3.9+ is required for the zoneinfo module.")
    sys.exit(1)

from caltib.reference import planets, coords, stars
from caltib.reference import time_scales as ts

# ============================================================
# Built-in City Registry: (Latitude, Longitude, IANA Timezone)
# ============================================================
CITIES = {
    "montreal": (45.5017, -73.5673, "America/Toronto"),
    "lhasa": (29.6500, 91.1000, "Asia/Shanghai"),
    "new york": (40.7128, -74.0060, "America/New_York"),
    "london": (51.5074, -0.1278, "Europe/London"),
    "paris": (48.8566, 2.3522, "Europe/Paris"),
    "tokyo": (35.6762, 139.6503, "Asia/Tokyo"),
    "sydney": (-33.8688, 151.2093, "Australia/Sydney"),
    "beijing": (39.9042, 116.4074, "Asia/Shanghai"),
    "delhi": (28.6139, 77.2090, "Asia/Kolkata"),
    "ulaanbaatar": (47.9200, 106.9200, "Asia/Ulaanbaatar"),
    "ub": (47.9200, 106.9200, "Asia/Ulaanbaatar"),
    "moscow": (55.7558, 37.6173, "Europe/Moscow"),
    "seoul": (37.5665, 126.9780, "Asia/Seoul"),
    "san diego": (32.7157, -117.1611, "America/Los_Angeles"),
    "amsterdam": (52.3676, 4.9041, "Europe/Amsterdam"),
    "utrecht": (52.0907, 5.1214, "Europe/Amsterdam"),
    "hohhot": (40.8422, 111.7492, "Asia/Shanghai"),
    "elista": (46.3078, 44.2558, "Europe/Moscow"),
    "thimphu": (27.4728, 89.6393, "Asia/Thimphu"),
    "vienna": (48.2082, 16.3738, "Europe/Vienna"),
    "toronto": (43.6510, -79.3470, "America/Toronto"),
    "nanchang": (28.6820, 115.8579, "Asia/Shanghai"),
}

# JPL Horizons ID Mapping
JPL_IDS = {
    "sun": "10",
    "moon": "301",
    "mercury": "199",
    "venus": "299",
    "mars": "499",
    "jupiter": "599",
    "saturn": "699",
    "sirius": "6730001", # Sirius
    "vega": "6730230",   # Vega
    "betelgeuse": "6730052", # Betelgeuse
    "spica": "6730163",  # Spica
    "aldebaran": "6730039" # Aldebaran
}

def _get_timezone(lat: float, lon: float, tz_str: str = None) -> ZoneInfo:
    if tz_str:
        try:
            return ZoneInfo(tz_str)
        except Exception as e:
            print(f"Warning: Could not load timezone '{tz_str}': {e}. Falling back to UTC.")
            return timezone.utc

    try:
        from timezonefinder import TimezoneFinder
        tf = TimezoneFinder()
        auto_tz = tf.timezone_at(lng=lon, lat=lat)
        if auto_tz:
            return ZoneInfo(auto_tz)
    except ImportError:
        pass
        
    return timezone.utc

def get_jpl_horizons_data(target_id: str, lat: float, lon: float, jd_start: float) -> dict:
    """Queries the JPL Horizons API for topocentric coordinates."""
    params = {
        "format": "json",
        "COMMAND": f"'{target_id}'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'", 
        "CENTER": f"'coord@399'",   
        "COORD_TYPE": "'GEODETIC'",
        "SITE_COORD": f"'{lon},{lat},0'", 
        "TLIST": f"'{jd_start}'",   
        "QUANTITIES": "'2,4'", 
        "CSV_FORMAT": "'YES'",
        "ANG_FORMAT": "'DEG'"  
    }
    
    url = "https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
    except Exception:
        return None

    result_text = data.get("result", "")
    try:
        soe_idx = result_text.find("$$SOE") + 6
        eoe_idx = result_text.find("$$EOE")
        csv_line = result_text[soe_idx:eoe_idx].strip()
        cols = csv_line.split(',')
        
        return {
            "app_ra_deg": float(cols[3].strip()),
            "app_dec_deg": float(cols[4].strip()),
            "azimuth_deg": float(cols[5].strip()),
            "altitude_deg": float(cols[6].strip())
        }
    except Exception:
        return None

def _diff_angle(a: float, b: float) -> float:
    """Safely calculates the shortest angular difference."""
    return ((a - b + 180.0) % 360.0) - 180.0

def print_body(name: str, eq: coords.Equatorial, jd_utc: float, lat: float, lon: float, jpl_data: dict = None):
    horiz = coords.equatorial_to_horizontal(eq, jd_utc, lat, lon)
    app_alt = coords.apply_refraction(horiz.alt_deg)
    
    print(f"--- {name} ---")
    if jpl_data:
        d_ra = _diff_angle(eq.ra_deg, jpl_data['app_ra_deg'])
        d_dec = eq.dec_deg - jpl_data['app_dec_deg']
        d_az = _diff_angle(horiz.az_deg, jpl_data['azimuth_deg'])
        d_alt = app_alt - jpl_data['altitude_deg']
        
        print(f"                   Analytical | JPL Horizons | Difference (deg)")
        print(f"  Right Ascension: {eq.ra_deg:10.4f}° | {jpl_data['app_ra_deg']:12.4f}° | {d_ra:10.4f}°")
        print(f"  Declination:     {eq.dec_deg:10.4f}° | {jpl_data['app_dec_deg']:12.4f}° | {d_dec:10.4f}°")
        print(f"  Azimuth:         {horiz.az_deg:10.4f}° | {jpl_data['azimuth_deg']:12.4f}° | {d_az:10.4f}°")
        print(f"  Apparent Alt:    {app_alt:10.4f}° | {jpl_data['altitude_deg']:12.4f}° | {d_alt:10.4f}°")
    else:
        print(f"  Right Ascension: {eq.ra_deg:8.4f}°")
        print(f"  Declination:     {eq.dec_deg:8.4f}°")
        print(f"  Azimuth:         {horiz.az_deg:8.4f}° (North=0, East=90)")
        print(f"  Apparent Alt:    {app_alt:8.4f}°")
    
    if app_alt > 0:
        print(f"  Status: Visible above horizon")
    else:
        print(f"  Status: Below horizon")
    print("")

def main():
    parser = argparse.ArgumentParser(description="Calculate local sky coordinates for celestial bodies.")
    
    parser.add_argument("--city", type=str, default=None, help="Name of a known city (e.g., 'Montreal', 'Lhasa').")
    parser.add_argument("--lat", type=float, default=45.5017, help="Observer Latitude.")
    parser.add_argument("--lon", type=float, default=-73.5673, help="Observer Longitude.")
    
    parser.add_argument("--jd", type=float, default=None, help="Specific Julian Date (UTC).")
    parser.add_argument("--date", type=str, default=None, help="Date in YYYY-MM-DD format.")
    parser.add_argument("--time", type=str, default="00:00:00", help="Time in HH:MM:SS format.")
    
    parser.add_argument("--utc", action="store_true", help="Treat the --date and --time input as UTC.")
    parser.add_argument("--tz", type=str, default=None, help="Force a specific IANA timezone.")
    
    # NEW: JPL Flag
    parser.add_argument("--jpl", action="store_true", help="Fetch JPL Horizons data for line-by-line validation.")
    
    args = parser.parse_args()

    lat, lon = args.lat, args.lon
    tz_str = args.tz

    if args.city:
        city_key = args.city.lower()
        if city_key in CITIES:
            lat, lon, tz_str = CITIES[city_key]
        else:
            print(f"Error: City '{args.city}' not in registry. Available: {', '.join(CITIES.keys())}")
            sys.exit(1)

    local_tz = _get_timezone(lat, lon, tz_str)

    if args.jd is not None:
        jd_utc = args.jd
    elif args.date is not None:
        try:
            dt_naive = datetime.strptime(f"{args.date} {args.time}", "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            print(f"Error parsing date/time: {e}.")
            sys.exit(1)
            
        if args.utc:
            dt_aware = dt_naive.replace(tzinfo=timezone.utc)
        else:
            dt_aware = dt_naive.replace(tzinfo=local_tz)
            
        jd_utc = ts.datetime_utc_to_jd(dt_aware)
    else:
        dt_now = datetime.now(timezone.utc)
        jd_utc = ts.datetime_utc_to_jd(dt_now)

    jd_tt = ts.jd_utc_to_jd_tt(jd_utc)
    dt_utc_display = ts.jd_to_datetime_utc(jd_utc)
    dt_local_display = dt_utc_display.astimezone(local_tz)

    print(f"=== Local Sky Viewer ===")
    if args.city: print(f"City:       {args.city.title()}")
    print(f"Location:   Lat {lat:.4f}°, Lon {lon:.4f}°")
    print(f"Time Zone:  {local_tz.key if hasattr(local_tz, 'key') else local_tz}")
    print(f"Local Time: {dt_local_display.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"UTC Time:   {dt_utc_display.strftime('%Y-%m-%d %H:%M:%S')} (JD {jd_utc:.5f})")
    print(f"TT Scale:   JD {jd_tt:.5f}")
    print("========================\n")
    
    if args.jpl:
        print("Note: JPL Horizons API enabled. Fetching topocentric data (may take a few seconds)...\n")
    
    solar_system_bodies = [
        ("Sun", "sun"), ("Moon", "moon"), 
        ("Mercury", "mercury"), ("Venus", "venus"), 
        ("Mars", "mars"), ("Jupiter", "jupiter"), ("Saturn", "saturn")
    ]

    stellar_bodies = [
        ("Sirius", "sirius"), 
        ("Vega", "vega"), 
        ("Betelgeuse", "betelgeuse"),
        ("Spica", "spica")
    ]
    
    for display_name, body_name in solar_system_bodies:
        # A single, unified call for all solar system bodies
        geo = planets.geocentric_position(body_name, jd_tt)
            
        # 1. Geocentric Ecliptic to Geocentric Equatorial
        eq_geo = coords.ecliptic_to_equatorial(geo.L_true_deg, geo.B_true_deg, jd_tt)
        
        # 2. Geocentric to Topocentric (Applies Lunar Parallax, ignores distant planets)
        eq_top = coords.geocentric_to_topocentric(eq_geo, geo.R_true_au, lat, 0.0, jd_utc, lon)
        
        jpl_data = None
        if args.jpl and body_name in JPL_IDS:
            jpl_data = get_jpl_horizons_data(JPL_IDS[body_name], lat, lon, jd_utc)
            
        print_body(display_name, eq_top, jd_utc, lat, lon, jpl_data)

    for display_name, body_name in stellar_bodies:
            try:
                star_id = stars.get_star_id(body_name)
                
                # Get analytical geocentric coordinates
                eq_star = stars.get_star_equatorial(star_id, jd_tt)
                eq_star_formatted = coords.Equatorial(ra_deg=eq_star.ra_deg, dec_deg=eq_star.dec_deg)
                
                # Fetch JPL ground-truth if requested and available
                jpl_star_data = None
                if args.jpl and body_name in JPL_IDS:
                    jpl_star_data = get_jpl_horizons_data(JPL_IDS[body_name], lat, lon, jd_utc)
                    
                print_body(display_name, eq_star_formatted, jd_utc, lat, lon, jpl_star_data)
                
            except ValueError as e:
                # Catches if a star isn't in your COMMON_STARS dictionary in stars.py
                print(f"--- {display_name} ---\n  Status: Not in local star catalog.\n")
            except Exception as e:
                print(f"--- {display_name} ---\n  Status: Error calculating star data ({e})\n")

if __name__ == "__main__":
    main()