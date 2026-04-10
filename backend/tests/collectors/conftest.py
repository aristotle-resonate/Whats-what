"""
Collector test fixtures and sys.modules stubs.

feedparser 6.x depends on sgmllib3k (which provides module-level regex
attributes on sgmllib).  The system sgmllib is a thin stub, so we inject a
lightweight feedparser mock into sys.modules before any test module imports it.
The real collectors patch feedparser.parse at the call site, so the stub only
needs to expose a callable `parse` attribute.
"""

import sys
import types
from unittest.mock import MagicMock

# Only stub if feedparser cannot be imported natively.
try:
    import feedparser  # noqa: F401
except Exception:
    _feedparser_stub = types.ModuleType("feedparser")
    _feedparser_stub.parse = MagicMock()  # type: ignore[attr-defined]
    sys.modules["feedparser"] = _feedparser_stub
