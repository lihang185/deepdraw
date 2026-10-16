"""Per-document state needed by human tools, with no observation or AI API."""
import uuid
from engine import core
from engine.qt import QtCore
from .objects import Entity, Container, Selection, Scene
from .edit import Edit
from .build import Build
from .metadata import NamedSets
from .selection import SelectionTools
from .sweep import Sweeps


class EditingContext:
    def __init__(self, view):
        self.widget, self.model = view, view.model
        self.token, self.revision, self.history_epoch = uuid.uuid4().hex, 0, 0
        self.alive, self.results = True, []
        self.metadata = NamedSets(self.model)
        self.scene, self.edit = Scene(self), Edit(self)
        self.build, self.selection, self.sweep = Build(self), SelectionTools(self), Sweeps(self)
        self.diagnostics = GeometryChecks(view)
        from .bounds import Bounds
        self.inspect = Bounds(self)
        from .material_assets import MaterialAssets
        self.assets = MaterialAssets(self)

    def check(self):
        self.diagnostics.check_thread()
        if not self.alive or self.widget.model != self.model:
            raise RuntimeError('编辑对象所属的模型已关闭，请重新选择')

    def wrap(self, native):
        return (Container if isinstance(native, core.CComponent) else Entity)(self, native)

    def unwrap(self, target):
        self.check()
        if isinstance(target, Selection):
            if target.session is not self or target.history_epoch != self.history_epoch:
                raise ValueError('选择已失效，请重新选择')
            return [self.wrap(e).native for e in target.entities]
        if isinstance(target, Entity):
            if target.session is not self:
                raise ValueError('对象属于另一个模型')
            return [target.native]
        if isinstance(target, (list, tuple)):
            return [e for item in target for e in self.unwrap(item)]
        raise TypeError('Expected a current editing object')

    def single(self, target):
        entities = self.unwrap(target)
        if len(entities) != 1:
            raise ValueError('请选择一个对象')
        return entities[0]


class GeometryChecks:
    def __init__(self, view):
        self.view = view

    def check_thread(self):
        if QtCore.QThread.currentThread() != self.view.thread():
            raise RuntimeError('模型只能在界面主线程访问')

    def invalidate(self):
        # The editor has only the human view; its pipeline receives edit changes.
        self.view.update()

    def validate(self):
        self.check_thread()
        from engine.entity_refs import sanitize_model_references
        model = self.view.model
        model.ClearError()
        try:
            if getattr(self.view, "validate_edits", False):
                model.TestValidity()
        finally:
            sanitize_model_references(model)
        message = model.GetLastError()
        severity = int(message.error) if message is not None else 0
        issue = message.GetErrorMessage() if severity and hasattr(message, 'GetErrorMessage') else None
        return dict(status='invalid' if model.HasError() or severity else 'valid', issue=issue)

    def resolve_topology(self, entities, component):
        self.check_thread()
        manager = core.CMergeEventManager()
        controller = core.CMergeController(component, list(entities), manager)
        try:
            controller.Compute()
        finally:
            del controller
            del manager
        result = self.validate()
        if result['status'] != 'valid':
            raise RuntimeError('拓扑检查失败：{}'.format(result['issue']))
        return result
