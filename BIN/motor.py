#!/usr/bin/env python3
"""Convenience entry point for one safe CatedralX analysis cycle."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
ELITE = ROOT / "elite"
if str(ELITE) not in sys.path:
    sys.path.insert(0, str(ELITE))
from REASON.razon import main
if __name__ == "__main__":
    raise SystemExit(main())
