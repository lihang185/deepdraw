"""Shared lifetime for human tools with live, undoable native previews."""
from engine import core
from engine.mutation_guard import check_mutation


class PreviewCanceled(Exception):
    pass


class TransactionTool(core.IBaseTool):
    @property
    def is_begin(self):
        return self.transaction is not None

    def __init__(self, view):
        super().__init__(view.view_proxy)
        self.view = view
        self.transaction = None
        self.transform_targets = None
        self.local_geometry = False

    def begin_transaction(self, label, transform_targets=None, local_geometry=False):
        check_mutation()
        edit = self.view.mainWindow.editing.edit
        if self.transaction is not None:
            raise RuntimeError('工具操作尚未结束')
        transaction = edit.operation(label, local_geometry=local_geometry)
        transaction.__enter__()
        self.transaction = transaction
        self.local_geometry = local_geometry
        self.transform_targets = tuple(transform_targets) if transform_targets is not None else None
        if self.transform_targets is None:
            edit.touch(self.view.mainWindow.editing.wrap(self.view.model.GetActiveComponent()))
        else:
            edit.touch_transform([self.view.mainWindow.editing.wrap(e) for e in self.transform_targets])

    def refresh(self):
        self._revision = self.view.mainWindow.editing.revision
        if self.transform_targets is None:
            if self.local_geometry:
                if self.transaction is not None:
                    from engine.viewer.render_changes import RenderChange
                    self.view.pipeline.apply_render_change(RenderChange(
                        components=(self.view.model.GetActiveComponent(),), local_geometry=True))
                self.view.MarkViewDirty()
            else:
                self.view.MarkDirty()
        elif self.transaction is not None:
            from engine.viewer.render_changes import RenderChange
            self.view.pipeline.apply_render_change(RenderChange(instances=self.transform_targets))
        self.view.update()

    def commit(self):
        check_mutation()
        transaction, self.transaction = self.transaction, None
        if transaction is not None:
            try:
                transaction.__exit__(None, None, None)
            finally:
                self.refresh()
                self.transform_targets = None
                self.local_geometry = False

    def cancel_preview(self):
        if self.transaction is not None:
            check_mutation()
            transaction, self.transaction = self.transaction, None
            try:
                transaction.__exit__(PreviewCanceled, PreviewCanceled('取消工具预览'), None)
            except PreviewCanceled:
                pass
            finally:
                self.refresh()
                self.transform_targets = None
                self.local_geometry = False

    def deactivate(self):
        self.cancel_preview()
        self.view.setMouseTracking(False)

    def on_cancel(self):
        self.activate()

    def on_left_button_up(self, pos):
        pass

    def draw(self, gl):
        pass

    def selected(self):
        component = self.view.model.GetActiveComponent()
        selected = list(self.view.model.GetSelection())
        if not selected or any(e.IsMarkedDeleted() or e.GetParentComponent() != component for e in selected):
            raise ValueError('请先选择当前编辑层的对象')
        return selected

    def point(self, pos, origin=None):
        from .drawing_support import infer
        return infer(self.view, self.input, pos, origin)



def copy_instance(model, source):
    instance = core.CEntityFactory(model).NewComponentInstance()
    if source.is_group:
        from types import SimpleNamespace
        from editing.grouping import clone_group_definition
        dd = SimpleNamespace(model=model, wrap=lambda entity: entity,
                             edit=SimpleNamespace(touch=lambda entity: None))
        instance.SetDefinition(clone_group_definition(dd, source.GetDefinition()))
    else:
        instance.SetDefinition(source.GetDefinition())
    instance.is_group = source.is_group
    instance.is_image = source.is_image
    instance.SetTransform(source.GetTransform())
    instance.SetMaterial(source.GetMaterial())
    instance.name = source.name
    model.GetActiveComponent().AddEntity(instance)
    return instance
