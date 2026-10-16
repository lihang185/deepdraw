from engine.coordinates import world_length, local_distance, to_local, hit_in_active, local_ray
from engine.viewer.overlays import draw_inference
"""HMI push/pull with a live solid preview inside one undo transaction."""
from engine import core
from engine.push_pull import PushPullController
from .edit_tool_support import interactive


class PreviewCanceled(Exception):
    pass


@interactive
class PushTool(core.IBaseTool):
    @property
    def is_begin(self):
        return self.transaction is not None

    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view
        self.transaction = None

    def activate(self):
        self.cancel_preview()
        self.face = None
        self.distance = 0.0
        self.input = core.CInputPointFinder(self.view.view_proxy)
        self.view.setMouseTracking(True)

    def deactivate(self):
        self.cancel_preview()
        self.face = None
        self.view.setMouseTracking(False)

    def on_left_button_down(self, pos, mod):
        if self.face is None:
            pick = core.CPickHelper(self.view.view_proxy)
            pick.SinglePick(pos.x(), pos.y(), 9, None, True)
            hit = pick.PickedFace()
            if not hit_in_active(self.view,hit) or hit.e.GetParentComponent() != self.view.model.GetActiveComponent():
                self.view.setStatusBar('请选择当前编辑层的面；组件请先双击进入')
                return
            self.face = hit.e
            plane = self.face.GetPlane()
            self.direction = plane.GetNormal()
            ray = local_ray(self.view,pos.x(),pos.y())
            self.origin = ray.PointAt(plane.IntersectWithLine(ray))
            self.distance = 0.0
            edit = self.view.mainWindow.editing.edit
            self.transaction = edit.operation('Push/pull', local_geometry=True)
            self.transaction.__enter__()
            edit.touch(self.view.mainWindow.editing.wrap(self.view.model.GetActiveComponent()))
            self.controller = PushPullController()
            self.controller.begin(self.face, self.view.model)
            
            #===================
            # 注意：
            # PushPullController会创建新的面
            # 老的self.face可能会被删除
            # 如果Selection中还有self.face
            # 绘制select_face会导致崩溃
            #===================
            from engine.entity_refs import live_entities
            select_ls = live_entities([self.controller.push_face])
            self.view.model.SetSelection(select_ls)
            
            self.invalidate_preview()
        else:
            self.on_mouse_move(pos, mod)
            if abs(self.distance) > core.EPS:
                self.commit()
            
            #===================
            # 注意：
            # 自动开孔，推挤到重合面
            # 会自动push_face
            # 必须清空Selection
            # 否则会导致崩溃
            #===================
            self.view.model.ClearSelection()
            self.activate()

    def commit(self):
        if self.transaction is None:
            return
        self.controller.finish()
        transaction, self.transaction = self.transaction, None
        transaction.__exit__(None, None, None)
        self.face = None
        self._revision = self.view.mainWindow.editing.revision
        self.view.MarkViewDirty()
        self.view.update()

    def cancel_preview(self):
        if self.transaction is not None:
            transaction, self.transaction = self.transaction, None
            self.face = None
            error = PreviewCanceled('取消推拉预览')
            try:
                transaction.__exit__(PreviewCanceled, error, None)
            except PreviewCanceled:
                pass
            self._revision = self.view.mainWindow.editing.revision
            self.view.MarkViewDirty()
            self.view.update()

    def on_cancel(self):
        self.activate()

    def preview_distance(self, distance):
        if abs(distance-self.distance) <= core.EPS:
            return
        self.controller.push(self.direction * (distance - self.distance))
        self.distance = distance
        self.invalidate_preview()
        self.view.update()

    def on_mouse_move(self, pos, modifiers):
        if self.face is None:
            return
        self.input.Reset()
        entity_filter = core.EntityFilter(lambda entity: entity not in self.controller.filter_set)
        found = self.input.Inference(pos.x(), pos.y(), entity_filter, None)
        if found and self.input.snap_type in (core.SnapType.vertex, core.SnapType.edge, core.SnapType.edge_center, core.SnapType.face):
            point = to_local(self.view,self.input.Position())
            distance = (point - self.origin).Dot(self.direction)
            # Ignore the unmoved source plane; otherwise it would hold the preview at zero.
            if abs(distance) > core.EPS:
                self.preview_distance(distance)
                self.view.setStatusBar('推拉吸附距离：%.3f；单击确认，Esc 取消' % (world_length(self.view,self.direction)*distance))
                return
        ray = local_ray(self.view,pos.x(), pos.y())
        axis = core.CStraightLine(self.origin, self.direction)
        ok, distance, unused = core.CStraightLine.ComputeNearestPoint(axis, ray)
        if ok:
            from engine.units import snap_integer
            distance = snap_integer(distance)
            self.preview_distance(distance)
            self.view.setStatusBar('推拉距离：%.3f；单击确认，Esc 取消' % (world_length(self.view,self.direction)*distance))

    def enterValue(self, value):
        if self.transaction is None:
            raise ValueError('请先选择推拉面')
        # Mouse distances retain the original axis. Numeric input follows the
        # current face normal, which reverses when a new extrusion crosses zero.
        value=local_distance(self.view,self.direction,value)
        self.preview_distance(-value if self.distance < 0 else value)
        self.commit()
        self.activate()

    def on_left_button_up(self, pos):
        pass

    def draw(self, gl):
        if self.face is None:
            return
        draw_inference(self.view, self.input, gl)

    def invalidate_preview(self):
        """Moving a face does not change the component-instance hierarchy."""
        from engine.viewer.render_changes import RenderChange
        comp = self.view.model.GetActiveComponent()
        comp.MarkBoundingBoxDirty()
        self.view.pipeline.apply_render_change(RenderChange(components=(comp,), local_geometry=True))
        self.view.MarkViewDirty()

