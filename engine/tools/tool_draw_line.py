from engine.coordinates import world_length, local_distance
from engine.viewer.overlays import draw_inference
from engine import core
from .edit_tool_support import interactive, operation
from .drawing_support import infer, draw_path, commit_path, length, show_length

@interactive
class DrawLineTool(core.IBaseTool):
    @property
    def is_begin(self):
        return getattr(self, 'prev_point', None) is not None

    input_prompt='线段长度（可带 cm、mm、m）'
    def __init__(self,view):
        super().__init__(view.view_proxy);self.view=view
    def reset(self):
        self.first_point=self.prev_point=self.cur_point=None
        self.is_first_point=True
    def activate(self):
        self.input=core.CInputPointFinder(self.view.view_proxy)
        self.view.setMouseTracking(True);self.reset()
    def deactivate(self):self.view.setMouseTracking(False)
    def draw(self,gl):
        draw_inference(self.view, self.input, gl)
        if self.prev_point is not None and self.cur_point is not None:
            draw_path(gl,[self.prev_point,self.cur_point],color=self.axis_color())
    def axis_color(self):
        delta=self.cur_point-self.prev_point
        active=[abs(value)>core.EPS for value in delta.ToTuple()]
        if sum(active)==1:
            return ((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))[active.index(True)]
        return (0.,0.,0.)

    def point(self,pos):
        return infer(self.view,self.input,pos,self.prev_point,refs=(self.first_point,))
    @operation('Draw line', local_geometry=True)
    def add_new_line(self):
        commit_path(self,[self.prev_point,self.cur_point])
    def accept(self,point):
        if self.prev_point is None:
            self.first_point=point;self.is_first_point=False
        else:
            if (point-self.prev_point).Length()<=core.EPS:return
            self.cur_point=point;self.add_new_line()
        self.prev_point=self.cur_point=point
    def on_left_button_down(self,pos,mod):self.accept(self.point(pos))
    def on_mouse_move(self,pos,modifiers):
        self.cur_point=self.point(pos)
        if self.prev_point is not None:show_length(self,world_length(self.view,self.cur_point-self.prev_point),'长度：')
    def enterValue(self,value):
        if self.prev_point is None or self.cur_point is None:raise ValueError('先选起点并移动鼠标确定方向')
        delta=self.cur_point-self.prev_point
        distance=length(self,value)
        if delta.Length()<=core.EPS or distance<=core.EPS:raise ValueError('请确定方向并输入正长度')
        self.accept(self.prev_point+delta.Normalized()*local_distance(self.view,delta,distance))
    def on_left_button_up(self,pos):pass
    def on_cancel(self):self.reset()
