"""Isolated SKP import worker using the current education engine only."""
from pathlib import Path
import sys

_application = None


def main():
    global _application
    if len(sys.argv) != 4:
        raise ValueError('Usage: convert.py runtime_directory source.skp output.dim')
    runtime, source, output = (Path(value).resolve() for value in sys.argv[1:])
    if runtime != Path(__file__).resolve().parent:
        raise ValueError('SketchUp runtime directory does not match this worker')
    if not getattr(sys, 'frozen', False):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from PySide2.QtWidgets import QApplication
    _application = QApplication.instance() or QApplication([])
    from engine import core
    from importers.sketchup.import_model import convert
    core.CModel.InitSystem()
    convert(source, output)
    print('SKP import complete: editor2, DAI', flush=True)


if __name__ == '__main__':
    main()
