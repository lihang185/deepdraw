"""Vertex snapping on picked nested geometry, in the active editing coordinates."""
from engine import core
from engine.qt import QtGui

def vertex_at(view,picker,pos,excluded,entity_filter=None):
    picker.Reset();picker.SinglePick(pos.x(),pos.y(),10,entity_filter, False)
    projection=view.ComputeProjectMatrix()*view.ComputeCameraMatrix()[0]
    eye=view.camera.position
    best=None;seen=set()
    def visit(entity,matrix,depth=0):
        nonlocal best
        if depth>64 or entity.IsMarkedDeleted() or entity.IsHide() or entity.GetID() in excluded:return
        if isinstance(entity,core.CComponentInstance):
            tm=matrix.Multiply(entity.GetTransform().Multiply(entity.GetAnimationTransform()))
            for child in entity.GetDefinition().EnumEntities():visit(child,tm,depth+1)
            return
        if isinstance(entity,core.CEdge):vertices=[entity.GetStartVertex(),entity.GetEndVertex()]
        elif isinstance(entity,core.CFace):vertices=entity.EnumVertices()
        elif isinstance(entity,core.CVertex):vertices=[entity]
        else:return
        for vertex in vertices:
            point=matrix.Transform(vertex.Pos());key=point.ToTuple()
            if key in seen:continue
            seen.add(key)
            q=projection.map(QtGui.QVector3D(*key))
            if not -1<=q.z()<=1:continue
            x=(q.x()+1)*view.width()/2-.5;y=(1-q.y())*view.height()/2-.5
            distance=(x-pos.x())**2+(y-pos.y())**2
            if distance>100:continue
            depth=(QtGui.QVector3D(*key)-eye).lengthSquared()
            score=(distance,depth)
            if best is None or score<best[0]:best=(score,point)
    for hit in picker.GetPicked():
        path=list(hit.inst_path)
        if any(e.GetID() in excluded or e.IsHide() for e in path):continue
        matrix=core.CMatrix()
        for inst in path:
            if inst!=hit.e:matrix=matrix.Multiply(inst.GetTransform().Multiply(inst.GetAnimationTransform()))
        visit(hit.e,matrix)
    from engine.coordinates import to_local
    return None if best is None else to_local(view,best[1])
