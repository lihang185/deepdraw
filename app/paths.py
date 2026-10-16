"""Application paths, independent of the working directory."""
from pathlib import Path
import sys
ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
RUNTIME = ROOT / 'runtime'
PLUGINS = ROOT / 'plugins'
SKETCHUP = Path(__file__).resolve().parents[1] / 'importers' / 'sketchup'
