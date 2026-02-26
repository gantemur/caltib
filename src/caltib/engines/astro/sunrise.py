from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from typing import Protocol, Optional

from .trans import SinAcosTurnProvider
from .fundamental import FundamentalContext

@dataclass(frozen=True)
class Location:
    lat_turn: Fraction    # latitude as turns (lat_deg/360)
    lon_turn: Fraction    # longitude as turns (lon_deg/360)
    elev_m: float = 0.0

class SunriseModel(Protocol):
    def sunrise_day_fraction(self, d: date, loc: Location) -> float: ...

@dataclass(frozen=True)
class ConstantSunrise(SunriseModel):
    day_fraction: float = 0.25  # 6:00 as fraction of day (placeholder)
    def sunrise_day_fraction(self, d: date, loc: Location) -> float:
        return self.day_fraction


@dataclass(frozen=True)
class LocationRational:
    lat_turn: Fraction    # latitude as turns (lat_deg/360)
    lon_turn: Fraction    # longitude as turns (positive East)
    elev_m: Fraction = Fraction(0, 1)

class SunriseRationalModel(Protocol):
    def sunrise_utc_fraction(self, jd_utc_midnight: int, loc: LocationRational) -> Fraction: ...

@dataclass(frozen=True)
class ConstantSunriseRational(SunriseRationalModel):
    """L1-L2: Fixed dawn in Local Mean Time (LMT), shifted by longitude to UTC."""
    day_fraction: Fraction = Fraction(1, 4)  # Default 6:00 AM LMT
    
    def sunrise_utc_fraction(self, jd_utc_midnight: int, loc: LocationRational) -> Fraction:
        # dawn_UTC = dawn_LMT - longitude_offset
        return self.day_fraction - loc.lon_turn