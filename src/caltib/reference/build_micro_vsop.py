#!/usr/bin/env python3
import urllib.request
import math
import sys
import pprint
import argparse
import os

PLANETS = ["mercury", "venus", "earth", "mars", "jupiter", "saturn"]

def fetch_vsop(planet, threshold):
    name_map = {"mercury": "mer", "venus": "ven", "earth": "ear", 
                "mars": "mar", "jupiter": "jup", "saturn": "sat"}
    
    ext = name_map[planet]
    
    urls = [
        f"https://raw.githubusercontent.com/ctdk/vsop87/master/VSOP87D.{ext}",
        f"ftp://cdsarc.cds.unistra.fr/pub/cats/VI/81/VSOP87D.{ext}"
    ]
    
    print(f"\nDownloading {planet.capitalize()}...")
    lines = None
    
    for url in urls:
        print(f"  -> Trying {url}")
        try:
            if url.startswith("http"):
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            else:
                req = url 
                
            with urllib.request.urlopen(req, timeout=10) as response:
                lines = response.read().decode('ascii').splitlines()
                
            print(f"  -> Success!")
            break
        except Exception as e:
            print(f"  -> Failed: {e}")
            
    if not lines:
        print(f"\nCRITICAL: Could not download data for {planet} from any mirror.")
        sys.exit(1)
        
    data = {"L": {}, "B": {}, "R": {}}
    for line in lines:
        if len(line) < 100: continue
        
        header = line[:5].strip()
        if not header.isdigit() or len(header) != 4: continue
        
        coord_idx = int(header[2]) # 1=L, 2=B, 3=R
        alpha = int(header[3])     # Power of tau
        
        if coord_idx == 1: coord = "L"
        elif coord_idx == 2: coord = "B"
        elif coord_idx == 3: coord = "R"
        else: continue
            
        parts = line.split()
        A, B, C = float(parts[-3]), float(parts[-2]), float(parts[-1])
        
        # Scale amplitude by maximum tau (approx 3 millennia) to ensure long-term stability
        max_amplitude = abs(A) * (3.0 ** alpha)
        
        if max_amplitude >= threshold:
            if alpha not in data[coord]:
                data[coord][alpha] = []
            data[coord][alpha].append((A, B, C))
            
    clean_data = {"L": {}, "B": {}, "R": {}}
    for coord in ["L", "B", "R"]:
        for alpha in data[coord]:
            clean_data[coord][int(alpha)] = tuple(data[coord][alpha])
            
    return clean_data

if __name__ == "__main__":
    # 1. Dynamically get the directory where this script lives
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    parser = argparse.ArgumentParser(description="Build Micro-VSOP planetary ephemeris library.")
    parser.add_argument("--threshold", type=float, default=1.5e-5,
                        help="Amplitude threshold in radians/AU for dropping terms (default: 1.5e-5).")
    
    # 2. Anchor the default file paths to the script's directory
    parser.add_argument("--template", type=str, 
                        default=os.path.join(script_dir, "planets_tmpl.py"),
                        help="Path to the template Python file.")
    parser.add_argument("--out", type=str, 
                        default=os.path.join(script_dir, "planets.py"),
                        help="Output file name.")
    args = parser.parse_args()

    try:
        with open(args.template, "r") as f:
            template_code = f.read()
    except FileNotFoundError:
        print(f"CRITICAL: Template file '{args.template}' not found.")
        sys.exit(1)

    all_data = {}
    for p in PLANETS:
        all_data[p] = fetch_vsop(p, args.threshold)
        
    planet_data_str = pprint.pformat(all_data, indent=4)
    
    if "{planet_data_str}" not in template_code:
        print(f"CRITICAL: The string '{{planet_data_str}}' was not found in {args.template}.")
        sys.exit(1)
        
    out_code = template_code.replace("{planet_data_str}", planet_data_str)
    
    with open(args.out, "w") as f:
        f.write(out_code)
        
    print(f"\nSuccessfully built {args.out} using threshold {args.threshold}!")