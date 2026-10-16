import core

class OffsetTool(core.IBaseTool):
    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view

    def activate(self):
        self.is_begin = False
        
        self.target_face = None
        self.start_point = None
        self.start_point_edge = None
        self.offset_points = None
        
        self.input = core.CInputPointFinder(self.view.view_proxy)
        
        self.view.setMouseTracking(True)

    def deactivate(self):
        self.view.setMouseTracking(False)

    def draw(self, gl):
        if self.is_begin:
            if self.start_point:
                size = self.view.camera_zoom * 0.01
                core.draw_target_with_size(self.start_point, size, gl)
                
                self.draw_offset_loop(gl)
    
    def draw_offset_loop(self, gl):
        if self.offset_points:
            gl.glColor3f(1.0, 0.0, 0.0);
            count = len(self.offset_points)
            for i in range(count):
                p1 = self.offset_points[i-1]
                p2 = self.offset_points[i]
                self.draw_line(p1, p2, gl)
                
    def draw_points(self, gl):
        if self.offset_points:
            size = self.view.camera_zoom * 0.01
            for p in self.offset_points:
                core.draw_target_with_size(p, size, gl)
    
    def create_offset(self):
        if not self.offset_points:
            return
            
        fac = core.CEntityFactory(self.view.model)
            
        self.view.model.UndoManager().StartOperation("Offset")
        
        comp = self.view.model.GetActiveComponent()
        entity_ls = []
        
        vert_ls = []
        for p, edge in self.offset_edges:
            vert = fac.NewVertex(p)
            vert_ls.append(vert)
            entity_ls.append(vert)

        count = len(vert_ls)
        for i in range(count):
            v1 = vert_ls[i-1]
            v2 = vert_ls[i]
            new_edge = fac.NewEdge(v1, v2, False)
            comp.AddEntity(new_edge)
            entity_ls.append(new_edge)

        comp.CheckModel(entity_ls, None)
        
        self.view.model.UndoManager().CommitOperation()
        
        self.view.MarkDirty()
    
    def draw_line(self, p1, p2, gl):
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(*p1.ToTuple())
        gl.glVertex3d(*p2.ToTuple())
        gl.glEnd()

    def init_face_space(self, plane):
        s, t = plane.ComputeST()
        self.dir_s = s
        self.dir_t = t
    
    def static_input_face(self):
        face_set = set()
        
        snap_type = self.input.snap_type
        if snap_type == core.SnapType.face:
            face_set.add(self.input.snap_to)
        elif snap_type == core.SnapType.edge or snap_type == core.SnapType.edge_center:
            edge = self.input.snap_to
            for eu in edge.EnumEdgeUse():
                face_set.add(eu.GetParentFace())
        elif snap_type == core.SnapType.vertex:
            vertex = self.input.snap_to
            for edge in vertex.EnumEdges():
                for eu in edge.EnumEdgeUse():
                    face_set.add(eu.GetParentFace())
        
        return face_set
    
    def compute_offset_start(self, x, y):
        pick_ray = self.view.ComputePickRay(x, y)
        plane = self.target_face.GetPlane()
        
        s = plane.IntersectWithLine(pick_ray)
        self.point = pick_ray.PointAt(s)
        
        min_len = 1e10
        near_point = self.point
        snap_edge = None
        
        outer_loop = self.target_face.GetOuterLoop()
        for eu in outer_loop.EnumEdgeUse():
            edge = eu.GetEdge()
            p1 = edge.GetStartVertex().Pos()
            p2 = edge.GetEndVertex().Pos()
            line1 = core.CStraightLine.FromEdge(p1, p2 )
            orig, dir, llen = core.edge_to_ray(eu.GetEdge())
            ok, s1, s2 = core.CStraightLine.ComputeNearestPoint(line1, pick_ray)
            if ok:
                if s1 < 0: s1 = 0
                if s1 > llen: s1 = llen
                point = orig.MoveForward(dir, s1)
                length = (point - self.point).Length()
                if length < min_len:
                    min_len = length
                    near_point = point
                    snap_edge = eu
        
        self.offset_length = min_len
        self.start_point = near_point
        self.start_point_edge = snap_edge
        
    def compute_offset_value(self, x, y):
        camray_orig, camray_dir, camray_end = self.view.ComputeCameraRay(x, y)
        plane = self.target_face.GetPlane()
        s = plane.IntersectWithRay(camray_orig, camray_dir)
        self.point = camray_orig.MoveForward(camray_dir, s)
        
        line_orig, line_dir = self.compute_line_by_edgeuse(self.start_point_edge)
        
        inner_dir = plane.GetNormal().Cross(line_dir)
        clip_plane = core.CPlane(inner_dir, line_orig)
        dist = clip_plane.ProjPoint(self.point)
        self.offset_length = dist
    
    def compute_line_by_edgeuse(self, edgeuse):
        p1 = edgeuse.GetStartVertex().Pos()
        p2 = edgeuse.GetEndVertex().Pos()
        dir = (p2 - p1).Normalized()
        return p1, dir
    
    def compute_offset_line(self, edgeuse, offset, plane):
        p1 = edgeuse.GetStartVertex().Pos()
        p2 = edgeuse.GetEndVertex().Pos()

        diff = p2 - p1
        dir = diff.Normalized()
        offset_dir = plane.GetNormal().Cross(dir)
        orig = p1.MoveForward(offset_dir, offset)
        return core.CStraightLine(orig, dir)
        
    def compute_offset(self, offset_length):
        plane = self.target_face.GetPlane()
        
        points = []
        offset_edges = []
        
        outer_loop = self.target_face.GetOuterLoop()
        for eu in outer_loop.EnumEdgeUse():
            this_line = self.compute_offset_line(eu, offset_length, plane)
            next_line = self.compute_offset_line(eu.Next(), offset_length, plane)
            
            ok, s1, s2 = core.CStraightLine.ComputeNearestPoint(this_line, next_line)
            if ok:
                #assert math.fabs(s1-s2) < EPS
                point = this_line.PointAt(s1)
            else:
                point = this_line.orig
            
            points.append(point)
            item = point, eu.GetEdge()
            offset_edges.append(item)
        
        self.offset_points = points
        self.offset_edges = offset_edges
    
    def get_point(self, px, py):
        input = self.input
        input.Reset()
        ok = input.Inference(px, py, None, None)
        assert ok
        return input.Position()

    def on_left_button_down(self, pos, mod):
        if self.is_begin == False:
            pick = self.input.pick_helper
            pick.Reset()
            pick.SinglePick(pos.x(), pos.y(), 9, None, True)
            
            self.target_face = None
            model = self.view.model
            best_face = pick.PickedFace()
            if best_face:
                self.target_face = best_face.e
                selected = [self.target_face]
                model.SetSelection(selected)
            else:
                model.ClearSelection()
                return
            
            self.compute_offset_start(pos.x(), pos.y())
            self.is_begin = True
            
        else:
            # 执行
            self.create_offset()
            
            #print("ok")
            self.is_begin = False
            self.target_face = None
            self.start_point = None
            self.start_point_edge = None
            self.offset_points = None

    def on_left_button_up(self, pos):
        pass

    def on_mouse_move(self, pos, modifiers):
        if self.is_begin:
            self.compute_offset_value(pos.x(), pos.y())
            self.compute_offset(self.offset_length)
