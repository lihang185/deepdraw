from engine import core
from .objects import Selection
from .edit import vector


class Build:
    def __init__(self, session):
        self.s = session

    def component(self, name, description='', parent=None):
        self.s.edit.require_operation()
        parent = parent or self.s.scene.root
        if name in parent.names() and len(parent.named(name)):
            raise ValueError('Name already exists: ' + name)
        factory = core.CEntityFactory(self.s.model)
        definition = factory.NewComponentDefinition()
        definition.name, definition.description = name, description
        self.s.model.addDefinition(definition)
        inst = factory.NewComponentInstance()
        inst.name = name
        inst.SetDefinition(definition)
        parent.native.AddEntity(inst)
        self.s.edit.touch(parent)
        wrapped = self.s.wrap(inst)
        self.s.scene.name(name, wrapped, parent)
        return wrapped

    def polyline(self, points, target=None, closed=False):
        self.s.edit.require_operation()
        target = target or self.s.scene.root
        points = [vector(p) for p in points]
        if len(points) < (3 if closed else 2):
            raise ValueError('Not enough points')
        pairs = list(zip(points, points[1:]))
        if closed:
            pairs.append((points[-1], points[0]))
        if any((a-b).Length() < 0.001 for a,b in pairs):
            raise ValueError('Degenerate segment below engine tolerance')
        self.s.edit.touch(target)
        edges = [target.native.AddLine(a,b) for a,b in pairs]
        return Selection(self.s, edges, target)

    def line(self, start, end, target=None):
        return self.polyline([start,end],target=target).one()



