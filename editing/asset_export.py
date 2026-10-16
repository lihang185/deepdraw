"""Export a human-selected component to a versioned education DIM."""
import pickle
from pathlib import Path
from engine import core, serialization as codec
import os, tempfile

def export_instances_file(session, instances, path):
    """Export one instance's definition as the standalone model's top component."""
    session.check()
    if len(instances) != 1:
        raise ValueError('请选择一个组件导出')
    top_component = instances[0].GetDefinition()
    path = Path(path)
    if path.suffix.lower() != '.dim':
        raise ValueError('模型必须保存为 .dim')
    definitions, materials = {}, {}
    visiting = set()
    def visit(comp):
        ident = comp.GetID()
        if ident in visiting:
            raise ValueError('Cyclic definition cannot be exported')
        if ident in definitions:
            return
        visiting.add(ident)
        definitions[ident] = comp
        for entity in comp.EnumEntities():
            if entity.IsMarkedDeleted():
                continue
            if isinstance(entity, (core.CFace, core.CComponentInstance)):
                mat = entity.GetMaterial()
                if mat is not None:
                    materials[mat.GetID()] = mat
            if isinstance(entity, core.CComponentInstance):
                visit(entity.GetDefinition())
        visiting.remove(ident)
    visit(top_component)
    for layer in session.model.GetLayers():
        if not layer.IsMarkedDeleted() and layer.mtl is not None:
            materials[layer.mtl.GetID()] = layer.mtl
    # The selected definition is the root, not an additional library definition.
    definitions.pop(top_component.GetID())
    def save_model(model):
        return codec.load_CModel, ({'version': codec.MODEL_VERSION,
            'layers': codec.layer_records(session.model), 'materials': list(materials.values()), 'definitions': list(definitions.values()),
            'top_component': codec.component_definition_record(top_component)},)
    def serialize(stream):
        writer = pickle.Pickler(stream, protocol=4)
        writer.dispatch_table = dict(codec.DISPATCH)
        writer.dispatch_table[core.CModel] = save_model
        writer.dump(session.model)
    fd, temp = tempfile.mkstemp(dir=str(path.parent), suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(codec.MAGIC)
            serialize(stream)
        os.replace(temp, str(path))
    finally:
        if os.path.exists(temp):os.unlink(temp)
    return str(path)
