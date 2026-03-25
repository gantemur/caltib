# High-Precision Tibetan Calendrical Math

A rigorous Python library that unifies 15th-century historical algorithms with modern astrophysics. `caltib` spans pure-integer arithmetic, continuous rational-fraction kinematics, strictly reproducible float-day models, and JPL numerical integrations under a single, elegant API.

[Live Calendar &rarr;](app.html){: .md-button .md-button--primary }
[Diagnostic Dashboard &rarr;](diag.html){: .md-button }
[GitHub](https://github.com/gantemur/caltib){: .md-button }

---

## The caltib Laboratory

<div class="grid cards" markdown>

-   **📅 [Interactive Web Calendar](app.html)**

    ---

    A fully localized, universal civil calendar generator. Explore localized Tithi generation across multiple historical and modern reform engines instantly in your browser.

-   **📈 [Diagnostic Dashboard](diag.html)**

    ---

    A deep-time analytical laboratory. Plot secular drift, evaluate continuous solar kinematics, and visually map mathematical variance across millennia.

</div>

---

## Key Features

<div class="grid cards" markdown>

-   :material-history: **Historical Fidelity**

    ---

    Exact implementations of the Phugpa, Tsurphu, Bhutan, Mongol, and Karana traditions. Faithfully reproduces regional intercalations and historical epoch constants.

-   :material-chart-timeline-variant: **A Spectrum of Reforms**

    ---

    Advances from zero-FPU continuous rational fractions using integer sine-tables (L0–L3), through strictly reproducible floating-point kinematic models using minimax polynomials (L4–L5).

-   :material-earth: **Universal Civil Generator**

    ---

    Built on the absolute continuous lunar day count with localized spherical sunrise to accurately handle discrete skipped and duplicated days globally.

-   :material-flask-outline: **Automated Design Lab**

    ---
    
    A complete mathematical laboratory for calendrical research. Use the CLI to derive optimal continued fractions and Chebyshev minimax polynomials.

</div>
---

## Installation & Modular Extras

The core `caltib` package is a lightweight, pure-Python library with zero external dependencies, perfect for web deployment and embedded systems. Advanced design and diagnostic capabilities are available through optional subpackages.

**Core Package** (Traditional engines and Reform Tiers L0–L5)
```bash
pip install caltib
```

**[tools]** (The Design & Diagnostics Lab)
Provides the CLI and internal tools for measuring secular drift, calculating minimax polynomials, and analyzing calendar variance.
```bash
pip install "caltib[tools]"
```

**[ephemeris]** (JPL DE422 High-Precision Truth Data)
Required for deep-time secular drift analysis and the upcoming L6 engine. Provides the bridge between traditional algorithms and JPL DE422 numerical integrations.
```bash
pip install "caltib[ephemeris]"
```

---

## API Quickstart

The unified `caltib` API allows you to switch between 15th-century historical logic and 21st-century astrophysics with a single parameter change.

```python
from datetime import date
import caltib
from caltib.engines.specs import LOC_ULAANBAATAR

# 1. Standard traditional lookup
info = caltib.day_info(date(2026, 2, 21), engine="mongol")
print(f"Traditional Mongol Tithi: {info.tibetan.tithi}")

# 2. Modern L3 Reform localized to Ulaanbaatar
# (Uses fixed-iteration rational Picard solvers and spherical sunrise)
ub_engine = caltib.get_calendar("l3", location=LOC_ULAANBAATAR)
ub_info = ub_engine.day_info(date(2026, 2, 21))
print(f"Localized L3 Tithi: {ub_info.tibetan.tithi}")

# 3. The L6 Numerical Engine
# (Roadmap: Requires [ephemeris] extra and JPL DE422 files)
# l6 = caltib.get_calendar("l6")
# l6_info = l6.day_info(date(2026, 2, 21))
```

!!! info "Level 6 (L6) Status"
    The **L6 Numerical Engine** is currently an experimental roadmap feature. While the underlying `[ephemeris]` dependency is fully implemented for use in **Design & Diagnostics**, the L6 calendrical engine is still under development.