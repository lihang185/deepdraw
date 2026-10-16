"""Face handles scale one axis; corner handles scale uniformly about the opposite corner."""
from engine.coordinates import to_world, local_ray, local_projection, inverse_matrix
import itertools
import math
from engine import core
from engine.qt import QtCore, QtGui
from .transaction_tool import TransactionTool
from .edit_tool_support import interactive


@interactive
class ScaleTool(TransactionTool):
    input_prompt = '输入缩放比例（例如 2 或 0.5）'

    def activate(self):
        self.cancel_preview()
        self.hover = None
        self.drag = None
        self.view.setMouseTracking(True)
        self.view.setStatusBar('缩放：面中心单轴，角点等比；单击控制点后移动，再次单击确认；Enter 输入比例；Esc 取消')

    def cage_transform(self, entity):
        if isinstance(entity, core.CComponentInstance):
            return entity.GetTransform()
        # Keep the face basis stable throughout a preview.
        if self.drag is not None and self.drag['entity'] == entity:
            return self.drag['initial']
        vertices=list(entity.EnumVertices())
        origin=vertices[0].Pos()
        normal=entity.GetPlane().GetNormal().Normalized()
        x=next((v.Pos()-origin for v in vertices if (v.Pos()-origin).Length()>core.EPS)).Normalized()
        y=normal.Cross(x).Normalized()
        matrix=core.CMatrix()
        for axis,vector in enumerate((x,y,normal)):matrix.SetAxis(axis,vector)
        matrix.SetRow(3,origin)
        return matrix

    def cages(self):
        dd=self.view.mainWindow.editing
        parent=self.view.model.GetActiveComponent()
        for entity in self.view.model.GetSelection():
            if (entity is None or entity.IsMarkedDeleted()
                    or entity.GetParentComponent()!=parent):continue
            if isinstance(entity,core.CComponentInstance):
                box=dd.inspect.bounds(dd.wrap(entity.GetDefinition()))
            elif isinstance(entity,core.CFace):
                inverse=inverse_matrix(self.cage_transform(entity))
                points=[inverse.Transform(v.Pos()).ToTuple() for v in entity.EnumVertices()]
                low=[min(p[i] for p in points) for i in range(3)]
                high=[max(p[i] for p in points) for i in range(3)]
                low[2]=high[2]=0.
                box=dict(min=low,max=high,size=[high[i]-low[i] for i in range(3)])
            else:continue
            if box is not None:yield entity,box

    def project(self,p):
        q=(local_projection(self.view)).map(QtGui.QVector3D(*p.ToTuple()))
        if not -1<=q.z()<=1:return None
        return QtCore.QPointF((q.x()+1)*self.view.width()/2-.5,(1-q.y())*self.view.height()/2-.5)

    def handles(self):
        for entity,box in self.cages():
            center=[(a+b)/2 for a,b in zip(box['min'],box['max'])]
            for axis in range(3):
                if box['size'][axis]<=core.EPS:continue
                for side in (0,1):
                    point=list(center);point[axis]=box['max' if side else 'min'][axis]
                    world=self.cage_transform(entity).Transform(core.CVector3D(*point))
                    screen=self.project(world)
                    if screen is not None:yield entity,box,axis,side,point,world,screen
            dimensions=[i for i,size in enumerate(box['size']) if size>core.EPS]
            if len(dimensions)>=2:
                for bits in itertools.product(*[(0,1) if i in dimensions else (0,) for i in range(3)]):
                    point=[box['max' if bits[i] else 'min'][i] for i in range(3)]
                    world=self.cage_transform(entity).Transform(core.CVector3D(*point))
                    screen=self.project(world)
                    if screen is not None:yield entity,box,None,bits,point,world,screen

    def hit(self,pos):
        hits=[]
        for item in self.handles():
            d=(item[-1].x()-pos.x())**2+(item[-1].y()-pos.y())**2
            if d<=100:
                eye=self.view.camera.position
                distance=(QtGui.QVector3D(*to_world(self.view,item[-2]).ToTuple())-eye).lengthSquared()
                hits.append((d,distance,item))
        return min(hits,key=lambda h:h[:2])[2] if hits else None

    def axis_distance(self,pos):
        ray=local_ray(self.view,pos.x(),pos.y())
        direction=ray.dir.Normalized();axis=self.drag['direction']
        b=axis.Dot(direction);denom=1-b*b
        if denom<1e-5:raise ValueError('缩放轴接近视线方向，请调整视角')
        w=ray.PointAt(0)-self.drag['fixed']
        return (axis.Dot(w)-b*direction.Dot(w))/denom

    def begin_scale(self,item,pos):
        entity,box,axis,side,point,world,screen=item
        initial=self.cage_transform(entity)
        anchor=list(point)
        if axis is None:
            anchor=[box['min' if side[i] else 'max'][i] for i in range(3)]
        else:
            anchor[axis]=box['min' if side else 'max'][axis]
        fixed=initial.Transform(core.CVector3D(*anchor))
        length=(world-fixed).Length()
        if length<=core.EPS:raise ValueError('对象尺寸过小，无法缩放')
        self.drag=dict(entity=entity,initial=initial,axis=axis,anchor=anchor,
                       fixed=fixed,direction=(world-fixed).Normalized(),length=length)
        self.drag['start']=self.axis_distance(pos)
        face_mode=isinstance(entity,core.CFace)
        self.begin_transaction('等比缩放' if axis is None else '单轴缩放',
                               transform_targets=None if face_mode else (entity,), local_geometry=face_mode)
        if face_mode:
            vertices={v.GetID():v for v in entity.EnumVertices()}
            self.drag['vertices']=[(v,v.Pos()) for v in vertices.values()]
            faces={}
            for v in vertices.values():
                for loop in v.EnumLoops():
                    face=loop.GetParentFace();faces[face.GetID()]=face
            self.drag['faces']=list(faces.values())

    def preview_factor(self,factor):
        if not math.isfinite(factor) or factor<=0:raise ValueError('缩放比例必须大于零')
        self.view.mainWindow.editing.edit.require_operation()
        d=self.drag;scales=[1.,1.,1.]
        axes=range(3) if d['axis'] is None else (d['axis'],)
        for axis in axes:scales[axis]=factor
        matrix=core.CMatrix();matrix.Scale3(*scales)
        shift=[d['anchor'][i]*(1-scales[i]) for i in range(3)]
        matrix.SetRow(3,core.CVector3D(*shift))
        if 'vertices' in d:
            inverse=inverse_matrix(d['initial'])
            for vertex,point in d['vertices']:
                local=inverse.Transform(point)
                vertex.SetPosition(d['initial'].Transform(matrix.Transform(local)))
            for face in d['faces']:
                face.MarkDirty();face.UpdatePlane()
        else:
            d['entity'].SetTransform(d['initial'].Multiply(matrix))
        self.refresh()
        self.view.setStatusBar('缩放 %.3f 倍；单击确认；Enter 输入比例；Esc 取消'%factor)

    def on_left_button_down(self,pos,mod):
        if self.transaction is None:
            item=self.hit(pos)
            if item is not None:self.begin_scale(item,pos)
        else:
            self.on_mouse_move(pos,mod)
            self.commit();self.activate()

    def on_mouse_move(self,pos,mod):
        if self.transaction is not None:
            d=self.drag
            factor=1+(self.axis_distance(pos)-d['start'])/d['length']
            self.preview_factor(max(core.EPS/d['length'],factor))
        else:
            item=self.hit(pos)
            self.hover=(item[0].GetID(),item[2],item[3]) if item else None
            self.view.update()

    def on_left_button_up(self,pos):
        pass

    def enterValue(self,value):
        if self.transaction is None:raise ValueError('请先单击一个缩放控制点')
        self.preview_factor(float(value));self.commit();self.activate()

    def draw(self,gl):
        gl.glPushAttrib(gl.GL_ENABLE_BIT | gl.GL_DEPTH_BUFFER_BIT | gl.GL_POINT_BIT | gl.GL_CURRENT_BIT)
        try:
            gl.glEnable(gl.GL_DEPTH_TEST)
            gl.glDepthFunc(gl.GL_LEQUAL)
            gl.glDepthMask(False)
            gl.glDisable(gl.GL_LIGHTING)
            gl.glDisable(gl.GL_TEXTURE_2D)
            gl.glDisable(gl.GL_POINT_SMOOTH)
            gl.glPointSize(8*self.view.devicePixelRatioF())
            for entity,box,axis,side,point,world,p in self.handles():
                active=self.hover==(entity.GetID(),axis,side)
                gl.glColor3f(1.,1.,0.) if active else gl.glColor3f(.26,.87,.33)
                gl.glBegin(gl.GL_POINTS)
                gl.glVertex3d(world.x,world.y,world.z)
                gl.glEnd()
        finally:
            gl.glPopAttrib()

    def draw_2d(self,painter):
        if self._revision!=self.view.mainWindow.editing.revision:return
        painter.save()
        painter.setPen(QtGui.QPen(QtGui.QColor(230,180,20),1.5))
        for entity,box in self.cages():
            corners={bits:self.project(self.cage_transform(entity).Transform(core.CVector3D(
                *[box['max' if bits[i] else 'min'][i] for i in range(3)]))) for bits in itertools.product((0,1),repeat=3)}
            for bits,p in corners.items():
                for axis in range(3):
                    if bits[axis]:continue
                    other=list(bits);other[axis]=1;q=corners[tuple(other)]
                    if p is not None and q is not None:painter.drawLine(p,q)
        painter.restore()
