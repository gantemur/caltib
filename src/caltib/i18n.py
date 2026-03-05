"""
caltib.i18n
-----------
Localization and translation dictionaries for the caltib UI.
"""

TRANSLATIONS = {
    "en": {
        "tab_day": "Day", "tab_month": "Month", "tab_year": "Year", "tab_losar": "Losar",
        "alignment": "Alignment", "lunar_month": "Lunar Month", "tithi": "Tithi (Lunar Day)",
        "leap_suffix": " (Leap)", "duplicated_day": "Duplicated Day", "skipped_day": "Preceding Day Skipped",
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "greg_grid": "Gregorian Grid", "tib_grid": "Tibetan Grid",
        "greg_year": "Gregorian Year", "tib_year": "Tibetan Year",
        "month_prefix": "Month ", "year_prefix": "Year ",
        "greg_months": ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
        "day_title_fmt": "{month} {day}, {year}",
        "weekday_lbl": "Weekday",
        "month_grid_title_fmt": "Year {year}, {month_str}",
        "greg_month_long_fmt": "{month} {year}",
        "rabjung_fmt": "Rabjung {R}, Year {Y}, {element} {animal}",
        "rabjung_year_fmt": "Rabjung {R}, Year {Y}",
        "greg_date_lbl": "Gregorian",
        "weekdays_long": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "day_card_greg_fmt": "{month} {day}, {year}",
        "rabjung_title": "Rabjung",
        "tib_year_title": "Tibetan Year",
        "year_fmt": "Year {year}",
        "tib_month_long_fmt": "Lunar Month {month}, {element} {animal}",
        "tib_month_box_fmt": "Lunar Month {month}, {element} {animal}",
        "tithi_title_fmt": "{element} {animal} • Lunar Day",
        "losar": "Losar",
        "tsagaan_sar": "Tsagaan Sar",
        "losar_date_fmt": "{month} {day}",
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
        "elements_adj": ["Wood", "Fire", "Earth", "Iron", "Water"],
        "animals": ["Mouse", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Sheep", "Monkey", "Bird", "Dog", "Pig"],
        "mewa_colors": ["White", "Black", "Blue", "Green", "Yellow", "White", "Red", "White", "Red"],
        "trigrams": ["Li", "Khon", "Dwa", "Khen", "Kham", "Gin", "Zin", "Zon"],
        "element_colors": [["Blue", "Blue"], ["Red", "Red"], ["Yellow", "Yellow"], ["White", "White"], ["Black", "Black"]],
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
        "day_title_fmt": "སྤྱི་ལོ་ {year} {month} ཚེས་ {day}",
        "weekday_lbl": "གཟའ།",
        "month_grid_title_fmt": "བོད་ལོ་ {year}, {month_str}",
        "rabjung_fmt": "རབ་བྱུང་ {R} པའི་ལོ་ {Y}, {element} {animal}",
        "rabjung_year_fmt": "རབ་བྱུང་ {R} པའི་ལོ་ {Y}",
        "greg_date_lbl": "སྤྱི་ཚེས།",
        "weekdays_long": ["གཟའ་ཟླ་བ།", "གཟའ་མིག་དམར།", "གཟའ་ལྷག་པ།", "གཟའ་ཕུར་བུ།", "གཟའ་པ་སངས།", "གཟའ་སྤེན་པ།", "གཟའ་ཉི་མ།"],
        "day_card_greg_fmt": "ཕྱི་ལོ་ {year} {month} ཚེས་ {day}",
        "greg_month_long_fmt": "སྤྱི་ལོ་ {year} {month}",
        "rabjung_title": "རབ་བྱུང་།",
        "tib_year_title": "བོད་ལོ།",
        "year_fmt": "ལོ་ {year}",
        "tib_month_long_fmt": "ཟླ་བ་ {month}, {element} {animal}",
        "tib_month_box_fmt": "ཟླ་བ་ {month}, {element} {animal}",
        "tithi_title_fmt": "{element} {animal} • ཚེས།",
        "losar": "ལོ་གསར།",
        "tsagaan_sar": "Tsagaan Sar", # Or Tibetan phonetic equivalent
        "losar_date_fmt": "ཕྱི་ཟླ་ {month} ཚེས་ {day}", # Adjust prefix if needed
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
        "elements_adj": ["ཤིང་", "མེ་", "ས་", "ལྕགས་", "ཆུ་"],
        "element_colors": [
            ["སྔོན་པོ།", "སྔོན་པོ།"], 
            ["དམར་པོ།", "དམར་པོ།"], 
            ["སེར་པོ།", "སེར་པོ།"], 
            ["དཀར་པོ།", "དཀར་པོ།"], 
            ["ནག་པོ།", "ནག་པོ།"]
        ],
    },
    "dz": { # Dzongkha (Bhutanese)
        "tab_day": "ཉིནམ།", "tab_month": "ཟླཝ།", "tab_year": "ལོ།", "tab_losar": "ལོ་གསར།",
        "alignment": "རབ་བྱུང་།", "lunar_month": "ཟླཝ།", "tithi": "ཚེས།",
        "leap_suffix": " (ཟླ་ཤོལ)", "duplicated_day": "ཞག་ལྷག", "skipped_day": "ཧེ་མའི་ཚེས་ཆདཔ།",
        "weekdays": ["ཟླཝ་", "མིག་དམར་", "ལྷགཔ་", "ཕུར་བུ་", "པ་སངས་", "སྤེན་པ་", "ཉིམ་"],
        "greg_grid": "ཕྱི་ཟླའི་རེའུ་མིག", "tib_grid": "རང་ཟླའི་རེའུ་མིག",
        "greg_year": "ཕྱི་ལོ།", "tib_year": "རང་ལོ།",
        "month_prefix": "ཟླཝ་ ", "year_prefix": "ལོ་ ",
        "day_title_fmt": "ཕྱི་ལོ་ {year} {month} ཚེས་ {day}",
        "weekday_lbl": "གཟའ།",
        "month_grid_title_fmt": "བོད་ལོ་ {year}, {month_str}",
        "greg_months": ["", "སྤྱི་ཟླ་ 1", "སྤྱི་ཟླ་ 2", "སྤྱི་ཟླ་ 3", "སྤྱི་ཟླ་ 4", "སྤྱི་ཟླ་ 5", "སྤྱི་ཟླ་ 6", "སྤྱི་ཟླ་ 7", "སྤྱི་ཟླ་ 8", "སྤྱི་ཟླ་ 9", "སྤྱི་ཟླ་ 10", "སྤྱི་ཟླ་ 11", "སྤྱི་ཟླ་ 12"],
        "rabjung_fmt": "རབ་བྱུང་ {R} པའི་ལོ་ {Y}, {element} {animal}",
        "rabjung_year_fmt": "རབ་བྱུང་ {R} པའི་ལོ་ {Y}",
        "greg_date_lbl": "ཕྱི་ཚེས།",
        "weekdays_long": ["གཟའ་ཟླཝ།", "གཟའ་མིག་དམར།", "གཟའ་ལྷགཔ།", "གཟའ་ཕུར་བུ།", "གཟའ་པ་སངས།", "གཟའ་སྤེན་པ།", "གཟའ་ཉིམ།"],
        "losar": "ལོ་གསར།",
        "tsagaan_sar": "Tsagaan Sar",
        "losar_date_fmt": "ཕྱི་ཟླ་ {month} ཚེས་ {day}", # Adjust prefix if needed
        "day_card_greg_fmt": "ཕྱི་ལོ་ {year} {month} ཚེས་ {day}",
        "greg_month_long_fmt": "སྤྱི་ལོ་ {year} {month}",
        "rabjung_title": "རབ་བྱུང་།",
        "tib_year_title": "བོད་ལོ།",
        "year_fmt": "ལོ་ {year}",
        "tib_month_long_fmt": "ཟླ་བ་ {month}, {element} {animal}",
        "tib_month_box_fmt": "ཟླ་བ་ {month}, {element} {animal}",
        "tithi_title_fmt": "{element} {animal} • ཚེས།",
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
        "elements_adj": ["ཤིང་", "མེ་", "ས་", "ལྕགས་", "ཆུ་"],
        "element_colors": [
            ["སྔོན་པོ།", "སྔོན་པོ།"], 
            ["དམར་པོ།", "དམར་པོ།"], 
            ["སེར་པོ།", "སེར་པོ།"], 
            ["དཀར་པོ།", "དཀར་པོ།"], 
            ["ནག་པོ།", "ནག་པོ།"]
        ],
    },
    "mn": { # Mongolian (Cyrillic)
        "tab_day": "Өдөр", "tab_month": "Сар", "tab_year": "Жил", "tab_losar": "Цагаан сар",
        "alignment": "Жил", "lunar_month": "Билгийн сар", "tithi": "Шинийн",
        "leap_suffix": " (Илүү)", "duplicated_day": "Давхар өдөр", "skipped_day": "Өмнөх өдөр тасарсан",
        "weekdays": ["Да", "Мя", "Лх", "Пү", "Ба", "Бя", "Ня"],
        "greg_grid": "Аргын тоолол", "tib_grid": "Билгийн тоолол",
        "greg_year": "Аргын жил", "tib_year": "Билгийн жил",
        "month_prefix": "Сар ", "year_prefix": "Жил ",
        "weekday_lbl": "Гараг",
        "month_grid_title_fmt": "{year} он, {month_str}",
        "greg_months": ["", "1-р сар", "2-р сар", "3-р сар", "4-р сар", "5-р сар", "6-р сар", "7-р сар", "8-р сар", "9-р сар", "10-р сар", "11-р сар", "12-р сар"],
        "greg_months_genitive": ["", "1-р сарын", "2-р сарын", "3-р сарын", "4-р сарын", "5-р сарын", "6-р сарын", "7-р сарын", "8-р сарын", "9-р сарын", "10-р сарын", "11-р сарын", "12-р сарын"],
        "day_card_greg_fmt": "{year} оны {month} {day}",
        "day_title_fmt": "{year} оны {month} {day}",
        "greg_month_long_fmt": "{year} оны {month}",
        "tib_month_box_fmt": "{month} {element} {animal}",
        "tib_month_long_fmt": "{month} {element} {animal} сар",
        "rabjung_fmt": "{R}-р жарны {Y} он {element} {animal} жил",
        "rabjung_year_fmt": "{R}-р жарны {Y} он",
        "greg_date_lbl": "Аргын өдөр",
        "weekdays_long": ["Даваа", "Мягмар", "Лхагва", "Пүрэв", "Баасан", "Бямба", "Ням"],
        "rabjung_title": "Жаран",
        "year_fmt": "{year} он",
        "tib_year_title": "Билгийн жил",
        "tithi_title_fmt": "{element} {animal} өдөр шинийн",
        "losar": "Лосар",
        "tsagaan_sar": "Цагаан сар",
        "losar_date_fmt": "{month} {day}",
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
            1: "Хаврын тэргүүн", 2: "Хаврын дунд", 3: "Хаврын сүүл",
            4: "Зуны эхэн", 5: "Зуны дунд", 6: "Зуны сүүл",
            7: "Намрын эхэн", 8: "Намрын дунд", 9: "Намрын сүүл",
            10: "Өвлийн эхэн", 11: "Өвлийн дунд", 12: "Өвлийн сүүл"
        },
        "attr_title": "Зурхайн мэдээлэл",
        "attr_element": "Махбод", "attr_animal": "Амьтан", "attr_mewa": "Мэнгэ", "attr_trigram": "Суудал",
        "elements": ["Мод", "Гал", "Шороо", "Төмөр", "Ус"],
        "elements_adj": ["модон", "гал", "шороон", "төмөр", "усан"],
        "animals": ["Хулгана", "Үхэр", "Бар", "Туулай", "Луу", "Могой", "Морь", "Хонь", "Бич", "Тахиа", "Нохой", "Гахай"],
        "animals_year": ["хулгана", "үхэр", "бар", "туулай", "луу", "могой", "морин", "хонин", "бичин", "тахиа", "нохой", "гахай"],
        "animals_month": ["хулгана", "үхэр", "барс", "туулай", "луу", "могой", "морь", "хонь", "бич", "тахиа", "нохой", "гахай"],
        "mewa_colors": ["цагаан", "хар", "хөх", "ногоон", "шар", "цагаан", "улаан", "цагаан", "улаан"],
        "trigrams": ["Гал", "Шороо", "Төмөр", "Огторгуй", "Ус", "Уул", "Мод", "Хий"],
        "element_colors": [
            ["хөх", "хөхөгчин"],      # 0: Wood
            ["улаан", "улаагчин"],    # 1: Fire
            ["шар", "шарагчин"],      # 2: Earth
            ["цагаан", "цагаагчин"],  # 3: Iron
            ["хар", "харагчин"]       # 4: Water
        ],
    },
    "ru": { # Russian
        "tab_day": "День", "tab_month": "Месяц", "tab_year": "Год", "tab_losar": "Лосар",
        "alignment": "Год", "lunar_month": "Лунный месяц", "tithi": "Лунный день (Титхи)",
        "leap_suffix": " (Високосный)", "duplicated_day": "Дублирующийся день", "skipped_day": "Предыдущий день пропущен",
        "weekdays": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
        "greg_grid": "Григорианский", "tib_grid": "Тибетский",
        "greg_year": "Григорианский год", "tib_year": "Тибетский год",
        "month_prefix": "Месяц ", "year_prefix": "Год ",
        "day_title_fmt": "{day} {month} {year} г.",
        "weekday_lbl": "День недели",
        "month_grid_title_fmt": "Год {year}, {month_str}",
        "greg_months": ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"],
        "greg_months_genitive": ["", "января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"],
        "greg_month_long_fmt": "{month} {year} г.",
        "rabjung_fmt": "{R}-й цикл, год {Y}, {element} {animal}",
        "rabjung_year_fmt": "{R}-й цикл, год {Y}",
        "greg_date_lbl": "Григорианский",
        "weekdays_long": ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"],
        "day_card_greg_fmt": "{day} {month} {year} г.",
        "rabjung_title": "Рабджунг",
        "tib_year_title": "Тибетский год",
        "year_fmt": "{year} год",
        "tib_month_long_fmt": "Лунный месяц {month}, {element} {animal}",
        "tib_month_box_fmt": "Лунный месяц {month}, {element} {animal}",
        "tithi_title_fmt": "{element} {animal} • Лунный день",
        "losar": "Лосар",
        "tsagaan_sar": "Цагаан сар",
        "losar_date_fmt": "{day} {month}",
        "engines": {
            "phugpa": "Пхугпа",
            "tsurphu": "Цурпху",
            "mongol": "Монгольский",
            "bhutan": "Бутан",
            "karana": "Карана",
            "l0": "L0", "l1": "L1", "l2": "L2", "l3": "L3", "l4": "L4", "l5": "L5", "l6": "L6"
        },
        "attr_title": "Астрологические атрибуты",
        "attr_element": "Стихия", "attr_animal": "Животное", "attr_mewa": "Мэнгэ", "attr_trigram": "Триграмма",
        "elements": ["Дерево", "Огонь", "Земля", "Железо", "Вода"],
        "animals": ["Мышь", "Корова", "Тигр", "Кролик", "Дракон", "Змея", "Лошадь", "Овца", "Обезьяна", "Птица", "Собака", "Свинья"],
        "mewa_colors": ["белый", "черный", "синий", "зеленый", "желтый", "белый", "красный", "белый", "красный"],
        "trigrams": ["Ли", "Хон", "Два", "Хэн", "Хам", "Гин", "Зин", "Зон"],
        "elements_adj": ["деревянный", "огненный", "земляной", "железный", "водяной"],
        "element_colors": [
            ["синий", "синяя"], 
            ["красный", "красная"], 
            ["желтый", "желтая"], 
            ["белый", "белая"], 
            ["черный", "черная"]
        ],
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