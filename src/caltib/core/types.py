from __future__ import annotations
from dataclasses import dataclass, replace
from datetime import date
from typing import Any, Dict, Literal, Optional, Tuple

@dataclass(frozen=True)
class EngineId:
    family: Literal["trad", "reform", "custom"]
    name: str
    version: str

@dataclass(frozen=True)
class TibetanDate:
    engine: EngineId
    tib_year: int
    month_no: int
    is_leap_month: bool
    tithi: int
    occ: int = 1  # 1 or 2

@dataclass(frozen=True)
class DayInfo:
    civil_date: date
    engine: EngineId
    tibetan: TibetanDate
    status: Literal["normal", "duplicated"]
    festival_tags: Tuple[str, ...] = ()
    attributes: Optional[Dict[str, Any]] = None
    debug: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class CalendarSpec:
    """Pure data payload for constructing a full modular calendar."""
    id: EngineId
    month_params: Any  # ArithmeticMonthParams
    day_params: Any    # TraditionalDayParams | RationalDayParams
    leap_labeling: str
    meta: dict

@dataclass(frozen=True)
class EngineSpec:
    """Top-level wrapper for all engine specifications."""
    kind: Literal["traditional", "rational", "float", "ephemeris"]
    id: EngineId
    payload: CalendarSpec
