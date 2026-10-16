"""Resolve editor2 from the running interpreter's ABI directory."""
import importlib
import os
import sys
import struct
from pathlib import Path

if sys.version_info[:2] != (3, 8) or struct.calcsize('P') != 8:
    raise ImportError('DeepDraw engine requires CPython 3.8 x64')
ABI = 'cp38'
DIRECTORY = Path(__file__).parent / ABI
if not DIRECTORY.is_dir():
    raise ImportError('DeepDraw binding missing for {}. Install matching editor2.pyd and DLLs in {}'.format(ABI, DIRECTORY))
sys.path.insert(0, str(DIRECTORY))
_dll_directory = os.add_dll_directory(str(DIRECTORY)) if hasattr(os, 'add_dll_directory') else None
editor2 = importlib.import_module('editor2')
