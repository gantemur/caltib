from __future__ import annotations

from datetime import date, timedelta
import calendar as pycal
import argparse

import caltib
# Import ALL_SPECS to leverage our new location builder
from caltib.engines.factory import build_calendar_engine
from caltib.engines.specs import ALL_SPECS, LOC_MONTREAL, LOC_LHASA, LOC_ULAANBAATAR

def dow_header() -> str:
    return "Mo     Tu     We     Th     Fr     Sa     Su"


def cell(top: str, bot: str, w: int = 6) -> tuple[str, str]:
    return (top[:w].ljust(w), bot[:w].ljust(w))


def print_grid(title: str, weeks: list[list[tuple[str, str]]]) -> None:
    print(title)
    print(dow_header())
    print("-" * len(dow_header()))
    for wk in weeks:
        print(" ".join(c[0] for c in wk))
        print(" ".join(c[1] for c in wk))
    print()


def lunar_month_calendar(engine_obj, engine_name: str, Y: int, M: int, is_leap: bool) -> None:
    # Use the initialized engine object directly if your API supports it, 
    # otherwise fallback to the string name
    b = caltib.month_bounds(Y, M, is_leap_month=is_leap, engine=engine_name)
    d0 = b["first_date"]
    d1 = b["last_date"]

    days = []
    d = d0
    while d <= d1:
        # Use engine_name for standard lookup, or engine_obj if you updated your API
        info = caltib.day_info(d, engine=engine_name) 
        t = info.tibetan
        top = f"{t.tithi:2d}"
        bot = f"{d.month:02d}-{d.day:02d}"
        days.append((d, top, bot))
        d += timedelta(days=1)

    weeks: list[list[tuple[str, str]]] = []
    wk: list[tuple[str, str]] = []
    pad = d0.weekday()  # Monday=0
    for _ in range(pad):
        wk.append(cell("", ""))
    for _, top, bot in days:
        wk.append(cell(top, bot))
        if len(wk) == 7:
            weeks.append(wk)
            wk = []
    if wk:
        while len(wk) < 7:
            wk.append(cell("", ""))
        weeks.append(wk)

    leap_tag = "L" if is_leap else ""
    # Check if the engine has our new location protocol!
    loc_str = getattr(engine_obj, 'location', '')
    if loc_str:
        loc_str = f" @ {loc_str.name}"
        
    title = f"{engine_name.upper()}{loc_str} lunar month  Y={Y}  M={M}{leap_tag}   ({d0} .. {d1})"
    print_grid(title, weeks)


def gregorian_month_calendar(engine_name: str, gy: int, gm: int) -> None:
    first = date(gy, gm, 1)
    last_day = pycal.monthrange(gy, gm)[1]
    last = date(gy, gm, last_day)

    days = []
    d = first
    while d <= last:
        info = caltib.day_info(d, engine=engine_name)
        t = info.tibetan
        top = f"{d.day:2d}"
        
        # Validated: using t.month instead of t.month_no to match our engine dicts
        leap_tag = "L" if getattr(t, 'is_leap_month', False) else ""
        month_val = getattr(t, 'month', getattr(t, 'month_no', 0)) 
        
        bot = f"{month_val:02d}{leap_tag}-{t.tithi:02d}"
        days.append((d, top, bot))
        d += timedelta(days=1)

    weeks: list[list[tuple[str, str]]] = []
    wk: list[tuple[str, str]] = []
    pad = first.weekday()  # Monday=0
    for _ in range(pad):
        wk.append(cell("", ""))
    for _, top, bot in days:
        wk.append(cell(top, bot))
        if len(wk) == 7:
            weeks.append(wk)
            wk = []
    if wk:
        while len(wk) < 7:
            wk.append(cell("", ""))
        weeks.append(wk)

    title = f"{engine_name.upper()} Gregorian month  {gy}-{gm:02d}"
    print_grid(title, weeks)

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Print a lunar-month calendar and/or a Gregorian-month calendar with paired labels."
    )
    # Updated to include the new aliases!
    p.add_argument("--engine", default="mongol", 
                   help="phugpa|tsurphu|mongol|bhutan|l0|l1|l2|l3|l4 (default: mongol)")

    p.add_argument("--lunar", nargs=2, type=int, metavar=("Y", "M"),
                   help="Lunar month to print: Y M (e.g. 2026 1)")
    p.add_argument("--leap", action="store_true",
                   help="If set, lunar month is the leap instance.")

    p.add_argument("--greg", nargs=2, type=int, metavar=("GY", "GM"),
                   help="Gregorian month to print: GY GM (e.g. 2026 2)")
                   
    # New location hot-swapping argument!
    p.add_argument("--loc", type=str, choices=["lhasa", "montreal", "ub"],
                   help="Override the default engine location (requires caltib.api to support engine object passing)")

    args = p.parse_args(argv)

    # 1. Resolve Engine and Optional Location Override
    engine_name = args.engine
    engine_obj = build_calendar_engine(ALL_SPECS.get(engine_name, ALL_SPECS["mongol"]))
    
    if args.loc:
        loc_map = {"lhasa": LOC_LHASA, "montreal": LOC_MONTREAL, "ub": LOC_ULAANBAATAR}
        target_loc = loc_map[args.loc]
        if hasattr(engine_obj, 'with_location'):
            engine_obj = engine_obj.with_location(target_loc)
            # Temporarily register this custom instance into the API so the string 
            # name resolves to the localized engine during this script's execution.
            from caltib import api as _api
            _api._reg()._engines[engine_name] = engine_obj

    # 2. Execute
    if not args.lunar and not args.greg:
        lunar_month_calendar(engine_obj, engine_name, Y=2026, M=1, is_leap=False)
        gregorian_month_calendar(engine_name, gy=2026, gm=2)
        return 0

    if args.lunar:
        Y, M = args.lunar
        lunar_month_calendar(engine_obj, engine_name, Y=Y, M=M, is_leap=args.leap)

    if args.greg:
        gy, gm = args.greg
        gregorian_month_calendar(engine_name, gy=gy, gm=gm)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())