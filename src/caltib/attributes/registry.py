from __future__ import annotations
from typing import Any, Callable, Dict, Sequence

from ..core.types import DayInfo
from ..core.time import to_jdn

AttrFunc = Callable[[DayInfo], Dict[str, Any]]
_REGISTRY: Dict[str, AttrFunc] = {}

def register_attribute(name: str, fn: AttrFunc) -> None:
    _REGISTRY[name] = fn

def compute_attributes(info: DayInfo, names: Sequence[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name in names:
        if name not in _REGISTRY:
            raise KeyError(f"Unknown attribute '{name}'. Available: {sorted(_REGISTRY)}")
        out.update(_REGISTRY[name](info))
    return out

# helper for attribute implementations
def jdn(info: DayInfo) -> int:
    return to_jdn(info.civil_date)
