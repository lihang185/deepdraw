"""Native DAI routing adapter; file parsing and model construction stay in C++."""
import struct
from .mutation_guard import check_mutation

MAGIC = b'DeepDrawNative\r\n'


def save_sketchup_model(model, filename):
    check_mutation()
    from .scenes import file_layer_references
    with file_layer_references(model):
        status, message = model.SaveNativeFile(str(filename))
    if status != 0:
        raise ValueError('Native model save failed (%s): %s' % (status, message))
    return True


def load_sketchup_model(model, filename, progress=None):
    check_mutation()
    with open(filename, 'rb') as stream:
        if stream.read(len(MAGIC)) != MAGIC:
            raise ValueError('Not a native DAI file')
        header = stream.read(8)
    if len(header) != 8:
        raise ValueError('Truncated native DAI header')
    version, flags = struct.unpack('<II', header)
    if version != 2 or flags:
        raise ValueError('Unsupported native DAI version or flags: %s / %s' % (version, flags))
    if not hasattr(model, 'ReadNativeFile'):
        raise RuntimeError('当前引擎未提供原生文件读取接口，请更新引擎')
    if progress:
        progress('读取原生模型', 0, 0)
    status, message = model.ReadNativeFile(str(filename))
    if status != 0:
        raise ValueError('原生模型读取失败（%s）：%s' % (status, message))
    from .scenes import restore_file_layer_references
    restore_file_layer_references(model)
    if progress:
        progress('读取原生模型', 1, 1)
    return model


def load_sketchup_model_as_component(model, filename, **kwargs):
    # Moving entities out of a temporary model requires an engine ownership API.
    raise ValueError('原生 DAI 暂不支持作为组件插入，请使用“打开模型”或旧格式组件文件')
