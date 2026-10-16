"""Topology-aware component construction, adapted from editor_dist/comp_maker.py.

The caller owns the edit transaction. Only shared boundary topology is copied.
"""
from engine import core


class ComponentMaker:
    def __init__(self, entity_ls, model):
        self.model = model
        self.factory = core.CEntityFactory(model)
        self.entity_set = set(entity_ls)
        if not self.entity_set or any(not isinstance(e, (core.CEdge, core.CFace, core.CComponentInstance, core.CGuideLine)) for e in self.entity_set):
            raise ValueError('请选择可成组的边、面、组件或辅助线')
        self.mapping = {}
        self.curves = {}

    def create_comp_def(self, name):
        comp = self.factory.NewComponentDefinition()
        comp.name = name
        self.model.addDefinition(comp)
        return comp

    def separate_from(self):
        faces = {e for e in self.entity_set if isinstance(e, core.CFace)}
        edges = {e for e in self.entity_set if isinstance(e, core.CEdge)}
        for face in faces:
            edges.update(face.EnumEdges())
        split = {edge for edge in edges if any(use.GetParentFace() not in faces for use in edge.EnumEdgeUse())}
        moving = edges - split
        vertices = {v for edge in edges for v in (edge.GetStartVertex(), edge.GetEndVertex())}
        # Include outside loose edges as well as outside faces.
        self.copy_vert_map = {v: self.factory.NewVertex(v.Pos()) for v in vertices
                              if any(edge not in moving for edge in v.EnumEdges())}
        for edge in edges:
            curve = edge.GetCurve()
            if curve is not None:
                self.curves.setdefault(curve, list(curve.GetEdges()))
        replacements = set()
        for edge in split:
            new = self.factory.NewEdge(self.copy_vert_map[edge.GetStartVertex()],
                                       self.copy_vert_map[edge.GetEndVertex()], False)
            new.SetHide(edge.IsHide()); new.SetSoft(edge.IsSoft()); new.SetSmooth(edge.IsSmooth())
            for use in list(edge.EnumEdgeUse()):
                if use.GetParentFace() in faces:
                    use.Record(True)
                    use.DelinkEdge(); use.LinkEdge(new)
            self.mapping[edge.GetID()] = new
            replacements.add(new)
        for edge in moving:
            start, end = edge.GetStartVertex(), edge.GetEndVertex()
            if start in self.copy_vert_map:
                edge.Record(True)
                edge.DisconnectVertex(start)
                edge.ConnectStartToVertex(self.copy_vert_map[start], False)
            if end in self.copy_vert_map:
                edge.Record(True)
                edge.DisconnectVertex(end)
                edge.ConnectEndToVertex(self.copy_vert_map[end], False)
        moved = moving | faces | {e for e in self.entity_set if isinstance(e, (core.CComponentInstance, core.CGuideLine))}
        for entity in moved:
            self.mapping[entity.GetID()] = entity
            entity.GetParentComponent().RemoveEntity(entity)
        self.entity_set = moved | replacements

    def add_to_component(self, comp_def):
        for entity in self.entity_set:
            comp_def.AddEntity(entity)
        for curve, original_edges in self.curves.items():
            transferred = [self.mapping[e.GetID()] for e in original_edges if e.GetID() in self.mapping]
            if not transferred:
                continue
            if len(transferred) == len(original_edges) and all(a == b for a, b in zip(transferred, original_edges)):
                curve.Record(True)
                curve.SetParentComponent(comp_def)
                curve.UpdateEdgeLink(transferred[0])
            else:
                new_curve = self.factory.NewCurve()
                new_curve.SetParentComponent(comp_def)
                for edge in transferred:
                    edge.SetCurve(new_curve)
                new_curve.UpdateEdgeLink(transferred[0])
                remaining = [e for e in original_edges if e.GetParentComponent() != comp_def and not e.IsMarkedDeleted()]
                if remaining:
                    curve.UpdateEdgeLink(remaining[0])

    def set_center_point(self, comp_def):
        vertices = {v for e in self.entity_set if isinstance(e, core.CEdge)
                    for v in (e.GetStartVertex(), e.GetEndVertex())}
        instances = [e for e in self.entity_set if isinstance(e, core.CComponentInstance)]
        guides = [e for e in self.entity_set if isinstance(e, core.CGuideLine)]
        points = [v.Pos() for v in vertices] + [e.orig for e in guides]
        refreshed = set()
        def bounds(comp):
            # Shared definitions need one bottom-up refresh, not one per
            # occurrence. Only children can contribute descendant bounds.
            if comp.GetID() not in refreshed:
                refreshed.add(comp.GetID())
                for entity in comp.EnumChildren():
                    if not entity.IsMarkedDeleted():
                        bounds(entity.GetDefinition())
                comp.ComputeBoundingBox()
            return comp.GetBoundingBox()
        for instance in instances:
            box = bounds(instance.GetDefinition())
            points.extend(instance.GetTransform().Transform(core.CVector3D(x,y,z))
                          for x in (box.min_x, box.max_x) for y in (box.min_y, box.max_y)
                          for z in (box.min_z, box.max_z))
        center = core.CVector3D((min(p.x for p in points)+max(p.x for p in points))/2,
                               (min(p.y for p in points)+max(p.y for p in points))/2, 0) if points else core.CVector3D()
        self.center_point = center
        faces = [e for e in self.entity_set if isinstance(e, core.CFace)]
        uv_samples = {}
        for face in faces:
            coords = face.GetTextureCoords()
            if coords is not None:
                projection = core.UVHelper(face, face.GetMaterial()).ComputeProjectionToFaceSpace(face)
                samples = []
                for vertex in face.EnumVertices():
                    point = vertex.Pos(); local = projection.Transform(point)
                    uv = coords.GetFrontTextureCoords().Reversed().Transform(core.CVector3D(local.x, local.y, 1))
                    samples.append((point-center, uv))
                uv_samples[face] = samples
        for vertex in vertices:
            vertex.SetPosition(vertex.Pos()-center)
        for instance in instances:
            matrix = instance.GetTransform()
            matrix.SetRow(3, matrix.GetRow(3)-center)
            instance.SetTransform(matrix)
        for guide in guides:
            guide.orig = guide.orig-center
        for face in faces:
            face.UpdatePlane(); face.MarkDirty()
            if face in uv_samples:
                import numpy as np
                projection = core.UVHelper(face, face.GetMaterial()).ComputeProjectionToFaceSpace(face)
                source, values = [], []
                for point, uv in uv_samples[face]:
                    local = projection.Transform(point)
                    source.append([local.x, local.y, 1]); values.append(uv.ToTuple())
                fitted, _, rank, _ = np.linalg.lstsq(np.asarray(source), np.asarray(values), rcond=None)
                if rank < 3:
                    raise ValueError('Cannot preserve UVs on a degenerate face')
                matrix = core.CMatrix33.Load(np.linalg.inv(fitted).ravel().tolist())
                face.SetTextureCoords(core.CFaceTextureCoords.Load(matrix).AddToUndoManager())

    def make_instance(self, comp_def):
        instance = self.factory.NewComponentInstance()
        instance.SetDefinition(comp_def)
        instance.is_group = True
        matrix = core.CMatrix(); matrix.SetRow(3, self.center_point)
        instance.SetTransform(matrix)
        return instance
