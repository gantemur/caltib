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

from typing import Protocol, List, Dict, Any, Union

NumT = Union[int, float, Fraction]

class MonthEngineProtocol(Protocol):
    """
    Handles discrete arithmetic. Maps absolute lunation indices (n)
    to human calendar labels (Year, Month, Leap status) and vice versa.
    """
    @property
    def epoch_k(self) -> int:
        """The absolute Meeus lunation index of the engine's epoch."""
        ...

    @property
    def sgang_base(self) -> NumT:
        """The principal solar term (longitude anchor) for the epoch."""
        ...

    # ---------------------------------------------------------
    # 1. Civil/Human Labels (The Orchestrator's Interface)
    # ---------------------------------------------------------
    def first_lunation(self, year: int) -> int:
        """
        Returns the absolute lunation index of the first lunation in the given year.
        """
        ...

    def get_lunations(self, tib_year: int, month_no: int) -> List[int]:
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

    # ---------------------------------------------------------
    # 2. Continuous Physics (The Diagnostic Interface)
    # ---------------------------------------------------------
    def mean_date(self, l: NumT) -> NumT:
        """Physical time t when Mean Elongation equals l turns."""
        ...
        
    def true_date(self, l: NumT) -> NumT:
        """Physical time t when True Elongation equals l turns."""
        ...

    def get_l_from_t2000(self, t2000: NumT) -> NumT:
        """Inverse kinematic lookup: true elongation (in turns) at physical time t."""
        ...
        
    def mean_sun(self, l: NumT) -> NumT:
        """Mean solar longitude (turns) at the moment true_date(l)."""
        ...
        
    def true_sun(self, l: NumT) -> NumT:
        """True solar longitude (turns) at the moment true_date(l)."""
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

    def local_civil_date(self, x: NumT) -> Fraction:
        """
        Civil-aligned time. Shifted such that floor(local_civil_date + J2000) 
        accurately bounds the human day (e.g., local dawn).
        """
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