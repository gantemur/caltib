from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Protocol

from .types import DayInfo, TibetanDate

class CalendarEngine(Protocol):
    def info(self) -> Dict[str, Any]: ...
    def day_info(self, d: date, *, debug: bool = False) -> DayInfo: ...
    def to_gregorian(self, t: TibetanDate, *, policy: str = "all") -> List[date]: ...
    def explain(self, d: date) -> Dict[str, Any]: ...

@dataclass
class EngineRegistry:
    _engines: Dict[str, CalendarEngine]

    def get(self, name: str) -> CalendarEngine:
        if name not in self._engines:
            raise KeyError(f"Unknown engine '{name}'. Available: {sorted(self._engines)}")
        return self._engines[name]

    def list(self) -> List[str]:
        return sorted(self._engines.keys())

    def register(self, name: str, engine: CalendarEngine, *, overwrite: bool = False) -> None:
        if (not overwrite) and (name in self._engines):
            raise KeyError(f"Engine '{name}' already exists. Use overwrite=True to replace.")
        self._engines[name] = engine
