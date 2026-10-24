"""GestureOS Root Forwarder — Allows running 'python run_gestureos.py' from project root."""

import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
gestureos_dir = os.path.join(base_dir, "GestureOS")

if gestureos_dir not in sys.path:
    sys.path.insert(0, gestureos_dir)

os.chdir(gestureos_dir)

import run_gestureos

if __name__ == "__main__":
    sys.exit(run_gestureos.main())
