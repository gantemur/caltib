# The Design & Diagnostics Laboratory

A core philosophy of `caltib` is **complete transparency**. The modern reform engines (L1–L6) are not black boxes with arbitrary magic numbers. The library includes the exact mathematical tools used to derive, optimize, and validate every parameter in the system. Anyone can verify our constants or use these tools to design their own calendar engine.

!!! note "Laboratory Dependencies"
    To access these modules, ensure you have installed the optional laboratory dependencies: `pip install "caltib[tools]"` (for design/charting) and `pip install "caltib[ephemeris]"` (for JPL DE422 integration).

---

## 1. The "Ground Truth" Ephemeris Layer

All parameter design and diagnostic testing must be measured against physical reality. `caltib` natively supports two interchangeable standards of truth:

* **The Analytical Reference (REF):** A lightweight, highly precise, built-in implementation of truncated ELP2000/Meeus series algorithms. It allows the tools to run anywhere without heavy downloads or external dependencies.
* **The JPL Integration (DE422):** By supplying JPL `.bsp` files, the tools seamlessly swap to evaluating exact NASA numerical integrations for absolute astronomical proof.

```bash
# Calculate true solar longitude, Equation of Time, and precise sunrise
caltib solar --jd-utc 2461072.5 --lat 29.65 --lon 91.11

# Compare an engine's output natively against the JPL ephemeris
caltib diag offsets --engine l3 --ephem de422
```

---

## 2. Calendar Design Tools

These commands automatically process modern astronomical rates and compress them into the highly optimized rational fractions, integer tables, and minimax polynomials used by the reform engines.

* `caltib rational-params`: Uses continued fractions to generate optimal rational convergents for mean orbital motions, balancing precision with computational limits.
* `caltib sine-table`: Generates perfectly scaled, FPU-free integer sine-tables for evaluating the Equation of Center in the L1–L3 rational engines.
* `caltib minimax` & `pade-arctan`: Computes rigorous Chebyshev minimax odd-polynomial approximations for strictly reproducible floating-point trigonometric evaluation in the L4/L5 engines.
* `caltib float-params`: Generates full-precision hex-float representations of orbital parameters to guarantee bit-for-bit reproducibility across hardware architectures.

---

## 3. The Diagnostics Suite

Once an engine is designed, the diagnostic suite visually and mathematically proves its stability across centuries. These tools were used to generate the charts seen on the *Traditions* and *Reforms* pages.

* `caltib diag analysis`: Fits quadratic curves to syzygy offsets over millennia to locate the engine's "Drift Vertex" (the exact historical year its parameters were perfect) and measures its implied secular acceleration.
* `caltib diag anomaly`: Plots the forward and inverse kinematic anomalies, proving that the engine's continuous orbital math successfully absorbs the Moon's orbital perturbations (Evection, Variation, etc.).
* `caltib diag equinox`: Evaluates an engine's sidereal/tropical drift by plotting its true solar longitude precisely at the true Vernal Equinox over a span of 1,500 years.
* `caltib diag drift-quad`: A deep-dive tool that generates scatter plots and rolling standard deviation ($\pm 1\sigma$) spread bands to visualize the exact moment an engine's phase drifts into chaos.

---

## CLI & Tools Reference

Below is the automatically generated technical reference for the command-line interface and the underlying design algorithms.

### Command Line Interface
::: caltib.cli

### Calendar Design & Parameter Optimization
::: caltib.design.rational_params
::: caltib.design.float_params
::: caltib.design.sine_tables
::: caltib.design.minimax_polys
::: caltib.design.pade_arctan

### The Diagnostics Suite
::: caltib.diagnostics.analysis
::: caltib.diagnostics.drift_quad
::: caltib.diagnostics.anomaly
::: caltib.diagnostics.equinox
::: caltib.diagnostics.offsets