"""
caltib.engines.arithmetic_month
-------------------------------
Discrete arithmetic engine for mapping absolute lunation indices (n)
to human calendar labels (Year, Month, Leap status).
"""

from __future__ import annotations

from fractions import Fraction
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .interfaces import MonthEngineProtocol


def _floor_div(a: int, b: int) -> int:
    return a // b


def amod12(x: int) -> int:
    """Arithmetic mod giving 1..12."""
    return ((x - 1) % 12) + 1


@dataclass(frozen=True)
class ArithmeticMonthParams:
    """
    Paper convention: P=p < Q=q, ell=Q-P.
    """
    epoch_k: int           # The absolute Meeus lunation index of the epoch
    sgang1: Fraction           # The solar longitude anchor (denoted by d1 in [Gantumur], and by p1 in [Janson])
    
    Y0: int
    M0: int

    P: int
    Q: int

    beta_star: int
    tau: int

    def __post_init__(self) -> None:
        if self.P <= 0 or self.Q <= 0:
            raise ValueError("P,Q must be positive")
        if not (self.P < self.Q):
            raise ValueError("Require P < Q")
        if not (1 <= self.M0 <= 12):
            raise ValueError("M0 must be in 1..12")
        if not (0 <= self.tau < self.P):
            raise ValueError("tau must be in 0..P-1")
        if self.leap_labeling not in ("first_is_leap", "second_is_leap"):
            raise ValueError("leap_labeling must be 'first_is_leap' or 'second_is_leap'")

    @property
    def ell(self) -> int:
        return self.Q - self.P

    @property
    def trigger_set(self) -> Tuple[int, ...]:
        return tuple(((self.tau + k) % self.P) for k in range(self.ell))

    @property
    def gamma_shift(self) -> int:
        """
        Shift sending TriggerSet to {0,...,ell-1}:
          gamma_shift ≡ -tau (mod P), in {0,...,P-1}.
        """
        return (self.P - self.tau) % self.P

    @property
    def beta_int(self) -> int:
        """
        Combined constant used in internal index and n_+:
          beta_int := beta_star + gamma_shift.
        """
        return self.beta_star + self.gamma_shift


class ArithmeticMonthEngine:
    """
    Strictly handles discrete arithmetic for the calendar.
    Fully implements MonthEngineProtocol.
    """
    def __init__(self, params: ArithmeticMonthParams):
        self.p = params

    # ---------------------------------------------------------
    # Protocol Properties
    # ---------------------------------------------------------

    @property
    def epoch_k(self) -> int:
        return self.p.epoch_k

    @property
    def sgang1(self) -> NumT:
        return self.p.sgang1

    # ---------------------------------------------------------
    # Protocol Methods
    # ---------------------------------------------------------

    def get_lunations(self, year: int, month: int) -> List[int]:
        """
        Returns the absolute lunation indices for a given Year and Month number.
        Chronological order is strictly preserved.
        """
        nplus = self.n_plus(year, month)
        if self.is_trigger_label(year, month):
            # A leap month pair chronologically spans [nplus - 1, nplus]
            return [nplus - 1, nplus]
        return [nplus]

    def first_lunation(self, year: int) -> int:
        """
        Returns the absolute lunation index (n) for the very first month 
        of the given Tibetan year.
        """
        return self.get_lunations(year, 1)[0]

    def get_month_info(self, n: int) -> Dict[str, Any]:
        """
        Returns calendar data for a given lunation n.
        """
        Y, M, leap_state = self.label_from_lunation(n)
        
        # Linear month count is strictly 0-indexed relative to the start of the year
        linear = n - self.first_lunation(Y)
        
        return {
            "year": Y,
            "month": M,
            "leap_state": leap_state,  # 0: regular, 1: first of two, 2: second of two
            "linear_month": linear
        }

    # ---------------------------------------------------------
    # Core Mathematical Forward Tracking
    # ---------------------------------------------------------

    def mstar(self, Y: int, M: int) -> int:
        return 12 * (Y - self.p.Y0) + (M - self.p.M0)

    def intercalation_index(self, Y: int, M: int) -> int:
        """I ≡ ell*M* + beta_star  (mod P)."""
        return (self.p.ell * self.mstar(Y, M) + self.p.beta_star) % self.p.P

    def intercalation_index_internal(self, Y: int, M: int) -> int:
        """I_int ≡ ell*M* + beta_int  (mod P). Trigger iff I_int < ell."""
        return (self.p.ell * self.mstar(Y, M) + self.p.beta_int) % self.p.P

    def is_trigger_label(self, Y: int, M: int) -> bool:
        return self.intercalation_index_internal(Y, M) < self.p.ell

    def intercalation_index_traditional(self, Y: int, M: int, *, wrap: str = "extended") -> int:
        """
        Traditional/almanac-style intercalation index.
        Rule:
            cutoff = tau + ell - 1
            if I > cutoff: I_trad = I + ell
            else:          I_trad = I

        wrap:
        - "extended": return I_trad as an integer in {0,...,P-1} ∪ {P,...,P+ell-1}.
                        (So 65/66 can appear when P=65, ell=2.)
        - "mod":      return I_trad mod P in {0,...,P-1}.
                        (So 0/1 instead of 65/66.)

        Notes:
        * This matches the Phugpa-style statement “index increases by 2 once >49”.
        * For tau near the end (e.g. tau=P-ell), the shift may be rare/none in this
            linear convention; this mirrors the “gap / wrap” discussion in the remark.
        """
        I = self.intercalation_index(Y, M)

        cutoff = self.p.tau + self.p.ell - 1
        I_trad = I + self.p.ell if I > cutoff else I

        if wrap == "extended":
            return I_trad
        if wrap == "mod":
            return I_trad % self.p.P
        raise ValueError("wrap must be 'extended' or 'mod'")


    def n_plus(self, Y: int, M: int) -> int:
        """
        Right-end lunation index attached to label (Y,M):
          n_+(M*) = floor((Q*M* + beta_int)/P).
        """
        Mst = self.mstar(Y, M)
        return _floor_div(self.p.Q * Mst + self.p.beta_int, self.p.P)

    # ---------------------------------------------------------
    # Core Mathematical Inverse Tracking
    # ---------------------------------------------------------

    def mstar_from_lunation(self, n: int) -> int:
        """
        Right-end inverse: M*(n) = floor((P*n - beta_int - 1)/Q) + 1.
        """
        return _floor_div(self.p.P * n - self.p.beta_int - 1, self.p.Q) + 1

    def cumul_month_from_lunation(self, n: int) -> int:
        """x = M* + M0 = 12(Y-Y0)+M."""
        return self.mstar_from_lunation(n) + self.p.M0

    def label_from_lunation(self, n: int) -> Tuple[int, int, int]:
        """
        Inverse label computation handling standard and intercalary cases.
        Returns (Year, Month, leap_state) where leap_state is:
        0 = regular, 1 = first occurrence, 2 = second occurrence.
        """
        cumul = self.cumul_month_from_lunation(n)
        M = amod12(cumul)
        Y = self.p.Y0 + _floor_div(cumul - M, 12)

        cumul_next = self.cumul_month_from_lunation(n + 1)
        cumul_prev = self.cumul_month_from_lunation(n - 1)

        if cumul == cumul_next:
            leap_state = 1
        elif cumul == cumul_prev:
            leap_state = 2
        else:
            leap_state = 0

        return Y, M, leap_state

    # ---------------------------------------------------------
    # Debug / Legacy Helpers
    # ---------------------------------------------------------
    
    def debug_label(self, Y: int, M: int) -> Dict[str, object]:
        Mst = self.mstar(Y, M)
        I_ext = self.intercalation_index(Y, M)
        I_int = self.intercalation_index_internal(Y, M)
        trig = self.is_trigger_label(Y, M)
        # Traditional/almanac intercalation index (see Henning/Janson remark):
        I_trad_ext = self.intercalation_index_traditional(Y, M, wrap="extended")
        I_trad_mod = self.intercalation_index_traditional(Y, M, wrap="mod")

        nplus = self.n_plus(Y, M)
        out: Dict[str, object] = {
            "label": {"Y": Y, "M": M},
            "Mstar": Mst,
            "P": self.p.P,
            "Q": self.p.Q,
            "ell": self.p.ell,
            "beta_star": self.p.beta_star,
            "tau": self.p.tau,
            "gamma_shift": self.p.gamma_shift,
            "beta_int": self.p.beta_int,
            "I_ext": I_ext,
            "I_int": I_int,
            "I_trad_extended": I_trad_ext,
            "I_trad_mod": I_trad_mod,
            "trigger": trig,
            "n_plus": nplus,
            "check": {
                "formula": "n_plus = floor((Q*M* + beta_int)/P)",
                "numerator": self.p.Q * Mst + self.p.beta_int,
            },
        }

        lunations = self.get_lunations(Y, M)
        if trig:
            out["n_minus"] = nplus - 1
            out["instances"] = {
                "first_occurrence": lunations[0],
                "second_occurrence": lunations[1],
            }
        else:
            out["instances"] = {"regular": lunations[0]}

        return out

    def debug_lunation(self, n: int) -> Dict[str, object]:
        cumul = self.cumul_month_from_lunation(n)
        M = amod12(cumul)
        Y = self.p.Y0 + _floor_div(cumul - M, 12)

        cumul_prev = self.cumul_month_from_lunation(n - 1)
        cumul_next = self.cumul_month_from_lunation(n + 1)

        Y2, M2, leap_state = self.label_from_lunation(n)

        # decode label, then compute intercalation indices for that label
        I_ext = self.intercalation_index(Y2, M2)
        I_int = self.intercalation_index_internal(Y2, M2)
        I_trad_ext = self.intercalation_index_traditional(Y2, M2, wrap="extended")
        I_trad_mod = self.intercalation_index_traditional(Y2, M2, wrap="mod")

        return {
            "n": n,
            "P": self.p.P,
            "Q": self.p.Q,
            "ell": self.p.ell,
            "beta_star": self.p.beta_star,
            "tau": self.p.tau,
            "gamma_shift": self.p.gamma_shift,
            "beta_int": self.p.beta_int,
            "Mstar_rightend": self.mstar_from_lunation(n),
            "cumul_month": cumul,
            "cumul_prev": cumul_prev,
            "cumul_next": cumul_next,
            "decoded": {"Y": Y, "M": M},
            "label_from_lunation": {"Y": Y2, "M": M2, "leap_state": leap_state},
            "repeat_test": {
                "cumul==cumul_next": (cumul == cumul_next),
                "cumul==cumul_prev": (cumul == cumul_prev),
            },
            "check": {
                "formula_Mstar": "M* = floor((P*n - beta_int - 1)/Q) + 1",
                "numerator": self.p.P * n - self.p.beta_int - 1,
            },
            "intercalation_for_label": {
                "I_ext": I_ext,
                "I_int": I_int,
                "I_trad_extended": I_trad_ext,
                "I_trad_mod": I_trad_mod,
            },
        }
