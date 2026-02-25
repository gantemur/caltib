#ephemeris/de422.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional


# --------------------------
# small numeric helpers
# --------------------------

def wrap180(deg: float) -> float:
    return (deg + 180.0) % 360.0 - 180.0


SYNODIC_MEAN = 29.530588853
EPS_J2000_DEG = 23.439291111


def _rot_x_minus_eps(v):
    eps = math.radians(EPS_J2000_DEG)
    x, y, z = float(v[0]), float(v[1]), float(v[2])
    y2 =  math.cos(eps) * y + math.sin(eps) * z
    z2 = -math.sin(eps) * y + math.cos(eps) * z
    return (x, y2, z2)


def _lon_ecl_deg(v_eq) -> float:
    x, y, z = _rot_x_minus_eps(v_eq)
    return (math.degrees(math.atan2(y, x)) % 360.0)


def _load_constants_dict(de422_mod) -> dict:
    # de422 package typically has constants.npy next to __file__
    import pathlib
    import numpy as np
    pkgdir = pathlib.Path(de422_mod.__file__).resolve().parent
    p = pkgdir / "constants.npy"
    if not p.exists():
        return {}
    c = np.load(str(p), allow_pickle=True)
    try:
        return c.item()
    except Exception:
        return {}


def _get_emrat(constants: dict) -> float:
    for k in ("EMRAT", "emrat"):
        if k in constants:
            return float(constants[k])
    # fallback canonical value
    return 81.30056907419062


@dataclass
class DE422Elongation:
    """
    Computes geocentric ecliptic elongation λ_moon - λ_sun (deg) using DE422.

    Requires optional deps:
      pip install "caltib[ephemeris]" de422
    """
    eph: object
    emrat: float

    @classmethod
    def load(cls) -> "DE422Elongation":
        try:
            import de422  # type: ignore
            from jplephem import Ephemeris  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "DE422 ephemeris not available. Install extras:\n"
                "  pip install \"caltib[ephemeris]\" de422"
            ) from e

        eph = Ephemeris(de422)
        const = {}
        try:
            const = _load_constants_dict(de422)
        except Exception:
            const = {}
        emrat = _get_emrat(const)
        return cls(eph=eph, emrat=emrat)

    def elong_deg(self, jd_tt: float) -> float:
        """
        Elongation in degrees at TT Julian day 'jd_tt'.
        """
        # Vectors in equatorial frame (J2000)
        r_emb = self.eph.compute("earthmoon", jd_tt)[:3]
        r_em  = self.eph.compute("moon", jd_tt)[:3]      # geocentric moon
        r_sun = self.eph.compute("sun", jd_tt)[:3]       # barycentric sun

        # Earth position from EMB and Moon vector
        # r_earth = r_emb - r_em/(EMRAT+1)
        r_earth = r_emb - r_em / (self.emrat + 1.0)

        # Earth->Sun and Earth->Moon
        r_es = r_sun - r_earth
        lon_s = _lon_ecl_deg(r_es)
        lon_m = _lon_ecl_deg(r_em)

        return (lon_m - lon_s) % 360.0


# --------------------------
# root finding for elongation targets
# --------------------------

def solve_target_near(el: DE422Elongation, t_guess: float, target_deg: float, halfwidth_days: float = 3.0) -> float:
    """
    Solve elong(t)=target (deg) near t_guess, in TT JD, with Newton+bracket.
    """
    def f(t: float) -> float:
        return wrap180(el.elong_deg(t) - target_deg)

    # Newton
    t = t_guess
    for _ in range(10):
        y = f(t)
        if abs(y) < 1e-8:
            return t
        h = 1e-3
        dy = wrap180(el.elong_deg(t + h) - el.elong_deg(t - h)) / (2 * h)
        if not math.isfinite(dy) or abs(dy) < 1e-6:
            break
        t -= y / dy

    # bracket+bisect
    w = halfwidth_days
    a, b = t_guess - w, t_guess + w
    fa, fb = f(a), f(b)
    while fa * fb > 0 and w < 40.0:
        w *= 1.6
        a, b = t_guess - w, t_guess + w
        fa, fb = f(a), f(b)
    if fa * fb > 0:
        return t

    for _ in range(140):
        m = 0.5 * (a + b)
        fm = f(m)
        if fa * fm <= 0:
            b, fb = m, fm
        else:
            a, fa = m, fm
        if (b - a) < 1e-10:
            break
    return 0.5 * (a + b)


def find_new_moon_near(el: DE422Elongation, jd0: float) -> float:
    """
    Find a new moon near jd0: solve elong(t)=0.
    """
    # coarse scan then refine
    try:
        import numpy as np
    except ImportError as e:
        raise RuntimeError("This function needs numpy. Install: pip install numpy") from e

    grid = np.linspace(jd0 - 25.0, jd0 + 25.0, 1201)
    vals = np.array([abs(wrap180(el.elong_deg(t))) for t in grid])
    t_guess = float(grid[int(vals.argmin())])
    return solve_target_near(el, t_guess, 0.0, halfwidth_days=4.0)


def build_new_moons(el: DE422Elongation, t_min: float, t_max: float) -> List[float]:
    """
    Build list of new moons covering [t_min, t_max] (TT JD).
    """
    center = 0.5 * (t_min + t_max)
    t0 = find_new_moon_near(el, center)
    moons = [t0]

    t = t0
    while t < t_max + 60.0:
        t = solve_target_near(el, t + SYNODIC_MEAN, 0.0, halfwidth_days=4.0)
        moons.append(t)

    t = t0
    back = []
    while t > t_min - 60.0:
        t = solve_target_near(el, t - SYNODIC_MEAN, 0.0, halfwidth_days=4.0)
        back.append(t)

    return list(reversed(back)) + moons


def tithi_boundary_in_lunation(el: DE422Elongation, t0: float, t1: float, d: int) -> float:
    """
    Boundary time in TT JD when elongation reaches 12*d degrees inside [t0,t1],
    where t0,t1 are consecutive new moons.
    """
    if d == 30:
        return t1

    target = 12.0 * d
    guess = t0 + (t1 - t0) * (d / 30.0)

    def f(t: float) -> float:
        return wrap180(el.elong_deg(t) - target)

    w = 0.8
    a = max(t0, guess - w)
    b = min(t1, guess + w)
    fa, fb = f(a), f(b)
    while fa * fb > 0 and w < 10.0:
        w *= 1.6
        a = max(t0, guess - w)
        b = min(t1, guess + w)
        fa, fb = f(a), f(b)

    if fa * fb > 0:
        return solve_target_near(el, guess, target, halfwidth_days=3.0)

    for _ in range(140):
        m = 0.5 * (a + b)
        fm = f(m)
        if fa * fm <= 0:
            b, fb = m, fm
        else:
            a, fa = m, fm
        if (b - a) < 1e-10:
            break
    return 0.5 * (a + b)