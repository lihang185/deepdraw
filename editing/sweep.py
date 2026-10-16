"""Native adapter for deterministic architectural profile sweeps."""
import copy
import json
from engine import core
from . import sweep_geometry as geo

PREFIX = 'DeepDraw sweep v1\n'


class Profile(list):
    """Ordered section points with a Curve label for each outgoing edge."""
    def __init__(self, points, curves):
        super().__init__(points)
        self.curves = list(curves)


class Sweeps:
    def __init__(self, session): self.s = session

    def chain(self, target, reverse=False):
        """Snapshot one edge chain in its container's local coordinates."""
        entities = self.s.unwrap(target)
        if len(entities)==1 and isinstance(entities[0],core.CComponentInstance):
            inst=entities[0]
            points,closed=self.chain(self.s.wrap(inst.GetDefinition()))
            matrix=inst.GetTransform()
            points=[matrix.Transform(core.CVector3D(*p)) for p in points]
            points=[(p.x,p.y,p.z) for p in points]
            return (list(reversed(points)) if reverse else points),closed
        if len(entities)==1 and isinstance(entities[0],core.CComponent):
            entities=list(entities[0].EnumEntities())
            entities=[e for e in entities if isinstance(e,core.CEdge)]
        if len(entities)==1 and isinstance(entities[0],core.CFace):
            face=entities[0]
            if face.GetNumLoops()!=1: raise ValueError('Choose a single loop, not a face with holes')
            entities=[eu.GetEdge() for eu in face.GetOuterLoop().EnumEdgeUse()]
        if any(not isinstance(e,core.CEdge) for e in entities): raise TypeError('Expected one edge chain')
        if len({e.GetParentComponent().GetID() for e in entities})>1:
            raise ValueError('Path edges must belong to one container')
        segments=[]
        for e in entities:
            a,b=e.GetStartVertex(),e.GetEndVertex()
            segments.append((a.GetID(),(a.p.x,a.p.y,a.p.z),b.GetID(),(b.p.x,b.p.y,b.p.z)))
        points,closed=geo.ordered_edges(segments)
        return (list(reversed(points)) if reverse else points),closed

    def profile(self, target, origin=(0,0,0), x_axis=(1,0,0), y_axis=(0,1,0)):
        """Project a single closed native contour into explicit profile axes."""
        points,closed=self.chain(target)
        if not closed: raise ValueError('Profile must be closed')
        x,y=geo.unit(x_axis),geo.unit(y_axis);origin=geo.point(origin,3)
        if abs(geo.dot(x,y))>1e-9: raise ValueError('Profile axes must be orthogonal')
        normal=geo.cross(x,y)
        if any(abs(geo.dot(geo.sub(p,origin),normal))>geo.EPS for p in points):
            raise ValueError('Profile contour is outside the specified plane')
        entities = self.s.unwrap(target)
        while len(entities)==1 and isinstance(entities[0],core.CComponentInstance):
            entities=[entities[0].GetDefinition()]
        local, _ = self.chain([self.s.wrap(e) for e in entities])
        if len(entities)==1 and isinstance(entities[0],core.CComponent):
            entities=list(entities[0].EnumEntities())
        elif len(entities)==1 and isinstance(entities[0],core.CFace):
            entities=[eu.GetEdge() for eu in entities[0].GetOuterLoop().EnumEdgeUse()]
        labels={}
        for edge in entities:
            if isinstance(edge,core.CEdge):
                ends=[v.p for v in (edge.GetStartVertex(),edge.GetEndVertex())]
                key=frozenset((p.x,p.y,p.z) for p in ends)
                curve=edge.GetCurve()
                labels[key]=curve.GetID() if curve is not None else None
        curves=[labels[frozenset((p,local[(i+1)%len(local)]))] for i,p in enumerate(local)]
        return Profile([(geo.dot(geo.sub(p,origin),x),geo.dot(geo.sub(p,origin),y)) for p in points],curves)

    def plan(self, profile, path, closed=None, up=(0,0,1), anchor=(0,0), offset=(0,0), reverse=False, miter_limit=10, profile_curves=None):
        self.s.check()
        if not isinstance(path,(list,tuple)):
            path,inferred=self.chain(path)
            if closed is not None and bool(closed)!=inferred: raise ValueError('closed conflicts with native path topology')
            closed=inferred
        if reverse: path=list(reversed(path))
        if not isinstance(profile,(list,tuple)): profile=self.profile(profile)
        curves=profile_curves if profile_curves is not None else getattr(profile,'curves',None)
        result=geo.mesh(profile,path,bool(closed),up,anchor,offset,miter_limit)
        if curves is not None:
            points=[tuple(p) for p in profile]
            if points[0]==points[-1]: points.pop()
            if len(curves)!=len(points): raise ValueError('Expected one Curve label per profile edge')
            if any(c is not None and (isinstance(c,bool) or not isinstance(c,int)) for c in curves):
                raise ValueError('Curve labels must be integers or None')
            links={frozenset((p,points[(i+1)%len(points)])):curves[i] for i,p in enumerate(points)}
            ordered=list(reversed(points)) if geo.area(points)<0 else points
            result['profile_curves']=[links[frozenset((p,ordered[(i+1)%len(ordered)]))] for i,p in enumerate(ordered)]
        result['recipe']=dict(profile=result['profile'],path=result['path'],closed=result['closed'],
                              up=result['up'],miter_limit=miter_limit)
        if 'profile_curves' in result: result['recipe']['profile_curves']=result['profile_curves']
        return result




    def _build(self,name,plan,parent):
        obj=self.s.build.component(name,PREFIX+json.dumps(plan['recipe'],ensure_ascii=False),parent)
        comp=obj.definition
        factory=core.CEntityFactory(self.s.model)
        vertices=[factory.NewVertex(core.CVector3D(*p)) for p in plan['vertices']]
        edges={}; native_faces=[]
        for indices in plan['faces']:
            face=factory.NewFace();loop=factory.NewLoop()
            for a,b in zip(indices,indices[1:]+indices[:1]):
                key=(min(a,b),max(a,b))
                if key not in edges:
                    edge=factory.NewEdge(vertices[key[0]],vertices[key[1]],False)
                    comp.native.AddEntity(edge);edges[key]=edge
                loop.AddEdgeUseToTail(factory.NewEdgeUse(edges[key],a!=key[0]))
            face.AddLoop(loop)
            if not face.UpdatePlane(): raise ValueError('Sweep produced a degenerate face')
            # New loops default to convex; concave caps need native tessellation.
            loop.ComputeIsConvex(face.GetPlane().GetNormal())
            comp.native.AddEntity(face);native_faces.append(face)
        self.s.edit.touch(comp)
        self.s.scene.name('surface', [self.s.wrap(f) for f in native_faces],comp)
        if 'rims' in plan:
            for name,indices in zip(('start_rim','end_rim'),plan['rims']):
                self.s.scene.name(name,[self.s.wrap(native_faces[i]) for i in indices],comp)
            # Smooth circumferential facets, keeping rim/bend creases visible.
            k=plan['recipe']['segments'];count=len(plan['vertices'])//2
            for (a,b),edge in edges.items():
                if a//count==b//count and (a%count)//k!=(b%count)//k:
                    edge.SetSoft(True);edge.SetSmooth(True)
        elif not plan['closed']:
            self.s.scene.name('start_cap',self.s.wrap(native_faces[-2]),comp)
            self.s.scene.name('end_cap',self.s.wrap(native_faces[-1]),comp)
        if 'profile_curves' in plan:
            labels=plan['profile_curves'];k=len(labels)
            rings=len(plan['vertices'])//k
            for (a,b),edge in edges.items():
                if a//k!=b//k and a%k==b%k:
                    i=a%k
                    if labels[i] is not None and labels[i]==labels[i-1]:
                        edge.SetSoft(True);edge.SetSmooth(True)
            # Copy each section Curve independently at every path station.
            for ring in range(rings):
                groups={}
                for i,label in enumerate(labels):
                    if label is None: continue
                    a=ring*k+i;b=ring*k+(i+1)%k
                    edge=edges[(min(a,b),max(a,b))]
                    if label not in groups:
                        curve=factory.NewCurve();curve.SetParentComponent(comp.native)
                        groups[label]=(curve,edge)
                    edge.SetCurve(groups[label][0])
                for curve,first in groups.values(): curve.UpdateEdgeLink(first)
        self.s.edit._report(dict(kind='sweep',instance_id=obj.id,vertex_count=len(vertices),
                                 edge_count=len(edges),face_count=len(native_faces),
                                 volume=plan['volume'],path_length=plan['path_length'],closed=plan['closed']))
        return obj


