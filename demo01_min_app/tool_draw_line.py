import core

class DrawLineTool(core.IBaseTool):
    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view
        self.activate()
        
    def reset(self):
        self.is_first_point = True
        self.first_point = None
        self.prev_point = None
        self.cur_point = None
    
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
        
        if self.is_first_point == False:
            gl.glColor3f(0.0, 0.0, 0.0)
            
            p1 = self.prev_point
            p2 = self.cur_point
            
            gl.glBegin(gl.GL_LINES)
            gl.glVertex3d(p1.x, p1.y, p1.z )
            gl.glVertex3d(p2.x, p2.y, p2.z )
            gl.glEnd()
    
    def add_new_line(self):        
        model = core.active_model()
        comp = model.GetActiveComponent()
        
        new_edge = comp.AddLine(self.prev_point, self.cur_point)

        edge_ls = [new_edge]
        
        merge_controller = core.CMergeController(comp, edge_ls, None)
        merge_controller.Compute()
        
        rs = merge_controller.GetEvents()
        print(rs)
        
        #comp.CheckModel(edge_ls, None)
        
        self.view.MarkDirty()
        self.view.repaint()

    def on_left_button_down(self, pos, mod):
        px = pos.x()
        py = pos.y()
        
        self.input.Reset()
        ok = self.input.Inference(px, py, None, None )
        assert ok
        
        new_point = self.input.Position()
        if self.is_first_point:
            self.first_point = new_point
            self.is_first_point = False
        else:
            # create line
            self.add_new_line()
        
        self.prev_point = self.cur_point = new_point
    
    def on_left_button_up(self, pos):
        pass

    def on_mouse_move(self, pos, modifiers):
        px = pos.x()
        py = pos.y()
        
        self.input.Reset()
        
        ok = self.input.Inference(px, py, None, None )
        assert ok
        
        self.cur_point = self.input.Position()
    
    def on_cancel(self):
        self.reset()


class TestInputTool(core.IBaseTool):
    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view
        self.activate()
    
    def activate(self):
        self.input = core.CInputPointFinder(self.view.view_proxy)
        #启动鼠标追踪
        self.view.setMouseTracking(True)
    
    def deactivate(self):
        #关闭鼠标追踪
        self.view.setMouseTracking(False)
    
    def draw(self, gl):
        self.input.Draw()
   
    def on_left_button_down(self, pos, mod):
        pass
    
    def on_left_button_up(self, pos):
        pass

    def on_mouse_move(self, pos, modifiers):
        px = pos.x()
        py = pos.y()
        
        self.input.Reset()
        
        ok = self.input.Inference(px, py, None, None )
        assert ok
        
        self.cur_point = self.input.Position()


