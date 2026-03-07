#!/usr/bin/env python3
from caltib.reference import events
from caltib.reference import time_scales as ts
from datetime import datetime, timezone

def main():
    # Base configuration
    lat = 45.5017
    lon = -73.5673
    
    # Let's start the search from today
    dt_now = datetime.now(timezone.utc)
    jd_start = ts.datetime_utc_to_jd(dt_now)
    
    print(f"Starting Search from JD: {jd_start:.4f}\n")
    
    # 1. Next Sunset (Applying atmospheric refraction, looking for setting direction)
    jd_set = events.find_altitude_event("sun", jd_start, lat, lon, target_alt_deg=-0.833, apply_refraction=False, rising=False)
    if jd_set:
        print(f"Next Sunset (UTC):       {ts.jd_to_datetime_utc(jd_set)}")
        
    # 2. Next Vernal Equinox (Sun Ecliptic Longitude = 0)
    jd_eq = events.find_solar_longitude(jd_start, 0.0)
    if jd_eq:
        print(f"Next Vernal Equinox:     {ts.jd_to_datetime_utc(jd_eq)}")
        
    # 3. Next Solar Eclipse
    eclipse = events.find_next_eclipse(jd_start, "solar")
    if eclipse:
        print(f"\nNext Solar Eclipse:      {ts.jd_to_datetime_utc(eclipse['jd_utc'])}")
        print(f"  Max Moon Latitude:     {eclipse['moon_lat_deg']:.4f}°")
        print(f"  Rough Central Path:    {eclipse['rough_path_center']['lat_deg']:.2f}° N, {eclipse['rough_path_center']['lon_deg']:.2f}° E")

if __name__ == "__main__":
    main()