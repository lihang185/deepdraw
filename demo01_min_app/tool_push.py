import core
from push_pull_controller import PushPullController

class PushTool(core.IBaseTool):
    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view
        self.ctrl = None

    def activate(self):
        self.push_dir = None
        self.push_orig = None
        self.push_dist = 0.0
        self.input = core.CInputPointFinder(self.view.view_proxy)
        self.is_begin = False
        self.view.setMouseTracking(True)
    
    def deactivate(self):
        self.view.setMouseTracking(False)

    def draw(self, gl):
        if self.is_begin:
            self.input.Draw()
            
            push_target_point = self.push_orig.MoveForward(self.push_dir, self.push_dist)
            
            gl.glColor3f(0.0, 0.0, 1.0)
            core.draw_line(self.push_orig, push_target_point, gl)

    
    def on_left_button_down(self, pos, mod):
        self.last_pos = pos
        
        if self.is_begin == False:
            
            pick = core.CPickHelper(self.view.view_proxy)
            pick.SinglePick(pos.x(), pos.y(), 9, None, True)
            
            push_face = None
            model = self.view.model
            best_face = pick.PickedFace()
            if best_face:
                push_face = best_face.e
            else:
                model.ClearSelection()
                return
                
            self.view.model.UndoManager().StartOperation("Push")

            self.is_begin = True

            self.ctrl = PushPullController()
            self.ctrl.begin(push_face, model)
            
            select_ls = [self.ctrl.push_face]
            model.SetSelection(select_ls)
            
            plane = push_face.GetPlane()
            self.push_dir = core.CVector3D(plane.x, plane.y, plane.z)
            
            pick_ray = pick.GetPickRay()
            
            s = plane.IntersectWithLine(pick_ray)
            self.push_orig = pick_ray.PointAt(s)
            self.push_dist = 0.0

        else:
            self.ctrl.finish()
            self.view.model.UndoManager().CommitOperation()
            self.is_begin = False
            self.view.model.ClearSelection()
        
        self.view.MarkDirty()

    def on_left_button_up(self, pos):
        pass

    def get_point(self, px, py):
        input = self.input
        input.Reset()
        
        self.snap_axis = 8
        
        #=======================
        # Pick
        def filter1(e):
            return e not in self.ctrl.filter_set
        
        filter_proxy = core.EntityFilter(filter1)
        
        ok = input.Inference(px, py, filter_proxy, None)
        assert ok
        
        #print( self.input.snap_type)
        
        if self.input.snap_type == core.SnapType.axis_plane:
            #print("SnapType.axis_plane")
            return False, None
        elif self.input.snap_type == core.SnapType.axis:
            #print("SnapType.axis")
            return False, None
        elif self.input.snap_type == core.SnapType.face:
            # check plane
            face = self.input.snap_to
            if face.GetPlane().IsSameTo2(self.ctrl.begin_plane):
                #print("same to begin_plane")
                return False, None
            
            push_face = self.ctrl.push_face
            if not face.GetPlane().GetNormal().InParallelWith(push_face.GetPlane().GetNormal()):
                #print("not paralle")
                return False, None
        
        return True, input.Position()
 
    def on_mouse_move(self, pos, modifiers):
        if self.is_begin:
            ok, point = self.get_point(pos.x(), pos.y())
            if ok:
                s1 = (point-self.push_orig).Dot(self.push_dir)
            else:
                pick_ray = self.input.pick_helper.GetPickRay()
                push_ray = core.CStraightLine(self.push_orig, self.push_dir)
                ok, s1, s2 = core.CStraightLine.ComputeNearestPoint(push_ray, pick_ray)
                if not ok:
                    print("Compute push_dist Error")
                    return
            
            value = s1
            
            diff = value - self.push_dist
            
            diff_vec = self.push_dir*diff

            self.ctrl.push(diff_vec)
            
            self.push_dist = value

            # update model
            self.view.MarkDirty()
        
        self.last_pos = pos

