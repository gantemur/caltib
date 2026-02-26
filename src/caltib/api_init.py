"""Registry bootstrap (import side-effect)."""
from .api import set_registry
from .bootstrap import build_registry

set_registry(build_registry())
