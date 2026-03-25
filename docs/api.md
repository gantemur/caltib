# The `caltib` Python API

The library provides a clean, unified interface to query both discrete traditional engines and continuous astronomical models. Because of the strict mathematical decoupling under the hood, the top-level API remains identical whether you are evaluating a 15th-century integer framework or an L6 JPL numerical ephemeris.

---

## 1. Initialization & The Engine Factory

The `get_calendar()` factory is the gateway to the library. It dynamically instantiates the requested `CalendarEngine`, utilizing lazy loading to ensure high-end dependencies (like `jplephem`) are only imported if explicitly requested.

```python
import caltib
from caltib.engines.specs import LOC_MONTREAL, LOC_LHASA

# Instantiate a traditional engine (defaults to approximate historical coordinates)
phugpa_engine = caltib.get_calendar("phugpa")

# Instantiate a reform engine with localized geographical dependency injection
# This dynamically overrides the thresholds used for spherical sunrise
l3_montreal = caltib.get_calendar("l3", location=LOC_MONTREAL)
```

---

## 2. Core Day Queries

The most common operation is fetching the complete calendrical state for a specific Gregorian date. You can use the top-level `day_info()` function for quick lookups, or call it directly on an instantiated engine.

```python
from datetime import date

# 1. Top-level quick query
info = caltib.day_info(date(2026, 2, 21), engine="mongol")

# 2. Engine-level query (faster for bulk operations)
info = l3_montreal.day_info(date(2026, 2, 21))

print(f"Tibetan Year: {info.tibetan.year}")
print(f"Tithi (Lunar Day): {info.tibetan.tithi}")
print(f"Is Leap Month?: {info.tibetan.is_leap_month}")
```

### The `DayInfo` & `TibetanDate` Data Models

The `day_info` method returns a comprehensive `DayInfo` dataclass containing both the input Gregorian parameters and the resulting Tibetan mapping.

* `DayInfo.gregorian`: A standard Python `datetime.date` object.
* `DayInfo.jdn`: The Julian Day Number (integer) representing local noon.
* `DayInfo.tibetan`: A `TibetanDate` dataclass containing:
    * `year`: The Tibetan year number.
    * `month`: The Tibetan month number (1–12).
    * `is_leap_month`: Boolean. `True` if this is an intercalary month.
    * `tithi`: The lunar day number (1–30).
    * `is_leap_day`: Boolean. `True` if this specific tithi is duplicated (the second occurrence).
    * `is_skipped`: Boolean. Identifies if the *preceding* mathematical tithi was skipped in the civil calendar.

---

## 3. Calendar Arithmetic & Conversions

The API provides robust tools for navigating the calendar chronologically, handling the complex boundaries of leap months and missing days.

* `caltib.new_year_day(Y: int, engine: str) -> date`: Resolves the Gregorian start date of the Tibetan New Year (Losar / Tsagaan Sar) for the given Tibetan year $Y$.
* `caltib.month_bounds(Y: int, M: int, is_leap: bool = False, engine: str) -> MonthBounds`: Returns the exact starting and ending JDN and Gregorian dates of a specific lunar month, mapping the continuous coordinate $x$ to the civil grid.
* `caltib.to_gregorian(t_date: TibetanDate, engine: str, policy: str = "all") -> list[date]`: Inverts a Tibetan date back into Gregorian. Because Tibetan civil days can be duplicated, this returns a list.
    * `policy="all"`: Returns all Gregorian dates matching the Tibetan date (returns 2 dates if duplicated, 0 if skipped).
    * `policy="first"`: Returns only the first occurrence of a duplicated day.
    * `policy="second"`: Returns only the second occurrence.

---

## 4. High-Performance Bulk Processing

When generating millennia-spanning charts in the Diagnostics Lab, repeatedly calling the top-level `caltib.day_info(..., engine="...")` introduces factory overhead. For maximum performance, instantiate the `CalendarEngine` once and use its internal generators.

```python
# Instantiate engine once
engine = caltib.get_calendar("l4")

# Fetch civil calendar mappings for an entire lunation efficiently
# lunation_index (n) maps directly to the absolute coordinate x = 30n + d
month_map = engine.build_civil_month(lunation_index=12345)

for civil_jdn, tithi in month_map.items():
    # Process the discrete grid...
    pass
```

---

## Exhaustive API Reference

Below is the automatically generated technical reference for all public classes and functions in the `caltib` library, extracted directly from the Python source code.

### Top-Level API & Configuration
::: caltib.api
::: caltib.engines.factory
::: caltib.engines.specs

### Core Data Models
::: caltib.core.types
::: caltib.core.time

### Base Engine Architectures
::: caltib.engines.interfaces
::: caltib.engines.calendar

### Internal Solvers & Physics Models
::: caltib.engines.trad_day
::: caltib.engines.rational_day
::: caltib.engines.fp_day

!!! warning "Experimental: L6 Engine"
    The following `l6.engine` module is under development.

::: caltib.engines.l6.engine

### Analytical Astronomical Reference (Ground Truth)
::: caltib.reference.solar
::: caltib.reference.lunar
::: caltib.reference.time_scales
::: caltib.reference.astro_args