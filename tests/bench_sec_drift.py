import math
from typing import Dict
from dataclasses import dataclass

# Assuming these are available in your engine
from caltib.engines.astro.float_series import (
    FloatTermDef, FloatFundArg, FloatFourierSeries, build_collapsed_terms
)
from caltib.engines.astro.fp_math import QuarterWavePolynomial

def run_millennium_benchmark():
    print("--- 1000-Year Secular Drift Benchmark ---")
    
    # 1. Mock the Sun's Fundamental Arguments for the benchmark
    # Base solar motion (B) is ~0.9856 deg/day (0.0027379 turns/day)
    base_motion_turns = 0.985647 / 360.0
    mock_funds = {
        "M": FloatFundArg(c0=0.0, c1=base_motion_turns),
    }
    
    # The 1-Term Solar Table (with the -4817 microdeg/cy drift)
    mock_solar_table = (
        (1, 1914602.0, -4817.0), # (m, amp, drift_per_cy)
    )
    
    # 2. Custom compiler block for the benchmark
    static_terms = []
    dynamic_terms = []
    for m, amp, drift in mock_solar_table:
        term = FloatTermDef(
            amp=amp * (1e-6 / 360.0),
            c0=0.0,
            c1=mock_funds["M"].c1 * m,
            amp1=(drift * (1e-6 / 360.0)) / 36525.0  # Scale century drift to daily drift
        )
        static_terms.append(term)
        dynamic_terms.append(term) # We'll manually pass this to the dynamic engine
        
    # Dummy polynomial (just passes the value through math.sin for the test)
    class MockPoly:
        def eval_normalized_turn(self, phase): return math.sin(phase * 2 * math.pi)
        def cos_normalized_turn(self, phase): return math.cos(phase * 2 * math.pi)
        
    # 3. Build the two engines
    # Engine A: Static (No drift, simulates L3 or include_drift=False)
    engine_static = FloatFourierSeries(
        A=0.0, B=base_motion_turns, C=0.0,
        static_terms=tuple(static_terms), dynamic_terms=(),
        poly=MockPoly()
    )
    
    # Engine B: Dynamic (Includes the T-drift)
    engine_dynamic = FloatFourierSeries(
        A=0.0, B=base_motion_turns, C=0.0,
        static_terms=(), dynamic_terms=tuple(dynamic_terms),
        poly=MockPoly()
    )
    
    # 4. The Benchmark: Year 1000 CE (approx -365,250 days from J2000)
    # We want to solve for when the True Sun reaches x0 = -1000.0 turns 
    target_turns = -1000.25
    t_guess = target_turns / base_motion_turns # ~ -365250 days
    
    # Solve using Newton-Raphson for ultra-precision
    t_static = engine_static.nr_solve(x0=target_turns, iterations=5, t_init=t_guess)
    t_dynamic = engine_dynamic.nr_solve(x0=target_turns, iterations=5, t_init=t_guess)
    
    # 5. The Results
    delta_days = t_dynamic - t_static
    delta_minutes = delta_days * 1440.0
    
    print(f"Target Event:     Sun reaches {target_turns} turns (~Year 1000 CE)")
    print(f"Static Engine:    {t_static:.5f} days from J2000")
    print(f"Dynamic Engine:   {t_dynamic:.5f} days from J2000")
    print("-" * 40)
    print(f"Time Difference:  {delta_minutes:+.2f} minutes")
    print("If this is ~70 minutes, your deep-time physics are absolutely perfect.")

if __name__ == "__main__":
    run_millennium_benchmark()