#!/usr/bin/env python3
import urllib.request
import argparse
import sys
import os

TEMPLATE = """\
from __future__ import annotations
from dataclasses import dataclass
import math
from . import astro_args as aa

@dataclass(frozen=True)
class Star:
    hip_id: int
    mag: float
    ra_j2000_deg: float
    dec_j2000_deg: float
    pm_ra_mas_yr: float
    pm_dec_mas_yr: float

# Automatically generated catalog from Hipparcos (I/239)
# Filter: Magnitude <= {max_mag}
# Total Stars: {star_count}

STAR_CATALOG = {
{stars_dict_str}
}
"""

def fetch_hipparcos_stars(max_mag: float) -> list[tuple]:
    """Queries VizieR for Hipparcos stars brighter than max_mag."""
    url = (f"https://vizier.cds.unistra.fr/viz-bin/asu-tsv?"
           f"-source=I/239/hip_main&"
           f"-out=HIP,Vmag,RAICRS,DEICRS,pmRA,pmDE&"
           f"-out.max=unlimited&"
           f"Vmag=%3C{max_mag}")
    
    print(f"URL: {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            lines = response.read().decode('utf-8').splitlines()
    except Exception as e:
        print(f"CRITICAL: Failed to download star data: {e}")
        sys.exit(1)
        
    stars = []
    for line in lines:
        parts = line.split('\t')
        
        # Aggressive bypass: If the line doesn't have 6 columns or the first column isn't a number, skip.
        if len(parts) < 6 or not parts[0].strip().isdigit():
            continue
            
        try:
            hip = int(parts[0].strip())
            mag = float(parts[1].strip())
            ra = float(parts[2].strip())
            dec = float(parts[3].strip())
            
            # Missing proper motion data falls back to 0.0
            pmra = float(parts[4].strip()) if parts[4].strip() else 0.0
            pmdec = float(parts[5].strip()) if parts[5].strip() else 0.0
            
            stars.append((hip, mag, ra, dec, pmra, pmdec))
        except ValueError:
            continue
            
    return stars

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    parser = argparse.ArgumentParser(description="Build stellar catalog from VizieR.")
    parser.add_argument("--mag", type=float, default=3.0,
                        help="Maximum visual magnitude (Default: 3.0).")
    parser.add_argument("--template", type=str, 
                        default=os.path.join(script_dir, "stars_tmpl.py"),
                        help="Path to the template Python file.")
    parser.add_argument("--out", type=str, 
                        default=os.path.join(script_dir, "stars.py"),
                        help="Output Python file name.")
    args = parser.parse_args()

    try:
        with open(args.template, "r") as f:
            template_code = f.read()
    except FileNotFoundError:
        print(f"CRITICAL: Template file '{args.template}' not found.")
        sys.exit(1)

    print(f"Querying CDS VizieR for stars brighter than mag {args.mag}...")
    stars = fetch_hipparcos_stars(args.mag)
    
    if not stars:
        print("Error: No stars returned from query. The TSV parsing failed or VizieR is down.")
        sys.exit(1)
        
    print(f"Successfully retrieved {len(stars)} stars.")
    
    dict_lines = []
    for s in stars:
        hip, mag, ra, dec, pmra, pmdec = s
        dict_lines.append(
            f"    {hip}: Star(hip_id={hip}, mag={mag}, ra_j2000_deg={ra}, "
            f"dec_j2000_deg={dec}, pm_ra_mas_yr={pmra}, pm_dec_mas_yr={pmdec}),"
        )
        
    stars_dict_str = "\n".join(dict_lines)
    
    out_code = template_code.replace("{stars_dict_str}", stars_dict_str)
    
    with open(args.out, "w") as f:
        f.write(out_code)
        
    print(f"Successfully built {args.out}!")