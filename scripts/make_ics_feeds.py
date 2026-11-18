#!/usr/bin/env python3
"""
Generate subscribable iCalendar (.ics) feeds of the main lunar days and
festivals of the traditional calendars computed by caltib.

Each feed is a static file; calendar apps (Apple, Google, Outlook, ...)
subscribe to its URL and re-download it periodically.  No server logic is
needed, so the files can be hosted on any static site (e.g. GitHub Pages).

Usage
-----
    python scripts/make_ics_feeds.py OUTDIR [--start 2020] [--end 2050]

Conventions (one event per civil day unless stated):

* Month start: the first civil day of every lunar month gets an event titled
  with the lunar day and the short month name (e.g. "Шинийн 1 · Өвлийн
  тэргүүн сар"); the full month and year are in its description.  If lunar
  day 1 is omitted, the event goes on lunar day 2 and its description says
  so.  If lunar day 1 is repeated, the second occurrence gets a small
  "repeated" event.  Festival descriptions start with the lunar day alone
  (e.g. "Шинийн 1"), then the full month and year.
* Lunar day 15 (feeds without the ``-no15`` suffix): every civil day labelled
  15 gets an event, the second of a repeated pair being marked "repeated".
  If day 15 is omitted, the event goes on lunar day 14 and its description
  says so ("шинийн 15 тасарсан"); the title is just lunar day 14.
* Festivals on a fixed lunar day follow the same rule as day 15: both days if
  the lunar day is repeated, the preceding lunar day if it is omitted.
  Festivals on the first day of a month go on the first civil day of that
  month.  Festivals are placed in the regular (non-leap) month.
* The Mongol "auspicious days" feed (mongol-auspicious-*.ics) marks
  Baljinnyam, Dashnyam, Modon khokhimoi and Tersüüd by the table in
  caltib-private development/auspicious-days.md (see almanac_events; leap
  months carry none, as in L. Terbish's almanac).  It is meant as an add-on to the Mongol calendar
  feed, so it holds no festivals: subscribing to both shows nothing twice.
* The Mongol feeds also mark the winter Nine Nines (Есийн ес): the first
  day of each nine, counted from 22 December, with its folk saying
  (caltib-private development/nine-nines.md).  Nines 1-8 are yearly
  repeating events (RRULE), since their Gregorian dates never change; on a
  day that already has an event the nine goes into that event's description
  (and the repeating event skips that year via EXDATE).
* A festival day has a single event: a lunar-day event on the same day is
  folded into the festival's description.
* Mongol feeds: Tsagaan Sar, Ikh Düichen and Mongolian Pride Day (Chinggis
  Khaan's birthday) end their description with "Бүх нийтээр амрах баярын
  өдөр" (public holiday); so do the other days off of Tsagaan Sar by law,
  every later day of the first month labelled lunar day 1 (repeated), 2 or 3,
  titled by its lunar day (so if day 1 is omitted, day 2 is Tsagaan Sar and
  the next day is "Шинийн 3").  Bituun is not a public holiday.
* The Mongol feeds also mark Mongolia's public holidays on fixed Gregorian
  dates (days off by law: New Year, 8 March, 1 June, Naadam 10-15 July, 26
  November, 29 December; see PUBLIC_HOLIDAYS) as yearly repeating events.
  On a festival day the holiday joins the festival's title ("festival ·
  holiday"); on a lunar-day event's day it keeps its title and takes the
  lunar day, month and year as its description (a dated event for that
  year, skipped by the repeating one).
* All events are all-day, "free" (they do not block busy time) and have
  stable UIDs, so a regenerated file updates events in place.
"""
from __future__ import annotations

import argparse
import sys
import warnings
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import caltib  # noqa: E402
from caltib.i18n import TRANSLATIONS, localize_num  # noqa: E402

SITE_URL = "https://gantemur.github.io/cal/"
UID_DOMAIN = "gantemur.github.io"
DTSTAMP = "20261111T000000Z"  # fixed, so that regenerated files are deterministic

# ---------------------------------------------------------------------------
# Phrases that are not (yet) in caltib.i18n.  Mongolian and Tibetan wording
# should be reviewed by a native speaker before publication.
# ---------------------------------------------------------------------------
PHRASES: Dict[str, Dict[str, str]] = {
    "en": {
        "day": "Lunar day {d}",
        "repeated": "repeated",
        "omitted": "lunar day {d} omitted",
        "month_plain": "Lunar Month {m}{leap}",
        "month_mongol": "{season}{leap}, {elem} {anim} month",
        "month_tib": "Lunar Month {m}{leap}, {elem} {anim}",
        "year": "Rabjung {R}, Year {Y}, {elem} {anim}",
        "year_mongol": TRANSLATIONS["en"]["mongol_cycle_year_fmt"] + ", {elem} {anim}",
        "note": "Computed with caltib ({engine} tradition).",
    },
    "mn": {
        "day": "Шинийн {d}",
        "repeated": "давхар",
        "omitted": "шинийн {d} тасарсан",
        "month_mongol": "{season}{leap} {elem} {anim} сар",
        "year": "{R}-р жарны {Y} он {elem} {anim} жил",
        "note": "caltib-ээр тооцоолов ({engine} зурхай).",
    },
    "bo": {
        "day": "ཚེས་{d}",
        "repeated": "ཞག་ལྷག",
        "omitted": "ཚེས་{d} ཆད།",
        "month_tib": "ཟླ་བ་{m}{leap}, {elem}{anim}",
        "year": "རབ་བྱུང་{R}པའི་ལོ་{Y}, {elem}{anim}་ལོ།",
        "note": "caltib ({engine})",
    },
}
PHRASES["dz"] = dict(PHRASES["bo"])

# English season months of the Mongol calendar, from caltib.i18n ("mn_seasons").
EN_SEASONS = {m: f"{name} month" for m, name in TRANSLATIONS["en"]["mn_seasons"].items()}

# Festival names.  key -> lang -> name
FESTIVAL_NAMES: Dict[str, Dict[str, str]] = {
    "tsagaan_sar": {"en": "Tsagaan Sar (Lunar New Year)", "mn": "Цагаан сар"},
    "bituun": {"en": "Bituun (Lunar New Year's Eve)", "mn": "Битүүн"},
    "ikh_duichen": {"en": "Ikh Düichen", "mn": "Их дүйчин өдөр"},
    "chinggis": {"en": "Mongolian Pride Day", "mn": "Монгол бахархлын өдөр"},
    "losar": {"en": "Losar (Tibetan New Year)", "bo": "ལོ་གསར།", "dz": "ལོ་གསར།"},
    "chotrul": {"en": "Chotrul Düchen (Day of Miracles)", "bo": "ཆོ་འཕྲུལ་དུས་ཆེན།"},
    "saga_dawa": {
        "en": "Saga Dawa Düchen: Buddha's birth, enlightenment and parinirvana",
        "bo": "ས་ག་ཟླ་བའི་དུས་ཆེན།",
    },
    "chokhor": {"en": "Chökhor Düchen (First Turning of the Wheel)", "bo": "ཆོས་འཁོར་དུས་ཆེན།"},
    "lhabab": {"en": "Lhabab Düchen (Descent from the god realm)", "bo": "ལྷ་བབས་དུས་ཆེན།"},
}
for _k in ("chotrul", "saga_dawa", "chokhor", "lhabab"):
    FESTIVAL_NAMES[_k]["dz"] = FESTIVAL_NAMES[_k]["bo"]

# (month, lunar day, key); lunar day 1 means "first civil day of the month".
TIBETAN_FESTIVALS = [(1, 15, "chotrul"), (4, 15, "saga_dawa"), (6, 4, "chokhor"), (9, 22, "lhabab")]
MONGOL_FESTIVALS = [(4, 15, "ikh_duichen"), (10, 1, "chinggis")]

# Mongolian public holidays on fixed Gregorian dates (days off; Law on public
# holidays and observances, art. 4.1).  Mongol feeds only.  The lunar-dated
# days off (Tsagaan Sar, Ikh Düichen, Chinggis Khaan's Day) are festivals above.
# (key, month, day, first year it applies)
PUBLIC_HOLIDAYS = [
    ("new_year", 1, 1, 0),
    ("womens_day", 3, 8, 0),
    ("childrens_day", 6, 1, 0),
    ("naadam", 7, 10, 2022),  # 10 July added by the 2022 amendment
    ("naadam", 7, 11, 0), ("naadam", 7, 12, 0), ("naadam", 7, 13, 0),
    ("naadam", 7, 14, 0), ("naadam", 7, 15, 0),
    ("republic_day", 11, 26, 2016),
    ("independence_day", 12, 29, 2011),
]
HOLIDAY_NAMES: Dict[str, Dict[str, str]] = {
    "new_year": {"mn": "Шинэ жил", "en": "New Year's Day"},
    "womens_day": {"mn": "Эмэгтэйчүүдийн баяр", "en": "International Women's Day"},
    "childrens_day": {"mn": "Хүүхдийн баяр", "en": "Children's Day"},
    "naadam": {"mn": "Үндэсний их баяр наадам", "en": "Naadam (National Festival)"},
    "republic_day": {"mn": "Улс тунхагласан өдөр", "en": "Republic Day"},
    "independence_day": {"mn": "Тусгаар тогтнолын өдөр", "en": "Independence Day"},
}
# Official name in the description where the title is a shortened form.
HOLIDAY_OFFICIAL: Dict[str, Dict[str, str]] = {
    "womens_day": {"mn": "Олон улсын эмэгтэйчүүдийн өдөр", "en": ""},
    "republic_day": {"mn": "Бүгд Найрамдах Улс тунхагласан өдөр", "en": ""},
    "independence_day": {"mn": "Үндэсний эрх чөлөө, тусгаар тогтнолоо сэргээсний баярын өдөр",
                         "en": "National Freedom and Independence Day"},
}
HOLIDAY_NOTE = {"mn": "Бүх нийтээр амрах баярын өдөр", "en": "Public holiday in Mongolia"}
# Extra description line of a festival (before the public-holiday line).
FESTIVAL_NOTES: Dict[str, Dict[str, str]] = {
    "ikh_duichen": {"en": "Buddha's birth, enlightenment and parinirvana"},
    "chinggis": {"mn": "Их Эзэн Чингис хааны төрсөн өдөр", "en": "Birthday of Chinggis Khaan"},
}
# Lunar festivals that are public holidays in Mongolia (Mongol feeds): their
# description ends with HOLIDAY_NOTE.  Tsagaan Sar also makes lunar days 2
# and 3 (each occurrence) of the first month public holidays.
LUNAR_PUBLIC_HOLIDAYS = {"tsagaan_sar", "ikh_duichen", "chinggis"}

TRADITIONS = {
    # engine: (languages, fixed-lunar-day festivals, new-year key, eve key)
    "mongol": (("en", "mn"), MONGOL_FESTIVALS, "tsagaan_sar", "bituun"),
    "phugpa": (("en", "bo"), TIBETAN_FESTIVALS, "losar", None),
    "tsurphu": (("en", "bo"), TIBETAN_FESTIVALS, "losar", None),
    "bhutan": (("en", "dz"), TIBETAN_FESTIVALS, "losar", None),
}

CAL_TITLES = {
    "mongol": {"en": "Mongol lunar calendar", "mn": "Монгол билгийн тоолол"},
    "phugpa": {"en": "Tibetan calendar (Phugpa)", "bo": "བོད་ཀྱི་ལོ་ཐོ། (ཕུག་ལུགས།)"},
    "tsurphu": {"en": "Tibetan calendar (Tsurphu)", "bo": "བོད་ཀྱི་ལོ་ཐོ། (མཚུར་ལུགས།)"},
    "bhutan": {"en": "Bhutanese calendar", "dz": "འབྲུག་གི་ལོ་ཐོ།"},
}


# ---------------------------------------------------------------------------
# Localized names
# ---------------------------------------------------------------------------
def _tr(lang: str, key: str):
    return TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS["en"].get(key))


def _num(n: int, lang: str) -> str:
    return localize_num(n, lang) if lang in ("bo", "dz") else str(n)


def _strip_shad(s: str) -> str:
    return s.rstrip("།").rstrip("་")


def _elem_anim(attrs: dict, lang: str, engine: str, kind: str) -> Tuple[str, str]:
    """Element and animal for a year ('year') or month ('month')."""
    e_idx, a_idx = attrs.get("element", 0), attrs.get("animal", 0)
    if engine == "mongol":
        elem = _tr(lang, "element_colors")[e_idx][a_idx % 2]
    else:
        elem = _tr(lang, "elements_adj")[e_idx]
    anim = _tr(lang, "animals")[a_idx]
    if lang == "mn":
        anim = (_tr(lang, "animals_year") if kind == "year" else _tr(lang, "animals_month"))[a_idx]
        elem = elem.lower()
    if lang in ("bo", "dz"):
        elem = elem.rstrip("།")
        anim = _strip_shad(anim)
    return elem, anim


def month_short(engine: str, lang: str, m: int, leap: bool) -> str:
    """Short month name for event titles, e.g. 'Өвлийн тэргүүн сар', 'Lunar Month 10'."""
    leap_s = _tr(lang, "leap_suffix") if leap else ""
    if lang == "mn":
        return f"{_tr(lang, 'mn_seasons')[m]}{leap_s.lower()} сар"
    if engine == "mongol" and lang == "en":
        return f"{EN_SEASONS[m]}{leap_s}"
    if lang in ("bo", "dz"):
        return f"ཟླ་བ་{_num(m, lang)}{leap_s}"
    return f"Lunar Month {m}{leap_s}"


def month_name(engine: str, lang: str, m: int, leap: bool, attrs: dict) -> str:
    P = PHRASES[lang]
    leap_s = _tr(lang, "leap_suffix") if leap else ""
    if lang == "mn":
        leap_s = leap_s.lower()
    elem, anim = _elem_anim(attrs, lang, engine, "month")
    if engine == "mongol":
        season = _tr(lang, "mn_seasons")[m] if lang == "mn" else EN_SEASONS[m]
        return P["month_mongol"].format(season=season, leap=leap_s, elem=elem, anim=anim)
    return P["month_tib"].format(m=_num(m, lang), leap=leap_s, elem=elem, anim=anim)


def year_name(engine: str, lang: str, y_tib, attrs: dict) -> str:
    elem, anim = _elem_anim(attrs, lang, engine, "year")
    fmt = PHRASES[lang].get("year_mongol" if engine == "mongol" else "year", PHRASES[lang]["year"])
    s = fmt.format(
        R=_num(y_tib.rabjung_cycle, lang), Y=_num(y_tib.rabjung_year, lang), elem=elem, anim=anim
    )
    return s[0].upper() + s[1:]


def day_label(lang: str, d: int) -> str:
    return PHRASES[lang]["day"].format(d=_num(d, lang))


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------
@dataclass
class Event:
    day: date
    uid: str
    summary: str
    description: str = ""
    categories: Tuple[str, ...] = field(default_factory=tuple)
    rrule: str = ""  # RFC 5545 RRULE value for a repeating event, e.g. "FREQ=YEARLY;UNTIL=20501231"
    exdates: Tuple[date, ...] = ()  # occurrences of a repeating event to skip


@dataclass
class Month:
    year: int
    month: int
    leap: bool
    days: list
    attrs: dict
    year_tib: object
    year_attrs: dict


def collect_months(engine: str, start: date, end: date) -> List[Month]:
    eng = caltib.get_calendar(engine)
    out: List[Month] = []
    seen = set()
    for Y in range(start.year - 1, end.year + 1):
        yi = eng.year_info(Y)
        for mi in yi.months:
            t = mi.tibetan
            key = (t.year, t.month, t.is_leap_month)
            if key in seen or not mi.days:
                continue
            seen.add(key)
            if mi.days[-1].civil_date < start or mi.days[0].civil_date > end:
                continue
            out.append(Month(t.year, t.month, t.is_leap_month, mi.days, mi.attributes or {},
                             yi.tibetan, yi.attributes or {}))
    out.sort(key=lambda mo: mo.days[0].civil_date)
    return out


def _uid(feed: str, mo: Month, tag: str) -> str:
    leap = "L" if mo.leap else ""
    return f"{feed}-{mo.year}-{mo.month:02d}{leap}-{tag}@{UID_DOMAIN}"


def days_for_tithi(mo: Month, tithi: int):
    """[(DayInfo, kind)] for a fixed lunar day: kind in {'normal','repeated','omitted'}."""
    hits = [d for d in mo.days if d.tibetan.tithi == tithi]
    if hits:
        return [(d, "repeated" if d.tibetan.occ == 2 else "normal") for d in hits]
    prev = [d for d in mo.days if d.tibetan.tithi == tithi - 1]
    if prev:
        return [(prev[-1], "omitted")]
    return []


def month_events(engine: str, lang: str, feed: str, mo: Month, with15: bool) -> List[Event]:
    P = PHRASES[lang]
    ev: List[Event] = []
    mname = month_name(engine, lang, mo.month, mo.leap, mo.attrs)
    yname = year_name(engine, lang, mo.year_tib, mo.year_attrs)
    short = month_short(engine, lang, mo.month, mo.leap)
    desc = f"{mname}\n{yname}"

    # --- month start: title leads with the lunar day, then the short month name;
    # the full month (element, animal) and year are in the description ---
    first = mo.days[0]
    t0 = first.tibetan.tithi
    head = f"{day_label(lang, t0)} · {short}"
    d0 = desc if t0 == 1 else f"{P['omitted'].format(d=_num(1, lang))}\n{desc}"
    ev.append(Event(first.civil_date, _uid(feed, mo, "d01"), head, d0))
    rep1 = [d for d in mo.days if d.tibetan.tithi == 1 and d.tibetan.occ == 2]
    for d in rep1:
        ev.append(Event(d.civil_date, _uid(feed, mo, "d01r"),
                        f"{day_label(lang, 1)} ({P['repeated']}) · {short}", desc))

    # --- lunar day 15 ---
    if with15:
        for d, kind in days_for_tithi(mo, 15):
            if kind == "normal":
                s, tag = day_label(lang, 15), "d15"
            elif kind == "repeated":
                s, tag = f"{day_label(lang, 15)} ({P['repeated']})", "d15r"
            else:
                s, tag = day_label(lang, 14), "d15o"
            dsc = f"{P['omitted'].format(d=_num(15, lang))}\n{desc}" if kind == "omitted" else desc
            ev.append(Event(d.civil_date, _uid(feed, mo, tag), f"{s} · {short}", dsc))
    return ev


def festival_events(engine: str, lang: str, feed: str, months: List[Month],
                    festivals, ny_key: Optional[str], eve_key: Optional[str]) -> List[Event]:
    P = PHRASES[lang]
    ev: List[Event] = []
    day_month = {d.civil_date: (d, m) for m in months for d in m.days}

    def full_desc(day: date) -> str:
        if day not in day_month:
            return ""
        d, m = day_month[day]
        rep_s = f" ({P['repeated']})" if d.tibetan.occ == 2 else ""
        return (f"{day_label(lang, d.tibetan.tithi)}{rep_s}\n"
                f"{month_name(engine, lang, m.month, m.leap, m.attrs)}\n"
                f"{year_name(engine, lang, m.year_tib, m.year_attrs)}")

    for mo in months:
        if mo.leap:
            continue
        mname = month_name(engine, lang, mo.month, mo.leap, mo.attrs)
        yname = year_name(engine, lang, mo.year_tib, mo.year_attrs)
        short = month_short(engine, lang, mo.month, mo.leap)

        def desc_for(d, key: str = "", omitted: str = "") -> str:
            rep_s = f" ({P['repeated']})" if d.tibetan.occ == 2 else ""
            lines = [f"{day_label(lang, d.tibetan.tithi)}{rep_s}"]
            if omitted:
                lines.append(omitted)
            lines += [mname, yname]
            if FESTIVAL_NOTES.get(key, {}).get(lang):
                lines.append(FESTIVAL_NOTES[key][lang])
            if engine == "mongol" and key in LUNAR_PUBLIC_HOLIDAYS:
                lines.append(HOLIDAY_NOTE[lang])
            return "\n".join(lines)

        for (m, tithi, key) in festivals:
            if m != mo.month:
                continue
            name = FESTIVAL_NAMES[key][lang]
            if tithi == 1:
                d = mo.days[0]
                om = P['omitted'].format(d=_num(1, lang)) if d.tibetan.tithi != 1 else ""
                ev.append(Event(d.civil_date, _uid(feed, mo, key), name, desc_for(d, key, om), ("festival",)))
                continue
            for d, kind in days_for_tithi(mo, tithi):
                s = f"{name} ({P['repeated']})" if kind == "repeated" else name
                om = P['omitted'].format(d=_num(tithi, lang)) if kind == "omitted" else ""
                ev.append(Event(d.civil_date, _uid(feed, mo, key + ("-r" if kind == "repeated" else "")), s,
                                desc_for(d, key, om), ("festival",)))
        # New year (first civil day of the regular first month; matches caltib.new_year_day)
        if mo.month == 1 and ny_key:
            d = mo.days[0]
            om = P['omitted'].format(d=_num(1, lang)) if d.tibetan.tithi != 1 else ""
            ev.append(Event(d.civil_date, _uid(feed, mo, ny_key), FESTIVAL_NAMES[ny_key][lang],
                            desc_for(d, ny_key, om), ("festival",)))
            if engine == "mongol":
                # Days off by law: lunar days 1, 2, 3 of the first month.  The
                # first civil day is Tsagaan Sar; every later day labelled 1
                # (repeated), 2 or 3 is titled by its lunar day.
                for x in mo.days[1:]:
                    t, occ = x.tibetan.tithi, x.tibetan.occ
                    if t > 3:
                        break
                    rep_s = f" ({P['repeated']})" if occ == 2 else ""
                    ev.append(Event(x.civil_date, _uid(feed, mo, f"ts{t}" + ("r" if occ == 2 else "")),
                                    f"{day_label(lang, t)}{rep_s}", desc_for(x, ny_key), ("festival",)))
            if eve_key:
                eve = d.civil_date - timedelta(days=1)
                ev.append(Event(eve, _uid(feed, mo, eve_key),
                                FESTIVAL_NAMES[eve_key][lang], full_desc(eve), ("festival",)))
    return ev


# ---------------------------------------------------------------------------
# Mongol almanac special days (caltib-private development/auspicious-days.md)
# ---------------------------------------------------------------------------
# lunar day of each special day by lunar month 1..12 (None: not in that month)
ALMANAC_TABLE = {
    "baljinnyam": [2, 8, 10, 3, 3, 29, 3, 17, 3, 16, 1, 9],
    "dashnyam": [6, 3, 1, 9, 4, 5, 18, 17, 3, 1, 27, 10],
    "modon_khokhimoi": [None, 2, 3, 4, 5, 6, 7, 8, 9, 19, 16, 29],
    "tersuud": [13, 11, 9, 7, 5, 3, 1, 19, 17, 25, 23, 21],
}
ALMANAC_NAMES = {
    "baljinnyam": {"en": "Baljinnyam", "mn": "Балжинням"},
    "dashnyam": {"en": "Dashnyam", "mn": "Дашням"},
    "modon_khokhimoi": {"en": "Modon khokhimoi", "mn": "Модон хохимой"},
    "tersuud": {"en": "Tersüüd", "mn": "Тэрсүүд"},
}
# Event descriptions: attribute the meaning to the almanac tradition.
ALMANAC_NOTES = {
    "good": {"en": "Regarded as an auspicious day in the traditional Mongolian almanac.",
             "mn": "Уламжлалт зурхайд сайн өдөрт тооцдог."},
    "careful": {"en": "Regarded as a day to be careful in the traditional Mongolian almanac.",
                "mn": "Уламжлалт зурхайд цээртэй өдөрт тооцдог."},
}
ALMANAC_KIND = {"baljinnyam": "good", "dashnyam": "good", "modon_khokhimoi": "careful", "tersuud": "careful"}


def almanac_events(lang: str, feed: str, months: List[Month]) -> List[Event]:
    """Special days of the Mongolian almanac: a skipped lunar day is marked on
    the civil day before it (for lunar day 1, the last day of the previous
    month); of a repeated lunar day only the second civil day is marked (as on
    gogo.mn); leap (intercalary) months carry no special days, as in
    L. Terbish's almanac (owner, 2026-11-12), so the regular month of a leap
    pair carries them."""
    by_day: Dict[date, Tuple[List[str], Month]] = {}
    for mo in months:
        if mo.leap:
            continue
        for key, row in ALMANAC_TABLE.items():
            d = row[mo.month - 1]
            if d is None:
                continue
            hits = [x for x in mo.days if x.tibetan.tithi == d]
            if hits:
                day = hits[-1].civil_date
            elif d == 1:
                day = mo.days[0].civil_date - timedelta(days=1)
            else:
                prev = [x for x in mo.days if x.tibetan.tithi == d - 1]
                if not prev:
                    continue
                day = prev[-1].civil_date
            by_day.setdefault(day, ([], mo))[0].append(key)
    ev = []
    for day, (keys, mo) in by_day.items():
        names = " · ".join(ALMANAC_NAMES[k][lang] for k in keys)
        mname = month_name("mongol", lang, mo.month, mo.leap, mo.attrs)
        leap = "L" if mo.leap else ""
        uid = f"{feed}-{mo.year}-{mo.month:02d}{leap}-{'-'.join(keys)}@{UID_DOMAIN}"
        notes = []
        for k in keys:
            n = ALMANAC_NOTES[ALMANAC_KIND[k]][lang]
            if n not in notes:
                notes.append(n)
        ev.append(Event(day, uid, names, "\n".join(notes + [mname])))
    return ev


def build_almanac_feed(lang: str, start: date, end: date, months: List[Month]) -> Tuple[str, str, int]:
    feed = f"mongol-auspicious-{lang}"
    events = [e for e in almanac_events(lang, feed, months) if start <= e.day <= end]
    title = {"en": "Mongol auspicious days", "mn": "Балжка Дашка"}[lang]
    desc = (f"Baljinnyam, Dashnyam, Modon khokhimoi and Tersüüd, {start.year}–{end.year}. "
            f"Add-on to the Mongol lunar calendar feed. {SITE_URL}")
    return feed, render_ics(title, desc, lang, events), len(events)


# ---------------------------------------------------------------------------
# iCalendar serialization (RFC 5545)
# ---------------------------------------------------------------------------
def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Fold a content line at 75 octets without splitting UTF-8 characters."""
    out, cur, n = [], "", 0
    for ch in line:
        b = len(ch.encode("utf-8"))
        limit = 75 if not out else 74
        if n + b > limit:
            out.append(cur)
            cur, n = "", 0
        cur += ch
        n += b
    out.append(cur)
    return "\r\n ".join(out)


def render_ics(name: str, desc: str, lang: str, events: Sequence[Event]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//caltib//lunar day feeds//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_esc(name)}",
        f"X-WR-CALDESC:{_esc(desc)}",
        f"NAME:{_esc(name)}",
        f"DESCRIPTION:{_esc(desc)}",
        f"URL:{SITE_URL}",
        "REFRESH-INTERVAL;VALUE=DURATION:P7D",
        "X-PUBLISHED-TTL:P7D",
    ]
    for e in sorted(events, key=lambda e: (e.day, e.uid)):
        lines += [
            "BEGIN:VEVENT",
            f"UID:{e.uid}",
            f"DTSTAMP:{DTSTAMP}",
            f"DTSTART;VALUE=DATE:{e.day:%Y%m%d}",
            f"DTEND;VALUE=DATE:{e.day + timedelta(days=1):%Y%m%d}",
        ]
        if e.rrule:
            lines.append(f"RRULE:{e.rrule}")
        if e.exdates:
            lines.append("EXDATE;VALUE=DATE:" + ",".join(f"{d:%Y%m%d}" for d in sorted(e.exdates)))
        lines += [
            f"SUMMARY:{_esc(e.summary)}",
        ]
        if e.description:
            lines.append(f"DESCRIPTION:{_esc(e.description)}")
        if e.categories:
            lines.append(f"CATEGORIES:{','.join(e.categories)}")
        lines += ["TRANSP:TRANSPARENT", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Winter Nine Nines (caltib-private development/nine-nines.md): the 81 days
# from 22 December (fixed Gregorian date), counted in nine nines of nine days.
# ---------------------------------------------------------------------------
NINE_NINES_TEXT = {
    "start": {"mn": "{n} ес эхэлнэ", "en": "{ord} nine begins"},
}
# Folk saying for each nine (owner's readings, 2026-11-13; sources in
# caltib-private development/nine-nines.md).  English: Claude's rendering.
NINE_NINES_SAYINGS = {
    "mn": [
        "Нэг есөд нэрмэл архи хөлдөнө",
        "Хоёр есөд хорз архи хөлдөнө",
        "Гурван есөд гунан үхрийн эвэр хуга хөлдөнө",
        "Дөрвөн есөд дөнөн үхрийн эвэр хуга хөлдөнө",
        "Таван есөд тавьсан будаа хөлдөхгүй",
        "Зургаан есөд зурайсан зам гарна",
        "Долоон есөд довны толгой бараална",
        "Найман есөд нял шал болно",
        "Есөн есөд ердийн дулаан болно",
    ],
    "en": [
        "Milk vodka freezes",
        "Double-distilled vodka freezes",
        "A three-year-old ox's horns freeze and crack",
        "A four-year-old ox's horns freeze and crack",
        "Porridge set out no longer freezes",
        "Paths start to show",
        "Hilltops turn bare",
        "It turns slushy",
        "Ordinary warmth returns",
    ],
}


def _ordinal_en(n: int) -> str:
    return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n, "th")


def nine_nines_starts(start: date, end: date) -> Dict[date, int]:
    """First day of each nine in [start, end] -> nine number (1-9)."""
    out: Dict[date, int] = {}
    for Y in range(start.year - 1, end.year + 1):
        for n in range(1, 10):
            d = date(Y, 12, 22) + timedelta(days=9 * (n - 1))
            if start <= d <= end:
                out[d] = n
    return out


def nine_nines_line(lang: str, n: int) -> str:
    """'7 ес эхэлнэ · Долоон есөд довны толгой бараална'."""
    return (NINE_NINES_TEXT["start"][lang].format(n=n, ord=_ordinal_en(n))
            + " · " + NINE_NINES_SAYINGS[lang][n - 1])


def add_nine_nines(lang: str, feed: str, events: List[Event], start: date, end: date) -> List[Event]:
    """Add the first day of each nine (Mongol feeds).

    On a day that already has an event (month start, day 15, a festival) the
    nine is folded into that event's description: its first line becomes
    e.g. 'Шинийн 1 · Хаврын тэргүүн сар · 7 ес эхэлнэ · Долоон есөд ...'.
    Otherwise the nine gets its own event titled 'N ес эхэлнэ', with the
    saying in the description.  Nines 1-8 start on the same Gregorian date
    every winter (12-22, 12-31, 01-09, 01-18, 01-27, 02-05, 02-14, 02-23), so
    each is one yearly repeating event, with the folded years as EXDATEs.
    The 9th nine (03-04, or 03-03 after a 29 February) is a dated event per
    winter."""
    starts = nine_nines_starts(start, end)
    by_day: Dict[date, List[Event]] = {}
    for e in events:
        by_day.setdefault(e.day, []).append(e)
    folded = set()
    for d, n in starts.items():
        if d not in by_day:
            continue
        e = sorted(by_day[d], key=lambda x: x.uid)[0]
        line = nine_nines_line(lang, n)
        lines = e.description.split("\n") if e.description else []
        if "festival" in e.categories and lines:
            lines[0] = f"{lines[0]} · {line}"  # first line is the lunar day
        else:
            lines.insert(0, f"{e.summary} · {line}")
        e.description = "\n".join(lines)
        folded.add(d)
    new: List[Event] = []
    for n in range(1, 10):
        title = NINE_NINES_TEXT["start"][lang].format(n=n, ord=_ordinal_en(n))
        ndesc = NINE_NINES_SAYINGS[lang][n - 1]
        days = sorted(d for d, k in starts.items() if k == n)
        if not days:
            continue
        if n <= 8:
            assert len({(d.month, d.day) for d in days}) == 1  # fixed Gregorian date
            new.append(Event(days[0], f"{feed}-nine{n}@{UID_DOMAIN}", title, ndesc, ("nine_nines",),
                             rrule=f"FREQ=YEARLY;UNTIL={end:%Y%m%d}",
                             exdates=tuple(d for d in days if d in folded)))
        else:
            for d in days:
                if d not in folded:
                    Y = d.year - 1  # the winter starts on 22 December of the previous year
                    new.append(Event(d, f"{feed}-{Y}-nine{n}@{UID_DOMAIN}", title, ndesc, ("nine_nines",)))
    return events + new


def holiday_events(lang: str, feed: str, start: date, end: date) -> List[Event]:
    """Dated public-holiday events (compressed later by compress_holidays)."""
    ev: List[Event] = []
    for (key, m, d, since) in PUBLIC_HOLIDAYS:
        for Y in range(max(start.year, since), end.year + 1):
            day = date(Y, m, d)
            if start <= day <= end:
                note = HOLIDAY_NOTE[lang]
                if HOLIDAY_OFFICIAL.get(key, {}).get(lang):
                    note = f"{HOLIDAY_OFFICIAL[key][lang]}\n{note}"
                ev.append(Event(day, f"{feed}-hol-{m:02d}{d:02d}@{UID_DOMAIN}", HOLIDAY_NAMES[key][lang],
                                note, ("holiday",)))
    return ev


def merge_holidays(lang: str, events: List[Event]) -> List[Event]:
    """One event per day: a public holiday on the same day as a festival is
    joined to it ('festival · holiday'); on a lunar-day event's day (month
    start, day 15) the holiday keeps its title and takes the lunar line,
    month and year as its description.  Such holidays become dated events."""
    by_day: Dict[date, List[Event]] = {}
    for e in events:
        by_day.setdefault(e.day, []).append(e)
    out: List[Event] = []
    for day, evs in sorted(by_day.items()):
        hol = [e for e in evs if "holiday" in e.categories]
        rest = [e for e in evs if "holiday" not in e.categories]
        if not hol or not rest:
            out += evs
            continue
        assert len(hol) == 1
        h = hol[0]
        fest = [e for e in rest if "festival" in e.categories]
        lunar = [e for e in rest if not e.categories]
        other = [e for e in rest if e.categories and "festival" not in e.categories]
        if not fest and not lunar:
            out += evs
            continue
        uid = h.uid.replace("@", f"-{day.year}@")
        if fest:
            f = fest[0]
            lines = f.description.split("\n")
            lines += [x for x in h.description.split("\n") if x not in lines]
            out.append(Event(day, f.uid, f"{f.summary} · {h.summary}", "\n".join(lines), ("festival", "holiday")))
            out += fest[1:] + lunar + other
        else:
            first = " / ".join(e.summary.split(" · ")[0] for e in lunar)
            desc = lunar[0].description
            out.append(Event(day, uid, h.summary, f"{first}\n{desc}\n{h.description}",
                             ("festival", "holiday")))
            out += other
    return out


def compress_holidays(events: List[Event], end: date) -> List[Event]:
    """Turn the remaining (unmerged) dated holiday events into one yearly
    repeating event per date, skipping (EXDATE) the years where the holiday
    was merged into another event."""
    groups: Dict[str, List[Event]] = {}
    out: List[Event] = []
    for e in events:
        if e.categories == ("holiday",):
            groups.setdefault(e.uid, []).append(e)
        else:
            out.append(e)
    for uid, evs in groups.items():
        evs.sort(key=lambda e: e.day)
        first, years = evs[0], {e.day.year for e in evs}
        skip = tuple(date(Y, first.day.month, first.day.day)
                     for Y in range(first.day.year, end.year + 1) if Y not in years)
        out.append(Event(first.day, uid, first.summary, first.description, ("holiday",),
                         rrule=f"FREQ=YEARLY;UNTIL={end:%Y%m%d}", exdates=skip))
    return out


def merge_festival_days(events: List[Event]) -> List[Event]:
    """One event per festival day: a lunar-day event (month start, day 15) on
    the same day as a festival is dropped; the festival's description already
    starts with the lunar day (and says if it is repeated or omitted)."""
    by_day: Dict[date, List[Event]] = {}
    for e in events:
        by_day.setdefault(e.day, []).append(e)
    out: List[Event] = []
    for day, evs in by_day.items():
        fest = [e for e in evs if "festival" in e.categories]
        lunar = [e for e in evs if not e.categories]  # month start, day 15
        other = [e for e in evs if e.categories and "festival" not in e.categories]
        if fest and lunar:
            out += fest + other
        else:
            out += evs
    return out


def build_feed(engine: str, lang: str, with15: bool, start: date, end: date,
               months: Optional[List[Month]] = None) -> Tuple[str, str, int]:
    langs, festivals, ny, eve = TRADITIONS[engine]
    feed = f"{engine}-{lang}" + ("" if with15 else "-no15")
    months = months if months is not None else collect_months(engine, start, end)
    events: List[Event] = []
    for mo in months:
        events += month_events(engine, lang, feed, mo, with15)
    events += festival_events(engine, lang, feed, months, festivals, ny, eve)
    events = merge_festival_days([e for e in events if start <= e.day <= end])
    if engine == "mongol":
        events = merge_holidays(lang, events + holiday_events(lang, feed, start, end))
        events = compress_holidays(events, end)
        events = add_nine_nines(lang, feed, events, start, end)
    title = CAL_TITLES[engine][lang]
    if lang == "en":
        desc = ("Lunar day 1" + (" and 15" if with15 else "") + " of each month and main festivals"
                + (", Mongolian public holidays and the winter Nine Nines" if engine == "mongol" else "")
                + f", {start.year}–{end.year}. {SITE_URL}")
    else:
        desc = f"{start.year}–{end.year}. {SITE_URL}"
    return feed, render_ics(title, desc, lang, events), len(events)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--start", type=int, default=2020)
    ap.add_argument("--end", type=int, default=2050)
    ap.add_argument("--engines", nargs="*", default=list(TRADITIONS))
    args = ap.parse_args(argv)
    start, end = date(args.start, 1, 1), date(args.end, 12, 31)
    args.outdir.mkdir(parents=True, exist_ok=True)
    for engine in args.engines:
        months = collect_months(engine, start, end)
        for lang in TRADITIONS[engine][0]:
            for with15 in (True, False):
                feed, text, n = build_feed(engine, lang, with15, start, end, months)
                (args.outdir / f"{feed}.ics").write_bytes(text.encode("utf-8"))
                print(f"{feed}.ics: {n} events, {len(text.encode('utf-8')) // 1024} KiB")
        if engine == "mongol":
            for lang in ("en", "mn"):
                feed, text, n = build_almanac_feed(lang, start, end, months)
                (args.outdir / f"{feed}.ics").write_bytes(text.encode("utf-8"))
                print(f"{feed}.ics: {n} events, {len(text.encode('utf-8')) // 1024} KiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
