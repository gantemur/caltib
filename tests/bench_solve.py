import time
from fractions import Fraction
import caltib

def main(argv=None):
    # Grab the heaviest float engine (L5 Day Engine)
    eng = caltib.get_calendar("l5")
    float_series = eng.day.elong_series  # The FloatFourierSeries instance
    
    # Generate 10,000 target tithis (approx 27 years)
    targets = [x for x in range(1, 10001)]
    
    print("Benchmarking Solvers (10,000 evaluations)...")
    
    # --- Benchmark 1: Picard (4 iterations) ---
    start_time = time.perf_counter()
    picard_results = []
    for x in targets:
        picard_results.append(float_series.picard_solve(float(x), iterations=4))
    picard_time = time.perf_counter() - start_time
    print(f"Picard (4 iters): {picard_time:.4f} seconds")
    
    # --- Benchmark 2: Newton-Raphson (2 iterations) ---
    start_time = time.perf_counter()
    nr_results = []
    for x in targets:
        nr_results.append(float_series.nr_solve(float(x), iterations=2))
    nr_time = time.perf_counter() - start_time
    print(f"Newton (2 iters): {nr_time:.4f} seconds")
    
    # --- Accuracy Check ---
    max_diff = max(abs(p - n) for p, n in zip(picard_results, nr_results))
    print(f"\nMax difference between solvers: {max_diff:.4e} days")
    if max_diff < 1e-6:
        print("-> ACCURACY VERIFIED: Both solvers converge to the same physical time.")
    
    # --- Verdict ---
    if nr_time < picard_time:
        print(f"\nVerdict: NEWTON is {(picard_time/nr_time):.2f}x FASTER.")
    else:
        print(f"\nVerdict: PICARD is {(nr_time/picard_time):.2f}x FASTER.")
        
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())