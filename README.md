# caltib

A high-precision Python library implementing traditional Tibetan lunisolar calendars, complete with analytical design tools for structural validation and calendar reform.

This package provides a rigorous framework for evaluating historical algorithms, testing N-body ephemeris models, and generating optimal fixed-point parameters for modern calendrical computation.

## Core Capabilities

* **Traditional Engines:** Exact implementations of historical Tibetan and regional calendars (Phugpa, Tsurphu, Bhutan, Mongol, Karana).
* **Reform Engines:** Modernized lunisolar algorithms (L1–L5) and continuous floating-point implementations (L6) backed by JPL N-body ephemerides.
* **Astronomical Reference Models:** High-precision continuous solar and lunar series grounded in modern theory (ELP2000/82, IAU coordinate frames) optimized for calendar-grade accuracy.
* **Design & Approximation Tools:** A suite of analytical tools to generate mathematically optimal calendar constants (rational convergents, dyadic fractions, minimax polynomials, and Padé approximants).
* **Engine-Agnostic Attributes:** Universal evaluation of weekdays, sexagenary cycles, and leap month mechanics.

## Installation

Install the base package in development mode:
```bash
pip install -e .