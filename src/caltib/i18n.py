"""
caltib.i18n
-----------
Localization and translation dictionaries for the caltib UI.
"""

TRANSLATIONS = {
    "en": {
        "tab_day": "Day", "tab_month": "Month", "tab_year": "Year", "tab_losar": "Losar",
        "alignment": "Alignment", "lunar_month": "Lunar Month", "tithi": "Tithi (Lunar Day)",
        "leap_suffix": " (Leap)", "duplicated_day": "DUPLICATED DAY", "skipped_day": "PRECEDING DAY SKIPPED",
        "dup_short": "+", "skip_short": "⚠",
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "greg_grid": "Gregorian Grid", "tib_grid": "Tibetan Grid",
        "greg_year": "Gregorian Year", "tib_year": "Tibetan Year",
        "month_prefix": "Month ", "year_prefix": "Year ",
        "greg_months": ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
        "rabjung_fmt": "Rabjung {R}, Year {Y}",
        "day_title_fmt": "{month} {day}, {year}",
        "weekday_lbl": "Weekday",
        "greg_month_long_fmt": "{month} {year}",
        "tib_month_long_fmt": "Year {year}, Lunar Month {month}",
        "greg_date_lbl": "Gregorian",
    },
    "bo": { # Tibetan
        "tab_day": "ཉིན་རེ།", "tab_month": "ཟླ་རེ།", "tab_year": "ལོ་རེ།", "tab_losar": "ལོ་གསར།",
        "alignment": "རབ་བྱུང་།", "lunar_month": "ཟླ་བ།", "tithi": "ཚེས་པ།",
        "leap_suffix": " (ཟླ་ཤོལ)", "duplicated_day": "ཞག་ལྷག", "skipped_day": "ཞག་ཆད",
        "dup_short": "+", "skip_short": "⚠",
        "weekdays": ["ཟླ་བ", "མིག་དམར", "ལྷག་པ", "ཕུར་བུ", "པ་སངས", "སྤེན་པ", "ཉི་མ"],
        "greg_grid": "སྤྱི་ཟླའི་རེའུ་མིག", "tib_grid": "བོད་ཟླའི་རེའུ་མིག",
        "greg_year": "སྤྱི་ལོ།", "tib_year": "བོད་ལོ།",
        "month_prefix": "ཟླ་བ ", "year_prefix": "ལོ ",
        "greg_months": ["", "སྤྱི་ཟླ་དང་པོ།", "སྤྱི་ཟླ་གཉིས་པ།", "སྤྱི་ཟླ་གསུམ་པ།", "སྤྱི་ཟླ་བཞི་པ།", "སྤྱི་ཟླ་ལྔ་པ།", "སྤྱི་ཟླ་དྲུག་པ།", "སྤྱི་ཟླ་བདུན་པ།", "སྤྱི་ཟླ་བརྒྱད་པ།", "སྤྱི་ཟླ་དགུ་པ།", "སྤྱི་ཟླ་བཅུ་པ།", "སྤྱི་ཟླ་བཅུ་གཅིག་པ།", "སྤྱི་ཟླ་བཅུ་གཉིས་པ།"],
        "rabjung_fmt": "རབ་བྱུང་ {R} པའི་ལོ་ {Y}",
        "day_title_fmt": "སྤྱི་ལོ་ {year} ཟླ་ {month} ཚེས་ {day}",
        "weekday_lbl": "གཟའ།",
        "greg_month_long_fmt": "སྤྱི་ལོ་ {year} {month}",
        "tib_month_long_fmt": "བོད་ལོ་ {year}, ཟླ་བ་ {month}",
        "greg_date_lbl": "སྤྱི་ཚེས།",
    },
    "dz": { # Dzongkha (Bhutanese)
        "tab_day": "ཉིནམ།", "tab_month": "ཟླཝ།", "tab_year": "ལོ།", "tab_losar": "ལོ་གསར།",
        "alignment": "རབ་བྱུང་།", "lunar_month": "ཟླཝ།", "tithi": "ཚེས།",
        "leap_suffix": " (ཟླ་ཤོལ)", "duplicated_day": "ཞག་ལྷག", "skipped_day": "ཞག་ཆད",
        "dup_short": "+", "skip_short": "⚠",
        "weekdays": ["ཟླཝ་", "མིག་དམར་", "ལྷགཔ་", "ཕུར་བུ་", "པ་སངས་", "སྤེན་པ་", "ཉིམ་"],
        "greg_grid": "ཕྱི་ཟླའི་རེའུ་མིག", "tib_grid": "རང་ཟླའི་རེའུ་མིག",
        "greg_year": "ཕྱི་ལོ།", "tib_year": "རང་ལོ།",
        "month_prefix": "ཟླཝ་ ", "year_prefix": "ལོ་ ",
        "rabjung_fmt": "རབ་བྱུང་ {R} པའི་ལོ་ {Y}",
        "day_title_fmt": "ཕྱི་ལོ་ {year} ཟླཝ་ {month} ཚེས་ {day}",
        "weekday_lbl": "གཟའ།",
        "greg_months": ["", "སྤྱི་ཟླ་ ༡ པ།", "སྤྱི་ཟླ་ ༢ པ།", "སྤྱི་ཟླ་ ༣ པ།", "སྤྱི་ཟླ་ ༤ པ།", "སྤྱི་ཟླ་ ༥ པ།", "སྤྱི་ཟླ་ ༦ པ།", "སྤྱི་ཟླ་ ༧ པ།", "སྤྱི་ཟླ་ ༨ པ།", "སྤྱི་ཟླ་ ༩ པ།", "སྤྱི་ཟླ་ ༡༠ པ།", "སྤྱི་ཟླ་ ༡༡ པ།", "སྤྱི་ཟླ་ ༡༢ པ།"],
        "greg_month_long_fmt": "ཕྱི་ལོ་ {year} ཟླཝ་ {month}",
        "tib_month_long_fmt": "རང་ལོ་ {year}, ཟླཝ་ {month}",
        "greg_date_lbl": "ཕྱི་ཚེས།",
    },
    "mn": { # Mongolian (Cyrillic)
        "tab_day": "Өдөр", "tab_month": "Сар", "tab_year": "Жил", "tab_losar": "Цагаан сар",
        "alignment": "Жил", "lunar_month": "Билгийн сар", "tithi": "Шинийн",
        "leap_suffix": " (Илүү)", "duplicated_day": "ДАВХАР ӨДӨР", "skipped_day": "ТАСАРСАН ӨДӨР",
        "dup_short": "+", "skip_short": "⚠",
        "weekdays": ["Да", "Мя", "Лх", "Пү", "Ба", "Бя", "Ня"],
        "greg_grid": "Аргын тоолол", "tib_grid": "Билгийн тоолол",
        "greg_year": "Аргын жил", "tib_year": "Билгийн жил",
        "month_prefix": "Сар ", "year_prefix": "Жил ",
        "rabjung_fmt": "{R}-р жаран, {Y}-р он",
        "day_title_fmt": "{year} оны {month}-р сарын {day}",
        "weekday_lbl": "Гараг",
        "greg_months": ["", "1-р сар", "2-р сар", "3-р сар", "4-р сар", "5-р сар", "6-р сар", "7-р сар", "8-р сар", "9-р сар", "10-р сар", "11-р сар", "12-р сар"],
        "greg_month_long_fmt": "{year} оны {month}",
        "tib_month_long_fmt": "{year} он, {month}",
        "greg_date_lbl": "Аргын өдөр",
        # Mongolian Seasonal Abbreviations
        "mn_seasons": {
            1: "Хаврын эхэн", 2: "Хаврын дунд", 3: "Хаврын эцэс",
            4: "Зуны эхэн", 5: "Зуны дунд", 6: "Зуны эцэс",
            7: "Намрын эхэн", 8: "Намрын дунд", 9: "Намрын эцэс",
            10: "Өвлийн эхэн", 11: "Өвлийн дунд", 12: "Өвлийн эцэс"
        }
    },
    "ru": { # Russian
        "tab_day": "День", "tab_month": "Месяц", "tab_year": "Год", "tab_losar": "Лосар",
        "alignment": "Год", "lunar_month": "Лунный месяц", "tithi": "Лунный день (Титхи)",
        "leap_suffix": " (Високосный)", "duplicated_day": "ДУБЛИРУЮЩИЙСЯ ДЕНЬ", "skipped_day": "ПРОПУЩЕННЫЙ ДЕНЬ",
        "dup_short": "+", "skip_short": "⚠",
        "weekdays": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
        "greg_grid": "Григорианский", "tib_grid": "Тибетский",
        "greg_year": "Григорианский год", "tib_year": "Тибетский год",
        "month_prefix": "Месяц ", "year_prefix": "Год ",
        "rabjung_fmt": "{R}-й цикл Рабджунг, год {Y}",
        "day_title_fmt": "{day} {month} {year} г.",
        "weekday_lbl": "День недели",
        "greg_months": ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"],
        "greg_month_long_fmt": "{month} {year} г.",
        "tib_month_long_fmt": "Год {year}, Лунный месяц {month}",
        "greg_date_lbl": "Григорианский",
    }
}

# Fast numeral translator mapping Arabic to Tibetan Unicode digits
TIBETAN_DIGITS = str.maketrans("0123456789", "༠༡༢༣༤༥༦༧༨༩")

def translate(key: str, lang: str = "en") -> str:
    """Returns the translated string for a given key."""
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

def localize_num(num: int | str, lang: str = "en") -> str:
    """Translates numeric characters if the target language uses a different script."""
    num_str = str(num)
    if lang in ("bo", "dz"):
        return num_str.translate(TIBETAN_DIGITS)
    return num_str