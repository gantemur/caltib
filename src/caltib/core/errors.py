class CaltibError(Exception):
    """Base error."""

class EngineUnavailableError(CaltibError):
    """Raised when an optional engine (e.g. L6) is not available."""
