from __future__ import annotations

import math
from dataclasses import replace
from datetime import date
from typing import Any, Dict, List, Optional, Sequence
from fractions import Fraction

from .core.engine import CalendarEngine, EngineRegistry
from .core.types import DayInfo, TibetanDate, EngineSpec 
from .core.time import from_jdn
from .attributes.registry import compute_attributes
from .engines.astro.sunrise import LocationRational
from .engines.factory import make_engine as _make_engine

JD_J2000 = Fraction(2451545, 1)
_registry: Optional[EngineRegistry] = None

def set_registry(reg: EngineRegistry) -> None:
    global _registry
    _registry = reg

def _reg() -> EngineRegistry:
    if _registry is None:
        raise RuntimeError("Engine registry not initialized")
    return _registry

def list_engines() -> List[str]:
    return _reg().list()

def engine_info(engine: str) -> Dict[str, Any]:
    return _reg().get(engine).info()

def day_info(
    d: date,
    *,
    engine: str = "phugpa",
    attributes: Sequence[str] = (),
    debug: bool = False,
) -> DayInfo:
    info = _reg().get(engine).day_info(d, debug=debug)
    if attributes:
        attrs = compute_attributes(info, attributes)
        info = replace(info, attributes=attrs)
    return info

def to_gregorian(t: TibetanDate, *, engine: Optional[str] = None, policy: str = "all") -> List[date]:
    eng = _reg().get(engine) if engine is not None else _reg().get(t.engine.name)
    return eng.to_gregorian(t, policy=policy)

def explain(d: date, *, engine: str = "phugpa") -> Dict[str, Any]:
    return _reg().get(engine).explain(d)

def get_calendar(name: str, *, location: Optional[LocationRational] = None) -> CalendarEngine:
    from .engines.specs import ALL_SPECS
    if name not in ALL_SPECS:
        raise KeyError(f"Unknown engine spec '{name}'")
    spec = ALL_SPECS[name]
    
    if location is not None:
        if hasattr(spec.payload.day_params, 'location'):
            day_params = replace(spec.payload.day_params, location=location)
            spec = spec.tweak(day_params=day_params)
        else:
            raise ValueError(f"Calendar '{name}' does not support location overrides.")

    return _make_engine(spec)

def make_engine(spec: EngineSpec) -> CalendarEngine:
    return _make_engine(spec)

def register_engine(name: str, engine: CalendarEngine, *, overwrite: bool = False) -> None:
    _reg().register(name, engine, overwrite=overwrite)

# ============================================================
# Helpers for API Diagnostics
# ============================================================

def _get_n_m(eng: CalendarEngine, Y: int, M: int, is_leap: bool) -> int:
    """Helper to resolve the specific lunation index from the new get_lunations API."""
    lunations = eng.month.get_lunations(Y, M)
    if len(lunations) == 1:
        return lunations[0]
    if eng.leap_labeling == "first_is_leap":
        return lunations[0] if is_leap else lunations[1]
    return lunations[1] if is_leap else lunations[0]

# ============================================================
# Month-level debug API
# ============================================================

def intercalation_index(Y: int, M: int, *, engine: str = "phugpa") -> int:
# This works only for traditional engines
    eng = _reg().get(engine)
    return eng.trad.intercalation_index(Y, M)

def month_info(Y: int, M: int, *, engine: str = "phugpa", debug: bool = False) -> Dict[str, Any]:
    eng = _reg().get(engine)
    if hasattr(eng.month, "debug_label"):
        out = eng.month.debug_label(Y, M)
        if debug:
            out["engine"] = eng.info()
        return out
    raise TypeError(f"Engine '{engine}' does not expose month-layer info")

def month_from_n(n: int, *, engine: str = "phugpa", debug: bool = False) -> Dict[str, Any]:
    eng = _reg().get(engine)
    if hasattr(eng.month, "debug_lunation"):
        out = eng.month.debug_lunation(n)
        if debug:
            out["engine"] = eng.info()
        return out
    raise TypeError(f"Engine '{engine}' does not expose month-layer info")

def months_in_year(Y: int, *, engine: str = "phugpa", debug: bool = False):
    eng = _reg().get(engine)
    me = eng.month
    out = []
    
    for M in range(1, 13):
        trig = me.is_trigger_label(Y, M)
        insts = [True, False] if trig and eng.leap_labeling == "first_is_leap" else ([False, True] if trig else [False])

        for is_leap in insts:
            n = _get_n_m(eng, Y, M, is_leap)
            rec = {
                "Y": Y, "M": M, "is_leap_month": is_leap, "n": n, "trigger": trig,
                "I": me.intercalation_index(Y, M),
                "I_int": me.intercalation_index_internal(Y, M),
            }
            if hasattr(me, "intercalation_index_traditional"):
                rec["I_trad_ext"] = me.intercalation_index_traditional(Y, M, wrap="extended")
                rec["I_trad_mod"] = me.intercalation_index_traditional(Y, M, wrap="mod")
            out.append(rec)
    return out

def days_in_month(Y: int, M: int, *, is_leap_month: bool = False, engine: str = "phugpa"):
    eng = _reg().get(engine)
    n_m = _get_n_m(eng, Y, M, is_leap_month)
    n_d = n_m + eng.delta_k
    
    # Use the orchestrator's civil map instead of the old DayEngine hits
    month_map = eng._build_civil_month(n_d)
    
    rows = []
    for jdn, info in sorted(month_map.items()):
        # Calculate skipped labels if needed (for display consistency)
        skipped_labels = [info["day"] - 1] if info["skipped"] else []
        rows.append({
            "date": from_jdn(jdn),
            "jdn": jdn,
            "tithi": info["day"],
            "occ": 2 if info["repeated"] else 1,
            "repeated": info["repeated"],
            "skipped_labels": skipped_labels,
        })
    return rows

def true_date_dn(d: int, n: int, *, engine: str = "phugpa"):
    """Returns absolute true_date (Days since J2000.0) via continuous x."""
    eng = _reg().get(engine)
    x = Fraction(30 * n + d, 1)
    return eng.day.true_date(x)

def end_jd_dn(d: int, n: int, *, engine: str = "phugpa") -> int:
    """Returns absolute Julian Day Number via continuous x."""
    eng = _reg().get(engine)
    x = Fraction(30 * n + d, 1)
    return math.floor(eng.day.true_date(x) + JD_J2000)

def civil_month_n(n: int, *, engine: str = "phugpa") -> List[Dict[str, Any]]:
    """Diagnostic: list civil day records for a specific lunation n."""
    eng = _reg().get(engine)
    # Convert month engine n to day engine n_d
    n_d = n + eng.delta_k
    month_map = eng._build_civil_month(n_d)
    
    out = []
    for jdn, info in sorted(month_map.items()):
        out.append({
            "jd": jdn,
            "label": info["day"],
            "repeated": info["repeated"],
            "skipped": info["skipped"],
            "date": from_jdn(jdn)
        })
    return out

def month_bounds(Y: int, M: int, *, is_leap_month: bool = False, engine: str = "phugpa", debug: bool = False, as_date: bool = True) -> dict:
    eng = _reg().get(engine)
    n_m = _get_n_m(eng, Y, M, is_leap_month)
    n_d = n_m + eng.delta_k

    first_jdn = end_jd_dn(30, n_d - 1, engine=engine) + 1
    last_jdn = end_jd_dn(30, n_d, engine=engine)

    out = {"Y": Y, "M": M, "is_leap_month": is_leap_month, "n": n_m, "first_jdn": first_jdn, "last_jdn": last_jdn}
    if as_date:
        out["first_date"] = from_jdn(first_jdn)
        out["last_date"] = from_jdn(last_jdn)
    return out

def new_year_day(Y: int, *, engine: str = "phugpa", debug: bool = False, as_date: bool = True) -> dict:
    eng = _reg().get(engine)
    if eng.leap_labeling == "first_is_leap":
        Y_last, M_last, L_last = Y - 1, 12, False
    else:
        n1 = _get_n_m(eng, Y, 1, False)
        Y_last, M_last, leap_state = eng.month.label_from_lunation(n1 - 1)
        L_last = (leap_state == 2)

    n_last = _get_n_m(eng, Y_last, M_last, L_last)
    n_last_d = n_last + eng.delta_k
    jdn = end_jd_dn(30, n_last_d, engine=engine) + 1

    out = {"Y": Y, "jdn": jdn, "prev_month": {"Y": Y_last, "M": M_last, "is_leap_month": L_last}, "n_last": n_last}
    if as_date:
        out["date"] = from_jdn(jdn)
    return out

def prev_month(Y: int, M: int, *, is_leap_month: bool = False, engine: str = "phugpa", debug: bool = False) -> dict:
    eng = _reg().get(engine)
    n = _get_n_m(eng, Y, M, is_leap_month)
    Y2, M2, leap_state = eng.month.label_from_lunation(n - 1)
    
    L2 = False
    if leap_state == 1: L2 = (eng.leap_labeling == "first_is_leap")
    elif leap_state == 2: L2 = (eng.leap_labeling == "second_is_leap")

    return {"Y": Y2, "M": M2, "is_leap_month": L2, "n": n - 1}

def next_month(Y: int, M: int, *, is_leap_month: bool = False, engine: str = "phugpa", debug: bool = False) -> dict:
    eng = _reg().get(engine)
    n = _get_n_m(eng, Y, M, is_leap_month)
    Y2, M2, leap_state = eng.month.label_from_lunation(n + 1)
    
    L2 = False
    if leap_state == 1: L2 = (eng.leap_labeling == "first_is_leap")
    elif leap_state == 2: L2 = (eng.leap_labeling == "second_is_leap")

    return {"Y": Y2, "M": M2, "is_leap_month": L2, "n": n + 1}

def first_day_of_month(Y: int, M: int, *, is_leap_month: bool = False, engine: str = "phugpa") -> date:
    b = month_bounds(Y, M, is_leap_month=is_leap_month, engine=engine, debug=False)
    return b["first_date"]

def last_day_of_month(Y: int, M: int, *, is_leap_month: bool = False, engine: str = "phugpa") -> date:
    b = month_bounds(Y, M, is_leap_month=is_leap_month, engine=engine, debug=False)
    return b["last_date"]