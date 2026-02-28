"""
caltib.engines.interfaces
-------------------------
Defines the strict architectural boundaries between discrete arithmetic (Month),
continuous kinematics (Day), and the orchestrator (Calendar).

Standard Reference Frame:
Unless otherwise specified, all physical time variables (t) in the DayEngine
represent Days since J2000.0 TT (Terrestrial Time), where J2000.0 = JD 2451545.0.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Dict, List, Protocol, Union

# A generic numeric type to support both exact Rational engines and Float engines
NumT = Union[int, float, Fraction]

class MonthEngineProtocol(Protocol):
    """
    Strictly handles discrete arithmetic. Maps absolute lunation indices (n)
    to human calendar labels (Year, Month, Leap status) and vice versa.
    Knows nothing about physical time or J2000.
    """
    @property
    def epoch_k(self) -> int:
        """The absolute Meeus lunation index of the engine's epoch."""
        ...

    @property
    def sgang1(self) -> NumT:
        """The principal solar term (longitude anchor) for the epoch."""
        ...

    def first_lunation(self, year: int) -> int:
        """
        Returns the absolute lunation index (n) for the first month 
        of the given Tibetan/Gregorian year.
        """
        ...

    def get_lunations(self, year: int, month: int) -> List[int]:
        """
        Returns the absolute lunation indices for a given Year and Month number.
        Returns:
            [] -> If the astronomical month was skipped.
            [n] -> Standard single month.
            [n, n+1] -> If the month is leaped (contains a main and intercalary month).
        """
        ...

    def get_month_info(self, n: int) -> Dict[str, Any]:
        """
        Expected keys:
        'year': int
        'month': int
        'leap_state': int (0=regular, 1=first of two, 2=second of two)
        'linear_month': int
        """
        ...
    

class DayEngineProtocol(Protocol):
    """
    Strictly handles kinematics. Maps the absolute tithi index (x) 
    to physical time (Days since J2000.0 TT) and solar/lunar longitudes.
    
    The absolute kinematic coordinate is defined as: x = 30 * n + d
    """
    @property
    def epoch_k(self) -> int:
        """The absolute Meeus lunation index of the engine's epoch."""
        ...

    def mean_date(self, x: NumT) -> NumT:
        """Returns the mean physical time (Days since J2000.0) for absolute tithi x."""
        ...

    def true_date(self, x: NumT) -> NumT:
        """Returns the true physical time (Days since J2000.0) for absolute tithi x."""
        ...

    def true_sun(self, x: NumT) -> NumT:
        """Returns the true solar longitude (turns) at absolute tithi x."""
        ...

    def mean_sun(self, x: NumT) -> NumT:
        """Returns the mean solar longitude (turns) at absolute tithi x."""
        ...
        
    def get_x_from_t2000(self, t2000: NumT) -> int:
        """
        Inverse kinematic lookup. Returns the active absolute tithi index (x) 
        that covers the given physical time (Days since J2000.0).
        """
        ...


class CalendarEngineProtocol(Protocol):
    """
    The orchestrator. Binds a MonthEngine and a DayEngine together.
    Translates full human dates to local Julian Day Numbers (JDN) and vice versa,
    hiding all internal continuous time (t2000) and time zone kinematics.
    """
    month: MonthEngineProtocol
    day: DayEngineProtocol
    leap_labeling: str  # "first_is_leap" or "second_is_leap"

    def from_jdn(self, jdn: int) -> Dict[str, Any]:
        """
        Translates a local Julian Day Number (integer day) into a human calendar date.
        """
        ...

    def to_jdn(self, year: int, month: int, is_leap: bool, day: int) -> int:
        """
        Translates a full human calendar date into a local Julian Day Number (integer).
        """
        ...