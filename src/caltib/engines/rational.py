from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from typing import Any, Dict, List, Literal, Optional, Tuple

from ..core.engine import CalendarEngine
from ..core.time import to_jdn, from_jdn
from ..core.types import DayInfo, EngineId, TibetanDate

from .rational_month import RationalMonthEngine, RationalMonthParams
from .rational_day import RationalDayEngine, RationalDayParams, CivilDay


@dataclass(frozen=True)
class RationalSpec:
    id: EngineId
    month: RationalMonthParams
    day: RationalDayParams
    meta: Optional[Dict[str, Any]] = None


class RationalEngine(CalendarEngine):
    def __init__(self, spec: RationalSpec):
        self.spec = spec
        self.month = RationalMonthEngine(spec.month)
        self.day = RationalDayEngine(spec.day)

    def info(self) -> Dict[str, Any]:
        return {
            "family": self.spec.id.family,
            "name": self.spec.id.name,
            "version": self.spec.id.version,
            "numeric": "rational",
            "epoch": {"Y0": self.month.p.Y0, "M0": self.month.p.M0},
            "P": self.month.p.P,
            "Q": self.month.p.Q,
            "ell": self.month.p.ell,
            "beta_star": self.month.p.beta_star,
            "tau": self.month.p.tau,
            "gamma_shift": self.month.p.gamma_shift,
            "beta_int": self.month.p.beta_int,
            "trigger_set": list(self.month.p.trigger_set),
            "leap_labeling": self.month.p.leap_labeling,
        }

    # -------- month debug API --------
    def month_info(self, Y: int, M: int, *, debug: bool = False) -> Dict[str, Any]:
        out = self.month.debug_label(Y, M)
        if debug:
            out["engine"] = self.info()
            if self.spec.meta:
                out["meta"] = dict(self.spec.meta)
        return out

    def month_from_n(self, n: int, *, debug: bool = False) -> Dict[str, Any]:
        out = self.month.debug_true_month(n)
        if debug:
            out["engine"] = self.info()
            if self.spec.meta:
                out["meta"] = dict(self.spec.meta)
        return out

    def _find_lunation(self, jd: int) -> int:
        """
        Robust lunation finder using monotone bounds:
        first_jd(n)=end_jd(30,n-1)+1, last_jd(n)=end_jd(30,n).
        """
        p = self.day.p
        n = ((Fraction(jd, 1) - p.m0) / p.m1)
        n = n.numerator // n.denominator  # floor seed

        for _ in range(5000):
            first_jd = self.day.end_jd(30, n - 1) + 1
            last_jd = self.day.end_jd(30, n)
            if jd < first_jd:
                n -= 1
            elif jd > last_jd:
                n += 1
            else:
                return n
        raise RuntimeError(f"Could not bracket lunation for jd={jd}")
   

    def day_info(self, d: date, *, debug: bool = False) -> DayInfo:
        jd = to_jdn(d)
        n = self._find_lunation(jd)

        cm = self.day.civil_month(n)
        idx = next(i for i, x in enumerate(cm) if x.jd == jd)
        cd = cm[idx]

        # occurrence of this label within the month (1st or 2nd)
        occ = 1 + sum(1 for x in cm[:idx] if x.label == cd.label)

        status: Literal["normal", "duplicated"] = "duplicated" if occ == 2 else "normal"

        Y, M, is_leap_month = self.month.label_from_true_month(n)

        t = TibetanDate(
            engine=self.spec.id,
            tib_year=Y,
            month_no=M,
            is_leap_month=is_leap_month,
            tithi=cd.label,
            occ=occ,
        )

        dbg = None
        if debug:
            dbg = {
                "jdn": jd,
                "n": n,
                "civil": {"repeated": cd.repeated, "skipped": cd.skipped},
                "engine": self.info(),
            }
            if self.spec.meta:
                dbg["meta"] = dict(self.spec.meta)

        return DayInfo(civil_date=d, engine=self.spec.id, tibetan=t, status=status, debug=dbg)

    def to_gregorian(self, t: TibetanDate, *, policy: str = "all") -> List[date]:
        """
        Map a TibetanDate label back to civil dates.

        policy:
        - "all":   return all civil dates in that (Y,M,leap) month with the given tithi label
        - "occ":   use t.occ (1 or 2) to select the occurrence (recommended if you want a single date)
        - "first": select first occurrence (if any)
        - "second":select second occurrence (if any)
        - "raise": require exactly one match, else raise
        """
        if policy not in ("all", "occ", "first", "second", "raise"):
            raise ValueError("policy must be one of: all, occ, first, second, raise")

        n = self.month.true_month(
            t.tib_year,
            t.month_no,
            is_leap_month=t.is_leap_month,
        )

        cm = self.day.civil_month(n)
        jds = [cd.jd for cd in cm if cd.label == t.tithi]

        if policy == "occ":
            k = t.occ - 1
            jds = jds[k:k+1]

        elif policy == "first":
            jds = jds[:1]

        elif policy == "second":
            jds = jds[1:2]

        elif policy == "raise":
            if len(jds) != 1:
                raise ValueError(f"Expected exactly one match for {t}, got {len(jds)}")
            # keep jds as-is

        # policy == "all" leaves jds unchanged
        return [from_jdn(j) for j in jds]

    def explain(self, d: date) -> Dict[str, Any]:
        info = self.day_info(d, debug=True)
        return {"engine": self.info(), "debug": info.debug}


def build_rational_engine(spec: RationalSpec) -> RationalEngine:
    return RationalEngine(spec)