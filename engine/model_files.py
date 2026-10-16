"""Route DAI by magic: pickle and native v2 only."""
from . import serialization
from pathlib import Path


def _reader(filename):
    suffix = Path(filename).suffix.lower()
    if suffix == '.dim':
        from . import native_serialization
        with open(filename, 'rb') as stream:
            magic = stream.read(len(native_serialization.MAGIC))
        if magic == native_serialization.MAGIC:
            return native_serialization
        return serialization
    raise ValueError('Only .dim models are supported')


def load_sketchup_model(model, filename, progress=None):
    return _reader(filename).load_sketchup_model(model, filename, progress=progress)


def load_sketchup_model_as_component(model, filename, unwrap_canonical=False):
    reader = _reader(filename)
    if reader is serialization:
        return reader.load_sketchup_model_as_component(model, filename, unwrap_canonical=unwrap_canonical)
    return reader.load_sketchup_model_as_component(model, filename)


def save_sketchup_model(model, filename, *, native=False):
    if native:
        from . import native_serialization
        return native_serialization.save_sketchup_model(model, filename)
    return serialization.save_sketchup_model(model, filename)


def release_texture_records():
    serialization.release_texture_records()
