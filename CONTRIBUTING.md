# Contributing to caltib

Read [ARCHITECTURE.md](ARCHITECTURE.md) before changing calendar behavior. Keep
changes small and check the affected calendar semantics with regression tests.

- Preserve the month/day/orchestrator separation: month engines assign labels
  and leap months, day engines assign physical times and civil days, and the
  calendar orchestrator connects them.
- Keep `delta_k` epoch alignment explicit. Month and day engines can use
  different lunation origins; the orchestrator translates them with
  `n_d = n_m + delta_k`.
- Distinguish published parameters and epoch conventions from normalized
  internal parameters. Reproducing a published calendar and comparing normalized
  models are different tasks; preserve the intended interpretation.
- Treat repeated or skipped days separately from leap months. A repeated date
  can have two civil occurrences, so a forward conversion may be ambiguous even
  when the inverse conversion identifies each occurrence.
- Handle calendar boundaries, inverse maps, and historical conventions with
  care. Avoid broad refactors of sensitive calendrical logic without evidence
  that the existing semantics remain intact.
