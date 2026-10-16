"""Three-click planar angle measurement with exact-geometry and 10-degree snaps."""
from engine.coordinates import to_local, to_world, local_ray, local_plane, local_vector, local_projection
import math
from engine import core
from engine.qt import QtCore,QtGui
from .drawing_support import EXACT,basis,draw_path
from .edit_tool_support import interactive


def snapped_angle(angle,exact=False):
    nearest=math.floor(angle/10+.5)*10
    return (nearest,True) if not exact and abs(angle-nearest)<=2 else (angle,False)


@interactive
class ProtractorTool(core.IBaseTool):
    @property
    def is_begin(self):return self.state in (1,2)

    def __init__(self,view):
        super().__init__(view.view_proxy);self.view=view

    def activate(self):
        self.input=core.CInputPointFinder(self.view.view_proxy)
        self.state=0;self.center=core.CVector3D();self.hover=None
        self.plane=core.CPlane(self.default_normal(),self.center)
        self.start=None;self.angle=0.;self.angle_snap=False
        self.view.setMouseTracking(True)
        self.view.setStatusBar('量角器：选择中心点，再选择起始方向和结束方向；每 10° 吸附；Esc 重置')

    def default_normal(self):
        forward=local_vector(self.view,self.view.GetCameraForward()).Normalized()
        axes=[core.CVector3D(1,0,0),core.CVector3D(0,1,0),core.CVector3D(0,0,1)]
        return max(axes,key=lambda n:abs(n.Dot(forward)))

    def deactivate(self):self.view.setMouseTracking(False)

    def point(self,pos):
        self.input.Reset()
        if not self.input.Inference(pos.x(),pos.y(),getattr(self,'entity_filter',None),to_world(self.view,self.center) if self.state in (1,2) else None):
            return None,False
        point=to_local(self.view,self.input.Position())
        if self.state in (0,3):
            hit=self.input.pick_helper.PickedFace()
            normal=(local_plane(self.view,self.input.pick_helper.GetFacePlane()).GetNormal()
                    if hit is not None and isinstance(hit.e,core.CFace) else self.default_normal())
            self.plane=core.CPlane(normal.Normalized(),point)
            return point,False
        exact=self.input.snap_type in EXACT
        if exact and abs(self.plane.ProjPoint(point))<.001:return point,True
        ray=local_ray(self.view,pos.x(),pos.y())
        if abs(self.plane.GetNormal().Dot(ray.dir))<1e-8:return None,False
        return ray.PointAt(self.plane.IntersectWithLine(ray)),False

    def update_end(self,point,exact=False):
        delta=point-self.center
        if delta.Length()<=core.EPS:return False
        x,y=self.axes()
        angle=math.degrees(math.atan2(delta.Dot(y),delta.Dot(x)))%360
        self.angle,self.angle_snap=snapped_angle(angle,exact)
        radians=math.radians(self.angle)
        self.hover=self.center+(x*math.cos(radians)+y*math.sin(radians))*delta.Length()
        suffix='（10° 吸附）' if self.angle_snap else ''
        self.view.setStatusBar('角度 %.2f°%s；%s，Esc 重置'%(abs(self.angle),suffix,
                               '单击确定起始方向' if self.state==1 else '单击结束'))
        return True

    def on_mouse_move(self,pos,modifiers):
        if self.state==3:return
        point,exact=self.point(pos)
        if point is None:return
        if self.state==0:self.center=point
        if self.state==0:self.hover=point
        else:self.update_end(point,exact)

    def on_left_button_down(self,pos,mod):
        point,exact=self.point(pos)
        if point is None:return
        if self.state in (0,3):
            self.center=point;self.hover=point;self.start=None;self.state=1;self.angle=0;self.angle_snap=False
            self.view.setStatusBar('量角器：选择起始方向')
        elif self.state==1:
            if not self.update_end(point,exact):return
            self.start=self.hover;self.state=2;self.angle=0;self.angle_snap=False
            self.view.setStatusBar('量角器：选择结束方向；靠近整 10° 时吸附')
        elif self.update_end(point,exact):
            self.state=3
            self.view.setStatusBar('测量角度 %.2f°；点击开始新测量，Esc 重置'%abs(self.angle))

    def on_left_button_up(self,pos):pass

    def axes(self):
        if self.start is not None:
            x=(self.start-self.center).Normalized()
            return x,self.plane.GetNormal().Normalized().Cross(x)
        return basis(self.plane)

    def radius(self):return max(1.,self.view.camera_zoom*.08)

    def draw(self,gl):
        x,y=self.axes();radius=self.radius()
        def at(angle,r):
            a=math.radians(angle)
            return self.center+(x*math.cos(a)+y*math.sin(a))*r
        gl.glPushAttrib(gl.GL_ENABLE_BIT|gl.GL_CURRENT_BIT|gl.GL_LINE_BIT|gl.GL_DEPTH_BUFFER_BIT)
        try:
            gl.glDisable(gl.GL_DEPTH_TEST);gl.glDisable(gl.GL_LIGHTING)
            gl.glDisable(gl.GL_TEXTURE_2D);gl.glDisable(gl.GL_LINE_STIPPLE);gl.glDepthMask(False)
            gl.glLineWidth(1.5)
            draw_path(gl,[at(a,radius) for a in range(0,360,3)],True,(.25,.55,.75))
            gl.glColor3f(.25,.55,.75);gl.glBegin(gl.GL_LINES)
            for a in range(0,360,10):
                for p in (at(a,radius*(.82 if a%30==0 else .9)),at(a,radius)):
                    gl.glVertex3d(p.x,p.y,p.z)
            gl.glEnd()
            core.draw_target_with_size(self.center,radius*.05,gl)
            if self.start is not None:draw_path(gl,[self.center,self.start],color=(.2,.5,.85))
            if self.state and self.hover is not None:draw_path(gl,[self.center,self.hover],color=(1.,.45,.05))
            if self.state>=1 and self.hover is not None and (self.hover-self.center).Length()>core.EPS:
                steps=max(1,int(abs(self.angle)/3))
                draw_path(gl,[at(self.angle*i/steps,radius*.65) for i in range(steps+1)],color=(1.,.45,.05))
        finally:gl.glPopAttrib()

    def draw_2d(self,painter):
        projection=local_projection(self.view)
        center=projection.map(QtGui.QVector3D(*self.center.ToTuple()))
        def label(point,text,radial=False):
            q=projection.map(QtGui.QVector3D(*point.ToTuple()))
            if -1<=q.z()<=1:
                px=(q.x()+1)*self.view.width()/2
                py=(1-q.y())*self.view.height()/2
                if radial:
                    bounds=painter.fontMetrics().boundingRect(text)
                    dx=(q.x()-center.x())*self.view.width()/2
                    dy=(center.y()-q.y())*self.view.height()/2
                    length=math.hypot(dx,dy)
                    if length<1e-6:return
                    dx,dy=dx/length,dy/length
                    gap=4+abs(dx)*bounds.width()/2+abs(dy)*bounds.height()/2
                    px+=dx*gap-bounds.center().x()
                    py+=dy*gap-bounds.center().y()
                else:
                    px+=4;py-=4
                painter.drawText(QtCore.QPointF(px,py),text)
        painter.save()
        try:
            if self.state>=1 and self.hover is not None and (self.hover-self.center).Length()>core.EPS:
                x,y=self.axes();radius=self.radius()
                painter.setPen(QtGui.QColor(35,90,135))
                for degrees in range(0,361,30):
                    if degrees>=abs(self.angle):break
                    radians=math.radians(degrees)
                    point=self.center+(x*math.cos(radians)+y*math.sin(radians))*radius
                    label(point,str(degrees),radial=True)
                painter.setPen(QtGui.QColor(185,75,0))
                label(self.center,'%.2f°'%abs(self.angle))
        finally:painter.restore()
