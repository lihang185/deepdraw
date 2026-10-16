"""Toolbar layer assignment; retain IDs only across model callbacks."""
from engine import core
from engine.qt import QtCore, QtWidgets
from engine.mutation_guard import human_callback, check_mutation
from .Ui_selection_layer import Ui_SelectionLayer


class SelectionLayer(QtWidgets.QWidget, Ui_SelectionLayer):
    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.snapshot = None
        self.setupUi(self)
        self.clear()
        host.about_to_release.connect(self.clear)
        host.model_changed.connect(self.refresh)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()

    def clear(self):
        self.snapshot = None
        self.layerCombo.clear()
        self.layerCombo.addItem('未选择对象', None)
        self.layerCombo.setEnabled(False)

    def ready(self):
        dd = self.host.editing
        return dd is not None and dd.alive and not self.host.input_busy and dd.edit.active is None

    def selection(self):
        model = self.host.view.model
        selected = list(model.GetSelection())
        if any(not isinstance(e, core.CDrawingElement) or e.IsMarkedDeleted()
               or e.GetParentComponent() != model.GetActiveComponent() for e in selected):
            return []
        return selected

    @human_callback
    def refresh(self):
        if not self.ready():
            self.layerCombo.setEnabled(False)
            return
        # GetLayers owns these wrappers for the duration of GetLayer queries.
        layers = [e for e in self.host.view.model.GetLayers() if not e.IsMarkedDeleted()]
        selected = self.selection()
        ids = set()
        for entity in selected:
            layer = entity.GetLayer()
            ids.add(layer.GetID() if layer is not None else '__default__')
        rows = (('__default__', '默认图层'),) + tuple((e.GetID(), e.name) for e in layers)
        key = (self.host.editing.token, rows, tuple(sorted(e.GetID() for e in selected)), frozenset(ids))
        self.layerCombo.setEnabled(bool(selected))
        if key == self.snapshot:
            return
        self.layerCombo.clear()
        current = next(iter(ids)) if len(ids) == 1 else None
        if not selected or len(ids) != 1 or current not in dict(rows):
            label = '未选择对象' if not selected else ('多个不同图层' if len(ids) > 1 else '未分配图层')
            self.layerCombo.addItem(label, None)
        for ident, name in rows:
            self.layerCombo.addItem(name, ident)
        self.layerCombo.setCurrentIndex(max(0, self.layerCombo.findData(current)))
        self.snapshot = key

    @QtCore.Slot(int)
    def on_layerCombo_activated(self, index):
        ident = self.layerCombo.itemData(index)
        token = self.snapshot[0] if self.snapshot else None
        if ident is not None:
            self.host.run_action(self.assign, ident, token)
        self.snapshot = None
        self.refresh()

    def assign(self, ident, token):
        check_mutation()
        if not self.ready() or token != self.host.editing.token:
            raise ValueError('模型已改变或正在编辑，请重新选择图层')
        model = self.host.view.model
        layers = [e for e in model.GetLayers() if not e.IsMarkedDeleted()]
        layer = next((e for e in layers if e.GetID() == ident), None)
        if layer is None and ident != '__default__':
            raise ValueError('图层已不存在')
        selected = self.selection()
        changed = [e for e in selected if e.GetLayer() != layer]
        if not changed:
            return
        dd = self.host.editing
        with dd.edit.operation('设置选中对象图层'):
            dd.edit.touch(dd.wrap(model.GetActiveComponent()))
            for entity in changed:
                entity.Record(True)
                entity.SetLayer(layer)
        self.host.view.MarkDirty()
        self.host.view.update()
