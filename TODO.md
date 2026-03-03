# caltib Project Roadmap

## 🎯 Active Development Tracks

### 1. Web Application & Documentation (The Frontend)
- [ ] **Polish Website:** Finalize the static HTML documentation site, ensuring all architectural concepts, reform methodologies, and laboratory tools are clearly explained.
- [ ] **Build the Web Calendar App (`app.html`):**
  - [ ] Implement a full-featured UI with Day, Month, and Year views similar to modern calendar applications.
  - [ ] Integrate PyScript/WebAssembly to load the zero-dependency core engine directly in the browser.
  - [ ] Build specialized features, such as a chronological list generator for Losar / Tsagaan Sar dates over arbitrary year ranges.

### 2. High-Precision Floating-Point Kinematics (L4 & L5)
- [ ] **Develop `FloatDayEngine`:** Implement strictly reproducible floating-point kinematics using Chebyshev minimax polynomials to approximate transcendental functions.
- [ ] **Develop `FloatMonthEngine`:** Bridge the rational month constants with the floating-point day boundaries.
- [ ] **Implement FP Sunrise Models:** Develop high-precision, floating-point spherical sunrise models (incorporating the Equation of Time) to replace or supplement the rational L3 sunrise logic.
- [ ] **Implement Solvers:** Integrate fixed-iteration Picard and Steffensen solvers for the floating-point anomalies.

### 3. Numerical Ephemeris Integration (L6)
- [ ] **Develop `EphDayEngine`:** Create the ultimate truth layer by directly querying JPL DE422 `.bsp` files to map physical syzygies.
- [ ] **Develop `EphMonthEngine`:** Allow the month boundaries and intercalation logic to be driven natively by ephemeris data rather than analytical mean motions.

### 4. Phenomenological & Astrological Engines
- [ ] **Develop `AttributeEngine`:** Map the discrete chronological grids to traditional Tibetan/Mongolian attributes (Elements, Animals, Trigrams/Mewa, Lunar Mansions, Weekdays).
- [ ] **Develop `PlanetsEngine`:** Implement both the historical Siddhantic planetary mathematical models and a modern routing layer to fetch true planetary positions via ephemeris.

### 5. Advanced Diagnostics Laboratory
- [ ] **Month Engine Diagnostics:** Write specialized `caltib diag` tools to visualize month-level behavior, such as intercalation triggers, drift in the leap-month assignment, and rational vs. ephemeris month boundaries.
- [ ] **Sunrise & Latitude Diagnostics:** Write tools to compare the civil phase shifts caused by localized spherical sunrise models across different geographic latitudes (e.g., Lhasa vs. Ulaanbaatar).

---

## ✅ Completed Milestones
* **Architecture Refactor:** Successfully decoupled discrete arithmetic from continuous kinematics using the `CalendarSpec` polymorphic factory.
* **Rational Engines (L0-L3):** Implemented zero-FPU continuous rational fractions, Picard solvers, and integer sine-tables.
* **Universal Civil Generator:** Built the orchestrator to convert continuous $x$-coordinates into discrete JDN boundaries, accurately handling skipped/duplicated days based on geographical location.
* **Unified Diagnostics Lab:** Built the comprehensive suite for measuring secular drift, variance, equinox precession, and syzygy offsets against JPL DE422 truth.
* **Design Tools:** Implemented continued fraction generators and Chebyshev minimax polynomial calculators for engine design.