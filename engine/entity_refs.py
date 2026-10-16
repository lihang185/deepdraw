"""Read-only filters for metadata containers that do not participate in Undo."""


def live_entities(entities):
    # Check deletion before any derived-type access, serialization or ID lookup.
    return [entity for entity in entities if entity is not None and not entity.IsMarkedDeleted()]


def named_members(component, name):
    return live_entities(component.GetNamedSet(name))


def sanitize_model_references(model):
    """Remove deleted/null references before native selection/metadata consumers.

    Never inspect IDs or derived geometry on deleted entities. Preserve live
    selection order and named-set names, including now-empty named sets.
    Session metadata's ID history is deliberately not pruned (Undo needs it).
    """
    from engine.mutation_guard import check_mutation
    check_mutation()
    selected = list(model.GetSelection())
    live = live_entities(selected)
    removed = len(selected) - len(live)
    if removed:
        model.SetSelection(live)
    named_changes = []
    components = [model.GetTopComponent()] + list(model.GetDefinitionList())
    seen = set()
    for comp in live_entities(components):
        ident = comp.GetID()
        if ident in seen:
            continue
        seen.add(ident)
        for name in list(comp.GetNamedSetNames()):
            members = list(comp.GetNamedSet(name))
            live = live_entities(members)
            count = len(members) - len(live)
            if count:
                comp.SetNamedSet(name, live)
                named_changes.append({'component_id': ident, 'name': name, 'removed': count})
    return {'selection_removed': removed, 'named_sets': named_changes}
