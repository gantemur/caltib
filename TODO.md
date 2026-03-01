# Caltib Architecture Refactor Plan

This document tracks the 5-step migration to the fully modular `CalendarEngine` architecture (separating discrete arithmetic from continuous kinematics).

## Step 1: Lay the Foundation (Zero Risk)
- [x] Create `caltib/engines/interfaces.py`.
- [x] Define `MonthEngineProtocol` (handles labels, years, leap status).
- [x] Define `DayEngineProtocol` (handles $x \to t2000$ kinematics).
- [x] Define `CalendarEngineProtocol` (handles the Civil $JDN$ boundary).
- [x] Document the $x = 30n + d$ unified coordinate and J2000.0 TT standard.

## Step 2: The Month Migration (Low Risk)
- [ ] Rename `caltib/engines/rational_month.py` to `caltib/engines/arithmetic_month.py`.
- [ ] Rename `RationalMonthParams` to `ArithmeticMonthParams`.
- [ ] Rename `RationalMonthEngine` to `ArithmeticMonthEngine`.
- [ ] Implement `epoch_k` and `sgang1` properties.
- [ ] Implement `first_lunation(year) -> int`.
- [ ] Implement `get_lunations(year, month) -> list[int]`.
- [ ] Implement `month_label(n) -> dict`.
- [ ] Update `caltib/engines/specs.py` to import and use the new Arithmetic classes.

## Step 3: The Day Kinematics (Medium Risk)
- [ ] **Traditional Engine (`trad_day.py`)**
  - [ ] Add `epoch_k` property.
  - [ ] Refactor solvers to accept absolute $x$ instead of $(n, d)$.
  - [ ] Implement `mean_date(x)`, `true_date(x)`, `mean_sun(x)`, `true_sun(x)` returning Days since J2000.0.
  - [ ] Implement `get_x_from_t2000(t2000) -> int`.
- [ ] **Rational Engine (`rational_day.py`)**
  - [ ] Add `epoch_k` property.
  - [ ] Refactor Picard solver and boundaries to use absolute $x$.
  - [ ] Ensure all internal tracking strictly uses J2000.0 coordinates.
  - [ ] Implement `get_x_from_t2000(t2000) -> int`.

## Step 4: The Orchestrator (The Integration)
- [ ] Create `caltib/engines/calendar.py`.
- [ ] Build the `CalendarEngine` class that takes a `MonthEngine` and `DayEngine`.
- [ ] Implement epoch synchronization: $\Delta k = \text{Day.epoch\_k} - \text{Month.epoch\_k}$.
- [ ] Implement `from_jdn(jdn) -> dict`:
  - [ ] Convert JDN to internal $t2000$.
  - [ ] Call `DayEngine.get_x_from_t2000(t2000)`.
  - [ ] Extract $n = \lfloor x / 30 \rfloor$ and $d = x \pmod{30}$.
  - [ ] Call `MonthEngine.month_label(n)`.
- [ ] Implement `to_jdn(year, month, is_leap, day) -> int`:
  - [ ] Call `MonthEngine.get_lunations(year, month)` to find $n$.
  - [ ] Calculate $x = 30n + d$.
  - [ ] Call `DayEngine.true_date(x)` to find physical $t2000$.
  - [ ] Convert physical dawn/boundary to civil integer JDN.

## Step 5: The Purge (Cleanup)
- [ ] Update `caltib/cli.py` and `caltib/api.py` to route through the new `CalendarEngine`.
- [ ] Verify all tests and scatter plots pass.
- [ ] Delete the obsolete `caltib/engines/rational.py`.
- [ ] Rename `caltib/engines/fp.py` to `caltib/engines/fp_day.py` in preparation for L4/L5 development.

## Future / Backlog
- [ ] Build `FloatDayEngine` (L4-L5) in `fp_day.py`.
- [ ] Build `AttributeEngine` (Elements, Animals, Weekdays).
- [ ] Build `PlanetsEngine` (JPL / Siddhantic ephemerides).


## Phase 1: Post-Refactor Verification & Diagnostics
- [ ] **Run Core Ephemeris Plots:** Execute `caltib ephem raw-offsets`, `caltib ephem anomaly-trads`, and `caltib ephem drift-trads` to guarantee the J2000.0 TT coordinate shifts generate the exact same visual data as the pre-refactor monolith.
- [ ] **Verify Civil Boundaries:** Test the skipped/repeated day logic inside `CalendarEngine._build_civil_month` against a known tricky traditional month (e.g., a month with consecutive skipped days or boundary edge cases).
- [ ] **Audit Diagnostics API:** Ensure all diagnostic scripts in `src/caltib/diagnostics/` are fully updated to consume the new `api.py` outputs and do not rely on legacy properties.

## Phase 2: The Continuous Month Engine (`RationalMonthEngine`)
- [ ] **Draft the Math Layer:** Port the rational lunisolar model to handle continuous month boundaries. This engine will replace the discrete arithmetic table lookups with pure kinematic intersections.
- [ ] **Implement `MonthEngineProtocol`:** Create `RationalMonthEngine` in `src/caltib/engines/rational_month.py` ensuring it exposes `get_lunations()`, `get_month_info()`, etc.
- [ ] **Update Factory:** Add the `isinstance(spec.month_params, RationalMonthParams)` hook into `factory.py`.
- [ ] **Draft Spec:** Create an `L4` calendar spec in `specs.py` that utilizes the new `RationalMonthEngine`.

## Phase 3: High-Precision Floating-Point & Ephemeris (L4-L6)
- [ ] **L5 Floating-Point Day Engine:** Implement `FloatDayEngine` in `fp_day.py` using minimax polynomial approximations and full-precision hex-floats to break free of rational fractional limits.
- [ ] **L6 JPL Ephemeris Integration:** Implement `EphDayEngine` and `EphMonthEngine` in `eph_day.py`. This tier will directly query the DE422 ephemeris (or a Siddhantic equivalent) to serve as the ultimate truth layer for the calendar protocols.
- [ ] **Update Factory for Eph/FP:** Wire the new day models into `factory.py` and update the `EngineSpec(kind="...")` literal types as necessary.

