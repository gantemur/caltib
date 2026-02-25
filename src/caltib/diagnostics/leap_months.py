#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from matplotlib.colors import ListedColormap

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


@dataclass(frozen=True)
class Style:
    label: str
    engine: str
    marker: str
    size: float
    hollow: bool
    color: str = "0.15"
    lw: float = 1.2
    alpha: float = 0.95


DEFAULT_STYLES: Dict[str, Style] = {
    "phugpa": Style("Phugpa", "phugpa", marker="o", size=22, hollow=False),
    "tsurphu": Style("Tsurphu/Mongol", "tsurphu", marker="o", size=95, hollow=True),
    "mongol": Style("Tsurphu/Mongol", "mongol", marker="o", size=95, hollow=True),
    "bhutan": Style("Bhutan", "bhutan", marker="^", size=90, hollow=True),
    "karana": Style("Karana", "karana", marker="s", size=80, hollow=True),
}


def parse_engines(s: str) -> List[str]:
    out = [x.strip() for x in s.split(",") if x.strip()]
    if not (1 <= len(out) <= 3):
        raise SystemExit("--engines must contain 1 to 3 comma-separated engines")
    return out


def is_leap_label(engine: str, Y: int, M: int) -> bool:
    info = caltib.month_info(Y, M, engine=engine, debug=False)
    return bool(info.get("trigger", False))


def build_points(np, engine: str, start_year: int, end_year: int) -> Tuple["np.ndarray", "np.ndarray"]:
    xs, ys = [], []
    for Y in range(start_year, end_year + 1):
        for M in range(1, 13):
            if is_leap_label(engine, Y, M):
                xs.append(Y)
                ys.append(M)
    return np.array(xs, dtype=int), np.array(ys, dtype=int)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Leap-month barcode diagram across traditions (square cell grid only)."
    )
    p.add_argument("--start-year", type=int, default=1960)
    p.add_argument("--end-year", type=int, default=2030)
    p.add_argument("--out", default="leapmonth_barcode.png")
    p.add_argument("--title", default="Leap month pattern across traditions")
    p.add_argument(
        "--engines",
        default="phugpa,tsurphu,bhutan",
        help="Comma list of 1-3 engines to plot (default: phugpa,tsurphu,bhutan).",
    )

    # labeling controls (no tick marks)
    p.add_argument(
        "--labels",
        choices=("none", "years", "months", "both"),
        default="both",
        help="Which axis labels to show (tick marks are always suppressed).",
    )
    p.add_argument(
        "--year-step",
        type=int,
        default=5,
        help="If year labels are shown, label every k years (default: 5).",
    )
    p.add_argument(
        "--month-labels",
        choices=("sparse", "all"),
        default="sparse",
        help="If month labels are shown: sparse=1,3,6,9,12; all=1..12.",
    )

    # grid appearance
    p.add_argument("--cell-edge", default="0.88", help="Cell border color (matplotlib gray string).")
    p.add_argument("--cell-lw", type=float, default=0.6, help="Cell border line width.")
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    start_year, end_year = args.start_year, args.end_year
    if end_year < start_year:
        raise SystemExit("--end-year must be >= --start-year")

    engines = parse_engines(args.engines)
    styles: List[Style] = []
    for e in engines:
        if e not in DEFAULT_STYLES:
            raise SystemExit(f"Unknown engine '{e}'. Known: {sorted(DEFAULT_STYLES.keys())}")
        styles.append(DEFAULT_STYLES[e])

    fig, ax = plt.subplots(figsize=(16, 3.6))

    # --- square cell grid ONLY (no extra grid lines) ---
    x_edges = np.arange(start_year - 0.5, end_year + 1.5, 1.0)
    y_edges = np.arange(0.5, 13.5, 1.0)  # 0.5..12.5 edges

    Z = np.zeros((12, end_year - start_year + 1), dtype=float)

    white = ListedColormap(["white"])
    ax.pcolormesh(
        x_edges,
        y_edges,
        Z,
        shading="flat",
        cmap=white,           # <- all faces white
        vmin=0, vmax=1,
        edgecolors=args.cell_edge,
        linewidth=float(args.cell_lw),
        antialiased=True,
        zorder=0,
    )

    ax.set_xlim(start_year - 0.5, end_year + 0.5)
    ax.set_ylim(0.5, 12.5)
    ax.grid(False)

    # --- labels without tick marks ---
    ax.tick_params(axis="both", which="both", length=0)

    show_years = args.labels in ("years", "both")
    show_months = args.labels in ("months", "both")

    if show_years:
        step = max(1, int(args.year_step))
        xt = list(range(start_year, end_year + 1, step))
        ax.set_xticks(xt)
        ax.set_xticklabels([str(y) for y in xt])
        ax.set_xlabel("Gregorian year")
    else:
        ax.set_xticks([])
        ax.set_xticklabels([])
        ax.set_xlabel("")

    if show_months:
        yt = list(range(1, 13)) if args.month_labels == "all" else [1, 3, 6, 9, 12]
        ax.set_yticks(yt)
        ax.set_yticklabels([str(m) for m in yt])
        ax.set_ylabel("Leap month label (month number)")
    else:
        ax.set_yticks([])
        ax.set_yticklabels([])
        ax.set_ylabel("")

    # --- plot markers at cell centers ---
    for st in styles:
        x, m = build_points(np, st.engine, start_year, end_year)
        if st.hollow:
            ax.scatter(
                x, m,
                s=st.size,
                marker=st.marker,
                facecolors="none",
                edgecolors=st.color,
                linewidths=st.lw,
                alpha=st.alpha,
                label=st.label,
                zorder=5,
            )
        else:
            ax.scatter(
                x, m,
                s=st.size,
                marker=st.marker,
                c=st.color,
                linewidths=0.0,
                alpha=st.alpha,
                label=st.label,
                zorder=5,
            )

    ax.set_title(args.title)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False)
    fig.tight_layout()
    fig.savefig(args.out, dpi=250)
    print(f"Saved: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())