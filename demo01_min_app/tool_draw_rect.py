import core


class DrawRectTool(core.IBaseTool):
    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view
        self.activate()
        
    def reset(self):
        self.state = 1
        self.start_point = None
        self.end_point = None
    
    def activate(self):
        self.input = core.CInputPointFinder(self.view.view_proxy)
        #启动鼠标追踪
        self.view.setMouseTracking(True)
        self.reset()
    
    def deactivate(self):
        #关闭鼠标追踪
        self.view.setMouseTracking(False)
    
    #=====================
    # 预览
    #=====================
    def draw(self, gl):
        self.input.Draw()
        if self.state == 2:
            self.draw_temp_rect(self.start_point, self.end_point, gl)

    def draw_temp_rect(self, p1, p3, gl):
        p1, p2, p3, p4 = self.rect_points(p1, p3)

        gl.glColor3f(0.0, 0.0, 1.0);
        self.draw_line(p1, p2, gl)
        self.draw_line(p2, p3, gl)
        self.draw_line(p3, p4, gl)
        self.draw_line(p4, p1, gl)
    
    def draw_line(self, p1, p2, gl):
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(p1.x, p1.y, p1.z)
        gl.glVertex3d(p2.x, p2.y, p2.z)
        gl.glEnd()
    
    #=====================
    # 交互
    #=====================
    def init_face_space(self, plane):
        s, t = plane.ComputeST()
        self.dir_s = s
        self.dir_t = t

    def rect_points(self, p1, p3):
        delta = p3 - p1
        u = self.dir_s * delta.Dot(self.dir_s)
        v = self.dir_t * delta.Dot(self.dir_t)
        return p1, p1 + u, p1 + u + v, p1 + v

    def get_point(self, px, py):
        input = self.input
        input.Reset()
        ok = input.Inference(px, py, None, None)
        assert ok
        point = input.Position()
        if self.state == 2 and abs(self.on_face_plane.ProjPoint(point)) > core.EPS:
            origin, direction, _ = self.view.ComputeCameraRay(px, py)
            if abs(self.on_face_plane.GetNormal().Dot(direction)) < 1e-9:
                return self.end_point
            ray = core.CStraightLine(origin, direction)
            point = ray.PointAt(self.on_face_plane.IntersectWithLine(ray))
        return point

    def on_left_button_down(self, pos, mod):
        new_point = self.get_point(pos.x(), pos.y())

        if self.state == 1:
            self.start_point = new_point
            
            picker = self.input.pick_helper
            normal = (picker.GetFacePlane().GetNormal() if picker.PickedFace() is not None
                      else core.CVector3D(0, 0, 1))
            self.on_face_plane = core.CPlane(normal, new_point)
            self.init_face_space(self.on_face_plane)
            
            self.state = 2
        else:
            # create rect
            self.draw_rect_operation(self.start_point, new_point)
            self.state = 1
        
        self.end_point = new_point
    
    def on_left_button_up(self, pos):
        pass

    def on_mouse_move(self, pos, modifiers):
        self.end_point = self.get_point(pos.x(), pos.y())
    
    def on_cancel(self):
        self.reset()

    #=====================
    # 执行
    #=====================
    def draw_rect_operation(self, p1, p3):
        comp = self.view.model.GetActiveComponent()
        
        p1, p2, p3, p4 = self.rect_points(p1, p3)
        if (p2-p1).Length() <= core.EPS or (p4-p1).Length() <= core.EPS:
            return
        self.view.model.UndoManager().StartOperation("Draw rect")

        edge1 = comp.AddLine(p1, p2)
        edge2 = comp.AddLine(p2, p3)
        edge3 = comp.AddLine(p3, p4)
        edge4 = comp.AddLine(p4, p1)
        
        entity_ls = [
            edge1, edge2, edge3, edge4
        ]

        comp.CheckModel(entity_ls, None)

        self.view.model.UndoManager().CommitOperation()
        
        self.view.MarkDirty()


class DrawRectToolStep1(core.IBaseTool):
    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view
        self.activate()
        
    def reset(self):
        self.state = 1
        self.start_point = None
        self.end_point = None
    
    def activate(self):
        self.input = core.CInputPointFinder(self.view.view_proxy)
        #启动鼠标追踪
        self.view.setMouseTracking(True)
        self.reset()
    
    def deactivate(self):
        #关闭鼠标追踪
        self.view.setMouseTracking(False)
    
    def draw(self, gl):
        self.input.Draw()
        if self.state == 2:
            self.draw_temp_rect(self.start_point, self.end_point, gl)

    def draw_temp_rect(self, p1, p3, gl):
        diff = p3 - p1
        
        d = diff.Dot(self.dir_s)
        p2 = p1.MoveForward(self.dir_s, d)
        
        d = diff.Dot(self.dir_t)
        p4 = p1.MoveForward(self.dir_t, d)

        gl.glColor3f(0.0, 0.0, 1.0);
        self.draw_line(p1, p2, gl)
        self.draw_line(p2, p3, gl)
        self.draw_line(p3, p4, gl)
        self.draw_line(p4, p1, gl)
    
    def draw_line(self, p1, p2, gl):
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(*p1.ToTuple())
        gl.glVertex3d(*p2.ToTuple())
        gl.glEnd()
    
    def init_face_space(self, plane):
        s, t = plane.ComputeST()
        self.dir_s = s
        self.dir_t = t

    def get_point(self, px, py):
        input = self.input
        input.Reset()
        ok = input.Inference(px, py, None, None)
        assert ok
        return input.Position()

    def on_left_button_down(self, pos, mod):
        new_point = self.get_point(pos.x(), pos.y())

        if self.state == 1:
            self.start_point = new_point
            
            self.on_face_plane = core.CPlane(0, 0, 1, 0)
            self.init_face_space(self.on_face_plane)
            
            self.state = 2
        else:
            # create rect
            self.state = 1
        
        self.end_point = new_point
    
    def on_left_button_up(self, pos):
        pass

    def on_mouse_move(self, pos, modifiers):
        self.end_point = self.get_point(pos.x(), pos.y())
    
    def on_cancel(self):
        self.reset()

