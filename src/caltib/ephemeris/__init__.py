"""Ephemeris adapters/providers (optional).

This package provides thin wrappers around external ephemeris libraries.
Install with:
  pip install "caltib[ephemeris]"
"""

def require_ephemeris():
    """Raise a clear error if ephemeris extras aren't installed."""
    try:
        import jplephem  # noqa: F401
        import skyfield  # noqa: F401
    except ImportError as e:
        raise RuntimeError('Ephemeris support requires: pip install "caltib[ephemeris]"') from e
