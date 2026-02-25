"""caltib public API.

Keep this surface small: users should mostly interact with functions re-exported here.
"""

# Initialize registry on import
from . import api_init as _api_init  # noqa: F401

from .api import (
    day_info,
    to_gregorian,
    explain,
    list_engines,
    engine_info,
    make_engine,
    register_engine,
    month_info,
    month_from_n,
    months_in_year, 
    days_in_month,
    true_date_dn,
    end_jd_dn,
    civil_month_n,
    prev_month,
    next_month,
    month_bounds,
    new_year_day,
    first_day_of_month,
    last_day_of_month
)
from .core.types import TibetanDate

__all__ = [
    "day_info",
    "to_gregorian",
    "explain",
    "list_engines",
    "engine_info",
    "make_engine",
    "register_engine",
    "month_info",
    "month_from_n",
    "TibetanDate",
    "months_in_year", 
    "days_in_month",
    "true_date_dn",
    "end_jd_dn",
    "civil_month_n",
    "prev_month",
    "next_month",
    "month_bounds",
    "new_year_day",
    "first_day_of_month",
    "last_day_of_month",
]
