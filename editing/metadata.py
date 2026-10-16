"""Session-local named membership by ID, independent of geometry undo history."""
from engine import core
from engine.entity_refs import named_members


class NamedSets:
    def __init__(self, model):
        self.model = model
        self.sets = {}
        for comp in self.containers():
            self.sets[comp.GetID()] = {
                name: [e.GetID() for e in named_members(comp, name)]
                for name in comp.GetNamedSetNames()}

    def containers(self):
        return [c for c in [self.model.GetTopComponent()] + list(self.model.GetDefinitionList())
                if c is not None and not c.IsMarkedDeleted()]

    def assign(self, comp, name, entities):
        self.sets.setdefault(comp.GetID(), {})[name] = [e.GetID() for e in entities]
        # Clear native references now: a subsequent geometry edit may delete them.
        comp.SetNamedSet(name, [])

    def members(self, comp, name):
        ids = self.sets.get(comp.GetID(), {}).get(name)
        if ids is None:
            # Read only previously unknown native metadata while still valid.
            entities = named_members(comp, name)
            ids = [e.GetID() for e in entities]
            self.sets.setdefault(comp.GetID(), {})[name] = ids
        collector = core.CEntityCollector(comp)
        result = []
        for ident in ids:
            entity = comp.GetEntityById(ident)
            if entity is None:
                entity = collector.FindEntityByID(ident)
            if entity is not None and not entity.IsMarkedDeleted():
                result.append(entity)
        return result

    def detach(self):
        for comp in self.containers():
            for name in comp.GetNamedSetNames():
                if name not in self.sets.get(comp.GetID(), {}):
                    self.members(comp, name)
                comp.SetNamedSet(name, [])

    def restore(self):
        for comp in self.containers():
            for name in self.sets.get(comp.GetID(), {}):
                comp.SetNamedSet(name, self.members(comp, name))
