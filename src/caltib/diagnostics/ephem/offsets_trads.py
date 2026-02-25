#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import caltib
from caltib.ephemeris.de422 import (
    DE422Elongation,
    build_new_moons,
    tithi_boundary_in_lunation,
    wrap180,
)


def wrap_signed_hours(h: float) -> float:
    return ((h + 12.0) % 24.0) - 12.0


def circular_mean_mod24(hours_mod24) -> float:
    # hours_mod24 in [0,24)
    theta = [2.0 * math.pi * (x / 24.0) for x in hours_mod24]
    c = sum(math.cos(t) for t in theta) / len(theta)
    s = sum(math.sin(t) for t in theta) / len(theta)
    ang = math.atan2(s, c) % (2.0 * math.pi)
    return 24.0 * ang / (2.0 * math.pi)


def match_monotone(t_tib: List[float], moons: List[float]) -> List[int]:
    """
    Match each tib timestamp to nearest moon timestamp with monotone k.
    """
    if not t_tib:
        return []
    k_prev = min(range(len(moons)), key=lambda j: abs(t_tib[0] - moons[j]))
    out = [k_prev]
    for t in t_tib[1:]:
        # allow small look-ahead
        lo = max(0, k_prev - 1)
        hi = min(len(moons), k_prev + 6)
        k = min(range(lo, hi), key=lambda j: abs(t - moons[j]))
        if k < k_prev:
            k = k_prev
        out.append(k)
        k_prev = k
    return out


def iter_lunations_for_year(engine: str, Y: int) -> Tuple[int, int]:
    """
    Return (n_start, n_last) for lunar year Y using public API:
      n_start = n(Y,1,False)
      n_last  = new_year_day(Y+1)["n_last"]  (last month of year Y)
    """
    n_start = caltib.month_bounds(Y, 1, is_leap_month=False, engine=engine)["n"]
    n_last = caltib.new_year_day(Y + 1, engine=engine)["n_last"]
    return int(n_start), int(n_last)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Histogram raw offsets: Tib true_date vs DE422 TT.")
    p.add_argument("--engine", default="phugpa", help="phugpa|tsurphu|mongol|bhutan|karana")
    p.add_argument("--year-start", type=int, default=1900)
    p.add_argument("--year-end", type=int, default=2100)
    p.add_argument("--mode", choices=("newmoon", "tithi"), default="newmoon")
    p.add_argument("--days", default="1-30", help='For tithi mode: "1-30" or "1,2,15,30"')
    p.add_argument("--max-months", type=int, default=0, help="0 means no cap")
    p.add_argument("--bins", type=int, default=100)
    p.add_argument("--out-csv", default="offsets_raw.csv")
    p.add_argument("--out-png", default="offsets_raw_hist.png")
    args = p.parse_args(argv)

    # parse days
    day_list: List[int] = []
    if args.mode == "tithi":
        s = args.days.strip()
        if "-" in s:
            a, b = s.split("-", 1)
            day_list = list(range(int(a), int(b) + 1))
        else:
            day_list = [int(x) for x in s.split(",") if x.strip()]
        if not day_list:
            raise SystemExit("No days parsed")

    # Get internal engine object to access true_date(d,n) (trad mode).
    # For the ephem diagnostics we can keep this internal; later we can expose true_date_dn.
    from caltib import api as _api
    eng_obj = _api._reg().get(args.engine)

    # Build lunation list over years
    n_months: List[int] = []
    months_meta: List[Tuple[int, int]] = []  # (Y, n)
    for Y in range(args.year_start, args.year_end + 1):
        n0, n1 = iter_lunations_for_year(args.engine, Y)
        for n in range(n0, n1 + 1):
            n_months.append(n)
            months_meta.append((Y, n))
            if args.max_months and len(n_months) >= args.max_months:
                break
        if args.max_months and len(n_months) >= args.max_months:
            break

    if not n_months:
        raise SystemExit("No lunations selected")

    # Tib times to compare (float JD-like days from true_date)
    t_tib_raw: List[float] = []
    if args.mode == "newmoon":
        # boundary at end of day 30 of previous lunation
        for n in n_months:
            t = eng_obj.day.true_date(30, n - 1)  # Fraction
            t_tib_raw.append(float(t))
    else:
        # all chosen tithi boundaries inside each lunation
        for n in n_months:
            for d in day_list:
                t = eng_obj.day.true_date(d, n)
                t_tib_raw.append(float(t))

    t_min, t_max = min(t_tib_raw), max(t_tib_raw)

    # DE422: build new moons covering window
    el = DE422Elongation.load()
    print(f"Building DE422 new moons over TT JD ~ [{t_min:.1f}, {t_max:.1f}] ...")
    moons = build_new_moons(el, t_min - 30.0, t_max + 30.0)

    # Match each month boundary to nearest DE new moon (monotone)
    if args.mode == "newmoon":
        k_match = match_monotone(t_tib_raw, moons)

    # Compute diffs in hours
    diffs_h: List[float] = []
    rows = []

    if args.mode == "newmoon":
        for (Y, n), t_tib, k in zip(months_meta, t_tib_raw, k_match):
            t_de = moons[k]
            dh = 24.0 * (t_tib - t_de)
            diffs_h.append(dh)
            rows.append((Y, n, 30, t_tib, t_de, dh, k))
    else:
        # Need lunation-to-moon mapping for each lunation n:
        # match tib month boundary times for these lunations using end(30,n-1)
        t_bound = [float(eng_obj.day.true_date(30, n - 1)) for n in n_months]
        k_bound = match_monotone(t_bound, moons)
        n_to_k = {n: k for n, k in zip(n_months, k_bound)}

        for (Y, n) in months_meta:
            k = n_to_k[n]
            t0 = moons[k]
            t1 = moons[k + 1]
            for d in day_list:
                t_tib = float(eng_obj.day.true_date(d, n))
                t_de = tithi_boundary_in_lunation(el, t0, t1, d)
                dh = 24.0 * (t_tib - t_de)
                diffs_h.append(dh)
                rows.append((Y, n, d, t_tib, t_de, dh, k))

    # summary
    import numpy as np
    arr = np.array(diffs_h, dtype=float)
    mean_h = float(arr.mean())
    med_h = float(np.median(arr))
    mean_mod24 = float(circular_mean_mod24((arr % 24.0)))
    print(f"N={len(arr)}  mean={mean_h:.4f}h  median={med_h:.4f}h  circmean_mod24={mean_mod24:.4f}h")

    # write CSV
    with open(args.out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Y", "n", "d", "t_tib_raw", "t_de_tt", "diff_hours", "k"])
        w.writerows(rows)
    print(f"Wrote {args.out_csv}")

    # histogram
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise RuntimeError("matplotlib not installed. Install: pip install \"caltib[diagnostics]\"") from e

    plt.figure(figsize=(10, 6))
    plt.hist(arr, bins=args.bins, alpha=0.7, edgecolor="black")
    plt.axvline(mean_h, linestyle="--", label=f"Mean: {mean_h:.2f}h")
    plt.xlabel("Raw Difference (Tib true_date - DE422 TT) [hours]")
    plt.ylabel("Count")
    plt.title(f"Raw Offset Distribution: {args.engine} vs DE422 ({args.mode})")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.out_png)
    print(f"Wrote {args.out_png}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())