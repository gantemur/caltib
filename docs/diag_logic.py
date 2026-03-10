import json
import datetime
from fractions import Fraction
import numpy as np

from caltib.api import get_calendar
from caltib.reference.solar import solar_longitude
from caltib.reference.lunar import lunar_position

# =====================================================================
# UTILITIES
# =====================================================================

def detrended_anomaly(times, angles_deg):
    coeffs = np.polyfit(times, angles_deg, 1)
    mean_line = np.polyval(coeffs, times)
    anom = angles_deg - mean_line
    anom -= float(np.mean(anom))
    return anom

def jd_to_date_str(jd):
    dt = datetime.datetime(2000, 1, 1, 12, 0, 0) + datetime.timedelta(days=(jd - 2451545.0))
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_abbr(eng_name):
    """Maps full engine names to compact abbreviations."""
    abbrs = {"phugpa": "PH", "mongol": "MN", "tsurphu": "TS", "bhutan": "BH", "karana": "KA"}
    return abbrs.get(eng_name.lower(), eng_name.upper())

# =====================================================================
# TOOL 1: ANGULAR ANOMALY
# =====================================================================

def get_anomaly_reference_trace(jd_start, jd_end, step_days=1.0):
    ts = np.arange(jd_start, jd_end + 1e-12, step_days, dtype=float)
    angles = []
    
    for jd in ts:
        s = solar_longitude(jd).L_true_deg
        m = lunar_position(jd).L_true_deg
        elong = (m - s) % 360.0
        angles.append(elong)
        
    ang = np.array(angles, dtype=float)
    ang_unw = np.degrees(np.unwrap(np.radians(ang)))
    anom = detrended_anomaly(ts, ang_unw)
    
    return {
        "x": [jd_to_date_str(jd) for jd in ts],
        "y": list(anom),
        "type": "scatter",
        "mode": "lines",
        "name": "REF",  # Compact Reference Name
        "line": {"color": "black", "dash": "dash", "width": 2}
    }

def get_anomaly_engine_trace(engine_name, jd_start, jd_end):
    eng = get_calendar(engine_name)
    t2000_start = jd_start - 2451545.0
    t2000_end = jd_end - 2451545.0
    
    x_lo = eng.day.get_x_from_t2000(t2000_start) - 2
    x_hi = eng.day.get_x_from_t2000(t2000_end) + 2

    times = []
    angles = []
    
    for x in range(x_lo, x_hi + 1):
        t_val = float(eng.day.true_date(x))
        jd_val = t_val + 2451545.0
        
        if jd_start <= jd_val <= jd_end:
            times.append(jd_val)
            angles.append(float(x) * 12.0)

    if not times:
        return None

    t_arr = np.array(times, dtype=float)
    a_arr = np.array(angles, dtype=float)
    
    idx = np.argsort(t_arr)
    t_arr = t_arr[idx]
    a_arr = a_arr[idx]

    anom = detrended_anomaly(t_arr, a_arr)
    
    return {
        "x": [jd_to_date_str(jd) for jd in t_arr],
        "y": list(anom),
        "type": "scatter",
        "mode": "lines",
        "name": get_abbr(engine_name),  # Uses compact abbreviation
        "line": {"width": 1.5}
    }

# =====================================================================
# MAIN ROUTER
# =====================================================================

def handle_request(tool, engine_str, start_str, end_str, lat, lon):
    dt_start = datetime.datetime.strptime(start_str, "%Y-%m-%d")
    dt_end = datetime.datetime.strptime(end_str, "%Y-%m-%d")
    jd_start = dt_start.toordinal() + 1721424.5
    jd_end = dt_end.toordinal() + 1721424.5

    engines = [e.strip() for e in engine_str.split(",") if e.strip()]
    traces = []

    if tool == "anomaly":
        traces.append(get_anomaly_reference_trace(jd_start, jd_end, step_days=1.0))
        for eng_name in engines:
            try:
                trace = get_anomaly_engine_trace(eng_name, jd_start, jd_end)
                if trace:
                    traces.append(trace)
            except Exception as e:
                print(f"Skipping {eng_name}: {e}")

    # We now ONLY return the traces. JS handles the layout.
    return json.dumps({"traces": traces})