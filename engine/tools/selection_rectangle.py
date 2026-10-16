"""World-space rectangle selection within the active editing occurrence."""
import numpy as np
from engine import core
from engine.coordinates import active_matrix, affine
from engine.viewer.render_pipeline import visible_entity


def select_rectangle(view, x0, y0, x1, y1, inside):
    projection = view.ComputeProjectMatrix()*view.ComputeCameraMatrix()[0]
    matrix = np.array([[getattr(projection.row(i),k)() for k in ('x','y','z','w')]
                       for i in range(4)])
    left,right = (2*(x+.5)/view.width()-1 for x in (x0,x1))
    bottom,top = (1-2*(y+.5)/view.height() for y in (y1,y0))
    planes = np.array(((1,0,0,-left),(-1,0,0,right),
                       (0,1,0,-bottom),(0,-1,0,top),(0,0,1,1),(0,0,-1,1)))

    def primitives(entity, transform):
        if not visible_entity(entity):return
        if isinstance(entity,core.CComponentInstance):
            transform=transform.Multiply(entity.GetTransform().Multiply(entity.GetAnimationTransform()))
            for child in entity.GetDefinition().EnumEntities():
                yield from primitives(child,transform)
            return
        def clip_points(points):
            points=np.array([(*p.ToTuple(),1.) for p in points])
            return points.dot((matrix @ affine(transform)).T)
        if isinstance(entity,core.CEdge):
            yield clip_points([entity.GetStartVertex().p,entity.GetEndVertex().p])
        elif isinstance(entity,core.CFace):
            mesh=core.TriangleMesh();entity.ComputeMesh(mesh)
            for i in range(0,mesh.GetNumVertexIndices(),3):
                yield clip_points([mesh.GetVertex(mesh.GetVertexIndex(i+j)) for j in range(3)])
        elif isinstance(entity,core.CGuideLine):
            yield clip_points([entity.orig-entity.dir*2000,entity.orig+entity.dir*2000])
        elif isinstance(entity,core.CSectionPlane) and getattr(view,'show_section_planes',True):
            from .tool_section import section_corners
            points=section_corners(entity.plane,entity.bounds)
            for a,b in zip(points,points[1:]+points[:1]):yield clip_points([a,b])

    def intersects(points):
        # Homogeneous clipping handles near-plane crossings without dividing by w.
        for plane in planes:
            clipped=[]
            for a,b in zip(points,list(points[1:])+[points[0]]):
                da,db=plane.dot(a),plane.dot(b)
                if da>=0:clipped.append(a)
                if (da<0)!=(db<0):clipped.append(a+(b-a)*(da/(da-db)))
            if not clipped:return False
            points=clipped
        return True

    selected=[]
    frame=active_matrix(view)
    for entity in view.model.GetActiveComponent().EnumEntities():
        found=False;accepted=inside
        for points in primitives(entity,frame):
            found=True
            if inside:
                if not np.all(points @ planes.T >= -1e-9):accepted=False;break
            elif intersects(points):accepted=True;break
        if found and accepted:selected.append(entity)
    return selected
