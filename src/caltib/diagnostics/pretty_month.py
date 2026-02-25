from __future__ import annotations

from datetime import date, timedelta
import calendar as pycal
import argparse

import caltib


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


def lunar_month_calendar(engine: str, Y: int, M: int, is_leap: bool) -> None:
    b = caltib.month_bounds(Y, M, is_leap_month=is_leap, engine=engine)
    d0 = b["first_date"]
    d1 = b["last_date"]

    days = []
    d = d0
    while d <= d1:
        info = caltib.day_info(d, engine=engine)
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
    title = f"{engine} lunar month  Y={Y}  M={M}{leap_tag}   ({d0} .. {d1})"
    print_grid(title, weeks)


def gregorian_month_calendar(engine: str, gy: int, gm: int) -> None:
    first = date(gy, gm, 1)
    last_day = pycal.monthrange(gy, gm)[1]
    last = date(gy, gm, last_day)

    days = []
    d = first
    while d <= last:
        info = caltib.day_info(d, engine=engine)
        t = info.tibetan
        top = f"{d.day:2d}"
        leap_tag = "L" if t.is_leap_month else ""
        bot = f"{t.month_no:02d}{leap_tag}-{t.tithi:02d}"
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

    title = f"{engine} Gregorian month  {gy}-{gm:02d}"
    print_grid(title, weeks)

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Print a lunar-month calendar and/or a Gregorian-month calendar with paired labels."
    )
    p.add_argument("--engine", default="mongol", help="phugpa|tsurphu|mongol|bhutan|karana (default: mongol)")

    p.add_argument("--lunar", nargs=2, type=int, metavar=("Y", "M"),
                   help="Lunar month to print: Y M (e.g. 2026 1)")
    p.add_argument("--leap", action="store_true",
                   help="If set, lunar month is the leap instance (only meaningful when the label repeats).")

    p.add_argument("--greg", nargs=2, type=int, metavar=("GY", "GM"),
                   help="Gregorian month to print: GY GM (e.g. 2026 2)")

    args = p.parse_args(argv)

    if not args.lunar and not args.greg:
        # sensible default demo
        lunar_month_calendar(args.engine, Y=2026, M=1, is_leap=False)
        gregorian_month_calendar(args.engine, gy=2026, gm=2)
        return

    if args.lunar:
        Y, M = args.lunar
        lunar_month_calendar(args.engine, Y=Y, M=M, is_leap=args.leap)

    if args.greg:
        gy, gm = args.greg
        gregorian_month_calendar(args.engine, gy=gy, gm=gm)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())