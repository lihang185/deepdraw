import time
from engine import core
from engine.qt import QtCore, QtGui, QtWidgets
from engine.mutation_guard import human_callback, check_mutation

class SelectTool(core.IBaseTool):
    @property
    def is_begin(self):
        return False

    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view
        self.activate()
    
    def activate(self):
        self.pick_helper = core.CPickHelper(self.view.view_proxy)
        self.start = None
        self.end = None
        self._double_click = None
    
    def draw(self, gl):
        pass

    def on_cancel(self):
        check_mutation()
        self.start=self.end=None
        self._double_click=None
        self.view.model.ClearSelection()
        self.view.MarkViewDirty()
        self.view.update()
        
    def draw_2d(self, painter):
        if self.start is not None and self.end is not None and (self.end-self.start).manhattanLength()>4:
            rect=QtCore.QRect(self.start,self.end).normalized()
            cross=self.end.x()<self.start.x()
            painter.save()
            pen=QtGui.QPen(QtGui.QColor(30,160,100) if cross else QtGui.QColor(40,110,220))
            if cross:pen.setStyle(QtCore.Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect)
            painter.restore()

    def on_left_button_down(self, pos, mod):
        check_mutation()
        pending=self._double_click
        self._double_click=None
        if pending is not None:
            when,where,entity,component,revision=pending
            if (time.monotonic()-when<=QtWidgets.QApplication.doubleClickInterval()/1000
                    and (pos-where).manhattanLength()<=QtWidgets.QApplication.startDragDistance()
                    and component==self.view.model.GetActiveComponent()
                    and revision==self.view.mainWindow.editing.revision
                    and not entity.IsMarkedDeleted()):
                self.start=self.end=None
                self.select_connected(entity,include_faces=True)
                return
        self.start=QtCore.QPoint(pos)
        self.end=QtCore.QPoint(pos)
        self.additive=bool(mod & (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier))

    
    def on_left_button_up(self, pos):
        check_mutation()
        if self.start is None:return
        self.end=QtCore.QPoint(pos)
        model=self.view.model
        comp=model.GetActiveComponent()
        picker=self.pick_helper
        picker.Reset()
        if (self.end-self.start).manhattanLength()>4:
            x0,x1=sorted((self.start.x(),self.end.x()))
            y0,y1=sorted((self.start.y(),self.end.y()))
            if x0==x1 or y0==y1:
                self.start=self.end=None
                return
            mode=1 if self.end.x()<self.start.x() else 2
            picker.MultiSelect(round((x0+x1)/2),round((y0+y1)/2),x1-x0,y1-y0,mode)
            selected=list(picker.GetSelected())
        else:
            picker.SinglePick(pos.x(),pos.y(),9,None, True)
            best=picker.BestPick()
            selected=[]
            if best is not None and best.e is not None:
                # Promote a face hit to its instance in the active editing context.
                for entity in list(best.inst_path)+[best.e]:
                    if isinstance(entity,core.CDrawingElement) and entity.GetParentComponent()==comp:
                        selected=[entity]
                        break
            from .tool_section import pick_section_frame
            section = pick_section_frame(self.view,pos)
            if section is not None:
                selected=[section]
        selected=[e for e in selected if not e.IsMarkedDeleted() and e.GetParentComponent()==comp]
        if not getattr(self.view,'show_section_planes',True):
            selected=[e for e in selected if not isinstance(e,core.CSectionPlane)]
        # Treat a Curve as one selection unit, including when a box hits only
        # some of its segments. Never reach outside the active editing context.
        units={};surface_units={};curve_members=None
        for entity in selected:
            if isinstance(entity,core.CFace):
                key=surface_units.get(entity.GetID())
                if key is None:
                    members=self.soft_faces(entity,comp)
                    key=('surface',min(members))
                    units[key]=members
                    surface_units.update((ident,key) for ident in members)
                continue
            curve=entity.GetCurve() if isinstance(entity,core.CEdge) else None
            key=('curve',curve.GetID()) if curve is not None else ('entity',entity.GetID())
            if curve is not None:
                if curve_members is None:
                    # Use component-owned live edges, not the Curve's linked
                    # edge list: stale native members must never reach selection.
                    curve_members={}
                    for edge in comp.EnumEntities():
                        if (edge is None or edge.IsMarkedDeleted()
                                or not isinstance(edge,core.CEdge) or edge.GetParentComponent()!=comp):
                            continue
                        owner=edge.GetCurve()
                        if owner is not None:
                            curve_members.setdefault(owner.GetID(),[]).append(edge)
                members=curve_members.get(curve.GetID(),[entity])
            else:
                members=[entity]
            units[key]={e.GetID():e for e in members
                        if not e.IsMarkedDeleted() and e.GetParentComponent()==comp}
        if self.additive:
            previous={e.GetID():e for e in model.GetSelection() if not e.IsMarkedDeleted()}
            for members in units.values():
                if all(ident in previous for ident in members):
                    for ident in members:previous.pop(ident,None)
                else:previous.update(members)
            selected=list(previous.values())
        else:
            selected=list({ident:e for members in units.values() for ident,e in members.items()}.values())
        from .tool_section import component_section_bounds
        updates=[]
        for entity in selected:
            if isinstance(entity,core.CSectionPlane):
                bounds=component_section_bounds(comp,entity.plane)
                previous=entity.bounds
                if any(abs(getattr(bounds,k)-getattr(previous,k))>1e-8
                       for k in ('min_x','max_x','min_y','max_y')):
                    updates.append((entity,bounds))
        if updates:
            session=self.view.mainWindow.editing
            with session.edit.operation('刷新剖切面范围'):
                for entity,bounds in updates:entity.bounds=bounds
                session.edit.touch(session.wrap(comp))
        model.SetSelection(selected)
        self.start=self.end=None
        self.view.MarkViewDirty()
        self.view.update()
        self.view.setStatusBar('已选择 %d 个对象'%len(selected))

    def on_mouse_move(self, pos, modifiers):
        if self.start is not None:
            self.end=QtCore.QPoint(pos)

    def soft_faces(self, face, component):
        """Select a surface across Soft edges, stopping at hard/context boundaries."""
        found={};pending=[face]
        while pending:
            current=pending.pop()
            if (current is None or current.IsMarkedDeleted()
                    or current.GetParentComponent()!=component or current.GetID() in found):
                continue
            found[current.GetID()]=current
            for edge in current.EnumEdges():
                if not edge.IsMarkedDeleted() and edge.IsSoft():
                    pending.extend(use.GetParentFace() for use in edge.EnumEdgeUse())
        return found

    def select_connected(self,target,include_faces=False):
        component=self.view.model.GetActiveComponent()
        found={};pending=[target]
        while pending:
            entity=pending.pop()
            if entity.GetID() in found or entity.IsMarkedDeleted() or entity.GetParentComponent()!=component:continue
            found[entity.GetID()]=entity
            if isinstance(entity,core.CEdge):
                for vertex in (entity.GetStartVertex(),entity.GetEndVertex()):
                    pending.extend(vertex.EnumEdges())
                if include_faces:pending.extend(u.GetParentFace() for u in entity.EnumEdgeUse())
            elif isinstance(entity,core.CFace):
                pending.extend(u.GetEdge() for u in entity.EnumEdgeUse())
        selection=[e for e in found.values() if not e.IsHide()]
        self.view.model.SetSelection(selection)
        self.view.MarkViewDirty();self.view.update()
        self.view.setStatusBar('已选择相连几何 %d 个对象'%len(selection))

    @human_callback
    def on_left_button_double_click(self, pos, modifiers):
        # Qt sends a release after the double click. Do not select again in the
        # newly opened component when that release arrives.
        self.start = self.end = None
        host = self.view.mainWindow
        session = getattr(host, 'editing', None)
        if (getattr(host, 'input_busy', False)
                or (session is not None and session.edit.active is not None)):
            self.view.setStatusBar('请等待当前建模操作完成后再进入或退出组件')
            return
        check_mutation()
        model = self.view.model
        comp = model.GetActiveComponent()
        from .tool_section import pick_section_frame
        section = pick_section_frame(self.view,pos)
        if section is not None:
            if not section.is_active:
                limit = getattr(self.view.pipeline,'section_limit',6)
                count = sum(isinstance(e,core.CSectionPlane) and not e.IsMarkedDeleted()
                            and not e.IsHide() and e.is_active for e in comp.EnumEntities())
                if count >= limit:
                    self.view.setStatusBar('已达到当前显卡支持的剖切面数量，请先停用其他剖切面')
                    return
            with session.edit.operation('切换剖切面激活状态'):
                section.is_active = not section.is_active
                from .tool_section import component_section_bounds
                section.bounds = component_section_bounds(comp,section.plane)
                session.edit.touch(session.wrap(comp))
            model.SetSelection([section])
            self.view.MarkViewDirty();self.view.update()
            self.view.setStatusBar('剖切面已激活' if section.is_active else '剖切面已停用')
            return
        picker = self.pick_helper
        picker.Reset()
        picker.SinglePick(pos.x(), pos.y(), 9, None, True)
        hit = picker.BestPick()
        if hit is not None and hit.e is not None:
            target = next((entity for entity in list(hit.inst_path) + [hit.e]
                           if isinstance(entity, core.CDrawingElement)
                           and not entity.IsMarkedDeleted()
                           and entity.GetParentComponent() == comp), None)
            if isinstance(target,(core.CEdge,core.CFace)):
                if isinstance(target,core.CFace):
                    selected={target.GetID():target}
                    selected.update((u.GetEdge().GetID(),u.GetEdge()) for u in target.EnumEdgeUse())
                    model.SetSelection(list(selected.values()))
                    self.view.MarkViewDirty();self.view.update()
                else:self.select_connected(target)
                self._double_click=(time.monotonic(),QtCore.QPoint(pos),target,comp,session.revision)
                return
            self._double_click=None
            if not isinstance(target, core.CComponentInstance):
                return
            # Navigation changes the active editing context, not model geometry.
            model.OpenComponent(target)
            message = '已进入组件：' + target.name
        else:
            if model.GetActivePathLength() == 0:
                return
            target = model.GetActiveComponentInstance()
            host.editing.edit.flush_deferred_bounds()
            model.CloseComponent()
            message = '已返回上一层组件'
        model.ClearSelection()
        self.view.pipeline.mark_outer_path_dirty()
        self.view.MarkViewDirty()
        self.view.update()
        self.view.setStatusBar(message + ' · 双击组件进入 · 双击空白返回上一层')


