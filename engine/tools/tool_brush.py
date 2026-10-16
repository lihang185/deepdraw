"""Paint in the active context; Ctrl samples the visible face material."""
from engine.coordinates import hit_in_active
from engine import core
from engine.qt import QtCore
from .edit_tool_support import interactive, operation


@interactive
class BrushTool(core.IBaseTool):
    @property
    def is_begin(self):
        return False

    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view
        self.material_id = None
        self.sampled = False
        # Tool instances are recreated on every toolbar activation. Restore the
        # current scene material shown by the panel, not the library selection.
        host = view.mainWindow
        dock = getattr(host, 'material_library_dock', None)
        asset = getattr(dock, 'scene_material', None)
        if asset is not None:
            ident = asset.get('material_id')
            if ident is None:
                self.sampled = True
            elif asset.get('session_token') == host.editing.token:
                material = next((view.model.getMaterial(i)
                                 for i in range(view.model.getNumMaterials())
                                 if view.model.getMaterial(i).GetID() == ident
                                 and not view.model.getMaterial(i).IsMarkedDeleted()), None)
                if material is not None:
                    self.material_id = ident
                    self.sampled = True
                else:
                    dock.clear_scene_material()

    def activate(self):
        self.picker = core.CPickHelper(self.view.view_proxy)
        self.view.setMouseTracking(True)
        self.view.setStatusBar('材质刷：Ctrl+单击吸取材质，单击面或组件涂刷；Esc 清除吸取材质')

    def deactivate(self):
        self.view.setMouseTracking(False)

    def set_material(self, material):
        self.material_id = material.GetID() if material is not None else None
        self.sampled = True
        self.view.setStatusBar('当前材质：' + (material.name if material is not None else '默认材质') + '；单击涂刷，Ctrl+单击吸取')

    def draw(self, gl):
        pass

    def on_mouse_move(self, pos, modifiers):
        pass

    def on_left_button_up(self, pos):
        pass

    def on_cancel(self):
        self.material_id = None
        self.sampled = False
        dock = getattr(self.view.mainWindow, 'material_library_dock', None)
        if dock is not None:
            dock.clear_scene_material()
        self.activate()

    def on_left_button_down(self, pos, mod):
        self.picker.Reset()
        self.picker.SinglePick(pos.x(), pos.y(), 9, None, True)
        hit = self.picker.PickedFace()
        if not hit:
            return
        if mod & QtCore.Qt.ControlModifier:
            material = hit.e.GetMaterial()
            if material is None:
                for instance in reversed(list(hit.inst_path)):
                    material = instance.GetMaterial()
                    if material is not None:
                        break
            self.material_id = material.GetID() if material is not None else None
            self.sampled = True
            self.view.mainWindow.show_right_panels('material_library_dock')
            self.view.mainWindow.material_library_dock.show_scene_material(material)
            self.view.setStatusBar('已吸取：' + (material.name if material is not None else '默认材质') + '；单击涂刷，Ctrl+单击重新吸取')
            return
        if not self.sampled:
            self.view.setStatusBar('请先 Ctrl+单击吸取材质')
            return
        material = None
        if self.material_id is not None:
            model = self.view.model
            material = next((model.getMaterial(i) for i in range(model.getNumMaterials())
                             if not model.getMaterial(i).IsMarkedDeleted()
                             and model.getMaterial(i).GetID() == self.material_id), None)
            if material is None:
                self.on_cancel()
                self.view.setStatusBar('吸取的材质已失效，请重新吸取')
                return
        if not hit_in_active(self.view,hit):return
        component = self.view.model.GetActiveComponent()
        target = next((e for e in list(hit.inst_path) + [hit.e]
                       if e.GetParentComponent() == component), None)
        if target is not None and target.GetMaterial() != material:
            self.paint(target, material)

    @operation('材质刷', material_only=True)
    def paint(self, entity, material):
        entity.Record(True)
        entity.SetMaterial(material)
