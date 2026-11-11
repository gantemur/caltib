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

* Month start: the first civil day of every lunar month carries the full
  month and year.  If lunar day 1 is omitted, the event goes on lunar day 2
  and says that it is the first day of the month.  If lunar day 1 is
  repeated, the second occurrence gets a small "repeated" event.
* Lunar day 15 (feeds without the ``-no15`` suffix): every civil day labelled
  15 gets an event, the second of a repeated pair being marked "repeated".
  If day 15 is omitted, the event goes on lunar day 14 and says so.
* Festivals on a fixed lunar day follow the same rule as day 15: both days if
  the lunar day is repeated, the preceding lunar day if it is omitted.
  Festivals on the first day of a month go on the first civil day of that
  month.  Festivals are placed in the regular (non-leap) month.
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
        "first_day_of": "first day of {month}",
        "repeated": "repeated",
        "omitted": "lunar day {d} omitted",
        "month_plain": "Lunar Month {m}{leap}",
        "month_mongol": "{season}{leap}, {elem} {anim} month",
        "month_tib": "Lunar Month {m}{leap}, {elem} {anim}",
        "year": "Rabjung {R}, Year {Y}, {elem} {anim}",
        "note": "Computed with caltib ({engine} tradition).",
    },
    "mn": {
        "day": "Шинийн {d}",
        "first_day_of": "{month}",
        "repeated": "давхар",
        "omitted": "шинийн {d} тасарсан",
        "month_mongol": "{season}{leap} {elem} {anim} сар",
        "year": "{R}-р жарны {Y} он {elem} {anim} жил",
        "note": "caltib-ээр тооцоолов ({engine} зурхай).",
    },
    "bo": {
        "day": "ཚེས་{d}",
        "first_day_of": "{month}",
        "repeated": "ཞག་ལྷག",
        "omitted": "ཚེས་{d} ཆད།",
        "month_tib": "ཟླ་བ་{m}{leap}, {elem}{anim}",
        "year": "རབ་བྱུང་{R}པའི་ལོ་{Y}, {elem}{anim}་ལོ།",
        "note": "caltib ({engine})",
    },
}
PHRASES["dz"] = dict(PHRASES["bo"])

EN_SEASONS = {
    1: "First spring month", 2: "Middle spring month", 3: "Last spring month",
    4: "First summer month", 5: "Middle summer month", 6: "Last summer month",
    7: "First autumn month", 8: "Middle autumn month", 9: "Last autumn month",
    10: "First winter month", 11: "Middle winter month", 12: "Last winter month",
}

# Festival names.  key -> lang -> name
FESTIVAL_NAMES: Dict[str, Dict[str, str]] = {
    "tsagaan_sar": {"en": "Tsagaan Sar (Lunar New Year)", "mn": "Цагаан сар"},
    "bituun": {"en": "Bituun (Lunar New Year's Eve)", "mn": "Битүүн"},
    "ikh_duichen": {
        "en": "Ikh Düichen: Buddha's birth, enlightenment and parinirvana",
        "mn": "Бурхан багшийн Их дүйчин өдөр",
    },
    "chinggis": {
        "en": "Chinggis Khaan's birthday (Mongolian Pride Day)",
        "mn": "Их Эзэн Чингис хааны төрсөн өдөр (Монгол бахархлын өдөр)",
    },
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


def month_name(engine: str, lang: str, m: int, leap: bool, attrs: dict) -> str:
    P = PHRASES[lang]
    leap_s = _tr(lang, "leap_suffix") if leap else ""
    elem, anim = _elem_anim(attrs, lang, engine, "month")
    if engine == "mongol":
        season = _tr(lang, "mn_seasons")[m] if lang == "mn" else EN_SEASONS[m]
        return P["month_mongol"].format(season=season, leap=leap_s, elem=elem, anim=anim)
    return P["month_tib"].format(m=_num(m, lang), leap=leap_s, elem=elem, anim=anim)


def year_name(engine: str, lang: str, y_tib, attrs: dict) -> str:
    elem, anim = _elem_anim(attrs, lang, engine, "year")
    s = PHRASES[lang]["year"].format(
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

    # --- month start ---
    first = mo.days[0]
    t0 = first.tibetan.tithi
    if t0 == 1:
        head = f"{day_label(lang, 1)} · {mname}"
    else:
        head = f"{day_label(lang, t0)} · {P['first_day_of'].format(month=mname)} ({P['omitted'].format(d=_num(1, lang))})"
    ev.append(Event(first.civil_date, _uid(feed, mo, "d01"), f"{head} · {yname}",
                    f"{mname}\n{yname}"))
    rep1 = [d for d in mo.days if d.tibetan.tithi == 1 and d.tibetan.occ == 2]
    for d in rep1:
        ev.append(Event(d.civil_date, _uid(feed, mo, "d01r"),
                        f"{day_label(lang, 1)} ({P['repeated']})", f"{mname}\n{yname}"))

    # --- lunar day 15 ---
    if with15:
        for d, kind in days_for_tithi(mo, 15):
            if kind == "normal":
                s, tag = day_label(lang, 15), "d15"
            elif kind == "repeated":
                s, tag = f"{day_label(lang, 15)} ({P['repeated']})", "d15r"
            else:
                s, tag = f"{day_label(lang, 14)} ({P['omitted'].format(d=_num(15, lang))})", "d15o"
            ev.append(Event(d.civil_date, _uid(feed, mo, tag), s, f"{mname}\n{yname}"))
    return ev


def festival_events(engine: str, lang: str, feed: str, months: List[Month],
                    festivals, ny_key: Optional[str], eve_key: Optional[str]) -> List[Event]:
    P = PHRASES[lang]
    ev: List[Event] = []
    for mo in months:
        if mo.leap:
            continue
        mname = month_name(engine, lang, mo.month, mo.leap, mo.attrs)
        yname = year_name(engine, lang, mo.year_tib, mo.year_attrs)
        desc = f"{mname}\n{yname}"
        for (m, tithi, key) in festivals:
            if m != mo.month:
                continue
            name = FESTIVAL_NAMES[key][lang]
            if tithi == 1:
                d = mo.days[0]
                ev.append(Event(d.civil_date, _uid(feed, mo, key), name,
                                f"{day_label(lang, d.tibetan.tithi)}\n{desc}", ("festival",)))
                continue
            for d, kind in days_for_tithi(mo, tithi):
                if kind == "normal":
                    s = name
                elif kind == "repeated":
                    s = f"{name} ({P['repeated']})"
                else:
                    s = f"{name} ({P['omitted'].format(d=_num(tithi, lang))})"
                ev.append(Event(d.civil_date, _uid(feed, mo, key + ("-r" if kind == "repeated" else "")), s,
                                f"{day_label(lang, d.tibetan.tithi)}\n{desc}", ("festival",)))
        # New year (first civil day of the regular first month; matches caltib.new_year_day)
        if mo.month == 1 and ny_key:
            d = mo.days[0]
            ev.append(Event(d.civil_date, _uid(feed, mo, ny_key), FESTIVAL_NAMES[ny_key][lang],
                            f"{yname}", ("festival",)))
            if eve_key:
                ev.append(Event(d.civil_date - timedelta(days=1), _uid(feed, mo, eve_key),
                                FESTIVAL_NAMES[eve_key][lang], "", ("festival",)))
    return ev


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
def build_feed(engine: str, lang: str, with15: bool, start: date, end: date,
               months: Optional[List[Month]] = None) -> Tuple[str, str, int]:
    langs, festivals, ny, eve = TRADITIONS[engine]
    feed = f"{engine}-{lang}" + ("" if with15 else "-no15")
    months = months if months is not None else collect_months(engine, start, end)
    events: List[Event] = []
    for mo in months:
        events += month_events(engine, lang, feed, mo, with15)
    events += festival_events(engine, lang, feed, months, festivals, ny, eve)
    events = [e for e in events if start <= e.day <= end]
    title = CAL_TITLES[engine][lang]
    if lang == "en":
        desc = ("Lunar day 1" + (" and 15" if with15 else "") +
                f" of each month and main festivals, {start.year}–{end.year}. {SITE_URL}")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
