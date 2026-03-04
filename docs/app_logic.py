import js
from datetime import date, timedelta
import calendar
import caltib
from pyodide.ffi import create_proxy

# --- GLOBAL APPLICATION STATE ---
APP_STATE = {
    "date": date.today(),
    "engine_cache": {},
    "data_cache": {},  # NEW: Prevents UI freezing by caching heavy calculations
    "month_mode": "gregorian",
    "year_mode": "gregorian"
}

# --- INITIALIZATION ---
status_div = js.document.getElementById("sys-status")

def init_app():
    status_div.innerText = "System Ready."
    status_div.style.color = "#22c55e"
    
    # Set default Losar range (-5 to +10)
    curr_y = APP_STATE["date"].year
    js.document.getElementById("losar-start").value = str(curr_y - 5)
    js.document.getElementById("losar-end").value = str(curr_y + 10)
    
    # Handle engine changes seamlessly
    def on_engine_change(e):
        APP_STATE["data_cache"].clear()
        render_all_views()
        generate_losar_list()  # Keep the Losar tab perfectly synced!
        
    select_el = js.document.getElementById("engine-select")
    select_el.addEventListener("change", create_proxy(on_engine_change))
    
    render_all_views()
    generate_losar_list()  # Initial calculation

# --- CACHE WRAPPERS (The Performance Fix) ---
def get_engine():
    engine_id = js.document.getElementById("engine-select").value
    if engine_id not in APP_STATE["engine_cache"]:
        APP_STATE["engine_cache"][engine_id] = caltib.get_calendar(engine_id)
    return APP_STATE["engine_cache"][engine_id]

def get_cached_day(engine, d: date):
    key = f"D_{engine.id.name}_{d.isoformat()}"
    if key not in APP_STATE["data_cache"]:
        APP_STATE["data_cache"][key] = engine.day_info(d)
    return APP_STATE["data_cache"][key]

def get_cached_month(engine, y: int, m: int, is_leap: bool):
    key = f"M_{engine.id.name}_{y}_{m}_{is_leap}"
    if key not in APP_STATE["data_cache"]:
        APP_STATE["data_cache"][key] = engine.month_info(y, m, is_leap=is_leap)
    return APP_STATE["data_cache"][key]

def get_cached_year(engine, y: int):
    key = f"Y_{engine.id.name}_{y}"
    if key not in APP_STATE["data_cache"]:
        APP_STATE["data_cache"][key] = engine.year_info(y)
    return APP_STATE["data_cache"][key]

# --- UI TOGGLE ROUTING ---
def toggle_month_mode(mode):
    APP_STATE["month_mode"] = mode
    js.document.getElementById("tog-m-greg").classList.toggle("active", mode == "gregorian")
    js.document.getElementById("tog-m-tib").classList.toggle("active", mode == "tibetan")
    render_month_view(APP_STATE["date"], get_engine())

def toggle_year_mode(mode):
    APP_STATE["year_mode"] = mode
    js.document.getElementById("tog-y-greg").classList.toggle("active", mode == "gregorian")
    js.document.getElementById("tog-y-tib").classList.toggle("active", mode == "tibetan")
    render_year_view(APP_STATE["date"], get_engine())

# --- ROUTERS & NAVIGATION ---
def set_date(new_date):
    APP_STATE["date"] = new_date
    render_all_views()

def nav_day_prev(e): set_date(APP_STATE["date"] - timedelta(days=1))
def nav_day_next(e): set_date(APP_STATE["date"] + timedelta(days=1))

def nav_month_prev(e): 
    d = APP_STATE["date"].replace(day=1) - timedelta(days=1)
    set_date(d.replace(day=1))
def nav_month_next(e):
    d = APP_STATE["date"].replace(day=28) + timedelta(days=5)
    set_date(d.replace(day=1))

def nav_year_prev(e): set_date(APP_STATE["date"].replace(year=APP_STATE["date"].year - 1))
def nav_year_next(e): set_date(APP_STATE["date"].replace(year=APP_STATE["date"].year + 1))

def sync_year_spinner(e):
    try:
        input_y = int(js.document.getElementById("year-spinner").value)
        mode = APP_STATE.get("year_mode", "gregorian")
        
        if mode == "gregorian":
            set_date(APP_STATE["date"].replace(year=input_y))
        else:
            engine = get_engine()
            new_date = caltib.new_year_day(input_y, engine=engine.id)
            set_date(new_date)
    except ValueError:
        pass

def go_to_month_view(e): js.document.getElementById("btn-tab-month").click()
def go_to_year_view(e): js.document.getElementById("btn-tab-year").click()

def jump_to_specific_date(y, m, d):
    set_date(date(y, m, d))
    js.document.getElementById("btn-tab-day").click()

def jump_to_month_view(y, m):
    set_date(date(y, m, 1))
    js.document.getElementById("btn-tab-month").click()

def jump_to_month_grid(y, m, d):
    set_date(date(y, m, d))
    js.document.getElementById("btn-tab-month").click()

# Expose globals to JS scope
import pyodide
js.window.toggle_month_mode = pyodide.ffi.create_proxy(toggle_month_mode)
js.window.toggle_year_mode = pyodide.ffi.create_proxy(toggle_year_mode)
js.window.jump_to_month_grid = pyodide.ffi.create_proxy(jump_to_month_grid)
js.window.jump_to_month_view = pyodide.ffi.create_proxy(jump_to_month_view)
js.window.jump_to_specific_date = pyodide.ffi.create_proxy(jump_to_specific_date)

# --- VIEW RENDERERS ---
def render_day_view(cur_date, engine):
    info = get_cached_day(engine, cur_date)  # Cached!
    tib = info.tibetan
    
    # Using the new, clean API attributes!
    js.document.getElementById("day-title").innerText = cur_date.strftime("%A, %B %d, %Y")
    js.document.getElementById("day-val-year").innerText = f"Alignment: {getattr(tib, 'year', '--')}"
    js.document.getElementById("day-val-month").innerText = f"{getattr(tib, 'month', '--')}{' (Leap)' if getattr(tib, 'is_leap_month', False) else ''}"
    js.document.getElementById("day-val-tithi").innerText = str(getattr(tib, 'tithi', '--'))
    
    meta_str = ""
    if getattr(tib, 'occ', 1) == 2: meta_str = "DUPLICATED DAY"
    if getattr(tib, 'previous_tithi_skipped', False): meta_str = "PRECEDING DAY SKIPPED"
    js.document.getElementById("day-val-tithi-meta").innerText = meta_str

def render_month_view(cur_date, engine):
    mode = APP_STATE.get("month_mode", "gregorian")
    container = js.document.getElementById("month-grid-container")
    
    if mode == "gregorian":
        y, m = cur_date.year, cur_date.month
        js.document.getElementById("month-title").innerText = cur_date.strftime("%B %Y")
        
        html = '<div class="month-grid">'
        for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            html += f'<div class="month-header">{d}</div>'
            
        cal_matrix = calendar.monthcalendar(y, m)
        for week in cal_matrix:
            for d in week:
                if d == 0:
                    html += '<div class="month-cell empty"></div>'
                else:
                    cell_date = date(y, m, d)
                    cell_info = get_cached_day(engine, cell_date) # Cached!
                    cell_tib = cell_info.tibetan
                    
                    cell_meta = ""
                    if getattr(cell_tib, 'occ', 1) == 2: cell_meta += "+ "
                    if getattr(cell_tib, 'previous_tithi_skipped', False): cell_meta += "⚠ "
                    
                    bg = "#eff6ff" if d == cur_date.day else ""
                    border = "var(--primary-color)" if d == cur_date.day else "var(--border-color)"
                    
                    html += f'''
                    <div class="month-cell" style="background:{bg}; border-color:{border}" onclick="window.jump_to_specific_date({y}, {m}, {d})">
                        <div class="greg-date">{d}</div>
                        <div class="tib-tithi" style="font-size: 1rem;">{getattr(cell_tib, 'tithi', '--')}</div>
                        <div style="font-size: 0.75rem; color: #ef4444; text-align: right; margin-top: auto;">{cell_meta}</div>
                    </div>'''
        html += '</div>'
        container.innerHTML = html

    else:
        anchor_info = get_cached_day(engine, cur_date)
        t_year = getattr(anchor_info.tibetan, 'year')
        t_month = getattr(anchor_info.tibetan, 'month')
        is_leap = getattr(anchor_info.tibetan, 'is_leap_month', False)
        
        m_info = get_cached_month(engine, t_year, t_month, is_leap) # Cached!
        
        leap_str = " (Leap)" if is_leap else ""
        js.document.getElementById("month-title").innerText = f"Tibetan Month {t_month}{leap_str}, Year {t_year}"
        
        html = '<div class="month-grid" style="grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));">'
        for day in m_info.days:
            tib = day.tibetan
            c_date = day.civil_date
            greg_label = c_date.strftime("%b %d")
            
            bg = "#eff6ff" if c_date == cur_date else ""
            border = "var(--primary-color)" if c_date == cur_date else "var(--border-color)"
            
            meta = []
            if getattr(tib, 'occ', 1) == 2: meta.append("+")
            if getattr(tib, 'previous_tithi_skipped', False): meta.append("⚠")
            meta_str = "<br>".join(meta)
            
            html += f'''
            <div class="month-cell" style="background:{bg}; border-color:{border}" onclick="window.jump_to_specific_date({c_date.year}, {c_date.month}, {c_date.day})">
                <div class="tib-tithi" style="text-align: left; font-size: 1.6rem; color: var(--text-main);">{getattr(tib, 'tithi', '--')}</div>
                <div class="greg-date" style="text-align: right; font-size: 0.8rem; font-weight: normal; color: var(--text-muted);">{greg_label}</div>
                <div style="font-size: 0.7rem; color: #ef4444; margin-top: auto; font-weight: bold;">{meta_str}</div>
            </div>'''
        html += '</div>'
        container.innerHTML = html

def render_year_view(cur_date, engine):
    mode = APP_STATE.get("year_mode", "gregorian")
    container = js.document.getElementById("year-grid-container")
    
    if mode == "gregorian":
        y = cur_date.year
        js.document.getElementById("year-spinner").value = str(y)
        
        y_html = ""
        for mi in range(1, 13):
            y_html += f'<div class="mini-month" onclick="window.jump_to_month_grid({y}, {mi}, 1)">'
            y_html += f'<div class="mini-month-title">{calendar.month_name[mi]}</div>'
            y_html += '<div class="mini-month-body" style="grid-template-columns: repeat(7, 1fr);">'
            mini_matrix = calendar.monthcalendar(y, mi)
            for week in mini_matrix:
                for d in week:
                    if d == 0:
                        y_html += '<div></div>'
                    else:
                        if d == cur_date.day and mi == cur_date.month:
                            y_html += f'<div style="background: var(--primary-color); color: white; border-radius: 50%; font-weight: bold;">{d}</div>'
                        else:
                            y_html += f'<div>{d}</div>'
            y_html += '</div></div>'
            
        container.innerHTML = y_html

    else:
        anchor_info = get_cached_day(engine, cur_date)
        t_year = getattr(anchor_info.tibetan, 'year')
        js.document.getElementById("year-spinner").value = str(t_year)
        
        y_info = get_cached_year(engine, t_year) # Cached!
        
        y_html = ""
        for m_info in y_info.months:
            m_tib = m_info.tibetan
            t_month = getattr(m_tib, 'month')
            is_leap = getattr(m_tib, 'is_leap_month', False)
            leap_str = " (Leap)" if is_leap else ""
            
            if m_info.gregorian_start:
                gy, gm, gd = m_info.gregorian_start.year, m_info.gregorian_start.month, m_info.gregorian_start.day
                click_action = f'onclick="window.jump_to_month_grid({gy}, {gm}, {gd})"'
            else:
                click_action = ""
                
            y_html += f'<div class="mini-month" {click_action}>'
            y_html += f'<div class="mini-month-title">Month {t_month}{leap_str}</div>'
            y_html += '<div class="mini-month-body" style="grid-template-columns: repeat(6, 1fr);">'
            
            for d_info in m_info.days:
                d_tib = d_info.tibetan
                if d_info.civil_date == cur_date:
                    y_html += f'<div style="background: var(--primary-color); color: white; border-radius: 4px; font-weight: bold;">{getattr(d_tib, "tithi", "--")}</div>'
                else:
                    if getattr(d_tib, 'occ', 1) == 2:
                        y_html += f'<div style="color: var(--primary-color); font-weight: bold;">{getattr(d_tib, "tithi", "--")}+</div>'
                    elif getattr(d_tib, 'previous_tithi_skipped', False):
                        y_html += f'<div style="color: var(--primary-color); font-weight: bold;">{getattr(d_tib, "tithi", "--")}-</div>'
                    else:
                        y_html += f'<div>{getattr(d_tib, "tithi", "--")}</div>'
                        
            y_html += '</div></div>'
            
        container.innerHTML = y_html

def render_all_views():
    cur_date = APP_STATE["date"]
    engine = get_engine()
    render_day_view(cur_date, engine)
    render_month_view(cur_date, engine)
    render_year_view(cur_date, engine)

# --- SPECIAL TOOLS ---
# --- SPECIAL TOOLS ---
def adjust_losar_range(d_start, d_end):
    """Fired by the inline +/- buttons to grow/shrink the table."""
    el_start = js.document.getElementById("losar-start")
    el_end = js.document.getElementById("losar-end")
    el_start.value = str(int(el_start.value) + d_start)
    el_end.value = str(int(el_end.value) + d_end)
    generate_losar_list()

js.window.adjust_losar_range = pyodide.ffi.create_proxy(adjust_losar_range)

def generate_losar_list(event=None):
    try:
        start_y = int(js.document.getElementById("losar-start").value)
        end_y = int(js.document.getElementById("losar-end").value)
        engine_id = js.document.getElementById("engine-select").value
        
        output = js.document.getElementById("losar-output")
        output.innerHTML = "<em>Calculating...</em>"
        
        # Added a strict width to the +/- column to keep the UI from jumping
        html = '<table class="data-table"><tr><th>Alignment Year</th><th>Engine</th><th>Gregorian Date</th><th style="text-align:center; width: 80px;">Range</th></tr>'
        
        for y in range(start_y, end_y + 1):
            losar_date = caltib.new_year_day(y, engine=engine_id)
            gy, gm, gd = losar_date.year, losar_date.month, losar_date.day
            
            # Make the date clickable to jump to the Day Card
            date_link = f"<span class='clickable-link' style='color: var(--primary-color); font-weight: bold;' onclick='window.jump_to_specific_date({gy}, {gm}, {gd})'>{losar_date.strftime('%A, %B %d, %Y')}</span>"
            
            # Build inline +/- buttons
            controls = ""
            btn_style = 'style="cursor: pointer; padding: 2px 6px; margin: 0 2px;"'
            if y == start_y:
                controls += f'<button {btn_style} onclick="window.adjust_losar_range(-1, 0)" title="Extend back">+</button>'
                if start_y < end_y:
                    controls += f'<button {btn_style} onclick="window.adjust_losar_range(1, 0)" title="Shrink top">-</button>'
            elif y == end_y:
                if y != start_y:
                    controls += f'<button {btn_style} onclick="window.adjust_losar_range(0, -1)" title="Shrink bottom">-</button>'
                controls += f'<button {btn_style} onclick="window.adjust_losar_range(0, 1)" title="Extend forward">+</button>'
                
            html += f"<tr><td>{y}</td><td>{engine_id}</td><td>{date_link}</td><td style='text-align:center;'>{controls}</td></tr>"
            
        html += "</table>"
        output.innerHTML = html
        
    except Exception as e:
        js.document.getElementById("losar-output").innerText = f"Error: {str(e)}"

js.window.generate_losar_list = pyodide.ffi.create_proxy(generate_losar_list)


# Start the app
init_app()