from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from fractions import Fraction
from typing import Any, Dict, Literal, Optional, Tuple


@dataclass(frozen=True)
class EngineId:
    family: Literal["trad", "reform", "custom"]
    name: str
    version: str

@dataclass(frozen=True)
class TibetanDate:
    engine: EngineId
    year: int
    month: int
    is_leap_month: bool
    tithi: int
    occ: int = 1  # 1 or 2
    previous_tithi_skipped: bool = False  # Crystal clear nomenclature
    linear_day: int = 0

    @property
    def lunar_day(self) -> int:
        return self.tithi

@dataclass(frozen=True)
class DayInfo:
    civil_date: date
    engine: EngineId
    tibetan: TibetanDate
    status: Literal["normal", "duplicated"]
    festival_tags: Tuple[str, ...] = ()
    attributes: Optional[Dict[str, Any]] = None
    planets: Optional[Dict[str, Any]] = None
    debug: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class TibetanMonth:
    engine: EngineId
    year: int
    month: int
    is_leap_month: bool
    occ: int = 1
    previous_month_skipped: bool = False  # Symmetric with previous_tithi_skipped
    linear_month: int = 0     # Absolute civil month index of this year (1 to 12/13)

@dataclass(frozen=True)
class MonthInfo:
    tibetan: TibetanMonth
    gregorian_start: Optional[date]  # None if the month is skipped
    gregorian_end: Optional[date]    # None if the month is skipped
    days: List[DayInfo] = field(default_factory=list) # Exactly length 29 or 30 for valid months
    status: Literal["normal", "duplicated", "skipped"] = "normal"
    attributes: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class TibetanYear:
    engine: EngineId
    year: int
    
    # 60-Year Sexagenary Cycle (Starts 1027 AD)
    @property
    def rabjung_cycle(self) -> int:
        return (self.year - 1027) // 60 + 1

    @property
    def rabjung_year(self) -> int:
        return (self.year - 1027) % 60 + 1

@dataclass(frozen=True)
class YearInfo:
    tibetan: TibetanYear
    gregorian_start: date
    gregorian_end: date
    months: List[MonthInfo] = field(default_factory=list) # Length 12 or 13 (leap year)
    attributes: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class LocationSpec:
    name: str
    lon_turn: Fraction
    lat_turn: Optional[Fraction] = None
    elev_m: Optional[Fraction] = None

    def __str__(self) -> str:
        """Allows CalendarEngine to answer 'what is your location?' cleanly."""
        if self.lat_turn is None:
            return f"{self.name} (Longitude: {float(self.lon_turn * 360):.2f}°E)"
        return f"{self.name} (Lon: {float(self.lon_turn * 360):.2f}°E, Lat: {float(self.lat_turn * 360):.2f}°N)"

@dataclass(frozen=True)
class CalendarSpec:
    """Pure data payload for constructing a full modular calendar."""
    id: EngineId
    month_params: Any  # ArithmeticMonthParams
    day_params: Any    # TraditionalDayParams | RationalDayParams
    leap_labeling: str
    meta: dict

    def with_location(self, new_loc: 'LocationSpec') -> 'CalendarSpec':
        """Creates a new spec securely recalibrated for the target location."""
        import dataclasses
        
        # Check if the day_params supports dynamic location swapping
        if hasattr(self.day_params, 'with_location'):
            new_day_params = self.day_params.with_location(new_loc)
            return dataclasses.replace(self, day_params=new_day_params)
            
        raise NotImplementedError(f"{type(self.day_params).__name__} does not support location swapping.")

@dataclass(frozen=True)
class EngineSpec:
    """Top-level wrapper for all engine specifications."""
    kind: Literal["traditional", "rational", "float", "ephemeris"]
    id: EngineId
    payload: CalendarSpec
