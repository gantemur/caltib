from __future__ import annotations

"""
caltib.reference.deltat

Reference-quality ΔT (= TT − UT1) model intended for *design* and *diagnostics*.

Philosophy
----------
- Prefer *tabulated* modern ΔT derived from IERS Earth Orientation Parameters (UT1−UTC)
  together with the leap-second schedule (TAI−UTC). This is the most faithful way to
  recover ΔT in the leap-second era.
- Outside the table coverage, fall back to the standard Espenak–Meeus (NASA) piecewise
  polynomials used in eclipse work (valid across roughly −1999..+3000).

This module is *not* used by calendar engines. Engines should keep their own simple
ΔT models (if any) for historical fidelity and reproducibility.

Data sources (recommended)
--------------------------
- IERS EOP 14 C04 (daily UT1−UTC) for 1962–present (we use 1972–present here because
  leap-seconds.list is defined from 1972-01-01 in the modern integer-leap system).
- leap-seconds.list (public-domain IERS/NTP format via IANA).

The package may ship a snapshot table:
  caltib/reference/data/deltat_iers_monthly.csv
generated from those sources (see design/ephem tooling).
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Iterator, Optional, Tuple
import math

# stdlib-only: avoid numpy/pandas; keep this light and embeddable.
import csv
import importlib
import importlib.resources
import datetime as _dt


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def decimal_year(year: int, month: int = 1, day: float = 1.0) -> float:
    """Decimal year; day may be fractional. Uses the simple 365/366 day count."""
    # Day-of-year
    d0 = _dt.date(year, 1, 1)
    di = _dt.date(year, month, int(day))
    doy = (di - d0).days + 1 + (day - int(day))
    days_in_year = 366 if _dt.date(year, 12, 31).toordinal() - d0.toordinal() + 1 == 366 else 365
    return year + (doy - 0.5) / days_in_year


def delta_t_for_date(d: _dt.date, *, method: str = "best") -> float:
    """Convenience wrapper: ΔT for a Gregorian date (UTC calendar)."""
    y = decimal_year(d.year, d.month, float(d.day))
    return delta_t_seconds(y, method=method)



# ---------------------------------------------------------------------------
# Table model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeltaTTable:
    """
    Piecewise-linear ΔT table over decimal-year coordinate.
    """
    x: Tuple[float, ...]   # decimal years (strictly increasing)
    y: Tuple[float, ...]   # ΔT in seconds

    def __len__(self) -> int:
        return len(self.x)

    def __iter__(self) -> Iterator[Tuple[float, float]]:
        """
        Iterate over (decimal_year, delta_t_seconds) pairs.
        """
        return iter(zip(self.x, self.y))

    def items(self) -> Tuple[Tuple[float, float], ...]:
        """
        Convenience: return all (x,y) pairs as a tuple.
        """
        return tuple(zip(self.x, self.y))

    def eval(self, xq: float) -> float:
        if not (self.x[0] <= xq <= self.x[-1]):
            raise ValueError(f"x out of range [{self.x[0]}, {self.x[-1]}]: {xq}")
        # binary search
        lo, hi = 0, len(self.x) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.x[mid] <= xq:
                lo = mid
            else:
                hi = mid
        x0, x1 = self.x[lo], self.x[hi]
        y0, y1 = self.y[lo], self.y[hi]
        if x1 == x0:
            return y0
        t = (xq - x0) / (x1 - x0)
        return y0 + t * (y1 - y0)

    @property
    def range(self) -> Tuple[float, float]:
        return (self.x[0], self.x[-1])


def _read_csv_xy(rows: Iterable[dict], *, xcol: str, ycol: str) -> DeltaTTable:
    xs: list[float] = []
    ys: list[float] = []
    for r in rows:
        xs.append(float(r[xcol]))
        ys.append(float(r[ycol]))
    # ensure strict monotonicity
    for i in range(1, len(xs)):
        if not (xs[i] > xs[i - 1]):
            raise ValueError("ΔT table x is not strictly increasing")
    return DeltaTTable(tuple(xs), tuple(ys))


@lru_cache(maxsize=1)
def load_iers_monthly_table() -> Optional[DeltaTTable]:
    """
    Load an IERS-derived monthly ΔT table (piecewise linear).

    Search order:
      1) CALTIB_DELTAT_TABLE environment variable (path to CSV)
      2) user cache (~/.cache/caltib/deltat_iers_monthly.csv or $XDG_CACHE_HOME/caltib/...)
      3) packaged data (caltib.reference.data/deltat_iers_monthly.csv)

    Expected CSV columns:
      decimal_year, ..., delta_t_seconds
    """
    import os
    from pathlib import Path

    # 1) explicit override
    p = os.environ.get("CALTIB_DELTAT_TABLE", "").strip()
    if p:
        path = Path(p).expanduser()
        if path.is_file():
            try:
                with path.open("r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    return _read_csv_xy(reader, xcol="decimal_year", ycol="delta_t_seconds")
            except Exception:
                pass  # fall through

    # 2) user cache (works for non-editable installs)
    xdg = os.environ.get("XDG_CACHE_HOME", "").strip()
    cache_dir = (Path(xdg).expanduser() / "caltib") if xdg else (Path.home() / ".cache" / "caltib")
    cache_path = cache_dir / "deltat_iers_monthly.csv"
    if cache_path.is_file():
        try:
            with cache_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                return _read_csv_xy(reader, xcol="decimal_year", ycol="delta_t_seconds")
        except Exception:
            pass  # fall through

    # 3) packaged data
    try:
        pkg = importlib.import_module("caltib.reference.data")
        path = importlib.resources.files(pkg).joinpath("deltat_iers_monthly.csv")
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return _read_csv_xy(reader, xcol="decimal_year", ycol="delta_t_seconds")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Espenak–Meeus (NASA) piecewise polynomial (fallback)
# ---------------------------------------------------------------------------

def _poly(u: float, coeffs: Tuple[float, ...]) -> float:
    """Horner evaluation for Σ coeffs[k] u^k."""
    acc = 0.0
    for c in reversed(coeffs):
        acc = acc * u + c
    return acc


def delta_t_em2006(y: float, *, apply_correction_c: bool = False) -> float:
    """
    Espenak–Meeus piecewise polynomial ΔT(y) in seconds.

    y is the decimal year (often y = year + (month-0.5)/12).
    The branch polynomials match those published by NASA for the Five Millennium Canon.

    apply_correction_c:
        If True, apply the lunar-secular-acceleration correction
        c = -0.000012932 (y-1955)^2 outside 1955..2005, as described
        in the Canon documentation. (Many users can leave this False.)
    """
    # (11) and (25): long-term parabola
    if y < -500.0:
        u = (y - 1820.0) / 100.0
        dt = -20.0 + 32.0 * u * u
    elif y < 500.0:
        # (12): u = y/100
        u = y / 100.0
        dt = _poly(u, (
            10583.6,
            -1014.41,
            33.78311,
            -5.952053,
            -0.1798452,
            0.022174192,
            0.0090316521,
        ))
    elif y < 1600.0:
        # (13): u=(y-1000)/100
        u = (y - 1000.0) / 100.0
        dt = _poly(u, (
            1574.2,
            -556.01,
            71.23472,
            0.319781,
            -0.8503463,
            -0.005050998,
            0.0083572073,
        ))
    elif y < 1700.0:
        # (14): t = y-1600
        t = y - 1600.0
        dt = 120.0 - 0.9808 * t - 0.01532 * t * t + (t ** 3) / 7129.0
    elif y < 1800.0:
        # (15): t=y-1700
        t = y - 1700.0
        dt = 8.83 + 0.1603 * t - 0.0059285 * t * t + 0.00013336 * (t ** 3) - (t ** 4) / 1174000.0
    elif y < 1860.0:
        # (16): t=y-1800
        t = y - 1800.0
        dt = _poly(t, (
            13.72,
            -0.332447,
            0.0068612,
            0.0041116,
            -0.00037436,
            0.0000121272,
            -0.0000001699,
            0.000000000875,
        ))
    elif y < 1900.0:
        # (17): t=y-1860
        t = y - 1860.0
        dt = 7.62 + 0.5737 * t - 0.251754 * (t ** 2) + 0.01680668 * (t ** 3) - 0.0004473624 * (t ** 4) + (t ** 5) / 233174.0
    elif y < 1920.0:
        # (18): t=y-1900
        t = y - 1900.0
        dt = -2.79 + 1.494119 * t - 0.0598939 * (t ** 2) + 0.0061966 * (t ** 3) - 0.000197 * (t ** 4)
    elif y < 1941.0:
        # (19): t=y-1920
        t = y - 1920.0
        dt = 21.20 + 0.84493 * t - 0.076100 * (t ** 2) + 0.0020936 * (t ** 3)
    elif y < 1961.0:
        # (20): t=y-1950
        t = y - 1950.0
        dt = 29.07 + 0.407 * t - (t ** 2) / 233.0 + (t ** 3) / 2547.0
    elif y < 1986.0:
        # (21): t=y-1975
        t = y - 1975.0
        dt = 45.45 + 1.067 * t - (t ** 2) / 260.0 - (t ** 3) / 718.0
    elif y < 2005.0:
        # (22): t=y-2000
        t = y - 2000.0
        dt = _poly(t, (
            63.86,
            0.3345,
            -0.060374,
            0.0017275,
            0.000651814,
            0.00002373599,
        ))
    elif y < 2050.0:
        # (23): t=y-2000
        t = y - 2000.0
        dt = 62.92 + 0.32217 * t + 0.005589 * (t ** 2)
    elif y < 2150.0:
        # (24): discontinuity-fix term
        u = (y - 1820.0) / 100.0
        dt = -20.0 + 32.0 * u * u - 0.5628 * (2150.0 - y)
    else:
        u = (y - 1820.0) / 100.0
        dt = -20.0 + 32.0 * u * u

    if apply_correction_c and (y < 1955.0 or y > 2005.0):
        dt += -0.000012932 * (y - 1955.0) ** 2

    return float(dt)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def delta_t_seconds(y: float, *, method: str = "best", blend_years: float = 30.0) -> float:
    """
    ΔT(y) in seconds, where y is a decimal year.

    method:
      - "best": use IERS-derived table when available/in-range, else polynomial fallback,
                with optional blending near table endpoints.
      - "iers": require the table and require in-range.
      - "em2006": polynomial only (Espenak–Meeus / NASA).

    blend_years:
      Width of the linear blend window (years) used by method="best"
      just outside the IERS table range. Set to 0 to disable blending.
    """
    method = method.lower().strip()
    if method not in {"best", "iers", "em2006"}:
        raise ValueError("method must be one of: best, iers, em2006")

    if method == "em2006":
        return delta_t_em2006(y)

    tbl = load_iers_monthly_table()
    if tbl is None:
        if method == "iers":
            raise RuntimeError('IERS ΔT table not installed. Reinstall with package data or regenerate.')
        return delta_t_em2006(y)

    a, b = tbl.range

    # table interior
    if a <= y <= b:
        return tbl.eval(y)

    if method == "iers":
        raise ValueError(f"y={y} out of IERS table range [{a},{b}]")

    # method == "best" beyond endpoints: blend if requested
    if blend_years is None or blend_years <= 0.0:
        return delta_t_em2006(y)

    # right-side blend (after table ends)
    if y > b:
        A = tbl.eval(b)
        B0 = delta_t_em2006(b)
        C = A - B0                       # offset so poly matches table at y=b
        w = min(1.0, max(0.0, (y - b) / blend_years))
        return delta_t_em2006(y) + (1.0 - w) * C

    return delta_t_em2006(y)

