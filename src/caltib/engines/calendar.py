"""
caltib.engines.calendar
-----------------------
The Orchestrator. Binds the discrete MonthEngine and continuous DayEngine 
together, handling epoch synchronization and civil Julian Day boundaries.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Any, Dict, List

from caltib.core.types import EngineId, DayInfo, TibetanDate
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
        id: EngineId,
        month: MonthEngineProtocol, 
        day: DayEngineProtocol, 
        leap_labeling: str = "first_is_leap"
    ):
        self.id = id
        self.month = month
        self.day = day
        self.leap_labeling = leap_labeling
        
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
        
        # 3. Use civil-aligned date, NOT physical true_date
        t2000_civil = self.day.local_civil_date(x)
        return math.floor(t2000_civil + JD_J2000)

    # ---------------------------------------------------------
    # Inverse: Physical JDN to Civil Date
    # ---------------------------------------------------------

    def _build_civil_month(self, n_d: int) -> Dict[int, Dict[str, Any]]:
        """
        Internally maps a Day engine lunation n_d to a dictionary of 
        JDN -> Civil Day attributes, handling skipped and repeated days.
        """
        hits: Dict[int, List[int]] = {}
        # Use civil-aligned date, NOT physical true_date
        for d in range(1, 31):
            x = Fraction(30 * n_d + d, 1)
            t2000_civil = self.day.local_civil_date(x) # Shifted to dawn
            j = math.floor(t2000_civil + JD_J2000)
            hits.setdefault(j, []).append(d)
            
        # Get absolute civil month boundaries
        first_t2000 = self.day.true_date(Fraction(30 * (n_d - 1) + 30, 1))
        first_jd = math.floor(first_t2000 + JD_J2000) + 1
        
        last_t2000 = self.day.true_date(Fraction(30 * n_d + 30, 1))
        last_jd = math.floor(last_t2000 + JD_J2000)

        day_map = {}
        prev_label: int | None = None
        
        for j in range(first_jd, last_jd + 1):
            ended = hits.get(j, [])
            if not ended:
                if prev_label is None:
                    day_map[j] = {"day": 1, "repeated": False, "skipped": False}
                    prev_label = 1
                else:
                    day_map[j] = {"day": prev_label, "repeated": True, "skipped": False}
            else:
                label = ended[-1]
                skipped = len(ended) >= 2
                day_map[j] = {"day": label, "repeated": False, "skipped": skipped}
                prev_label = label
                
        return day_map

    def from_jdn(self, jdn: int) -> Dict[str, Any]:
        """
        Translates a local Julian Day Number into a human calendar date dictionary.
        """
        # 1. Estimate the target n_d using the Day engine inverse lookup
        approx_t2000 = jdn - float(JD_J2000) + 0.5
        approx_x = self.day.get_x_from_t2000(approx_t2000)
        n_d = approx_x // 30
        
        # 2. Look up the exact day in the civil month map
        month_map = self._build_civil_month(n_d)
        
        # Edge case: JDN falls just outside the estimated month boundaries
        if jdn not in month_map:
            if jdn < min(month_map.keys()):
                n_d -= 1
            elif jdn > max(month_map.keys()):
                n_d += 1
            month_map = self._build_civil_month(n_d)
            
        day_info = month_map[jdn]
        
        # 3. Shift back to Month engine coordinates
        n_m = n_d - self.delta_k
        m_info = self.month.get_month_info(n_m)
        
        # 4. Resolve human leap month label
        is_leap = False
        leap_state = m_info["leap_state"]
        if leap_state == 1:
            is_leap = (self.leap_labeling == "first_is_leap")
        elif leap_state == 2:
            is_leap = (self.leap_labeling == "second_is_leap")
            
        return {
            "year": m_info["year"],
            "month": m_info["month"],
            "is_leap": is_leap,
            "day": day_info["day"],
            "repeated": day_info["repeated"],
            "skipped": day_info["skipped"],
            "linear_month": m_info["linear_month"]
        }

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

    def to_gregorian(self, t: TibetanDate, *, policy: str = "all") -> List[Any]:
        from caltib.core.time import from_jdn
        jdn = self.to_jdn(t.tib_year, t.month_no, t.is_leap_month, t.tithi)
        # Note: robust policy handling (first, second, all) can be expanded here
        return [from_jdn(jdn)]

    def explain(self, d: Any) -> Dict[str, Any]:
        return self.day_info(d, debug=True).__dict__
