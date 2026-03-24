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

-   **Historical Fidelity**

    ---

    Exact implementations of the Phugpa, Tsurphu, Bhutan, Mongol, and Karana traditions. Faithfully reproduces regional intercalations and historical epoch constants.

-   **A Spectrum of Reforms**

    ---

    Advances from zero-FPU continuous rational fractions using integer sine-tables (L0–L3), through strictly reproducible floating-point kinematic models using Chebyshev minimax approximations (L4–L5), culminating in high-fidelity JPL DE422 ephemeris evaluations (L6).

-   **Universal Civil Generator**

    ---

    Built on the absolute continuous lunar day count. It seamlessly evaluates continuous orbital syzygies against localized spherical sunrise models (without defaulting to the Equation of Time) to accurately handle discrete skipped and duplicated days globally.

-   **Automated Design Lab**

    ---

    Not just a calculator, but a complete mathematical laboratory for calendrical research. Use the comprehensive CLI to derive optimal continued fractions for mean motions and Chebyshev minimax polynomials for strictly reproducible floating-point kinematics.

</div>
---

## Installation & Modular Extras

The core `caltib` package is a lightweight, pure-Python library with zero external dependencies, perfect for web deployment and embedded systems. Advanced design and diagnostic capabilities are available through optional subpackages.

**Core Package** (Traditional engines and Reform Tiers L0–L5)
```bash
pip install caltib
```

**[tools]** (The Design & Diagnostics Lab)
```bash
pip install "caltib[tools]"
```

**[ephemeris]** (JPL DE422 integration for the L6 engine)
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
# (Requires [ephemeris] extra and JPL DE422 files)
l6 = caltib.get_calendar("l6")
l6_info = l6.day_info(date(2026, 2, 21))
```