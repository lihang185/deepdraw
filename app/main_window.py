"""Education main window: model lifetime, actions and application UI composition."""

import sys
import traceback
from pathlib import Path

from engine.qt import QtCore, QtWidgets, QtGui
from engine.mutation_guard import human_callback, check_mutation
from engine.tools.tool_select import SelectTool
from engine import core, model_files
from engine.tools.tool_draw_line import DrawLineTool
from engine.tools.tool_draw_rect import DrawRectTool
from engine.tools.tool_draw_circle import DrawCircleTool, DrawPolygonTool
from engine.tools.tool_draw_arc import DrawArcTool
from engine.tools.tool_guide_line import GuideLineTool
from engine.tools.tool_push import PushTool
from engine.tools.tool_offset import OffsetTool
from engine.tools.tool_follow_me import FollowMeTool
from engine.tools.tool_move import MoveTool
from engine.tools.tool_rotate import RotateTool, rotate_next_quadrant
from engine.tools.tool_protractor import ProtractorTool
from engine.tools.tool_dimension import DimensionTool
from engine.tools.tool_annotation import AnnotationTool
from engine.tools.tool_camera import LookTool, PositionCameraTool, WalkTool
from engine.tools.tool_scale import ScaleTool
from engine.tools.tool_section import SectionTool
from engine.tools.tool_erase import EraseTool
from engine.tools.tool_brush import BrushTool
from engine.tools.tool_comp_place import ComponentPlaceTool


from engine.tools.tool_camera import OrbitTool, PanTool
from engine.scenes import SceneManager
from editing.context import EditingContext
from .ui.Ui_main_window import Ui_MainWindow
LARGE_SCENE_BYTES = 30 * 1024 * 1024

from .paths import ROOT, DATA, SKETCHUP


class EditorMainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    """Own the native model and compose education panels and human tools."""

    about_to_release = QtCore.Signal()
    model_changed = QtCore.Signal()
    scene_applied = QtCore.Signal()
    right_panel_names = ('library_dock', 'material_library_dock', 'layer_dock')

    # Window and document lifetime

    def __init__(self, startup_model=None):
        super().__init__()
        self.model = None
        self.editing = None
        self.current_model_path = ''
        self._native_file = False
        self.version = 0
        self.exiting = False
        self.input_busy = False
        self.ready = False
        self.startup_error = None
        self.startup_model = startup_model
        self._ready_attempts = 0
        self.setupUi(self)
        self.menuBar.setEnabled(False)
        self.toolBar.setEnabled(False)
        self.view.mainWindow = self
        self.view.model = self.view.pipeline = None
        self.view.show_section_planes = self.view.section_cut_enabled = True
        self.scenes = SceneManager(self)
        self.scene_applied.connect(self.sync_shadow_actions)
        self.create_panels()
        from app.ui.selection_layer import SelectionLayer
        self.selection_layer = SelectionLayer(self)
        self.toolBar.addWidget(self.selection_layer)
        from app.extensions.ui import UIManager
        from app.extensions.manager import SimpleExtensionManager
        self.ui_manager = UIManager.create(self)
        self.extension_manager = SimpleExtensionManager.create(self)
        QtCore.QTimer.singleShot(0, self.init_system)

    def init_system(self):
        if self.ready or self.exiting or self.startup_error:
            return
        if not self.view.isValid() or not hasattr(self.view, 'gl'):
            self._ready_attempts += 1
            if self._ready_attempts > 100:
                self.startup_error = 'OpenGL 初始化失败'
                self.statusBar().showMessage(self.startup_error)
            else:
                QtCore.QTimer.singleShot(100, self.init_system)
            return
        try:
            # Keep the current engine's licensing contract, without AI services.
            self.bind_model(core.CModel())
            core.core.license.start(int(self.winId()), '1.0')
            self.ready = True
            self.menuBar.setEnabled(True)
            self.toolBar.setEnabled(True)
            self.load_plugins()
            if self.startup_model is not None:
                self.load_file(self.startup_model, show_progress=False)
            self.statusBar().showMessage('左键建模 · 中键旋转 · Shift+中键平移 · 滚轮缩放 · Enter 输入尺寸')
        except Exception as error:
            self.startup_error = str(error)
            traceback.print_exc()
            self.statusBar().showMessage('启动失败：' + str(error))

    @property
    def diagnostics(self):
        return self.editing.diagnostics if self.editing else None

    def release_model(self):
        if self.model is None:
            return
        self.cancel_tool()
        self.about_to_release.emit()
        self.editing.alive = False
        self.view.makeCurrent()
        try:
            self.view.ReleaseModel()
            self.model.DisableUndo()
            self.model.Release()
            self.model.Deactivate()
            core.set_active_model(None)
            self.model = None
            self.editing = None
        finally:
            self.view.doneCurrent()

    def bind_model(self, model):
        self.release_model()
        model.Activate()
        model.EnableUndo()
        self.model = model
        core.set_active_model(model)
        core.set_active_view(self.view)
        self.view.makeCurrent()
        try:
            self.view.BindModel(model)
        finally:
            self.view.doneCurrent()
        self.editing = EditingContext(self.view)
        self.view.SetActiveTool(SelectTool(self.view))
        self.version += 1
        self.model_changed.emit()
        self.view.MarkDirty()
        self.view.update()

    def closeEvent(self, event):
        self.cancel_tool()
        if self.ready and not self.confirm_replace():
            event.ignore()
            return
        self.exiting = True
        process = getattr(self, '_import_process', None)
        if process is not None:
            process.kill()
            process.waitForFinished(2000)
        self.release_model()
        super().closeEvent(event)

    # Panels and tool dispatch

    def create_panels(self):
        from app.ui.model_browser import ModelBrowser
        from app.ui.material_library_dock import MaterialLibraryDock
        from app.ui.model_library_dock import ModelLibraryDock
        from app.ui.layer_dock import LayerDock
        self.model_browser = ModelBrowser()
        self.model_browser.model_requested.connect(lambda path: self.run_action(self.insert_model, path))
        self.library_dock = ModelLibraryDock(self, self.model_browser, 'modelLibrary', '模型库')
        self.material_library_dock = MaterialLibraryDock(self)
        self.layer_dock = LayerDock(self)
        self.setDockOptions(self.dockOptions() | QtWidgets.QMainWindow.AllowTabbedDocks)
        self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtWidgets.QTabWidget.South)
        for name in self.right_panel_names:
            panel = getattr(self, name)
            self.add_right_dock(panel)
            panel.installEventFilter(self)
        self.about_to_release.connect(self.clear_materials)
        self.show_right_panels('library_dock')

    def add_right_dock(self, dock):
        """Share the right sidebar height through tabs instead of vertical splits."""
        area = QtCore.Qt.RightDockWidgetArea
        peers = [widget for widget in self.findChildren(QtWidgets.QDockWidget)
                 if widget is not dock and not widget.isFloating()
                 and self.dockWidgetArea(widget) == area]
        self.addDockWidget(area, dock)
        if peers:
            self.tabifyDockWidget(peers[0], dock)

    def show_right_panels(self, selected):
        if selected not in self.right_panel_names:
            raise ValueError('Unknown panel: ' + selected)
        for name in self.right_panel_names:
            getattr(self, name).show()
        getattr(self, selected).raise_()

    def close_right_panels(self):
        for name in self.right_panel_names:
            getattr(self, name).hide()

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Close and any(
                watched is getattr(self, name, None) for name in self.right_panel_names):
            self.close_right_panels()
        return super().eventFilter(watched, event)

    def clear_materials(self):
        self.material_library_dock.clear_scene_material()

    @human_callback
    def run_action(self, callback, *args):
        """Qt event boundary: report human tool failures in the status bar."""
        try:
            check_mutation()
            if self.input_busy:
                raise RuntimeError('请等待当前建模操作完成')
            callback(*args)
        except Exception as error:
            self.statusBar().showMessage(str(error), 10000)

    def activate_tool(self, tool_class):
        current = self.view.active_tool
        if getattr(current, 'transaction', None) is not None:
            current.cancel_preview()
        if self.editing.edit.active is not None:
            raise RuntimeError('请先完成当前建模操作')
        self.statusBar().showMessage('Esc 取消当前绘制；中键环绕，Shift+中键平移')
        self.view.SetActiveTool(tool_class(self.view))
        self.view.setFocus(QtCore.Qt.OtherFocusReason)

    def cancel_tool(self):
        if self.view.active_tool is not None:
            self.view.SetActiveTool(None)

    def ensure_idle(self):
        if self.input_busy:
            raise RuntimeError("正在载入模型，请稍候")
        if not self.ready:
            raise RuntimeError(self.startup_error or '引擎尚未就绪')
        if self.editing.edit.active is not None:
            raise RuntimeError('请先完成或取消当前操作')

    # Files and isolated SketchUp import

    def confirm_replace(self):
        if self.editing.revision or list(self.model.GetTopComponent().EnumEntities()):
            return QtWidgets.QMessageBox.question(self, '替换模型', '当前模型将被替换，未保存修改会丢失。是否继续？',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes
        return True

    def new_model(self):
        self.ensure_idle()
        if not self.confirm_replace():
            return
        self.bind_model(core.CModel())
        self.current_model_path = ''
        self._native_file = False

    def load_file(self, filename, *, show_progress=True):
        self.ensure_idle()
        from .ui.load_progress_dialog import LoadProgressDialog
        dialog = LoadProgressDialog(self) if show_progress else None
        candidate = core.CModel()
        self.input_busy = self.view.loading_model = True
        try:
            if dialog is not None:dialog.show()
            model_files.load_sketchup_model(candidate, str(filename),
                                             progress=dialog.update_progress if dialog is not None else None)
            self.bind_model(candidate)
            candidate = None
            if dialog is not None and Path(filename).stat().st_size >= LARGE_SCENE_BYTES and dialog.ask_initialize():
                self.view.pipeline.initialize_geometry(dialog.update_progress)
        finally:
            if candidate is not None:candidate.Release()
            self.input_busy = self.view.loading_model = False
            if dialog is not None:
                dialog.hide()
                dialog.deleteLater()
            self.view.update()
        self.current_model_path = str(Path(filename).absolute())
        from engine.native_serialization import MAGIC
        with open(filename, 'rb') as stream:self._native_file = stream.read(len(MAGIC)) == MAGIC
        #self.fit_view()
        return True

    def save_model(self, save_as=False, path=None, native=None):
        self.ensure_idle()
        filename = path or (None if save_as else self.current_model_path)
        if not filename:
            filename, selected = QtWidgets.QFileDialog.getSaveFileName(self, '保存教育版模型', self.current_model_path or str(ROOT/'data/未命名.dim'), 'DeepDraw 模型 (*.dim);;DeepDraw 大场景原生模型 (*.dim)')
            if filename:native = '大场景' in selected
        if not filename:
            return
        filename = Path(filename).with_suffix(".dim")
        native = self._native_file if native is None else native
        model_files.save_sketchup_model(self.model, str(filename), native=native)
        self._native_file = native
        self.current_model_path = str(filename.absolute())
        self.statusBar().showMessage('已保存：' + self.current_model_path)
        return filename

    def insert_model(self, path=None):
        self.ensure_idle()
        if not path:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, '插入模型', str(DATA), 'DeepDraw 模型 (*.dim)')
        if not path:
            return
        self.activate_tool(ComponentPlaceTool)
        # Imported definitions precede placement; the tool owns placement undo.
        definition = model_files.load_sketchup_model_as_component(self.model, str(path))
        self.view.active_tool.configure(definition)
        self.view.active_tool.preview_point(core.CVector3D())

    def import_skp(self):
        self.ensure_idle()
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self,'导入 SketchUp',str(DATA),'SketchUp (*.skp)')
        if filename:
            self.start_skp_import(filename)

    def start_skp_import(self, filename):
        if getattr(self, '_import_process', None) is not None:
            raise RuntimeError('请等待当前导入完成')
        self.ensure_idle()
        source = Path(filename).resolve()
        output = source.with_suffix('.dim')
        if output.exists():
            answer = QtWidgets.QMessageBox.question(
                self, '覆盖模型文件', '同名 DAI 文件已存在，是否覆盖？\n' + str(output),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if answer != QtWidgets.QMessageBox.Yes:
                return
        filename = str(source)
        token = self.editing.token
        process = QtCore.QProcess(self)
        self._import_process = process
        process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        process.finished.connect(lambda code, status: self.finish_skp_import(code, output, token))
        process.errorOccurred.connect(lambda error: self.import_start_failed(error))
        if getattr(sys, 'frozen', False):
            # A packaged client dispatches the isolated converter via itself.
            program, args = sys.executable, ['--convert-skp', str(SKETCHUP), filename, str(output)]
        else:
            program, args = sys.executable, [str(SKETCHUP/'convert.py'),str(SKETCHUP),filename,str(output)]
        process.start(program, args)
        self.statusBar().showMessage('正在导入 SketchUp…')

    def import_start_failed(self, error):
        if error == QtCore.QProcess.FailedToStart:
            self.finish_skp_import(-1, None, None)

    def finish_skp_import(self, code, output, token):
        process = self._import_process
        if process is None:
            return
        self._import_process = None
        details = bytes(process.readAllStandardOutput()).decode('utf-8', errors='replace')
        try:
            if self.exiting:
                return
            if code or output is None or not output.is_file():
                raise RuntimeError('SketchUp 导入失败：' + details[-1000:])
            self.statusBar().showMessage('已生成：' + str(output))
            if self.editing is None or self.editing.token != token:
                raise RuntimeError('导入期间模型已切换，DAI 已生成，可从模型库插入：' + str(output))
            self.run_action(self.insert_model, output)
        except Exception as error:
            self.statusBar().showMessage(str(error), 15000)
        finally:
            process.deleteLater()

    # Selection and editing

    def hide_selected(self):
        """隐藏当前组件内选中的对象。"""
        model = self.view.model
        component = model.GetActiveComponent()
        entities = [e for e in model.GetSelection()
                    if isinstance(e, core.CDrawingElement) and not e.IsMarkedDeleted()
                    and e.GetParentComponent() == component and not e.IsHide()]
        if not entities:
            return
        with self.editing.edit.operation('隐藏'):
            self.editing.edit.touch(self.editing.wrap(component))
            for entity in entities:
                entity.Record(True)
                entity.SetHide(True)
            model.ClearSelection()
        self.view.MarkViewDirty()
        self.view.update()

    def unhide_all_in_active_component(self):
        """取消当前打开组件这一层的全部隐藏，不依赖选择，不递归子组件。"""
        model = self.view.model
        component = model.GetActiveComponent()
        entities = [e for e in component.EnumEntities()
                    if isinstance(e, core.CDrawingElement) and not e.IsMarkedDeleted()
                    and e.GetParentComponent() == component and e.IsHide()]
        if not entities:
            return
        with self.editing.edit.operation('取消隐藏'):
            self.editing.edit.touch(self.editing.wrap(component))
            for entity in entities:
                entity.Record(True)
                entity.SetHide(False)
            model.ClearSelection()
        self.view.MarkDirty()
        self.view.update()

    def delete_selected(self):
        self.erase_entities(list(self.view.model.GetSelection()), '删除选中对象')

    def delete_guides(self):
        component = self.view.model.GetActiveComponent()
        self.erase_entities([e for e in component.EnumEntities() if isinstance(e, core.CGuideLine)],
                            '删除参考线')

    def erase_entities(self, entities, label):
        """HMI deletion in the current editing component, inside one undo operation."""
        edit = self.editing.edit
        if edit.active is not None:
            raise RuntimeError('请先完成当前建模操作')
        component = self.view.model.GetActiveComponent()
        entities = [e for e in entities if not e.IsMarkedDeleted()]
        if not entities:
            return
        if any(e.GetParentComponent() != component for e in entities):
            raise ValueError('只能删除当前编辑层的对象')
        # As in the HMI implementation: faces before their edges/other entities.
        entities.sort(key=lambda e: 0 if isinstance(e, core.CFace) else 1)
        with edit.operation(label, local_geometry=all(not isinstance(e, core.CComponentInstance) for e in entities)):
            edit.touch(self.editing.wrap(component))
            self.view.model.ClearSelection()
            for entity in entities:
                if not entity.IsMarkedDeleted():
                    entity.Erase(component)
        self.view.MarkViewDirty()
        self.view.update()

    def group_selection(self, explode=False):
        if self.editing.edit.active is not None:
            raise RuntimeError('请先完成当前编辑操作')
        with self.editing.edit.operation('解组' if explode else '成组'):
            if explode:self.editing.edit.explode()
            else:self.editing.edit.group()
        self.view.MarkViewDirty();self.view.update()

    def mirror_selected(self):
        selected = list(self.model.GetSelection())
        if not selected or any(not isinstance(e, core.CComponentInstance) for e in selected):
            raise ValueError('请先选择组或组件')
        with self.editing.edit.operation('沿局部 X 镜像'):
            mirror = core.CMatrix()
            mirror.SetRow(0, core.CVector3D(-1,0,0))
            mirror.is_identity = False
            for entity in selected:
                self.editing.edit.set_transform(self.editing.wrap(entity), entity.GetTransform().Multiply(mirror))

    def copy_selection(self):
        from editing.clipboard import copy
        self._clipboard = copy(self.editing)
        self.statusBar().showMessage('已复制选中对象')

    def cut_selection(self):
        self.copy_selection()
        self.delete_selected()

    def paste_selection(self):
        from editing.clipboard import paste_definition
        if not getattr(self, '_clipboard', None):
            raise ValueError('请先复制模型对象')
        self.activate_tool(ComponentPlaceTool)
        definition = paste_definition(self.model, self._clipboard)
        self.view.active_tool.configure(definition, is_group=True)
        self.view.active_tool.preview_point(core.CVector3D())

    def open_component(self):
        selected = list(self.model.GetSelection())
        if len(selected)!=1 or not isinstance(selected[0],core.CComponentInstance):
            raise ValueError('请选择一个组件')
        self.view.OpenComponent(selected[0])

    # View and display

    @QtCore.Slot()
    def on_actionRenderStats_triggered(self):
        visible = self.actionRenderStats.isChecked()
        dock = getattr(self, 'render_stats_dock', None)
        if dock is None:
            from .ui.render_stats_dock import RenderStatsDock
            dock = self.render_stats_dock = RenderStatsDock(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
            dock.setFloating(True)
        dock.setVisible(visible)

    @QtCore.Slot()
    def on_actionTest4_triggered(self):
        self.view.test_disable_frustum_culling = self.actionTest4.isChecked()
        self.view.update()

    def fit_view(self):
        if self.model is None:
            return
        comp = self.model.GetActiveComponent()
        if not list(comp.EnumEntities()):
            return
        comp.ComputeBoundingBox()
        box = comp.GetBoundingBox()
        from engine.coordinates import active_matrix, transform_bounds
        from types import SimpleNamespace
        bounds=transform_bounds(active_matrix(self.view),dict(min=[box.min_x,box.min_y,box.min_z],max=[box.max_x,box.max_y,box.max_z]))
        box=SimpleNamespace(**{side+"_"+axis:bounds[side][i] for side in ("min","max") for i,axis in enumerate("xyz")})
        _, vertical_fov, aspect = self.view.ComputeFOV()
        self.view.camera.fit_bounds(box, vertical_fov, aspect)
        self.view.onViewChanged()
        self.view.update()

    def choose_display_unit(self):
        units=['cm','mm','m','in','ft']
        value,ok=QtWidgets.QInputDialog.getItem(self,'显示单位','长度显示及无后缀输入单位',units,
            units.index(getattr(self.view,'display_unit','cm')),False)
        if ok:self.view.display_unit=value

    def create_text(self):
        if self.editing.edit.active is not None:
            raise RuntimeError('请先完成或取消当前建模操作')
        state=(self.editing.token,self.editing.revision,self.view.model.GetActiveComponent().GetID())
        from app.ui.text_dialog import TextDialog
        dialog=TextDialog(self)
        if dialog.exec_()!=QtWidgets.QDialog.Accepted:return
        check_mutation()
        if self.input_busy or self.editing.edit.active is not None:
            raise RuntimeError('请等待当前建模操作完成')
        if state!=(self.editing.token,self.editing.revision,self.view.model.GetActiveComponent().GetID()):
            raise RuntimeError('场景或编辑层已变化，请重新创建文字')
        from engine.tools.tool_text import TextPlaceTool
        self.activate_tool(TextPlaceTool)
        tool=self.view.active_tool
        tool.set_plan(dialog.plan)
        try:tool.preview_point(core.CVector3D())
        except Exception:
            tool.on_cancel()
            raise

    def toggle_section_view(self, name):
        setattr(self.view,name,not getattr(self.view,name,True))
        self.view.update()

    def clear_sections(self):
        self.erase_entities([e for e in self.view.model.GetActiveComponent().EnumEntities()
                             if isinstance(e, core.CSectionPlane)], '清除剖切面')

    def set_light_from_view(self):
        from engine.viewer.shadows import affine, camera_light_direction
        matrix = core.CMatrix()
        direction = camera_light_direction(self.view.camera, affine(matrix))
        self.configure_shadows(True)
        self.view.shadow_direction = direction
        self.view.update()
        self.statusBar().showMessage('已按当前视角设置光源并开启阴影；旋转视角不会移动光源', 6000)

    def configure_shadows(self, enabled=None, resolution=None):
        enabled = self.view.shadows_enabled if enabled is None else enabled
        resolution = self.view.shadow_resolution if resolution is None else resolution
        self.view.makeCurrent()
        try:
            if enabled:
                self.view.pipeline.shadow_pass().native.configure(resolution)
            self.view.shadows_enabled = enabled
            self.view.shadow_resolution = resolution
        finally:
            self.view.doneCurrent()
        self.view.update()

    def sync_shadow_actions(self):
        self.actionShadows.setChecked(self.view.shadows_enabled)
        for action, size in ((self.actionShadowLow,1024),(self.actionShadowMedium,2048),(self.actionShadowHigh,4096)):
            action.setChecked(self.view.shadow_resolution == size)

    # Extensions

    def load_plugins(self):
        """Keep the extension manager; never load old native-pointer plugins."""
        import ast
        import runpy
        self.plugin_compatibility = {}
        for path in sorted((ROOT/'plugins').glob('*.py')):
            try:
                tree = ast.parse(path.read_text(encoding='utf-8-sig'))
                compatible = any(isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'DEEPDRAW_ENGINE_API' for t in node.targets)
                    and isinstance(node.value, ast.Constant) and node.value.value == 2 for node in tree.body)
                if not compatible:
                    self.plugin_compatibility[path.name] = '未加载：旧引擎接口，需适配后声明 DEEPDRAW_ENGINE_API = 2'
                    continue
                runpy.run_path(str(path))
                self.plugin_compatibility[path.name] = '已加载'
            except Exception as error:
                self.plugin_compatibility[path.name] = '加载失败：' + str(error)
        self.extension_manager.start_all()

    # Additional window operations


    def open_model(self):
        self.ensure_idle()
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, '打开教育版模型', self.current_model_path or str(DATA), 'DeepDraw 模型 (*.dim)')
        if filename and self.confirm_replace():
            self.load_file(filename)

    def toggle_xray(self):
        self.view.pipeline.xray_mode = not self.view.pipeline.xray_mode
        self.view.update()

    # Named Qt Designer slots (keep on the concrete QObject class).

    @QtCore.Slot()
    def on_actionBrush_triggered(self):
        self.run_action(self.activate_tool, BrushTool)

    @QtCore.Slot()
    def on_actionFollowMe_triggered(self):
        self.run_action(self.activate_tool, FollowMeTool)

    @QtCore.Slot()
    def on_actionDimension_triggered(self):
        self.run_action(self.activate_tool, DimensionTool)

    @QtCore.Slot()
    def on_actionAnnotation_triggered(self):
        self.run_action(self.activate_tool, AnnotationTool)

    @QtCore.Slot()
    def on_actionInsertModel_triggered(self):
        self.run_action(self.insert_model)

    @QtCore.Slot()
    def on_actionSave_triggered(self):
        self.run_action(self.save_model)

    @QtCore.Slot()
    def on_actionSaveAs_triggered(self):
        self.run_action(self.save_model, True)

    @QtCore.Slot()
    def on_actionHide_triggered(self):
        self.run_action(self.hide_selected)

    @QtCore.Slot()
    def on_actionUnhide_triggered(self):
        self.run_action(self.unhide_all_in_active_component)

    @QtCore.Slot()
    def on_actionImportSkp_triggered(self):
        self.run_action(self.import_skp)

    @QtCore.Slot()
    def on_actionMove_triggered(self):
        self.run_action(self.activate_tool, MoveTool)

    @QtCore.Slot()
    def on_actionRotate_triggered(self):
        self.run_action(self.activate_tool, RotateTool)

    @QtCore.Slot()
    def on_actionProtractor_triggered(self):
        self.run_action(self.activate_tool, ProtractorTool)

    @QtCore.Slot()
    def on_actionLook_triggered(self):
        self.run_action(self.activate_tool, LookTool)

    @QtCore.Slot()
    def on_actionLayers_triggered(self):
        self.run_action(self.show_right_panels,'layer_dock')

    @QtCore.Slot()
    def on_actionWalk_triggered(self):
        self.run_action(self.activate_tool, WalkTool)

    @QtCore.Slot()
    def on_actionPositionCamera_triggered(self):
        self.run_action(self.activate_tool, PositionCameraTool)

    @QtCore.Slot()
    def on_actionScale_triggered(self):
        self.run_action(self.activate_tool, ScaleTool)

    @QtCore.Slot()
    def on_actionSection_triggered(self):
        self.run_action(self.activate_tool, SectionTool)

    @QtCore.Slot()
    def on_actionText3D_triggered(self):
        self.run_action(self.create_text)

    @QtCore.Slot()
    def on_actionSectionPlanes_triggered(self):
        self.run_action(self.toggle_section_view,'show_section_planes')
        self.actionSectionPlanes.setChecked(self.view.show_section_planes)

    @QtCore.Slot()
    def on_actionLightFromView_triggered(self):
        self.run_action(self.set_light_from_view)
        self.sync_shadow_actions()

    @QtCore.Slot()
    def on_actionShadows_triggered(self):
        self.run_action(self.configure_shadows, self.actionShadows.isChecked())
        self.sync_shadow_actions()

    @QtCore.Slot()
    def on_actionShadowLow_triggered(self):
        self.run_action(self.configure_shadows, None, 1024)
        self.sync_shadow_actions()

    @QtCore.Slot()
    def on_actionShadowMedium_triggered(self):
        self.run_action(self.configure_shadows, None, 2048)
        self.sync_shadow_actions()

    @QtCore.Slot()
    def on_actionShadowHigh_triggered(self):
        self.run_action(self.configure_shadows, None, 4096)
        self.sync_shadow_actions()

    @QtCore.Slot()
    def on_actionSectionCut_triggered(self):
        self.run_action(self.toggle_section_view,'section_cut_enabled')
        self.actionSectionCut.setChecked(self.view.section_cut_enabled)

    @QtCore.Slot()
    def on_actionClearSections_triggered(self):
        self.run_action(self.clear_sections)

    @QtCore.Slot()
    def on_actionRotateNextQuadrant_triggered(self):
        self.run_action(rotate_next_quadrant, self.view)

    @QtCore.Slot()
    def on_actionErase_triggered(self):
        self.run_action(self.activate_tool, EraseTool)

    @QtCore.Slot()
    def on_actionNew_triggered(self):
        self.run_action(self.new_model)

    @QtCore.Slot()
    def on_actionOpen_triggered(self):
        self.run_action(self.open_model)

    @QtCore.Slot()
    def on_actionSelect_triggered(self):
        self.run_action(self.activate_tool, SelectTool)

    @QtCore.Slot()
    def on_actionFitCamera_triggered(self):
        self.run_action(self.fit_view)

    @QtCore.Slot()
    def on_actionUndo_triggered(self):
        self.run_action(self.editing.edit.undo)

    @QtCore.Slot()
    def on_actionRedo_triggered(self):
        self.run_action(self.editing.edit.redo)

    @QtCore.Slot()
    def on_actionDelete_triggered(self):
        self.run_action(self.delete_selected)

    @QtCore.Slot()
    def on_actionDeleteAllGuide_triggered(self):
        self.run_action(self.delete_guides)

    @QtCore.Slot()
    def on_actionModelLibrary_triggered(self):
        self.run_action(self.show_library)

    @QtCore.Slot()
    def on_actionMaterialLibrary_triggered(self):
        self.run_action(self.show_right_panels, 'material_library_dock')

    @QtCore.Slot()
    def on_actionDrawLine_triggered(self):
        self.run_action(self.activate_tool, DrawLineTool)

    @QtCore.Slot()
    def on_actionDrawRectangle_triggered(self):
        self.run_action(self.activate_tool, DrawRectTool)

    @QtCore.Slot()
    def on_actionGuideLine_triggered(self):
        self.run_action(self.activate_tool, GuideLineTool)

    @QtCore.Slot()
    def on_actionPushPull_triggered(self):
        self.run_action(self.activate_tool, PushTool)

    @QtCore.Slot()
    def on_actionOffset_triggered(self):
        self.run_action(self.activate_tool, OffsetTool)

    @QtCore.Slot()
    def on_actionGroup_triggered(self):self.run_action(self.group_selection)

    @QtCore.Slot()
    def on_actionExplode_triggered(self):self.run_action(self.group_selection,True)

    @QtCore.Slot()
    def on_actionDrawCircle_triggered(self):self.run_action(self.activate_tool,DrawCircleTool)

    @QtCore.Slot()
    def on_actionDrawPolygon_triggered(self):self.run_action(self.activate_tool,DrawPolygonTool)

    @QtCore.Slot()
    def on_actionDrawArc_triggered(self):self.run_action(self.activate_tool,DrawArcTool)

    @QtCore.Slot()
    def on_actionDisplayUnits_triggered(self):
        self.run_action(self.choose_display_unit)

    @QtCore.Slot()
    def on_actionmirror_triggered(self):
        self.run_action(self.mirror_selected)

    @QtCore.Slot()
    def on_actionCopy_triggered(self):
        self.run_action(self.copy_selection)

    @QtCore.Slot()
    def on_actionCut_triggered(self):
        self.run_action(self.cut_selection)

    @QtCore.Slot()
    def on_actionPaste_triggered(self):
        self.run_action(self.paste_selection)

    @QtCore.Slot()
    def on_actionxray_triggered(self):
        self.run_action(self.toggle_xray)

    @QtCore.Slot()
    def on_actionGuides_triggered(self):
        self.view.show_guides = not getattr(self.view, 'show_guides', True)
        self.view.update()

    @QtCore.Slot()
    def on_actionManager_Trays_triggered(self):
        if any(getattr(self, name).isVisible() for name in self.right_panel_names):
            self.close_right_panels()
        else:
            self.show_right_panels('library_dock')

    @QtCore.Slot()
    def on_actionPerferences_triggered(self):
        self.run_action(self.choose_display_unit)

    @QtCore.Slot()
    def on_actionAbout_triggered(self):
        QtWidgets.QMessageBox.information(self, '关于', 'DeepDraw 教育版\n独立人工建模客户端\nDAI 模型格式')

    @QtCore.Slot()
    def on_actionModel_Info_triggered(self):
        if self.editing is None:
            return
        report = self.diagnostics.validate()
        lines = ['模型检查：' + report['status'], '组件定义：' + str(len(list(self.model.GetDefinitionList())))]
        lines += ['\n插件兼容状态：'] + [name + '：' + status for name, status in getattr(self, 'plugin_compatibility', {}).items()]
        QtWidgets.QMessageBox.information(self, '模型信息', '\n'.join(lines))

    @QtCore.Slot()
    def on_actionDocuments_triggered(self):
        QtWidgets.QMessageBox.information(self, '建模操作', '左键选择／绘制；双击进入组件，双击空白退出。\n中键旋转，Shift+中键平移，滚轮缩放。\nEnter 输入精确尺寸；Esc 取消。\n移动工具 Ctrl 切换复制，方向键锁轴。\n文件仅使用 DAI 格式。')

    @QtCore.Slot()
    def on_actionExit_triggered(self):
        self.close()

    @QtCore.Slot()
    def on_actionorbit_triggered(self):
        self.run_action(self.activate_tool, OrbitTool)

    @QtCore.Slot()
    def on_actionpan_triggered(self):
        self.run_action(self.activate_tool, PanTool)

    @QtCore.Slot()
    def on_actionOpen_Component_triggered(self):
        self.run_action(self.open_component)

    @QtCore.Slot()
    def on_actionClose_Component_triggered(self):
        self.run_action(self.view.CloseComponent)

