from engine.coordinates import world_length, local_distance, local_ray
from engine.viewer.overlays import draw_inference
"""Two-point move, adapted from editor_dist/tool_move.py."""
from engine import core
from .edit_tool_support import interactive
from .transaction_tool import TransactionTool
from .drawing_support import infer,draw_path,EXACT
from engine.qt import QtCore
from engine.units import snap_integer
from .move_snap import vertex_at
from engine.units import parse_length
import re


@interactive
class MoveTool(TransactionTool):
    @property
    def input_prompt(self):
        if self.transaction is None and getattr(self, 'last_copy', None) is not None:
            return 'x5连续复制或/5等分复制'
        return '输入距离(cm)'

    def activate(self):
        self.cancel_preview()
        self.last_copy = None
        self.input = core.CInputPointFinder(self.view.view_proxy)
        self.snap_picker = core.CPickHelper(self.view.view_proxy)
        self.hover_point = None
        self.excluded = set()
        self.start_point = self.end_point = None
        self.copy_mode = False
        self.targets = []
        self.faces = []
        self.section_axis = None
        self.locked_axis = None
        self.view.setMouseTracking(True)
        self.view.setStatusBar('移动：先选择对象，再点起点和终点；Ctrl 随时切换移动复制；←锁Y、→锁X、↑锁Z（再按解锁）；Enter 输入距离；Esc 取消')

    def begin_move(self, point):
        self.last_copy = None
        selected = self.selected()
        sections = [e for e in selected if isinstance(e,core.CSectionPlane)]
        if sections and len(selected)!=1:
            raise ValueError('请单独选择一个剖切面沿法向移动')
        if any(not isinstance(e, (core.CComponentInstance, core.CEdge, core.CFace, core.CSectionPlane)) for e in selected):
            raise ValueError('移动支持组件、边、面和剖切面')
        self.section_axis = sections[0].plane.GetNormal().Normalized() if sections else None
        if sections:
            self.copy_mode = False
        self.source_ids=[e.GetID() for e in selected]
        only_instances = all(isinstance(e, core.CComponentInstance) for e in selected)
        self.begin_transaction('复制移动' if self.copy_mode else '移动',
                               transform_targets=(() if self.copy_mode else selected) if only_instances else None,
                               local_geometry=all(not isinstance(e,core.CComponentInstance) for e in selected))
        if self.copy_mode:
            from editing.grouping import clone_entities
            selected,_=clone_entities(self.view.mainWindow.editing,selected,self.view.model.GetActiveComponent(),
                                      touch_target=not only_instances)
            self.view.model.SetSelection(selected)
            if only_instances:
                # Membership changes once; mouse movement changes only the
                # new instances' transforms. Never rebuild the tree per preview.
                self.transform_targets=tuple(selected)
                dd=self.view.mainWindow.editing
                dd.edit.touch_transform([dd.wrap(e) for e in selected])
                self.view.MarkDirty()
        vertices = {}
        self.targets = []
        for entity in selected:
            if isinstance(entity, core.CComponentInstance):
                self.targets.append((entity, entity.GetTransform()))
            elif isinstance(entity,core.CSectionPlane):
                self.targets.append((entity,entity.plane))
            else:
                points = entity.EnumVertices() if isinstance(entity, core.CFace) else (entity.GetStartVertex(), entity.GetEndVertex())
                for vertex in points:
                    vertices[vertex.GetID()] = vertex
        faces = {}
        for vertex in vertices.values():
            self.targets.append((vertex, vertex.Pos()))
            for loop in vertex.EnumLoops():
                face = loop.GetParentFace()
                faces[face.GetID()] = face
        self.faces = list(faces.values())
        self.excluded={e.GetID() for e in selected}
        self.excluded.update(faces)
        for vertex in vertices.values():
            self.excluded.update(e.GetID() for e in vertex.EnumEdges())
        self.start_point = self.end_point = point

    def preview_point(self, point):
        if self.transaction is None:
            return
        self.view.mainWindow.editing.edit.require_operation()
        delta = point - self.start_point
        axis = self.move_axis()
        if axis is not None:
            delta = axis*delta.Dot(axis)
        self.end_point = self.start_point+delta
        matrix = core.CMatrix()
        matrix.Translate(delta.x, delta.y, delta.z)
        for entity, initial in self.targets:
            if isinstance(entity, core.CComponentInstance):
                entity.SetTransform(matrix.Multiply(initial))
            elif isinstance(entity,core.CSectionPlane):
                entity.plane = core.CPlane.Load(initial.x,initial.y,initial.z,
                                                initial.w-initial.GetNormal().Dot(delta))
            else:
                entity.SetPosition(initial + delta)
        for face in self.faces:
            face.MarkDirty()
            face.UpdatePlane()
        self.refresh()
        self.view.setStatusBar('移动 %.3f cm；单击确认，Enter 输入距离，Esc 取消' % world_length(self.view,delta))

    def on_left_button_down(self, pos, mod):
        point = self.point(pos, self.start_point)
        if self.transaction is None:
            self.begin_move(point)
        else:
            self.preview_point(point)
            self.finish_move()

    def finish_move(self):
        record = None
        if self.copy_mode:
            record = (self.view.model.GetActiveComponent().GetID(), list(self.source_ids),
                      (self.end_point-self.start_point).ToTuple())
        self.commit()
        self.activate()
        if record is not None:
            self.last_copy = (self.view.mainWindow.editing.revision, record)
            self.view.setStatusBar('复制已完成；Enter 输入 x5 连续复制或 /5 等分复制；Esc 结束')

    def array_copy(self, mode, count):
        if self.transaction is not None or self.last_copy is None:
            raise ValueError('请先完成一次移动复制，再输入复制数量')
        dd = self.view.mainWindow.editing
        revision, (parent_id, source_ids, offset) = self.last_copy
        parent = self.view.model.GetActiveComponent()
        if revision != dd.revision or parent.GetID() != parent_id:
            self.last_copy = None
            raise ValueError('模型已改变，请重新完成移动复制')
        sources = [parent.GetEntityById(ident) for ident in source_ids]
        if any(e is None or e.IsMarkedDeleted() for e in sources):
            self.last_copy = None
            raise ValueError('原对象已失效，请重新完成移动复制')
        delta = core.CVector3D(*offset)
        if delta.Length() <= core.EPS:
            raise ValueError('复制间距不能为零')
        from editing.grouping import clone_entities
        if count > 1:
            with dd.edit.operation('连续复制' if mode == 'x' else '等分复制'):
                for i in range(1, count):
                    factor = i+1 if mode == 'x' else i/count
                    move = delta*factor
                    matrix = core.CMatrix();matrix.Translate(move.x,move.y,move.z)
                    clone_entities(dd, sources, parent, matrix)
        self.activate()
        self.view.setStatusBar('已完成 %d 个副本（不含原件）' % count)

    def move_axis(self):
        if self.section_axis is not None:return self.section_axis
        if self.locked_axis is None:return None
        return core.CVector3D(*{'X':(1,0,0),'Y':(0,1,0),'Z':(0,0,1)}[self.locked_axis])

    def on_axis_key(self,key):
        if self.section_axis is not None:
            self.view.setStatusBar('剖切面仅沿法向移动')
            return
        name={QtCore.Qt.Key_Left:'Y',QtCore.Qt.Key_Right:'X',QtCore.Qt.Key_Up:'Z'}[key]
        self.locked_axis=None if self.locked_axis==name else name
        if self.transaction is not None:
            self.preview_point(self.end_point)
            self.hover_point=self.end_point
        self.view.setStatusBar('锁定 %s 轴；再按同一方向键解锁'%name if self.locked_axis else '已解除轴锁定')
        self.view.update()

    def point(self,pos,origin=None):
        if self.transaction is not None and self.move_axis() is not None:
            ray = local_ray(self.view,pos.x(),pos.y())
            direction = ray.dir.Normalized()
            axis = self.move_axis()
            if self.section_axis is None:
                entity_filter=core.EntityFilter(lambda e:e.GetID() not in self.excluded)
                vertex=vertex_at(self.view,self.snap_picker,pos,self.excluded,entity_filter)
                exact=vertex
                if exact is None:
                    try:
                        inferred=infer(self.view,self.input,pos,origin,entity_filter=entity_filter)
                        if self.input.snap_type in EXACT:exact=inferred
                    except ValueError:pass
                if exact is not None:
                    self.hover_point=self.start_point+axis*(exact-self.start_point).Dot(axis)
                    return self.hover_point
            b = axis.Dot(direction)
            denominator = 1-b*b
            if denominator < 1e-5:
                self.view.setStatusBar('锁定方向接近视线方向，请调整视角或 Enter 输入距离')
                return self.end_point
            w = ray.PointAt(0)-self.start_point
            distance = (axis.Dot(w)-b*direction.Dot(w))/denominator
            if self.section_axis is None:distance=snap_integer(distance)
            self.hover_point = self.start_point+axis*distance
            return self.hover_point
        entity_filter=core.EntityFilter(lambda e:e.GetID() not in self.excluded)
        # Keep the native inference state/axis helpers, but prefer a concrete vertex.
        vertex=vertex_at(self.view,self.snap_picker,pos,self.excluded,entity_filter)
        try:
            point=infer(self.view,self.input,pos,origin,entity_filter=entity_filter)
        except ValueError:
            if vertex is None:raise
            point=vertex
        self.hover_point=vertex if vertex is not None else point
        return self.hover_point

    def on_mouse_move(self, pos, modifiers):
        point=self.point(pos,self.start_point)
        if self.transaction is not None:self.preview_point(point)

    def on_ctrl_press(self):
        if any(isinstance(e,core.CSectionPlane) for e in self.view.model.GetSelection()):
            self.view.setStatusBar('剖切面仅沿法向移动，不进行移动复制')
            return
        mode=not self.copy_mode
        if self.transaction is not None:
            # Restart only this uncommitted preview: restores the source before
            # making a copy, and keeps the same start/end and one final undo step.
            start,end=self.start_point,self.end_point
            ids=list(self.source_ids)
            self.cancel_preview()
            parent=self.view.model.GetActiveComponent()
            self.view.model.SetSelection([parent.GetEntityById(ident) for ident in ids])
            self.copy_mode=mode
            self.begin_move(start);self.preview_point(end)
        else:self.copy_mode=mode
        self.view.setStatusBar('移动复制' if self.copy_mode else '普通移动')

    def enterValue(self, value):
        if isinstance(value, str):
            text = value.strip().lower()
            if text.startswith(('x','/')):
                if not re.fullmatch(r'[x/]\s*[1-9][0-9]*', text):
                    self.view.setStatusBar('复制数量须为正整数，例如 x5 或 /5')
                    return
                self.array_copy(text[0], int(text[1:].strip()))
                return
            value = parse_length(text, getattr(self.view,'display_unit','cm'))
        if self.transaction is None:
            raise ValueError('复制确认后请输入 x数量 或 /数量；距离输入需先开始移动')
        delta = self.end_point - self.start_point
        if delta.Length() <= core.EPS:
            if self.move_axis() is None:
                raise ValueError('请先移动鼠标确定方向')
            delta = self.move_axis()
        self.preview_point(self.start_point + delta.Normalized() * local_distance(self.view,delta,value))
        self.finish_move()

    def draw(self, gl):
        draw_inference(self.view, self.input, gl)
        if self.hover_point is not None:
            core.draw_target_with_size(self.hover_point,self.view.camera_zoom*.01,gl)
        if self.transaction is not None:
            draw_path(gl,[self.start_point,self.end_point],color={'X':(1.,0.,0.),'Y':(0.,.7,0.),'Z':(0.,.35,1.)}.get(self.locked_axis,(1.,0.,0.)))
            core.draw_target_with_size(self.start_point, self.view.camera_zoom * .01, gl)
            core.draw_target_with_size(self.end_point, self.view.camera_zoom * .01, gl)
