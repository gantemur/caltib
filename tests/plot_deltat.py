#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date

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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Plot Delta T (TT-UT1) using caltib.reference.deltat.")
    p.add_argument("--y0", type=int, default=1600, help="start year")
    p.add_argument("--y1", type=int, default=2100, help="end year")
    p.add_argument("--step", type=float, default=0.25, help="sampling step in years (e.g., 0.1, 0.25, 1.0)")
    p.add_argument("--out", default="deltat.png", help="output image filename")
    p.add_argument("--show-poly", action="store_true", help="also plot polynomial-only fallback")
    p.add_argument("--show-table", action="store_true", help="scatter the monthly table points if present")
    args = p.parse_args(argv)

    if args.y1 < args.y0:
        raise SystemExit("--y1 must be >= --y0")

    np = _need_numpy()
    plt = _need_matplotlib()

    from caltib.reference import deltat as dt

    # dense evaluation grid
    ys = np.arange(float(args.y0), float(args.y1) + 1e-12, float(args.step), dtype=float)
    best = np.array([dt.delta_t_seconds(float(y), method="best") for y in ys], dtype=float)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(ys, best, linewidth=2, label="best (IERS table + poly)")

    poly = None
    if args.show_poly:
        poly = np.array([dt.delta_t_seconds(float(y), method="em2006") for y in ys], dtype=float)
        ax.plot(ys, poly, linewidth=1.5, linestyle="--", label="poly only (Espenak–Meeus)")

        # diff plot in its own figure/axes
        fig2, ax2 = plt.subplots(figsize=(10, 3))
        ax2.plot(ys, best - poly, linewidth=2)
        ax2.set_title("best - poly (seconds)")
        ax2.set_xlabel("Year")
        ax2.set_ylabel("ΔT_best - ΔT_poly")
        ax2.grid(True, alpha=0.3)
        fig2.tight_layout()
        fig2.savefig("deltat_diff.png", dpi=200)
        print("Saved: deltat_diff.png")

    if args.show_table:
        tbl = dt.load_iers_monthly_table()
        if tbl is None:
            print("No monthly table found.")
        else:
            y_tbl = np.array([x for (x, _) in tbl], dtype=float)
            dt_tbl = np.array([v for (_, v) in tbl], dtype=float)
            ax.scatter(y_tbl, dt_tbl, s=8, alpha=0.6, label="IERS monthly table")

    ax.set_title("Delta T = TT − UT1 (seconds)")
    ax.set_xlabel("Year")
    ax.set_ylabel("ΔT (s)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.out, dpi=200)
    print(f"Saved: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())