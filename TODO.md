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