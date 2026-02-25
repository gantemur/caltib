from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from typing import Protocol, Optional

from ._trans import SinAcosTurnProvider
from ._fundamental import FundamentalContext

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

# Placeholder L3 spherical sunrise (no EOT):
# Implement later using only sin_turn/acos_turn and solar declination.
@dataclass(frozen=True)
class SphericalSunriseL3(SunriseModel):
    def sunrise_day_fraction(self, d: date, loc: Location) -> float:
        raise NotImplementedError("Spherical sunrise model not implemented in skeleton.")
