"""Human editing transactions and stale-preview protection for HMI tools."""
from functools import wraps
from engine.mutation_guard import human_callback, check_mutation


def operation(label, local_geometry=False, material_only=False):
    def decorate(fn):
        @wraps(fn)
        def run(self, *args, **kwargs):
            check_mutation()
            edit = self.view.mainWindow.editing.edit
            with edit.operation(label, local_geometry=local_geometry, material_only=material_only):
                edit.touch(self.view.mainWindow.editing.wrap(self.view.model.GetActiveComponent()))
                result = fn(self, *args, **kwargs)
            self._revision = self.view.mainWindow.editing.revision
            self.view.MarkViewDirty()
            self.view.update()
            return result
        return run
    return decorate


def interactive(cls):
    cls.wants_hover = True
    activate = cls.activate
    def start(self):
        activate(self)
        self._revision = self.view.mainWindow.editing.revision
    cls.activate = start
    original_draw = cls.draw
    def draw(self, gl):
        if self._revision != self.view.mainWindow.editing.revision:
            self.activate()
            return
        original_draw(self, gl)
    cls.draw = draw
    if not hasattr(cls, 'on_cancel') or 'on_cancel' not in cls.__dict__:
        cls.on_cancel = start
    def wrap(fn):
        @human_callback
        @wraps(fn)
        def call(self, *args):
            try:
                check_mutation()
                if self.view.mainWindow.input_busy:
                    return
                if self._revision != self.view.mainWindow.editing.revision:
                    self.activate()
                    self.view.setStatusBar('模型已改变，请重新选取起点')
                    return
                return fn(self, *args)
            except Exception as exc:
                self.activate()
                self.view.setStatusBar(str(exc) or '无法确定输入点，请重新选取')
        return call
    for name in ('on_left_button_down', 'on_left_button_up', 'on_mouse_move', 'on_cancel', 'on_ctrl_press', 'on_axis_key', 'enterValue'):
        if hasattr(cls, name):
            setattr(cls, name, wrap(getattr(cls, name)))
    return cls
