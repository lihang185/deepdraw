"""Export current editor2 models through the matching native DeepDraw API."""
import os
import tempfile

from .native import editor2

from importers.sketchup.native import load
_exporter = None


def _native():
    global _exporter
    if _exporter is None:
        _exporter = load('skp_exporter')
    return _exporter


def _export(model, path, selection):
    if not isinstance(model, editor2.CModel):
        raise TypeError('Expected current editor2.CModel')
    exporter = _native()
    with tempfile.TemporaryDirectory(prefix='deepdraw-skp-export-') as temp:
        exporter.set_temp_dir(temp)
        function = exporter.export_selection_to_file if selection else exporter.export_scene_to_file
        return function(model, os.fspath(path))


def export_scene_to_file(model, path):
    return _export(model, path, False)


def export_selection_to_file(model, path):
    return _export(model, path, True)
