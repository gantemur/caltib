"""
caltib.engines.trad_planets
---------------------------
Traditional kinematic engine for the 5 visible planets, Sun, and Rahu.
Uses the Kālacakra algorithms (mean slow longitude, step index, and dual tables).
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Tuple

from caltib.engines.interfaces import PlanetsEngineProtocol, NumT
from caltib.engines.astro.tables import QuarterWaveTable, HalfWaveTable

PLANETS = ("mercury", "venus", "mars", "jupiter", "saturn")

def frac_turn(val: Fraction) -> Fraction:
    """Wraps a fractional turn to [0, 1)."""
    q = val.numerator // val.denominator
    return val - Fraction(q, 1)

@dataclass(frozen=True)
class TraditionalPlanetsParams:
    epoch_k: int
    m0: Fraction  # Epoch absolute Julian Day
    jd0: Fraction # Epoch base JD (often the integer part of m0)
    
    # Sun, Rahu, and Planetary Parameters
    p0: Dict[str, Fraction]          # Epoch mean geo/heliocentric longitudes
    p_rate: Dict[str, Fraction]      # Mean geo/heliocentric rates (turns per solar day)
    birth_signs: Dict[str, Fraction] # Apse lines
    
    manda_tables: Dict[str, Tuple[int, ...]]  # Table 12
    sighra_tables: Dict[str, Tuple[int, ...]] # Table 13

class TraditionalPlanetsEngine(PlanetsEngineProtocol):
    def __init__(self, p: TraditionalPlanetsParams):
        self.p = p
        
        # Initialize the generalized tables with their specific ancient periods
        self.manda = {
            k: QuarterWaveTable(v) for k, v in self.p.manda_tables.items()
        }
        self.sighra = {
            # Table 13 spans 27 Nakshatras for a full orbit
            k: HalfWaveTable(v) for k, v in self.p.sighra_tables.items()
        }

    @property
    def epoch_k(self) -> int:
        return self.p.epoch_k

    def _get_base_longitudes(self, jd: NumT) -> Dict[str, Fraction]:
        """Calculates the pure mean motions for the requested JD."""
        gen_day = Fraction(jd) - self.p.jd0
        
        bases = {}
        # Sun, Rahu, and Heliocentric Planets (Mean)
        for p in ("sun", "rahu") + PLANETS:
            bases[p] = frac_turn(self.p.p0[p] + self.p.p_rate[p] * gen_day)
            
        return bases

    def mean_longitude(self, planet: str, jd: NumT) -> Fraction:
        planet = planet.lower()
        bases = self._get_base_longitudes(jd)
        # In the Kālacakra system, the "mean geocentric" longitude (Dal-ba) 
        # is the Sun for inner planets, and the Heliocentric for outer planets.
        if planet in ("mercury", "venus"):
            return bases["sun"]
        return bases[planet]

    def true_longitude(self, planet: str, jd: NumT) -> Fraction:
        planet = planet.lower()
        bases = self._get_base_longitudes(jd)
        
        # The traditional planetary algorithm does not calculate true Sun/Rahu here
        # (Sun is handled by DayEngine, Rahu is purely linear). We return mean.
        if planet in ("sun", "rahu"):
            return bases[planet]
            
        mean_sun = bases["sun"]
        mean_helio = bases[planet]
        
        # 1. Assign "Slow Longitude" and "Step Index" based on inner/outer
        if planet in ("mercury", "venus"):
            slow_long = mean_sun
            step_index = mean_helio
        else:
            slow_long = mean_helio
            step_index = mean_sun
            
        # 2. Equation of Center (Manda)
        anomaly = frac_turn(slow_long - self.p.birth_signs[planet])
        equ = self.manda[planet].eval_turn(anomaly)
        
        # Convert Kālacakra units (60 * 27 = 1620) to turns
        true_slow_long = frac_turn(slow_long + equ / Fraction(1620))
        
        # 3. Equation of Conjunction (Sighra)
        diff = frac_turn(step_index - true_slow_long)
        corr = self.sighra[planet].eval_turn(diff)
        
        fast_long = frac_turn(true_slow_long + corr / Fraction(1620))
        return fast_long

    def longitudes(self, jd: NumT) -> Dict[str, Dict[str, Fraction]]:
        """Evaluates everything in a single optimized pass."""
        res = {}
        # Pre-compute all linear bases once
        bases = self._get_base_longitudes(jd)
        
        for p in ("sun", "rahu") + PLANETS:
            
            # Extract mean longitude directly from pre-computed bases
            if p in ("mercury", "venus"):
                # Inner planets' "mean" geocentric longitude is tied to the Sun
                mean_val = bases["sun"]
            else:
                mean_val = bases[p]
                
            if p in ("sun", "rahu"):
                true_val = mean_val
            else:
                # Assign "Slow Longitude" and "Step Index"
                if p in ("mercury", "venus"):
                    slow, step = bases["sun"], bases[p]
                else:
                    slow, step = bases[p], bases["sun"]
                    
                anomaly = frac_turn(slow - self.p.birth_signs[p])
                equ = self.manda[p].eval_turn(anomaly)
                true_slow = frac_turn(slow + equ / Fraction(1620))
                
                diff = frac_turn(step - true_slow)
                corr = self.sighra[p].eval_turn(diff)
                true_val = frac_turn(true_slow + corr / Fraction(1620))
                
            res[p] = {"mean": mean_val, "true": true_val}
            
        return res