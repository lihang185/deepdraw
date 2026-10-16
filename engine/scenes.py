"""Saved human views stored in the top component's persistent metadata.

Layer IDs are session identities; the education DIM reader remaps them after loading.
No native pointers are retained in a scene.
"""
import json
import uuid
from contextlib import contextmanager

from engine.qt import QtGui
from engine.mutation_guard import check_mutation

KEY = 'saved_scenes_v1'
FILE_KEY = 'saved_scenes_file_v1'


@contextmanager
def file_layer_references(model):
    """Encode scene visibility with registry indices; restore session text exactly."""
    data = metadata(model)
    if KEY not in data:
        yield
        return
    indices = {str(layer.GetID()): str(index) for index, layer in
               enumerate(l for l in model.GetLayers() if not l.IsMarkedDeleted())}
    scenes = data.pop(KEY)
    for scene in scenes:
        scene['layers'] = {indices[uid]: hidden for uid, hidden in scene['layers'].items()
                           if uid in indices}
    data[FILE_KEY] = scenes
    top = model.GetTopComponent()
    original = top.agent_hint
    try:
        top.agent_hint = json.dumps(data, ensure_ascii=False)
        yield
    finally:
        top.agent_hint = original


def restore_file_layer_references(model, legacy_mapping=None):
    data = metadata(model)
    if FILE_KEY not in data:
        if legacy_mapping is not None:
            remap_layers(model, legacy_mapping)
        return
    layers = [layer for layer in model.GetLayers() if not layer.IsMarkedDeleted()]
    scenes = data.pop(FILE_KEY)
    for scene in scenes:
        restored = {}
        for index, hidden in scene['layers'].items():
            index = int(index)
            if not 0 <= index < len(layers):
                raise ValueError('Saved scene references an invalid layer index')
            restored[str(layers[index].GetID())] = hidden
        scene['layers'] = restored
    data[KEY] = scenes
    model.GetTopComponent().agent_hint = json.dumps(data, ensure_ascii=False)



def metadata(model):
    text = model.GetTopComponent().agent_hint
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        data = None
    return data if isinstance(data, dict) else ({'legacy_agent_hint': text} if text else {})


def read(model):
    return metadata(model).get(KEY, [])


def write(model, scenes):
    data = metadata(model)
    data[KEY] = scenes
    model.GetTopComponent().agent_hint = json.dumps(data, ensure_ascii=False)


def remap_layers(model, mapping):
    scenes = read(model)
    if not scenes:
        return
    for scene in scenes:
        scene['layers'] = {str(mapping[int(uid)]): hidden
                           for uid, hidden in scene['layers'].items() if int(uid) in mapping}
    write(model, scenes)


class SceneManager:
    def __init__(self, document):
        self.document = document

    def check(self):
        check_mutation()
        dd = self.document.editing
        if dd is None or not dd.alive or dd.edit.active is not None:
            raise ValueError('请先完成当前操作')
        if dd.model.GetActiveComponent() != dd.model.GetTopComponent():
            raise ValueError('请先退出组件编辑，再保存或切换场景')
        return dd

    def capture(self):
        dd = self.check()
        view = self.document.view
        camera = view.camera
        def vector(v):
            return [v.x(), v.y(), v.z()]
        return dict(camera=dict(position=vector(camera.position), target=vector(camera.target),
                                up=vector(camera.up), fov=camera.fov),
                    layers={str(e.GetID()): bool(e.is_hide) for e in dd.model.GetLayers()
                            if not e.IsMarkedDeleted()},
                    lighting=dict(direction=list(view.shadow_direction),
                                  shadows_enabled=bool(view.shadows_enabled),
                                  resolution=int(view.shadow_resolution),
                                  strength=float(view.shadow_strength)))

    def edit(self, action, ident=None, name=None):
        dd = self.check()
        scenes = read(dd.model)
        scene = next((s for s in scenes if s['id'] == ident), None)
        if action == 'add':
            names = {s['name'] for s in scenes}
            number = 1
            while '场景%d' % number in names:
                number += 1
            scene = dict(id=uuid.uuid4().hex, name='场景%d' % number, **self.capture())
            scenes.append(scene)
        elif scene is None:
            raise ValueError('请先选择场景')
        elif action == 'update':
            scene.update(self.capture())
        elif action == 'delete':
            scenes.remove(scene)
        elif action == 'rename':
            name = name.strip()
            if not name or any(s['id'] != ident and s['name'] == name for s in scenes):
                raise ValueError('场景名称不能为空或重复')
            scene['name'] = name
        else:
            raise ValueError('未知场景操作')
        with dd.edit.operation('场景管理'):
            top = dd.model.GetTopComponent()
            old = top.agent_hint
            dd.edit.rollback_actions.append(lambda: setattr(top, 'agent_hint', old))
            top.Record(True)
            write(dd.model, scenes)
            dd.edit.touch(dd.wrap(top))
        return scene['id']

    def apply(self, ident):
        dd = self.check()
        scene = next((s for s in read(dd.model) if s['id'] == ident), None)
        if scene is None:
            raise ValueError('请先选择场景')
        saved = scene['camera']
        vectors = {key: QtGui.QVector3D(*saved[key]) for key in ('position', 'target', 'up')}
        view = self.document.view
        lighting = scene.get('lighting')
        # Old scenes have no lighting snapshot: preserve the current settings.
        # Allocate GL resources before changing scene state, so an unsupported
        # shadow map fails without partially applying the camera or layers.
        if lighting is not None and lighting['shadows_enabled']:
            view.makeCurrent()
            try:
                view.pipeline.shadow_pass().native.configure(lighting['resolution'])
            finally:
                view.doneCurrent()
        with dd.edit.operation('切换场景图层'):
            for layer in dd.model.GetLayers():
                if not layer.IsMarkedDeleted():
                    # Restore a complete visible-layer set. Layers added/imported
                    # later were not visible in the saved scene.
                    layer.is_hide = scene['layers'].get(str(layer.GetID()), True)
            dd.model.ClearSelection()
            dd.edit.touch(dd.wrap(dd.model.GetTopComponent()))
        camera = self.document.view.camera
        for key, value in vectors.items():
            setattr(camera, key, value)
        camera.fov = saved['fov']
        camera.compute()
        if lighting is not None:
            view.shadow_direction = tuple(lighting['direction'])
            view.shadows_enabled = lighting['shadows_enabled']
            view.shadow_resolution = lighting['resolution']
            view.shadow_strength = lighting['strength']
        self.document.view.MarkDirty()
        self.document.view.update()
        self.document.scene_applied.emit()
