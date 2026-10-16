"""Face-aligned section placement in active editing coordinates."""
from engine.coordinates import local_ray, local_plane, local_projection
from engine import core
from .edit_tool_support import interactive, operation


def section_frame(plane):
    s, t = plane.ComputeST()
    n = plane.GetNormal()
    return n * (-plane.w / n.Dot(n)), s, t


def component_section_bounds(comp, plane):
    box = comp.GetBoundingBox()
    origin, s, t = section_frame(plane)
    projected = [core.CVector3D(x,y,z)-origin for x in (box.min_x,box.max_x)
                 for y in (box.min_y,box.max_y) for z in (box.min_z,box.max_z)]
    bounds = core.CBounds2D()
    bounds.min_x = min(p.Dot(s) for p in projected)
    bounds.max_x = max(p.Dot(s) for p in projected)
    bounds.min_y = min(p.Dot(t) for p in projected)
    bounds.max_y = max(p.Dot(t) for p in projected)
    return bounds


def section_corners(plane, bounds):
    origin, s, t = section_frame(plane)
    pad_x = (bounds.max_x-bounds.min_x)*.05
    pad_y = (bounds.max_y-bounds.min_y)*.05
    x0,x1 = bounds.min_x-pad_x,bounds.max_x+pad_x
    y0,y1 = bounds.min_y-pad_y,bounds.max_y+pad_y
    return [origin+s*x+t*y for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]


def pick_section_frame(view, pos):
    if not getattr(view,'show_section_planes',True):
        return None
    from engine.qt import QtGui
    projection = local_projection(view)
    hits = []
    for entity in view.model.GetActiveComponent().EnumEntities():
        if not isinstance(entity,core.CSectionPlane) or entity.IsMarkedDeleted() or entity.IsHide():
            continue
        points = [projection.map(QtGui.QVector3D(*p.ToTuple()))
                  for p in section_corners(entity.plane,entity.bounds)]
        for a,b in zip(points,points[1:]+points[:1]):
            if not (-1<=a.z()<=1 and -1<=b.z()<=1): continue
            ax,ay=(a.x()+1)*view.width()/2-.5,(1-a.y())*view.height()/2-.5
            bx,by=(b.x()+1)*view.width()/2-.5,(1-b.y())*view.height()/2-.5
            dx,dy=bx-ax,by-ay
            t=max(0.,min(1.,((pos.x()-ax)*dx+(pos.y()-ay)*dy)/max(dx*dx+dy*dy,1e-12)))
            distance=(pos.x()-ax-t*dx)**2+(pos.y()-ay-t*dy)**2
            if distance<=36:
                hits.append((distance,a.z()+t*(b.z()-a.z()),entity))
    return min(hits,key=lambda hit:hit[:2])[2] if hits else None


def draw_section_frame(gl, plane, bounds, preview=False, selected=False):
    origin, s, t = section_frame(plane)
    gl.glPushAttrib(gl.GL_ENABLE_BIT | gl.GL_CURRENT_BIT | gl.GL_LINE_BIT | gl.GL_DEPTH_BUFFER_BIT)
    try:
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_TEXTURE_2D)
        if preview:
            gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDepthMask(False)
        gl.glColor3f(*((1., .1, .85) if preview else ((.1,.55,1.) if selected else (1.,.5,.05))))
        gl.glLineWidth(2.)
        corners = section_corners(plane,bounds)
        gl.glBegin(gl.GL_LINE_LOOP)
        for p in corners:
            gl.glVertex3d(p.x,p.y,p.z)
        gl.glEnd()
        size = max(bounds.max_x-bounds.min_x,bounds.max_y-bounds.min_y)*.15
        normal = plane.GetNormal().Normalized()
        gl.glBegin(gl.GL_LINES)
        for base in corners:
            tip = base+normal*size
            for a,b in ((base,tip),(tip,tip-normal*size*.3+s*size*.15),
                        (tip,tip-normal*size*.3-s*size*.15)):
                for p in (a,b): gl.glVertex3d(p.x,p.y,p.z)
        gl.glEnd()
    finally:
        gl.glPopAttrib()


@interactive
class SectionTool(core.IBaseTool):
    is_begin = False

    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view

    def activate(self):
        self.input = core.CInputPointFinder(self.view.view_proxy)
        self.plane = None
        self.bounds = None
        self.view.setMouseTracking(True)
        self.view.setStatusBar('捕获面后单击创建剖切面；Esc 取消')

    def deactivate(self):
        self.plane = None
        self.view.setMouseTracking(False)

    def on_mouse_move(self, pos, mod):
        self.plane = None
        self.input.Reset()
        if not self.input.Inference(pos.x(),pos.y(),None,None): return
        if self.input.snap_type != core.SnapType.face: return
        plane = local_plane(self.view,self.input.pick_helper.GetFacePlane())
        ray = local_ray(self.view,pos.x(),pos.y())
        if abs(plane.GetNormal().Dot(ray.dir)) < 1e-9: return
        point = ray.PointAt(plane.IntersectWithLine(ray))
        # Section normal is always opposite the picked face, independent of camera.
        normal = plane.GetNormal().Normalized()*-1
        point = point + normal*.1
        self.plane = core.CPlane(normal,point)
        origin,s,t = section_frame(self.plane)
        delta = point-origin
        radius = max(5.,self.view.camera_zoom*.08)
        box = core.CBounds2D()
        box.min_x,box.max_x = delta.Dot(s)-radius,delta.Dot(s)+radius
        box.min_y,box.max_y = delta.Dot(t)-radius,delta.Dot(t)+radius
        self.bounds = box

    def on_left_button_down(self, pos, mod):
        self.on_mouse_move(pos,mod)
        if self.plane is not None:
            self.create_section()
            self.activate()

    def on_left_button_up(self, pos):
        pass

    @operation('创建剖切面')
    def create_section(self):
        comp = self.view.model.GetActiveComponent()
        limit = getattr(self.view.pipeline, 'section_limit', 6)
        if sum(isinstance(e,core.CSectionPlane) and not e.IsMarkedDeleted() and not e.IsHide()
               and e.is_active for e in comp.EnumEntities()) >= limit:
            raise ValueError('已达到当前显卡支持的剖切面数量，请先清除剖切面')
        # Capture the component bounds before adding the new drawing element.
        bounds = component_section_bounds(comp,self.plane)
        section = core.CEntityFactory(self.view.model).NewSectionPlane()
        section.plane = self.plane
        section.bounds = bounds
        section.is_active = True
        comp.AddEntity(section)

    def draw(self, gl):
        if self.plane is not None:
            draw_section_frame(gl,self.plane,self.bounds,True)
