"""Production-facing EBX analysis package."""

from pathlib import Path
import sys

_repository_root = Path(__file__).resolve().parents[2]
if str(_repository_root) not in sys.path:
    sys.path.insert(0, str(_repository_root))

__version__ = "0.1.0"
