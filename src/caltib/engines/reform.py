from __future__ import annotations
from .menu import standard_reform_specs, make_engine

def build_reform_engines():
    engines = {name: make_engine(spec) for name, spec in standard_reform_specs().items()}

    # Optional L6 (ephemeris-backed). Only register if extras are available.
    try:
        from .l6.engine import build_l6_engine  # noqa: F401
    except Exception:
        return engines

    try:
        engines["reform-l6"] = build_l6_engine()
    except Exception:
        # Keep it unavailable unless configured (e.g., ephemeris path)
        pass

    return engines
