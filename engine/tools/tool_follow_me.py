"""Preselect a planar path, then click a section to sweep a new component."""
from engine.coordinates import inverse_matrix, active_matrix
from engine import core
from editing import sweep_geometry as geo
from .edit_tool_support import interactive, operation


def section_plan(sweeps, path, closed, face, matrix):
    if face.GetNumLoops() != 1:
        raise ValueError('暂不支持带孔截面')
    uses = list(face.GetOuterLoop().EnumEdgeUse())
    points = [tuple(matrix.Transform(u.GetStartVertex().p).ToTuple()) for u in uses]
    center = tuple(sum(p[i] for p in points)/len(points) for i in range(3))
    pairs = list(zip(path, path[1:]+path[:1] if closed else path[1:]))
    candidates = []
    for a,b in pairs:
        direction = geo.unit(geo.sub(b,a))
        distance = max(0, min(geo.length(geo.sub(b,a)), geo.dot(geo.sub(center,a),direction)))
        origin = geo.add(a,geo.mul(direction,distance))
        candidates.append((geo.length(geo.sub(center,origin)),origin,direction))
    _,origin,direction = min(candidates,key=lambda x:x[0])
    up = None
    for a,b in pairs:
        normal = geo.cross(direction,geo.sub(b,a))
        if geo.length(normal)>geo.EPS:
            up = geo.unit(normal)
            break
    if up is None:
        axis = min(((0,0,1),(0,1,0),(1,0,0)),key=lambda a:abs(geo.dot(a,direction)))
        up = geo.unit(geo.sub(axis,geo.mul(direction,geo.dot(axis,direction))))
    # Deterministic orientation for planar paths, including vertical ones.
    dominant = max(range(3),key=lambda i:abs(up[i]))
    if up[dominant]<0: up=geo.mul(up,-1)
    if any(abs(geo.dot(geo.sub(p,points[0]),direction))>geo.EPS for p in points):
        raise ValueError('截面需垂直于最近的路径段')
    lateral = geo.cross(up,direction)
    profile = [(geo.dot(geo.sub(p,origin),lateral),geo.dot(geo.sub(p,origin),up)) for p in points]
    curves = [u.GetEdge().GetCurve() for u in uses]
    return sweeps.plan(profile,path,closed=closed,up=up,
                       profile_curves=[c.GetID() if c is not None else None for c in curves])


@interactive
class FollowMeTool(core.IBaseTool):
    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view

    def activate(self):
        self.is_begin = False
        self.plan = None
        self.path = None
        self.picker = core.CPickHelper(self.view.view_proxy)
        self.view.setMouseTracking(True)
        dd = self.view.mainWindow.editing
        selected = list(self.view.model.GetSelection())
        try:
            if not selected or any(e.IsMarkedDeleted() or e.GetParentComponent()!=self.view.model.GetActiveComponent() for e in selected):
                raise ValueError('请先选择连续路径线段，或一个面作为闭合路径')
            self.path,self.closed = dd.sweep.chain([dd.wrap(e) for e in selected])
            self.is_begin = True
            self.view.setStatusBar('路径跟随：移动到截面预览，单击生成；Esc 取消')
        except (ValueError,TypeError) as error:
            self.view.setStatusBar(str(error))

    def deactivate(self):
        self.plan = None
        self.is_begin = False
        self.view.setMouseTracking(False)

    def on_cancel(self):
        self.plan = None
        self.path = None
        self.is_begin = False
        self.view.setStatusBar('已取消路径跟随，请重新选择路径并启动工具')

    def on_mouse_move(self,pos,mod):
        self.plan = None
        if self.path is None:return
        self.picker.SinglePick(pos.x(),pos.y(),9,None, True)
        hit = self.picker.PickedFace()
        if hit is None:return
        try:
            self.plan = section_plan(self.view.mainWindow.editing.sweep,self.path,self.closed,hit.e,inverse_matrix(active_matrix(self.view)).Multiply(hit.matrix()))
            self.view.setStatusBar('单击生成路径跟随组件；Esc 取消')
        except ValueError as error:
            self.view.setStatusBar(str(error))
        self.view.update()

    def on_left_button_down(self,pos,mod):
        self.on_mouse_move(pos,mod)
        if self.plan is not None:
            self.create()
            self.on_cancel()

    def on_left_button_up(self,pos):pass

    @operation('路径跟随')
    def create(self):
        dd = self.view.mainWindow.editing
        parent = dd.wrap(self.view.model.GetActiveComponent())
        name = '路径跟随'; i = 1
        while name in parent.names():
            i += 1; name = '路径跟随%d'%i
        result = dd.sweep._build(name,self.plan,parent)
        self.view.model.SetSelection([result.native])
        return result

    def draw(self,gl):
        if self.plan is None:return
        vertices = self.plan['vertices']
        edges = {tuple(sorted((a,b))) for face in self.plan['faces'] for a,b in zip(face,face[1:]+face[:1])}
        gl.glPushAttrib(gl.GL_ENABLE_BIT|gl.GL_CURRENT_BIT|gl.GL_LINE_BIT)
        try:
            gl.glDisable(gl.GL_LIGHTING);gl.glDisable(gl.GL_TEXTURE_2D)
            gl.glColor3f(.8,.2,.8);gl.glLineWidth(2)
            gl.glBegin(gl.GL_LINES)
            for a,b in edges:
                gl.glVertex3d(*vertices[a]);gl.glVertex3d(*vertices[b])
            gl.glEnd()
        finally:gl.glPopAttrib()
