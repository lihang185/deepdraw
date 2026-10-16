"""Real-engine scene metadata roundtrips through pickle and native Python adapters."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import core, scenes, serialization, native_serialization

models = []
def new_model():
    model = core.CModel()
    models.append(model)
    return model

def visibility(model):
    names = {str(layer.GetID()): layer.name for layer in model.GetLayers()}
    return [{names[uid]: hidden for uid, hidden in scene['layers'].items()}
            for scene in scenes.read(model)]

try:
    source = new_model()
    source.Activate()
    core.set_active_model(source)
    for name in ('walls', 'furniture', 'empty'):
        source.addLayer(core.CLayer.Load(name, False, None))
    layers = list(source.GetLayers())
    source.GetTopComponent().agent_hint = json.dumps({
        'unrelated': {'keep': True},
        scenes.KEY: [dict(name='one', layers={str(l.GetID()): i == 1 for i, l in enumerate(layers)}),
                     dict(name='two', layers={str(l.GetID()): i != 1 for i, l in enumerate(layers)})]})
    original = source.GetTopComponent().agent_hint
    expected = visibility(source)
    with tempfile.TemporaryDirectory() as directory:
        for codec in (serialization, native_serialization):
            filename = str(Path(directory)/(codec.__name__ + '.dim'))
            codec.save_sketchup_model(source, filename)
            assert source.GetTopComponent().agent_hint == original
            target = new_model()
            codec.load_sketchup_model(target, filename)
            assert visibility(target) == expected
            assert scenes.metadata(target)['unrelated'] == {'keep': True}
            assert scenes.FILE_KEY not in scenes.metadata(target)
            codec.save_sketchup_model(target, filename)
            again = new_model()
            codec.load_sketchup_model(again, filename)
            assert visibility(again) == expected
            try:
                codec.save_sketchup_model(source, str(Path(directory)/'missing'/'bad.dim'))
            except (OSError, ValueError):
                pass
            else:
                raise AssertionError('Expected failed write')
            assert source.GetTopComponent().agent_hint == original
        # Existing ID-based metadata still follows the legacy pickle mapping.
        scenes.restore_file_layer_references(source, {l.GetID(): l.GetID() for l in layers})
        assert visibility(source) == expected
    print('SCENE_LAYER_PICKLE_NATIVE_ROUNDTRIP_FAILURE_RESTORE_OK', flush=True)
finally:
    for model in reversed(models):
        model.Release()
    core.set_active_model(None)
