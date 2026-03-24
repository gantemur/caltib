# System Architecture

The `caltib` library is built on a philosophy of strict mathematical decoupling. By separating the discrete arithmetic of human calendar rules from the continuous kinematics of orbital mechanics, the library can evaluate ancient 15th-century integer algorithms and modern floating-point ephemeris models using the exact same polymorphic API.

---

## 1. The Absolute Lunar Day

The core mathematical innovation of the library is the 1D continuous coordinate $x$. Instead of jumping between nested loops of years, months, and days, the entire timeline is mapped to an absolute fractional sequence where exactly $x \pmod{30} = 0$ represents a theoretical mean New Moon.

Every calculation is anchored to the J2000.0 Terrestrial Time (TT) standard. By defining a global lunation index $n$ and a fractional day index $d$, any point in history can be mapped precisely using the formula $x = 30n + d$. This strips away all chronological ambiguity before applying any regional or historical rules.

## 2. The Decoupled Engine Protocols

To handle the massive complexity of leap months, geographical sunrise, and astronomical anomalies, the internal workload is strictly divided into isolated, interoperable protocols:

* **The Month Engine:** Handles the discrete, arithmetic logic. It determines leap-year status, assigns regional month names, and calculates exactly which lunation index $n$ belongs to a given year.
* **The Day Engine:** Handles the continuous, physical kinematics. It is completely blind to "years" or "months." It simply takes an absolute coordinate $x$ and calculates the exact physical moment ($t2000$) of the solar/lunar anomaly and corresponding sunrise.
* **The Calendar Engine:** The orchestrator. It merges the outputs of the Month and Day engines, applying the local civil boundaries to generate the final human-readable date.

## 3. Strictly Reproducible Solvers

A major failing of many astronomical libraries is "floating-point drift"—where different CPUs or operating systems produce slightly different calculation results. `caltib` guarantees cross-platform, deterministic reproducibility by strictly avoiding dynamic `while` loops, variable error tolerances, and hardware-dependent transcendental math libraries. Instead, it relies on:

* **Rational Picard Solvers (L0–L3):** Execute a strictly fixed number of iteration steps (typically 1 or 2) using pure arbitrary-precision fractions and integer sine-tables, achieving zero floating-point accumulation error.
* **Reproducible Float Solvers (L4–L5):** Utilize a fixed number of Picard or Steffensen iterations combined with highly optimized Chebyshev minimax polynomials for transcendental functions, guaranteeing bit-for-bit reproducibility across any CPU architecture.
* **Ephemeris Integration (L6):** Directly queries highly precise JPL `.bsp` files.

*Note: Secant root-finders are explicitly excluded from the core engines to maintain deterministic performance; they are reserved exclusively for the diagnostic suite to evaluate heavy numerical reference models.*

## 4. The Civil Calendar Generator

The highest layer of the architecture bridges continuous math into discrete human reality. The Civil Calendar Generator evaluates the true physical time of a syzygy (the moon phase) against the local physical time of sunrise.

If two mathematical lunar boundaries ($x$ and $x+1$) fall within a single solar day, that day is **skipped** in the civil calendar. If a solar day passes without crossing a lunar boundary, that civil day is **duplicated**. This allows the calendar to remain perfectly synchronized with the cosmos without breaking the uninterrupted flow of the 7-day week.

## 5. Dependency Injection & Localization

Through the polymorphic `CalendarSpec` builder pattern, users can dynamically inject and swap geographical locations (e.g., Lhasa, Montreal, Ulaanbaatar). This instantly alters the spherical sunrise thresholds and shifts the resulting civil grids (changing which days are skipped or duplicated) without touching the underlying orbital kinematics.

## 6. Dependency Isolation

The `caltib` factory utilizes lazy instantiation to protect system resources. Traditional algorithms and Reform tiers L0–L5 are bundled in the zero-dependency core. The heavy L6 numerical engine, which requires downloading massive ephemeris files, only activates if the optional `[ephemeris]` extra is present. This architectural boundary ensures the base library remains incredibly lightweight, lightning-fast, and natively portable to WebAssembly/PyScript environments.