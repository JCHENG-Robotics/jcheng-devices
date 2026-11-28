"""jcheng-devices: offline device library for the JCHENG ecosystem.

The package reads declarative device and capability profiles, validates them
against the bundled JSON schemas and emits deterministic summaries. It never
opens a device, joins a runtime graph or commands motion.
"""

from .compatibility import CompatibilityReport, match
from .hashing import canonical_yaml, content_hash, content_hash_of
from .registry import Registry
from .snapshot import build_snapshot, load_snapshot
from .version import __version__

__all__ = [
    "CompatibilityReport",
    "Registry",
    "__version__",
    "build_snapshot",
    "canonical_yaml",
    "content_hash",
    "content_hash_of",
    "load_snapshot",
    "match",
]
