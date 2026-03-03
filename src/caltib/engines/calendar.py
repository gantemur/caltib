"""
caltib.engines.calendar
-----------------------
The Orchestrator. Binds the discrete MonthEngine and continuous DayEngine 
together, handling epoch synchronization and civil Julian Day boundaries.
"""

from __future__ import annotations

from datetime import date
from fractions import Fraction
from typing import Any, Dict

from caltib.core.types import EngineId, DayInfo, TibetanDate, LocationSpec
from caltib.engines.interfaces import MonthEngineProtocol, DayEngineProtocol

# J2000.0 TT base for absolute Julian Day conversion
JD_J2000 = Fraction(2451545, 1)

class CalendarEngine:
    """
    Translates full human dates to local Julian Day Numbers (JDN) and vice versa,
    hiding all internal continuous time (t2000) and coordinate (x) shifts.
    """
    def __init__(
        self, 
        spec: 'CalendarSpec',  # <-- Store the exact spec that built this engine
        month: MonthEngineProtocol, 
        day: DayEngineProtocol, 
    ):
        self.spec = spec
        self.id = spec.id
        # Safely extract leap_labeling from the spec
        self.leap_labeling = getattr(spec, 'leap_labeling', "first_is_leap")
        
        self.month = month
        self.day = day
        
        if self.leap_labeling not in ("first_is_leap", "second_is_leap"):
            raise ValueError("leap_labeling must be 'first_is_leap' or 'second_is_leap'")
            
        # The critical epoch synchronization shift.
        # Absolute Meeus k = n_M + epoch_M = n_D + epoch_D
        # Therefore: n_D = n_M + (epoch_M - epoch_D)
        self.delta_k = self.month.epoch_k - self.day.epoch_k

    @property
    def trad(self):
        """Convenience accessor for traditional almanac methods, if available."""
        if hasattr(self.month, "intercalation_index_traditional"):
            return self.month
        raise TypeError("This calendar does not use an Arithmetic Month Engine.")

    #Generate a calendar engine with given location
    def with_location(self, new_loc: 'LocationSpec') -> 'CalendarEngine':
        """
        Returns a completely new CalendarEngine instance, perfectly 
        recalibrated for the requested geographic location.
        """
        # 1. Ask the internal spec to rebuild its math for the new coordinates
        new_spec = self.spec.with_location(new_loc)
        
        # 2. Import locally to avoid circular import issues with factory.py
        from caltib.engines.factory import build_calendar_engine
        
        # 3. Spin up the fresh, location-aware engine!
        return build_calendar_engine(new_spec)

    # ---------------------------------------------------------
    # Forward: Civil Date to Physical JDN
    # ---------------------------------------------------------

    def to_jdn(self, year: int, month: int, is_leap: bool, day: int) -> int:
        """
        Translates a full human calendar date into a local Julian Day Number.
        """
        # 1. Get the month index
        n_m_list = self.month.get_lunations(year, month)
        
        if len(n_m_list) == 1:
            if is_leap:
                raise ValueError(f"Month {month} in year {year} is not a leap month.")
            n_m = n_m_list[0]
        else:
            if self.leap_labeling == "first_is_leap":
                n_m = n_m_list[0] if is_leap else n_m_list[1]
            else:
                n_m = n_m_list[1] if is_leap else n_m_list[0]

        # 2. Shift to Day engine coordinates and calculate x
        n_d = n_m + self.delta_k
        x = Fraction(30 * n_d + day, 1)
        
        # 3. Use the protected discrete boundary!
        return self.day.civil_jdn(x)

    # ---------------------------------------------------------
    # Inverse: Physical JDN to Civil Date
    # ---------------------------------------------------------

    def from_jdn(self, jdn: int) -> dict:
        """
        Maps a Gregorian JDN to a Tibetan Date using pure monotonic search 
        over exact discrete boundaries.
        """
        # 1. Get initial approximation for x (t2000 coordinate)
        t2000 = jdn - 2451545
        x = self.day.get_x_from_t2000(t2000)
        
        # 2. Monotonic search for the exact x active at the dawn of `jdn`
        # The civil day `jdn` belongs to tithi `x` iff: J(x-1) < jdn <= J(x)
        while True:
            # We now rely on the DayEngine to provide the exact absolute JDN!
            j_end = self.day.civil_jdn(x)
            j_prev = self.day.civil_jdn(x - 1)
            
            if jdn <= j_prev:
                x -= 1
            elif jdn > j_end:
                x += 1
            else:
                break
                
        # 3. Decompose absolute x into relative month (n_m) and day (d)
        n_d = (x - 1) // 30
        d = (x - 1) % 30 + 1
        n_m = n_d - self.delta_k
        
        # 4. Resolve Month labels
        year, month_no, leap_state = self.month.label_from_lunation(n_m)
        is_leap = False
        if leap_state == 1:
            is_leap = (self.leap_labeling == "first_is_leap")
        elif leap_state == 2:
            is_leap = (self.leap_labeling == "second_is_leap")
            
        # 5. Strict Physical Metadata
        occ = jdn - j_prev
        
        # CRITICAL FIX: The Orchestrator expects 'repeated' to mean "Is THIS day the duplicate?"
        # If occ == 2, it is the duplicate day. If occ == 1, it is the main day.
        is_duplicate_day = (occ > 1)
        
        # skipped: The previous tithi (x-1) was skipped if it covered 0 dawns
        skipped = (self.day.civil_jdn(x - 1) == self.day.civil_jdn(x - 2))
        
        return {
            "year": year,
            "month": month_no,
            "is_leap": is_leap,
            "day": d,
            "occ": occ,
            "repeated": is_duplicate_day,  # Prevents day_info from overwriting occ=1!
            "skipped": skipped,
            "linear_month": n_m
        }

    def build_civil_month(self, n_d: int) -> dict:
        """Diagnostic wrapper: Builds a month array using pure continuous bounds."""
        # Bracket the month safely using the protected boundaries
        j_start = self.day.civil_jdn(30 * n_d)
        j_end = self.day.civil_jdn(30 * n_d + 30)
        
        month_map = {}
        for jdn in range(j_start, j_end + 2):
            res = self.from_jdn(jdn)
            # Filter days to only those belonging to this exact lunation
            if (res["linear_month"] + self.delta_k) == n_d:
                month_map[jdn] = res
        return month_map
    
    # ---------------------------------------------------------
    # High-Level API Methods (Required by CLI / api.py)
    # ---------------------------------------------------------
    def info(self) -> Dict[str, Any]:
        return {"id": self.id.__dict__, "leap_labeling": self.leap_labeling}

    def day_info(self, d: Any, *, debug: bool = False) -> DayInfo:
        from caltib.core.time import to_jdn
        jdn = to_jdn(d)
        res = self.from_jdn(jdn)
        
        tib_date = TibetanDate(
            engine=self.id,
            tib_year=res["year"],
            month_no=res["month"],
            is_leap_month=res["is_leap"],
            tithi=res["day"],
            occ=2 if res["repeated"] else 1
        )
        
        return DayInfo(
            civil_date=d,
            engine=self.id,
            tibetan=tib_date,
            status="duplicated" if res["repeated"] else "normal",
            debug=res if debug else None
        )

    
    def to_gregorian(self, t: 'TibetanDate', *, policy: str = "all") -> list[date]:
        """
        Maps a TibetanDate back to Gregorian dates using pure continuous analytical mapping.
        """
        from caltib.core.time import from_jdn
        
        # 1. Resolve absolute lunation index
        lunations = self.month.get_lunations(t.tib_year, t.month_no)
        if len(lunations) == 1:
            n_m = lunations[0]
        else:
            if self.leap_labeling == "first_is_leap":
                n_m = lunations[0] if t.is_leap_month else lunations[1]
            else:
                n_m = lunations[1] if t.is_leap_month else lunations[0]
                
        # 2. Get the absolute continuous tithi index (x)
        n_d = n_m + self.delta_k
        x = 30 * n_d + t.tithi
        
        # 3. The Pure Mathematical Mapping using the DayEngine's exact integers
        j_start = self.day.civil_jdn(x - 1) + 1
        j_end   = self.day.civil_jdn(x) + 1 
        
        valid_jdns = list(range(j_start, j_end))
        
        # 4. Routing
        if policy == "all":
            return [from_jdn(j) for j in valid_jdns]
            
        elif policy == "occ":
            if not valid_jdns:
                return [] 
            idx = min(t.occ - 1, len(valid_jdns) - 1)
            return [from_jdn(valid_jdns[idx])]
            
        else:
            raise ValueError(f"Unknown to_gregorian policy: {policy}")
