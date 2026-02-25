"""Diagnostics package.

- diagnostics: always available, light-weight checks (no ephemeris)
- diagnostics.ephem: optional (requires ephemeris extras + DE file)
"""

__all__ = ["pretty_month", "new_years_table", "round_trip", "leap_months", "losar_scatter", "equinox_trads"]