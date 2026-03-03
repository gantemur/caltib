caltib
High-Precision Tibetan Calendrical Math

caltib is a rigorous Python library designed to unify 15th-century historical algorithms with 21st-century astrophysics. It provides a polymorphic framework for evaluating traditional lunisolar calendars alongside modern mathematical reforms.

🚀 Live Demo
Experience the library in action without installing anything. The web calendar runs completely client-side via WebAssembly:
Launch the caltib Web App

✨ Key Features
Unified API: Evaluate traditional engines (Phugpa, Mongol, Tsurphu, etc.) and modern reforms (L0–L6) using a single, elegant interface.

Progressive Reforms: A tiered sequence of engines advancing from pure-integer mean motion (L0) and fixed-iteration Picard solvers (L1–L3) to strictly reproducible floating-point models (L4–L5) and JPL-powered numerical integration (L6).

Strict Reproducibility: L0–L5 engines utilize integer sine-tables or Chebyshev minimax polynomials to ensure bit-for-bit consistency across all CPU architectures.

Localized Physics: Support for geographical location injection (e.g., Lhasa vs. Montreal) to handle spherical sunrise boundaries and civil day-numbering.

Design & Diagnostics Lab: A professional-grade toolkit for designing new calendar parameters via continued fractions and analyzing secular drift over millennia.

📦 Installation
caltib is designed to be lightweight. The core package has zero external dependencies and is perfect for embedded or web use.

Bash
# Core: Traditional engines & Reform Tiers L0-L5
pip install caltib

# Tools: Diagnostic charting & parameter design (requires NumPy/Matplotlib)
pip install "caltib[tools]"

# Ephemeris: JPL DE422 integration & L6 engine (requires Skyfield/jplephem)
pip install "caltib[ephemeris]"
🛠 Quickstart
Basic Day Query
Python
from datetime import date
import caltib

# Standard traditional lookup
info = caltib.day_info(date(2026, 2, 21), engine="mongol")
print(f"Mongol Tithi: {info.tibetan.tithi}")
Advanced Localized Reform
Python
from caltib.engines.specs import LOC_MONTREAL

# Build an L3 engine localized to Montreal coordinates
# L3 uses fixed-iteration rational Picard solvers and spherical sunrise.
engine = caltib.get_calendar("l3", location=LOC_MONTREAL)
info = engine.day_info(date(2026, 2, 21))
📊 Diagnostics & Design
The library includes a "Mathematical MRI" suite to analyze calendar accuracy.

Secular Drift: Track how sidereal calendars decouple from the tropical equinox over 1,500 years.

Variance Mapping: Visualize the "exploding sigma" of traditional anomaly approximations.

Rational Design: Derive optimal convergents for new calendar architectures.

Bash
# Analyze secular acceleration against JPL DE422 truth
caltib diag analysis --engine mongol --ephem de422
📝 License
Distributed under the MIT License. Created by Tsogtgerel Gantumur.

Would you like me to generate the updated app.html to ensure the PyScript configuration matches these new subpackage names?