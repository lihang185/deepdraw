from engine.coordinates import to_world, to_local, active_matrix, transform_plane
from engine.viewer.overlays import draw_inference
import math
from engine import core
from .edit_tool_support import interactive,operation
from .drawing_support import infer,plane_at,basis,draw_path,commit_path,length

@interactive
class DrawArcTool(core.IBaseTool):
    @property
    def is_begin(self):
        return getattr(self, 'state', 0) != 0

    input_prompt='弓高（相对弦中点，可带 cm、mm、m；负数反向）'
    def __init__(self,view):super().__init__(view.view_proxy);self.view=view
    def activate(self):
        self.input=core.CInputPointFinder(self.view.view_proxy)
        self.state=0;self.a=self.b=self.hover=None;self.view.setMouseTracking(True)
    def deactivate(self):self.view.setMouseTracking(False)
    def point(self,pos):
        return infer(self.view,self.input,pos,self.a,self.plane if self.state else None)
    def arc_points(self,height):
        a,b=to_world(self.view,self.a),to_world(self.view,self.b)
        plane=transform_plane(active_matrix(self.view),self.plane)
        chord=b-a;half=chord.Length()/2
        if half<=core.EPS or abs(height)<=core.EPS:raise ValueError('弦长和弓高必须非零')
        side=plane.GetNormal().Normalized().Cross(chord.Normalized())
        middle=(a+b)*.5
        center=middle+side*((height*height-half*half)/(2*height))
        x=a-center;radius=x.Length();x=x.Normalized()
        y=plane.GetNormal().Normalized().Cross(x)
        def angle(p):
            d=p-center;return math.atan2(d.Dot(y),d.Dot(x))%(2*math.pi)
        end=angle(b);through=angle(middle+side*height)
        if through>end:end-=2*math.pi
        n=max(12,min(180,int(abs(end)*24/math.pi)+1))
        points=[center+x*(radius*math.cos(end*i/n))+y*(radius*math.sin(end*i/n)) for i in range(n+1)]
        points[0]=a;points[-1]=b
        return [to_local(self.view,p) for p in points]
    def height(self):
        a,b=to_world(self.view,self.a),to_world(self.view,self.b)
        plane=transform_plane(active_matrix(self.view),self.plane)
        side=plane.GetNormal().Normalized().Cross((b-a).Normalized())
        return (to_world(self.view,self.hover)-(a+b)*.5).Dot(side)
    def draw(self,gl):
        draw_inference(self.view, self.input, gl)
        if self.state==1:draw_path(gl,[self.a,self.hover])
        elif self.state==2:
            try:draw_path(gl,self.arc_points(self.height()))
            except ValueError:draw_path(gl,[self.a,self.b])
    @operation('Draw arc', local_geometry=True)
    def commit(self,height):commit_path(self,self.arc_points(height),curve=True)
    def on_left_button_down(self,pos,mod):
        point=self.point(pos)
        if self.state==0:
            self.a=self.hover=point;self.plane=plane_at(self.view,self.input,point,pos);self.state=1
            self.view.setStatusBar('选择弧线终点')
        elif self.state==1:
            if (point-self.a).Length()<=core.EPS:return
            self.b=self.hover=point;self.state=2
            self.view.setStatusBar('选择弓高；Enter 输入弓高；Esc 取消')
        else:self.hover=point;self.commit(self.height());self.activate()
    def on_mouse_move(self,pos,modifiers):self.hover=self.point(pos)
    def enterValue(self,value):
        if self.state!=2:raise ValueError('先选择弧线两个端点')
        self.commit(length(self,value));self.activate()
    def on_left_button_up(self,pos):pass
    def on_cancel(self):self.activate()
