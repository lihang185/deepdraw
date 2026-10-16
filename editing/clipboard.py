"""Detached clipboard records: never retain native pointers across model changes."""
import io
import pickle
from engine import core, serialization


def copy(context):
    context.check()
    selected = list(context.selection.current().entities)
    if not selected:
        raise ValueError('请先选择需要复制的对象')
    geometry = {e.GetID(): e for e in selected}
    for entity in selected:
        if isinstance(entity, core.CFace):
            for loop in entity.EnumLoops():
                for use in loop.EnumEdgeUse():
                    edge = use.GetEdge()
                    geometry[edge.GetID()] = edge
    selected = list(geometry.values())
    model = context.model
    data = dict(entities=selected,
                materials=[model.getMaterial(i) for i in range(model.getNumMaterials())
                           if not model.getMaterial(i).IsMarkedDeleted()],
                definitions=[e for e in model.GetDefinitionList() if not e.IsMarkedDeleted()])
    stream = io.BytesIO()
    writer = pickle.Pickler(stream, protocol=4)
    writer.dispatch_table = serialization.DISPATCH
    writer.dump(data)
    return stream.getvalue()


def paste_definition(model, data):
    reader = serialization.CurrentUnpickler(io.BytesIO(data))
    record = reader.load()
    for material in record['materials']:
        model.addMaterial(material)
    for definition in record['definitions']:
        model.addDefinition(definition)
    serialization.restore_sections(reader.sections)
    definition = core.CEntityFactory(model).NewComponentDefinition()
    definition.name = '粘贴对象'
    model.addDefinition(definition)
    for entity in record['entities']:
        definition.AddEntity(entity)
    serialization.restore_curves(model, reader.curves)
    return definition
