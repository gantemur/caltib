from __future__ import annotations
from .menu import standard_trad_specs, make_engine

def build_traditional_engines():
    specs = standard_trad_specs()
    return {name: make_engine(spec) for name, spec in specs.items()}
