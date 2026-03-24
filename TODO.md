# caltib Project Roadmap

## 🎯 Active Development Tracks

### 1. Web Application & Documentation
- [ ] **Implement Open/Save Configuration:** Add functionality to export and import complete custom calendar specifications (via JSON) directly within the `app.html` web interface.
- [ ] **Automated Documentation Pipeline:** Implement docstring-driven documentation using MkDocs (with the Material theme) and `mkdocstrings`. Set up a GitHub Action to automatically build and deploy the API reference to GitHub Pages on `main` branch pushes.

### 2. Numerical Ephemeris Integration (L6)
- [ ] **Develop `EphDayEngine` (L6):** Create the ultimate truth layer by implementing L6, allowing users to toggle between **JPL DE422 `.bsp` files** and the **internal analytical reference library** as optional sources for mapping physical syzygies.
- [ ] **Develop `EphMonthEngine`:** Allow the month boundaries and intercalation logic to be driven natively by continuous ephemeris data rather than analytical mean motions.

### 3. Phenomenological & Planetary Engines
- [ ] **Write Rational Planet Engine:** Implement the pure-rational historical Siddhantic planetary mathematical models (fast/slow motions, dal-bar, etc.).

### 4. Advanced Diagnostics Laboratory & Validation
- [ ] **Near-Tie & Boundary Validation:** Ensure all extreme mathematical boundary cases are correct. Write dedicated, rigorous test scripts targeting near-tie scenarios (e.g., borderline leap months, micro-second skipped/repeated day boundaries).
- [ ] **Integrate Exotic Epochs:** Extract and implement the "exotic" historical epoch data and parameters from Edward Henning's source code/pages to use as hardened validation baselines.
- [ ] **Web-Diag Enhancements:** Add the Equinox Solar Longitude drift analysis tool directly into the `diag.html` web dashboard.

---

## ✅ Completed Milestones
* **Architecture Refactor:** Successfully decoupled discrete arithmetic from continuous kinematics using the `CalendarSpec` polymorphic factory.
* **Rational Engines (L0-L3):** Implemented zero-FPU continuous rational fractions, Picard solvers, and integer sine-tables.
* **Floating-Point Engines (L4-L5):** Developed strictly reproducible FP kinematics using Chebyshev minimax polynomials, floating-point spherical sunrise models, and Picard/Steffensen solvers.
* **Universal Civil Generator:** Built the orchestrator to convert continuous $x$-coordinates into discrete JDN boundaries, accurately handling skipped/duplicated days based on geographical location.
* **Web Calendar Frontend:** Built `app.html` with full-featured Day/Month/Year views, chronological Losar/Tsagaan Sar generators, and fully integrated client-side PyScript/WebAssembly execution.
* **Attribute Engine:** Mapped the discrete chronological grids to traditional Tibetan/Mongolian attributes (Elements, Animals, Trigrams/Mewa, Lunar Mansions, Weekdays).
* **Unified Diagnostics Lab:** Built the comprehensive suite for measuring secular drift, variance, equinox precession, and syzygy offsets against JPL DE422 truth.
* **Diagnostic Enhancements:** Completed month-level diagnostics (intercalation triggers, drift) and spherical sunrise/latitude geographic phase shift comparisons.
* **Design Tools:** Implemented continued fraction generators and Chebyshev minimax polynomial calculators for engine design.