from engine import core


class Selection:
    def __init__(self, session, entities, container=None):
        self.session, self.entities, self.container = session, tuple(entities), container
        self.history_epoch = getattr(session, 'history_epoch', 0)

    def __iter__(self):
        self.session.check()
        if self.history_epoch != getattr(self.session, 'history_epoch', 0):
            raise ValueError('Selection predates undo/redo/abort; query it again')
        return (self.session.wrap(e) for e in self.entities)

    def __len__(self):
        self.session.check()
        if self.history_epoch != getattr(self.session, 'history_epoch', 0):
            raise ValueError('Selection predates undo/redo/abort; query it again')
        return len(self.entities)

    def one(self):
        if len(self) != 1:
            raise ValueError('Expected exactly one member, got %d' % len(self))
        return self.session.wrap(self.entities[0])

    def ids(self):
        self.session.check()
        len(self)
        return [e.GetID() for e in self.entities]


class Entity:
    def __init__(self, session, native):
        self.session, self._native = session, native
        self.history_epoch = getattr(session, 'history_epoch', 0)

    @property
    def native(self):
        self.session.check()
        if self.history_epoch != getattr(self.session, 'history_epoch', 0):
            raise ValueError('Object predates undo/redo/abort; query it again')
        if self._native.IsMarkedDeleted():
            raise ValueError('Entity has been erased')
        return self._native

    @property
    def id(self):
        return self.native.GetID()

    @property
    def definition(self):
        if not isinstance(self.native, core.CComponentInstance):
            raise TypeError('Only instances have definitions')
        return Container(self.session, self.native.GetDefinition())


class Container(Entity):
    def named(self, name):
        if name not in self.names():
            raise KeyError('No named set: ' + name)
        return Selection(self.session, self.session.metadata.members(self.native, name), self)

    def names(self):
        return list(self.native.GetNamedSetNames())

    def children(self):
        return Selection(self.session, list(self.native.EnumEntities()), self)

    @property
    def description(self):
        return self.native.description




class Scene:
    def __init__(self, session):
        self.session = session

    @property
    def root(self):
        self.session.check()
        return Container(self.session, self.session.model.GetTopComponent())

    def named(self, name):
        return self.root.named(name)

    def definition_users(self, definition):
        comp = self.session.single(definition)
        containers = [self.session.model.GetTopComponent()] + list(self.session.model.GetDefinitionList())
        return Selection(self.session, [e for c in containers if not c.IsMarkedDeleted() for e in c.EnumEntities()
                         if isinstance(e,core.CComponentInstance) and e.GetDefinition()==comp])


    def name(self, name, members, container=None):
        self.session.edit.require_operation()
        container = container or self.root
        entities = self.session.unwrap(members)
        # Internal entities (vertices, edge uses, loops) require the collector.
        native = container.native
        collector = core.CEntityCollector(native)
        for e in entities:
            found = native.GetEntityById(e.GetID()) if isinstance(e, core.CDrawingElement) else collector.FindEntityByID(e.GetID())
            if found != e:
                raise ValueError('Named member is not indexed in the target container')
        self.session.metadata.assign(native, name, entities)
        self.session.edit.touch(container)
        return container.named(name)

    def describe(self, target, text):
        self.session.edit.require_operation()
        native = self.session.single(target)
        self.session.edit.touch(target)
        if isinstance(native, core.CComponentDefinition):
            native.description = str(text)
        else:
            raise TypeError('Descriptions belong to the model or component definition')


