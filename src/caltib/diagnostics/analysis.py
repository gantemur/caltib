#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from caltib.api import get_calendar
from caltib.reference.time_scales import jd_utc_to_jd_tt, jd_tt_to_jd_utc
from caltib.reference.deltat import delta_t_seconds


def _need_numpy():
    try:
        import numpy as np
        return np
    except ImportError as e:
        raise RuntimeError('Need numpy. Install: pip install "caltib[tools]"') from e


def _need_matplotlib():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError as e:
        raise RuntimeError('Need matplotlib. Install: pip install "caltib[tools]"') from e


def rolling_std(y, window_pts: int):
    """
    Centered rolling std (ddof=0). Returns array with NaNs at ends.
    """
    import numpy as np
    n = len(y)
    out = np.full(n, np.nan)
    if window_pts < 3 or window_pts > n:
        return out
    w = window_pts
    half = w // 2
    for i in range(half, n - half):
        seg = y[i - half : i + half + 1]
        out[i] = float(np.std(seg, ddof=0))
    return out


def parabola_vertex(A: float, B: float, C: float) -> Tuple[float, float]:
    if abs(A) < 1e-20:
        return (float("nan"), float("nan"))
    x0 = -B / (2.0 * A)
    y0 = A * x0 * x0 + B * x0 + C
    return x0, y0


def drift_h_per_century(A: float, B: float, year: float) -> float:
    """
    If offset(y) = A y^2 + B y + C (hours), then d/dy = 2A y + B (hours/year).
    Return hours/century.
    """
    return (2.0 * A * year + B) * 100.0


def find_exact_syzygy(x: int, jd_guess: float, evaluator) -> float:
    """
    Finds the exact JD(TT) where elongation matches the absolute tithi x.
    Uses a highly efficient Secant root-finder seeded by the engine's true_date.
    """
    target_deg = (x % 30) * 12.0
    
    def error(jd: float) -> float:
        e = evaluator(jd)
        d = (e - target_deg) % 360.0
        if d > 180.0: d -= 360.0
        return d
        
    jd0 = jd_guess
    jd1 = jd_guess + 0.1
    e0 = error(jd0)
    e1 = error(jd1)
    
    for _ in range(15):
        if abs(e1) < 1e-6:
            break
        if e1 == e0:
            break
        jd_next = jd1 - e1 * (jd1 - jd0) / (e1 - e0)
        jd0, e0 = jd1, e1
        jd1 = jd_next
        e1 = error(jd1)
        
    return jd1


def analyze_one(
    np, 
    evaluator, 
    engine_name: str, 
    jd_start: float, 
    jd_end: float,
    time_mode: str,
    sigma_window_years: float,
    filter_hours: float,
    apply_delta_t: bool
) -> Dict[str, object]:
    
    eng = get_calendar(engine_name)
    x_start = eng.day.get_x_from_t2000(jd_start - 2451545.0)
    x_end = eng.day.get_x_from_t2000(jd_end - 2451545.0)
    
    x_year_list, offsets_list = [], []
    
    for x in range(x_start, x_end + 1):
        if x % 30 != 0:
            continue
            
        n = (x // 30) - 1
        try:
            Y, M, _ = eng.month.label_from_lunation(n)
        except AttributeError:
            info = eng.month.get_month_info(n)
            Y, M = info["year"], info["month"]
            
        x_year = Y + (M - 0.5) / 12.0
        
        # Rigorous Time Scale Alignment
        if time_mode == "civil":
            # Civil date is explicitly evaluated in UTC/UT1
            t_engine_utc = float(eng.day.local_civil_date(x)) + 2451545.0
            # Convert guess to TT so the ephemeris evaluator uses continuous orbit time
            t_engine_tt = jd_utc_to_jd_tt(t_engine_utc)
        else:
            try:
                t_engine_tt = float(eng.day.true_date(x)) + 2451545.0
            except AttributeError:
                t_engine_tt = float(eng.day.treu_date(x)) + 2451545.0
                
        # Truth evaluated strictly in TT
        t_truth_tt = find_exact_syzygy(x, t_engine_tt, evaluator)
        
        # Transform coordinate back for subtraction if needed
        if time_mode == "civil":
            t_truth_utc = jd_tt_to_jd_utc(t_truth_tt)
            off_h = 24.0 * (t_engine_utc - t_truth_utc)
        else:
            off_h = 24.0 * (t_engine_tt - t_truth_tt)
        
        x_year_list.append(x_year)
        offsets_list.append(off_h)

    years = np.array(x_year_list, dtype=float)
    raw_offsets = np.array(offsets_list, dtype=float)

    # Historical mapping utility using your high-precision delta_t module
    if apply_delta_t:
        dt = np.array([delta_t_seconds(y) / 3600.0 for y in years], dtype=float)
        offsets = raw_offsets + dt
    else:
        offsets = raw_offsets

    mask = np.abs(offsets) < float(filter_hours)
    years_f = years[mask]
    off_f = offsets[mask]
    
    if len(off_f) < 200:
        raise RuntimeError(f"{engine_name}: too few samples after filtering ({len(off_f)})")

    order = np.argsort(years_f)
    years_f = years_f[order]
    off_f = off_f[order]

    # Quadratic drift fit
    A, B, C = np.polyfit(years_f, off_f, 2)
    vx, vy = parabola_vertex(A, B, C)

    # Rolling sigma
    diffs = np.diff(years_f)
    step = float(np.median(diffs[diffs > 0]))
    samples_per_year = max(1.0, 1.0 / step)
    window_pts = int(round(sigma_window_years * samples_per_year))
    if window_pts % 2 == 0:
        window_pts += 1

    sig = rolling_std(off_f, window_pts=window_pts)
    ok = np.isfinite(sig)
    
    if ok.sum() == 0:
        sigma_min_year = float("nan")
        sigma_min_val = float("nan")
    else:
        j = int(np.nanargmin(sig))
        sigma_min_year = float(years_f[j])
        sigma_min_val = float(sig[j])

    return {
        "engine": engine_name,
        "years": years_f,
        "offsets": off_f,
        "sig": sig,
        "fit_coeffs": (float(A), float(B), float(C)),
        "vertex_year": float(vx),
        "vertex_offset": float(vy),
        "sigma_min_year": float(sigma_min_year),
        "sigma_min_val": float(sigma_min_val),
        "drift_0": float(drift_h_per_century(A, B, 0.0)),
        "drift_1000": float(drift_h_per_century(A, B, 1000.0)),
        "drift_2000": float(drift_h_per_century(A, B, 2000.0)),
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Final metrics: sigma minima + drift vertices + drift rates.")
    p.add_argument("--engines", default="phugpa,tsurphu,mongol,bhutan",
                   help='Comma list of engines, e.g. "phugpa,l1,l4".')
    p.add_argument("--ephem", choices=("ref", "de422"), default="ref", help="Reference Ephemeris or DE422")
    p.add_argument("--time", choices=("true", "civil"), default="true", help="Evaluate continuous true_date or snapped local_civil_date")
    p.add_argument("--year-start", type=int, default=-500)
    p.add_argument("--year-end", type=int, default=2500)
    p.add_argument("--sigma-window", type=float, default=100.0, help="Rolling sigma window (years)")
    p.add_argument("--filter-hours", type=float, default=50.0)
    p.add_argument("--apply-delta-t", action="store_true",
                   help="Apply rigorous ΔT to convert TT->UTC offset drift.")
    p.add_argument("--out-drift", default="analysis_drift.png")
    p.add_argument("--out-sigma", default="analysis_sigma.png")
    args = p.parse_args(argv)

    np = _need_numpy()
    plt = _need_matplotlib()

    y0, y1 = args.year_start, args.year_end
    if y1 < y0:
        raise SystemExit("--year-end must be >= --year-start")

    engines_list = [x.strip() for x in args.engines.split(",") if x.strip()]

    # Load Evaluator
    if args.ephem == "de422":
        try:
            from caltib.ephemeris.de422 import DE422Elongation
            el = DE422Elongation.load()
            def evaluator(jd): return el.elong_deg(jd)
        except ImportError as e:
            raise SystemExit("DE422 ephemeris tools not available. Use --ephem ref") from e
    else:
        from caltib.reference.solar import solar_longitude
        from caltib.reference.lunar import lunar_position
        def evaluator(jd):
            s = solar_longitude(jd)
            m = lunar_position(jd)
            return (m.L_true_deg - s.L_true_deg) % 360.0

    jd_start = datetime.date(y0 if y0 > 0 else 1, 1, 1).toordinal() + 1721425.5
    if y0 <= 0:
        jd_start += (y0 - 1) * 365.25
        
    jd_end = datetime.date(y1, 12, 31).toordinal() + 1721425.5

    print(f"Evaluating metrics for {len(engines_list)} engines against {args.ephem.upper()} ({y0} to {y1})...")

    results: List[Dict[str, object]] = []
    for eng_name in engines_list:
        try:
            res = analyze_one(
                np=np,
                evaluator=evaluator,
                engine_name=eng_name,
                jd_start=jd_start,
                jd_end=jd_end,
                time_mode=args.time,
                sigma_window_years=float(args.sigma_window),
                filter_hours=float(args.filter_hours),
                apply_delta_t=bool(args.apply_delta_t),
            )
            results.append(res)
            print(f"  Processed {eng_name} successfully.")
        except Exception as e:
            print(f"  Failed {eng_name}: {e}")

    if not results:
        raise SystemExit("No successful results.")

    # Print summary table
    print("\n" + "=" * 115)
    print(f"{'ENGINE':<12} | {'SIGMA MIN':<10} | {'VERTEX':<10} | {'DRIFT(0)':<10} | {'DRIFT(1000)':<11} | {'DRIFT(2000)':<11}")
    print(f"{'':<12} | {'(AD)':<10} | {'(AD)':<10} | {'(h/cy)':<10} | {'(h/cy)':<11} | {'(h/cy)':<11}")
    print("-" * 115)
    for r in results:
        print(
            f"{r['engine']:<12} | "
            f"{r['sigma_min_year']:<10.0f} | "
            f"{r['vertex_year']:<10.0f} | "
            f"{r['drift_0']:<10.4f} | "
            f"{r['drift_1000']:<11.4f} | "
            f"{r['drift_2000']:<11.4f}"
        )
    print("-" * 115)
    print("NOTE: Drift is d/dY of the fitted offset curve, reported in hours/century.")
    if args.apply_delta_t:
        print("NOTE: Rigorous ΔT correction applied: offsets ≈ (Tib_TT - TT_Truth) + ΔT(year).")
    print("=" * 115 + "\n")

    color_map = {
        "phugpa": "tab:orange", "mongol": "tab:blue", "tsurphu": "tab:purple", 
        "bhutan": "tab:green", "karana": "tab:red", "l0": "tab:brown", 
        "l1": "tab:pink", "l2": "tab:cyan", "l3": "tab:olive", "l4": "gold"
    }

    # Plot 1: Drift fit curves
    plt.figure(figsize=(10, 6))
    for r in results:
        years = r["years"]
        A, B, C = r["fit_coeffs"]
        fit = A * years**2 + B * years + C
        c = color_map.get(r["engine"], "black")
        plt.plot(years, fit, linewidth=2, color=c, label=f"{r['engine']} (v~{r['vertex_year']:.0f})")
        
    plt.title(f"Mean Drift [{args.time} time]" + (" — ΔT corrected" if args.apply_delta_t else ""))
    plt.xlabel("Lunar Year Coordinate: Y + (M-0.5)/12")
    plt.ylabel(f"Offset (hours)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.out_drift, dpi=200)
    print(f"Saved: {args.out_drift}")

    # Plot 2: Rolling sigma curves
    plt.figure(figsize=(10, 6))
    for r in results:
        c = color_map.get(r["engine"], "black")
        plt.plot(r["years"], r["sig"], linewidth=2, color=c, label=f"{r['engine']} (min~{r['sigma_min_year']:.0f})")

    plt.title(f"Spread / Sigma (rolling {args.sigma_window:g}y window)")
    plt.xlabel("Lunar Year Coordinate: Y + (M-0.5)/12")
    plt.ylabel("Standard Deviation (hours)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(args.out_sigma, dpi=200)
    print(f"Saved: {args.out_sigma}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())