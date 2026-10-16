from engine.coordinates import world_length, local_distance, world_vector, to_world, to_local, active_matrix, transform_plane
from engine.viewer.overlays import draw_inference
import math
from engine import core
from .edit_tool_support import interactive,operation
from .drawing_support import infer,plane_at,basis,draw_path,commit_path,length,show_length

@interactive
class DrawCircleTool(core.IBaseTool):
    @property
    def is_begin(self):
        return getattr(self, 'center', None) is not None

    input_prompt='半径[,分段数]（例如 50cm,96）'
    default_sides=24
    curved=True
    def __init__(self,view):
        super().__init__(view.view_proxy);self.view=view;self.num_side=self.default_sides
    def activate(self):
        self.input=core.CInputPointFinder(self.view.view_proxy)
        self.center=self.end_point=None;self.view.setMouseTracking(True)
    def deactivate(self):self.view.setMouseTracking(False)
    def point(self,pos):
        return infer(self.view,self.input,pos,self.center,self.plane if self.center is not None else None)
    def points(self):
        center=to_world(self.view,self.center)
        delta=world_vector(self.view,self.end_point-self.center);radius=delta.Length()
        plane=transform_plane(active_matrix(self.view),self.plane)
        x=delta.Normalized() if radius>core.EPS else world_vector(self.view,self.dir_s).Normalized()
        y=plane.GetNormal().Normalized().Cross(x)
        return [to_local(self.view,center+(x*math.cos(2*math.pi*i/self.num_side)+
                y*math.sin(2*math.pi*i/self.num_side))*radius) for i in range(self.num_side)]
    def draw(self,gl):
        draw_inference(self.view, self.input, gl)
        if self.center is not None:draw_path(gl,self.points(),True)
    @operation('Draw circle / polygon', local_geometry=True)
    def commit(self):
        if (self.end_point-self.center).Length()<=core.EPS:raise ValueError('半径必须为正数')
        commit_path(self,self.points(),True,curve=self.curved)
    def on_left_button_down(self,pos,mod):
        point=self.point(pos)
        if self.center is None:
            self.center=self.end_point=point;self.plane=plane_at(self.view,self.input,point,pos)
            self.dir_s,self.dir_t=basis(self.plane)
            self.view.setStatusBar('选择半径端点；Enter 输入半径,边数；Esc 取消')
        else:self.end_point=point;self.commit();self.activate()
    def on_mouse_move(self,pos,modifiers):
        self.end_point=self.point(pos)
        if self.center is not None:show_length(self,world_length(self.view,self.end_point-self.center),'半径：')
    def enterValue(self,value):
        if self.center is None:raise ValueError('请先选择圆心')
        parts=str(value).replace('，',',').split(',')
        if len(parts)>2:raise ValueError('请输入半径[,边数]')
        radius=length(self,parts[0])
        if len(parts)==2:
            n=int(parts[1])
            if not 3<=n<=720:raise ValueError('边数须为3到720的整数')
            self.num_side=n
        delta=self.end_point-self.center
        direction=delta.Normalized() if delta.Length()>core.EPS else self.dir_s
        if radius<=core.EPS:raise ValueError('半径必须为正数')
        self.end_point=self.center+direction*local_distance(self.view,direction,radius);self.commit();self.activate()
    def on_left_button_up(self,pos):pass
    def on_cancel(self):self.activate()

class DrawPolygonTool(DrawCircleTool):
    curved=False
    default_sides=6
    input_prompt='外接圆半径,边数（例如 50cm,6）'
