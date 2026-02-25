#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional


IERS_C04_CSV_URL = "https://datacenter.iers.org/data/csv/eopc04_14_IAU2000.62-now.csv"
LEAP_SECONDS_URL = "https://data.iana.org/time-zones/data/leap-seconds.list"


# -----------------------------
# Leap seconds parsing (IANA)
# -----------------------------
@dataclass(frozen=True)
class LeapEntry:
    # UTC date at which new TAI-UTC applies (inclusive)
    utc_date: date
    tai_minus_utc: int

def _parse_leap_seconds_list(text: str) -> List[LeapEntry]:
    """
    Parse IANA leap-seconds.list, using the explicit UTC date in the comment:

      2272060800 10 # 1 Jan 1972

    We IGNORE the NTP timestamp, because converting it to UTC via timedelta
    is not reliable in the presence of leap seconds.
    """
    month = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    entries: List[LeapEntry] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Expect: "<ntp> <tai_utc> # <day> <Mon> <year>"
        # Example: "2272060800 10 # 1 Jan 1972"
        if "#" not in line:
            continue
        left, right = line.split("#", 1)
        left = left.strip().split()
        right = right.strip().split()
        if len(left) < 2 or len(right) < 3:
            continue

        try:
            tai_utc = int(left[1])
            dd = int(right[0])
            mm = month[right[1].lower()[:3]]
            yy = int(right[2])
            d = date(yy, mm, dd)
        except Exception:
            continue

        entries.append(LeapEntry(d, tai_utc))

    entries.sort(key=lambda e: e.utc_date)
    if not entries:
        raise RuntimeError("Failed to parse leap-seconds.list (no entries)")

    # dedup by date (keep last)
    dedup: Dict[date, LeapEntry] = {}
    for e in entries:
        dedup[e.utc_date] = e
    return sorted(dedup.values(), key=lambda e: e.utc_date)


def _seconds_to_timedelta(s: int):
    # avoid importing timedelta at module import (tiny)
    from datetime import timedelta
    return timedelta(seconds=s)


def tai_minus_utc_for_day(leaps: List[LeapEntry], d: date) -> int:
    """
    Return TAI-UTC (seconds) valid at UTC date d.
    """
    # last entry with utc_date <= d
    lo, hi = 0, len(leaps) - 1
    if d < leaps[0].utc_date:
        # before 1972 leap-second regime: we just clamp
        return leaps[0].tai_minus_utc
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if leaps[mid].utc_date <= d:
            lo = mid
        else:
            hi = mid
    if leaps[hi].utc_date <= d:
        return leaps[hi].tai_minus_utc
    return leaps[lo].tai_minus_utc


# -----------------------------
# IERS C04 parsing
# -----------------------------
@dataclass(frozen=True)
class EOPRow:
    d: date
    ut1_utc: float  # seconds


def _fetch(url: str) -> str:
    with urllib.request.urlopen(url) as r:
        return r.read().decode("utf-8", errors="replace")

def _parse_iers_c04_csv(text: str) -> List[EOPRow]:
    """
    Parse IERS C04 CSV.

    Note: IERS 'csv' files are typically semicolon-separated.
    We detect delimiter from the header line.
    """
    # Keep non-empty, non-comment lines
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        raise RuntimeError("IERS CSV appears empty")

    # Detect delimiter from header line
    header_line = lines[0]
    if header_line.count(";") >= 5:
        delim = ";"
    elif header_line.count(",") >= 5:
        delim = ","
    elif header_line.count("\t") >= 5:
        delim = "\t"
    else:
        # fallback: let csv.Sniffer try
        try:
            delim = csv.Sniffer().sniff(header_line, delimiters=";,\t").delimiter
        except Exception:
            delim = ";"

    reader = csv.reader(lines, delimiter=delim)
    header = next(reader)
    h = [c.strip().lower() for c in header]

    def find_col(names: List[str]) -> Optional[int]:
        for nm in names:
            if nm in h:
                return h.index(nm)
        return None

    iy = find_col(["year", "yyyy"])
    im = find_col(["month", "mm"])
    iday = find_col(["day", "dd"])
    imjd = find_col(["mjd"])

    # UT1-UTC column: exact match first, then fuzzy match
    iut1 = None
    for cand in ["ut1-utc", "ut1 - utc", "ut1_utc", "ut1utc"]:
        if cand in h:
            iut1 = h.index(cand)
            break
    if iut1 is None:
        for j, name in enumerate(h):
            if "ut1" in name and "utc" in name:
                iut1 = j
                break
    if iut1 is None:
        raise RuntimeError(f"Could not locate UT1-UTC column. Header: {header}")

    rows: List[EOPRow] = []
    for row in reader:
        if not row or len(row) <= iut1:
            continue

        # parse UT1-UTC
        s_ut1 = row[iut1].strip()
        if not s_ut1:
            continue
        try:
            ut1 = float(s_ut1)
        except ValueError:
            continue

        d: Optional[date] = None
        if iy is not None and im is not None and iday is not None:
            try:
                y = int(row[iy]); m = int(row[im]); dd = int(row[iday])
                d = date(y, m, dd)
            except Exception:
                d = None
        elif imjd is not None:
            try:
                mjd = float(row[imjd])
                d = _mjd_to_date(mjd)
            except Exception:
                d = None

        if d is None:
            continue

        rows.append(EOPRow(d=d, ut1_utc=ut1))

    if not rows:
        raise RuntimeError("Parsed 0 EOP rows from IERS CSV (delimiter/header mismatch?)")

    rows.sort(key=lambda r: r.d)
    return rows


def _mjd_to_date(mjd: float) -> date:
    # MJD 0 = 1858-11-17
    from datetime import timedelta
    base = date(1858, 11, 17)
    return base + timedelta(days=int(mjd))


# -----------------------------
# Monthly aggregation
# -----------------------------
def _month_midpoint(y: int, m: int) -> date:
    # pick 15th as stable midpoint
    return date(y, m, 15)


def _decimal_year(d: date) -> float:
    y = d.year
    start = date(y, 1, 1)
    end = date(y + 1, 1, 1)
    return y + (d - start).days / (end - start).days

def _month_center_decimal_year(y: int, m: int) -> float:
    # exact month-center grid: y + (m-0.5)/12
    return y + (m - 0.5) / 12.0

def _end_of_month(y: int, m: int) -> date:
    if m == 12:
        return date(y, 12, 31)
    return date(y, m + 1, 1).fromordinal(date(y, m + 1, 1).toordinal() - 1)

def build_monthly_table(eops: List[EOPRow], leaps: List[LeapEntry]) -> List[Tuple[float, int, int, date, int, float, float]]:
    """
    Returns rows:
      (decimal_year, year, month, sample_date, tai_utc, ut1_utc, delta_t_seconds)
    using sample_date = 15th of each month.
    """
    # index UT1-UTC by date
    ut1_by_date: Dict[date, float] = {r.d: r.ut1_utc for r in eops}

    # available range in EOP
    d0, d1 = eops[0].d, eops[-1].d
    first_leap_date = leaps[0].utc_date  # should be 1972-01-01    

    out = []
    y0, y1 = d0.year, d1.year

    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            d = _month_midpoint(y, m)
            if d < d0 or d > d1:
                continue

            # if missing exactly on 15th, search nearest within +/-3 days
            ut1 = None
            for k in [0, -1, 1, -2, 2, -3, 3]:
                dd = d.fromordinal(d.toordinal() + k)
                if dd in ut1_by_date:
                    ut1 = ut1_by_date[dd]
                    d_use = dd
                    break
            if d_use < first_leap_date:
                continue
            if ut1 is None:
                # try: last available EOP date within the same month (for tail months)
                # scan backwards from min(d1, end_of_month) up to 31 days
                end = _end_of_month(y, m)
                dd = min(d1, end)
                found = None
                for k in range(0, 32):
                    dtry = dd.fromordinal(dd.toordinal() - k)
                    if dtry.month != m:
                        break
                    if dtry in ut1_by_date:
                        found = dtry
                        ut1 = ut1_by_date[dtry]
                        d_use = dtry
                        break
                if found is None:
                    continue

            tai_utc = tai_minus_utc_for_day(leaps, d_use)
            delta_t = (tai_utc + 32.184) - ut1  # seconds
            out.append((_month_center_decimal_year(y, m), y, m, d_use, tai_utc, float(ut1), float(delta_t)))

    if not out:
        raise RuntimeError("Built 0 monthly ΔT rows (unexpected)")
    return out


def default_output_path() -> Path:
    # default: user cache (works for non-editable installs)
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        base = Path(xdg) / "caltib"
    else:
        base = Path.home() / ".cache" / "caltib"
    base.mkdir(parents=True, exist_ok=True)
    return base / "deltat_iers_monthly.csv"


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Update caltib ΔT monthly table from IERS C04 + leap seconds.")
    p.add_argument("--out", default=None, help="Output CSV path (default: ~/.cache/caltib/deltat_iers_monthly.csv)")
    p.add_argument("--also-write-package", action="store_true",
                   help="Also overwrite src/caltib/reference/data/deltat_iers_monthly.csv (for repo maintenance).")
    args = p.parse_args(argv)

    print("Downloading IERS C04 CSV ...")
    iers_text = _fetch(IERS_C04_CSV_URL)

    print("Downloading leap-seconds.list ...")
    leap_text = _fetch(LEAP_SECONDS_URL)

    print("Parsing ...")
    eops = _parse_iers_c04_csv(iers_text)
    leaps = _parse_leap_seconds_list(leap_text)

    print(f"IERS daily range: {eops[0].d} .. {eops[-1].d}")
    print(f"Leap list range: {leaps[0].utc_date} .. {leaps[-1].utc_date} (TAI-UTC last={leaps[-1].tai_minus_utc})")

    rows = build_monthly_table(eops, leaps)
    print(f"Monthly rows: {len(rows)}   (from {rows[0][1]:04d}-{rows[0][2]:02d} to {rows[-1][1]:04d}-{rows[-1][2]:02d})")

    out = Path(args.out) if args.out else default_output_path()
    out.parent.mkdir(parents=True, exist_ok=True)

    header = ["decimal_year", "year", "month", "sample_date", "tai_utc", "ut1_utc", "delta_t_seconds"]
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for (dec, y, m, d, tai, ut1, dt) in rows:
            w.writerow([f"{dec:.8f}", y, m, d.isoformat(), tai, f"{ut1:.6f}", f"{dt:.6f}"])

    print(f"Wrote: {out}")

    if args.also_write_package:
        pkg = Path(__file__).resolve().parents[2] / "reference" / "data" / "deltat_iers_monthly.csv"
        pkg.parent.mkdir(parents=True, exist_ok=True)
        pkg.write_text(out.read_text(), encoding="utf-8")
        print(f"Also wrote package table: {pkg}")

    print("\nTo make caltib use this file automatically, set:")
    print(f'  export CALTIB_DELTAT_TABLE="{out}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())