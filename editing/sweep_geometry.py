"""Planar miter sweeps, independent of the native engine (Python 3.8)."""
import math

EPS = 0.001


def pipe_mesh(path, radius=5, wall=0.4, segments=32, up=(0,1,0), miter_limit=10):
    """Open planar tube, with annular rims instead of solid end caps."""
    radius,wall=float(radius),float(wall)
    if not all(math.isfinite(x) for x in (radius,wall)) or not EPS <= wall < radius-EPS:
        raise ValueError('Pipe requires finite radius > wall >= 0.001 and a nonzero bore')
    if isinstance(segments,bool) or not isinstance(segments,int) or not 8<=segments<=128:
        raise ValueError('Pipe segments must be an integer from 8 to 128')
    path=[point(p,3) for p in path]
    if len(path)>1 and length(sub(path[0],path[-1]))<EPS:
        raise ValueError('Pipe requires an open path')
    if 2*segments*len(path)>50000: raise ValueError('Pipe exceeds 50000 vertices')
    def section(r):
        return [(r*math.cos(2*math.pi*i/segments),r*math.sin(2*math.pi*i/segments)) for i in range(segments)]
    outer=mesh(section(radius),path,up=up,miter_limit=miter_limit)
    inner=mesh(section(radius-wall),path,up=up,miter_limit=miter_limit)
    offset=len(outer['vertices']);n=len(outer['path']);k=segments
    faces=outer['faces'][:-2]+[[v+offset for v in reversed(f)] for f in inner['faces'][:-2]]
    rims=[[],[]]
    for i in range(k):
        j=(i+1)%k
        rims[0].append(len(faces));faces.append([j,i,offset+i,offset+j])
        a=(n-1)*k+i;b=(n-1)*k+j
        rims[1].append(len(faces));faces.append([a,b,offset+b,offset+a])
    return dict(vertices=outer['vertices']+inner['vertices'],faces=faces,closed=False,
                volume=outer['volume']-inner['volume'],path=outer['path'],up=outer['up'],
                path_length=outer['path_length'],max_miter=outer['max_miter'],rims=rims,
                recipe=dict(kind='pipe',path=outer['path'],radius=radius,wall=wall,
                            segments=segments,up=outer['up'],miter_limit=miter_limit))


def add(a, b): return tuple(x+y for x, y in zip(a, b))
def sub(a, b): return tuple(x-y for x, y in zip(a, b))
def mul(a, t): return tuple(x*t for x in a)
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def length(a): return math.sqrt(dot(a, a))


def point(p, n):
    p = tuple(float(x) for x in p)
    if len(p) != n or not all(math.isfinite(x) for x in p):
        raise ValueError('Expected %d finite coordinates' % n)
    return p


def unit(p):
    p = point(p, 3)
    size = length(p)
    if size < EPS: raise ValueError('Zero direction')
    return mul(p, 1/size)


def area(points):
    return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))/2


def intersects(a, b, c, d):
    def turn(p,q,r):
        return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    def on(p,q,r):
        return (abs(turn(p,q,r)) <= EPS*max(length(sub(q,p)),EPS) and
                all(min(x,y)-EPS <= z <= max(x,y)+EPS for x,y,z in zip(p,q,r)))
    u,v,w,x = turn(a,b,c),turn(a,b,d),turn(c,d,a),turn(c,d,b)
    return (u*v < 0 and w*x < 0) or on(a,b,c) or on(a,b,d) or on(c,d,a) or on(c,d,b)


def simple(points, closed):
    pairs = list(zip(points, points[1:]+points[:1] if closed else points[1:]))
    for i,(a,b) in enumerate(pairs):
        if length(sub(b,a)) < EPS: raise ValueError('Segment below engine tolerance')
        for j in range(i+1,len(pairs)):
            if j == i+1 or (closed and i == 0 and j == len(pairs)-1): continue
            if intersects(a,b,*pairs[j]): raise ValueError('Self-intersecting or touching contour/path')


def ordered_edges(segments):
    """Order one connected edge chain by native vertex IDs, not scene degree."""
    adjacent, positions, edges = {}, {}, []
    for a,p,b,q in segments:
        if a == b: raise ValueError('Degenerate edge')
        if frozenset((a,b)) in edges: raise ValueError('Duplicate edge')
        edges.append(frozenset((a,b)))
        positions[a], positions[b] = point(p,3), point(q,3)
        adjacent.setdefault(a,[]).append(b); adjacent.setdefault(b,[]).append(a)
    if not edges: raise ValueError('Empty path')
    if any(len(v)>2 for v in adjacent.values()): raise ValueError('Branching path')
    ends = sorted(k for k,v in adjacent.items() if len(v)==1)
    if len(ends) not in (0,2): raise ValueError('Disconnected path')
    start = ends[0] if ends else min(adjacent)
    order, prev, cur = [], None, start
    while cur not in order:
        order.append(cur)
        following = sorted(v for v in adjacent[cur] if v != prev)
        if not following: break
        prev,cur = cur,following[0]
    if len(order) != len(adjacent): raise ValueError('Disconnected path')
    return [positions[v] for v in order], not ends


def mesh(profile, path, closed=False, up=(0,0,1), anchor=(0,0), offset=(0,0), miter_limit=10):
    """Profile (lateral,height); lateral = up cross travel direction."""
    profile = [point(p,2) for p in profile]
    path = [point(p,3) for p in path]
    if len(profile)>1 and length(sub(profile[0],profile[-1]))<EPS: profile.pop()
    if len(path)>1 and length(sub(path[0],path[-1]))<EPS:
        closed = True; path.pop()
    if not 3 <= len(profile) <= 512: raise ValueError('Profile needs 3..512 points')
    if not (3 if closed else 2) <= len(path) <= 1000: raise ValueError('Invalid path point count')
    if len(profile)*len(path)>50000: raise ValueError('Sweep exceeds 50000 vertices')
    simple(profile,True)
    for i,p in enumerate(profile):
        a,b=sub(p,profile[i-1]),sub(profile[(i+1)%len(profile)],p)
        if dot(a,b)/(length(a)*length(b)) < -0.999999:
            raise ValueError('Profile doubles back on itself')
    if abs(area(profile))<EPS*EPS: raise ValueError('Zero profile area')
    if area(profile)<0: profile.reverse()
    anchor,offset = point(anchor,2),point(offset,2)
    profile = [add(sub(p,anchor),offset) for p in profile]
    up = unit(up)
    if not math.isfinite(miter_limit) or miter_limit<1: raise ValueError('miter_limit must be >= 1')
    if any(abs(dot(sub(p,path[0]),up))>EPS for p in path):
        raise ValueError('Path must lie in a plane perpendicular to up')
    # Project tolerance-small departures to one plane.
    path = [sub(p,mul(up,dot(sub(p,path[0]),up))) for p in path]
    # Remove forward collinear intermediate points, reject reversals.
    changed = True
    while changed:
        changed = False
        for i in range(len(path)) if closed else range(1,len(path)-1):
            before = unit(sub(path[i],path[i-1]))
            after = unit(sub(path[(i+1)%len(path)],path[i]))
            if dot(before,after)<-0.999999: raise ValueError('Path reverses direction')
            if length(cross(before,after))<1e-9:
                path.pop(i); changed=True; break
        if len(path)<(3 if closed else 2): raise ValueError('Degenerate path')
    direction = unit(sub(path[1],path[0])); lateral = cross(up,direction)
    project = lambda p: (dot(sub(p,path[0]),direction),dot(sub(p,path[0]),lateral))
    simple([project(p) for p in path],closed)
    n = len(path)
    dirs = [unit(sub(path[(i+1)%n],path[i])) for i in range(n if closed else n-1)]
    sides = [cross(up,d) for d in dirs]
    miters = []
    for i in range(n):
        if not closed and i==0: m=sides[0]
        elif not closed and i==n-1: m=sides[-1]
        else:
            a,b = sides[i-1],sides[i%len(sides)]
            denom=1+dot(a,b)
            if denom<1e-9: raise ValueError('Path reverses direction')
            m=mul(add(a,b),1/denom)
        if length(m)>miter_limit: raise ValueError('Corner exceeds miter_limit')
        miters.append(m)
    # Ensure even the extreme lateral offsets remain simple and advance on
    # every segment. Also check their boundary against each other.
    tracks=[]
    for side in (min(p[0] for p in profile),max(p[0] for p in profile)):
        track=[add(p,mul(m,side)) for p,m in zip(path,miters)]
        for i,d in enumerate(dirs):
            if dot(sub(track[(i+1)%n],track[i]),d)<EPS:
                raise ValueError('Profile too wide for a path segment/corner')
        track=[project(p) for p in track];simple(track,closed);tracks.append(track)
    # The lateral envelope is a simple strip (open) or disjoint ring pair.
    if closed:
        for a,b in zip(tracks[0],tracks[0][1:]+tracks[0][:1]):
            for c,d in zip(tracks[1],tracks[1][1:]+tracks[1][:1]):
                if intersects(a,b,c,d): raise ValueError('Sweep envelope overlaps')
    else:
        simple(tracks[0]+list(reversed(tracks[1])),True)
    vertices=[add(add(p,mul(m,s)),mul(up,h)) for p,m in zip(path,miters) for s,h in profile]
    k=len(profile); faces=[]
    for i in range(len(dirs)):
        j=(i+1)%n
        for a in range(k):
            b=(a+1)%k
            faces.append([i*k+a,i*k+b,j*k+b,j*k+a])
    if not closed:
        faces += [list(reversed(range(k))),list(range((n-1)*k,n*k))]
    # Consistently orient all faces outward using signed volume.
    volume=0
    for face in faces:
        a=sub(vertices[face[0]],vertices[0])
        for i in range(1,len(face)-1):
            volume += dot(a,cross(sub(vertices[face[i]],vertices[0]),sub(vertices[face[i+1]],vertices[0])))/6
    if abs(volume)<EPS**3: raise ValueError('Zero sweep volume')
    if volume<0: faces=[list(reversed(f)) for f in faces]
    return dict(vertices=vertices,faces=faces,volume=abs(volume),closed=closed,
                path=path,profile=profile,up=up,path_length=sum(length(sub(path[(i+1)%n],path[i])) for i in range(len(dirs))),
                max_miter=max(map(length,miters)))
