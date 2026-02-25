# caltib (skeleton)

A Tibetan calendar toolkit designed to host:
- Traditional engines (Phugpa, Tsurphu, Bhutan, Mongol, Karana, …)
- Reform engines L1–L5 (and optional L6 via ephemeris)
- Engine-agnostic **attributes** (weekday, sexagenary labels, etc.)
- Optional diagnostics (core, plus ephemeris/DE-based validation)

This repository is a **starter scaffold**: the public API and internal architecture are in place,
while the detailed calendrical math is left for implementation.

## Install (development)
```bash
pip install -e .
```

## Optional extras
- Ephemeris-backed diagnostics + optional L6:
  ```bash
  pip install -e ".[ephemeris]"
  ```
- Diagnostics reporting helpers:
  ```bash
  pip install -e ".[diagnostics]"
  ```

## Quick test
```python
from datetime import date
import caltib

print(caltib.list_engines())
print(caltib.day_info(date(2026,2,21), engine="phugpa", attributes=("weekday",), debug=True))
```
