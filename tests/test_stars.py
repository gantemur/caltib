"""Star places against an independent reference.

Reference values: skyfield 1.55 stars built by its Hipparcos loader from
hip_main.dat (CDS I/239; epoch J1991.25, rigorous space motion, parallax set
to zero), Earth from JPL DE440; geometric place referred to the mean equator
and equinox of date (IAU 2006 precession). Computed 2026-11-14.

With proper motion counted from J2000.0 instead of the catalogue epoch
J1991.25 (caltib up to 0.3.4), Arcturus is 20 arcseconds and Sirius 12
arcseconds from these values at every date.
"""
import math

import pytest

from caltib.reference import stars

# (hip, jd_tt, ra_deg, dec_deg, ecliptic lon_deg, lat_deg)
REFERENCE = [
    (69673, 2415020.0, 212.7749536, 19.7030235, 202.8380542, 30.8055383),   # Arcturus, 1900
    (69673, 2461041.5, 214.2119876, 19.0480658, 204.5965607, 30.7182026),   # 2026
    (69673, 2488069.5, 215.0568530, 18.6680176, 205.6297204, 30.6668482),   # 2100
    (32349, 2415020.0, 100.1856181, -16.5783276, 102.7037226, -39.5822575),  # Sirius
    (32349, 2461041.5, 101.5735012, -16.7536306, 104.4400199, -39.6112204),
    (32349, 2488069.5, 102.3883088, -16.8641992, 105.4601134, -39.6282666),
    (17702, 2415020.0, 55.3844164, 23.7959873, 58.5959430, 4.0404131),      # Alcyone
    (17702, 2461041.5, 57.2588874, 24.1835127, 60.3555751, 4.0537018),
    (17702, 2488069.5, 58.3650456, 24.4020130, 61.3894501, 4.0615278),
]
TOLERANCE_ARCSEC = 1.0


def _arcsec(a, b):
    return ((a - b + 180.0) % 360.0 - 180.0) * 3600.0


@pytest.mark.parametrize("hip,jd,ra,dec,lon,lat", REFERENCE)
def test_star_places_match_hipparcos_at_its_epoch(hip, jd, ra, dec, lon, lat):
    eq = stars.get_star_equatorial(hip, jd)
    ecl = stars.get_star_ecliptic(hip, jd)
    assert abs(_arcsec(eq.ra_deg, ra)) * math.cos(math.radians(dec)) < TOLERANCE_ARCSEC
    assert abs(_arcsec(eq.dec_deg, dec)) < TOLERANCE_ARCSEC
    assert abs(_arcsec(ecl.L_deg, lon)) * math.cos(math.radians(lat)) < TOLERANCE_ARCSEC
    assert abs(_arcsec(ecl.B_deg, lat)) < TOLERANCE_ARCSEC


def test_catalogue_epoch_is_j1991_25():
    assert stars.CATALOG_EPOCH_JD == 2448349.0625


def test_template_matches_module():
    import pathlib
    here = pathlib.Path(stars.__file__).parent
    module = (here / "stars.py").read_text()
    template = (here / "stars_tmpl.py").read_text()
    head, tail = template.split("{stars_dict_str}")
    assert module.startswith(head) and module.endswith(tail)
