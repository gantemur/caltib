from __future__ import annotations

import argparse
from datetime import date
import sys
import re
import importlib
import inspect


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_ymd(s: str) -> date:
    y, m, d = map(int, s.split("-"))
    return date(y, m, d)


def _run_module_main(modpath: str, argv: list[str]) -> int:
    """
    Import module and run its main().

    Supports:
      - main(argv: list[str] | None = None) -> int|None
      - main() -> int|None
    """
    mod = importlib.import_module(modpath)
    if not hasattr(mod, "main"):
        raise SystemExit(f"Module {modpath} has no main()")
    fn = getattr(mod, "main")

    sig = inspect.signature(fn)
    if len(sig.parameters) == 0:
        rv = fn()
    else:
        rv = fn(argv)
    return int(rv or 0)


def cmd_day(argv: list[str]) -> int:
    import caltib

    p = argparse.ArgumentParser(prog="caltib day", description="Gregorian -> Tibetan day label")
    p.add_argument("date", help="YYYY-MM-DD")
    p.add_argument("--engine", default="phugpa")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--attr", action="append", default=[], help="attribute name (repeatable)")
    args = p.parse_args(argv)

    info = caltib.day_info(_parse_ymd(args.date), engine=args.engine, attributes=tuple(args.attr), debug=args.debug)
    print(info)
    return 0

def cmd_astro_args(argv: list[str]) -> int:
    import argparse
    from caltib.reference import astro_args as aa

    p = argparse.ArgumentParser(prog="caltib astro-args", description="Print astronomical fundamental arguments at a given JD(TT).")
    p.add_argument("--jd-tt", type=float, default=2451545.0, help="Julian Date in TT (default: J2000.0 = 2451545.0)")
    p.add_argument("--eps-model", choices=["iau2000", "iau1980"], default="iau2000", help="Mean obliquity model")
    p.add_argument("--k", type=float, default=0.0, help="Lunation index for mean new moon (Meeus), default 0")
    args = p.parse_args(argv)

    jd = float(args.jd_tt)
    T = aa.T_centuries(jd)

    fa = aa.fundamental_args(T)
    sm = aa.solar_mean_elements(T)
    eps = aa.mean_obliquity_deg(T, model=args.eps_model)

    print(f"JD_TT = {jd:.6f}")
    print(f"T (Julian centuries from J2000.0) = {T:.12f}")
    print()
    print("Fundamental arguments (degrees, wrapped to [0,360))")
    print(f"  L'     = {fa.Lp_deg:.10f}")
    print(f"  D      = {fa.D_deg:.10f}")
    print(f"  M      = {fa.M_deg:.10f}")
    print(f"  M'     = {fa.Mp_deg:.10f}")
    print(f"  F      = {fa.F_deg:.10f}")
    print(f"  Omega  = {fa.Omega_deg:.10f}")
    print()
    print("Solar mean elements (degrees)")
    print(f"  L0     = {sm.L0_deg:.10f}")
    print(f"  M      = {sm.M_deg:.10f}")
    print()
    print(f"Mean obliquity eps ({args.eps_model}) = {eps:.10f} deg")
    print()
    print("Representative mean periods (days)")
    print(f"  Y_trop(T) = {aa.tropical_year_days(T):.10f}")
    print(f"  S_syn(T)  = {aa.synodic_month_days(T):.10f}")
    print(f"  Y_anom(T) = {aa.anomalistic_year_days(T):.10f}")
    print(f"  S_anom(T) = {aa.anomalistic_month_days(T):.10f}")
    print()
    print("Mean new moon (Meeus)")
    print(f"  k = {args.k:g}  ->  JDE_mean_new_moon = {aa.jde_mean_new_moon(args.k):.8f} (TT)")

    return 0

def cmd_solar(argv: list[str]) -> int:
    import argparse
    from caltib.reference import solar
    from caltib.reference import astro_args as aa
    from caltib.reference import time_scales as ts

    p = argparse.ArgumentParser(prog="caltib solar", description="Calculate true/apparent solar longitude, EOT, and sunrise.")
    p.add_argument("--jd-utc", type=float, default=2451545.0, help="Julian Date in UTC")
    p.add_argument("--lat", type=float, default=48, help="Observer latitude in degrees")
    p.add_argument("--lon", type=float, default=107, help="Observer longitude in degrees (positive East)")
    p.add_argument("--eps-model", choices=["iau2000", "iau1980"], default="iau2000", help="Mean obliquity model")
    args = p.parse_args(argv)

    jd_utc = args.jd_utc
    jd_tt = ts.jd_utc_to_jd_tt(jd_utc)
    
    coords = solar.solar_longitude(jd_tt)
    eps = aa.mean_obliquity_deg(aa.T_centuries(jd_tt), model=args.eps_model)
    delta = solar.solar_declination_deg(coords.L_app_deg, eps)
    eot = solar.equation_of_time_minutes(jd_tt, eps_model=args.eps_model)

    print(f"Time Input:")
    print(f"  JD_UTC = {jd_utc:.6f}")
    print(f"  JD_TT  = {jd_tt:.6f}")
    print()
    print("Solar Position (degrees):")
    print(f"  True Longitude     (L_true) = {coords.L_true_deg:.6f}")
    print(f"  Apparent Longitude (L_app)  = {coords.L_app_deg:.6f}")
    print(f"  Declination        (delta)  = {delta:.6f}")
    print()
    print(f"Equation of Time:")
    print(f"  EOT (minutes) = {eot:.4f}")
    print()
    
    print("Sunrise & Sunset (-0.833 deg altitude):")
    app_times = solar.sunrise_apparent_time(jd_tt, args.lat, eps_model=args.eps_model)
    if app_times:
        print(f"  Local Apparent Rise: {app_times.rise_app_hours:.4f} h")
        print(f"  Local Apparent Set : {app_times.set_app_hours:.4f} h")
    else:
        print("  Local Apparent: Sun does not rise or set.")

    civil_times = solar.sunrise_sunset_utc(jd_utc, args.lat, args.lon, eps_model=args.eps_model)
    if civil_times:
        # Convert fractional hours to HH:MM:SS
        def fmt_time(h: float) -> str:
            h_int = int(h)
            m = (h - h_int) * 60
            m_int = int(m)
            s = (m - m_int) * 60
            return f"{h_int:02d}:{m_int:02d}:{s:05.2f}"
            
        print(f"  UTC Clock Rise     : {fmt_time(civil_times.rise_utc_hours)}")
        print(f"  UTC Clock Set      : {fmt_time(civil_times.set_utc_hours)}")
    else:
        print("  UTC Clock: Sun does not rise or set.")

    return 0

def cmd_lunar(argv: list[str]) -> int:
    import argparse
    from caltib.reference import lunar
    from caltib.reference import solar
    from caltib.reference import astro_args as aa

    p = argparse.ArgumentParser(
        prog="caltib lunar", 
        description="Calculate true/apparent lunar longitude, latitude, and elongation."
    )
    p.add_argument(
        "--jd-tt", 
        type=float, 
        default=2451545.0, 
        help="Julian Date in TT (default: J2000.0 = 2451545.0)"
    )
    args = p.parse_args(argv)

    jd_tt = args.jd_tt
    
    # Calculate both lunar and solar coordinates
    moon_coords = lunar.lunar_position(jd_tt)
    sun_coords = solar.solar_longitude(jd_tt)
    
    # Calculate elongations and wrap to [0, 360)
    elongation_true = aa.wrap_deg(moon_coords.L_true_deg - sun_coords.L_true_deg)
    elongation_app = aa.wrap_deg(moon_coords.L_app_deg - sun_coords.L_app_deg)

    print(f"Time Input:")
    print(f"  JD_TT = {jd_tt:.6f}")
    print()
    print("Lunar Position (degrees):")
    print(f"  True Longitude     (L_true) = {moon_coords.L_true_deg:.6f}")
    print(f"  Apparent Longitude (L_app)  = {moon_coords.L_app_deg:.6f}")
    print(f"  True Latitude      (B_true) = {moon_coords.B_true_deg:.6f}")
    print()
    print("Elongation (Moon - Sun, degrees):")
    print(f"  True Elongation             = {elongation_true:.6f}")
    print(f"  Apparent Elongation         = {elongation_app:.6f}")

    return 0

def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Backward compatibility: `caltib YYYY-MM-DD ...`
    if argv and _DATE_RE.match(argv[0]):
        return cmd_day(argv)

    p = argparse.ArgumentParser(prog="caltib", description="Tibetan calendar toolkit CLI.")
    sub = p.add_subparsers(dest="cmd", required=True)

    # day
    p_day = sub.add_parser("day", help="Gregorian -> Tibetan day label")
    p_day.add_argument("date", help="YYYY-MM-DD")
    p_day.add_argument("--engine", default="phugpa")
    p_day.add_argument("--debug", action="store_true")
    p_day.add_argument("--attr", action="append", default=[], help="attribute name (repeatable)")

    # diagnostics (non-ephem)
    sub.add_parser("pretty-month", help="Print lunar/Gregorian month calendars (diagnostics)")
    sub.add_parser("new-years", help="Print New Year table (diagnostics)")

    # diagnostics (non-ephem)
    p_diag = sub.add_parser("diag", help="Diagnostics tools (no ephemeris required)")
    p_diag.add_argument(
        "tool",
        choices=["equinox-trads", "leap-months", "losar-scatter", "round-trip"],
        help="Which diagnostic to run",
    )

    # ephem diagnostics
    p_ephem = sub.add_parser("ephem", help="Ephemeris-based diagnostics")
    p_ephem.add_argument(
        "tool",
        choices=[
            "raw-offsets",
            "drift-quad",
            "drift-trads",
            "analysis-trads",
            "offsets-trads",
            "anomaly-trads",
            "validate-ref"
        ],
        help="Which ephemeris diagnostic to run",
    )

    # astronomy tools
    sub.add_parser("astro-args", help="Print astronomical fundamental arguments at a given JD(TT).")
    sub.add_parser("solar", help="Calculate true/apparent solar longitude, EOT, and sunrise.")
    sub.add_parser("lunar", help="Calculate true/apparent lunar longitude and true latitude.")

    # design tools
    sub.add_parser("rational-params", help="Generate continued fraction convergents for calendar design.")
    sub.add_parser("dyadic-params", help="Generate dyadic (power of 2) approximants for calendar design.")
    sub.add_parser("float-params", help="Generate full-precision hex-float parameters for calendar engine design.")
    sub.add_parser("sine-table", help="Generate integer tables for a quarter-period sine function.")
    sub.add_parser("minimax", help="Compute minimax odd-polynomial approximations for sin and arctan.")
    sub.add_parser("pade-arctan", help="Compute minimax Padé approximant for arctan.")

    args, rest = p.parse_known_args(argv)

    if args.cmd == "day":
        day_argv = [args.date]
        if args.engine != "phugpa":
            day_argv += ["--engine", args.engine]
        if args.debug:
            day_argv += ["--debug"]
        for a in args.attr:
            day_argv += ["--attr", a]
        day_argv += rest
        return cmd_day(day_argv)

    if args.cmd == "pretty-month":
        return _run_module_main("caltib.diagnostics.pretty_month", rest)

    if args.cmd == "new-years":
        return _run_module_main("caltib.diagnostics.new_years_table", rest)

    if args.cmd == "diag":
        tool_map = {
            "equinox-trads": "caltib.diagnostics.equinox_trads",
            "leap-months": "caltib.diagnostics.leap_months",
            "losar-scatter": "caltib.diagnostics.losar_scatter",
            "round-trip": "caltib.diagnostics.round_trip",
        }
        return _run_module_main(tool_map[args.tool], rest)

    if args.cmd == "ephem":
        tool_map = {
            "raw-offsets": "caltib.diagnostics.ephem.offsets_trads",
            "drift-quad": "caltib.diagnostics.ephem.drift_quad_fit",
            "drift-trads": "caltib.diagnostics.ephem.drift_trads",
            "analysis-trads": "caltib.diagnostics.ephem.analysis_trads",
            "offsets-trads": "caltib.diagnostics.ephem.offsets_trads",
            "anomaly-trads": "caltib.diagnostics.ephem.anomaly_trads",
            "validate-ref": "caltib.diagnostics.ephem.validate_reference",
        }
        modpath = tool_map[args.tool]
        return _run_module_main(modpath, rest)

    if args.cmd == "astro-args":
        return cmd_astro_args(rest)

    if args.cmd == "solar":
        return cmd_solar(rest)

    if args.cmd == "lunar":
        return cmd_lunar(rest)

    if args.cmd == "rational-params":
        return _run_module_main("caltib.design.rational_params", rest)

    if args.cmd == "dyadic-params":
        return _run_module_main("caltib.design.dyadic_params", rest)

    if args.cmd == "float-params":
        return _run_module_main("caltib.design.float_params", rest)

    if args.cmd == "sine-table":
        return _run_module_main("caltib.design.sine_tables", rest)

    if args.cmd == "minimax":
        return _run_module_main("caltib.design.minimax_polys", rest)

    if args.cmd == "pade-arctan":
        return _run_module_main("caltib.design.pade_arctan", rest)

    raise RuntimeError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())

