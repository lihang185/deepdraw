"""Orthogonal drafting and exact coordinate-cell boundary extraction (no rasterization).

All distances use model units. Drawing uncertainty is resolved by moving constraints;
the geometric tolerance is only used to reject ambiguous/sub-tolerance geometry.
"""
import copy
import math

SIDES = ('left', 'right', 'bottom', 'top')
TOL = .001


def finite(value):
    value = float(value)
    if not math.isfinite(value):raise ValueError('Expected a finite number')
    return value


def rectangle(lines):
    # Ray/plane intersections at the same screen row can differ at ~1e-13.
    # Remove arithmetic noise, far below the native 0.001 geometry tolerance.
    r = [round(finite(lines[k]['value']),9) for k in SIDES]
    if r[1]-r[0] <= TOL or r[3]-r[2] <= TOL:
        raise ValueError('Rectangle boundaries are reversed or too close')
    return r


def area(ring):
    return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))/2


def simplify(ring):
    return [p for i,p in enumerate(ring)
            if not (ring[i-1][0]==p[0]==ring[(i+1)%len(ring)][0]
                    or ring[i-1][1]==p[1]==ring[(i+1)%len(ring)][1])]


def inside(point,ring):
    x,y=point; result=False
    for a,b in zip(ring,ring[1:]+ring[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:result=not result
    return result


def overlap(a,b):
    return min(a[1],b[1])>max(a[0],b[0])+TOL and min(a[3],b[3])>max(a[2],b[2])+TOL


def boundaries(outer, voids, max_cells=40000):
    """Boolean outer minus union(voids), returned as CCW outers and CW holes."""
    xs=sorted({v for r in [outer]+voids for v in r[:2]})
    ys=sorted({v for r in [outer]+voids for v in r[2:]})
    if (len(xs)-1)*(len(ys)-1)>max_cells:raise ValueError('Plan exceeds coordinate-cell limit')
    if any(0<b-a<=TOL for axis in (xs,ys) for a,b in zip(axis,axis[1:])):
        raise ValueError('Nearly coincident boundaries: align the constraints explicitly')
    def contains(r,x,y):return r[0]<x<r[1] and r[2]<y<r[3]
    return _cell_boundaries(xs,ys,lambda x,y:contains(outer,x,y) and not any(contains(r,x,y) for r in voids),max_cells)


def _cell_boundaries(xs,ys,occupied,max_cells):
    if (len(xs)-1)*(len(ys)-1)>max_cells:raise ValueError('Plan exceeds coordinate-cell limit')
    edges=set();wall_area=0
    for i in range(len(xs)-1):
        for j in range(len(ys)-1):
            x,y=(xs[i]+xs[i+1])/2,(ys[j]+ys[j+1])/2
            if not occupied(x,y):continue
            wall_area+=(xs[i+1]-xs[i])*(ys[j+1]-ys[j])
            ring=[(xs[i],ys[j]),(xs[i+1],ys[j]),(xs[i+1],ys[j+1]),(xs[i],ys[j+1])]
            for a,b in zip(ring,ring[1:]+ring[:1]):
                if (b,a) in edges:edges.remove((b,a))
                else:edges.add((a,b))
    outgoing={};incoming={}
    for a,b in edges:
        if a in outgoing or b in incoming:
            raise ValueError('Contours touch at a point; adjust room/opening constraints')
        outgoing[a]=b;incoming[b]=a
    if set(outgoing)!=set(incoming):raise ValueError('Open boundary graph')
    rings=[]
    while outgoing:
        start=min(outgoing);p=start;ring=[]
        while True:
            ring.append(p);p=outgoing.pop(p)
            if p==start:break
        ring=simplify(ring)
        if len(ring)<4 or abs(area(ring))<=TOL*TOL:raise ValueError('Degenerate contour')
        rings.append(ring)
    regions=[dict(outer=r,holes=[]) for r in rings if area(r)>0]
    for hole in (r for r in rings if area(r)<0):
        candidates=[r for r in regions if inside(hole[0],r['outer'])]
        if not candidates:raise ValueError('Hole has no containing wall region')
        min(candidates,key=lambda r:area(r['outer']))['holes'].append(hole)
    if not regions:raise ValueError('Plan contains no wall area')
    polygon_area=sum(area(r['outer'])+sum(area(h) for h in r['holes']) for r in regions)
    if not math.isclose(wall_area,polygon_area,rel_tol=1e-9,abs_tol=TOL*TOL):
        raise ValueError('Boundary area disagrees with cell area')
    return regions,wall_area


def validate_ring(points):
    ring=[tuple(round(finite(v),9) for v in p) for p in points]
    if not 4<=len(ring)<=1000 or any(len(p)!=2 for p in ring):raise ValueError('Expected 4..1000 planar vertices')
    segments=list(zip(ring,ring[1:]+ring[:1]))
    for a,b in segments:
        if (a[0]==b[0])==(a[1]==b[1]) or max(abs(a[0]-b[0]),abs(a[1]-b[1]))<=TOL:
            raise ValueError('Contour edges must be nonzero and axis-aligned')
    for i,(a,b) in enumerate(segments):
        for j,(c,d) in enumerate(segments[i+1:],i+1):
            adjacent=(j==i+1 or (i==0 and j==len(segments)-1))
            if adjacent:
                if (a[0]==b[0])==(c[0]==d[0]):raise ValueError('Adjacent contour lines must turn at a corner')
                continue
            # Axis-aligned segment boxes intersect iff the segments intersect.
            if all(max(min(a[k],b[k]),min(c[k],d[k]))<=min(max(a[k],b[k]),max(c[k],d[k]))+TOL for k in (0,1)):
                raise ValueError('Contour self-intersects or touches itself')
    if abs(area(ring))<=TOL*TOL:raise ValueError('Contour has zero area')
    return ring


def polygon_boundaries(shells,voids,max_cells=40000):
    """Exact orthogonal polygon union/difference, including concave exterior footprints."""
    shells=[validate_ring(r) for r in shells];voids=[validate_ring(r) for r in voids]
    if not shells:raise ValueError('At least one shell contour is required')
    all_rings=shells+voids
    xs=sorted({p[0] for r in all_rings for p in r});ys=sorted({p[1] for r in all_rings for p in r})
    if any(0<b-a<=TOL for axis in (xs,ys) for a,b in zip(axis,axis[1:])):
        raise ValueError('Nearly coincident boundaries: align the constraints explicitly')
    return _cell_boundaries(xs,ys,lambda x,y:any(inside((x,y),r) for r in shells)
                           and not any(inside((x,y),r) for r in voids),max_cells)


def solve(data):
    outer=rectangle(data['outer'])
    rooms={name:rectangle(lines) for name,lines in data['rooms'].items()}
    if not rooms:raise ValueError('Define at least one room')
    for name,r in rooms.items():
        if not (r[0]>outer[0]+TOL and r[1]<outer[1]-TOL and r[2]>outer[2]+TOL and r[3]<outer[3]-TOL):
            raise ValueError('Room must be strictly inside exterior boundary: '+name)
    items=list(rooms.items())
    for i,(name,r) in enumerate(items):
        for other,b in items[i+1:]:
            if overlap(r,b):raise ValueError('Room interiors overlap: '+name+', '+other)
            if min(r[1],b[1])>=max(r[0],b[0]) and min(r[3],b[3])>=max(r[2],b[2]):
                raise ValueError('Rooms touch without a separating wall: '+name+', '+other)
    doors=[]
    for name,spec in data['doors'].items():
        first,second=spec['rooms']
        if first==second or first not in rooms or second not in rooms:raise ValueError('Door requires two different existing rooms')
        a,b=rooms[first],rooms[second]
        points=spec['points']
        if len(points)!=2:raise ValueError('Door needs two jamb points')
        if a[1]<b[0] or b[1]<a[0]:
            a,b=sorted((a,b),key=lambda r:r[0]);direction='vertical'
            lo,hi=sorted(round(finite(p[1]),9) for p in points)
            if not max(a[2],b[2])+TOL<lo<hi<min(a[3],b[3])-TOL:raise ValueError('Door jambs must lie within the shared wall span')
            r=[a[1],b[0],lo,hi]
        elif a[3]<b[2] or b[3]<a[2]:
            a,b=sorted((a,b),key=lambda r:r[2]);direction='horizontal'
            lo,hi=sorted(round(finite(p[0]),9) for p in points)
            if not max(a[0],b[0])+TOL<lo<hi<min(a[1],b[1])-TOL:raise ValueError('Door jambs must lie within the shared wall span')
            r=[lo,hi,a[3],b[2]]
        else:raise ValueError('Rooms do not define an orthogonal separating wall')
        if min(r[1]-r[0],r[3]-r[2])<=TOL:raise ValueError('Degenerate doorway')
        if any(overlap(r,box) for room,box in rooms.items() if room not in (first,second)):
            raise ValueError('Another room obstructs the proposed shared wall')
        if any(overlap(r,d['rect']) for d in doors):raise ValueError('Doorways overlap')
        height=finite(spec['height'])
        if height<=TOL:raise ValueError('Door height must be positive')
        doors.append(dict(name=name,rect=r,width=hi-lo,height=height,direction=direction,rooms=[first,second]))
    regions,wall_area=boundaries(outer,list(rooms.values())+[d['rect'] for d in doors])
    return dict(regions=regions,wall_area=wall_area,rooms=copy.deepcopy(rooms),doors=doors,
                loop_count=sum(1+len(r['holes']) for r in regions),
                segment_count=sum(len(r['outer'])+sum(len(h) for h in r['holes']) for r in regions),
                validation='closed_nonbranching_orthogonal_boundaries',geometry_tolerance=TOL)
