"""
caltib.engines.factory
----------------------
Transforms pure data specifications into live, executable Engine objects.
"""

from __future__ import annotations
from caltib.core.types import EngineSpec, CalendarSpec
from caltib.engines.calendar import CalendarEngine
from caltib.engines.arithmetic_month import ArithmeticMonthParams, ArithmeticMonthEngine
from caltib.engines.rational_month import RationalMonthParams, RationalMonthEngine
from caltib.engines.trad_day import TraditionalDayParams, TraditionalDayEngine
from caltib.engines.rational_day import RationalDayParams, RationalDayEngine

    
def build_calendar_engine(spec: CalendarSpec) -> CalendarEngine:
    """Transforms a pure data CalendarSpec into a live CalendarEngine."""
    # 1. Build the appropriate Month Engine
    if isinstance(spec.month_params, ArithmeticMonthParams):
        month_engine = ArithmeticMonthEngine(spec.month_params)
    elif isinstance(spec.month_params, RationalMonthParams):
        month_engine = RationalMonthEngine(spec.month_params)
    # elif isinstance(spec.month_params, EphMonthParams):
    #     month_engine = EphMonthEngine(spec.month_params)
    else:
        raise TypeError(f"Unknown Month Params type: {type(spec.month_params)}")
    
    # 2. Build the appropriate Day Engine
    if isinstance(spec.day_params, TraditionalDayParams):
        day_engine = TraditionalDayEngine(spec.day_params)
    elif isinstance(spec.day_params, RationalDayParams):
        day_engine = RationalDayEngine(spec.day_params)
    # elif isinstance(spec.day_params, FloatDayParams):
    #     day_engine = FloatDayEngine(spec.day_params)
    else:
        raise TypeError(f"Unknown Day Params type: {type(spec.day_params)}")
        
    # 3. Orchestrate
    return CalendarEngine(
        id=spec.id,
        month=month_engine, 
        day=day_engine, 
        leap_labeling=spec.leap_labeling
    )

def make_engine(spec: EngineSpec) -> CalendarEngine:
    """The universal entry point."""
    return build_calendar_engine(spec.payload)