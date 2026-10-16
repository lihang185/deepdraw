from engine.coordinates import local_distance
from engine.viewer.overlays import draw_inference
from engine import core
from .edit_tool_support import interactive, operation
from .drawing_support import infer,faces_at,draw_path,commit_path,length

@interactive
class DrawRectTool(core.IBaseTool):
    @property
    def is_begin(self):
        return getattr(self, 'state', 1) == 2

    input_prompt='宽,高（例如 100,60；可带 cm、mm、m）'
    def __init__(self,view):
        super().__init__(view.view_proxy);self.view=view
    def reset(self):
        self.state=1;self.start_point=self.end_point=None
        self.start_point_faces=[];self.on_face=None
    def activate(self):
        self.input=core.CInputPointFinder(self.view.view_proxy)
        self.view.setMouseTracking(True);self.reset()
    def deactivate(self):self.view.setMouseTracking(False)
    def init_face_space(self,plane):
        self.dir_s=core.CVector3D();self.dir_t=core.CVector3D()
        self.dir_s,self.dir_t=plane.ComputeST()

    def calc_plane_by_two_point(self,p1,p2):
        # Legacy editor rule: XY, XZ, YZ, then the vertical plane through both points.
        delta=p2-p1
        if abs(delta.z)<core.EPS:normal=core.CVector3D(0,0,1)
        elif abs(delta.y)<core.EPS:normal=core.CVector3D(0,1,0)
        elif abs(delta.x)<core.EPS:normal=core.CVector3D(1,0,0)
        else:normal=core.CVector3D(0,0,1).Cross(core.CVector3D(delta.x,delta.y,0)).Normalized()
        return core.CPlane(normal,p1)

    def update_plane(self,point):
        end_faces={face.GetID():face for face in faces_at(self.input)}
        shared=[face for face in self.start_point_faces if face.GetID() in end_faces]
        if shared:
            # Retain a common face across mouse moves instead of arbitrary set order.
            self.on_face=next((f for f in shared if f==self.on_face),min(shared,key=lambda f:f.GetID()))
            from .drawing_support import plane_at
            self.on_face_plane=plane_at(self.view,self.input,point,None)
        else:
            self.on_face=None
            self.on_face_plane=self.calc_plane_by_two_point(self.start_point,point)
        self.init_face_space(self.on_face_plane)

    def get_point(self,px,py):
        from engine.qt import QtCore
        # Both corners are inferred freely. Do not project the second corner onto
        # a plane chosen at the first click: the two corners decide the plane.
        point=infer(self.view,self.input,QtCore.QPoint(px,py))
        if self.state==2:self.update_plane(point)
        return point

    def points(self,p1,p3):
        diff=p3-p1
        p2=p1+self.dir_s*diff.Dot(self.dir_s)
        p4=p1+self.dir_t*diff.Dot(self.dir_t)
        return [p1,p2,p2+(p4-p1),p4]
    def draw(self,gl):
        draw_inference(self.view, self.input, gl)
        if self.state==2:
            draw_path(gl,self.points(self.start_point,self.end_point),True)
            
            size = self.view.camera_zoom * 0.01
            core.draw_target_with_size(self.start_point, size, gl)
            core.draw_target_with_size(self.end_point, size, gl)
            
    def on_left_button_down(self,pos,mod):
        point=self.get_point(pos.x(),pos.y())
        if self.state==1:
            self.start_point=self.end_point=point
            self.start_point_faces=faces_at(self.input)
            self.on_face=None
            self.on_face_plane=core.CPlane(core.CVector3D(0,0,1),point)
            self.init_face_space(self.on_face_plane);self.state=2
            self.view.setStatusBar('选择对角点；Enter 输入宽,高；Esc 取消')
        else:
            self.draw_rect_operation(self.start_point,point);self.reset()
    def on_mouse_move(self,pos,modifiers):self.end_point=self.get_point(pos.x(),pos.y())
    @operation('Draw rectangle', local_geometry=True)
    def draw_rect_operation(self,p1,p3):commit_path(self,self.points(p1,p3),True)
    def enterValue(self,value):
        if self.state!=2:raise ValueError('请先选矩形起点')
        parts=str(value).replace('，',',').split(',')
        if len(parts)!=2:raise ValueError('请输入宽,高')
        w,h=(length(self,p) for p in parts)
        if min(w,h)<=core.EPS:raise ValueError('宽高必须为正数')
        w=local_distance(self.view,self.dir_s,w);h=local_distance(self.view,self.dir_t,h)
        diff=self.end_point-self.start_point
        w*=(-1 if diff.Dot(self.dir_s)<0 else 1);h*=(-1 if diff.Dot(self.dir_t)<0 else 1)
        self.draw_rect_operation(self.start_point,self.start_point+self.dir_s*w+self.dir_t*h);self.reset()
    def on_left_button_up(self,pos):pass
    def on_cancel(self):self.reset()
