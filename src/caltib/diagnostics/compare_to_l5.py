from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, List

import caltib

def compare_engines(
    engine_a: str,
    engine_b: str = "reform-l5",
    start: date = date(1900,1,1),
    days: int = 365,
    stride: int = 7,
) -> Dict[str, object]:
    """Compare two engines on sampled dates (engine-b often L5)."""
    mismatches: List[str] = []
    d = start
    for _ in range(0, days, stride):
        a = caltib.day_info(d, engine=engine_a).tibetan
        b = caltib.day_info(d, engine=engine_b).tibetan
        if (a.tib_year, a.month_no, a.is_leap_month, a.tithi, a.occ) != (b.tib_year, b.month_no, b.is_leap_month, b.tithi, b.occ):
            mismatches.append(f"{d}: {engine_a}={a} vs {engine_b}={b}")
        d += timedelta(days=stride)
    return {"engine_a": engine_a, "engine_b": engine_b, "start": str(start), "days": days, "stride": stride, "n_mismatch": len(mismatches), "examples": mismatches[:50]}
