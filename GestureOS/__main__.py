"""Execution entry point for python -m gestureos."""

from __future__ import annotations
import sys
import os
from pathlib import Path

# Add GestureOS package directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
gestureos_dir = root_dir / "GestureOS"

if str(gestureos_dir) not in sys.path:
    sys.path.insert(0, str(gestureos_dir))

import run_gestureos

if __name__ == "__main__":
    sys.exit(run_gestureos.main())
