from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from typing import List

import caltib


def parse_date(s: str) -> date:
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def random_date(start: date, end: date) -> date:
    span = (end - start).days
    return start + timedelta(days=random.randint(0, span))


def parse_engines(s: str) -> List[str]:
    # "phugpa,tsurphu,mongol" -> ["phugpa", ...]
    return [x.strip() for x in s.split(",") if x.strip()]


def roundtrip_test(
    engine: str,
    N: int,
    start: date,
    end: date,
    seed: int,
    *,
    max_failures: int,
) -> int:
    random.seed(seed)
    failures = 0

    for _ in range(N):
        d0 = random_date(start, end)

        info = caltib.day_info(d0, engine=engine, debug=False)
        t = info.tibetan

        back_occ = caltib.to_gregorian(t, engine=engine, policy="occ")
        if not back_occ or back_occ[0] != d0:
            failures += 1
            print("\nFAIL (occ)")
            print("engine:", engine)
            print("d0:", d0)
            print("tib:", t)
            print("back_occ:", back_occ)
            print("day_info(debug=True):", caltib.day_info(d0, engine=engine, debug=True))
            if failures >= max_failures:
                return failures

        back_all = caltib.to_gregorian(t, engine=engine, policy="all")
        if d0 not in back_all:
            failures += 1
            print("\nFAIL (all)")
            print("engine:", engine)
            print("d0:", d0)
            print("tib:", t)
            print("back_all:", back_all)
            print("day_info(debug=True):", caltib.day_info(d0, engine=engine, debug=True))
            if failures >= max_failures:
                return failures

    return failures


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Random round-trip tests: gregorian -> tibetan -> gregorian.")
    p.add_argument("--engines", type=str, default="phugpa,tsurphu,mongol,bhutan,karana",
                   help="Comma-separated engine list.")
    p.add_argument("--N", type=int, default=2000, help="Trials per engine.")
    p.add_argument("--start", type=str, default="1600-01-01", help="Start date YYYY-MM-DD.")
    p.add_argument("--end", type=str, default="2400-12-31", help="End date YYYY-MM-DD.")
    p.add_argument("--seed", type=int, default=123, help="RNG seed.")
    p.add_argument("--max-failures", type=int, default=5, help="Stop after this many failures per engine.")
    args = p.parse_args(argv)

    engines = parse_engines(args.engines)
    start = parse_date(args.start)
    end = parse_date(args.end)

    if end < start:
        raise SystemExit("--end must be >= --start")

    total_fail = 0
    for eng in engines:
        print(f"Testing {eng} ...")
        f = roundtrip_test(eng, N=args.N, start=start, end=end, seed=args.seed, max_failures=args.max_failures)
        total_fail += f

    if total_fail == 0:
        print("All round-trip tests passed.")
        return 0

    print(f"Round-trip failures: {total_fail}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())