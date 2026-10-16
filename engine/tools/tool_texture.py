"""Face texture tools adapted from editor_dist/plugins/painter.py."""
from engine.coordinates import local_ray
import math
from engine import core
from .edit_tool_support import interactive, operation
from .transaction_tool import TransactionTool


def has_texture(face):
    material = face.GetMaterial()
    return material is not None and material.GetTexture() is not None


class TextureTool(TransactionTool):
    def __init__(self, view, face_id):
        super().__init__(view)
        self.face_id = face_id

    def face(self):
        face = self.view.model.GetActiveComponent().GetEntityById(self.face_id)
        if not isinstance(face, core.CFace) or face.IsMarkedDeleted() or not has_texture(face):
            raise ValueError('所选面没有贴图，请重新选择')
        return face

    def matrix(self):
        coords = self.face().GetTextureCoords()
        return coords.GetFrontTextureCoords() if coords is not None else core.CMatrix33.NewFromTranslate(0, 0)

    def set_matrix(self, matrix):
        # Replace the coordinates so both initially absent and existing UVs undo.
        self.face().SetTextureCoords(core.CFaceTextureCoords.Load(matrix).AddToUndoManager())


@interactive
class MoveTextureTool(TextureTool):
    def activate(self):
        self.cancel_preview()
        self.start = None
        self.view.setMouseTracking(True)
        self.view.setStatusBar('贴图位置：单击起点，移动鼠标，单击确认；Esc 取消')

    def texture_point(self, pos):
        face = self.face()
        plane = face.GetPlane()
        ray = local_ray(self.view,pos.x(), pos.y())
        if abs(plane.GetNormal().Dot(ray.dir)) < 1e-9:
            raise ValueError('视线平行于面，请调整视角')
        point = ray.PointAt(plane.IntersectWithLine(ray))
        return core.UVHelper(face, None).ProjToFace(point)

    def begin_move(self, point):
        self.initial = self.matrix()
        self.start = point
        self.begin_transaction('贴图位置')

    def preview_move(self, point):
        self.view.mainWindow.editing.edit.require_operation()
        delta = point - self.start
        self.set_matrix(self.initial.Multiply(core.CMatrix33.NewFromTranslate(delta.x, delta.y)))
        self.refresh()

    def on_left_button_down(self, pos, mod):
        point = self.texture_point(pos)
        if self.transaction is None:
            self.begin_move(point)
        else:
            self.preview_move(point)
            self.commit()
            self.activate()

    def on_mouse_move(self, pos, modifiers):
        if self.transaction is not None:
            self.preview_move(self.texture_point(pos))


class RotateTextureTool(TextureTool):
    """One-shot command; never installed as the active mouse tool."""

    @operation('贴图旋转')
    def rotate(self):
        self.set_matrix(self.matrix().Multiply(core.CMatrix33.NewFromRotate(math.pi * .5)))
