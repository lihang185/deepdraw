"""Shared inference in the active component's centimetre coordinate system."""
from engine.coordinates import to_local, to_world, local_ray, local_plane
import math
from engine import core
from engine.units import snap_integer, parse_length, format_length

EXACT=(core.SnapType.vertex,core.SnapType.edge_center,core.SnapType.intersection,
       core.SnapType.other_point,core.SnapType.ref_point_intersect,core.SnapType.edge,
       core.SnapType.guide_line)

def faces_at(finder):
    entity=finder.snap_to
    if isinstance(entity,core.CFace): return [entity]
    edges=[]
    if isinstance(entity,core.CEdge): edges=[entity]
    elif isinstance(entity,core.CVertex): edges=list(entity.EnumEdges())
    faces={u.GetParentFace().GetID():u.GetParentFace() for e in edges for u in e.EnumEdgeUse()}
    return list(faces.values())

def basis(plane):
    normal=plane.GetNormal().Normalized()
    # Keep familiar X/Y dimensions on horizontal faces, X/Z on walls.
    seed=core.CVector3D(1,0,0) if abs(normal.x)<.9 else core.CVector3D(0,1,0)
    s=(seed-normal*seed.Dot(normal)).Normalized()
    return s,normal.Cross(s).Normalized()

def plane_at(view,finder,point,pos):
    hit = finder.pick_helper.PickedFace()
    if hit is not None:
        plane = local_plane(view, finder.pick_helper.GetFacePlane())
        return core.CPlane(plane.GetNormal(),point)
    return core.CPlane(core.CVector3D(0,0,1),point)


def infer(view,finder,pos,origin=None,plane=None,refs=(),entity_filter=None):
    finder.Reset()
    for ref in refs:
        if ref is not None: finder.AddRefPoint(to_world(view,ref))
    if not finder.Inference(pos.x(),pos.y(),entity_filter,to_world(view,origin)):
        raise ValueError('无法确定取点位置')
    point=to_local(view,finder.Position())
    exact=finder.snap_type in EXACT
    if plane is not None:
        n=plane.GetNormal()
        if exact and abs(plane.ProjPoint(point))<core.EPS: return point
        ray=local_ray(view,pos.x(),pos.y())
        if abs(n.Dot(ray.dir))<1e-9: raise ValueError('视线平行于绘图平面，请调整视角')
        point=ray.PointAt(plane.IntersectWithLine(ray))
        # Quantize plane coordinates, never push a rounded point off a sloped face.
        s,t=basis(plane);base=origin if origin is not None else plane.GetNormal()*(-plane.w/plane.GetNormal().Dot(plane.GetNormal()))
        delta=point-base
        return base+s*snap_integer(delta.Dot(s))+t*snap_integer(delta.Dot(t))
    if exact: return point
    if finder.snap_type==core.SnapType.face:
        # Preserve the exact world hit after converting to the editing frame.
        return point
    if finder.snap_type==core.SnapType.last_point_axis and origin is not None:
        delta=point-origin
        return origin+core.CVector3D(*(snap_integer(v) for v in delta.ToTuple()))
    return core.CVector3D(*(snap_integer(v) for v in point.ToTuple()))

def draw_path(gl,points,closed=False,color=(.15,.25,.8)):
    if len(points)<2:return
    gl.glColor3f(*color)
    gl.glBegin(gl.GL_LINE_LOOP if closed else gl.GL_LINE_STRIP)
    for p in points:gl.glVertex3d(p.x,p.y,p.z)
    gl.glEnd()

def commit_path(tool,points,closed=False,curve=False):
    pairs=list(zip(points,points[1:]))
    if closed:pairs.append((points[-1],points[0]))
    if any((a-b).Length()<=core.EPS for a,b in pairs):raise ValueError('线段长度须大于0.001厘米')
    comp=tool.view.model.GetActiveComponent()
    edges=[comp.AddLine(a,b) for a,b in pairs]
    if curve:
        native_curve=core.CEntityFactory(tool.view.model).NewCurve()
        native_curve.SetParentComponent(comp)
        for edge in edges:edge.SetCurve(native_curve)
        native_curve.UpdateEdgeLink(edges[0])
    comp.CheckModel(edges,None)
    return edges

def length(tool,text):
    return parse_length(text,getattr(tool.view,'display_unit','cm'))

def show_length(tool,value,prefix):
    tool.view.setStatusBar(prefix+format_length(value,getattr(tool.view,'display_unit','cm'))+'；Enter 精确输入，Esc 取消')
