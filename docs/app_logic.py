import js
from datetime import date, timedelta
import calendar
import caltib
from pyodide.ffi import create_proxy
import caltib.i18n as i18n
import json



from caltib.core.types import LocationSpec

from caltib.engines import specs

# Map the HTML dropdown values directly to your backend specs
PRESET_LOCATIONS = {
    "lhasa": specs.LOC_LHASA,
    "ulaanbaatar": specs.LOC_ULAANBAATAR,
    "thimphu": specs.LOC_THIMPHU,
    "hohhot": specs.LOC_HOHHOT,
    "beijing": specs.LOC_BEIJING,
    "ulan_ude": specs.LOC_ULAN_UDE,
    "elista": specs.LOC_ELISTA,
    "montreal": specs.LOC_MONTREAL
}

# --- GLOBAL APPLICATION STATE ---
APP_STATE = {
    "date": date.today(),
    "engine_cache": {},
    "data_cache": {},  # NEW: Prevents UI freezing by caching heavy calculations
    "month_mode": "gregorian",
    "year_mode": "gregorian"
}

APP_STATE["lang"] = "en"

# --- LOCAL STORAGE AUTO-SAVE ---
def save_state():
    """Saves the current dropdown selections to the browser's persistent storage."""
    state = {
        "engine": js.document.getElementById("engine-select").value,
        "location": js.document.getElementById("loc-select").value,
        "language": js.document.getElementById("lang-select").value
    }
    js.window.localStorage.setItem("caltib_config", json.dumps(state))

def load_state():
    """Attempts to load saved settings on startup."""
    saved = js.window.localStorage.getItem("caltib_config")
    if saved:
        try:
            state = json.loads(saved)
            if "engine" in state: js.document.getElementById("engine-select").value = state["engine"]
            if "location" in state: js.document.getElementById("loc-select").value = state["location"]
            if "language" in state: 
                js.document.getElementById("lang-select").value = state["language"]
                APP_STATE["lang"] = state["language"]
        except Exception:
            pass

# --- FILE EXPORT / IMPORT ---
def export_config(e):
    """Downloads the current state as a JSON file."""
    state = {
        "engine": js.document.getElementById("engine-select").value,
        "location": js.document.getElementById("loc-select").value,
        "language": js.document.getElementById("lang-select").value
    }
    json_str = json.dumps(state, indent=2)
    
    # Create a virtual file (Blob) and force the browser to download it
    blob = js.Blob.new([json_str], type="application/json")
    url = js.window.URL.createObjectURL(blob)
    
    a = js.document.createElement("a")
    a.href = url
    a.download = "caltib_config.json"
    js.document.body.appendChild(a)
    a.click()
    js.document.body.removeChild(a)
    js.window.URL.revokeObjectURL(url)

def import_config(e):
    """Reads an uploaded JSON file and applies it to the UI."""
    file_input = js.document.getElementById("config-upload")
    if not file_input.files.length:
        return
    
    file = file_input.files.item(0)
    
    def on_file_loaded(event):
        try:
            content = event.target.result
            state = json.loads(content)
            
            # Update DOM
            if "engine" in state: js.document.getElementById("engine-select").value = state["engine"]
            if "location" in state: js.document.getElementById("loc-select").value = state["location"]
            if "language" in state: js.document.getElementById("lang-select").value = state["language"]
            
            # Apply changes across the app
            APP_STATE["lang"] = js.document.getElementById("lang-select").value
            APP_STATE["data_cache"].clear()
            
            save_state()           # Update local storage with the new imported file
            sync_location_ui()     # Fix disabled dropdown states
            update_static_ui()     # Update translations
            render_all_views()     # Repaint calendar
            generate_losar_list()  # Repaint Losar table
            
        except Exception as ex:
            print(f"Failed to load config file: {ex}")
            
    # Read the file asynchronously
    reader = js.FileReader.new()
    reader.onload = create_proxy(on_file_loaded)
    reader.readAsText(file)
    file_input.value = "" # Reset input so the user can import the same file again later

js.window.export_config = create_proxy(export_config)

# --- TRANSLATION HELPERS ---
def _t(key):
    """Shorthand string translator"""
    return i18n.translate(key, APP_STATE["lang"])

def _n(num):
    """Shorthand numeral translator"""
    if num == "--": return num
    return i18n.localize_num(num, APP_STATE["lang"])

def _cap(text):
    """Universally capitalizes the first letter of a string, ignoring numbers/Tibetan."""
    if text and not text[0].isdigit():
        return text[0].upper() + text[1:]
    return text

def get_rabjung_string(tib_year):
    """Calculates the Rabjung cycle and year, returning a localized string."""
    if not isinstance(tib_year, int):
        return ""
    # The first Rabjung started in 1027 AD.
    offset = tib_year - 1026
    cycle = (offset - 1) // 60 + 1
    year_in_cycle = (offset - 1) % 60 + 1
    
    fmt_str = _t("rabjung_fmt")
    # Translate the numbers!
    return fmt_str.replace("{R}", _n(cycle)).replace("{Y}", _n(year_in_cycle))

# --- UI LABEL UPDATER ---
def update_static_ui():
    """Rewrites all static HTML text with the current language."""
    # Tabs
    js.document.getElementById("btn-tab-day").innerText = _t("tab_day")
    js.document.getElementById("btn-tab-month").innerText = _t("tab_month")
    js.document.getElementById("btn-tab-year").innerText = _t("tab_year")
    js.document.getElementById("btn-tab-losar").innerText = _t("tab_losar")
    
    # Day Card Static Labels
    js.document.querySelector("#day-val-year").previousElementSibling.innerText = _t("alignment")
    js.document.querySelector("#day-val-month").previousElementSibling.innerText = _t("lunar_month")
    js.document.querySelector("#day-val-tithi").previousElementSibling.innerText = _t("tithi")
    js.document.querySelector("#day-val-weekday").previousElementSibling.innerText = _t("weekday_lbl")
    js.document.getElementById("lbl-greg-date").innerText = _t("greg_date_lbl")
    js.document.getElementById("lbl-ext-attr").innerText = _t("attr_title")
    
    # Toggle Buttons
    js.document.getElementById("tog-m-greg").innerText = _t("greg_grid")
    js.document.getElementById("tog-m-tib").innerText = _t("tib_grid")
    js.document.getElementById("tog-y-greg").innerText = _t("greg_year")
    js.document.getElementById("tog-y-tib").innerText = _t("tib_year")

    # Dynamically rename the Losar Tab
    eng_val = js.document.getElementById("engine-select").value
    losar_tab_name = _t("tsagaan_sar") if eng_val == "mongol" else _t("losar")
    
    losar_tab_el = js.document.getElementById("btn-tab-losar")
    if losar_tab_el:
        losar_tab_el.innerText = losar_tab_name

# --- INITIALIZATION ---
status_div = js.document.getElementById("sys-status")

def init_app():
    status_div.innerText = "System Ready."
    status_div.style.color = "#22c55e"
    
    curr_y = APP_STATE["date"].year
    js.document.getElementById("losar-start").value = str(curr_y - 5)
    js.document.getElementById("losar-end").value = str(curr_y + 5)
    
    # 1. EVENT HANDLERS (Now with auto-save!)
    def handle_calc_change(e):
        APP_STATE["data_cache"].clear()
        sync_location_ui() 
        save_state()          # <-- Save on change
        update_static_ui()
        render_all_views()
        generate_losar_list()

    def handle_lang_change(e):
        APP_STATE["lang"] = js.document.getElementById("lang-select").value
        update_static_ui()
        save_state()          # <-- Save on change
        render_all_views()
        generate_losar_list()
        
    # 2. BINDINGS
    js.document.getElementById("engine-select").addEventListener("change", create_proxy(handle_calc_change))
    js.document.getElementById("loc-select").addEventListener("change", create_proxy(handle_calc_change))
    js.document.getElementById("lang-select").addEventListener("change", create_proxy(handle_lang_change))

    # --- SWIPE GESTURE DETECTION ---
    touch_start_x = 0
    touch_start_y = 0

    def on_touch_start(e):
        nonlocal touch_start_x, touch_start_y
        touch_start_x = e.touches.item(0).clientX
        touch_start_y = e.touches.item(0).clientY

    def on_touch_end(e):
        touch_end_x = e.changedTouches.item(0).clientX
        touch_end_y = e.changedTouches.item(0).clientY

        diff_x = touch_start_x - touch_end_x
        diff_y = touch_start_y - touch_end_y

        # If the horizontal swipe is longer than 50px AND mostly horizontal...
        if abs(diff_x) > 50 and abs(diff_x) > abs(diff_y):
            day_panel = js.document.getElementById("tab-day")
            month_panel = js.document.getElementById("tab-month")
            year_panel = js.document.getElementById("tab-year")
            
            if diff_x > 0:
                # Swiped Left -> Go Next
                if "active" in day_panel.className: nav_day_next(None)
                elif "active" in month_panel.className: nav_month_next(None)
                elif "active" in year_panel.className: nav_year_next(None)
            else:
                # Swiped Right -> Go Prev
                if "active" in day_panel.className: nav_day_prev(None)
                elif "active" in month_panel.className: nav_month_prev(None)
                elif "active" in year_panel.className: nav_year_prev(None)

    # Link to your existing view-panel class!
    main_area = js.document.querySelector(".view-panel")
    if main_area:
        main_area.addEventListener("touchstart", create_proxy(on_touch_start), {"passive": True})
        main_area.addEventListener("touchend", create_proxy(on_touch_end), {"passive": True})

    # 3. INITIAL BOOTSTRAP
    # Set hardcoded defaults first...
    js.document.getElementById("engine-select").value = "phugpa"
    js.document.getElementById("loc-select").value = "none"
    
    # ...then overwrite them if the user has previously saved settings!
    load_state()
    
    sync_location_ui()
    update_static_ui()
    render_all_views()
    generate_losar_list()


def sync_location_ui():
    """Manages the disabled state and auto-selection of the Location dropdown."""
    eng_select = js.document.getElementById("engine-select")
    loc_select = js.document.getElementById("loc-select")
    
    # Safely get the selected option and its parent <optgroup>
    selected_opt = eng_select.options.item(eng_select.selectedIndex)
    group = getattr(selected_opt, "parentElement", None)
    
    is_trad = False
    if group and getattr(group, "tagName", "").upper() == "OPTGROUP":
        if "traditional" in getattr(group, "label", "").lower():
            is_trad = True
            
    none_opt = loc_select.querySelector('option[value="none"]')
    
    if is_trad:
        # TRADITIONAL MODE
        loc_select.disabled = True
        if none_opt: none_opt.disabled = False
        loc_select.value = "none"
    else:
        # REFORMED MODE
        loc_select.disabled = False
        if none_opt: none_opt.disabled = True
        
        # Safe fallback if stuck on 'none'
        if loc_select.value == "none":
            loc_select.value = "lhasa"

# --- CACHE WRAPPERS (The Performance Fix) ---
def get_engine():
    """Purely fetches the engine based on current UI state. No DOM manipulation."""
    engine_id = js.document.getElementById("engine-select").value
    loc_id = js.document.getElementById("loc-select").value
    
    cache_key = f"{engine_id}_{loc_id}"
    
    if cache_key not in APP_STATE["engine_cache"]:
        if loc_id != "none" and loc_id in PRESET_LOCATIONS:
            # We now safely pass the location because ALL engines have with_location()
            loc_spec = PRESET_LOCATIONS[loc_id]
            APP_STATE["engine_cache"][cache_key] = caltib.get_calendar(engine_id, location=loc_spec)
        else:
            APP_STATE["engine_cache"][cache_key] = caltib.get_calendar(engine_id)
            
    return APP_STATE["engine_cache"][cache_key]

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
def go_today(e): set_date(date.today())

def nav_month_prev(e): 
    d = APP_STATE["date"].replace(day=1) - timedelta(days=1)
    set_date(d.replace(day=1))
def nav_month_next(e):
    d = APP_STATE["date"].replace(day=28) + timedelta(days=5)
    set_date(d.replace(day=1))

def nav_year_prev(e): set_date(APP_STATE["date"].replace(year=APP_STATE["date"].year - 1))
def nav_year_next(e): set_date(APP_STATE["date"].replace(year=APP_STATE["date"].year + 1))

def sync_year_spinner(e):
    """Fires instantly when the input arrows are clicked or enter is pressed"""
    try:
        input_y = int(js.document.getElementById("year-spinner").value)
        mode = APP_STATE.get("year_mode", "gregorian")
        
        if mode == "gregorian":
            set_date(APP_STATE["date"].replace(year=input_y))
        else:
            engine = get_engine()
            # Unpack the EngineId dataclass to pass just the string name
            new_date = caltib.new_year_day(input_y, engine=engine.id.name)
            set_date(new_date)            
    except ValueError:
        pass

def go_to_month_view(e): js.document.getElementById("btn-tab-month").click()
def go_to_year_view(e): js.document.getElementById("btn-tab-year").click()

def go_to_tib_month(e):
    """Forces the month grid to Tibetan mode and navigates."""
    APP_STATE["month_mode"] = "tibetan"
    js.document.getElementById("tog-m-greg").classList.remove("active")
    js.document.getElementById("tog-m-tib").classList.add("active")
    render_all_views()
    js.document.getElementById("btn-tab-month").click()

def go_to_tib_year(e):
    """Forces the year grid to Tibetan mode and navigates."""
    APP_STATE["year_mode"] = "tibetan"
    js.document.getElementById("tog-y-greg").classList.remove("active")
    js.document.getElementById("tog-y-tib").classList.add("active")
    render_all_views()
    js.document.getElementById("btn-tab-year").click()

# Register the proxies for the HTML clicks
js.window.go_to_tib_month = create_proxy(go_to_tib_month)
js.window.go_to_tib_year = create_proxy(go_to_tib_year)

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
js.window.go_today = pyodide.ffi.create_proxy(go_today)
js.window.toggle_month_mode = pyodide.ffi.create_proxy(toggle_month_mode)
js.window.toggle_year_mode = pyodide.ffi.create_proxy(toggle_year_mode)
js.window.jump_to_month_grid = pyodide.ffi.create_proxy(jump_to_month_grid)
js.window.jump_to_month_view = pyodide.ffi.create_proxy(jump_to_month_view)
js.window.jump_to_specific_date = pyodide.ffi.create_proxy(jump_to_specific_date)

# --- VIEW RENDERERS ---
def render_day_view(cur_date, engine):
    info = get_cached_day(engine, cur_date)
    tib = info.tibetan
    lang = APP_STATE.get("lang", "en")
    eng_name = engine.id.name
    
    # --- HELPER: Extracts localized attribute strings cleanly ---
    def _get_attrs(attrs):
        e_idx, a_idx = attrs.get("element", 0), attrs.get("animal", 0)
        m_idx, t_idx = attrs.get("mewa", 1), attrs.get("trigram", 0)

        e_base = _t("elements")[e_idx] if isinstance(_t("elements"), list) else ""
        a_base = _t("animals")[a_idx] if isinstance(_t("animals"), list) else ""
        m_col = _t("mewa_colors")[m_idx - 1] if isinstance(_t("mewa_colors"), list) else ""
        t_str = _t("trigrams")[t_idx] if isinstance(_t("trigrams"), list) else ""

        a_year = _t("animals_year")[a_idx] if isinstance(_t("animals_year"), list) else a_base
        a_month = _t("animals_month")[a_idx] if isinstance(_t("animals_month"), list) else a_base
        e_adj = _t("elements_adj")[e_idx] if isinstance(_t("elements_adj"), list) else e_base

        c_arr = _t("element_colors")
        c_str = c_arr[e_idx][a_idx % 2] if (isinstance(c_arr, list) and len(c_arr) > e_idx) else e_adj
        d_elem = c_str if eng_name == "mongol" else e_adj

        if lang == "ru":
            d_elem, a_year, a_month = d_elem.lower(), a_year.lower(), a_month.lower()

        # Added a_base for the nominative year box!
        return e_base, a_base, a_year, a_month, d_elem, m_idx, m_col, t_str

    # --- FETCH DATA & ATTRIBUTES ---
    y_val = getattr(tib, 'year', '--')
    m_val = getattr(tib, 'month', '--')
    is_leap = getattr(tib, 'is_leap_month', False)
    t_val = _n(getattr(tib, 'tithi', '--'))
    
    y_info = get_cached_year(engine, y_val) if y_val != '--' else None
    m_info = get_cached_month(engine, y_val, m_val, is_leap) if y_val != '--' else None
    
    y_attrs = getattr(y_info, 'attributes', {}) or {} if y_info else {}
    m_attrs = getattr(m_info, 'attributes', {}) or {} if m_info else {}
    l_attrs = getattr(info, 'lunar_attributes', {}) or {}

    # --- TRANSLATE UI LABELS ---
    lbl_tib_year = js.document.getElementById("lbl-tib-year")
    if lbl_tib_year: lbl_tib_year.innerText = _t("tib_year_title")

    # 1. Compact Blue Title
    js.document.getElementById("day-title").innerText = f"{cur_date.year}.{cur_date.month:02d}.{cur_date.day:02d}"

    # 2. Gregorian Box
    # Smart Lookup: Use Genitive array for specific dates if the language provides it!
    greg_months_gen = _t("greg_months_genitive")
    if isinstance(greg_months_gen, list) and len(greg_months_gen) > cur_date.month:
        greg_m_name = greg_months_gen[cur_date.month]
    else:
        greg_months = _t("greg_months")
        greg_m_name = greg_months[cur_date.month] if isinstance(greg_months, list) and len(greg_months) > cur_date.month else cur_date.strftime("%B")
    
    day_fmt = _t("day_card_greg_fmt")
    if day_fmt and day_fmt != "day_card_greg_fmt":
        greg_val_str = day_fmt.replace("{year}", str(cur_date.year)).replace("{month}", greg_m_name).replace("{day}", str(cur_date.day))
    else:
        greg_val_str = f"{greg_m_name} {cur_date.day}, {cur_date.year}"
        
    js.document.getElementById("day-val-greg").innerText = greg_val_str

    # 3. Weekday Box
    weekdays_long = _t("weekdays_long")
    js.document.getElementById("day-val-weekday").innerText = weekdays_long[cur_date.weekday()] if isinstance(weekdays_long, list) else cur_date.strftime("%A")
    js.document.getElementById("day-val-weekday").style.color = "var(--text-main)"
    
    # 4. Combined Rabjung & Tibetan Year Box
    if y_info:
        r_cyc = _n(getattr(y_info.tibetan, 'rabjung_cycle', ''))
        r_yr = _n(getattr(y_info.tibetan, 'rabjung_year', ''))

        # Extract the grammatical Element and Year-Animal (e.g., 'морин')
        # _get_attrs returns: e_base, a_base, a_year, a_month, d_elem, m_idx, m_col, t_str
        _, _, y_a_yr, _, y_elem, _, _, _ = _get_attrs(y_attrs)
        
        # Build the full string using the rabjung_fmt template
        rabjung_str = _t("rabjung_fmt").replace("{R}", str(r_cyc))\
                                       .replace("{Y}", str(r_yr))\
                                       .replace("{element}", y_elem)\
                                       .replace("{animal}", y_a_yr)
                                       
        # Apply the universal capitalization helper safely
        js.document.getElementById("day-val-year").innerHTML = _cap(rabjung_str)

    # 5. Month Box
    leap_str = _t("leap_suffix") if is_leap else ""
    _, _, _, m_anim, m_elem, _, _, _ = _get_attrs(m_attrs)
    
    if lang == "mn" and isinstance(m_val, int):
        seasons = _t("mn_seasons")
        m_base = f"{seasons.get(m_val, str(m_val))}{leap_str}" if isinstance(seasons, dict) else f"{m_val}{leap_str}"
    else:
        m_base = f"{_n(m_val)}{leap_str}"

    # Use the dedicated BOX formatter (which lacks "сар") and the universal capitalization!
    long_month = _t("tib_month_long_fmt").replace("{month}", m_base).replace("{element}", m_elem).replace("{animal}", m_anim)
    js.document.getElementById("day-val-month").innerText = _cap(long_month)

    # 6. Tithi Box & Title
    d_e_base, _, _, d_anim, d_elem, d_m_idx, d_m_col, d_t_str = _get_attrs(l_attrs)
    
    tithi_title = _t("tithi_title_fmt").replace("{element}", d_elem).replace("{animal}", d_anim)
    js.document.getElementById("lbl-tithi-title").innerText = _cap(tithi_title)
    js.document.getElementById("day-val-tithi").innerText = str(t_val)
    
    meta_str = ""
    if getattr(tib, 'occ', 1) == 2: meta_str = _t("duplicated_day")
    if getattr(tib, 'previous_tithi_skipped', False): meta_str = _t("skipped_day")
    js.document.getElementById("day-val-tithi-meta").innerText = meta_str

    # 7. Attributes Grid
    attr_grid = js.document.getElementById("day-attr-grid")
    if attr_grid and l_attrs:
        badges_html = f'''
            <span class="ext-badge">{_t("attr_element")}: {d_e_base}</span>
            <span class="ext-badge">{_t("attr_mewa")}: {_n(d_m_idx)} {d_m_col}</span>
            <span class="ext-badge">{_t("attr_trigram")}: {d_t_str}</span>
        '''
        attr_grid.innerHTML = badges_html
    elif attr_grid:
        attr_grid.innerHTML = f'<span class="ext-badge">No attributes available</span>'

def render_month_view(cur_date, engine):
    mode = APP_STATE.get("month_mode", "gregorian")
    container = js.document.getElementById("month-grid-container")
    lang = APP_STATE.get("lang", "en")
    
    # Helper to generate superscripts
    def fmt_mark(m): return f'<sup style="font-size: 0.65em; margin-left: 1px;">{m}</sup>' if m else ""

    if mode == "gregorian":
        y, m = cur_date.year, cur_date.month
        
        # Compact Blue Title
        js.document.getElementById("month-title").innerText = f"{y}.{m:02d}"
        
        # Long Sub-Title String
        greg_months = _t("greg_months")
        m_name = greg_months[m] if isinstance(greg_months, list) and len(greg_months) > m else cur_date.strftime("%B")
        long_title = _t("greg_month_long_fmt").replace("{month}", m_name).replace("{year}", _n(y))
        
        html = f'<div style="text-align: center; font-size: 1.1rem; font-weight: bold; color: var(--primary-color); margin-bottom: 15px;">{long_title}</div>'
        html += '<div class="month-grid">'
        
        weekdays = _t("weekdays")
        for d in weekdays: html += f'<div class="month-header">{d}</div>'
            
        REAL_TODAY = date.today()
        cal_matrix = calendar.monthcalendar(y, m)
        for week in cal_matrix:
            for d in week:
                if d == 0:
                    html += '<div class="month-cell empty"></div>'
                else:
                    cell_date = date(y, m, d)
                    cell_info = get_cached_day(engine, cell_date)
                    cell_tib = cell_info.tibetan
                    
                    m_num = _n(getattr(cell_tib, 'month', ''))
                    m_mark = ""
                    if getattr(cell_tib, 'is_leap_month', False):
                        m_mark = "-" if getattr(engine, 'leap_labeling', 'first_is_leap') == "first_is_leap" else "+"
                        
                    t_num = _n(getattr(cell_tib, 'tithi', ''))
                    t_mark = ""
                    if getattr(cell_tib, 'occ', 1) == 2: t_mark = "+"
                    elif getattr(cell_tib, 'previous_tithi_skipped', False): t_mark = "-"
                        
                    m_mark_html = f'<sup style="font-size: 0.75em;">{m_mark}</sup>' if m_mark else ""
                    month_sup = f'<sup style="font-size: 0.7em; margin-right: 2px; opacity: 0.75;">{m_mark_html}{m_num}</sup>'
                    tithi_sup = f'<sup style="font-size: 0.7em; margin-left: 2px;">{t_mark}</sup>'
                    combo_str = f"{month_sup}{t_num}{tithi_sup}"
                    
                    is_active = (d == cur_date.day)
                    is_real_today = (y == REAL_TODAY.year and m == REAL_TODAY.month and d == REAL_TODAY.day)
                    bg = "#eff6ff" if is_active else ""
                    border = "var(--primary-color)" if is_active else "var(--border-color)"
                    today_class = "real-today" if is_real_today else ""
                    
                    # Shrunk combo_str from 0.85rem to 0.75rem
                    html += f'''
                    <div class="month-cell {today_class}" style="background:{bg}; border-color:{border}; padding: 4px; display: flex; flex-direction: column; align-items: center; justify-content: center;" onclick="window.jump_to_specific_date({y}, {m}, {d})">
                        <div class="greg-date" style="font-size: 1.1rem; font-weight: bold; color: var(--text-main); line-height: 1.1;">{d}</div>
                        <div class="tib-tithi" style="font-size: 0.75rem; font-weight: bold; color: var(--primary-color); margin-top: 6px;">{combo_str}</div>
                    </div>'''

        html += '</div>'
        container.innerHTML = html

    else:
        # THE TIBETAN GRID
        anchor_info = get_cached_day(engine, cur_date)
        t_year = getattr(anchor_info.tibetan, 'year')
        t_month = getattr(anchor_info.tibetan, 'month')
        is_leap = getattr(anchor_info.tibetan, 'is_leap_month', False)
        
        m_info = get_cached_month(engine, t_year, t_month, is_leap)
        
        # --- 1. FETCH MONTH ATTRIBUTES ---
        m_attrs = getattr(m_info, 'attributes', {}) or {}
        elem_idx = m_attrs.get("element", 0)
        anim_idx = m_attrs.get("animal", 0)
        mewa_idx = m_attrs.get("mewa", 1)
        gender_idx = anim_idx % 2
        
        elem_base = _t("elements")[elem_idx] if isinstance(_t("elements"), list) else ""
        anim_base = _t("animals")[anim_idx] if isinstance(_t("animals"), list) else ""
        anim_month = _t("animals_month")[anim_idx] if isinstance(_t("animals_month"), list) else anim_base
        mewa_col = _t("mewa_colors")[mewa_idx - 1] if isinstance(_t("mewa_colors"), list) else ""
        elem_adj = _t("elements_adj")[elem_idx] if isinstance(_t("elements_adj"), list) else elem_base
        
        colors_arr = _t("element_colors")
        if isinstance(colors_arr, list) and len(colors_arr) > elem_idx:
            color_str = colors_arr[elem_idx][gender_idx]
        else:
            color_str = elem_adj  # Safe fallback
            
        if engine.id.name == "mongol":
            display_elem = color_str
        else:
            display_elem = elem_adj
        
        # Lowercase elements/animals for Russian and Mongolian mid-sentence grammar
        if lang in ("mn", "ru"):
            display_elem, anim_month = display_elem.lower(), anim_month.lower()
            
        t_year_str = _n(t_year)
        t_month_str = _n(t_month)
        leap_str = _t("leap_suffix") if is_leap else ""
        
        # Compact Blue Title (e.g., 2027/04-)
        m_mark = "-" if (is_leap and getattr(engine, 'leap_labeling', 'first_is_leap') == "first_is_leap") else ("+" if is_leap else "")
        js.document.getElementById("month-title").innerHTML = f"{t_year}/{t_month}<sup>{m_mark}</sup>"
        
        # --- 2. ASSEMBLE LONG TITLE ---
        if lang == "mn":
            seasons = _t("mn_seasons")
            season_name = seasons.get(t_month, str(t_month)) if isinstance(seasons, dict) else str(t_month)
            m_name = f"{season_name}{leap_str}"
        else:
            m_name = f"{t_month_str}{leap_str}"
            
        # 2a. Build the base month string (same as Day Card)
        long_month = _t("tib_month_long_fmt").replace("{month}", m_name)\
                                             .replace("{element}", display_elem)\
                                             .replace("{animal}", anim_month)
                                             
        # Capitalize the first letter for Mongolian/Russian grammar
        if lang in ("mn", "ru") and not long_month[0].isdigit():
            long_month = long_month[0].upper() + long_month[1:]
            
        # 2b. Wrap it with the Year for the Grid Title
        grid_fmt = _t("month_grid_title_fmt")
        if grid_fmt and grid_fmt != "month_grid_title_fmt":
            long_title = grid_fmt.replace("{year}", t_year_str).replace("{month_str}", long_month)
        else:
            long_title = f"{t_year_str}, {long_month}" # Fallback
        
        html = f'<div style="text-align: center; font-size: 1.1rem; font-weight: bold; color: var(--primary-color); margin-bottom: 15px;">{long_title}</div>'
        html += '<div class="month-grid" style="grid-template-columns: repeat(7, 1fr);">'
        
        for d in _t("weekdays"): html += f'<div class="month-header">{d}</div>'
        if m_info.days:
            first_weekday = m_info.days[0].civil_date.weekday()
            for _ in range(first_weekday): html += '<div class="month-cell empty"></div>'
            
            REAL_TODAY = date.today()
            for day in m_info.days:
                tib = day.tibetan
                c_date = day.civil_date
                
                bg = "#eff6ff" if c_date == cur_date else ""
                border = "var(--primary-color)" if c_date == cur_date else "var(--border-color)"
                today_class = "real-today" if c_date == REAL_TODAY else ""
                
                t_num = _n(getattr(tib, 'tithi', '--'))
                t_mark = ""
                if getattr(tib, 'occ', 1) == 2: t_mark = "+"
                if getattr(tib, 'previous_tithi_skipped', False): t_mark = "-"
                
                tithi_html = f"{t_num}{fmt_mark(t_mark)}"
                greg_label = f'<sup style="font-size: 0.7em; margin-right: 2px; opacity: 0.75;">{c_date.month}</sup>{c_date.day}'

                html += f'''
                <div class="month-cell {today_class}" style="background:{bg}; border-color:{border}; padding: 6px 4px; display: flex; flex-direction: column; align-items: center; justify-content: flex-start;" onclick="window.jump_to_specific_date({c_date.year}, {c_date.month}, {c_date.day})">
                    <div class="tib-tithi" style="font-size: 1.1rem; font-weight: bold; color: var(--primary-color); line-height: 1; margin-top: 2px;">{tithi_html}</div>
                    <div class="greg-date" style="font-size: 0.65rem; color: var(--text-muted); margin-top: 4px; white-space: nowrap;">{greg_label}</div>
                    <div class="attr-space" style="margin-top: auto; padding-top: 6px; display: flex; gap: 4px;">
                        <div style="width: 4px; height: 4px; border-radius: 50%; background: #94a3b8;"></div>
                        <div style="width: 4px; height: 4px; border-radius: 50%; background: #94a3b8;"></div>
                    </div>
                </div>'''
                                
        html += '</div>'
        
        # --- 3. BOTTOM ATTRIBUTES INJECTION ---
        if m_attrs:
            html += f'''
            <hr style="border: none; border-top: 1px solid var(--border-color); margin: 25px 0 15px 0;">
            <div class="ext-title" style="text-align: left; margin-bottom: 10px;">{_t("attr_title")}</div>
            <div style="display: flex; gap: 10px; justify-content: flex-start; flex-wrap: wrap;">
                <span class="ext-badge">{_t("attr_element")}: {elem_base}</span>
                <span class="ext-badge">{_t("attr_mewa")}: {_n(mewa_idx)} {mewa_col}</span>
            </div>'''
            
        container.innerHTML = html

def render_year_view(cur_date, engine):
    mode = APP_STATE.get("year_mode", "gregorian")
    container = js.document.getElementById("year-grid-container")
    
    # 1. Update the Year Spinner Label (The Blue Title)
    spinner_lbl = js.document.getElementById("label-year-spinner")
    if spinner_lbl:
        # Uses "Gregorian Year" vs "Tibetan Year" translations from i18n
        spinner_lbl.innerText = _t("year_prefix")
    
    if mode == "gregorian":
        y = cur_date.year
        js.document.getElementById("year-spinner").value = str(y)
        
        y_html = ""
        greg_months = _t("greg_months")
        
        for mi in range(1, 13):
            y_html += f'<div class="mini-month" onclick="window.jump_to_month_grid({y}, {mi}, 1)">'
            
            # 2. Translate Gregorian Mini-Month Titles
            m_name = greg_months[mi] if isinstance(greg_months, list) and len(greg_months) > mi else calendar.month_name[mi]
            y_html += f'<div class="mini-month-title">{m_name}</div>'
            
            y_html += '<div class="mini-month-body" style="grid-template-columns: repeat(7, 1fr);">'
            mini_matrix = calendar.monthcalendar(y, mi)
            REAL_TODAY = date.today()
            
            for week in mini_matrix:
                for d in week:
                    if d == 0:
                        y_html += '<div></div>'
                    else:
                        is_active = (d == cur_date.day and mi == cur_date.month)
                        is_real_today = (y == REAL_TODAY.year and mi == REAL_TODAY.month and d == REAL_TODAY.day)
                        
                        cell_date = date(y, mi, d)
                        tib = get_cached_day(engine, cell_date).tibetan
                        is_first_tib_day = (getattr(tib, 'linear_day', -1) == 1)
                        
                        day_text = str(d)
                        if is_first_tib_day:
                            day_text = f'<span style="color: var(--primary-color);">{d}</span>'
                        
                        if is_active:
                            y_html += f'<div style="background: var(--primary-color); color: white; border-radius: 50%; font-weight: bold;">{day_text}</div>'
                        elif is_real_today:
                            y_html += f'<div style="background: #10b981; color: white; border-radius: 50%; font-weight: bold;">{day_text}</div>'
                        else:
                            y_html += f'<div>{day_text}</div>'

            y_html += '</div></div>'
            
        container.innerHTML = y_html

    else:
        # THE TIBETAN GRID
        anchor_info = get_cached_day(engine, cur_date)
        t_year = getattr(anchor_info.tibetan, 'year')
        js.document.getElementById("year-spinner").value = str(t_year)
        
        y_info = get_cached_year(engine, t_year)
        lang = APP_STATE.get("lang", "en")
        
        # --- 1. FETCH YEAR ATTRIBUTES ---
        y_attrs = getattr(y_info, 'attributes', {}) or {}
        elem_idx = y_attrs.get("element", 0)
        anim_idx = y_attrs.get("animal", 0)
        mewa_idx = y_attrs.get("mewa", 1)
        gender_idx = anim_idx % 2
        
        elem_base = _t("elements")[elem_idx] if isinstance(_t("elements"), list) else ""
        elem_adj = _t("elements_adj")[elem_idx] if isinstance(_t("elements_adj"), list) else elem_base
        anim_base = _t("animals")[anim_idx] if isinstance(_t("animals"), list) else ""
        anim_year = _t("animals_year")[anim_idx] if isinstance(_t("animals_year"), list) else anim_base
        mewa_col = _t("mewa_colors")[mewa_idx - 1] if isinstance(_t("mewa_colors"), list) else ""
        
        colors_arr = _t("element_colors")
        if isinstance(colors_arr, list) and len(colors_arr) > elem_idx:
            color_str = colors_arr[elem_idx][gender_idx]
        else:
            color_str = elem_adj  # Safe fallback
            
        if engine.id.name == "mongol":
            display_elem = color_str
        else:
            display_elem = elem_adj
        
        # Lowercase elements/animals for Russian and Mongolian mid-sentence grammar
        if lang in ("mn", "ru"):
            anim_year, display_elem = anim_year.lower(), display_elem.lower()
            
        r_cycle = _n(getattr(y_info.tibetan, 'rabjung_cycle', ''))
        r_year = _n(getattr(y_info.tibetan, 'rabjung_year', ''))
        
        # --- 2. ASSEMBLE RABJUNG TITLE ---
        # This replaces get_rabjung_string(t_year) to include the element and animal!
        rabjung_str = _t("rabjung_fmt").replace("{R}", str(r_cycle))\
                                       .replace("{Y}", str(r_year))\
                                       .replace("{element}", display_elem)\
                                       .replace("{animal}", anim_year)
        
        y_html = f'<div style="grid-column: 1 / -1; width: 100%; text-align: center; margin-bottom: 15px; font-size: 1.1rem; font-weight: bold; color: var(--primary-color);">{rabjung_str}</div>'
        
        for m_info in y_info.months:
            m_tib = m_info.tibetan
            t_month = getattr(m_tib, 'month')
            is_leap = getattr(m_tib, 'is_leap_month', False)
            leap_str = _t("leap_suffix") if is_leap else ""
            
            if m_info.gregorian_start:
                gy, gm, gd = m_info.gregorian_start.year, m_info.gregorian_start.month, m_info.gregorian_start.day
                click_action = f'onclick="window.jump_to_month_grid({gy}, {gm}, {gd})"'
            else:
                click_action = ""
                
            y_html += f'<div class="mini-month" {click_action}>'
            
            # 4. Translate Tibetan Mini-Month Titles (with Mongolian Seasons)
            t_month_str = _n(t_month)
            if lang == "mn":
                seasons = _t("mn_seasons")
                season_name = seasons.get(t_month, str(t_month)) if isinstance(seasons, dict) else str(t_month)
                m_title = f"{season_name}{leap_str}"
            else:
                m_title = f"{_t('lunar_month')} {t_month_str}{leap_str}"
                
            y_html += f'<div class="mini-month-title">{m_title}</div>'
            y_html += '<div class="mini-month-body" style="grid-template-columns: repeat(7, 1fr);">'
            
            if m_info.days:
                first_weekday = m_info.days[0].civil_date.weekday()
                for _ in range(first_weekday):
                    y_html += '<div></div>'
            
                REAL_TODAY = date.today()
                for d_info in m_info.days:
                    tib = d_info.tibetan
                    tithi_val = _n(getattr(tib, "tithi", "--"))
                    
                    cell_style = ""
                    mark = ""
                    is_active = (d_info.civil_date == cur_date)
                    is_real_today = (d_info.civil_date == REAL_TODAY)
                    
                    if getattr(tib, 'occ', 1) == 2:
                        mark = "+"
                        cell_style = "color: var(--primary-color);"
                    elif getattr(tib, 'previous_tithi_skipped', False):
                        mark = "-"
                        cell_style = "color: var(--primary-color);"
                        
                    if is_active:
                        cell_style = "background: var(--primary-color); color: white; border-radius: 4px; font-weight: bold;"
                    elif is_real_today:
                        cell_style = "background: #10b981; color: white; border-radius: 4px; font-weight: bold;"
                        
                    y_html += f'<div style="{cell_style} padding: 4px 0; border-radius: 4px; text-align: center;">{tithi_val}<sup>{mark}</sup></div>'
                        
            y_html += '</div></div>'
            
        # --- 3. BOTTOM ATTRIBUTES INJECTION ---
        if y_attrs:
            y_html += f'''
            <div style="grid-column: 1 / -1; width: 100%;">
                <hr style="border: none; border-top: 1px solid var(--border-color); margin: 25px 0 15px 0;">
                <div class="ext-title" style="text-align: left; margin-bottom: 10px;">{_t("attr_title")}</div>
                <div style="display: flex; gap: 10px; justify-content: flex-start; flex-wrap: wrap;">
                    <span class="ext-badge">{_t("attr_element")}: {elem_base}</span>
                    <span class="ext-badge">{_t("attr_mewa")}: {_n(mewa_idx)} {mewa_col}</span>
                </div>
            </div>'''
            
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
        
        # Get the engine ID and the human-readable text from the dropdown
        select_el = js.document.getElementById("engine-select")
        engine_id = select_el.value
        engine_name = select_el.options.item(select_el.selectedIndex).text
        
        # 1. Update the blue Header Title
        # Get the current engine to determine naming
        eng_val = js.document.getElementById("engine-select").value
        
        # 1. Swap Losar to Tsagaan Sar if Mongol is selected
        main_title = _t("tsagaan_sar") if eng_val == "mongol" else _t("losar")
        
        # 2. Translate the engine name
        engines_dict = _t("engines")
        eng_name = engines_dict.get(eng_val, eng_val.capitalize()) if isinstance(engines_dict, dict) else eng_val.capitalize()
        
        # Build the translated title: e.g., "Цагаан сар - Пүг"
        header_title = f"{main_title} - {eng_name}"
        
        # Apply this title to Losar tab's title element
        title_el = js.document.getElementById("losar-title")
        if title_el:
            title_el.innerText = header_title
            
        output = js.document.getElementById("losar-output")
        output.innerHTML = "<em>Calculating...</em>"
        
        # Button styling for the +/- controls outside the table
        btn_style = 'style="cursor: pointer; padding: 4px 15px; margin: 0 5px; border-radius: 4px; border: 1px solid var(--border-color); background: #f1f5f9; font-weight: bold; color: var(--text-main);"'
        
        # 2. Top Controls (Before the table)
        html = f'''
        <div style="text-align: center; margin-bottom: 15px;">
            <button {btn_style} onclick="window.adjust_losar_range(-1, 0)" title="Extend list earlier">+</button>
            <button {btn_style} onclick="window.adjust_losar_range(1, 0)" title="Shrink list top" {"disabled" if start_y >= end_y else ""}>-</button>
        </div>
        '''
        
        # 3. Build the Table Header
        html += f'<table class="data-table"><tr><th style="text-align:center;">{_t("alignment")}</th><th>Date</th></tr>'
        
        for y in range(start_y, end_y + 1):
            eng_str = js.document.getElementById("engine-select").value
            losar_date = caltib.new_year_day(y, engine=eng_str)
            
            gy, gm, gd = losar_date.year, losar_date.month, losar_date.day
            
            # --- THE GENITIVE UPDATE ---
            greg_months_gen = _t("greg_months_genitive")
            if isinstance(greg_months_gen, list) and len(greg_months_gen) > gm:
                month_name = greg_months_gen[gm]
            else:
                greg_months = _t("greg_months")
                month_name = greg_months[gm] if isinstance(greg_months, list) and len(greg_months) > gm else losar_date.strftime("%B")
                
            short_fmt = _t("losar_date_fmt")
            if short_fmt and short_fmt != "losar_date_fmt":
                date_str = short_fmt.replace("{month}", month_name).replace("{day}", str(gd))
            else:
                date_str = f"{month_name} {gd}" # Fallback
            # ---------------------------

            date_link = f"<span class='clickable-link' style='color: var(--primary-color);' onclick='window.jump_to_specific_date({gy}, {gm}, {gd})'>{date_str}</span>"
            y_str = _n(y)
            
            html += f"<tr><td style='text-align: center;'>{y_str}</td><td>{date_link}</td></tr>"
            
        html += "</table>"
        
        # 4. Bottom Controls (After the table)
        html += f'''
        <div style="text-align: center; margin-top: 15px;">
            <button {btn_style} onclick="window.adjust_losar_range(0, -1)" title="Shrink list bottom" {"disabled" if start_y >= end_y else ""}>-</button>
            <button {btn_style} onclick="window.adjust_losar_range(0, 1)" title="Extend list later">+</button>
        </div>
        '''
        
        output.innerHTML = html
        
    except Exception as e:
        js.document.getElementById("losar-output").innerText = f"Error: {str(e)}"

js.window.generate_losar_list = pyodide.ffi.create_proxy(generate_losar_list)


# Start the app
init_app()