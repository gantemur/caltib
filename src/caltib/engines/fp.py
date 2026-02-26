from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from ..core.types import DayInfo, EngineId, TibetanDate
from ..core.time import to_jdn
from ..core.engine import CalendarEngine

@dataclass(frozen=True)
class FPSpec:
    id: EngineId
    meta: Optional[Dict[str, Any]] = None

class FPEngine(CalendarEngine):
    def __init__(self, spec: FPSpec):
        self.spec = spec

    def info(self) -> Dict[str, Any]:
        return {"family": self.spec.id.family, "name": self.spec.id.name, "version": self.spec.id.version, "numeric": "float"}

    def day_info(self, d: date, *, debug: bool = False) -> DayInfo:
        t = TibetanDate(engine=self.spec.id, tib_year=0, month_no=1, is_leap_month=False, tithi=1, occ=1)
        dbg = {"jdn": to_jdn(d), "note": "stub fp engine"} if debug else None
        return DayInfo(civil_date=d, engine=self.spec.id, tibetan=t, status="normal", debug=dbg)

    def to_gregorian(self, t: TibetanDate, *, policy: str = "all") -> List[date]:
        return []

    def explain(self, d: date) -> Dict[str, Any]:
        return {"engine": self.info(), "note": "stub explain"}

def build_fp_engine(spec: FPSpec) -> FPEngine:
    return FPEngine(spec)
