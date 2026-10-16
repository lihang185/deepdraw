from engine.coordinates import to_local
from engine.viewer.overlays import draw_inference
"""Surface-snapped component placement, excluding the live preview instance."""
from engine import core
from .edit_tool_support import interactive
from .transaction_tool import TransactionTool


@interactive
class ComponentPlaceTool(TransactionTool):
    def __init__(self, view):
        super().__init__(view)
        self.comp_def = None
        self.material = None
        self.copy_mode = False
        self.is_group = False

    def activate(self):
        self.cancel_preview()
        self.instance = None
        self.input = core.CInputPointFinder(self.view.view_proxy)
        self.view.setMouseTracking(True)
        self.view.setStatusBar('放置组件：移动鼠标定位，单击确认；Ctrl 切换连续放置；Esc 取消未确认预览')

    def configure(self, definition, material=None, is_group=False):
        self.is_group = is_group
        self.comp_def = definition
        self.material = material

    def preview_point(self, point):
        if self.comp_def is None or self.comp_def.IsMarkedDeleted():
            raise ValueError('请先指定组件定义')
        if self.transaction is None:
            # Non-group placement adds an occurrence, not parent face/edge data.
            # Publish its membership once below, then track its transform.
            self.begin_transaction('放置组件', transform_targets=None if self.is_group else ())
        created = self.instance is None
        if created:
            self.instance = core.CEntityFactory(self.view.model).NewComponentInstance()
            from editing.grouping import clone_group_definition
            definition = clone_group_definition(self.view.mainWindow.editing, self.comp_def) if self.is_group else self.comp_def
            self.instance.SetDefinition(definition)
            self.instance.is_group = self.is_group
            self.instance.SetMaterial(self.material)
            self.instance.name = self.comp_def.name
            self.view.model.GetActiveComponent().AddEntity(self.instance)
        self.view.mainWindow.editing.edit.require_operation()
        matrix = core.CMatrix()
        matrix.SetRow(3, point)
        self.instance.SetTransform(matrix)
        if created:
            # Publish the new occurrence once. Subsequent
            # previews only move it; keep the hierarchy and geometry caches.
            self.transform_targets = (self.instance,)
            self.view.mainWindow.editing.edit.touch_transform(
                self.view.mainWindow.editing.wrap(self.instance))
            self.view.MarkDirty()
        self.refresh()

    def point(self, pos, origin=None):
        excluded = self.instance.GetID() if self.instance is not None else None
        entity_filter = core.EntityFilter(lambda entity: entity.GetID() != excluded)
        self.input.Reset()
        if not self.input.Inference(pos.x(), pos.y(), entity_filter, None):
            raise ValueError('无法确定放置点，请调整视角')
        # Native inference returns active-context coordinates, including nested
        # instance transforms. Do not intersect a definition-local face plane.
        point = to_local(self.view,self.input.Position())
        from .drawing_support import EXACT
        if self.input.snap_type not in EXACT and self.input.snap_type != core.SnapType.face:
            from engine.units import snap_integer
            point = core.CVector3D(*(snap_integer(v) for v in point.ToTuple()))
        return point

    def draw(self, gl):
        draw_inference(self.view, self.input, gl)

    def on_mouse_move(self, pos, modifiers):
        if self.comp_def is not None:
            self.preview_point(self.point(pos))

    def on_left_button_down(self, pos, mod):
        if self.comp_def is None:
            return
        self.preview_point(self.point(pos))
        self.commit()
        self.instance = None
        if not self.copy_mode:
            self.comp_def = None
            self.view.setStatusBar('已放置；可撤销。再次使用放置工具可继续放置')

    def on_cancel(self):
        self.activate()
        self.comp_def = None

    def on_ctrl_press(self):
        self.copy_mode = not self.copy_mode
        self.view.setStatusBar('连续放置已开启' if self.copy_mode else '单次放置')
