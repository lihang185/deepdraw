import math
import time
from contextlib import contextmanager
from engine import core
from engine.push_pull import PushPullController
from engine.mutation_guard import check_mutation


def vector(value):
    values = tuple(float(v) for v in value)
    if len(values) != 3 or not all(math.isfinite(v) for v in values):
        raise ValueError('Expected three finite coordinates')
    return core.CVector3D(*values)


class Edit:
    def group(self, target=None, name='Group'):
        from .grouping import group
        return group(self.s, target, name)

    def explode(self, target=None):
        from .grouping import explode
        return explode(self.s, target)





    def _report(self, change):
        if self.report is not None:
            self.report.setdefault('changes', []).append(change)
        return change

    def __init__(self, session):
        self.s, self.active = session, None
        self.report = None
        self._transformed = {}
        self._transform_parents = {}
        self._deferred_bounds = {}

    def require_operation(self):
        check_mutation()
        self.s.check()
        if self.active is None:
            raise RuntimeError('Use with deepdraw.edit.operation(label): for mutations')

    @contextmanager
    def operation(self, label, validate=True, local_geometry=False, material_only=False):
        check_mutation()
        self.s.check()
        if self.active is not None:
            raise RuntimeError('Nested operations are not supported')
        start = time.perf_counter()
        result = {'label': label, 'status': 'running', 'rollback': 'not_attempted'}
        affected = {}
        self.s.metadata.detach()
        self.active = affected
        self._transformed = {}
        self._transform_parents = {}
        self.report = result
        self.rollback_actions = []
        undo = self.s.model.UndoManager()
        try:
            undo.StartOperation(label)
        except BaseException:
            self.active = None
            self.report = None
            self.s.metadata.restore()
            raise
        try:
            yield result
            self._refresh(affected, instances=tuple(self._transformed.values()), local_geometry=local_geometry, material_only=material_only)
            if validate:
                result['validation'] = self.s.diagnostics.validate()
                if result['validation']['status'] != 'valid':
                    raise RuntimeError('Model validity failed; inspect result and stop editing')
            else:
                result['validation'] = {'status': 'not_run'}
                from engine.entity_refs import sanitize_model_references
                result['reference_cleanup'] = sanitize_model_references(self.s.model)
            undo.CommitOperation()
            result['status'] = 'completed'
        except BaseException as error:
            result.update(status='failed', error=str(error), model_may_have_changed=True)
            self.s.model.ClearSelection()
            self.s.history_epoch += 1
            try:
                undo.AbortOperation()
                result['rollback'] = 'completed'
                self._refresh_all()
                result['rollback_validation'] = self.s.diagnostics.validate()
                if result['rollback_validation']['status'] != 'valid':
                    result['rollback'] = 'validation_failed'
            except Exception as rollback_error:
                result.update(rollback='failed', rollback_error=str(rollback_error))
            for restore in reversed(self.rollback_actions):
                restore()
            raise
        finally:
            try:
                self.s.metadata.restore()
            except Exception as metadata_error:
                result.update(status='failed', metadata_error=str(metadata_error))
            self.s.revision += 1
            affected_ids = set(affected)
            affected_ids.update(self._transform_parents)
            result.update(revision=self.s.revision, affected_component_ids=sorted(affected_ids),
                          elapsed_ms=round((time.perf_counter()-start)*1000, 2))
            self.s.results.append(result)
            self.active = None
            self.report = None
            self.rollback_actions = []
            self._transformed = {}
            self._transform_parents = {}

        checkpoint = getattr(self.s, 'ui_checkpoint', None)
        if checkpoint is not None:
            checkpoint()

    def _refresh_all(self):
        components = [self.s.model.GetTopComponent()] + list(self.s.model.GetDefinitionList())
        self._refresh({c.GetID(): c for c in components if not c.IsMarkedDeleted()}, strict=False)

    def _history(self, method):
        check_mutation()
        self.s.check()
        if self.active is not None:
            raise RuntimeError('Undo/redo must run outside an operation')
        self.s.widget.mainWindow.clear_materials()
        self.s.metadata.detach()
        self.s.model.ClearSelection()
        try:
            getattr(self.s.model.UndoManager(), method)()
        finally:
            self.s.history_epoch += 1
            self.s.revision += 1
            self.s.metadata.restore()
        self._refresh_all()
        result = {'operation': method.lower(), 'validation': self.s.diagnostics.validate(),
                  'revision': self.s.revision}
        self.s.results.append(result)
        return result

    def undo(self):
        return self._history('Undo')

    def redo(self):
        return self._history('Redo')

    def touch(self, target):
        self.require_operation()
        for e in self.s.unwrap(target):
            from .reference import locked
            if locked(e):
                raise ValueError('Image reference is locked; use deepdraw.reference.calibrate')
            comp = e if isinstance(e, core.CComponent) else e.GetParentComponent()
            if comp is None:
                raise ValueError('Pass the owning container for internal entities')
            self.active[comp.GetID()] = comp

    def touch_transform(self, target):
        """Declare only instance placement changed; use touch for any other edits."""
        self.require_operation()
        entities = self.s.unwrap(target)
        from .reference import locked
        for entity in entities:
            if not isinstance(entity, core.CComponentInstance):
                raise TypeError('touch_transform expects component instances')
            if entity.IsMarkedDeleted() or entity.GetParentComponent() is None:
                raise ValueError('Transform requires a live instance in a container')
            if locked(entity):
                raise ValueError('Image reference is locked; use deepdraw.reference.calibrate')
        for entity in entities:
            self._transformed[entity.GetID()] = entity
            parent = entity.GetParentComponent()
            self._transform_parents[parent.GetID()] = parent

    def set_transform(self, target, matrix):
        """Set one instance's absolute parent-space transform, including reflection."""
        self.require_operation()
        entity = self.s.single(target)
        self.touch_transform(self.s.wrap(entity))
        entity.SetTransform(matrix)

    def _refresh(self, affected, strict=True, instances=(), local_geometry=False, material_only=False):
        affected = {ident: comp for ident, comp in affected.items() if not comp.IsMarkedDeleted()}
        instances = tuple(e for e in instances if not e.IsMarkedDeleted())
        bounds_affected = dict(affected)
        for entity in instances:
            parent = entity.GetParentComponent()
            if parent is not None:
                bounds_affected[parent.GetID()] = parent
        for comp in (() if material_only else affected.values()):
            for e in comp.EnumEntities():
                if isinstance(e, core.CFace):
                    # Loaded decorative meshes may contain tiny faces whose
                    # saved plane is valid but cannot be recomputed. History
                    # restores stored geometry; keep that plane and still run
                    # the full native validity check afterwards.
                    if not e.UpdatePlane() and strict:
                        raise RuntimeError('Could not update plane for face %s' % e.GetID())
                    # Vertex changes invalidate both the face bbox and triangle
                    # mesh. Updating its plane alone does not invalidate them.
                    e.MarkDirty()
        # ComputeBoundingBox includes child instances via definition.GetBoundingBox(),
        # which can return a ready but stale component bbox. Recompute affected
        # definitions before their ancestors, after all face caches are invalidated.
        refreshed = {}
        def refresh_bounds(comp):
            ident = comp.GetID()
            if ident in refreshed:
                return refreshed[ident]
            refreshed[ident] = False
            changed = ident in bounds_affected
            for entity in comp.EnumChildren():
                if not entity.IsMarkedDeleted():
                    child = entity.GetDefinition()
                    if not child.IsMarkedDeleted():
                        changed = refresh_bounds(child) or changed
            if changed:
                comp.ComputeBoundingBox()
            refreshed[ident] = changed
            return changed
        if material_only:
            pass  # Material assignment changes neither planes nor bounds.
        elif local_geometry:
            for comp in bounds_affected.values():
                comp.MarkBoundingBoxDirty()
                if isinstance(comp, core.CComponentDefinition):
                    self._deferred_bounds[comp.GetID()] = comp
        elif getattr(self.s.widget, 'incremental_edit_bounds', True):
            self._refresh_affected_bounds(bounds_affected.values())
        else:
            refresh_bounds(self.s.model.GetTopComponent())
            for comp in bounds_affected.values():
                refresh_bounds(comp)
        # Publish only after every dependent bound is ready, once per edit.
        from engine.viewer.render_changes import RenderChange
        self.s.widget.pipeline.apply_render_change(RenderChange(
            components=tuple(affected.values()), instances=instances, local_geometry=local_geometry,
            material_only=material_only))
        if not affected and not instances:
            self.s.widget.pipeline.mark_outer_path_dirty()
            self.s.diagnostics.invalidate()
        self.s.widget.update()



    def _refresh_affected_bounds(self, components):
        """Use live instance back-references, including hidden/unrendered parents.

        Record only dependency edges on changed branches; do not enumerate the
        children of an otherwise unaffected assembly merely to find ancestors.
        """
        affected = {}
        children = {}
        pending = list(components)
        while pending:
            comp = pending.pop()
            if comp.IsMarkedDeleted() or comp.GetID() in affected:
                continue
            ident = comp.GetID()
            affected[ident] = comp
            if not isinstance(comp, core.CComponentDefinition):
                continue
            for inst in comp.GetInstances():
                if inst.IsMarkedDeleted():
                    continue
                parent = inst.GetParentComponent()
                if parent is None or parent.IsMarkedDeleted():
                    continue
                children.setdefault(parent.GetID(), set()).add(ident)
                pending.append(parent)
        done = set()
        def refresh(ident):
            if ident in done:
                return
            done.add(ident)
            for child in children.get(ident, ()):
                refresh(child)
            affected[ident].ComputeBoundingBox()
        for ident in affected:
            refresh(ident)

    def resolve_topology(self, target, container=None):
        self.require_operation()
        container = container or self.s.scene.root
        comp = self.s.single(container)
        entities = self.s.unwrap(target)
        if any(comp.GetEntityById(e.GetID()) != e for e in entities):
            raise ValueError('Merge inputs must belong to the supplied container')
        self.touch(container)
        return self.s.diagnostics.resolve_topology(entities, comp)

    def extrude(self, face, delta):
        self.require_operation()
        face = self.s.single(face)
        if not isinstance(face, core.CFace):
            raise TypeError('extrude expects a face')
        if face.GetParentComponent() != self.s.model.GetActiveComponent():
            raise ValueError('Enter the component with deepdraw.edit.enter(instance) before extruding')
        if len(self.s.scene.definition_users(self.s.wrap(face.GetParentComponent())))>1:
            raise ValueError('Extruding shared definitions is not supported by this entry point')
        d = vector(delta)
        self.touch(self.s.wrap(face))
        controller = PushPullController()
        controller.begin(face, self.s.model)
        controller.push(d)
        controller.finish()

    @contextmanager
    def enter(self, instance):
        self.require_operation()
        native = self.s.single(instance)
        if not isinstance(native, core.CComponentInstance):
            raise TypeError('Expected component instance')
        self.s.model.OpenComponent(native)
        try:
            yield self.s.wrap(native.GetDefinition())
        finally:
            self.flush_deferred_bounds()
            self.s.model.CloseComponent()

    def flush_deferred_bounds(self):
        """Publish containing bounds when leaving component editing."""
        check_mutation()
        affected={}
        instances=set()
        def collect(comp):
            if comp.IsMarkedDeleted() or comp.GetID() in affected:return
            affected[comp.GetID()]=comp
            if isinstance(comp,core.CComponentDefinition):
                for inst in comp.GetInstances():
                    if inst.IsMarkedDeleted():continue
                    instances.add(inst)
                    parent=inst.GetParentComponent()
                    if parent is not None:collect(parent)
        for comp in self._deferred_bounds.values():collect(comp)
        done=set()
        def refresh(comp):
            if comp.GetID() in done:return
            done.add(comp.GetID())
            for inst in comp.EnumChildren():
                child=inst.GetDefinition()
                if child.GetID() in affected:refresh(child)
            comp.MarkBoundingBoxDirty()
        for comp in affected.values():refresh(comp)
        self._deferred_bounds.clear()
        if instances:
            from engine.viewer.render_changes import RenderChange
            self.s.widget.pipeline.apply_render_change(RenderChange(instances=tuple(instances)))

