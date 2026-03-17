"""
caltib.engines.factory
----------------------
Transforms pure data specifications into live, executable Engine objects.
"""

from __future__ import annotations
from caltib.core.types import CalendarSpec
from caltib.engines.calendar import CalendarEngine
from caltib.engines.arithmetic_month import ArithmeticMonthParams, ArithmeticMonthEngine
from caltib.engines.arithmetic_day import ArithmeticDayParams, ArithmeticDayEngine
from caltib.engines.rational_month import RationalMonthParams, RationalMonthEngine
from caltib.engines.trad_day import TraditionalDayParams, TraditionalDayEngine
from caltib.engines.rational_day import RationalDayParams, RationalDayEngine
from caltib.engines.fp_day import FloatDayParams, FloatDayEngine
from caltib.engines.trad_attr import TraditionalAttributeEngine
from caltib.engines.trad_planets import TraditionalPlanetsParams, TraditionalPlanetsEngine

    
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
    elif isinstance(spec.day_params, ArithmeticDayParams):
        day_engine = ArithmeticDayEngine(spec.day_params)
    elif isinstance(spec.day_params, FloatDayParams):
         day_engine = FloatDayEngine(spec.day_params)
    # elif isinstance(spec.day_params, EphDayParams):
    #     day_engine = ephDayEngine(spec.day_params)
    else:
        raise TypeError(f"Unknown Day Params type: {type(spec.day_params)}")

    # 3. Build the Attribute Engine (Optional)
    attr_engine = TraditionalAttributeEngine(engine_id=spec.id.name)
    
    # 4. Build Planets Engine (Optional)
    planets_engine = None
    if spec.planets_params is not None:
        if isinstance(spec.planets_params, TraditionalPlanetsParams):
            planets_engine = TraditionalPlanetsEngine(spec.planets_params)
        else:
            raise TypeError(f"Unknown Planets Params type: {type(spec.planets_params)}")

    # 5. Orchestrate
    # We only need to pass spec, month, day, attribute, and planets. CalendarEngine handles the rest internally!
    return CalendarEngine(
        spec=spec,
        month=month_engine,
        day=day_engine,
        attr=attr_engine,
        planets=planets_engine
    )

def make_engine(spec: CalendarSpec) -> CalendarEngine:
    """The universal entry point."""
    return build_calendar_engine(spec)
