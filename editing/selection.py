"""Human selection with model and revision checks."""
from engine import core
from .objects import Selection


class SelectionTools:
    def __init__(self, session):
        self.s = session

    def current(self):
        self.s.check()
        comp = self.s.model.GetActiveComponent()
        entities = [e for e in self.s.model.GetSelection() if not e.IsMarkedDeleted()]
        if any(e.GetParentComponent() != comp for e in entities):
            raise ValueError('Selection is outside the active container; select its instance instead')
        return Selection(self.s, entities, self.s.wrap(comp))

    def set(self, target):
        self.s.check()
        entities = self.s.unwrap(target)
        comp = self.s.model.GetActiveComponent()
        if any(not isinstance(e,core.CDrawingElement) or e.GetParentComponent()!=comp for e in entities):
            raise ValueError('Select drawing elements in the active container')
        self.s.model.SetSelection(entities)
        self.s.widget.MarkViewDirty()
        self.s.widget.update()
        return self.current()

    def clear(self):
        self.s.check()
        self.s.model.ClearSelection()
        self.s.widget.MarkViewDirty()
        self.s.widget.update()

    def _path(self):
        path = self.s.model.GetActiveComponentPath()
        return [path.Get(i).GetID() for i in range(path.Length())]


