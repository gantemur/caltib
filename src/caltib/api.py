from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from .core.engine import CalendarEngine, EngineRegistry
from .core.types import DayInfo, TibetanDate
from .core.time import from_jdn
from .attributes.registry import compute_attributes
from .engines.menu import EngineSpec, make_engine as _make_engine

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


# ---- power users ----
def make_engine(spec: EngineSpec) -> CalendarEngine:
    return _make_engine(spec)


def register_engine(name: str, engine: CalendarEngine, *, overwrite: bool = False) -> None:
    _reg().register(name, engine, overwrite=overwrite)


# ============================================================
# Month-level debug API
# ============================================================

def month_info(Y: int, M: int, *, engine: str = "phugpa", debug: bool = False) -> Dict[str, Any]:
    eng = _reg().get(engine)
    if hasattr(eng, "month_info"):
        return eng.month_info(Y, M, debug=debug)  # type: ignore[attr-defined]
    # fallback
    if hasattr(eng, "month"):
        out = eng.month.debug_label(Y, M)  # type: ignore[attr-defined]
        if debug:
            out["engine"] = eng.info()
        return out
    raise TypeError(f"Engine '{engine}' does not expose month-layer info")


def month_from_n(n: int, *, engine: str = "phugpa", debug: bool = False) -> Dict[str, Any]:
    eng = _reg().get(engine)
    if hasattr(eng, "month_from_n"):
        return eng.month_from_n(n, debug=debug)  # type: ignore[attr-defined]
    if hasattr(eng, "month"):
        out = eng.month.debug_true_month(n)  # type: ignore[attr-defined]
        if debug:
            out["engine"] = eng.info()
        return out
    raise TypeError(f"Engine '{engine}' does not expose month-layer info")

def months_in_year(Y: int, *, engine: str = "phugpa", debug: bool = False):
    eng = _reg().get(engine)
    if not hasattr(eng, "month"):
        raise TypeError(f"Engine '{engine}' does not expose month-layer info")
    me = eng.month

    out = []
    for M in range(1, 13):
        trig = me.is_trigger_label(Y, M)
        # determine the order of instances for this label
        if trig:
            if me.p.leap_labeling == "first_is_leap":
                insts = [True, False]
            else:
                insts = [False, True]
        else:
            insts = [False]

        for is_leap in insts:
            n = me.true_month(Y, M, is_leap_month=is_leap)
            rec = {
                "Y": Y,
                "M": M,
                "is_leap_month": is_leap,
                "n": n,
                "trigger": trig,
                "I": me.intercalation_index(Y, M),
                "I_int": me.intercalation_index_internal(Y, M),
            }
            if hasattr(me, "intercalation_index_traditional"):
                rec["I_trad_ext"] = me.intercalation_index_traditional(Y, M, wrap="extended")
                rec["I_trad_mod"] = me.intercalation_index_traditional(Y, M, wrap="mod")
            if debug and hasattr(eng, "month_info"):
                rec["debug"] = eng.month_info(Y, M, debug=True)
            out.append(rec)
    return out


def days_in_month(
    Y: int,
    M: int,
    *,
    is_leap_month: bool = False,
    engine: str = "phugpa",
):
    eng = _reg().get(engine)
    if not (hasattr(eng, "month") and hasattr(eng, "day")):
        raise TypeError(f"Engine '{engine}' does not expose month/day layers")

    n = eng.month.true_month(Y, M, is_leap_month=is_leap_month)

    # reconstruct which tithis ended on each civil day (needed to explain skips)
    ends = {}
    for d in range(1, 31):
        j = eng.day.end_jd(d, n)   # trad mode only
        ends.setdefault(j, []).append(d)

    cm = eng.day.civil_month(n)

    rows = []
    for cd in cm:
        ended = ends.get(cd.jd, [])
        skipped_labels = ended[:-1] if len(ended) >= 2 else []
        rows.append({
            "date": from_jdn(cd.jd),
            "jdn": cd.jd,
            "tithi": cd.label,
            "occ": 2 if cd.repeated else 1,
            "repeated": cd.repeated,
            "skipped_labels": skipped_labels,
        })
    return rows

def true_date_dn(d: int, n: int, *, engine: str = "phugpa"):
    """Trad-mode diagnostic: return true_date(d,n) as Fraction."""
    eng = _reg().get(engine)
    return eng.day.true_date(d, n)

def end_jd_dn(d: int, n: int, *, engine: str = "phugpa") -> int:
    """Trad-mode diagnostic: return floor(true_date(d,n))."""
    eng = _reg().get(engine)
    return eng.day.end_jd(d, n)

def civil_month_n(n: int, *, engine: str = "phugpa"):
    """Trad-mode diagnostic: list CivilDay records for lunation n."""
    eng = _reg().get(engine)
    return eng.day.civil_month(n)

def month_bounds(
    Y: int,
    M: int,
    *,
    is_leap_month: bool = False,
    engine: str = "phugpa",
    debug: bool = False,
    as_date: bool = True,
) -> dict:
    """
    Bounds of the civil month, plus the true-month index n.

    If as_date=False, do not convert JDN to datetime.date (needed for years < 1).
    """
    eng = _reg().get(engine)
    n = eng.month.true_month(Y, M, is_leap_month=is_leap_month)

    first_jdn = eng.day.end_jd(30, n - 1) + 1
    last_jdn = eng.day.end_jd(30, n)

    out = {
        "Y": Y,
        "M": M,
        "is_leap_month": is_leap_month,
        "n": n,
        "first_jdn": first_jdn,
        "last_jdn": last_jdn,
    }

    if as_date:
        out["first_date"] = from_jdn(first_jdn)
        out["last_date"] = from_jdn(last_jdn)

    if debug:
        out["engine"] = eng.info()
        if hasattr(eng, "month_from_n"):
            out["month_from_n"] = eng.month_from_n(n, debug=True)
    return out


def prev_month(
    Y: int,
    M: int,
    *,
    is_leap_month: bool = False,
    engine: str = "phugpa",
    debug: bool = False,
) -> dict:
    """
    Previous lunar month label (date-based via n-1).

    Returns {Y,M,is_leap_month,n} for the previous month.
    """
    eng = _reg().get(engine)
    n = eng.month.true_month(Y, M, is_leap_month=is_leap_month)
    n_prev = n - 1
    Y2, M2, L2 = eng.month.label_from_true_month(n_prev)

    out = {"Y": Y2, "M": M2, "is_leap_month": L2, "n": n_prev}
    if debug:
        out["engine"] = eng.info()
        out["month_from_n"] = eng.month_from_n(n_prev, debug=True) if hasattr(eng, "month_from_n") else None
    return out


def next_month(
    Y: int,
    M: int,
    *,
    is_leap_month: bool = False,
    engine: str = "phugpa",
    debug: bool = False,
) -> dict:
    """
    Next lunar month label (date-based via n+1).

    Returns {Y,M,is_leap_month,n} for the next month.
    """
    eng = _reg().get(engine)
    n = eng.month.true_month(Y, M, is_leap_month=is_leap_month)
    n_next = n + 1
    Y2, M2, L2 = eng.month.label_from_true_month(n_next)

    out = {"Y": Y2, "M": M2, "is_leap_month": L2, "n": n_next}
    if debug:
        out["engine"] = eng.info()
        out["month_from_n"] = eng.month_from_n(n_next, debug=True) if hasattr(eng, "month_from_n") else None
    return out

def new_year_day(
    Y: int,
    *,
    engine: str = "phugpa",
    debug: bool = False,
    as_date: bool = True,
) -> dict:
    """
    First civil day of lunar year Y.

    Year-boundary logic (JS-style):
      - leap-month-first calendars: previous year ends at (Y-1,12,False)
      - leap-month-second calendars: previous year ends at prev_month(Y,1,False)

    New year JDN is:
      end_jd(30, n_last) + 1
    where n_last is the true-month index of the last month of the preceding year.

    If as_date=False, do not convert JDN to datetime.date (needed for years < 1).
    """
    eng = _reg().get(engine)
    me = eng.month

    # Determine last month of preceding year
    if me.p.leap_labeling == "first_is_leap":
        Y_last, M_last, L_last = Y - 1, 12, False
    else:
        n1 = me.true_month(Y, 1, is_leap_month=False)
        Y_last, M_last, L_last = me.label_from_true_month(n1 - 1)

    n_last = me.true_month(Y_last, M_last, is_leap_month=L_last)
    jdn = eng.day.end_jd(30, n_last) + 1

    out = {
        "Y": Y,
        "jdn": jdn,
        "prev_month": {"Y": Y_last, "M": M_last, "is_leap_month": L_last},
        "n_last": n_last,
    }
    if as_date:
        out["date"] = from_jdn(jdn)  # or from_jdn(jdn), depending on your api.py helper name

    if debug:
        out["engine"] = eng.info()
        if hasattr(eng, "month_info"):
            out["prev_month_info"] = eng.month_info(Y_last, M_last, debug=True)
        if hasattr(eng, "month_from_n"):
            out["month_from_n_last"] = eng.month_from_n(n_last, debug=True)

    return out


def first_day_of_month(
    Y: int,
    M: int,
    *,
    is_leap_month: bool = False,
    engine: str = "phugpa",
) -> date:
    """First civil day of lunar month (Y,M,leap)."""
    b = month_bounds(Y, M, is_leap_month=is_leap_month, engine=engine, debug=False)
    return b["first_date"]


def last_day_of_month(
    Y: int,
    M: int,
    *,
    is_leap_month: bool = False,
    engine: str = "phugpa",
) -> date:
    """Last civil day of lunar month (Y,M,leap)."""
    b = month_bounds(Y, M, is_leap_month=is_leap_month, engine=engine, debug=False)
    return b["last_date"]

