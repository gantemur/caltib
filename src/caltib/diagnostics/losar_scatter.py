#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Tuple, Optional, List

import argparse

import caltib


def _need_numpy():
    try:
        import numpy as np
        return np
    except ImportError as e:
        raise RuntimeError('Need numpy. Install: pip install "caltib[diagnostics]"') from e


def _need_matplotlib():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError as e:
        raise RuntimeError('Need matplotlib. Install: pip install "caltib[diagnostics]"') from e


def day_of_year(d: date) -> int:
    return (d - date(d.year, 1, 1)).days + 1


def days_since_winter_solstice(d: date) -> int:
    """
    Days since winter solstice, with Dec 22 = 1.
    For a date in Jan/Feb/Mar, we measure from Dec 22 of the previous year.
    """
    ws = date(d.year - 1, 12, 22)
    return (d - ws).days + 1


def rolling_median(np, y, win: int = 11):
    """Centered rolling median with edge padding."""
    if win < 3:
        return y.astype(float)
    if win % 2 == 0:
        win += 1
    k = win // 2
    ypad = np.pad(y, (k, k), mode="edge")
    out = np.empty_like(y, dtype=float)
    for i in range(len(y)):
        out[i] = float(np.median(ypad[i : i + win]))
    return out


@dataclass(frozen=True)
class Style:
    label: str
    start_year: int
    color: str
    marker: str
    linewidths: float = 0.0
    size: float = 16.0
    hollow: bool = False
    jitter: float = 0.0


def build_series(np, engine: str, start_year: int, end_year: int, *, metric: str) -> Tuple["np.ndarray", "np.ndarray"]:
    years = np.arange(start_year, end_year + 1, dtype=int)
    y = np.empty_like(years, dtype=float)

    for i, Y in enumerate(years):
        ny = caltib.new_year_day(int(Y), engine=engine)  # returns Gregorian date (year >= 1)
        d = ny["date"]
        if metric == "doy":
            y[i] = float(day_of_year(d))
        elif metric == "since-solstice":
            y[i] = float(days_since_winter_solstice(d))
        else:
            raise ValueError("metric must be 'doy' or 'since-solstice'")

    return years, y


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Scatter plot of Losar/Tsagaan Sar dates across traditions.")
    p.add_argument("--end-year", type=int, default=2100)
    p.add_argument("--show-trend", action="store_true")
    p.add_argument("--trend-win", type=int, default=11, help="Rolling median window (odd recommended).")
    p.add_argument("--outbase", default="new_year_scatter", help="Output base name (writes .png and .pdf)")
    p.add_argument(
        "--metric",
        choices=("since-solstice", "doy"),
        default="since-solstice",
        help="Y-axis metric (default: days since Dec 22).",
    )
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    styles: Dict[str, Style] = {
        "phugpa":  Style("Phugpa", 1447, "tab:blue",   "o", linewidths=0.0, size=12, hollow=False, jitter=0.0),
        "mongol":  Style("Mongol", 1747, "0.45",       "o", linewidths=1.2, size=18, hollow=True,  jitter=0.0),
        "tsurphu": Style("Tsurphu",1447, "tab:red",    "_", linewidths=1.0, size=18, hollow=False, jitter=0.0),
        "bhutan":  Style("Bhutan", 1754, "tab:red",    "|", linewidths=1.0, size=18, hollow=False, jitter=0.0),
        # "karana": Style("Karana", 1027, "tab:purple", "o", linewidths=0.0, size=10, hollow=False, jitter=0.0),
    }

    plt.rcParams.update({
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "legend.fontsize": 10,
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
    })

    fig, ax = plt.subplots(figsize=(9.2, 4.8), constrained_layout=True)
    ax.set_axisbelow(True)
    ax.grid(True, which="major", color="0.88", linewidth=0.7)
    ax.minorticks_off()

    ax.set_xlabel("Gregorian year")
    if args.metric == "doy":
        ax.set_ylabel("Day-of-year (Jan 1 = 1)")
    else:
        ax.set_ylabel("Days since winter solstice (Dec 22 = 1)")
    ax.set_title("Losar / Tsagaan Sar days across traditions")

    # plot each tradition
    for eng, st in styles.items():
        x, y = build_series(np, eng, st.start_year, args.end_year, metric=args.metric)
        xj = x.astype(float) + st.jitter

        if st.hollow:
            ax.scatter(
                xj, y,
                s=st.size,
                marker=st.marker,
                facecolors="none",
                edgecolors=st.color,
                linewidths=st.linewidths,
                alpha=0.60,
                label=st.label,
            )
        else:
            ax.scatter(
                xj, y,
                s=st.size,
                marker=st.marker,
                c=st.color,
                linewidths=st.linewidths,
                alpha=0.35,
                label=st.label,
            )

        if args.show_trend:
            y_med = rolling_median(np, y, win=int(args.trend_win))
            ax.plot(
                x, y_med,
                color=st.color if not st.hollow else "0.30",
                linewidth=1.8,
                alpha=0.95,
            )

    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)

    outbase = args.outbase
#    fig.savefig(outbase + ".pdf")
    fig.savefig(outbase + ".png", dpi=300)
    print(f"Saved: {outbase}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())