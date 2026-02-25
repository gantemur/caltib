from __future__ import annotations

from datetime import date
import argparse
from typing import List, Tuple

import caltib


DEFAULT_TRADITIONS: List[Tuple[str, str]] = [
    ("Karana", "karana"),
    ("Tsurphu", "tsurphu"),
    ("Phugpa", "phugpa"),
    ("Bhutan", "bhutan"),
    ("Mongol", "mongol"),
]


def mmdd(d: date) -> str:
    return f"{d.month:02d}-{d.day:02d}"


def parse_traditions(arg: str) -> List[Tuple[str, str]]:
    """
    Parse traditions list from CLI.
    Example:
      --traditions "Karana=karana,Tsurphu=tsurphu,Phugpa=phugpa"
    If you pass just engines, names will be capitalized engines:
      --traditions "phugpa,mongol"
    """
    items = [x.strip() for x in arg.split(",") if x.strip()]
    out: List[Tuple[str, str]] = []
    for it in items:
        if "=" in it:
            name, eng = it.split("=", 1)
            out.append((name.strip(), eng.strip()))
        else:
            eng = it
            out.append((eng.capitalize(), eng))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Print New Year (Losar/Tsagaan Sar) date table for multiple traditions."
    )
    p.add_argument("--from-year", type=int, default=2000)
    p.add_argument("--to-year", type=int, default=2030)
    p.add_argument(
        "--traditions",
        type=str,
        default="",
        help='Comma list like "Karana=karana,Tsurphu=tsurphu,Phugpa=phugpa" (default: standard 5).',
    )
    p.add_argument(
        "--dates",
        choices=("mmdd", "iso"),
        default="mmdd",
        help="Display format in table columns (default: mmdd).",
    )
    p.add_argument(
        "--list-month",
        type=int,
        default=3,
        help="After the table, list all occurrences that fall in this Gregorian month (default: 3=March).",
    )
    args = p.parse_args(argv)

    traditions = parse_traditions(args.traditions) if args.traditions else DEFAULT_TRADITIONS

    def fmt(d: date) -> str:
        return mmdd(d) if args.dates == "mmdd" else d.isoformat()

    Y0, Y1 = args.from_year, args.to_year
    if Y1 < Y0:
        raise SystemExit("--to-year must be >= --from-year")

    # table header
    headers = ["Year"] + [name for name, _ in traditions]
    colw = [5] + [max(6, len(h)) for h in headers[1:]]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, colw))
    print(line)
    print("-" * len(line))

    hits: list[tuple[date, int, str]] = []  # (date, lunar_year, tradition_name)

    for Y in range(Y0, Y1 + 1):
        row = [str(Y).ljust(colw[0])]
        for (name, eng), w in zip(traditions, colw[1:]):
            ny = caltib.new_year_day(Y, engine=eng)
            d = ny["date"]
            row.append(fmt(d).ljust(w))
            if d.month == args.list_month:
                hits.append((d, Y, name))
        print("  ".join(row))

    # month hits
    print(f"\nNew Year occurrences in month={args.list_month:02d}:")
    if not hits:
        print("(none)")
        return 0

    hits.sort()
    for d, Y, name in hits:
        # full date always shown here for clarity
        print(f"{d.isoformat()}  {name}  (Y={Y})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())