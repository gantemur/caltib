"""
caltib.engines.rational_planets
-------------------------------
Continuous geometric kinematic engine. Uses truncated rational VSOP87 series 
and exact geometric conjunction (Sighra) via table interpolants.
"""

from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Dict

from caltib.engines.interfaces import PlanetsEngineProtocol, NumT
from caltib.engines.astro.affine_series import AffineTabSeriesT

def frac_turn(val: Fraction) -> Fraction:
    """Wraps a fractional turn to [0, 1)."""
    q = val.numerator // val.denominator
    return val - Fraction(q, 1)

@dataclass(frozen=True)
class RationalPlanetsParams:
    epoch_k: int
    
    # Continuous Affine series for Heliocentric Longitude (L).
    # MUST include "earth" to serve as the baseline for geocentric conversions.
    helio_series: Dict[str, AffineTabSeriesT]
    
    # Geocentric series that bypass conjunction math entirely (e.g., Rahu, Moon)
    geo_series: Dict[str, AffineTabSeriesT]
    
    # Mean heliocentric distances in Astronomical Units (AU)
    r_au: Dict[str, Fraction]
    
    # Rational Trigonometry Injections (Expected to accept/return turns)
    sin_eval: Callable[[Fraction], Fraction]
    cos_eval: Callable[[Fraction], Fraction]
    arctan2_eval: Callable[[Fraction, Fraction], Fraction]

class RationalPlanetsEngine(PlanetsEngineProtocol):
    """
    Evaluates True Geocentric Longitudes using continuous rational affine series
    and continuous geometric parallax (Sighra).
    """
    def __init__(self, p: RationalPlanetsParams):
        self.p = p

    @property
    def epoch_k(self) -> int:
        return self.p.epoch_k

    def mean_longitude(self, planet: str, jd: NumT) -> Fraction:
        """
        Returns the base linear component (A + B*t) of the longitude.
        """
        t = Fraction(jd)
        planet = planet.lower()
        
        if planet in self.p.geo_series:
            return frac_turn(self.p.geo_series[planet].base(t))
            
        # Geocentric Sun is exactly opposite the Heliocentric Earth
        if planet == "sun":
            return frac_turn(self.p.helio_series["earth"].base(t) + Fraction(1, 2))
            
        return frac_turn(self.p.helio_series[planet].base(t))

    def true_longitude(self, planet: str, jd: NumT) -> Fraction:
        planet = planet.lower()
        t = Fraction(jd)
        
        # 1. Pure Geocentric Bodies (Rahu, Moon)
        if planet in self.p.geo_series:
            return frac_turn(self.p.geo_series[planet].eval(t))
        
        # Earth Helio Longitude is the baseline for all geometric parallax
        L_E = frac_turn(self.p.helio_series["earth"].eval(t))
        
        # 2. The Sun: Exactly 180 degrees from True Earth
        if planet == "sun":
            return frac_turn(L_E + Fraction(1, 2))
            
        # 3. Planets: Heliocentric Longitude -> Geocentric Conjunction
        L_P = frac_turn(self.p.helio_series[planet].eval(t))
        r = self.p.r_au[planet]
        
        # Calculate the angular anomaly between Planet and Earth
        alpha = frac_turn(L_P - L_E)
        
        # Evaluate rational trigonometry
        sin_alpha = self.p.sin_eval(alpha)
        cos_alpha = self.p.cos_eval(alpha)
        
        # The Conjunction Vector (Assuming Earth r_au = 1.0)
        y = r * sin_alpha
        x = r * cos_alpha - Fraction(1, 1)
        
        # Geocentric offset from the Earth's heliocentric longitude
        delta = self.p.arctan2_eval(y, x)
        
        # The final Geocentric Longitude
        return frac_turn(L_E + delta)

    def longitudes(self, jd: NumT) -> Dict[str, Dict[str, Fraction]]:
        """Evaluates all bodies for the given Julian Day."""
        res = {}
        for p in ("sun", "mercury", "venus", "mars", "jupiter", "saturn", "rahu"):
            if p in self.p.helio_series or p in self.p.geo_series or p == "sun":
                res[p] = {
                    "mean": self.mean_longitude(p, jd),
                    "true": self.true_longitude(p, jd)
                }
        return res