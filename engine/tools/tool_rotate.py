"""Three-point protractor rotation with absolute previews and transactional cancellation."""
from engine import core
from .edit_tool_support import interactive
from .transaction_tool import TransactionTool
from .tool_protractor import ProtractorTool
import math


def rotate_next_quadrant(view):
    """Snap one heading, or rotate a selection 90 degrees about its shared bounds."""
    dd=view.mainWindow.editing
    if dd.edit.active is not None:
        raise RuntimeError('请先完成当前建模操作')
    parent=view.model.GetActiveComponent()
    selected=list(view.model.GetSelection())
    if not selected or any(e.IsMarkedDeleted() or not isinstance(e,core.CComponentInstance)
                           or e.GetParentComponent()!=parent for e in selected):
        raise ValueError('请先选择当前编辑层的组或组件')
    changes=[]
    shared_rotation = None
    if len(selected) > 1:
        boxes = [dd.inspect.bounds(dd.wrap(entity)) for entity in selected]
        if any(box is None for box in boxes):
            raise ValueError('无法计算所选对象的包围盒')
        center = core.CVector3D(*[
            (min(box['min'][i] for box in boxes) + max(box['max'][i] for box in boxes))/2
            for i in range(2)], 0)
        shared_rotation = core.CMatrix()
        shared_rotation.RotateZ(90)
        shared_rotation.SetRow(3, center-shared_rotation.Transform(center))
    for entity in selected:
        initial=entity.GetTransform()
        if shared_rotation is not None:
            changes.append((entity, shared_rotation.Multiply(initial)))
            continue
        origin=initial.Transform(core.CVector3D())
        axis=initial.Transform(core.CVector3D(1,0,0))-origin
        offset=0
        if math.hypot(axis.x,axis.y)<1e-9:
            axis=initial.Transform(core.CVector3D(0,1,0))-origin
            offset=90
        if math.hypot(axis.x,axis.y)<1e-9:
            raise ValueError('对象在 XY 平面的朝向无法确定')
        heading=(math.degrees(math.atan2(axis.y,axis.x))-offset)%360
        target=((math.floor(heading/90+0.5+1e-10)+1)*90)%360
        rotation=core.CMatrix();rotation.RotateZ((target-heading)%360)
        result=rotation.Multiply(initial)
        result.SetRow(3,origin)
        changes.append((entity,result))
    with dd.edit.operation('递增直角旋转'):
        for entity,result in changes:dd.edit.set_transform(dd.wrap(entity), result)
    view.update()
    view.setStatusBar('已将 %d 个对象绕共同中心旋转 90°' % len(changes)
                      if shared_rotation is not None else '已旋转到下一直角朝向')


@interactive
class RotateTool(ProtractorTool, TransactionTool):
    input_prompt = '输入旋转角度（°）'

    def __init__(self, view):
        TransactionTool.__init__(self, view)

    def activate(self):
        self.cancel_preview()
        ProtractorTool.activate(self)
        self.targets = []
        self.entity_filter = None
        self.view.setStatusBar('旋转：选择组件，依次点击中心、起始方向、结束方向；Enter 输入角度；Esc 取消')

    def deactivate(self):
        TransactionTool.deactivate(self)

    def begin_rotate(self):
        selected = self.selected()
        if any(not isinstance(e, core.CComponentInstance) for e in selected):
            raise ValueError('请先选择当前编辑层的组件或组')
        self.begin_transaction('旋转', transform_targets=selected)
        self.targets = [(e, e.GetTransform()) for e in selected]
        excluded = {e.GetID() for e in selected}
        self.entity_filter = core.EntityFilter(lambda e: e.GetID() not in excluded)

    def preview_angle(self, angle):
        if self.transaction is None:return
        if not math.isfinite(angle):raise ValueError('请输入有限的旋转角度')
        self.view.mainWindow.editing.edit.require_operation()
        n = self.plane.GetNormal().Normalized()
        x,y,z=n.x,n.y,n.z
        a=math.radians(angle);c=math.cos(a);s=math.sin(a);k=1-c
        matrix=core.CMatrix()
        matrix.SetRow(0,core.CVector3D(c+x*x*k,x*y*k-z*s,x*z*k+y*s))
        matrix.SetRow(1,core.CVector3D(y*x*k+z*s,c+y*y*k,y*z*k-x*s))
        matrix.SetRow(2,core.CVector3D(z*x*k-y*s,z*y*k+x*s,c+z*z*k))
        matrix.is_identity=False
        matrix.is_orthogonal=True
        matrix.SetRow(3,self.center-matrix.Transform(self.center))
        for entity,initial in self.targets:
            entity.SetTransform(matrix.Multiply(initial))
        self.angle=angle
        self.refresh()
        self.view.setStatusBar('旋转 %.2f°；单击确认，Enter 输入角度，Esc 取消'%angle)

    def on_left_button_down(self,pos,mod):
        if self.state==0:
            selected=self.selected()
            if any(not isinstance(e,core.CComponentInstance) for e in selected):
                raise ValueError('请先选择当前编辑层的组件或组')
        previous=self.state
        ProtractorTool.on_left_button_down(self,pos,mod)
        if previous==1 and self.state==2:
            self.begin_rotate()
        elif previous==2 and self.state==3:
            self.preview_angle(self.angle)
            self.commit();self.activate()

    def on_mouse_move(self,pos,modifiers):
        ProtractorTool.on_mouse_move(self,pos,modifiers)
        if self.state==2 and self.transaction is not None:
            self.preview_angle(self.angle)

    def enterValue(self,value):
        if self.state!=2 or self.transaction is None:
            raise ValueError('请先确定旋转中心和起始方向')
        angle=float(str(value).strip().rstrip('°'))
        self.preview_angle(angle)
        self.commit();self.activate()
