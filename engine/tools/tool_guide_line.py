from engine.coordinates import world_length, local_distance, world_vector, to_world, to_local, active_matrix, inverse_matrix, local_vector
from engine.viewer.overlays import draw_inference
from engine import core
from .edit_tool_support import interactive, operation
from .drawing_support import length, show_length

@interactive
class GuideLineTool(core.IBaseTool):
    @property
    def is_begin(self):
        return getattr(self, 'state', core.PressState.press_first) == core.PressState.press_second

    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view

    def activate(self):
        self.state = core.PressState.press_first
        self.snap_line = False
        self.start_point = None
        self.prev_point = None
        self.end_point = core.CVector3D()
        
        self.input = core.CInputPointFinder(self.view.view_proxy)
        
        self.view.setMouseTracking(True)
        
    def deactivate(self):
        self.view.setMouseTracking(False)

    def draw(self, gl):
        draw_inference(self.view, self.input, gl)
        
        if self.state == core.PressState.press_second:
            size = self.view.camera_zoom * 0.01
            core.draw_target_with_size(self.start_point, size, gl)
            core.draw_target_with_size(self.end_point, size, gl)

            gl.glColor3f(0.0, 0.0, 0.0);
            core.draw_line(self.start_point, self.end_point, gl)
            
            if self.snap_line:
                self.draw_temp_guide_line(self.end_point, self.line_dir, gl)

    def draw_temp_guide_line(self, orig, dir, gl):
        inf = 100000
        p1 = orig + dir * inf
        p2 = orig + dir * -inf
        gl.glColor3f(0.24, 0.36, 0.53)
        core.draw_line(orig, p1, gl)
        core.draw_line(orig, p2, gl)

    def do_input_inference(self, px, py):
        from engine.qt import QtCore
        from .drawing_support import infer
        return infer(self.view,self.input,QtCore.QPoint(px,py),self.start_point)

    def enterValue(self,value):
        if not self.snap_line:raise ValueError('先选择边或辅助线并移动鼠标确定偏移方向')
        value = length(self, value)
        delta=self.end_point-self.line_origin
        if delta.Length()<=core.EPS:raise ValueError('请先确定偏移方向')
        self.create_guide_line(self.line_origin+delta.Normalized()*local_distance(self.view,delta,value),self.line_dir)
        self.activate()

    def picked_direction(self, entity, origin, direction, point):
        """Convert definition-local line direction through the picked instance path."""
        candidates=[]
        for hit in self.input.pick_helper.GetPicked():
            path=[item for item in hit.inst_path if isinstance(item,core.CComponentInstance)]
            owner=path[-1].GetDefinition() if path else self.view.model.GetTopComponent()
            if owner!=entity.GetParentComponent():continue
            matrix=inverse_matrix(active_matrix(self.view))
            for instance in path:matrix=matrix.Multiply(instance.GetTransform().Multiply(instance.GetAnimationTransform()))
            start=matrix.Transform(origin)
            vector=matrix.Transform(origin+direction)-start
            if vector.Length()<=core.EPS:continue
            vector=vector.Normalized()
            delta=point-start
            distance=(delta-vector*delta.Dot(vector)).Length()
            candidates.append((distance,vector))
        if not candidates:raise ValueError('无法确定参考边的组件路径，请重新选择')
        return min(candidates,key=lambda item:item[0])[1]

    def on_left_button_down(self, pos, mod):
        #=======================
        # input_point
        self.on_mouse_move(pos, mod)
        new_point = self.do_input_inference(pos.x(), pos.y())
        
        if self.state == core.PressState.press_first:
            self.state = core.PressState.press_second
            
            snap_type = self.input.snap_type
            
            if snap_type == core.SnapType.edge or snap_type == core.SnapType.edge_center:
                e = self.input.snap_to
                line_start, line_dir, line_len = core.edge_to_ray(e)

                self.line_origin = new_point
                self.line_dir = self.picked_direction(e,line_start,line_dir,new_point)
                
                self.snap_line = True

            elif snap_type == core.SnapType.axis:
                axis_id = self.input.snap_to_id
                if axis_id == 0:
                    axis_dir = core.CVector3D(1, 0, 0)
                elif axis_id == 1:
                    axis_dir = core.CVector3D(0, 1, 0)
                elif axis_id == 2:
                    axis_dir = core.CVector3D(0, 0, 1)

                self.line_origin = new_point
                self.line_dir = local_vector(self.view,axis_dir).Normalized()
                
                self.snap_line = True
            
            elif snap_type == core.SnapType.guide_line:

                self.line_origin = new_point
                #self.snap_to = self.input.snap_to
                line = self.input.snap_to.GetStraightLine()
                # snap_to释放后，对其dir的引用就失效了
                # 因该用line.dir.copy()
                self.line_dir = self.picked_direction(self.input.snap_to,line.PointAt(0),
                    core.CVector3D(line.dir.x,line.dir.y,line.dir.z),new_point)
                
                self.snap_line = True

            else:
               
                self.snap_line = False
            
            self.end_point = self.start_point = new_point
        
        elif self.state == core.PressState.press_second:
            self.state = core.PressState.press_first
            
            if self.snap_line:
                
                self.create_guide_line(self.end_point, self.line_dir)
            else:
                self.end_point = new_point
            
            self.snap_line = False
    
  
    def on_mouse_move(self, pos, modifiers):
        #=======================
        # input_point
        new_point = self.do_input_inference(pos.x(), pos.y())
        
        if self.snap_line:
            direction=world_vector(self.view,self.line_dir).Normalized()
            delta=world_vector(self.view,new_point-self.line_origin)
            self.end_point=to_local(self.view,to_world(self.view,self.line_origin)+delta-direction*delta.Dot(direction))
        else:
            self.end_point = new_point
            if self.state == core.PressState.press_first:
                self.line_origin = new_point
        
        # 计算长度
        line_len = (self.end_point - self.line_origin).Length()
        if self.state == core.PressState.press_second:
            show_length(self, world_length(self.view,self.end_point-self.line_origin), '距离：')
        
        #print("snap_type:", su_algo.snap_type_name(self.input.snap_type), self.input.snap_type)
        
        do_snap_at = core.SnapType.axis_plane, core.SnapType.last_point_axis, core.SnapType.axis, core.SnapType.face
        if self.input.snap_type in do_snap_at and line_len > core.EPS:
            dir = (self.end_point - self.line_origin).Normalized()
            self.end_point = self.line_origin.MoveForward(dir, line_len)

    def on_left_button_up(self, pos):
        pass

    @operation('Guide line', local_geometry=True)
    def create_guide_line(self, orig, _dir):
        fac = core.CEntityFactory(self.view.model)
        guide = fac.NewGuideLine()
        guide.orig = orig
        guide.dir = _dir
        
        comp = self.view.model.GetActiveComponent()
        comp.AddEntity(guide)

        self.view.MarkViewDirty()

