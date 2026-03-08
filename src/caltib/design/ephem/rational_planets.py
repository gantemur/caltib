#!/usr/bin/env python3
import urllib.request
import math
import sys
import argparse
from typing import List, Tuple

PLANETS = ["mercury", "venus", "earth", "mars", "jupiter", "saturn"]

class Tee:
    """Intercepts standard output and writes it to both the terminal and a file."""
    def __init__(self, filename):
        self.file = open(filename, 'w')
        self.stdout = sys.stdout

    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)

    def flush(self):
        self.file.flush()
        self.stdout.flush()

def get_convergents(x: float, max_den: int = 100000) -> List[Tuple[int, int]]:
    """Generates the continued fraction convergents (p, q) for a real number x."""
    sign = -1 if x < 0 else 1
    x_abs = abs(x)
    convergents = []
    a = math.floor(x_abs)
    rem = x_abs - a
    
    h_prev1, k_prev1 = 1, 0
    h, k = a, 1

    while k <= max_den:
        convergents.append((sign * h, k))
        if rem < 1e-12:
            break
            
        inv = 1.0 / rem
        a = math.floor(inv)
        rem = inv - a
        
        h_new = a * h + h_prev1
        k_new = a * k + k_prev1
        
        h_prev1, k_prev1 = h, k
        h, k = h_new, k_new

    return convergents

def format_best_convergent(val: float, max_den: int) -> str:
    """Returns a cleanly formatted string of the best convergent and its error."""
    if val == 0.0:
        return "0/1 (Exact)"
    convs = get_convergents(val, max_den)
    if not convs:
        return f"{val} (Failed)"
    
    num, den = convs[-1]
    approx = num / den
    err = abs(val - approx)
    return f"{num}/{den} (Error: {err:.2e})"

def fetch_nano_vsop(planet: str, threshold: float) -> dict:
    """Fetches VSOP87D and extracts dominant anomalies + Mean Motion."""
    name_map = {"mercury": "mer", "venus": "ven", "earth": "ear", 
                "mars": "mar", "jupiter": "jup", "saturn": "sat"}
    ext = name_map[planet]
    
    url = f"https://raw.githubusercontent.com/ctdk/vsop87/master/VSOP87D.{ext}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            lines = response.read().decode('ascii').splitlines()
    except Exception as e:
        print(f"CRITICAL: Could not download data for {planet}: {e}")
        sys.exit(1)
        
    data = {"L": {0: [], 1: []}, "B": {0: []}, "R": {0: []}}
    for line in lines:
        if len(line) < 100: continue
        
        header = line[:5].strip()
        if not header.isdigit() or len(header) != 4: continue
        
        coord_idx = int(header[2]) 
        alpha = int(header[3])     
        
        # We only care about alpha 0 (periodic) and alpha 1 (linear mean motion)
        if alpha > 1: continue 
        
        coord = "L" if coord_idx == 1 else "B" if coord_idx == 2 else "R"
        parts = line.split()
        A, B, C = float(parts[-3]), float(parts[-2]), float(parts[-1])
        
        # 1. Capture dominant alpha=0 terms based on threshold
        if alpha == 0 and abs(A) >= threshold:
            data[coord][0].append((A, B, C))
            
        # 2. Rescue the Mean Motion from alpha=1 (Only Longitude, Frequency C is 0)
        if alpha == 1 and coord == "L" and abs(C) < 1e-6:
            data[coord][1].append((A, B, C))
            
    return data

def print_pseudocode():
    print("\n" + "="*80)
    print(" IMPLEMENTATION GUIDE & PSEUDO-CODE")
    print("="*80)
    print("To compute the Heliocentric coordinates:\n")
    print("1. CALCULATE TIME (TAU)")
    print("   tau = (JD - 2451545.0) / 365250.0  # Julian Millennia since J2000.0\n")
    
    print("2. SUM THE L, B, R SERIES")
    print("   For B and R, simply sum the alpha=0 terms:")
    print("   B = SUM[ A * cos(B_phase + C * tau) ]")
    print("   R = SUM[ A * cos(B_phase + C * tau) ]\n")
    
    print("   For Longitude (L), add the alpha=0 periodic terms TO the alpha=1 Mean Motion:")
    print("   L_periodic = SUM[ A * cos(B_phase + C * tau) ]  # From the alpha=0 block")
    print("   L_linear   = (A * cos(B_phase)) * tau           # From the alpha=1 block (C=0)")
    print("   L = L_periodic + L_linear\n")

    print("3. GEOCENTRIC TRANSLATION (METHOD A: Full 3D Rectangular)")
    print("   x = R * cos(B) * cos(L)")
    print("   y = R * cos(B) * sin(L)")
    print("   z = R * sin(B)")
    print("   ")
    print("   geo_x = target_x - earth_x")
    print("   geo_y = target_y - earth_y")
    print("   geo_z = target_z - earth_z")
    print("   ")
    print("   dist_xy = sqrt(geo_x^2 + geo_y^2)")
    print("   geo_L   = atan2(geo_y, geo_x)   # Geocentric Longitude")
    print("   geo_B   = atan2(geo_z, dist_xy) # Geocentric Latitude")
    print("   geo_R   = sqrt(dist_xy^2 + geo_z^2)\n")

    print("4. GEOCENTRIC TRANSLATION (METHOD B: Simplified 2D Spherical)")
    print("   If you assume planets perfectly orbit on the Ecliptic (B=0) and use")
    print("   constant mean distances (R=const), you can bypass 3D geometry entirely.")
    print("   This reduces the translation to a single trigonometric formula:\n")
    print("   geo_L = atan2( R_target * sin(L_target) - R_earth * sin(L_earth), ")
    print("                  R_target * cos(L_target) - R_earth * cos(L_earth) )\n")
    print("="*80 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Generate rational convergents for Nano-VSOP.")
    parser.add_argument("--threshold", type=float, default=0.05,
                        help="Amplitude threshold in radians/AU (default: 0.05).")
    parser.add_argument("--max-den", type=int, default=10000,
                        help="Maximum denominator for rational fractions.")
    parser.add_argument("--out", type=str, default=None,
                        help="Optional filename to save the console output.")
    args = parser.parse_args()

    # Enable dual-logging if an output file is provided
    if args.out:
        sys.stdout = Tee(args.out)

    print(f"Building Nano-VSOP Designer...")
    print(f"Threshold: {args.threshold} (Only dominant terms retained)")
    print(f"Max Denom: {args.max_den}\n")

    for p in PLANETS:
        data = fetch_nano_vsop(p, args.threshold)
        
        print("-" * 80)
        print(f" {p.upper()} (Showing rational approximations for terms > {args.threshold})")
        print("-" * 80)
        
        for coord in ["L", "B", "R"]:
            if coord == "L":
                print(f"  Coordinate L (Longitude):")
                # Print Mean Motion first
                mean_motion = data["L"].get(1, [])
                if mean_motion:
                    A, B, C = mean_motion[0]
                    # Since C=0, A*cos(B) is the linear multiplier K
                    K = A * math.cos(B)
                    print(f"    MEAN MOTION (Linear Term):")
                    print(f"      Rate (K): {K:12.6f} rad/millennium => {format_best_convergent(K, args.max_den)}")
                
                # Print alpha=0 periodic terms
                terms = data["L"].get(0, [])
                if terms:
                    print(f"    PERIODIC TERMS ({len(terms)} dominant terms):")
                    for i, (A, B, C) in enumerate(terms):
                        print(f"      Term {i+1}: A={format_best_convergent(A, args.max_den):<15} | B={format_best_convergent(B, args.max_den):<15} | C={format_best_convergent(C, args.max_den)}")
                else:
                    print("    [No periodic terms met the threshold]")
            else:
                terms = data[coord].get(0, [])
                if not terms:
                    print(f"  Coordinate {coord}: [No periodic terms met the threshold]")
                    continue
                    
                print(f"  Coordinate {coord} ({len(terms)} dominant terms):")
                for i, (A, B, C) in enumerate(terms):
                    print(f"    Term {i+1}: A={format_best_convergent(A, args.max_den):<15} | B={format_best_convergent(B, args.max_den):<15} | C={format_best_convergent(C, args.max_den)}")
        print()
        
    print_pseudocode()

if __name__ == "__main__":
    main()