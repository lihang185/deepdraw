"""Selection context menu. Register type-specific actions in actions_for_types."""
from engine.qt import QtCore, QtWidgets
from engine.mutation_guard import human_callback
from engine import core
from .Ui_view_context_menu import Ui_ViewContextMenu
from .object_properties_dialog import ObjectPropertiesDialog

class ViewContextMenu(QtWidgets.QMenu, Ui_ViewContextMenu):
    def __init__(self, view, entities):
        super().__init__(view)
        self.view = view
        self.setupUi(self)
        # Snapshot while authorized; no native handles survive the menu event loop.
        self.object_text = '\n\n'.join(str(entity) for entity in entities)
        self.actionObjectProperties.setEnabled(bool(entities))
        components = bool(entities) and all(isinstance(e, core.CComponentInstance) for e in entities)
        faces = bool(entities) and all(isinstance(e, core.CFace) for e in entities)
        self.actionFlipFace.setVisible(faces)
        from engine.tools.tool_texture import has_texture
        textured = faces and len(entities) == 1 and has_texture(entities[0])
        for action in (self.actionTexturePosition, self.actionTextureRotate):
            action.setVisible(faces)
            action.setEnabled(textured)
        self.actionExport.setVisible(components)
        self.actionExport.setEnabled(components and len(entities) == 1)
        self.actionExplode.setVisible(components)
        self.actionToGroup.setVisible(components and any(not e.is_group for e in entities))
        self.actionToComponent.setVisible(components and any(e.is_group for e in entities))
        self.entity_ids = [e.GetID() for e in entities] if components or faces else []
        dd = getattr(getattr(view, 'mainWindow', None), 'editing', None)
        self.session_state = (dd.token, dd.revision) if dd is not None else None
        for action in self.actions_for_types(frozenset(type(entity) for entity in entities)):
            self.addAction(action)

    def actions_for_types(self, entity_types):
        """Extension point for actions applicable to every selected object type."""
        return []

    def resolve_instances(self):
        return self.resolve_entities(core.CComponentInstance)

    @QtCore.Slot()
    @human_callback
    def on_actionFitCamera_triggered(self):
        self.view.mainWindow.actionFitCamera.trigger()

    def activate_texture_tool(self, tool_class, rotate_once=False):
        try:
            dd, faces = self.resolve_entities(core.CFace)
            from engine.tools.tool_texture import has_texture
            if len(faces) != 1 or not has_texture(faces[0]):
                raise ValueError('请选择一个带贴图的面')
            face_id = faces[0].GetID()
            dd.model.ClearSelection()
            tool = tool_class(self.view, face_id)
            if rotate_once:
                tool.rotate()
                from engine.tools.tool_select import SelectTool
                self.view.SetActiveTool(SelectTool(self.view))
            else:
                self.view.SetActiveTool(tool)
            self.view.MarkDirty()
            self.view.update()
            self.view.setFocus(QtCore.Qt.OtherFocusReason)
        except Exception as error:
            self.view.setStatusBar(str(error))

    @QtCore.Slot()
    @human_callback
    def on_actionTexturePosition_triggered(self):
        from engine.tools.tool_texture import MoveTextureTool
        self.activate_texture_tool(MoveTextureTool)

    @QtCore.Slot()
    @human_callback
    def on_actionTextureRotate_triggered(self):
        from engine.tools.tool_texture import RotateTextureTool
        self.activate_texture_tool(RotateTextureTool, rotate_once=True)

    def resolve_entities(self, entity_type):
        if not self.view.allow_tool_input():
            raise RuntimeError('请等待当前操作完成')
        dd = self.view.mainWindow.editing
        if self.session_state != (dd.token, dd.revision) or dd.edit.active is not None:
            raise RuntimeError('场景已变化或正在编辑，请重新打开菜单')
        comp = dd.model.GetActiveComponent()
        entities = [comp.GetEntityById(ident) for ident in self.entity_ids]
        if not entities or any(not isinstance(e, entity_type) or e.IsMarkedDeleted() for e in entities):
            raise RuntimeError('所选对象已失效，请重新选择')
        return dd, entities

    @QtCore.Slot()
    @human_callback
    def on_actionFlipFace_triggered(self):
        try:
            dd, faces = self.resolve_entities(core.CFace)
            with dd.edit.operation('翻转面'):
                for face in faces:
                    dd.edit.touch(dd.wrap(face.GetParentComponent()))
                    face.Flip()
            self.view.MarkDirty()
            self.view.update()
        except Exception as error:
            self.view.setStatusBar(str(error))

    @QtCore.Slot()
    @human_callback
    def on_actionExport_triggered(self):
        try:
            from pathlib import Path
            dd, entities = self.resolve_instances()
            name = Path(entities[0].name or '组件').name if len(entities) == 1 else '组件'
            del entities
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self.view, '导出组件', name + '.dim', 'DeepDraw 模型 (*.dim)')
            if not path:
                return
            path = Path(path)
            if path.suffix.lower() != '.dim':
                path = path.with_suffix('.dim')
                if path.exists() and QtWidgets.QMessageBox.question(self.view, '覆盖文件', '文件已存在，是否覆盖？',
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes:
                    return
            dd, entities = self.resolve_instances()
            from editing.asset_export import export_instances_file
            export_instances_file(dd, entities, path)
        except Exception as error:
            self.view.setStatusBar(str(error))

    @QtCore.Slot()
    @human_callback
    def on_actionExplode_triggered(self):
        self.change_instances('炸开')

    @QtCore.Slot()
    @human_callback
    def on_actionToGroup_triggered(self):
        self.change_instances('转成Group', True)

    @QtCore.Slot()
    @human_callback
    def on_actionToComponent_triggered(self):
        self.change_instances('转成CComponent', False)

    def change_instances(self, label, group=None):
        try:
            dd, entities = self.resolve_instances()
            with dd.edit.operation(label):
                if group is None:
                    dd.edit.explode([dd.wrap(e) for e in entities])
                else:
                    for entity in entities:
                        if entity.is_group == group:
                            continue
                        dd.edit.touch(dd.wrap(entity.GetParentComponent()))
                        entity.Record(True)
                        if group and len(dd.scene.definition_users(dd.wrap(entity.GetDefinition()))) > 1:
                            from editing.grouping import clone_group_definition
                            entity.SetDefinition(clone_group_definition(dd, entity.GetDefinition()))
                        entity.is_group = group
            self.view.MarkDirty()
            self.view.update()
        except Exception as error:
            self.view.setStatusBar(str(error))

    @QtCore.Slot()
    @human_callback
    def on_actionObjectProperties_triggered(self):
        if self.actionObjectProperties.isEnabled() and self.view.allow_tool_input():
            ObjectPropertiesDialog(self.view, self.object_text).exec_()
