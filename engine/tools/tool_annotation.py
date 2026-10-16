"""Two-click text leaders on a camera-aligned plane through the picked point."""
from engine.coordinates import to_world, local_ray, local_plane, local_vector, local_projection
import json
from engine import core
from engine.qt import QtGui, QtWidgets
from engine.mutation_guard import check_mutation
from engine.viewer.overlays import draw_inference
from engine.viewer.dimension_labels import paint_label
from .drawing_support import infer, draw_path
from .edit_tool_support import interactive, operation


@interactive
class AnnotationTool(core.IBaseTool):
    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view

    @property
    def is_begin(self):
        return self.anchor is not None

    def activate(self):
        self.anchor = self.end = self.hover = None
        self.input = core.CInputPointFinder(self.view.view_proxy)
        self.view.setMouseTracking(True)
        self.view.setStatusBar('文字标注：捕捉起点，拉出引线后单击输入文字；Esc 取消')

    def deactivate(self):
        self.view.setMouseTracking(False)

    def begin(self, point):
        self.anchor = self.end = point
        forward = self.view.GetCameraForward().Normalized()
        self.right = forward.Cross(self.view.GetCameraUp()).Normalized()
        self.up = self.right.Cross(forward).Normalized()
        self.plane = local_plane(self.view,core.CPlane(forward,to_world(self.view,point)))
        self.right = local_vector(self.view,self.right)
        self.up = local_vector(self.view,self.up)
        self.stub = max(.1, self.view.camera_zoom*.015)

    def on_mouse_move(self, pos, mod):
        if not self.is_begin:
            self.hover = infer(self.view, self.input, pos)
        else:
            ray = local_ray(self.view,pos.x(), pos.y())
            if abs(self.plane.GetNormal().Dot(ray.dir)) < 1e-7:
                self.view.setStatusBar('视线平行于标注平面，请调整视角')
                return
            self.end = ray.PointAt(self.plane.IntersectWithLine(ray))
        self.view.update()

    def on_left_button_down(self, pos, mod):
        self.on_mouse_move(pos, mod)
        if not self.is_begin:
            if self.hover is not None:self.begin(self.hover)
            return
        if (self.end-self.anchor).Length()<.001:return
        self.request_text()

    def on_left_button_up(self, pos):
        pass

    def request_text(self):
        host = self.view.mainWindow
        state = (host.editing.token, host.editing.revision, self.view.model.GetActiveComponent().GetID())
        text, accepted = QtWidgets.QInputDialog.getText(self.view, '文字标注', '输入标注文字')
        check_mutation()
        if (host.input_busy or self.view.active_tool is not self
                or state != (host.editing.token, host.editing.revision, self.view.model.GetActiveComponent().GetID())
                or host.editing.edit.active is not None):
            raise ValueError('模型或工具已改变，请重新创建标注')
        if accepted and text.strip():self.create(text.strip())
        self.activate()

    def geometry(self):
        delta = self.end-self.anchor
        sign = 1 if delta.Dot(self.right)>=0 else -1
        tip = self.end+self.right*self.stub*sign
        lines = [(self.anchor,self.end),(self.end,tip)]
        if delta.Length()>.001:
            direction = delta.Normalized()
            side = self.plane.GetNormal().Cross(direction).Normalized()
            size = min(self.stub*.4,delta.Length()*.2)
            lines += [(self.anchor,self.anchor+direction*size+side*size*.35),
                      (self.anchor,self.anchor+direction*size-side*size*.35)]
        return lines,tip,sign

    @operation('创建文字标注')
    def create(self, text):
        if not text.strip() or len(text)>256:raise ValueError('请输入 1 至 256 个字符')
        dd = self.view.mainWindow.editing
        parent = dd.wrap(self.view.model.GetActiveComponent())
        name = '文字标注';index = 1
        while name in parent.names():
            index += 1;name = '文字标注%d'%index
        obj = dd.build.component(name, parent=parent)
        lines,tip,sign = self.geometry()
        for a,b in lines:dd.build.line(a.ToTuple(),b.ToTuple(),target=obj.definition)
        obj.definition.native.description = json.dumps(dict(kind='text_annotation',version=1,
            text=text,anchor=self.anchor.ToTuple(),label_position=tip.ToTuple(),
            elbow=self.end.ToTuple(),align='left' if sign>0 else 'right',
            plane_normal=self.plane.GetNormal().ToTuple()),ensure_ascii=False)
        dd.edit.touch(obj.definition)
        self.view.model.SetSelection([obj.native])
        return obj

    def draw(self, gl):
        if not self.is_begin:
            draw_inference(self.view,self.input,gl)
            return
        gl.glPushAttrib(gl.GL_ENABLE_BIT|gl.GL_CURRENT_BIT|gl.GL_LINE_BIT)
        try:
            gl.glDisable(gl.GL_LIGHTING);gl.glDisable(gl.GL_TEXTURE_2D)
            for a,b in self.geometry()[0]:draw_path(gl,[a,b])
        finally:gl.glPopAttrib()

    def draw_2d(self, painter):
        if not self.is_begin:return
        _,point,sign = self.geometry()
        projection = local_projection(self.view)
        paint_label(self.view,painter,projection,point,'输入文字', 'left' if sign>0 else 'right')
