from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from fractions import Fraction
from typing import Any, Dict, List, Literal, Optional, Tuple


@dataclass(frozen=True)
class EngineId:
    family: Literal["trad", "reform", "custom"]
    name: str
    version: str

@dataclass(frozen=True)
class TibetanDate:
    """Pure mathematical coordinate of a Tibetan day."""
    engine: EngineId
    year: int
    month: int
    is_leap_month: bool
    tithi: int
    occ: int = 1  # 1 or 2
    previous_tithi_skipped: bool = False 
    linear_day: int = 0

    @property
    def lunar_day(self) -> int:
        return self.tithi

@dataclass(frozen=True)
class DayInfo:
    """Rich UI container for a specific civil day."""
    civil_date: date
    engine: EngineId
    tibetan: TibetanDate
    status: Literal["normal", "duplicated"]
    festival_tags: Tuple[str, ...] = ()
    lunar_attributes: Optional[Dict[str, Any]] = None  # <-- Lunar elements, animals, etc.
    civil_attributes: Optional[Dict[str, Any]] = None  # <-- Solar/JD elements, animals, etc.
    planets: Optional[Dict[str, Any]] = None
    debug: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class TibetanMonth:
    """Pure mathematical coordinate of a Tibetan month."""
    engine: EngineId
    year: int
    month: int
    is_leap_month: bool
    occ: int = 1
    previous_month_skipped: bool = False 
    linear_month: int = 0     

@dataclass(frozen=True)
class MonthInfo:
    """Rich UI container for a lunar month."""
    tibetan: TibetanMonth
    gregorian_start: Optional[date]  
    gregorian_end: Optional[date]    
    days: List[DayInfo] = field(default_factory=list) 
    status: Literal["normal", "duplicated", "skipped"] = "normal"
    attributes: Optional[Dict[str, Any]] = None  # <-- Month attributes live here!

@dataclass(frozen=True)
class TibetanYear:
    """Pure mathematical coordinate of a Tibetan year."""
    engine: EngineId
    year: int
    
    @property
    def rabjung_cycle(self) -> int:
        return (self.year - 1027) // 60 + 1

    @property
    def rabjung_year(self) -> int:
        return (self.year - 1027) % 60 + 1

@dataclass(frozen=True)
class YearInfo:
    """Rich UI container for a Tibetan year."""
    tibetan: TibetanYear
    gregorian_start: Optional[date] = None
    gregorian_end: Optional[date] = None
    months: List[MonthInfo] = field(default_factory=list) 
    attributes: Optional[Dict[str, Any]] = None  # <-- Year attributes live here!

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
