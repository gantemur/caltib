# Developer Notes

This file records implementation details, deferred design issues, and architectural decisions
that are easy to forget but important for maintaining the calendar code correctly.

The intended audience is a new contributor who may not yet know the internal logic of the
project.

---

## 1. Calendar architecture: why the orchestrator exists

The calendar system is intentionally split into three layers:

1. **Month engine**
   - Decides the lunation skeleton.
   - Resolves leap months and month labels.
   - Works in terms of a lunation index, usually denoted `n_m`.

2. **Day engine**
   - Computes civil-day assignment from tithi boundaries.
   - Works in terms of a lunation index for the day calculation, usually denoted `n_d`.
   - Produces repeated/skipped days by comparing tithi boundaries to civil-day boundaries.

3. **Orchestrator (`calendar.py`)**
   - Glues the month and day engines together.
   - Applies the alignment shift
     ```python
     n_d = n_m + delta_k
     ```
     because the month and day engines may use different internal epoch choices.
   - Provides user-facing methods such as:
     - `from_jdn`
     - `to_jdn`
     - `to_gregorian`
     - `day_info`
     - `month_info`
     - `year_info`

This separation is deliberate. The month logic and the day logic are mathematically different,
and the project must support the possibility that they use different epochs or even different
internal conventions.

---

## 2. Important principle: published state vs normalized underlying state

A recurring source of confusion in this project is the distinction between:

- **Published state**
  - The epoch data as presented in published calendrical sources or engine specifications.
  - Example fields may include `Y0`, `M0`, `beta_star`, etc.
  - These values are sometimes chosen for human-facing convention, not because they are the
    most natural internal coordinates.

- **Normalized underlying state**
  - The internally consistent state obtained when one strips off publication-layer overrides
    and looks only at the mathematical lunation structure.
  - This is the natural state for geometric derivations, reconstruction of `sgang1`, and
    other structural analyses.

These are not always identical.

### Example: Phugpa E1927

A particularly tricky case is the Phugpa 1927 epoch.

It may be *published* with something like `M0 = 3`, but the underlying lunation alignment shows
that the epoch sits at a place where the actual structural month count behaves as though the
epoch start belongs to the previous labeled month. In other words, the published month label is
an override, while the underlying true-month geometry tells a slightly different story.

This distinction matters when:
- reconstructing `sgang1`,
- deducing `beta_star`,
- translating epochs,
- comparing traditions after forcing them to a common target epoch.

The general rule is:

- Use the **published state** when the goal is to reproduce the published calendar.
- Use the **normalized state** when the goal is structural analysis of the underlying engine.

Do **not** mix these two perspectives accidentally.

---

## 3. Current status of `calendar.py`

At present, the orchestrator is considered structurally sound.

In particular:
- the month/day split is correct,
- the `delta_k` alignment mechanism is necessary and intentional,
- `from_jdn()` performs a monotone search and is conceptually correct,
- `to_gregorian()` is acceptable for current use,
- `month_info()` and `year_info()` are conceptually aligned with the architecture.

One concrete bug involving attribute lookup in `_build_month_info_from_n()` was already fixed:
the code must guard against `self.attr is None` before calling attribute accessors.

That fix is necessary and should remain in place.

---

## 4. Deferred issue A: `to_jdn()` does not fully resolve repeated days

### Short version

This is a real design limitation, but not currently treated as a blocking bug.

### The issue

The calendar can contain **repeated civil dates**. This happens when a tithi spans two civil days,
so the same Tibetan day label appears twice.

The inverse map `from_jdn()` already knows about this:
- it can distinguish occurrences,
- it can report whether a day is repeated,
- it can assign something like `occ = 1` or `occ = 2`.

However, the forward map `to_jdn(year, month, is_leap, day)` currently does **not** have a way to
specify which occurrence is intended when the Tibetan date is repeated.

So the current asymmetry is:

- `from_jdn(JDN)` can distinguish repeated dates,
- but `to_jdn(...)` cannot always uniquely choose between the first and second occurrence.

### Why this matters

If a user asks for the Gregorian/JDN corresponding to a repeated Tibetan date, there are in fact
two correct answers.

Without an occurrence selector, the function must do one of the following:
- silently choose one,
- raise an ambiguity error,
- or adopt some implicit policy.

At present, this issue is intentionally deferred.

### Why it was not changed immediately

The current codebase is sensitive, and unnecessary edits to the orchestrator may introduce
regressions. Since many practical workflows do not require forward resolution of repeated dates,
the issue was judged real but non-urgent.

### Recommended future solution

Extend `to_jdn()` with an explicit occurrence or policy parameter, for example:

```python
def to_jdn(self, year, month, is_leap, day, occ=None, policy="raise"):
    ...
```

Possible policies:

- `policy="raise"`: raise if the Tibetan date is repeated and `occ` is not provided,
- `policy="first"`: choose the first occurrence,
- `policy="second"`: choose the second occurrence,
- `policy="occ"`: require `occ=1` or `occ=2`.

This would make the forward map more symmetric with `from_jdn()`.

### Important note

This is a feature-completeness issue, not necessarily a sign that the existing results are wrong.  
It only matters when the caller wants to disambiguate duplicated Tibetan dates in the forward direction.

## 5. Deferred issue B: repeated month-resolution logic in `calendar.py`

### Short version

This is cleanup, not a correctness bug.

### The issue

Several methods in `calendar.py` perform the same logical task:

- call the month engine to get the lunation(s) corresponding to a labeled month,
- if there is one lunation, require `is_leap=False`,
- if there are two lunations, resolve which one is leap according to the current leap-labeling convention.

This logic appears in more than one place, such as:

- `to_jdn()`,
- `to_gregorian()`,
- `month_info()`.

### Why this matters

Duplicated logic is risky because:

- later edits may fix one copy but not another,
- subtle convention changes may drift across methods,
- debugging becomes harder because the same idea is implemented repeatedly.

### Why it was not changed immediately

This duplication is annoying but harmless as long as all copies remain consistent.  
Since the orchestrator is sensitive, it was judged wiser not to refactor it immediately.

### Recommended future solution

Introduce a helper such as:

```python
def _resolve_lunation(self, year: int, month: int, is_leap: bool) -> int:
    ...
```

This helper should:

- obtain the candidate lunation list from the month engine,
- reject impossible leap flags,
- apply `self.leap_labeling`,
- return the unique month-engine lunation index.

Then all user-facing methods should call this helper instead of carrying their own copy of the logic.

### Important note

This is primarily a maintenance/readability issue, not a demonstrated source of wrong output.

## 6. Why `delta_k` must remain in the protocol

A tempting simplification is to remove the distinction between `n_m` and `n_d` and force the month
and day engines to share a single epoch.

That should not be done casually.

The project explicitly allows for:

- month engines and day engines with different epoch normalizations,
- historical published forms where month labels are overridden relative to the underlying structure,
- comparisons between traditions or reform layers where month and day modules are intentionally
  aligned only through a known shift.

Therefore the orchestrator-level alignment parameter

```python
delta_k
```

is not accidental boilerplate. It is part of the architecture.

Any future refactor must preserve the ability to express:

- a month-engine lunation index `n_m`,
- a day-engine lunation index `n_d`,
- and the translation `n_d = n_m + delta_k`.

## 7. Guidance for future contributors

When editing the calendar orchestrator, follow these rules:

1. **Prefer the smallest possible change.**  
   The current file already works, and broad rewrites are risky.

2. **Do not confuse publication conventions with internal structure.**  
   Ask whether the function is trying to:
   - reproduce a published calendar, or
   - analyze normalized underlying geometry.

3. **Respect the month/day separation.**  
   If a bug appears in date conversion, first identify whether it belongs to:
   - month labeling,
   - day assignment,
   - or orchestrator alignment.

4. **Treat repeated days and leap months as independent phenomena.**  
   Leap months come from the month engine.  
   Repeated/skipped days come from the day engine.  
   They interact in the calendar, but they are not the same mechanism.

5. **Be careful with inverse maps.**  
   Forward maps may be ambiguous even when inverse maps are not.  
   Repeated Tibetan days are the main example.

6. **Avoid refactoring for elegance unless there is a concrete benefit.**  
   This is not generic application code; it encodes delicate calendrical semantics.

## 8. Minimal future to-do list

These items are intentionally deferred, not forgotten.

### High priority

Keep the `self.attr is not None` guard in `_build_month_info_from_n()`.

### Medium priority

Extend `to_jdn()` so repeated Tibetan dates can be resolved explicitly.

### Low priority

Factor duplicated month-resolution code into `_resolve_lunation(...)`.

## 9. Suggested inline reminders in code

Short inline comments are useful near the relevant functions. For example:

```python
# TODO: repeated-day occurrence handling in to_jdn() is intentionally deferred.
```

and near repeated month-resolution logic:

```python
# TODO: consider centralizing month-resolution logic in a helper; deferred to avoid risky refactor.
```

These comments are not replacements for this note. They are just local signposts.

## 10. Final summary

The main deferred point is this:

The current orchestrator is basically correct.  
One real missing feature remains: forward disambiguation of repeated days in `to_jdn()`.  
One cleanup opportunity remains: centralizing month-resolution logic.  
Both were intentionally deferred to avoid destabilizing a sensitive file.

If a future contributor touches `calendar.py`, they should first read this file and decide whether
they are fixing a real calendrical bug, adding a missing feature, or merely refactoring for style.  
Those are very different levels of risk.