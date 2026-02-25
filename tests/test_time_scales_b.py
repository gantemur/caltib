#!/usr/bin/env python3
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta

from caltib.reference.time_scales import (
    date_to_jdn,
    jdn_to_date,
    jd_to_jdn,
    jdn_to_jd,
    datetime_utc_to_jd,
    jd_to_datetime_utc,
    jd_utc_to_jd_tt,
    jd_tt_to_jd_utc,
    T_from_jd_tt,
    jd_tt_from_T,
    utc_to_lmt,
    lmt_to_utc,
    utc_to_local,
    local_to_utc,
)


def assert_eq(a, b, msg=""):
    if a != b:
        raise AssertionError(f"{msg}  got {a!r} expected {b!r}")


def assert_close(a: float, b: float, tol: float, msg=""):
    if abs(a - b) > tol:
        raise AssertionError(f"{msg}  got {a:.12f} expected {b:.12f} (tol={tol})")


def test_date_jdn_roundtrip():
    samples = [
        date(1, 1, 1),
        date(1582, 10, 15),   # Gregorian reform date (proleptic here)
        date(1900, 1, 1),
        date(1970, 1, 1),
        date(2000, 1, 1),
        date(2026, 2, 24),
        date(2400, 12, 31),
    ]
    for d in samples:
        j = date_to_jdn(d)
        d2 = jdn_to_date(j)
        assert_eq(d2, d, f"date<->jdn roundtrip failed for {d}")


def test_jd_jdn_relation():
    # JDN corresponds to midnight, and JD at midnight is JDN-0.5
    d = date(2026, 2, 24)
    jdn = date_to_jdn(d)
    jd0 = jdn_to_jd(jdn)
    assert_eq(jd_to_jdn(jd0), jdn, "jd_to_jdn(jdn_to_jd(jdn)) mismatch")

    # noon is jd0+0.5 and should still map to same JDN
    assert_eq(jd_to_jdn(jd0 + 0.5), jdn, "noon JD should map to same JDN")


def test_datetime_jd_roundtrip():
    samples = [
        datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 2, 24, 3, 4, 5, tzinfo=timezone.utc),
    ]
    for dt in samples:
        jd = datetime_utc_to_jd(dt)
        dt2 = jd_to_datetime_utc(jd)
        # allow 1 millisecond tolerance because of float timestamp conversions
        assert_close(dt2.timestamp(), dt.timestamp(), tol=1e-3, msg=f"datetime<->jd roundtrip failed for {dt}")


def test_tt_utc_inverse_consistency():
    # This only checks that our forward/backward conversion is self-consistent
    # (not that it matches true IERS UT1/UTC).
    dt = datetime(2026, 2, 24, 0, 0, 0, tzinfo=timezone.utc)
    jd_utc = datetime_utc_to_jd(dt)

    jd_tt = jd_utc_to_jd_tt(jd_utc, ut1_utc_seconds=0.0)
    jd_utc2 = jd_tt_to_jd_utc(jd_tt, ut1_utc_seconds=0.0)

    # expect within ~0.5s (2 fixed-point iterations; ΔT changes slowly)
    assert_close((jd_utc2 - jd_utc) * 86400.0, 0.0, tol=0.5, msg="TT<->UTC inverse consistency")


def test_T_J2000_roundtrip():
    jd_tt = 2451545.0  # J2000.0 TT
    T = T_from_jd_tt(jd_tt)
    jd2 = jd_tt_from_T(T)
    assert_close(jd2, jd_tt, tol=0.0, msg="T_from_jd_tt / jd_tt_from_T mismatch")

    jd_tt2 = 2451545.0 + 12345.678
    T2 = T_from_jd_tt(jd_tt2)
    jd3 = jd_tt_from_T(T2)
    assert_close(jd3, jd_tt2, tol=1e-12, msg="T roundtrip mismatch")


def test_lmt_and_tz_offsets():
    dt_utc = datetime(2026, 2, 24, 12, 0, 0, tzinfo=timezone.utc)

    # LMT at 90E is +6h
    dt_lmt = utc_to_lmt(dt_utc, longitude_deg_east=90.0)
    back = lmt_to_utc(dt_lmt, longitude_deg_east=90.0)
    assert_close(back.timestamp(), dt_utc.timestamp(), tol=1e-6, msg="UTC<->LMT mismatch")

    # fixed timezone offset: Montreal standard approx -5
    dt_local = utc_to_local(dt_utc, tz_offset_hours=-5)
    back2 = local_to_utc(dt_local, tz_offset_hours=-5)
    assert_close(back2.timestamp(), dt_utc.timestamp(), tol=1e-6, msg="UTC<->local mismatch")


def main() -> int:
    test_date_jdn_roundtrip()
    test_jd_jdn_relation()
    test_datetime_jd_roundtrip()
    test_tt_utc_inverse_consistency()
    test_T_J2000_roundtrip()
    test_lmt_and_tz_offsets()
    print("OK: time_scales basic tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())