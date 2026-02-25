from __future__ import annotations
from typing import Any, Dict

from .registry import register_attribute, jdn

def weekday(info) -> Dict[str, Any]:
    # Convention: 0=Mon..6=Sun (ISO-like). Adjust offset if desired.
    return {"weekday": int((jdn(info) + 1) % 7)}

def sexagenary_year(info) -> Dict[str, Any]:
    # Placeholder: anchor offsets can be fixed later.
    y = info.tibetan.tib_year
    return {
        "animal_mod12": y % 12,
        "element_mod5": y % 5,
        "stem_mod10": y % 10,
    }

register_attribute("weekday", weekday)
register_attribute("sexagenary_year", sexagenary_year)
