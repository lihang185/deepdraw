import core

class GuideLineTool(core.IBaseTool):
    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view

    def activate(self):
        self.state = core.PressState.press_first
        self.is_begin = False
        self.snap_line = False
        self.start_point = None
        self.prev_point = None
        self.end_point = core.CVector3D()
        
        self.input = core.CInputPointFinder(self.view.view_proxy)
        
        self.view.setMouseTracking(True)
        
    def deactivate(self):
        self.view.setMouseTracking(False)

    def draw(self, gl):
        self.input.Draw()
        
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
        input = self.input
        input.Reset()
        
        self.snap_axis = 8
        
        #=======================
        # Pick
        if self.state == core.PressState.press_first:
            ok = input.Inference(px, py, None, None)
        else:
            ok = input.Inference(px, py, None, self.start_point)
        assert ok
        new_point = input.Position()
        
        return new_point
    
    def on_left_button_down(self, pos, mod):
        #=======================
        # input_point
        new_point = self.do_input_inference(pos.x(), pos.y())
        
        if self.state == core.PressState.press_first:
            self.state = core.PressState.press_second
            
            snap_type = self.input.snap_type
            
            if snap_type == core.SnapType.edge or snap_type == core.SnapType.edge_center:
                e = self.input.snap_to
                line_start, line_dir, line_len = core.edge_to_ray(e)

                self.line_origin = new_point
                self.line_dir = line_dir
                
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
                self.line_dir = axis_dir
                
                self.snap_line = True
            
            elif snap_type == core.SnapType.guide_line:

                self.line_origin = new_point
                #self.snap_to = self.input.snap_to
                line = self.input.snap_to.GetStraightLine()
                # snap_to释放后，对其dir的引用就失效了
                # 因该用line.dir.copy()
                self.line_dir = line.dir
                
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
            dir_end = new_point - self.line_origin
            dir_up = dir_end.Normalized().Cross(self.line_dir)
            dir_ok = self.line_dir.Cross(dir_up).Normalized()
            
            dist = dir_end.Dot(dir_ok)
            self.end_point = self.line_origin + dir_ok * dist
        else:
            self.end_point = new_point
            self.line_origin = new_point
        
        # 计算长度
        line_len = (self.end_point - self.line_origin).Length()
        
        #print("snap_type:", su_algo.snap_type_name(self.input.snap_type), self.input.snap_type)
        
        do_snap_at = core.SnapType.axis_plane, core.SnapType.last_point_axis, core.SnapType.axis, core.SnapType.face
        if self.input.snap_type in do_snap_at and line_len > core.EPS:
            dir = (self.end_point - self.line_origin).Normalized()
            self.end_point = self.line_origin.MoveForward(dir, line_len)

    def on_left_button_up(self, pos):
        pass

    def create_guide_line(self, orig, _dir):
        self.view.model.UndoManager().StartOperation("Tape")
        fac = core.CEntityFactory(self.view.model)
        guide = fac.NewGuideLine()
        guide.orig = orig
        guide.dir = _dir
        
        comp = self.view.model.GetActiveComponent()
        comp.AddEntity(guide)

        self.view.model.UndoManager().CommitOperation()
        self.view.MarkDirty()

