"""Three-click, persistent linear dimensions represented by grouped geometry."""
from engine.coordinates import world_length, local_ray, local_vector, local_projection
import json
from engine import core
from engine.qt import QtCore, QtGui
from engine.viewer.overlays import draw_inference
from .drawing_support import infer, draw_path
from .edit_tool_support import interactive, operation



@interactive
class DimensionTool(core.IBaseTool):
    def __init__(self,view):
        super().__init__(view.view_proxy)
        self.view=view

    @property
    def is_begin(self):return self.state>0

    def activate(self):
        self.state=0;self.a=self.b=self.hover=None;self.offset=0.;self.plane=None
        self.input=core.CInputPointFinder(self.view.view_proxy)
        self.view.setMouseTracking(True)
        self.view.setStatusBar('尺寸标注：点起点、终点，再点标注线位置；Esc 取消')

    def deactivate(self):self.view.setMouseTracking(False)

    def set_end(self,point):
        if (point-self.a).Length()<.001:raise ValueError('两个测量点不能重合')
        self.b=point;self.axis=(self.b-self.a).Normalized()
        # Extension lines stay horizontal in the active XY coordinate frame.
        self.side=core.CVector3D(0,0,1).Cross(self.axis)
        if self.side.Length()<1e-5:
            forward=local_vector(self.view,self.view.GetCameraForward()).Normalized()
            self.side=core.CVector3D(1,0,0) if abs(forward.y)>=abs(forward.x) else core.CVector3D(0,1,0)
        self.side=self.side.Normalized()
        self.plane=core.CPlane(self.axis.Cross(self.side),self.a)
        self.state=2

    def on_mouse_move(self,pos,mod):
        if self.state==2 and abs(self.axis.z)>.99999:
            # Compare horizontal mouse displacement at the second endpoint's height.
            horizontal=core.CPlane(core.CVector3D(0,0,1),self.b)
            ray=local_ray(self.view,pos.x(),pos.y())
            if abs(ray.dir.z)>1e-5:
                point=ray.PointAt(horizontal.IntersectWithLine(ray))
                delta=point-self.b
                self.side=core.CVector3D(1,0,0) if abs(delta.x)>=abs(delta.y) else core.CVector3D(0,1,0)
                self.plane=core.CPlane(self.axis.Cross(self.side),self.a)
        self.hover=infer(self.view,self.input,pos,self.a,plane=self.plane if self.state==2 else None)
        if self.state==2:self.offset=(self.hover-self.a).Dot(self.side)
        self.view.update()

    def on_left_button_down(self,pos,mod):
        self.on_mouse_move(pos,mod)
        if self.state==0:self.a=self.hover;self.state=1
        elif self.state==1:self.set_end(self.hover)
        else:
            if abs(self.offset)<.001:raise ValueError('请将标注线移离测量端点')
            self.create();self.activate()

    def on_left_button_up(self,pos):pass

    def geometry(self):
        length=(self.b-self.a).Length()
        height=max(.5,min(5.,length*.025))
        x=self.axis;y=self.side
        a=self.a+y*self.offset;b=self.b+y*self.offset
        sign=1 if self.offset>=0 else -1
        center=(a+b)*.5
        projection=local_projection(self.view)
        pa=projection.map(QtGui.QVector3D(*a.ToTuple()));pb=projection.map(QtGui.QVector3D(*b.ToTuple()))
        dx=abs(pb.x()-pa.x())*self.view.width()/2
        dy=abs(pb.y()-pa.y())*self.view.height()/2
        font=QtGui.QFont();font.setPixelSize(14);metrics=QtGui.QFontMetricsF(font)
        # Intersect the dimension's projected line with the padded text rectangle.
        half_fraction=min((metrics.horizontalAdvance(self.label())/2+5)/max(dx,1e-9),
                          (metrics.height()/2+3)/max(dy,1e-9),.45)
        gap=length*half_fraction
        lines=[(self.a,a+y*height*.5*sign),(self.b,b+y*height*.5*sign),
               (a,center-x*gap),(center+x*gap,b)]
        arrow=min(height*.7,length*.15)
        for tip,direction in ((a,x),(b,x*-1)):
            lines.extend([(tip,tip+direction*arrow+y*arrow*.35),(tip,tip+direction*arrow-y*arrow*.35)])
        return lines,center,height

    def label(self):
        from engine.units import format_length
        return format_length(world_length(self.view,self.b-self.a),getattr(self.view,'display_unit','cm'))

    @operation('创建尺寸标注')
    def create(self):
        dd=self.view.mainWindow.editing
        parent=dd.wrap(self.view.model.GetActiveComponent())
        name='尺寸标注';i=1
        while name in parent.names():i+=1;name='尺寸标注%d'%i
        obj=dd.build.component(name,parent=parent)
        lines,center,height=self.geometry()
        for a,b in lines:dd.build.line(a.ToTuple(),b.ToTuple(),target=obj.definition)
        obj.definition.native.description=json.dumps(dict(kind='linear_dimension',version=2,
            start=self.a.ToTuple(),end=self.b.ToTuple(),offset=self.offset,side=self.side.ToTuple(),
            label_position=center.ToTuple(),distance_cm=world_length(self.view,self.b-self.a),
            text=self.label(),associative=False),ensure_ascii=False)
        dd.edit.touch(obj.definition)
        self.view.model.SetSelection([obj.native])
        return obj

    def draw(self,gl):
        draw_inference(self.view,self.input,gl)
        gl.glPushAttrib(gl.GL_ENABLE_BIT|gl.GL_CURRENT_BIT|gl.GL_LINE_BIT)
        try:
            gl.glDisable(gl.GL_LIGHTING);gl.glDisable(gl.GL_TEXTURE_2D)
            if self.state==1 and self.hover is not None:draw_path(gl,[self.a,self.hover])
            elif self.state==2:
                for a,b in self.geometry()[0]:draw_path(gl,[a,b])
        finally:gl.glPopAttrib()

    def draw_2d(self,painter):
        if self.state!=2:return
        point=self.geometry()[1]
        projection=local_projection(self.view)
        p=projection.map(QtGui.QVector3D(*point.ToTuple()))
        if not -1<=p.z()<=1:return
        painter.save()
        try:
            font=painter.font();font.setPixelSize(14);painter.setFont(font)
            painter.setPen(QtGui.QColor(40,65,120))
            text=self.label();width=painter.fontMetrics().horizontalAdvance(text)
            painter.drawText(QtCore.QPointF((p.x()+1)*self.view.width()/2-width/2,(1-p.y())*self.view.height()/2+(painter.fontMetrics().ascent()-painter.fontMetrics().descent())/2),text)
        finally:painter.restore()
