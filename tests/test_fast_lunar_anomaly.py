import ast
import inspect
import math
from pathlib import Path

import pytest

from caltib.reference import astro_args as aa, lunar, planets


J2000 = 2451545.0


def angular_delta(a, b):
    return abs((a - b + 180) % 360 - 180)


def test_fast_lunar_j2000_and_full_moon_route():
    assert planets.fast_lunar_position(J2000)[0] == pytest.approx(222.76628231651577, abs=1e-10)
    full = lunar.lunar_position(J2000)
    assert full.L_true_deg == pytest.approx(223.31509086899683, abs=1e-10)
    assert full.L_true_deg != planets.fast_lunar_position(J2000)[0]
    for fast in (True, False):
        direct = planets.geocentric_position("moon", J2000, fast_emb=fast)
        assert (direct.L_true_deg, direct.B_true_deg, direct.R_true_au) == (
            full.L_true_deg, full.B_true_deg, full.R_true_au,
        )


@pytest.mark.parametrize("solar_phase, lunar_phase, expected", [(0.75, 0.25, 5.929), (0.25, 0.75, 353.351)])
def test_fast_lunar_uses_lunar_phase_and_wraps(solar_phase, lunar_phase, expected):
    args = aa.FundamentalArgs(Lp_turn=0.999, D_turn=0, M_turn=solar_phase,
                             Mp_turn=lunar_phase, F_turn=0.25, Omega_turn=0)
    lon, lat, radius = planets.fast_lunar_position(J2000, args)
    assert lon == pytest.approx(expected, abs=1e-10)
    assert lat == pytest.approx(5.128)
    assert radius == 0.00257


def test_fast_lunar_first_harmonic_on_a_historical_grid():
    for days in range(-365250, 365251, 4001):
        jd = J2000 + days
        args = aa.fundamental_args_jd(jd)
        expected = (args.Lp_deg + 6.289 * math.sin(math.tau * args.Mp_turn)) % 360
        lon, lat, radius = planets.fast_lunar_position(jd)
        assert angular_delta(lon, expected) < 1e-10
        assert lat == pytest.approx(5.128 * math.sin(math.tau * args.F_turn), abs=1e-10)
        assert radius == 0.00257


@pytest.mark.parametrize("body", ["sun", "mercury", "venus", "mars", "jupiter", "saturn"])
def test_fast_emb_selection_changes_reference_body_by_arcseconds(body):
    differences = []
    for days in range(-36525, 36526, 997):
        jd = J2000 + days
        default = planets.geocentric_position(body, jd)
        assert default == planets.geocentric_position(body, jd, fast_emb=True)
        full = planets.geocentric_position(body, jd, fast_emb=False)
        differences.append(3600 * angular_delta(default.L_true_deg, full.L_true_deg))
    # One-term approximation vs. the full lunar EMB offset, not ephemeris accuracy.
    assert 0.001 < max(differences) < 10


def test_fast_lunar_template_matches_the_generated_helper():
    template = Path(planets.__file__).with_name("planets_tmpl.py")
    original, = [node for node in ast.parse(template.read_text(encoding="utf-8")).body
                 if isinstance(node, ast.FunctionDef) and node.name == "fast_lunar_position"]
    generated, = ast.parse(inspect.getsource(planets.fast_lunar_position)).body
    assert ast.dump(original) == ast.dump(generated)
