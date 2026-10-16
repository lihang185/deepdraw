"""Erase edges/guides while dragging; one drag is one undo operation."""
from engine.coordinates import hit_in_active
from engine import core
from engine.qt import QtCore
from .edit_tool_support import interactive
from .transaction_tool import TransactionTool


@interactive
class EraseTool(TransactionTool):
    def activate(self):
        self.cancel_preview()
        self.pick_helper = core.CPickHelper(self.view.view_proxy)
        self.view.setMouseTracking(True)
        self.view.setStatusBar('擦除：按住左键划过边或参考线，松开确认；Ctrl 按住时平滑边；Esc 取消；组件请先双击进入')

    def on_left_button_down(self, pos, mod):
        self.begin_transaction('擦除 / 平滑', local_geometry=True)
        self.do_erase(pos,bool(mod & QtCore.Qt.ControlModifier))

    def on_left_button_up(self, pos):
        self.commit()

    def on_mouse_move(self, pos, modifiers):
        if self.transaction is not None:
            self.do_erase(pos,bool(modifiers & QtCore.Qt.ControlModifier))

    def do_erase(self, pos, smooth=False):
        if self.transaction is None:
            return
        self.view.mainWindow.editing.edit.require_operation()
        picker = self.pick_helper
        picker.Reset()
        picker.SinglePick(pos.x(), pos.y(), 9, None, True)
        hit = picker.BestPick()
        component = self.view.model.GetActiveComponent()
        if not hit_in_active(self.view,hit) or hit.e.GetParentComponent() != component:
            return
        if not isinstance(hit.e, (core.CEdge, core.CGuideLine)):
            return
        self.view.model.SetSelection([hit.e])
        self.view.model.AddCurveEdgesToSelection()
        selected = list(self.view.model.GetSelection())
        self.view.model.ClearSelection()
        for entity in selected:
            if not entity.IsMarkedDeleted() and entity.GetParentComponent() == component:
                if smooth:
                    if isinstance(entity,core.CEdge):
                        entity.SetSmooth(True)
                        entity.SetSoft(True)
                else:entity.Erase(component)
        self.refresh()
