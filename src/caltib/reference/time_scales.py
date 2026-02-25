from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import math
from typing import Optional, Tuple

# We use the reference ΔT model (seconds).
from .deltat import delta_t_seconds


# ============================================================
# Basic JD / JDN helpers
# ============================================================

def jd_to_jdn(jd: float) -> int:
    """
    Convert Julian Date (JD, days from noon) to Julian Day Number (JDN, integer day starting at midnight).

    Standard relation:
      JDN = floor(JD + 0.5)
    """
    return int(math.floor(jd + 0.5))


def jdn_to_jd(jdn: int) -> float:
    """
    Convert Julian Day Number (JDN) to the JD at midnight UTC of that day.
    Since JD starts at noon, midnight is JDN - 0.5.
    """
    return float(jdn) - 0.5


# ============================================================
# Gregorian calendar date <-> JDN  (Fliegel–Van Flandern)
# ============================================================

def date_to_jdn(d: date) -> int:
    """
    Gregorian date -> JDN (proleptic Gregorian).
    Time-zone/blind: purely civil date.
    """
    y = d.year
    m = d.month
    day = d.day

    a = (14 - m) // 12
    y2 = y + 4800 - a
    m2 = m + 12 * a - 3

    jdn = day + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - y2 // 100 + y2 // 400 - 32045
    return int(jdn)


def jdn_to_date(jdn: int) -> date:
    """
    JDN -> Gregorian date (proleptic Gregorian).
    """
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4

    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153

    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + (m // 10)

    return date(int(year), int(month), int(day))


# ============================================================
# datetime(UTC) <-> JD(UTC)
# ============================================================

_JD_UNIX_EPOCH = 2440587.5  # JD at 1970-01-01 00:00:00 UTC


def datetime_utc_to_jd(dt: datetime) -> float:
    """
    datetime -> JD (UTC). Requires timezone-aware UTC datetime.
    """
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware (UTC)")
    dt_utc = dt.astimezone(timezone.utc)
    t = dt_utc.timestamp()  # seconds since Unix epoch
    return _JD_UNIX_EPOCH + t / 86400.0


def jd_to_datetime_utc(jd: float) -> datetime:
    """
    JD (UTC) -> timezone-aware datetime in UTC.
    """
    t = (jd - _JD_UNIX_EPOCH) * 86400.0
    return datetime.fromtimestamp(t, tz=timezone.utc)


# ============================================================
# Decimal-year helper (for ΔT; simple and transparent)
# ============================================================

def decimal_year_from_date(d: date) -> float:
    """
    Convert a date to a decimal year, using day-of-year / year-length.
    """
    y = d.year
    start = date(y, 1, 1)
    end = date(y + 1, 1, 1)
    return y + (d - start).days / (end - start).days


# ============================================================
# TT <-> UTC conversions (via ΔT and optionally UT1-UTC)
# ============================================================

def jd_utc_to_jd_tt(jd_utc: float, *, ut1_utc_seconds: float = 0.0) -> float:
    """
    Convert JD(UTC) to JD(TT), using:
      TT = UT1 + ΔT
      UT1 = UTC + (UT1-UTC)

    We take UT1-UTC from caller (default 0). For high-precision work,
    supply it from IERS.

    ΔT is obtained from reference model delta_t_seconds(decimal_year).
    """
    dt_utc = jd_to_datetime_utc(jd_utc)
    y = decimal_year_from_date(dt_utc.date())
    dT = delta_t_seconds(y, method="best")  # seconds

    # UT1 = UTC + (UT1-UTC)
    # TT  = UT1 + ΔT
    return jd_utc + (ut1_utc_seconds + dT) / 86400.0


def jd_tt_to_jd_utc(jd_tt: float, *, ut1_utc_seconds: float = 0.0) -> float:
    """
    Approximate inverse of jd_utc_to_jd_tt.

    Solve:
      jd_tt = jd_utc + (ut1_utc + ΔT(y(jd_utc)))/86400

    We do 2 fixed-point iterations (enough for sub-second consistency
    given ΔT varies slowly).
    """
    jd_utc = jd_tt  # initial guess
    for _ in range(2):
        dt_utc = jd_to_datetime_utc(jd_utc)
        y = decimal_year_from_date(dt_utc.date())
        dT = delta_t_seconds(y, method="best")
        jd_utc = jd_tt - (ut1_utc_seconds + dT) / 86400.0
    return jd_utc


# ============================================================
# Local civil time / timezone helpers
# ============================================================

def local_to_utc(dt_local: datetime, tz_offset_hours: float) -> datetime:
    """
    Local civil time -> UTC, given a fixed timezone offset (hours).
    Example: tz_offset_hours = -5 for EST (standard time).
    """
    if dt_local.tzinfo is not None:
        # if tz-aware, respect it
        return dt_local.astimezone(timezone.utc)
    return (dt_local - timedelta(hours=tz_offset_hours)).replace(tzinfo=timezone.utc)


def utc_to_local(dt_utc: datetime, tz_offset_hours: float) -> datetime:
    """
    UTC -> local civil time, given a fixed timezone offset (hours).
    """
    if dt_utc.tzinfo is None:
        raise ValueError("dt_utc must be timezone-aware UTC")
    return (dt_utc.astimezone(timezone.utc) + timedelta(hours=tz_offset_hours)).replace(tzinfo=None)


# ============================================================
# Local Mean Time (LMT) <-> UTC (longitude-based)
# ============================================================

def lmt_offset_hours(longitude_deg_east: float) -> float:
    """
    Offset (hours) between UTC and Local Mean Time at given longitude.
    Positive east longitudes mean LMT ahead of UTC.
      360° -> 24h  =>  1° -> 4 minutes.
    """
    return longitude_deg_east / 15.0


def utc_to_lmt(dt_utc: datetime, longitude_deg_east: float) -> datetime:
    """
    UTC -> Local Mean Time at longitude (degrees east).
    """
    if dt_utc.tzinfo is None:
        raise ValueError("dt_utc must be timezone-aware UTC")
    return (dt_utc.astimezone(timezone.utc) + timedelta(hours=lmt_offset_hours(longitude_deg_east))).replace(tzinfo=None)


def lmt_to_utc(dt_lmt: datetime, longitude_deg_east: float) -> datetime:
    """
    Local Mean Time -> UTC at longitude (degrees east).
    """
    if dt_lmt.tzinfo is not None:
        # treat tz-aware input as local and convert to UTC
        return dt_lmt.astimezone(timezone.utc)
    return (dt_lmt - timedelta(hours=lmt_offset_hours(longitude_deg_east))).replace(tzinfo=timezone.utc)


# ============================================================
# Julian centuries from J2000.0 (TT)
# ============================================================

_JD_J2000_TT = 2451545.0  # J2000.0 epoch in TT


def T_from_jd_tt(jd_tt: float) -> float:
    """
    T = (JD_TT - 2451545.0) / 36525
    Julian centuries from J2000.0 in TT.
    """
    return (jd_tt - _JD_J2000_TT) / 36525.0


def jd_tt_from_T(T: float) -> float:
    """
    JD_TT = 2451545.0 + 36525*T
    """
    return _JD_J2000_TT + 36525.0 * T