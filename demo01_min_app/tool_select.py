import core

class SelectTool(core.IBaseTool):
    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view
        self.activate()
    
    def activate(self):
        self.pick_helper = core.CPickHelper(self.view.view_proxy)
    
    def draw(self, gl):
        pass
        
    def draw_2d(self, painter):
        pass

    def on_left_button_down(self, pos, mod):
        self.pos_x = pos.x()
        self.pos_y = pos.y()
        
        model = core.active_model()
        
        picker = self.pick_helper
        picker.Reset()

        picker.SinglePick(self.pos_x, self.pos_y, 9, None, True)
        
        best = picker.BestPick()
        
        print("select:")
        if best:
            print(best.e)
            model.SetSelection([best.e])
        else:
            model.ClearSelection()

    
    def on_left_button_up(self, pos):
        pass

    def on_mouse_move(self, pos, modifiers):
        pass


