"""jcheng-devices: offline device library for the JCHENG ecosystem.

The package reads declarative device and capability profiles, validates them
against the bundled JSON schemas and emits deterministic summaries. It never
opens a device, joins a runtime graph or commands motion.
"""

from .registry import Registry
from .version import __version__

__all__ = ["Registry", "__version__"]
