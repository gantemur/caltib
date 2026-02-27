#engines/rational_month.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


def _floor_div(a: int, b: int) -> int:
    return a // b


def amod12(x: int) -> int:
    """Arithmetic mod giving 1..12."""
    return ((x - 1) % 12) + 1


@dataclass(frozen=True)
class RationalMonthParams:
    """
    Paper convention: P=p < Q=q, ell=Q-P.

    TriggerSet is a contiguous block of length ell in Z/PZ starting at tau.

    We implement the "internal index" idea:
      beta_int := beta_star + gamma_shift
    so that trigger test becomes I_int < ell, where
      I_int ≡ ell*M* + beta_int (mod P).
    """
    Y0: int
    M0: int

    P: int
    Q: int

    beta_star: int
    tau: int

    leap_labeling: str = "first_is_leap"

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


class RationalMonthEngine:
    def __init__(self, params: RationalMonthParams):
        self.p = params

    # -------------------------
    # forward
    # -------------------------

    def mstar(self, Y: int, M: int) -> int:
        return 12 * (Y - self.p.Y0) + (M - self.p.M0)

    def intercalation_index(self, Y: int, M: int) -> int:
        """The intercalation index (external)"""
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

    def true_month(self, Y: int, M: int, *, is_leap_month: bool) -> int:
        nplus = self.n_plus(Y, M)

        if not self.is_trigger_label(Y, M):
            if is_leap_month:
                raise ValueError(f"({Y},{M}) is not trigger, cannot be leap")
            return nplus

        nminus = nplus - 1
        if self.p.leap_labeling == "first_is_leap":
            return nminus if is_leap_month else nplus
        return nplus if is_leap_month else nminus

    # -------------------------
    # inverse (closed form, right-end convention)
    # -------------------------

    def mstar_from_true_month(self, n: int) -> int:
        """
        Right-end inverse (your Prop 3.12 / Janson §5.3 style):

          M*(n) = floor((P*n - beta_int - 1)/Q) + 1.

        This fixes the off-by-one you observed (n=480 -> M*=466 for Phugpa:E1987).
        """
        return _floor_div(self.p.P * n - self.p.beta_int - 1, self.p.Q) + 1

    def x_from_true_month(self, n: int) -> int:
        """x = M* + M0 = 12(Y-Y0)+M."""
        return self.mstar_from_true_month(n) + self.p.M0

    def label_from_true_month(self, n: int) -> Tuple[int, int, bool]:
        """
        1) x = M*(n) + M0 with the right-end M*(n)
        2) decode M=amod12(x), Y=Y0 + (x-M)/12
        3) leap test by repetition of x(n):
             x(n)==x(n+1) => first in repeated pair
             x(n)==x(n-1) => second in repeated pair
           then apply leap_labeling.
        """
        x = self.x_from_true_month(n)
        M = amod12(x)
        Y = self.p.Y0 + _floor_div(x - M, 12)

        x_next = self.x_from_true_month(n + 1)
        x_prev = self.x_from_true_month(n - 1)

        if x == x_next:
            is_leap = (self.p.leap_labeling == "first_is_leap")
        elif x == x_prev:
            is_leap = (self.p.leap_labeling == "second_is_leap")
        else:
            is_leap = False

        return Y, M, is_leap

    # -------------------------
    # debug helpers
    # -------------------------

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

        if trig:
            out["n_minus"] = nplus - 1
            out["instances"] = {
                "leap": self.true_month(Y, M, is_leap_month=True),
                "regular": self.true_month(Y, M, is_leap_month=False),
                "leap_labeling": self.p.leap_labeling,
            }
        else:
            out["instances"] = {"regular": nplus}

        return out

    def debug_true_month(self, n: int) -> Dict[str, object]:
        x = self.x_from_true_month(n)
        M = amod12(x)
        Y = self.p.Y0 + _floor_div(x - M, 12)

        x_prev = self.x_from_true_month(n - 1)
        x_next = self.x_from_true_month(n + 1)

        Y2, M2, is_leap = self.label_from_true_month(n)

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
            "Mstar_rightend": self.mstar_from_true_month(n),
            "x": x,
            "x_prev": x_prev,
            "x_next": x_next,
            "decoded": {"Y": Y, "M": M},
            "label_from_true_month": {"Y": Y2, "M": M2, "is_leap": is_leap},
            "repeat_test": {
                "x==x_next": (x == x_next),
                "x==x_prev": (x == x_prev),
                "leap_labeling": self.p.leap_labeling,
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