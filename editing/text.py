"""Qt font outlines and native planar/solid text geometry, in centimetres."""
import math
from engine import core
from engine.qt import QtGui
from .planar import area, inside


class TextRing(list):
    def __init__(self,points,smooth,curves):
        super().__init__(points)
        self.smooth=smooth
        self.curves=curves

    def reversed(self):
        n=len(self)
        return TextRing(list(reversed(self)),list(reversed(self.smooth)),
                        [self.curves[(n-2-i)%n] for i in range(n)])


def flatten_cubic(points,tolerance):
    """Convex-hull distance to the finite chord bounds the approximation error."""
    a,b,c,d=points
    def distance(p):
        dx,dy=d[0]-a[0],d[1]-a[1]
        t=max(0.,min(1.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/max(dx*dx+dy*dy,1e-30)))
        return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
    if max(distance(b),distance(c))<=tolerance:return [d]
    def mid(p,q):return ((p[0]+q[0])/2,(p[1]+q[1])/2)
    ab,bc,cd=mid(a,b),mid(b,c),mid(c,d)
    abc,bcd=mid(ab,bc),mid(bc,cd);m=mid(abc,bcd)
    return flatten_cubic((a,ab,abc,m),tolerance)+flatten_cubic((m,bcd,cd,d),tolerance)


def font_rings(path,scale,box,tolerance):
    def xy(e):return ((e.x-box.left())*scale,(box.bottom()-e.y)*scale)
    subpaths=[];segments=[];current=None;first=None;label=0;i=0
    def close():
        if segments:
            if math.dist(segments[-1][0][-1],first)>1e-9:
                segments.append(([segments[-1][0][-1],first],None))
            subpaths.append(list(segments));segments.clear()
    while i<path.elementCount():
        e=path.elementAt(i)
        if e.isMoveTo():
            close();current=first=xy(e)
        elif e.isLineTo():
            end=xy(e)
            if math.dist(current,end)>1e-9:segments.append(([current,end],None))
            current=end
        elif e.isCurveTo():
            b,c,d=xy(e),xy(path.elementAt(i+1)),xy(path.elementAt(i+2))
            segments.append(([current,b,c,d],label));label+=1;current=d;i+=2
        i+=1
    close();rings=[]
    for segments in subpaths:
        points=[];smooth=[];curves=[]
        for index,(controls,label) in enumerate(segments):
            previous=segments[index-1][0]
            incoming=next(( (previous[-1][0]-p[0],previous[-1][1]-p[1]) for p in reversed(previous[:-1])
                           if math.dist(p,previous[-1])>1e-9),(0,0))
            outgoing=next(((p[0]-controls[0][0],p[1]-controls[0][1]) for p in controls[1:]
                           if math.dist(p,controls[0])>1e-9),(0,0))
            denom=math.hypot(*incoming)*math.hypot(*outgoing)
            tangent=denom>0 and sum(a*b for a,b in zip(incoming,outgoing))/denom>=math.cos(math.radians(2))
            samples=flatten_cubic(controls,tolerance) if label is not None else [controls[-1]]
            for j,p in enumerate([controls[0]]+samples[:-1]):
                points.append(p);smooth.append(tangent if j==0 else True);curves.append(label)
        # Remove redundant straight joins only; retain curve approximation guarantees.
        for j in range(len(points)-1,-1,-1):
            if len(points)>3 and curves[j] is None and curves[j-1] is None:
                a,p,b=points[j-1],points[j],points[(j+1)%len(points)]
                if abs((p[0]-a[0])*(b[1]-a[1])-(p[1]-a[1])*(b[0]-a[0]))<1e-10 and smooth[j]:
                    del points[j];del smooth[j];del curves[j]
        if len(points)>=3 and abs(area(points))>1e-6:
            if any(math.dist(a,b)<=.001 for a,b in zip(points,points[1:]+points[:1])):
                raise ValueError('文字轮廓小于引擎精度，请增大文字高度或更换字体')
            rings.append(TextRing(points,smooth,curves))
    return rings


def outline(text, font, height, depth, error_percent=.1):
    if not text.strip() or len(text)>256:
        raise ValueError('请输入 1 至 256 个字符的文字')
    if not all(math.isfinite(v) for v in (height,depth)) or height<=.01 or depth<0:
        raise ValueError('文字高度必须大于 0.01 cm，挤出高度不能为负数')
    if not math.isfinite(error_percent) or not .001<=error_percent<=5:
        raise ValueError('误差控制须在字高的 0.001% 至 5% 之间')
    font=QtGui.QFont(font);font.setPixelSize(1000)
    path=QtGui.QPainterPath()
    spacing=QtGui.QFontMetricsF(font).lineSpacing()
    for i,line in enumerate(text.splitlines()):path.addText(0,i*spacing,font,line)
    box=path.boundingRect()
    if box.isEmpty():raise ValueError('这些字符没有可生成的轮廓')
    scale=height/box.height()
    rings=font_rings(path,scale,box,height*error_percent/100)
    if not rings:raise ValueError('文字过小，无法生成有效轮廓')
    rings.sort(key=lambda r:abs(area(r)),reverse=True)
    parents=[];levels=[]
    for i,ring in enumerate(rings):
        candidates=[j for j in range(i) if inside(ring[0],rings[j])]
        parent=min(candidates,key=lambda j:abs(area(rings[j]))) if candidates else None
        parents.append(parent);levels.append(0 if parent is None else levels[parent]+1)
    regions=[]
    for i,ring in enumerate(rings):
        if levels[i]%2:continue
        loops=[ring]+[r for j,r in enumerate(rings) if parents[j]==i]
        regions.append([r if (area(r)>0)==(k==0) else r.reversed() for k,r in enumerate(loops)])
    return dict(text=text,regions=regions,depth=depth)


def build_definition(session, plan):
    session.edit.require_operation()
    factory=core.CEntityFactory(session.model)
    comp=factory.NewComponentDefinition();comp.name='文字：'+plan['text'][:32]
    session.model.addDefinition(comp)
    depth=plan['depth']
    for region in plan['regions']:
        vertices=[];bottom=[];top=[]
        for ring in region:
            indices=[]
            for x,y in ring:
                indices.append(len(vertices));vertices.append(factory.NewVertex(core.CVector3D(x,y,0)))
            bottom.append(indices)
        if depth:
            count=len(vertices)
            vertices += [factory.NewVertex(v.Pos()+core.CVector3D(0,0,depth)) for v in vertices[:count]]
            top=[[i+count for i in ring] for ring in bottom]
        edges={}
        def face(loops):
            f=factory.NewFace()
            native_loops=[]
            for k,indices in enumerate(loops):
                loop=factory.NewLoop();loop.SetIsOuterLoop(k==0)
                for a,b in zip(indices,indices[1:]+indices[:1]):
                    key=(min(a,b),max(a,b))
                    if key not in edges:
                        edges[key]=factory.NewEdge(vertices[key[0]],vertices[key[1]],False)
                        comp.AddEntity(edges[key])
                    loop.AddEdgeUseToTail(factory.NewEdgeUse(edges[key],a!=key[0]))
                f.AddLoop(loop);native_loops.append(loop)
            if not f.UpdatePlane():raise ValueError('文字轮廓含退化面，请增大文字高度或更换字体')
            for loop in native_loops:loop.ComputeIsConvex(f.GetPlane().GetNormal())
            comp.AddEntity(f)
        if depth:
            face([list(reversed(r)) for r in bottom]);face(top)
            for low,high in zip(bottom,top):
                for i,a in enumerate(low):
                    j=(i+1)%len(low);face([[a,low[j],high[j],high[i]]])
        else:face(bottom)
        for ring,low in zip(region,bottom):
            if depth:
                for index,smooth in zip(low,ring.smooth):
                    if smooth:
                        edge=edges[(index,index+count)]
                        edge.SetSoft(True);edge.SetSmooth(True)
            for offset in ((0,count) if depth else (0,)):
                groups={}
                for i,label in enumerate(ring.curves):
                    if label is None:continue
                    a,b=low[i]+offset,low[(i+1)%len(low)]+offset
                    edge=edges[(min(a,b),max(a,b))]
                    if label not in groups:
                        curve=factory.NewCurve();curve.SetParentComponent(comp)
                        groups[label]=(curve,edge)
                    edge.SetCurve(groups[label][0])
                for curve,first in groups.values():curve.UpdateEdgeLink(first)
    session.edit.touch(session.wrap(comp))
    return comp
