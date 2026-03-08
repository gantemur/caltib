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

from caltib.core.types import EngineId, DayInfo, TibetanDate, MonthInfo, TibetanMonth, YearInfo, TibetanYear, LocationSpec, CalendarSpec
from caltib.engines.interfaces import MonthEngineProtocol, DayEngineProtocol, AttributeEngineProtocol, PlanetsEngineProtocol, NumT

# J2000.0 TT base for absolute Julian Day conversion
JD_J2000 = Fraction(2451545, 1)

class CalendarEngine:
    """
    Translates full human dates to local Julian Day Numbers (JDN) and vice versa,
    hiding all internal continuous time (t2000) and coordinate (x) shifts.
    """
    def __init__(
        self, 
        spec: 'CalendarSpec',
        month: MonthEngineProtocol, 
        day: DayEngineProtocol, 
        attr: AttributeEngineProtocol = None,
        planets: PlanetsEngineProtocol = None,
    ):
        self.spec = spec
        self.id = spec.id
        # Safely extract leap_labeling from the spec
        self.leap_labeling = getattr(spec, 'leap_labeling', "first_is_leap")
        
        self.month = month
        self.day = day
        self.attr = attr
        self.planets = planets
        
        if self.leap_labeling not in ("first_is_leap", "second_is_leap"):
            raise ValueError("leap_labeling must be 'first_is_leap' or 'second_is_leap'")
            
        # The critical epoch synchronization shift.
        # Absolute Meeus k = n_M + epoch_M = n_D + epoch_D
        # Therefore: n_D = n_M + (epoch_M - epoch_D)
        self.delta_k = self.month.epoch_k - self.day.epoch_k

    @property
    def sgang_base(self) -> Fraction:
        """Returns the continuous zodiac offset [0, 1) turns for the first Sgang."""
        if hasattr(self, "month") and hasattr(self.month, "sgang_base"):
            return self.month.sgang_base
        return Fraction(0, 1) # Default to Aries 0° if the engine has no month component

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
        year, month, leap_state = self.month.label_from_lunation(n_m)
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
            "month": month,
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
        
        n_m = res["linear_month"]
        n_d = n_m + self.delta_k
        j_month_start_boundary = self.day.civil_jdn(30 * n_d)
        linear_day = jdn - j_month_start_boundary

        lunar_attrs = self.attr.get_lunar_day_attributes(res["year"], res["month"], res["day"])
        civil_attrs = self.attr.get_civil_day_attributes(jdn)

        # Calculate Planetary Longitudes strictly at Civil Dawn JDN
        planet_data = None
        if self.planets is not None:
            planet_data = self.planets.longitudes(jdn)
            # If you want float outputs for the UI, you can convert the Fractions here:
            # planet_data = {k: {"mean": float(v["mean"]), "true": float(v["true"])} for k, v in planet_data.items()}
        
        tib_date = TibetanDate(
            engine=self.id,
            year=res["year"],
            month=res["month"],
            is_leap_month=res["is_leap"],
            tithi=res["day"],
            occ=2 if res["repeated"] else 1,
            previous_tithi_skipped=res["skipped"],
            linear_day=linear_day,
        )
        
        return DayInfo(
            civil_date=d,
            engine=self.id,
            tibetan=tib_date,
            status="duplicated" if res["repeated"] else "normal",
            lunar_attributes=lunar_attrs,
            civil_attributes=civil_attrs,
            planets=planet_data,
            debug=res if debug else None
        )
    
    def to_gregorian(self, t: 'TibetanDate', *, policy: str = "all") -> list[date]:
        """
        Maps a TibetanDate back to Gregorian dates using pure continuous analytical mapping.
        """
        from caltib.core.time import from_jdn
        
        # 1. Resolve absolute lunation index
        lunations = self.month.get_lunations(t.year, t.month)
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

    # ---------------------------------------------------------
    # Bulk Data Generators (Month & Year)
    # ---------------------------------------------------------

    def _build_month_info_from_n(self, n: int) -> MonthInfo:
        """Internal helper to build a full MonthInfo object from an absolute lunation index."""
        # 1. Ask the protocol for the exact human labels for this n
        m_data = self.month.get_month_info(n)
        year = m_data["year"]
        month = m_data["month"]
        leap_state = m_data["leap_state"]
        linear_month = m_data.get("linear_month", 0)

        # 2. Resolve leap labeling policy
        is_leap = False
        if leap_state == 1:
            is_leap = (self.leap_labeling == "first_is_leap")
        elif leap_state == 2:
            is_leap = (self.leap_labeling == "second_is_leap")

        # 3. Shift to Day engine coordinates and generate the days
        n_d = n + self.delta_k
        raw_days = self.build_civil_month(n_d)
        
        # Find the absolute boundary for O(1) linear mapping
        j_month_start_boundary = self.day.civil_jdn(30 * n_d)

        from caltib.core.time import from_jdn
        
        days_list = []
        
        for jdn in sorted(raw_days.keys()):
            res = raw_days[jdn]
            civil_date = from_jdn(jdn)
            
            # Analytical O(1) calculation. First day is exactly 1.
            linear_day = jdn - j_month_start_boundary

            lunar_attrs = self.attr.get_lunar_day_attributes(year, month, res["day"])
            civil_attrs = self.attr.get_civil_day_attributes(jdn)
            
            t_date = TibetanDate(
                engine=self.id,
                year=year,
                month=month,
                is_leap_month=is_leap,
                tithi=res["day"],
                occ=2 if res["repeated"] else 1,
                previous_tithi_skipped=res["skipped"],
                linear_day=linear_day,
            )
            
            days_list.append(DayInfo(
                civil_date=civil_date, 
                engine=self.id, 
                tibetan=t_date, 
                status="duplicated" if res["repeated"] else "normal",
                lunar_attributes=lunar_attrs,
                civil_attributes=civil_attrs 
            ))

        tib_m = TibetanMonth(
            engine=self.id, 
            year=year, 
            month=month, 
            is_leap_month=is_leap, 
            linear_month=linear_month
        )

        m_attrs = self.attr.get_month_attributes(year, month)
                
        return MonthInfo(
            tibetan=tib_m,
            gregorian_start=days_list[0].civil_date if days_list else None,
            gregorian_end=days_list[-1].civil_date if days_list else None,
            days=days_list,
            attributes=m_attrs
        )
    
    def month_info(self, year: int, month: int, is_leap: bool = False) -> MonthInfo:
        """
        Generates a fully populated MonthInfo object using absolute lunation lookup.
        """
        lunations = self.month.get_lunations(year, month)
        
        # 1. Skipped Month Check
        if not lunations:
            tib_m = TibetanMonth(self.id, year, month, is_leap, previous_month_skipped=True)
            return MonthInfo(tib_m, None, None, [], status="skipped")
            
        # 2. Match Leap Request to the correct lunation index
        if len(lunations) == 1:
            if is_leap:
                raise ValueError(f"Month {month} in year {year} is not a leap month.")
            n = lunations[0]
        else:
            if self.leap_labeling == "first_is_leap":
                n = lunations[0] if is_leap else lunations[1]
            else:
                n = lunations[1] if is_leap else lunations[0]
                
        return self._build_month_info_from_n(n)


    def year_info(self, year: int) -> YearInfo:
        """
        Generates a complete YearInfo object by iterating continuously through 
        the exact mathematical lunations (n) that exist in the year.
        """
        months_list = []
        
        start_n = self.month.first_lunation(year)
        end_n = self.month.first_lunation(year + 1)
        
        prev_month_no = None
        
        # Iterate n strictly over the existing lunations
        for n in range(start_n, end_n):
            m_info = self._build_month_info_from_n(n)
            
            # Dynamically detect if a month was skipped prior to this one
            # by checking if the month number jumped by more than 1
            curr_month_no = m_info.tibetan.month
            prev_skipped = False
            
            if prev_month_no is not None:
                diff = curr_month_no - prev_month_no
                if diff > 1 or (diff < 0 and curr_month_no > 1):
                    prev_skipped = True
            else:
                # If the first month we encounter in the year is not Month 1 (or 12 from late prev year)
                if curr_month_no > 1 and curr_month_no != 12:
                    prev_skipped = True
                    
            if prev_skipped:
                import dataclasses
                new_tib_m = dataclasses.replace(m_info.tibetan, previous_month_skipped=True)
                m_info = dataclasses.replace(m_info, tibetan=new_tib_m)
                
            months_list.append(m_info)
            prev_month_no = curr_month_no
                
        tib_y = TibetanYear(self.id, year)
        y_attrs = self.attr.get_year_attributes(year)
        
        return YearInfo(
            tibetan=tib_y,
            gregorian_start=months_list[0].gregorian_start if months_list else None,
            gregorian_end=months_list[-1].gregorian_end if months_list else None,
            months=months_list,
            attributes=y_attrs
        )

    # ---------------------------------------------------------
    # Direct passthroughs for tests/debugging
    # ---------------------------------------------------------

    def get_planet_longitudes(self, jd: NumT) -> Dict[str, Dict[str, NumT]] | None:
        """
        Directly evaluates planetary longitudes for a given Julian Date (Local JD for traditional calendars) 
        or continuous physical time. Useful for debugging or isolated kinematic testing.
        """
        if self.planets is None:
            return None
        return self.planets.longitudes(jd)
