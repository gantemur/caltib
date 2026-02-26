from __future__ import annotations

from .core.engine import EngineRegistry
from .engines.trad import build_traditional_engines
from .engines.reform import build_reform_engines

def build_registry() -> EngineRegistry:
    engines = {}
    engines.update(build_traditional_engines())
    engines.update(build_reform_engines())
    return EngineRegistry(engines)
