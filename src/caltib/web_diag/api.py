import json
import datetime
import math
import bisect
from fractions import Fraction

import caltib
from caltib.api import get_calendar
from caltib.core.types import LocationSpec, SunriseState
from caltib.reference.solar import solar_longitude, sunrise_sunset_utc
from caltib.reference.lunar import lunar_position
from caltib.reference.astro_args import fundamental_args, T_centuries
from caltib.reference.time_scales import jd_utc_to_jd_tt, jd_tt_to_jd_utc
from caltib.reference.deltat import delta_t_seconds

# =====================================================================
# PURE PYTHON MATH UTILITIES
# =====================================================================

def linspace(start, stop, num):
    if num <= 1: return [start]
    step = (stop - start) / (num - 1)
    return [start + i * step for i in range(num)]

def interp(x, xp, yp):
    if x <= xp[0]: return yp[0]
    if x >= xp[-1]: return yp[-1]
    idx = bisect.bisect_right(xp, x)
    x0, x1 = xp[idx-1], xp[idx]
    y0, y1 = yp[idx-1], yp[idx]
    if x1 == x0: return y0
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)

def unwrap_turns(turns):
    if not turns: return []
    out = [turns[0]]
    for i in range(1, len(turns)):
        diff = turns[i] - turns[i-1]
        diff = (diff + 0.5) % 1.0 - 0.5
        out.append(out[-1] + diff)
    return out

def circular_mean_mod24(hours_mod24):
    if not hours_mod24: return 0.0
    theta = [2.0 * math.pi * (x / 24.0) for x in hours_mod24]
    c = sum(math.cos(t) for t in theta) / len(theta)
    s = sum(math.sin(t) for t in theta) / len(theta)
    ang = math.atan2(s, c) % (2.0 * math.pi)
    return 24.0 * ang / (2.0 * math.pi)

def find_exact_syzygy(x, jd_guess):
    target_deg = (x % 30) * 12.0
    def error(jd):
        e = (lunar_position(jd).L_true_deg - solar_longitude(jd).L_true_deg) % 360.0
        d = (e - target_deg) % 360.0
        if d > 180.0: d -= 360.0
        return d
    
    jd0, jd1 = jd_guess, jd_guess + 0.1
    e0, e1 = error(jd0), error(jd1)
    
    for _ in range(15):
        if abs(e1) < 1e-6 or e1 == e0: break
        jd_next = jd1 - e1 * (jd1 - jd0) / (e1 - e0)
        jd0, e0 = jd1, e1
        jd1 = jd_next
        e1 = error(jd1)
    return jd1

def get_stats(arr):
    if not arr: return 0, 0, 0
    n = len(arr)
    mean = sum(arr) / n
    s_arr = sorted(arr)
    median = (s_arr[n//2] + s_arr[(n-1)//2]) / 2.0
    std = math.sqrt(sum((x - mean)**2 for x in arr) / n)
    return mean, median, std

def solve_linear_system(A, B):
    n = len(B)
    for i in range(n):
        max_el, max_row = abs(A[i][i]), i
        for k in range(i+1, n):
            if abs(A[k][i]) > max_el:
                max_el, max_row = abs(A[k][i]), k
        A[i], A[max_row] = A[max_row], A[i]
        B[i], B[max_row] = B[max_row], B[i]
        if A[i][i] == 0: return [0]*n
        for k in range(i+1, n):
            c = -A[k][i] / A[i][i]
            for j in range(i, n):
                A[k][j] = 0 if i == j else A[k][j] + c * A[i][j]
            B[k] += c * B[i]
    x = [0]*n
    for i in range(n-1, -1, -1):
        x[i] = B[i] / A[i][i]
        for k in range(i-1, -1, -1): B[k] -= A[k][i] * x[i]
    return x

def polyfit2(x, y):
    """Fits c2*x^2 + c1*x + c0 robustly by centering data first to avoid precision collapse."""
    mean_x = sum(x) / len(x)
    xs = [xi - mean_x for xi in x]
    S4, S3, S2 = sum(xi**4 for xi in xs), sum(xi**3 for xi in xs), sum(xi**2 for xi in xs)
    S1, S0 = sum(xs), len(xs)
    B2, B1, B0 = sum(xi**2 * yi for xi, yi in zip(xs, y)), sum(xi * yi for xi, yi in zip(xs, y)), sum(y)
    
    coeffs = solve_linear_system([[S4, S3, S2], [S3, S2, S1], [S2, S1, S0]], [B2, B1, B0])
    if not coeffs or len(coeffs) != 3: return 0, 0, 0
    c2, c1, c0 = coeffs
    
    return c2, c1 - 2 * c2 * mean_x, c0 - c1 * mean_x + c2 * mean_x**2

def rolling_stats(x, y, window_pts):
    n = len(y)
    means, stds = [None]*n, [None]*n
    if window_pts < 3 or window_pts > n: return means, stds
    half = window_pts // 2
    for i in range(half, n - half):
        seg = y[i-half : i+half+1]
        m = sum(seg) / len(seg)
        means[i] = m
        stds[i] = math.sqrt(sum((v-m)**2 for v in seg)/len(seg))
    return means, stds

# =====================================================================
# GENERAL UTILITIES
# =====================================================================

def jd_to_date_str(jd):
    dt = datetime.datetime(2000, 1, 1, 12, 0, 0) + datetime.timedelta(days=(jd - 2451545.0))
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_abbr(eng_name):
    abbrs = {"phugpa": "PH", "mongol": "MN", "tsurphu": "TS", "bhutan": "BH", "karana": "KA"}
    name = eng_name.lower()
    if name.endswith("-m"):
        base = name[:-2]
        return abbrs.get(base, base.upper()) + "-M"
    return abbrs.get(name, name.upper())

# =====================================================================
# TOOL 1-6 (EXISTING TOOLS)
# =====================================================================

def get_anomaly_reference_trace(jd_start, jd_end, step_days=1.0):
    num_steps = max(2, int((jd_end - jd_start) / step_days))
    ts = linspace(jd_start, jd_end, num_steps)
    anomalies = []
    for jd in ts:
        s = solar_longitude(jd).L_true_deg
        m = lunar_position(jd).L_true_deg
        true_elong = (m - s) % 360.0
        mean_elong = fundamental_args(T_centuries(jd)).D_deg
        diff = (true_elong - mean_elong) % 360.0
        if diff > 180.0: diff -= 360.0
        anomalies.append(diff)
    return {"x": [jd_to_date_str(jd) for jd in ts], "y": anomalies, "type": "scatter", "mode": "lines", "name": "REF", "line": {"color": "black", "dash": "dash", "width": 2}}

def get_anomaly_engine_trace(engine_name, jd_start, jd_end):
    use_month = engine_name.endswith("-m")
    base_engine = engine_name[:-2] if use_month else engine_name
    eng = get_calendar(base_engine)
    t2000_start, t2000_end = jd_start - 2451545.0, jd_end - 2451545.0
    x_lo, x_hi = eng.day.get_x_from_t2000(t2000_start) - 2, eng.day.get_x_from_t2000(t2000_end) + 2

    mean_rate = 360.0 / 29.530588853
    data_points = []
    for x in range(x_lo, x_hi + 1):
        if use_month:
            if not hasattr(eng, "month"): continue
            t_true = float(eng.month.true_date(Fraction(x, 30)))
            t_mean = float(eng.month.mean_date(Fraction(x, 30)))
        else:
            # CLEANED
            t_true = float(eng.day.true_date(x))
            t_mean = float(eng.day.mean_date(x)) 
            
        jd_val = t_true + 2451545.0
        if jd_start <= jd_val <= jd_end: data_points.append((jd_val, - (t_true - t_mean) * mean_rate))

    if not data_points: return None
    data_points.sort(key=lambda item: item[0])
    return {"x": [jd_to_date_str(d[0]) for d in data_points], "y": [d[1] for d in data_points], "type": "scatter", "mode": "lines", "name": get_abbr(engine_name), "line": {"width": 1.5}}

def get_continuous_anomaly_payload(engines, jd_start, jd_end, mode="forward"):
    span_days = jd_end - jd_start
    num_steps = min(800, max(2, int(span_days)))
    ts = linspace(jd_start, jd_end, num_steps)
    traces = []
    ref_y = []
    for jd in ts:
        if mode == "forward":
            s = solar_longitude(jd).L_true_deg
            m = lunar_position(jd).L_true_deg
            true_val = (m - s) % 360.0
            mean_val = fundamental_args(T_centuries(jd)).D_deg
        else:
            true_val = solar_longitude(jd).L_true_deg
            T = (jd - 2451545.0) / 36525.0
            mean_val = (280.46646 + 36000.76983 * T + 0.0003032 * T**2) % 360.0
        diff = (true_val - mean_val) % 360.0
        if diff > 180.0: diff -= 360.0
        ref_y.append(diff)
        
    traces.append({"x": [jd_to_date_str(jd) for jd in ts], "y": ref_y, "type": "scatter", "mode": "lines", "name": "REF", "line": {"color": "black", "dash": "dash", "width": 2}})
    
    for eng_name in engines:
        use_month = eng_name.lower().endswith("-m")
        base_eng = eng_name[:-2] if use_month else eng_name
        try: eng = get_calendar(base_eng)
        except: continue
        
        y_vals, valid_ts = [], []
        for jd in ts:
            t2000_frac = Fraction(float(jd)) - Fraction(2451545)
            try:
                if mode == "forward":
                    if use_month:
                        if not hasattr(eng, "month"): continue
                        true_e = float(eng.month.true_elong_tt(t2000_frac))
                        mean_e = float(eng.month.mean_elong_tt(t2000_frac))
                    else:
                        if not hasattr(eng, "day"): continue
                        # CLEANED
                        true_e = float(eng.day.true_elong_tt(t2000_frac))
                        mean_e = float(eng.day.mean_elong_tt(t2000_frac))
                else:
                    if use_month:
                        if not hasattr(eng, "month"): continue
                        true_e = float(eng.month.true_sun_tt(t2000_frac))
                        mean_e = float(eng.month.mean_sun_tt(t2000_frac))
                    else:
                        if not hasattr(eng, "day"): continue
                        true_e = float(eng.day.true_sun_tt(t2000_frac))
                        mean_e = float(eng.day.mean_sun_tt(t2000_frac))
                        
                diff_turns = (true_e - mean_e) % 1.0
                if diff_turns > 0.5: diff_turns -= 1.0
                y_vals.append(diff_turns * 360.0)
                valid_ts.append(jd)
            except Exception: pass
                
        if y_vals:
            traces.append({"x": [jd_to_date_str(jd) for jd in valid_ts], "y": y_vals, "type": "scatter", "mode": "lines", "name": get_abbr(eng_name), "line": {"dash": "dot" if use_month else "solid", "width": 2.0 if use_month else 1.5}})
    return {"traces": traces, "layout_extras": {}}

def get_solar_lon_payload(engines, jd_start, jd_end):
    span_days = jd_end - jd_start
    num_steps = min(800, max(2, int(span_days))) 
    ts = linspace(jd_start, jd_end, num_steps)
    ref_deg = [solar_longitude(jd).L_true_deg for jd in ts]
    traces = [{"x": [jd_to_date_str(jd) for jd in ts], "y": [0] * len(ts), "type": "scatter", "mode": "lines", "name": "REF (0 Error)", "line": {"color": "black", "dash": "dash", "width": 2}}]
    
    for eng_name in engines:
        use_month = eng_name.lower().endswith("-m")
        base_eng = eng_name[:-2] if use_month else eng_name
        try: eng = get_calendar(base_eng)
        except Exception: continue
            
        errors, valid_ts = [], []
        for i, jd in enumerate(ts):
            t2000_frac = Fraction(float(jd)) - Fraction(2451545)
            try:
                if use_month:
                    if not hasattr(eng, "month"): continue
                    eng_turns = float(eng.month.true_sun_tt(t2000_frac))
                else:
                    if not hasattr(eng, "day"): continue
                    eng_turns = float(eng.day.true_sun_tt(t2000_frac))
            except Exception: continue
                
            err_deg = (eng_turns * 360.0 - ref_deg[i]) % 360.0
            if err_deg > 180.0: err_deg -= 360.0
            valid_ts.append(jd)
            errors.append(err_deg)
            
        if errors:
            traces.append({"x": [jd_to_date_str(jd) for jd in valid_ts], "y": errors, "type": "scatter", "mode": "lines", "name": get_abbr(eng_name), "line": {"dash": "dot" if use_month else "solid", "width": 2.0 if use_month else 1.5}})
    return {"traces": traces, "layout_extras": {}}

def get_assign_month_payload(engine_name, jd_start, jd_end):
    base_engine = engine_name[:-2] if engine_name.endswith("-m") else engine_name
    eng = get_calendar(base_engine)
    epoch_t2000 = float(eng.month.mean_date(Fraction(0)))
    t2000_start, t2000_end = jd_start - 2451545.0, jd_end - 2451545.0
    n_lo = int(math.floor((t2000_start - epoch_t2000) / 29.530588)) - 1
    n_hi = int(math.ceil((t2000_end - epoch_t2000) / 29.530588)) + 1
    total_months = n_hi - n_lo
    is_macro_view, is_ultra_macro = total_months > 36, total_months > 600
    moons_jd, labels = [], []
    for n in range(n_lo, n_hi + 1):
        try:
            moons_jd.append(float(eng.month.true_date(n)) + 2451545.0)
            labels.append(eng.month.get_month_info(n))
        except: pass
    if len(moons_jd) < 2: return {"traces": [], "layout_extras": {}}
    t_grid = linspace(moons_jd[0] - 2451545.0, moons_jd[-1] - 2451545.0, max(500, total_months * 10))
    sun_turns = [float(eng.month.true_sun_tt(Fraction(float(t)))) for t in t_grid]
    sun_deg_unwrapped = [t * 360.0 for t in unwrap_turns(sun_turns)]
    sgang_base_deg = float(eng.sgang_base) * 360.0
    k_min = math.floor((min(sun_deg_unwrapped) - sgang_base_deg) / 30.0)
    k_max = math.ceil((max(sun_deg_unwrapped) - sgang_base_deg) / 30.0)
    ks = range(k_min, k_max + 1)
    shapes, annotations, y_tickvals, y_ticktext = [], [], [], []
    for k in ks:
        if is_ultra_macro and k % 120 != 0: continue
        elif is_macro_view and not is_ultra_macro and k % 12 != 0: continue
        deg = sgang_base_deg + k * 30.0
        is_major = (k % 12 == 0)
        if not is_macro_view:
            y_tickvals.append(deg)
            y_ticktext.append(f"{int(deg % 360)}° (Sg {int(k % 12) + 1})")
        shapes.append({"type": "line", "xref": "paper", "x0": 0, "x1": 1, "y0": deg, "y1": deg, "line": {"color": "#888888", "width": 1.0 if is_major else 0.5}, "opacity": 0.5 if is_major else 0.2, "layer": "below"})
    for i in range(len(moons_jd) - 1):
        m1, m2 = moons_jd[i], moons_jd[i+1]
        yr = labels[i]['year']
        is_year_start = (labels[i]['month'] == 1) and (labels[i]['leap_state'] != 2)
        line_w, line_dash, line_alpha = 0.5, "dot", 0.4
        if is_year_start:
            if not is_ultra_macro: line_w, line_dash, line_alpha = 0.8, "solid", 0.5
            elif yr % 10 == 0: line_w, line_dash, line_alpha = 1.0, "solid", 0.3
        if not is_macro_view or is_year_start:
            shapes.append({"type": "line", "x0": jd_to_date_str(m1), "x1": jd_to_date_str(m1), "yref": "paper", "y0": 0, "y1": 1, "line": {"color": "#1f77b4", "width": line_w, "dash": line_dash}, "opacity": line_alpha, "layer": "below"})
        if not is_macro_view:
            annotations.append({"x": jd_to_date_str(m1 + (m2 - m1) / 2), "y": 1.02, "yref": "paper", "text": f"M{labels[i]['month']}", "showarrow": False, "font": {"size": 11, "color": "#333", "weight": "bold"}})
        y1 = interp(m1 - 2451545.0, t_grid, sun_deg_unwrapped)
        y2 = interp(m2 - 2451545.0, t_grid, sun_deg_unwrapped)
        crossings = math.floor((y2 - sgang_base_deg) / 30.0) - math.floor((y1 - sgang_base_deg) / 30.0)
        alpha_leap = 1.0 if is_ultra_macro else (0.6 if is_macro_view else 0.25)
        if crossings == 0: shapes.append({"type": "rect", "x0": jd_to_date_str(m1), "x1": jd_to_date_str(m2), "yref": "paper", "y0": 0, "y1": 1, "fillcolor": "#ffd700", "opacity": alpha_leap, "line": {"width": 0}, "layer": "below"})
        elif crossings >= 2: shapes.append({"type": "rect", "x0": jd_to_date_str(m1), "x1": jd_to_date_str(m2), "yref": "paper", "y0": 0, "y1": 1, "fillcolor": "#ff9999", "opacity": alpha_leap, "line": {"width": 0}, "layer": "below"})
    layout_extras = {"shapes": shapes, "annotations": annotations}
    if y_tickvals: layout_extras["yaxis"] = {"tickvals": y_tickvals, "ticktext": y_ticktext}
    return {"traces": [{"x": [jd_to_date_str(t + 2451545.0) for t in t_grid], "y": sun_deg_unwrapped, "type": "scatter", "mode": "lines", "name": "True Solar Longitude", "line": {"color": "#ff7f0e", "width": 2 if not is_ultra_macro else 0.5}}], "layout_extras": layout_extras}

def get_assign_day_payload(engine_name, jd_start, jd_end):
    base_engine = engine_name[:-2] if engine_name.endswith("-m") else engine_name
    eng = get_calendar(base_engine)
    J_start, J_end = int(math.floor(jd_start - 0.5)), int(math.floor(jd_end - 0.5))
    epoch_t2000 = float(eng.day.mean_date(Fraction(0)))
    mean_tithi = 29.530588853 / 30.0
    x_lo = int((J_start - 2451545.0 - epoch_t2000) / mean_tithi) - 10
    x_hi = int((J_end - 2451545.0 - epoch_t2000) / mean_tithi) + 10
    
    jdn_to_x = {J: [] for J in range(J_start, J_end + 1)}
    for x in range(x_lo - 15, x_hi + 16):
        try:
            J = eng.day.civil_jdn(x)
            if J_start <= J <= J_end: jdn_to_x[J].append(x)
        except: pass
            
    active_xs = [x for xs in jdn_to_x.values() for x in xs]
    if not active_xs: return {"traces": [], "layout_extras": {}}
    plot_x_min, plot_x_max = min(active_xs) - 1, max(active_xs) + 1
    
    def get_inherited_name(jdn: int) -> int:
        if jdn in jdn_to_x and jdn_to_x[jdn]: return sorted(jdn_to_x[jdn])[0]
        curr = jdn + 1
        while curr <= max(jdn_to_x.keys()) + 15:
            for x in range(x_lo - 15, x_hi + 16):
                if getattr(eng.day, 'civil_jdn', lambda x: -1)(x) == curr: return x
            curr += 1
        return plot_x_min
        
    x_grid = linspace(plot_x_min - 1, plot_x_max + 1, max(500, (plot_x_max - plot_x_min + 1) * 20))
    t_jd, y_val = [], []
    for x_fl in x_grid:
        try:
            # CLEANED
            t_tt = float(eng.day.true_date(Fraction(float(x_fl))))
            t_jd.append(t_tt + 2451545.0)
            y_val.append(float(x_fl))
        except: pass
            
    shapes, annotations, y_tickvals, y_ticktext = [], [], [], []
    num_days = J_end - J_start + 1
    label_step_x, label_step_y = 1, 1
    if num_days > 120: label_step_x, label_step_y = 10, 10
    elif num_days > 60: label_step_x, label_step_y = 5, 5
    elif num_days > 35: label_step_x, label_step_y = 3, 2
    elif num_days > 15: label_step_x, label_step_y = 2, 2
    
    for i, x in enumerate(range(plot_x_min, plot_x_max + 1)):
        y_tickvals.append(x)
        y_ticktext.append(f"LD {((x - 1) % 30) + 1}" if i % label_step_y == 0 else "")
        shapes.append({"type": "line", "xref": "paper", "x0": 0, "x1": 1, "y0": x, "y1": x, "line": {"color": "#888888", "width": 0.5}, "opacity": 0.3, "layer": "below"})
        
    x_tickvals, x_ticktext = [], []
    for J in range(J_start, J_end + 1):
        d_str1, d_str2 = jd_to_date_str(J), jd_to_date_str(J + 1)
        shapes.append({"type": "line", "x0": d_str1, "x1": d_str1, "yref": "paper", "y0": 0, "y1": 1, "line": {"color": "#1f77b4", "width": 0.8, "dash": "dash"}, "opacity": 0.6, "layer": "below"})
        assigned_x = jdn_to_x.get(J, [])
        if len(assigned_x) == 0: shapes.append({"type": "rect", "x0": d_str1, "x1": d_str2, "yref": "paper", "y0": 0, "y1": 1, "fillcolor": "#ffd700", "opacity": 0.15, "line": {"width": 0}, "layer": "below"})
        elif len(assigned_x) == 2: shapes.append({"type": "rect", "x0": d_str1, "x1": d_str2, "yref": "paper", "y0": 0, "y1": 1, "fillcolor": "#ff9999", "opacity": 0.20, "line": {"width": 0}, "layer": "below"})
                           
        i, mid_jd = J - J_start, J + 0.5
        if (i % label_step_x == 0) or (len(assigned_x) != 1 and num_days < 100):
            inherited_x = get_inherited_name(J)
            d_name = ((inherited_x - 1) % 30) + 1
            annotations.append({"x": jd_to_date_str(mid_jd), "y": 1.02, "yref": "paper", "text": f"D{d_name}", "showarrow": False, "font": {"size": 10, "color": "#333"}})
        if i % label_step_x == 0:
            x_tickvals.append(jd_to_date_str(mid_jd))
            dt = datetime.datetime(2000, 1, 1, 12, 0, 0) + datetime.timedelta(days=(J - 2451545.0))
            
            # Mimic Plotly's smart formatting: Show year on first tick or when year changes
            if len(x_tickvals) == 1 or (dt.month == 1 and dt.day <= label_step_x):
                x_ticktext.append(dt.strftime("%m/%d\n%Y"))
            else:
                x_ticktext.append(dt.strftime("%m/%d"))
            
    shapes.append({"type": "line", "x0": jd_to_date_str(J_end + 1), "x1": jd_to_date_str(J_end + 1), "yref": "paper", "y0": 0, "y1": 1, "line": {"color": "#1f77b4", "width": 0.8, "dash": "dash"}, "opacity": 0.6, "layer": "below"})
    return {"traces": [{"x": [jd_to_date_str(t) for t in t_jd], "y": y_val, "type": "scatter", "mode": "lines", "name": "True Elongation", "line": {"color": "#ff7f0e", "width": 1.5}}], "layout_extras": {"shapes": shapes, "annotations": annotations, "yaxis": {"tickvals": y_tickvals, "ticktext": y_ticktext, "title": "Lunar Phase (Tithi)"}, "xaxis": {"tickvals": x_tickvals, "ticktext": x_ticktext, "tickformat": ""}}}

def get_losar_scatter_payload(engines, start_year, end_year, metric):
    traces = []
    styles = {
        "PH": {"color": "#1f77b4", "symbol": "circle", "size": 8, "line_width": 0}, "MN": {"color": "#737373", "symbol": "circle-open", "size": 10, "line_width": 1.5},
        "TS": {"color": "#d62728", "symbol": "line-ew", "size": 12, "line_width": 1.5}, "BH": {"color": "#d62728", "symbol": "line-ns", "size": 12, "line_width": 1.5},
        "L1": {"color": "#2ca02c", "symbol": "square-open", "size": 8, "line_width": 1.5}, "L2": {"color": "#ff7f0e", "symbol": "triangle-up", "size": 9, "line_width": 0},
        "L3": {"color": "#9467bd", "symbol": "diamond", "size": 8, "line_width": 0}, "L4": {"color": "#e377c2", "symbol": "star", "size": 9, "line_width": 0}
    }
    for eng in engines:
        base_engine = eng[:-2] if eng.endswith("-m") else eng
        x_vals, y_vals = [], []
        abbr = get_abbr(base_engine)
        st = styles.get(abbr, {"color": "#8c564b", "symbol": "cross", "size": 8, "line_width": 1})
        for y in range(start_year, end_year + 1):
            try:
                ny = caltib.new_year_day(y, engine=base_engine)
                d = ny if isinstance(ny, datetime.date) else ny["date"]
                val = (d - datetime.date(d.year, 1, 1)).days + 1 if metric == "doy" else (d - datetime.date(d.year - 1, 12, 22)).days + 1
                x_vals.append(y); y_vals.append(val)
            except Exception: pass
        if x_vals:
            traces.append({"x": x_vals, "y": y_vals, "type": "scatter", "mode": "markers", "name": abbr, "marker": {"color": st["color"], "symbol": st["symbol"], "size": st["size"], "line": {"color": st["color"], "width": st["line_width"]} if st["line_width"] > 0 else {"width": 0}}})
    return {"traces": traces, "layout_extras": {"yaxis": {"title": "Day of Year" if metric == "doy" else "Days since Winter Solstice (Dec 22)"}}}

def get_offsets_payload(engine_name, year_start, year_end, time_mode, eval_mode):
    use_month = engine_name.endswith("-m")
    base_engine = engine_name[:-2] if use_month else engine_name
    eng = get_calendar(base_engine)
    jd_start = datetime.date(year_start, 1, 1).toordinal() + 1721425.5
    jd_end = datetime.date(year_end, 12, 31).toordinal() + 1721425.5
    
    x_start, x_end = eng.day.get_x_from_t2000(jd_start - 2451545.0), eng.day.get_x_from_t2000(jd_end - 2451545.0)
    diffs_raw = []
    for x in range(x_start, x_end + 1):
        d = x % 30
        if d == 0: d = 30
        if eval_mode == "newmoon" and d != 30: continue
        if eval_mode == "tithi" and x % 5 != 0: continue 
        
        if use_month:
            if not hasattr(eng, "month"): continue
            t_engine_tt = float(eng.month.true_date(Fraction(x, 30))) + 2451545.0
        elif time_mode == "civil": t_engine_tt = float(eng.day.local_civil_date(x)) + 2451545.0
        else:
            # CLEANED
            t_engine_tt = float(eng.day.true_date(x)) + 2451545.0
            
        t_truth_tt = find_exact_syzygy(x, t_engine_tt)
        diffs_raw.append(24.0 * (t_engine_tt - t_truth_tt))

    if not diffs_raw: return {"traces": [], "layout_extras": {}}
    arr_mod24 = [d % 24.0 for d in diffs_raw]
    mean_mod24 = circular_mean_mod24(arr_mod24)
    _, _, std_raw = get_stats(diffs_raw)
    _, _, std_mod24 = get_stats(arr_mod24)
    arr_final = [mean_mod24 + ((val - mean_mod24 + 12.0) % 24.0) - 12.0 for val in diffs_raw] if std_raw > 6.0 and std_mod24 < 6.0 else diffs_raw
    mean_h, med_h, std_h = get_stats(arr_final)
    color_map = {"l4": "gold", "l3": "olive", "l2": "cyan", "l1": "pink", "l0": "brown", "phugpa": "#1f77b4"}
    
    return {
        "traces": [{"x": arr_final, "type": "histogram", "name": get_abbr(engine_name), "marker": {"color": color_map.get(base_engine, "#1f77b4"), "line": {"color": "black", "width": 1}}, "opacity": 0.8}],
        "layout_extras": {
            "shapes": [{"type": "line", "x0": mean_h, "x1": mean_h, "yref": "paper", "y0": 0, "y1": 1, "line": {"color": "red", "dash": "dash", "width": 2}}],
            "annotations": [{"x": 0.95, "y": 0.95, "xref": "paper", "yref": "paper", "text": f"<b>Mean:</b> {mean_h:.2f}h<br><b>Median:</b> {med_h:.2f}h<br><b>Std Dev:</b> {std_h:.2f}h", "showarrow": False, "align": "left", "bgcolor": "white", "bordercolor": "black", "borderpad": 5}],
            "xaxis": {"title": f"Offset (Hours)"}, "yaxis": {"title": "Count"}
        }
    }


# =====================================================================
# TOOL 7: LONG-TERM DRIFT (QUADRATIC)
# =====================================================================
def get_drift_payload(engine_name, year_start, year_end, time_mode, apply_delta_t):
    use_month = engine_name.endswith("-m")
    base_engine = engine_name[:-2] if use_month else engine_name
    eng = get_calendar(base_engine)
    
    jd_start = datetime.date(year_start if year_start > 0 else 1, 1, 1).toordinal() + 1721425.5
    if year_start <= 0: jd_start += (year_start - 1) * 365.25
    jd_end = datetime.date(year_end, 12, 31).toordinal() + 1721425.5
    
    x_start = eng.day.get_x_from_t2000(jd_start - 2451545.0)
    x_end = eng.day.get_x_from_t2000(jd_end - 2451545.0)
    
    span_lunations = (x_end - x_start) // 30
    base_step = max(1, span_lunations // 1500)
    
    start_n = x_start // 30
    end_n = x_end // 30
    
    years_f, off_f = [], []
    current_n = start_n
    step_idx = 0
    
    while current_n <= end_n:
        n = current_n
        x = n * 30
        
        if base_step == 1:
            current_n += 1
        else:
            jitter = (step_idx * 137) % 5
            current_n += base_step + jitter
        step_idx += 1
        
        if x < x_start or x > x_end: continue
        
        try:
            if hasattr(eng.month, "label_from_lunation"):
                Y, M, _ = eng.month.label_from_lunation(n)
            else:
                info = eng.month.get_month_info(n)
                Y, M = info["year"], info["month"]
        except Exception: 
            continue
            
        x_year = Y + (M - 0.5) / 12.0
        
        try:
            if use_month:
                if not hasattr(eng, "month"): continue
                t_engine_tt = float(eng.month.true_date(Fraction(x, 30))) + 2451545.0
            elif time_mode == "civil":
                t_engine_utc = float(eng.day.local_civil_date(x)) + 2451545.0
                t_engine_tt = t_engine_utc + delta_t_seconds(x_year) / 86400.0
            else:
                t_engine_tt = float(eng.day.true_date(x)) + 2451545.0
        except Exception:
            continue
                
        t_truth_tt = find_exact_syzygy(x, t_engine_tt)
        
        if time_mode == "civil" and not use_month:
            t_truth_utc = t_truth_tt - delta_t_seconds(x_year) / 86400.0
            off_h = 24.0 * (t_engine_utc - t_truth_utc)
        else:
            off_h = 24.0 * (t_engine_tt - t_truth_tt)        
            
        if apply_delta_t:
            off_h += delta_t_seconds(x_year) / 3600.0
            
        if abs(off_h) < 50.0:
            years_f.append(x_year)
            off_f.append(off_h)

    if len(years_f) < 10: return {"traces": [], "layout_extras": {}}
    
    c2, c1, c0 = polyfit2(years_f, off_f)
    
    reg_x = linspace(min(years_f), max(years_f), 500)
    reg_y = [c2 * (xv**2) + c1 * xv + c0 for xv in reg_x]
    
    step = (max(years_f) - min(years_f)) / len(years_f)
    window_pts = max(3, int(round(100.0 / step)) | 1)
    roll_mean, roll_std = rolling_stats(years_f, off_f, window_pts)
    
    # NEW: Quadratic Variance Fit
    std_x, std_v = [], []
    for xv, sv in zip(years_f, roll_std):
        if sv is not None:
            std_x.append(xv)
            std_v.append(sv**2) # Fit to Variance (Sigma squared)

    if len(std_x) > 10:
        v2, v1, v0 = polyfit2(std_x, std_v)
        # Convert fitted variance back to standard deviation (sigma)
        smooth_sigma = [math.sqrt(max(0, v2 * (xv**2) + v1 * xv + v0)) for xv in reg_x]
    else:
        smooth_sigma = [0] * len(reg_x)

    # Apply smooth sigma to the central quadratic drift
    band_upper = [ry + sig for ry, sig in zip(reg_y, smooth_sigma)]
    band_lower = [ry - sig for ry, sig in zip(reg_y, smooth_sigma)]

    color_map = {
        "phugpa": "#ff7f0e",   # orange
        "mongol": "#1f77b4",   # blue
        "tsurphu": "#9467bd",  # purple
        "bhutan": "#2ca02c",   # green
        "karana": "#d62728",   # red
        "l0": "#8c564b",       # brown
        "l1": "#e377c2",       # pink
        "l2": "#17becf",       # cyan
        "l3": "#bcbd22",       # olive
        "l4": "#f1c40f"        # gold
    }
    c = color_map.get(base_engine, "#1f77b4")

    traces = [
        {"x": reg_x, "y": band_upper, "type": "scatter", "mode": "lines", "line": {"width": 0}, "hoverinfo": "skip", "showlegend": False},
        {"x": reg_x, "y": band_lower, "type": "scatter", "mode": "lines", "fill": "tonexty", "fillcolor": f"rgba(100, 150, 200, 0.2)", "line": {"width": 0}, "name": "±1σ Spread (Fit)"},
        {"x": reg_x, "y": reg_y, "type": "scatter", "mode": "lines", "name": "Mean Drift Fit", "line": {"color": "black", "width": 2.5}},
        {"x": years_f, "y": off_f, "type": "scatter", "mode": "markers", "name": get_abbr(engine_name), "marker": {"color": c, "size": 4, "opacity": 0.4}}
    ]

    shapes = []
    if abs(c2) > 1e-20:
        drift_vertex_x = -c1 / (2.0 * c2)
        if min(years_f) <= drift_vertex_x <= max(years_f):
            shapes.append({"type": "line", "x0": drift_vertex_x, "x1": drift_vertex_x, "yref": "paper", "y0": 0, "y1": 1, "line": {"color": "black", "dash": "dash", "width": 1.5}})

    return {
        "traces": traces,
        "layout_extras": {
            "shapes": shapes,
            "xaxis": {"title": "Lunar Year Coordinate"},
            "yaxis": {"title": "Offset (hours)"}
        }
    }

# =====================================================================
# TOOL 8: MULTI-ENGINE DRIFT & SIGMA COMPARISON
# =====================================================================
def get_multi_drift_payload(engines, year_start, year_end, time_mode, apply_delta_t):
    jd_start = datetime.date(year_start if year_start > 0 else 1, 1, 1).toordinal() + 1721425.5
    if year_start <= 0: jd_start += (year_start - 1) * 365.25
    jd_end = datetime.date(year_end, 12, 31).toordinal() + 1721425.5

    traces = []
    color_map = {
        "phugpa": "#ff7f0e",   # orange
        "mongol": "#1f77b4",   # blue
        "tsurphu": "#9467bd",  # purple
        "bhutan": "#2ca02c",   # green
        "karana": "#d62728",   # red
        "l0": "#8c564b",       # brown
        "l1": "#e377c2",       # pink
        "l2": "#17becf",       # cyan
        "l3": "#bcbd22",       # olive
        "l4": "#f1c40f"        # gold
    }
    
    for eng_name in engines:
        use_month = eng_name.endswith("-m")
        base_engine = eng_name[:-2] if use_month else eng_name
        try: eng = get_calendar(base_engine)
        except: continue
        
        x_start = eng.day.get_x_from_t2000(jd_start - 2451545.0)
        x_end = eng.day.get_x_from_t2000(jd_end - 2451545.0)
        
        span_lunations = (x_end - x_start) // 30
        base_step = max(1, span_lunations // 1000) 
        
        start_n = x_start // 30
        end_n = x_end // 30
        
        years_f, off_f = [], []
        current_n = start_n
        step_idx = 0
        
        while current_n <= end_n:
            n = current_n
            x = n * 30
            if base_step == 1: current_n += 1
            else: current_n += base_step + ((step_idx * 137) % 5)
            step_idx += 1
            
            if x < x_start or x > x_end: continue
            
            try:
                if hasattr(eng.month, "label_from_lunation"):
                    Y, M, _ = eng.month.label_from_lunation(n)
                else:
                    info = eng.month.get_month_info(n)
                    Y, M = info["year"], info["month"]
            except Exception: continue
                
            x_year = Y + (M - 0.5) / 12.0
            
            try:
                if use_month:
                    if not hasattr(eng, "month"): continue
                    t_engine_tt = float(eng.month.true_date(Fraction(x, 30))) + 2451545.0
                elif time_mode == "civil":
                    t_engine_utc = float(eng.day.local_civil_date(x)) + 2451545.0
                    t_engine_tt = t_engine_utc + delta_t_seconds(x_year) / 86400.0
                else:
                    t_engine_tt = float(eng.day.true_date(x)) + 2451545.0
            except Exception: continue
                    
            t_truth_tt = find_exact_syzygy(x, t_engine_tt)
            
            if time_mode == "civil" and not use_month:
                t_truth_utc = t_truth_tt - delta_t_seconds(x_year) / 86400.0
                off_h = 24.0 * (t_engine_utc - t_truth_utc)
            else:
                off_h = 24.0 * (t_engine_tt - t_truth_tt)        
                
            if apply_delta_t:
                off_h += delta_t_seconds(x_year) / 3600.0
                
            if abs(off_h) < 50.0:
                years_f.append(x_year)
                off_f.append(off_h)

        if len(years_f) < 10: continue
        
        c2, c1, c0 = polyfit2(years_f, off_f)
        reg_x = linspace(min(years_f), max(years_f), 200)
        reg_y = [c2 * (xv**2) + c1 * xv + c0 for xv in reg_x]
        
        step = (max(years_f) - min(years_f)) / len(years_f)
        window_pts = max(3, int(round(100.0 / step)) | 1)
        _, roll_std = rolling_stats(years_f, off_f, window_pts)
        
        # NEW: Quadratic Variance Fit
        std_x, std_v = [], []
        for xv, sv in zip(years_f, roll_std):
            if sv is not None:
                std_x.append(xv)
                std_v.append(sv**2)
                
        if len(std_x) > 10:
            v2, v1, v0 = polyfit2(std_x, std_v)
            sigma_y = [math.sqrt(max(0, v2 * (xv**2) + v1 * xv + v0)) for xv in reg_x]
        else:
            sigma_y = [0] * len(reg_x)
                
        c = color_map.get(base_engine, "#1f77b4")
        abbr = get_abbr(eng_name)
        
        traces.append({
            "x": reg_x, "y": reg_y, "type": "scatter", "mode": "lines",
            "name": f"{abbr} (Drift)", "line": {"color": c, "width": 2.5},
            "yaxis": "y"
        })
        
        # Plot Smooth Sigma Fit instead of jagged raw stats
        traces.append({
            "x": reg_x, "y": sigma_y, "type": "scatter", "mode": "lines",
            "name": f"{abbr} (Sigma)", "line": {"color": c, "width": 2.5, "dash": "dot"},
            "yaxis": "y2"
        })

    return {
        "traces": traces,
        "layout_extras": {
            "yaxis": {"title": "Mean Offset Drift (hours)", "automargin": True},
            "yaxis2": {
                "title": "Spread / Sigma (hours)",
                "overlaying": "y",
                "side": "right",
                "showgrid": False,
                "zeroline": False,
                "automargin": True
            },
            "xaxis": {"title": "Lunar Year Coordinate"}
        }
    }

# =====================================================================
# TOOL 9: PLANETARY LONGITUDE (SIDEREAL, TROPICAL, DETRENDED)
# =====================================================================
def get_ayanamsha(jd: float, zero_year: float) -> float:
    years_since_zero = 2000.0 - zero_year
    base_j2000 = years_since_zero * 0.0139697 
    days_since_j2000 = jd - 2451545.0
    years_since_j2000 = days_since_j2000 / 365.25
    precession_drift = years_since_j2000 * 0.0139697
    return base_j2000 + precession_drift

def get_planets_payload(engines, year_start, year_end, planet, mode, zero_year):
    from caltib.engines.factory import make_engine
    from caltib.engines.specs import ALL_SPECS
    from caltib.reference import planets as ref_planets

    jd_start = datetime.date(year_start if year_start > 0 else 1, 1, 1).toordinal() + 1721425.5
    if year_start <= 0: jd_start += (year_start - 1) * 365.25
    jd_end = datetime.date(year_end, 12, 31).toordinal() + 1721425.5

    span_days = jd_end - jd_start
    step_days = max(1, int(span_days / 2000))
    num_steps = min(800, max(2, int(span_days / step_days)))
    
    jds = linspace(jd_start, jd_end, num_steps)
    years = [2000.0 + (jd - 2451545.0) / 365.25 for jd in jds]

    traces = []
    mod_trop_deg = []
    mod_sid_deg = []
    sun_trop_deg = []

    # Precompute Reference Modern Kinematics
    for jd in jds:
        trop = ref_planets.geocentric_position(planet, jd).L_true_deg
        mod_trop_deg.append(trop)
        if mode == "sidereal":
            mod_sid_deg.append((trop - get_ayanamsha(jd, zero_year)) % 360.0)
        if mode == "detrended":
            sun_trop_deg.append(ref_planets.geocentric_position("sun", jd).L_true_deg)

    traces.append({
        "x": years, "y": [0]*len(years), "type": "scatter", "mode": "lines",
        "name": "REF (Modern)", "line": {"color": "black", "dash": "dash", "width": 2}
    })

    color_map = {"phugpa": "#ff7f0e", "mongol": "#1f77b4", "tsurphu": "#9467bd", "bhutan": "#2ca02c", "karana": "#d62728", "l0": "#8c564b", "l1": "#e377c2", "l2": "#17becf", "l3": "#bcbd22", "l4": "#f1c40f"}

    for eng_name in engines:
        base_eng = eng_name[:-2] if eng_name.endswith("-m") else eng_name
        if base_eng not in ALL_SPECS: continue
        
        try:
            engine = make_engine(ALL_SPECS[base_eng])
        except Exception:
            continue
            
        y_vals, valid_x = [], []
        for i, jd in enumerate(jds):
            try:
                trad_data = engine.get_planet_longitudes(jd)
                if trad_data is None or planet not in trad_data:
                    continue
                
                trad_deg = float(trad_data[planet]["true"]) * 360.0
                
                if mode == "tropical":
                    err = (trad_deg - mod_trop_deg[i] + 180.0) % 360.0 - 180.0
                elif mode == "sidereal":
                    err = (trad_deg - mod_sid_deg[i] + 180.0) % 360.0 - 180.0
                elif mode == "detrended":
                    trad_sun_deg = float(trad_data["sun"]["true"]) * 360.0
                    d_trop = (trad_deg - mod_trop_deg[i] + 180.0) % 360.0 - 180.0
                    sun_trop_err = (trad_sun_deg - sun_trop_deg[i] + 180.0) % 360.0 - 180.0
                    err = (d_trop - sun_trop_err + 180.0) % 360.0 - 180.0
                    
                y_vals.append(err)
                valid_x.append(years[i])
            except Exception:
                pass
        
        if y_vals:
            traces.append({
                "x": valid_x, "y": y_vals, "type": "scatter", "mode": "markers",
                "name": get_abbr(eng_name), "marker": {"color": color_map.get(base_eng, "#1f77b4"), "size": 4, "opacity": 0.6}
            })

    return {
        "traces": traces,
        "layout_extras": {
            "xaxis": {"title": "Gregorian Year"},
            "yaxis": {"title": "Error (Degrees)", "automargin": True}
        }
    }


# =====================================================================
# TOOL 10: SUNRISE ERROR (POLAR SHADED)
# =====================================================================
def get_sunrise_payload(engines, jd_start, jd_end, lat, lon):
    span_days = int(jd_end - jd_start)
    if span_days <= 0: return {"traces": [], "layout_extras": {}}
    
    num_steps = min(800, max(2, span_days))
    ts = linspace(jd_start, jd_end, num_steps)
    dates_str = [jd_to_date_str(jd).split(" ")[0] for jd in ts] # YYYY-MM-DD
    
    loc = LocationSpec(name="Custom", lat_turn=Fraction(lat)/360, lon_turn=Fraction(lon)/360)
    
    ref_utc_list = []
    polar_states = []
    
    for jd in ts:
        ref_sunrise = sunrise_sunset_utc(jd, lat_deg=lat, lon_deg_east=lon)
        polar_states.append(ref_sunrise.state)
        ref_utc_list.append(ref_sunrise.rise_utc_hours if ref_sunrise.state == SunriseState.NORMAL else math.nan)

    traces = []
    color_map = {"phugpa": "#ff7f0e", "mongol": "#1f77b4", "tsurphu": "#9467bd", "bhutan": "#2ca02c", "karana": "#d62728", "l0": "#8c564b", "l1": "#e377c2", "l2": "#17becf", "l3": "#bcbd22", "l4": "#f1c40f"}
    
    for eng_name in engines:
        base_eng = eng_name[:-2] if eng_name.endswith("-m") else eng_name
        try: eng = get_calendar(base_eng, location=loc)
        except: continue
        
        y_vals, valid_dates = [], []
        for i, jd in enumerate(ts):
            if polar_states[i] != SunriseState.NORMAL:
                continue
                
            t2000_tt = jd_utc_to_jd_tt(jd) - 2451545.0
            try:
                lmt_frac, state = eng.eval_sunrise_lmt(t2000_tt)
                if state != SunriseState.NORMAL: continue
                    
                engine_utc_frac = (float(lmt_frac) - (lon / 360.0)) % 1.0
                engine_utc_hours = engine_utc_frac * 24.0
                
                diff_hours = engine_utc_hours - ref_utc_list[i]
                diff_hours = (diff_hours + 12.0) % 24.0 - 12.0
                
                y_vals.append(diff_hours * 60.0)
                valid_dates.append(dates_str[i])
            except: pass
        
        if y_vals:
            c = color_map.get(base_eng, "#1f77b4")
            traces.append({
                "x": valid_dates, "y": y_vals, "type": "scatter", "mode": "lines",
                "name": get_abbr(eng_name), "line": {"color": c, "width": 1.5}
            })
    
    # Generate Polar Shading Shapes
    shapes = [{"type": "rect", "xref": "paper", "x0": 0, "x1": 1, "y0": -16, "y1": 16, "fillcolor": "gray", "opacity": 0.1, "line": {"width": 0}, "layer": "below"}]
    
    current_state = SunriseState.NORMAL
    start_idx = 0
    for i, state in enumerate(polar_states):
        if state != current_state:
            if current_state != SunriseState.NORMAL and i > start_idx:
                color = "#fef08a" if current_state == SunriseState.POLAR_DAY else "#1e3a8a"
                opacity = 0.4 if current_state == SunriseState.POLAR_DAY else 0.2
                shapes.append({"type": "rect", "x0": dates_str[start_idx], "x1": dates_str[i-1], "yref": "paper", "y0": 0, "y1": 1, "fillcolor": color, "opacity": opacity, "line": {"width": 0}, "layer": "below"})
            current_state = state
            start_idx = i
            
    if current_state != SunriseState.NORMAL and len(polar_states) > start_idx:
        color = "#fef08a" if current_state == SunriseState.POLAR_DAY else "#1e3a8a"
        opacity = 0.4 if current_state == SunriseState.POLAR_DAY else 0.2
        shapes.append({"type": "rect", "x0": dates_str[start_idx], "x1": dates_str[-1], "yref": "paper", "y0": 0, "y1": 1, "fillcolor": color, "opacity": opacity, "line": {"width": 0}, "layer": "below"})

    return {"traces": traces, "layout_extras": {"shapes": shapes}}


# =====================================================================
# MAIN ROUTER
# =====================================================================
def handle_request(tool, engine_str, start_str, end_str, lat, lon, opt1="since-solstice", opt2="newmoon", opt3="sun"):
    engines = [e.strip() for e in engine_str.split(",") if e.strip()]

    if tool == "planets":
        return json.dumps(get_planets_payload(engines, int(start_str), int(end_str), opt1, opt2, float(opt3)))

    if tool == "losar_scatter": return json.dumps(get_losar_scatter_payload(engines, int(start_str), int(end_str), opt1))
    if tool == "offsets": return json.dumps(get_offsets_payload(engines[0] if engines else "phugpa", int(start_str), int(end_str), opt1, opt2))
    
    if tool == "drift": 
        apply_dt = (str(opt2).lower() == "true")
        return json.dumps(get_drift_payload(engines[0] if engines else "phugpa", int(start_str), int(end_str), opt1, apply_dt))

    if tool == "multi_drift": 
        apply_dt = (str(opt2).lower() == "true")
        return json.dumps(get_multi_drift_payload(engines, int(start_str), int(end_str), opt1, apply_dt))

    try: dt_start = datetime.datetime.strptime(start_str, "%Y-%m-%d")
    except ValueError: dt_start = datetime.datetime.strptime(start_str, "%Y-%m")

    try: dt_end = datetime.datetime.strptime(end_str, "%Y-%m-%d")
    except ValueError: dt_end = datetime.datetime.strptime(end_str, "%Y-%m").replace(day=28) + datetime.timedelta(days=5)
        
    jd_start, jd_end = dt_start.toordinal() + 1721424.5, dt_end.toordinal() + 1721424.5

    if tool == "sunrise":
        return json.dumps(get_sunrise_payload(engines, jd_start, jd_end, lat, lon))

    if tool == "anomaly":
        traces = [get_anomaly_reference_trace(jd_start, jd_end, 1.0)]
        for eng in engines:
            tr = get_anomaly_engine_trace(eng, jd_start, jd_end)
            if tr: traces.append(tr)
        return json.dumps({"traces": traces, "layout_extras": {}})

    elif tool == "anomaly_forward": return json.dumps(get_continuous_anomaly_payload(engines, jd_start, jd_end, "forward"))
    elif tool == "anomaly_sun": return json.dumps(get_continuous_anomaly_payload(engines, jd_start, jd_end, "sun"))
    elif tool == "solar_lon": return json.dumps(get_solar_lon_payload(engines, jd_start, jd_end))
    elif tool == "assign_month": return json.dumps(get_assign_month_payload(engines[0] if engines else "l4", jd_start, jd_end))
    elif tool == "assign_day": return json.dumps(get_assign_day_payload(engines[0] if engines else "phugpa", jd_start, jd_end))

    return json.dumps({"traces": [], "layout_extras": {}})