"""
caltib.i18n
-----------
Localization and translation dictionaries for the caltib UI.
"""

TRANSLATIONS = {
    "en": {
        "tab_day": "Day", "tab_month": "Month", "tab_year": "Year", "tab_losar": "Losar",
        "alignment": "Alignment", "lunar_month": "Lunar Month", "tithi": "Tithi (Lunar Day)",
        "leap_suffix": " (Leap)", "duplicated_day": "DUPLICATED DAY", "skipped_day": "Preceding Day Skipped",
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
        "weekdays_long": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "day_card_greg_fmt": "{month} {day}",
        "losar": "Losar",
        "tsagaan_sar": "Tsagaan Sar",
        "engines": {
            "phugpa": "Phugpa",
            "tsurphu": "Tsurphu",
            "mongol": "Mongol",
            "bhutan": "Bhutan",
            "karana": "Karana",
            "l0": "L0", "l1": "L1", "l2": "L2", "l3": "L3", "l4": "L4", "l5": "L5", "l6": "L6"
        },
        "attr_title": "Astrological Attributes",
        "attr_element": "Element", "attr_animal": "Animal", "attr_mewa": "Mewa", "attr_trigram": "Trigram",
        "elements": ["Wood", "Fire", "Earth", "Iron", "Water"],
        "animals": ["Mouse", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Sheep", "Monkey", "Bird", "Dog", "Pig"],
        "mewa_colors": ["White", "Black", "Blue", "Green", "Yellow", "White", "Red", "White", "Red"],
        "trigrams": ["Li", "Khon", "Dwa", "Khen", "Kham", "Gin", "Zin", "Zon"],
    },
    "bo": { # Tibetan
        "tab_day": "ཉིན་རེ།", "tab_month": "ཟླ་རེ།", "tab_year": "ལོ་རེ།", "tab_losar": "ལོ་གསར།",
        "alignment": "རབ་བྱུང་།", "lunar_month": "ཟླ་བ།", "tithi": "ཚེས་པ།",
        "leap_suffix": " (ཟླ་ཤོལ)", "duplicated_day": "ཞག་ལྷག", "skipped_day": "སྔོན་མའི་ཚེས་ཆད་པ།",
        "weekdays": ["ཟླ་བ", "མིག་དམར", "ལྷག་པ", "ཕུར་བུ", "པ་སངས", "སྤེན་པ", "ཉི་མ"],
        "greg_grid": "སྤྱི་ཟླའི་རེའུ་མིག", "tib_grid": "བོད་ཟླའི་རེའུ་མིག",
        "greg_year": "སྤྱི་ལོ།", "tib_year": "བོད་ལོ།",
        "month_prefix": "ཟླ་བ ", "year_prefix": "ལོ ",
        "greg_months": ["", "སྤྱི་ཟླ་ 1", "སྤྱི་ཟླ་ 2", "སྤྱི་ཟླ་ 3", "སྤྱི་ཟླ་ 4", "སྤྱི་ཟླ་ 5", "སྤྱི་ཟླ་ 6", "སྤྱི་ཟླ་ 7", "སྤྱི་ཟླ་ 8", "སྤྱི་ཟླ་ 9", "སྤྱི་ཟླ་ 10", "སྤྱི་ཟླ་ 11", "སྤྱི་ཟླ་ 12"],
        "rabjung_fmt": "རབ་བྱུང་ {R} པའི་ལོ་ {Y}",
        "day_title_fmt": "སྤྱི་ལོ་ {year} {month} ཚེས་ {day}",
        "weekday_lbl": "གཟའ།",
        "greg_month_long_fmt": "སྤྱི་ལོ་ {year} {month}",
        "tib_month_long_fmt": "བོད་ལོ་ {year}, ཟླ་བ་ {month}",
        "greg_date_lbl": "སྤྱི་ཚེས།",
        "weekdays_long": ["གཟའ་ཟླ་བ།", "གཟའ་མིག་དམར།", "གཟའ་ལྷག་པ།", "གཟའ་ཕུར་བུ།", "གཟའ་པ་སངས།", "གཟའ་སྤེན་པ།", "གཟའ་ཉི་མ།"],
        "day_card_greg_fmt": "{month} ཚེས་ {day}",
        "losar": "ལོ་གསར།",
        "tsagaan_sar": "Tsagaan Sar", # Or Tibetan phonetic equivalent
        "engines": {
            "phugpa": "ཕུག་པ།",
            "tsurphu": "མཚུར་ཕུ།",
            "mongol": "སོག་པོ།",
            "bhutan": "འབྲུག་ལུགས།",
            "karana": "བྱེད་རྩིས།",
            "l0": "L0", "l1": "L1", "l2": "L2", "l3": "L3", "l4": "L4", "l5": "L5", "l6": "L6"
        },
        "attr_title": "རྩིས་ཀྱི་འབྲས་བུ།",
        "attr_element": "ཁམས།", "attr_animal": "ལོ་རྟགས།", "attr_mewa": "སྨེ་བ།", "attr_trigram": "སྤར་ཁ།",
        "elements": ["ཤིང་།", "མེ།", "ས།", "ལྕགས།", "ཆུ།"],
        "animals": ["བྱི་བ།", "གླང་།", "སྟག", "ཡོས།", "འབྲུག", "སྦྲུལ།", "རྟ།", "ལུག", "སྤྲེའུ།", "བྱ།", "ཁྱི།", "ཕག"],
        "mewa_colors": ["དཀར་པོ།", "ནག་པོ།", "མཐིང་ག", "ལྗང་གུ", "སེར་པོ།", "དཀར་པོ།", "དམར་པོ།", "དཀར་པོ།", "དམར་པོ།"],
        "trigrams": ["ལི།", "ཁོན།", "དྭ།", "ཁེན།", "ཁམ།", "གིན།", "ཟིན།", "ཟོན།"],
    },
    "dz": { # Dzongkha (Bhutanese)
        "tab_day": "ཉིནམ།", "tab_month": "ཟླཝ།", "tab_year": "ལོ།", "tab_losar": "ལོ་གསར།",
        "alignment": "རབ་བྱུང་།", "lunar_month": "ཟླཝ།", "tithi": "ཚེས།",
        "leap_suffix": " (ཟླ་ཤོལ)", "duplicated_day": "ཞག་ལྷག", "skipped_day": "ཧེ་མའི་ཚེས་ཆདཔ།",
        "weekdays": ["ཟླཝ་", "མིག་དམར་", "ལྷགཔ་", "ཕུར་བུ་", "པ་སངས་", "སྤེན་པ་", "ཉིམ་"],
        "greg_grid": "ཕྱི་ཟླའི་རེའུ་མིག", "tib_grid": "རང་ཟླའི་རེའུ་མིག",
        "greg_year": "ཕྱི་ལོ།", "tib_year": "རང་ལོ།",
        "month_prefix": "ཟླཝ་ ", "year_prefix": "ལོ་ ",
        "rabjung_fmt": "རབ་བྱུང་ {R} པའི་ལོ་ {Y}",
        "day_title_fmt": "ཕྱི་ལོ་ {year} {month} ཚེས་ {day}",
        "weekday_lbl": "གཟའ།",
        "greg_months": ["", "སྤྱི་ཟླ་ 1", "སྤྱི་ཟླ་ 2", "སྤྱི་ཟླ་ 3", "སྤྱི་ཟླ་ 4", "སྤྱི་ཟླ་ 5", "སྤྱི་ཟླ་ 6", "སྤྱི་ཟླ་ 7", "སྤྱི་ཟླ་ 8", "སྤྱི་ཟླ་ 9", "སྤྱི་ཟླ་ 10", "སྤྱི་ཟླ་ 11", "སྤྱི་ཟླ་ 12"],
        "greg_month_long_fmt": "ཕྱི་ལོ་ {year} ཟླཝ་ {month}",
        "tib_month_long_fmt": "རང་ལོ་ {year}, ཟླཝ་ {month}",
        "greg_date_lbl": "ཕྱི་ཚེས།",
        "weekdays_long": ["གཟའ་ཟླཝ།", "གཟའ་མིག་དམར།", "གཟའ་ལྷགཔ།", "གཟའ་ཕུར་བུ།", "གཟའ་པ་སངས།", "གཟའ་སྤེན་པ།", "གཟའ་ཉིམ།"],
        "losar": "ལོ་གསར།",
        "tsagaan_sar": "Tsagaan Sar",
        "day_card_greg_fmt": "{month} ཚེས་ {day}",
        "engines": {
            "phugpa": "ཕུག་པ།",
            "tsurphu": "མཚུར་ཕུ།",
            "mongol": "སོག་པོ།",
            "bhutan": "འབྲུག་ལུགས།",
            "karana": "བྱེད་རྩིས།",
            "l0": "L0", "l1": "L1", "l2": "L2", "l3": "L3", "l4": "L4", "l5": "L5", "l6": "L6"
        },
        "attr_title": "རྩིས་ཀྱི་འབྲས་བུ།",
        "attr_element": "ཁམས།", "attr_animal": "ལོ་རྟགས།", "attr_mewa": "སྨེ་བ།", "attr_trigram": "སྤར་ཁ།",
        "elements": ["ཤིང་།", "མེ།", "ས།", "ལྕགས།", "ཆུ།"],
        "animals": ["བྱི་བ།", "གླང་།", "སྟག", "ཡོས།", "འབྲུག", "སྦྲུལ།", "རྟ།", "ལུག", "སྤྲེའུ།", "བྱ།", "ཁྱི།", "ཕག"],
        "mewa_colors": ["དཀར་པོ།", "ནག་པོ།", "མཐིང་ག", "ལྗང་གུ", "སེར་པོ།", "དཀར་པོ།", "དམར་པོ།", "དཀར་པོ།", "དམར་པོ།"],
        "trigrams": ["ལི།", "ཁོན།", "དྭ།", "ཁེན།", "ཁམ།", "གིན།", "ཟིན།", "ཟོན།"],
    },
    "mn": { # Mongolian (Cyrillic)
        "tab_day": "Өдөр", "tab_month": "Сар", "tab_year": "Жил", "tab_losar": "Цагаан сар",
        "alignment": "Жил", "lunar_month": "Билгийн сар", "tithi": "Шинийн",
        "leap_suffix": " (Илүү)", "duplicated_day": "ДАВХАР ӨДӨР", "skipped_day": "Өмнөх өдөр тасарсан",
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
        "weekdays_long": ["Даваа", "Мягмар", "Лхагва", "Пүрэв", "Баасан", "Бямба", "Ням"],
        "day_card_greg_fmt": "{month}ын {day}", 
        "losar": "Лосар",
        "tsagaan_sar": "Цагаан сар",
        "engines": {
            "phugpa": "Пүг",
            "tsurphu": "Цүр",
            "mongol": "Төгсбуянт",
            "bhutan": "Бутан",
            "karana": "Карана",
            "l0": "L0", "l1": "L1", "l2": "L2", "l3": "L3", "l4": "L4", "l5": "L5", "l6": "L6"
        },
        # Mongolian Seasonal Abbreviations
        "mn_seasons": {
            1: "Хаврын эхэн", 2: "Хаврын дунд", 3: "Хаврын эцэс",
            4: "Зуны эхэн", 5: "Зуны дунд", 6: "Зуны эцэс",
            7: "Намрын эхэн", 8: "Намрын дунд", 9: "Намрын эцэс",
            10: "Өвлийн эхэн", 11: "Өвлийн дунд", 12: "Өвлийн эцэс"
        },
        "attr_title": "Зурхайн мэдээлэл",
        "attr_element": "Махбод", "attr_animal": "Амьтан", "attr_mewa": "Мэнгэ", "attr_trigram": "Суудал",
        "elements": ["Мод", "Гал", "Шороо", "Төмөр", "Ус"],
        "animals": ["Хулгана", "Үхэр", "Бар", "Туулай", "Луу", "Могой", "Морь", "Хонь", "Бич", "Тахиа", "Нохой", "Гахай"],
        "mewa_colors": ["цагаан", "хар", "хөх", "ногоон", "шар", "цагаан", "улаан", "цагаан", "улаан"],
        "trigrams": ["Гал", "Шороо", "Төмөр", "Огторгуй", "Ус", "Уул", "Мод", "Хий"],
    },
    "ru": { # Russian
        "tab_day": "День", "tab_month": "Месяц", "tab_year": "Год", "tab_losar": "Лосар",
        "alignment": "Год", "lunar_month": "Лунный месяц", "tithi": "Лунный день (Титхи)",
        "leap_suffix": " (Високосный)", "duplicated_day": "ДУБЛИРУЮЩИЙСЯ ДЕНЬ", "skipped_day": "Предыдущий день пропущен",
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
        "weekdays_long": ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"],
        "day_card_greg_fmt": "{day} {month}", # In Russian, the day number usually comes first
        "losar": "Лосар",
        "tsagaan_sar": "Цагаан сар",
        "engines": {
            "phugpa": "Пхугпа",
            "tsurphu": "Цурпху",
            "mongol": "Монгольский",
            "bhutan": "Бутан",
            "karana": "Карана",
            "l0": "L0", "l1": "L1", "l2": "L2", "l3": "L3", "l4": "L4", "l5": "L5", "l6": "L6"
        },
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