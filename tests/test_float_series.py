import math
from typing import Dict, Tuple
from dataclasses import dataclass

from caltib.engines.astro.float_series import FloatTermDef, FloatFundArg, build_collapsed_terms

def test_build_collapsed_terms_drift_routing():
    """Verifies that the include_drift flag correctly separates static and dynamic terms."""
    
    # 1. Mock Fundamental Arguments (dummy phases for testing)
    mock_funds: Dict[str, FloatFundArg] = {
        "d":  FloatFundArg(c0=0.1, c1=10.0),
        "m":  FloatFundArg(c0=0.2, c1=20.0),
        "mp": FloatFundArg(c0=0.3, c1=30.0),
        "f":  FloatFundArg(c0=0.4, c1=40.0),
    }
    keys = ("d", "m", "mp", "f")
    
    # 2. Mock Table (3 terms: 1 static, 2 with defined drifts)
    mock_table = (
        (0, 0, 1, 0, 1000.0),          # Term 0: No drift defined
        (0, 1, 0, 0, 2000.0, 50.0),    # Term 1: Drift defined (+50.0)
        (2, 0, 0, 0, 3000.0, -10.0),   # Term 2: Drift defined (-10.0)
    )
    
    # --- TEST A: Default (include_drift = False) ---
    static_a, dynamic_a = build_collapsed_terms(
        funds=mock_funds, keys=keys, rows=mock_table, include_drift=False, amp1_scale=1.0
    )
    
    # All 3 terms should be routed to static. Dynamic should be empty.
    assert len(static_a) == 3, "Failed: Expected 3 static terms when drift is disabled."
    assert len(dynamic_a) == 0, "Failed: Expected 0 dynamic terms when drift is disabled."
    
    # Ensure the amp1 property was zeroed out
    assert static_a[1].amp1 == 0.0, "Failed: amp1 should be 0.0 when drift is disabled."
    
    # --- TEST B: Active (include_drift = True) ---
    static_b, dynamic_b = build_collapsed_terms(
        funds=mock_funds, keys=keys, rows=mock_table, include_drift=True, amp1_scale=1.0
    )
    
    # Term 0 goes to static. Terms 1 and 2 go to dynamic.
    assert len(static_b) == 1, "Failed: Expected 1 static term when drift is active."
    assert len(dynamic_b) == 2, "Failed: Expected 2 dynamic terms when drift is active."
    
    # Verify the dynamic amplitudes were preserved correctly
    assert dynamic_b[0].amp == 2000.0
    assert dynamic_b[0].amp1 == 50.0
    
    assert dynamic_b[1].amp == 3000.0
    assert dynamic_b[1].amp1 == -10.0
    
    print("Success: build_collapsed_terms correctly routes static and dynamic tuples!")

# Run the test
if __name__ == "__main__":
    test_build_collapsed_terms_drift_routing()