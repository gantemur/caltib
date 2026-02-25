from .registry import register_attribute
from . import standard as _standard  # noqa: F401  (register built-ins)

__all__ = ["register_attribute"]
