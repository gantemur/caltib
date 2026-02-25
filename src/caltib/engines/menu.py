from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Any, Dict, Literal

from ..core.types import EngineId
from ..core.engine import CalendarEngine
from ._rational import RationalSpec, build_rational_engine
from ._fp import FPSpec, build_fp_engine

EngineKind = Literal["rational", "fp", "ephemeris"]

@dataclass(frozen=True)
class EngineSpec:
    kind: EngineKind
    id: EngineId
    payload: Any  # RationalSpec | FPSpec | ...

    @staticmethod
    def like(name: str) -> "EngineSpec":
        from .specs import ALL_SPECS
        if name not in ALL_SPECS:
            raise KeyError(f"Unknown base spec '{name}'. Available: {sorted(ALL_SPECS)}")
        return ALL_SPECS[name]

    def tweak(self, **kwargs) -> "EngineSpec":
        return replace(self, payload=replace(self.payload, **kwargs))

def make_engine(spec: EngineSpec) -> CalendarEngine:
    if spec.kind == "rational":
        return build_rational_engine(spec.payload)
    if spec.kind == "fp":
        return build_fp_engine(spec.payload)
    raise NotImplementedError("Ephemeris engines are optional; see engines/l6.")

def standard_trad_specs() -> Dict[str, EngineSpec]:
    from .specs import TRAD_SPECS
    return dict(TRAD_SPECS)

def standard_reform_specs() -> Dict[str, EngineSpec]:
    from .specs import REFORM_SPECS
    return dict(REFORM_SPECS)
