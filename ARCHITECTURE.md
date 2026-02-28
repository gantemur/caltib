# Caltib: Architecture & Design Philosophy

`caltib` is a high-precision, mathematically rigorous library for Siddhantic and Tibetan calendrical astronomy. It bridges the gap between historical medieval algorithms (piecewise linear integer models) and modern celestial mechanics (continuous trigonometric ephemerides) by unifying them under a single algebraic framework.

## 1. The Principle of Modularity

The historical calendar is fundamentally the intersection of two completely orthogonal mathematical domains. `caltib` strictly isolates these domains into independent protocols. 

1. **`MonthEngine` (Discrete Arithmetic):** * **Domain:** Labels, years, and leap statuses.
   * **Mechanics:** Maps absolute lunation indices ($n$) to human calendar labels (Year, Month, Intercalary status). It operates purely on modular arithmetic and knows nothing of physical time or Julian Days.
2. **`DayEngine` (Continuous Kinematics):**
   * **Domain:** Celestial motion and timekeeping.
   * **Mechanics:** Maps an absolute spatial coordinate ($x$) to an exact physical time (Julian Day) by solving for planetary alignments. It knows nothing of calendar years or human month labels.
3. **`CalendarEngine` (The Orchestrator):**
   * **Domain:** The Civil Boundary.
   * **Mechanics:** Acts as the bridge between the civil user and the physical engines. It takes a local integer Julian Day Number (JDN), queries the Day Engine for the spatial coordinate $x$, derives the lunation $n$, and asks the Month Engine for the label. 

By treating the Month and Day engines as modular plugins, the library supports seamless hybridization (e.g., combining a traditional 15th-century Phugpa month calculator with a 21st-century floating-point day kinematic solver).

## 2. The Absolute Spatial Coordinate ($x$)

A core breakthrough of the `caltib` architecture is the flattening of the traditional two-dimensional calendar grid (lunation $n$, tithi $d$) into a single, continuous, one-dimensional spatial coordinate:

$$x = 30n + d$$

In the kinematic layer (`DayEngine`), $x$ represents the absolute number of tithis (lunar days, or $12^\circ$ increments of elongation) elapsed since the epoch. 
* By removing $n$ and $d$ from the core physics loop, continuous root-finding algorithms (like the Picard solver) can evaluate fractional tithis seamlessly.
* The traditional engine logic is completely subsumed by this coordinate, evaluating mean elongation linearly via $m_0 + x \cdot m_1$.

## 3. The Temporal Reference Frame (J2000.0 TT)

To guarantee numerical stability, all internal physical time variables ($t$) in the `DayEngine` represent **Days since J2000.0 TT** (where J2000.0 = JD 2451545.0).

* **Rational Engines (L1-L3):** Shifting the origin to J2000.0 prevents fraction denominators from exploding when evaluating exact affine series over millions of days.
* **Floating-Point Engines (L4-L5):** Shifting the origin prevents catastrophic cancellation and floating-point precision loss when computing high-frequency astronomical anomalies.
* **Civil Abstraction:** The continuous $t2000$ values are only converted to absolute Julian Days (JD) or Julian Day Numbers (JDN) at the outermost `CalendarEngine` layer.

## 4. The Kinematic Solver (The Picard Iteration)

The continuous `DayEngine` reforms discard historical lookup tables in favor of dynamically solving the fundamental equation of syzygy. The engine builds an affine series for the mean elongation $D(t)$ and the solar/lunar perturbations $C(t)$. 

To find the exact time $t$ of a tithi boundary $x$, the engine solves:
$$D(t) + C_{moon}(t) - C_{sun}(t) = \frac{x}{30}$$

Because the perturbations $C(t)$ themselves depend on time, `caltib` employs a Picard fixed-point iteration, seeded by the linear mean system $t_0 = D^{-1}(x/30)$, to converge on the exact physical timing of the lunar day.

## 5. Epoch Synchronization

Because the Month and Day engines are independent, they may theoretically possess different astronomical epochs. `caltib` defines the epoch natively via the absolute Meeus mean new moon index ($k_0$).
The `CalendarEngine` automatically aligns the engines by computing $\Delta k = \text{Day.epoch\_k} - \text{Month.epoch\_k}$, dynamically shifting the $x$ coordinate to guarantee perfect phase synchronization across any combination of models.