from __future__ import annotations
from caltib.core.engine import EngineRegistry
from caltib.engines.specs import ALL_SPECS
from caltib.engines.factory import make_engine

def build_registry() -> EngineRegistry:
    engines = {}
    for name, spec in ALL_SPECS.items():
        engines[name] = make_engine(spec)
    return EngineRegistry(engines)
