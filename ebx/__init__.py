"""Source-checkout bootstrap for the package stored under ``src/ebx``.

Editable installs use the normal project package; this tiny shim also makes
``python -m ebx.cli`` work directly from a clean checkout before installation.
"""

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parents[1] / "src" / "ebx")]
__version__ = "0.1.0"
