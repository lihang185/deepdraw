
import core

class PushPullController:
    def __init__(self):
        pass
    
    def begin(self, face, model):
        self.factory = core.CEntityFactory(model)
        self.model = model
        self.comp = model.GetActiveComponent()
        
        self.filter_set = set()
        
        self.begin_plane = face.GetPlane()
       
        need_create_strip, delete_old_face = self.check_if_need_create_strip(face)
        
        self.combine_face_ls = []
        
        if need_create_strip:
            # create face strip
            self.orig_face = face
            new_face, side_face_ls = self.create_face(face)
            self.push_face = new_face
            self.orig_face.Flip()
        else:
            # move only
            self.orig_face = None
            self.push_face = face
        
        # enum all vertex
        vertex_sets = set()
        for vert in self.push_face.EnumVertices():
            vertex_sets.add(vert)
            #part = edgeuse.Partners()
            #if part:
            #    uf = part.GetParentLoop().GetParentFace()
            #    need_update.add(uf)
        self.vertex_list = list(vertex_sets)
        
        if delete_old_face:
            comp = face.GetParentComponent()
            assert comp
            face.Erase(comp)
            #self.comp.RemoveEntity(face)
            self.orig_face = None
        
        # 合并共面的
        for item in self.combine_face_ls:
            face1, edge, _ = item
            # get another face
            assert edge.GetPartnerCount()==1
            face2 = None
            for eu in edge.EnumEdgeUse():
                parface = eu.GetParentFace()
                if parface != face1:
                    face2 = parface
                    break
            assert face2
            
            face1.CombineOtherFace(face2, edge)
            face2.Erase(comp)
            edge.Erase(comp)
            face1.UpdatePlane()
        
        self.combine_face_ls.clear()
        
        connected = self.static_connected_face(self.push_face)
        connected.append(self.push_face)
        self.need_update = connected

        self.static_filter_face_and_edge()

    
    def static_filter_face_and_edge(self):
        self.filter_set.add(self.push_face)
        if self.orig_face:
            self.filter_set.add(self.orig_face)
        for x in self.need_update:
            self.filter_set.add(x)
        for edge in self.push_face.EnumEdges():
            self.filter_set.add(edge)
    
    def update_face_plane(self, face):
        plane = face.GetPlane()
        for v in face.EnumVertices():
            point1 = v.p
            break
        
        face_normal = plane.GetNormal()
        new_plane = core.CPlane(face_normal, point1)
        face.SetPlane(new_plane)
    
    def push(self, diff):
        for v in self.vertex_list:
            p = v.p + diff
            v.p = p
            
        # check need flip
        if self.orig_face:
            plane = self.orig_face.GetPlane()
            p = self.get_face_first_point(self.push_face)
            if plane.ProjPoint(p) > 0.0:
                print("flip")
                self.flip_all_face()
        
        #self.update_face_plane(self.push_face)
        #self.orig_face.UpdatePlane()
        self.push_face.UpdatePlane()
        
        for f in self.need_update:
            num_loops = f.GetNumLoops()
            assert num_loops>=1 
            ok = f.UpdatePlane()
            assert ok
            f.MarkDirty()
            #f.ComputeMesh()
    
    def finish(self):
        comp = self.comp
        entity_ls = [self.push_face]
        
        comp.CheckModel(entity_ls, self.push_face)
        
        #if merge_ctrl.opening_count and self.push_face:
        #    self.model.deleteEntity(self.push_face)
    
    def get_face_first_point(self, face):
        loop = face.GetOuterLoop()
        pEu = loop.GetEdgeUseHead()
        return pEu.GetStartVertex().Pos()
    
    def flip_all_face(self):
        self.orig_face.Flip()
        self.push_face.Flip()
        
        for f in self.need_update:
            if f is not self.push_face:
                f.Flip()

    def check_if_need_create_strip(self, face):
        total = 0
        connect = 0
        multi = 0
        need_create_strip = False
        delete_old_face = False
        
        face_plane = face.GetPlane()
        
        for edgeuse in face.EnumEdgeUse():
            count = edgeuse.GetEdge().GetPartnerCount()
            if count == 1:
                connect += 1
                other_face = edgeuse.GetPartnerFace()
                plane2 = other_face.GetPlane()
                if not plane2.GetNormal().IsPerpendicular(face_plane.GetNormal()):
                    need_create_strip = True
            elif count > 1:
                multi += 1
            total += 1
        
        if connect < total*0.5:
            need_create_strip = True
        else:
            delete_old_face = True
        
        if not need_create_strip:
            delete_old_face = False
        
        return need_create_strip, delete_old_face

    def static_connected_face(self, face):
        connected_face = []
        for edgeuse in face.EnumEdgeUse():
            other_face = edgeuse.GetPartnerFace()
            if other_face:
                connected_face.append(other_face)
       
        return connected_face
    
    
    def create_face(self, face):
        comp = self.comp
        
        new_face_list = []
        
        vertex_dict = {}
        edge_dict = {}
        curve_dict = {}
        
        new_face = self.factory.NewFace()
        plane = face.GetPlane()
        new_face.SetPlane(plane)
        for loop in face.EnumLoops():
            new_loop = self.factory.NewLoop()
            new_loop.SetIsOuterLoop(loop.IsOuterLoop())
            new_loop.SetIsConvex(loop.IsConvex())
            
            for edgeuse in loop.EnumEdgeUse():
                edge = edgeuse.GetEdge()
                
                v1 = edge.GetStartVertex()
                if v1 not in vertex_dict:
                    new_v1 = self.factory.NewVertex(v1.p)
                    vertex_dict[v1] = new_v1
                else:
                    new_v1 = vertex_dict[v1]

                v2 = edge.GetEndVertex()
                if v2 not in vertex_dict:
                    new_v2 = self.factory.NewVertex(v2.p)
                    vertex_dict[v2] = new_v2
                else:
                    new_v2 = vertex_dict[v2]
                
                if edge not in edge_dict:
                    new_edge = self.factory.NewEdge(new_v1, new_v2, False)
                    edge_dict[edge] = new_edge
                else:
                    new_edge = edge_dict[edge]
                
                # create new edgeuse and add to loop
                new_edgeuse = self.factory.NewEdgeUse(new_edge, edgeuse.IsEdgeReversed())
                #
                new_loop.AddEdgeUseToTail(new_edgeuse)
            
            new_face.AddLoop(new_loop)
            
            #====================
            # Create Side Faces
            #
            #====================
            ls = self.create_strip(new_face, loop, new_loop)
            new_face_list.extend(ls)

        for edge, new_edge in edge_dict.items():
            comp.AddEntity(new_edge)
        for curve, new_curve in curve_dict.items():
            edge1 = new_curve.last_edge
            new_curve.UpdateEdgeLink(edge1)
            
        new_face.MarkDirty()
        #new_face.ComputeMesh()
        comp.AddEntity(new_face)
        
        # update model
        #self.model_render.mark_dirty()
        
        #new_face_list.insert(0, new_face)
        
        #print("ok")
        return new_face, new_face_list

    def compute_plane_by_face(self, face_plane, v1, v2):
        dv2 = face_plane.GetNormal()
        cv1 = v1.p
        cv2 = v2.p
        
        dv1 = cv2 - cv1
        face_normal = dv2.Cross(dv1).Normalized()
        
        dist = -cv1.Dot(face_normal)
        
        return core.CPlane(face_normal.x, face_normal.y, face_normal.z, dist)
    
    def create_strip(self, push_face, loop, new_loop):
        comp = self.comp
        
        edgeuse_list = list(loop.EnumEdgeUse())
        new_edgeuse_list = list(new_loop.EnumEdgeUse())
        num_edges = len(edgeuse_list)
        
        face_list = []
        
        edge_set = set()
        
        last_created = None
        first_edge = None
        for i in range(num_edges):
            # 创建2个线，分别连接new_loop to old_loop
            v1 = new_edgeuse_list[i].GetStartVertex()
            v2 = edgeuse_list[i].GetStartVertex()
            if last_created:
                new_edge1 = last_created
            else:
                new_edge1 = self.factory.NewEdge(v1, v2, False)
                if v1.IsCurveVertex() and v2.IsCurveVertex():
                    new_edge1.SetSoft(True)
                    new_edge1.SetSmooth(True)
                first_edge = new_edge1
            
            v3 = new_edgeuse_list[i].GetEndVertex()
            v4 = edgeuse_list[i].GetEndVertex()
            if i == num_edges-1:
                new_edge2 = first_edge
            else:
                new_edge2 = self.factory.NewEdge(v3, v4, False)
                if v3.IsCurveVertex() and v4.IsCurveVertex():
                    new_edge2.SetSoft(True)
                    new_edge2.SetSmooth(True)
            
            if new_edge1 not in edge_set:
                edge_set.add(new_edge1)
                comp.AddEntity(new_edge1)
            if new_edge2 not in edge_set:
                edge_set.add(new_edge2)
                comp.AddEntity(new_edge2)
                
            #===================
            # 判断新面是否能合并
            #===================
            pEu = edgeuse_list[i]
            count = pEu.PartnersCount()
            #assert(count==2)
            pEu2 = pEu.Partner()
            
            orig_face = pEu2.GetParentFace()
            orig_face_normal = orig_face.GetPlane().GetNormal()
            push_face_normal = push_face.GetPlane().GetNormal()
            if orig_face_normal.IsPerpendicular(push_face_normal) and count <= 2:
                new_face_can_combine = True
            else:
                new_face_can_combine = False

            
            new_face = self.factory.NewFace()
            new_plane = self.compute_plane_by_face(push_face.GetPlane(), v2, v4)
            new_face.SetPlane(new_plane)
            
            new_loop = self.factory.NewLoop()
            
            rev1 = new_edgeuse_list[i].IsEdgeReversed()
            eu1 = self.factory.NewEdgeUse(new_edgeuse_list[i].GetEdge(), not rev1 )
            new_loop.AddEdgeUseToTail(eu1)
            
            eu2 = self.factory.NewEdgeUse(new_edge1, False )
            new_loop.AddEdgeUseToTail(eu2)
  
            rev3 = new_edgeuse_list[i].IsEdgeReversed()
            eu3 = self.factory.NewEdgeUse(edgeuse_list[i].GetEdge(), rev3 )
            new_loop.AddEdgeUseToTail(eu3)
            
            eu4 = self.factory.NewEdgeUse(new_edge2, True )
            new_loop.AddEdgeUseToTail(eu4)
            
            new_face.AddLoop(new_loop)
            new_face.MarkDirty()
            #new_face.ComputeMesh()
            comp.AddEntity(new_face)
            face_list.append(new_face)
            
            # 下一步要用到这个edge
            last_created = new_edge2
            
            if new_face_can_combine:
                edge = pEu2.GetEdge()
                item = new_face, edge, orig_face
                self.combine_face_ls.append(item)

        return face_list

