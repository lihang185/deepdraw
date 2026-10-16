MAGIC = b'DeepDrawDIM\x00\x03\n'
from . import core
from .entity_refs import named_members

#====================#
# CVector3D
#====================#
def load_CVector3D(x, y, z):
    return core.CVector3D.Load(x, y, z)
def save_CVector3D(a):
    return load_CVector3D, (a.x, a.y, a.z)
#====================#
# CPlane
#====================#
def load_CPlane(x, y, z, w):
    return core.CPlane.Load(x, y, z, w)
def save_CPlane(a):
    return load_CPlane, (a.x, a.y, a.z, a.w)

def load_CCircle3d(center, xaxis, plane, radius, yaxis):
    circle=core.CCircle3d()
    circle.center,circle.xaxis,circle.plane=center,xaxis,plane
    circle.radius,circle.yaxis=radius,yaxis
    return circle

def save_CCircle3d(circle):
    return load_CCircle3d,(circle.center,circle.xaxis,circle.plane,circle.radius,circle.yaxis)

def load_CArc3d(center, xaxis, plane, radius, yaxis, start_angle, end_angle):
    arc=core.CArc3d()
    arc.center,arc.xaxis,arc.plane=center,xaxis,plane
    arc.radius,arc.yaxis=radius,yaxis
    arc.start_angle,arc.end_angle=start_angle,end_angle
    return arc

def save_CArc3d(arc):
    return load_CArc3d,(arc.center,arc.xaxis,arc.plane,arc.radius,arc.yaxis,arc.start_angle,arc.end_angle)

def load_CCurve(first_edge, last_edge, num_edges, is_polygon):
    return core.CCurve.Load(first_edge,last_edge,num_edges,is_polygon)

def save_CCurve(curve):
    return load_CCurve,(curve.GetFirstEdge(),curve.GetLastEdge(),len(curve.GetEdges()),curve.is_polygon)

def load_CArcCurve(arc, first_edge, last_edge, num_edges, is_polygon):
    return core.CArcCurve.Load(arc,first_edge,last_edge,num_edges,is_polygon)

def save_CArcCurve(curve):
    return load_CArcCurve,(curve.arc,curve.GetFirstEdge(),curve.GetLastEdge(),len(curve.GetEdges()),curve.is_polygon)
#====================#
# CMatrix33
#====================#
def load_CMatrix33(d):
    return core.CMatrix33.Load(d)
def save_CMatrix33(m):
    d = []
    for i in range(3):
        for j in range(3):
            v = m.get(i, j)
            d.append(v)
    return load_CMatrix33, (d, )
#====================#
# CMatrix
#====================#
def load_CMatrix(d, scale, is_identity, is_orthogonal):
    return core.CMatrix.Load(d, scale, is_identity, is_orthogonal)
def save_CMatrix(m):
    d = []
    for i in range(4):
        for j in range(3):
            v = m.get(i, j)
            d.append(v)
    return load_CMatrix, (
        d, 
        m.scale, 
        m.is_identity, 
        m.is_orthogonal
    )
#====================#
# CVertex
#====================#
def load_CVertex(p):
    return core.CVertex.Load(p)
def save_CVertex(v):
    p = v.p
    return load_CVertex, (p, )
#====================#
# CEdge
#====================#
def load_CEdge(is_hide, v1, v2, is_soft, is_smooth):
    return load_CEdge_r2(is_hide, None, v1, v2, is_soft, is_smooth)

def load_CEdge_r2(is_hide, layer, v1, v2, is_soft, is_smooth):
    return core.CEdge.Load(is_hide, layer, v1, v2, is_soft, is_smooth)
def save_CEdge(edge):
    v1 = edge.GetStartVertex()
    v2 = edge.GetEndVertex()
    assert v1 and v2
    assert type(v1) is core.CVertex
    assert type(v2) is core.CVertex
    assert v1 is not v2
    is_hide = edge.IsHide()
    data = (
        is_hide, 
        edge.GetLayer(),
        v1, 
        v2, 
        edge.IsSoft(), 
        edge.IsSmooth(), 
    )
    return load_CEdge_r2, data
#====================#
# CEdgeUse
#====================#
def load_CEdgeUse(edge, is_edge_reversed):
    return core.CEdgeUse.Load(edge, is_edge_reversed)
def save_CEdgeUse(eu):
    return load_CEdgeUse, (
        eu.GetEdge(), 
        eu.IsEdgeReversed()
    )
#====================#
# CLoop
#====================#
def load_CLoop(is_outer_loop, is_convex, eu_list):
    return core.CLoop.Load(is_outer_loop, is_convex, eu_list)
def save_CLoop(loop):
    eu_list = list(loop.EnumEdgeUse())
    return load_CLoop, (
        loop.IsOuterLoop(), 
        loop.IsConvex(), 
        eu_list
    )
#====================#
# CFace
#====================#
def load_CFace(is_hide, plane, loops, mat, texcoord):
    return load_CFace_r2(is_hide, None, plane, loops, mat, texcoord)

def load_CFace_r2(is_hide, layer, plane, loops, mat, texcoord):
    return core.CFace.Load(is_hide, layer, plane, loops, mat, texcoord)
def save_CFace(face):
    is_hide = face.IsHide()
    loops = list(face.EnumLoops())
    return load_CFace_r2, (
        is_hide, 
        face.GetLayer(),
        face.GetPlane(), 
        loops, 
        face.GetMaterial(), 
        face.GetTextureCoords()
    )
#====================#
# CFaceTextureCoords
#====================#
_loaded_texture_coords = {}

def load_CFaceTextureCoords(m):
    coords = core.CFaceTextureCoords.Load(m)
    # Compatibility for bindings without a UV getter: preserve imported data.
    if not hasattr(coords, 'GetFrontTextureCoords'):
        _loaded_texture_coords[coords.GetID()] = m
    return coords
def save_CFaceTextureCoords(tc):
    if hasattr(tc, 'GetFrontTextureCoords'):
        matrix = tc.GetFrontTextureCoords()
    else:
        matrix = _loaded_texture_coords.get(tc.GetID())
        if matrix is None:
            raise RuntimeError('Cannot export new UV coordinates: native binding needs GetFrontTextureCoords')
    return load_CFaceTextureCoords, (matrix, )

def release_texture_records():
    _loaded_texture_coords.clear()
#====================#
# CGuideLine
#====================#
def load_CGuideLine(orig, dir):
    return core.CGuideLine.Load(orig, dir)
def save_CGuideLine(guide):
    return load_CGuideLine, (guide.orig, guide.dir)

def load_CSectionPlane(plane, bounds, hidden, is_active=True):
    section = core.CSectionPlane.Load(plane, is_active)
    box = core.CBounds2D()
    box.min_x, box.min_y, box.max_x, box.max_y = bounds
    section.bounds = box
    section.is_active = is_active
    section.SetHide(hidden)
    return section

def save_CSectionPlane(section):
    box = section.bounds
    return load_CSectionPlane, (section.plane,
        (box.min_x, box.min_y, box.max_x, box.max_y), section.IsHide(), section.is_active)
#====================#
# CDib
#====================#
def load_CDib(data):
    return core.CDib.Load(data)
def save_CDib(dib):
    data = dib.GetData()
    return load_CDib, (data, )
#====================#
# CTexture
#====================#
def load_CTexture(name, size_u, size_v, dib):
    return core.CTexture.Load(name, size_u, size_v, dib)
def save_CTexture(tex):
    return load_CTexture, (
        tex.name, 
        tex.size_u, 
        tex.size_v, 
        tex.GetDib()
    )
#====================#
# CMaterial
#====================#
def load_CMaterial(name, color, use_opacity, opacity, tex):
    return core.CMaterial.Load(name, color, use_opacity, opacity, tex)
def save_CMaterial(m):
    return load_CMaterial, (
        m.name,
        m.color, 
        m.use_opacity, 
        m.opacity, 
        m.GetTexture()
    )
#====================#
# CComponent
#====================#
def load_CComponent(entity_list, comp):
    # The container must already be attached to its model. Definition metadata
    # is restored separately; the base container owns only its entities here.
    for entity in entity_list:
        comp.AddEntity(entity)

def save_named_sets(comp):
    from .named_set_schema import names
    return names({name: named_members(comp, name) for name in comp.GetNamedSetNames()})
def save_CComponent(comp):
    entity_list = []
    for e in comp.EnumEntities():
        if e.IsMarkedDeleted():
            continue
        if type(e) is core.CEdge:
            entity_list.append(e)
        elif type(e) is core.CFace:
            entity_list.append(e)
        elif type(e) is core.CComponentInstance:
            entity_list.append(e)
        elif type(e) is core.CGuideLine:
            entity_list.append(e)
        elif type(e) is core.CSectionPlane:
            entity_list.append(e)
        else:
            pass
    return entity_list
#====================#
# CComponentDefinition
#====================#
def component_definition_record(comp):
    curves={}
    for edge in comp.EnumEntities():
        if isinstance(edge,core.CEdge) and not edge.IsMarkedDeleted():
            curve=edge.GetCurve()
            if curve is not None:
                curves.setdefault(curve.GetID(),dict(curve=curve,edges=[]))['edges'].append(edge)
    return {'name': comp.name, 'description': comp.description,
            'agent_hint': comp.agent_hint,
            'file_path': comp.file_path, 'entities': save_CComponent(comp),
            'named_sets': save_named_sets(comp),
            'is_dynamic_comp': comp.is_dynamic_comp, 'dynamic_comp': comp.dynamic_comp,
            'curves': list(curves.values())}


def normalize_definition_record(value):
    if not isinstance(value, dict):raise TypeError('Current definition record must be a dictionary')
    record = dict(value)
    record.setdefault('name', '')
    record.setdefault('description', '')
    record.setdefault('agent_hint', '')
    record.setdefault('file_path', '')
    record.setdefault('entities', [])
    record.setdefault('named_sets', {})
    from .named_set_schema import names
    record['named_sets']=names(record['named_sets'])
    record.pop('is_group', None)  # Legacy definition field; group state belongs to instances.
    record.setdefault('is_dynamic_comp', False)
    record.setdefault('dynamic_comp', '')
    if type(record['is_dynamic_comp']) is not bool or not isinstance(record['dynamic_comp'], str):
        raise TypeError('Invalid dynamic component fields')
    return record


def load_CComponentDefinition(record):
    record = normalize_definition_record(record)
    args = (record['name'], record['description'], record['agent_hint'],
            record['file_path'], record['entities'], record['named_sets'])
    try:
        return core.CComponentDefinition.Load(*args, record['is_dynamic_comp'], record['dynamic_comp'])
    except TypeError:
        # Transitional compatibility with older local native bindings.
        return core.CComponentDefinition.Load(*args, False, record['is_dynamic_comp'], record['dynamic_comp'])




def save_CComponentDefinition(comp):
    return load_CComponentDefinition, (component_definition_record(comp),)
#====================#
# CComponentInstance
#====================#
def load_CComponentInstance(is_hide, name, tm, mat, comp, is_group=False, is_image=False):
    return load_CComponentInstance_r2(is_hide, None, name, tm, mat, comp, is_group, is_image)

def load_CComponentInstance_r2(is_hide, layer, name, tm, mat, comp, is_group=False, is_image=False):
    instance=core.CComponentInstance.Load(is_hide, layer, name, tm, mat, comp, is_group, is_image)
    instance.dynamic_info=''
    instance.SetAnimationTransform(core.CMatrix())
    return instance
def save_CComponentInstance(inst):
    is_hide = inst.IsHide()
    return load_CComponentInstance_r2, (
        is_hide, 
        inst.GetLayer(),
        inst.name, 
        inst.GetTransform(), 
        inst.GetMaterial(), 
        inst.GetDefinition(),
        inst.is_group,
        inst.is_image
    )
#====================#
# CModel
#====================#
MODEL_VERSION = 3


def validate_model_record(record):
    if not isinstance(record, dict):
        raise TypeError('Current model record must be a dictionary')
    version = record.get('version')
    if type(version) is not int or version != MODEL_VERSION:
        raise ValueError('Unsupported model version: {!r}'.format(version))
    for field in ('materials', 'definitions', 'top_component'):
        if field not in record:
            raise ValueError('Missing model field: ' + field)
    return record


def load_CModel(record):
    record = validate_model_record(record)
    layers = prepare_layers(record.setdefault('layers', []))
    return core.CModelData.Load(record['materials'], layers, record['definitions'],
                           load_CComponentDefinition(record['top_component']))

def save_CModel(model):
    # material
    material_list = []
    for i in range(model.getNumMaterials()):
        mat = model.getMaterial(i)
        if mat is not None and not mat.IsMarkedDeleted():
            material_list.append(mat)
    
    # comp_def
    comp_def_lsit = []
    for i in range(model.getNumDefinition()):
        comp_def = model.getDefinition(i)
        if comp_def is not None and not comp_def.IsMarkedDeleted():
            comp_def_lsit.append(comp_def)
    
    # entities
    comp = model.GetTopComponent()
        
    return load_CModel, ({
        'version': MODEL_VERSION,
        'materials': material_list,
        'definitions': comp_def_lsit,
        'top_component': component_definition_record(comp),
        'layers': layer_records(model),
    },)


def load_CLayer(name, hidden, material):
    return core.CLayer.Load(name, hidden, material)

def save_CLayer(layer):
    return load_CLayer, (layer.name, layer.is_hide, layer.mtl)

def layer_records(model):
    # Keep source IDs only for saved-scene visibility remapping. Membership is
    # carried by r2 geometry references; never scan the scene to duplicate it.
    return [dict(id=e.GetID(),layer=e) for e in model.GetLayers() if not e.IsMarkedDeleted()]


def prepare_layers(records):
    """Resolve legacy metadata to objects before native model assembly."""
    layers=[]
    for index,record in enumerate(records):
        if not isinstance(record,dict):
            name,hidden,material=record
            record=dict(name=name,hidden=hidden,material=material,entities=[])
            records[index]=record
        layer=record.get('layer')
        if layer is None:
            layer=core.CLayer.Load(record['name'],record['hidden'],record['material'])
            record['layer']=layer
        layers.append(layer)
    return layers

def restore_layers(model,records):
    mapping = {}
    registered={layer.GetID() for layer in model.GetLayers()}
    for record in records:
        if isinstance(record,dict):
            entities=record.get('entities',[])
        else:name,hidden,material=record;entities=[]
        # r2 geometry and this record share the same pickle-memoized layer.
        # Legacy records have no layer object and use the membership list.
        layer=record.get('layer') if isinstance(record,dict) else None
        if layer is None:
            if isinstance(record,dict):name,hidden,material=record['name'],record['hidden'],record['material']
            layer=core.CLayer.Load(name,hidden,material)
        if layer.GetID() not in registered:
            model.addLayer(layer)
            registered.add(layer.GetID())
        if isinstance(record,dict) and 'id' in record:
            mapping[record['id']] = layer.GetID()
        for entity in entities:
            if not isinstance(entity,core.CDrawingElement) or entity.IsMarkedDeleted():
                raise ValueError('Invalid layer member')
            if isinstance(entity,(core.CEdge,core.CFace,core.CComponentInstance)):
                entity.SetLayer(layer)
    return mapping

import pickle
import io

DISPATCH = {
    core.CCircle3d: save_CCircle3d,
    core.CArc3d: save_CArc3d,
    core.CCurve: save_CCurve,
    core.CArcCurve: save_CArcCurve,
    core.CLayer: save_CLayer,
    core.CVector3D: save_CVector3D,
    core.CPlane: save_CPlane,
    core.CMatrix33: save_CMatrix33,
    core.CMatrix: save_CMatrix,
    core.CVertex: save_CVertex,
    core.CEdge: save_CEdge,
    core.CEdgeUse: save_CEdgeUse,
    core.CLoop: save_CLoop,
    core.CFace: save_CFace,
    core.CGuideLine: save_CGuideLine,
    core.CSectionPlane: save_CSectionPlane,
    core.CFaceTextureCoords: save_CFaceTextureCoords,
    core.CDib: save_CDib,
    core.CTexture: save_CTexture,
    core.CMaterial: save_CMaterial,
    core.CComponentDefinition: save_CComponentDefinition,
    core.CComponentInstance: save_CComponentInstance,
    core.CModel: save_CModel,
}

#====================#
# Export
#====================#
def save_sketchup_model(model, filename):
    if not str(filename).lower().endswith('.dim'):
        raise ValueError('Current DeepDraw models must be saved as .dim')
    # Complete serialization before touching the destination.
    buffer = io.BytesIO()
    buffer.write(MAGIC)
    writer = pickle.Pickler(buffer, protocol=4)
    writer.dispatch_table = DISPATCH
    from .scenes import file_layer_references
    with file_layer_references(model):
        writer.dump(model)
    import os, tempfile
    fd, temporary = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(filename)), suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(buffer.getvalue())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, filename)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
    return True

import os.path
def _check_header(stream):
    if stream.read(len(MAGIC)) != MAGIC:
        raise ValueError('Not a current DAI file or unsupported file version')


class CurrentUnpickler(pickle.Unpickler):
    def __init__(self,stream):
        super().__init__(stream)
        self.curves=[]
        self.layers=[]
        self.sections=[]
        self.top_sections=[]

    def definition(self,record):
        self.curves.extend(record.get('curves',[]))
        definition = load_CComponentDefinition(record)
        self.sections.append((definition, [e for e in record.get('entities', []) if isinstance(e, core.CSectionPlane)]))
        return definition

    def model(self,record):
        self.layers=record.get('layers',[])
        self.curves.extend(record.get('top_component',{}).get('curves',[]))
        self.top_sections = [e for e in record.get('top_component',{}).get('entities',[]) if isinstance(e,core.CSectionPlane)]
        return load_CModel(record)

    def find_class(self, module, name):
        if module == 'engine.serialization' and name.startswith('load_'):
            if name=='load_CComponentDefinition':return self.definition
            if name=='load_CModel':return self.model
            function = globals().get(name)
            if callable(function):return function
        if module == 'builtins' and name == 'bytearray':return bytearray
        raise pickle.UnpicklingError('Unsupported current record: '+module+'.'+name)


def restore_curves(model,groups):
    factory=core.CEntityFactory(model)
    for record in groups:
        edges=record['edges'] if isinstance(record,dict) else record
        if not edges:continue
        if any(not isinstance(e,core.CEdge) or e.IsMarkedDeleted() for e in edges):
            raise ValueError('Invalid curve edges')
        parent=edges[0].GetParentComponent()
        if parent is None or any(e.GetParentComponent()!=parent for e in edges):
            raise ValueError('Curve edges must share a component')
        curve=record['curve'] if isinstance(record,dict) else factory.NewCurve()
        curve.SetParentComponent(parent)
        for edge in edges:edge.SetCurve(curve)
        if not isinstance(record,dict):curve.UpdateEdgeLink(edges[0])


def load_sketchup_model(model, filename, progress=None):
    if not str(filename).lower().endswith('.dim'):raise ValueError('Only .dim models are supported')
    with open(filename, 'rb') as stream:
        _check_header(stream)
        from .load_progress import ProgressReader
        source = ProgressReader(stream, progress) if progress else stream
        reader = CurrentUnpickler(source)
        data = reader.load()
        if progress:source.report(True)
    if progress:progress('恢复模型', 0, 0)
    if not isinstance(data, core.CModelData):raise ValueError('Expected model record')
    model.LoadData(data)
    restore_sections(reader.sections + [(model.GetTopComponent(), reader.top_sections)])
    mapping = restore_layers(model,reader.layers)
    from .scenes import restore_file_layer_references
    restore_file_layer_references(model,mapping)
    restore_curves(model,reader.curves)
    return model


def load_sketchup_model_as_component(model, filename, unwrap_canonical=False):
    if not str(filename).lower().endswith('.dim'):raise ValueError('Only .dim models are supported')
    curve_groups=[]
    def model_record(data):
        data = validate_model_record(data)
        record = normalize_definition_record(data['top_component'])
        curve_groups.extend(record.get('curves',[]))
        return dict(materials_ls=data['materials'], compdef_ls=data['definitions'], entity_ls=record['entities'],
                    named_sets=record['named_sets'], description=record['description'], agent=record['agent_hint'],
                    is_dynamic_comp=record['is_dynamic_comp'], dynamic_comp=record['dynamic_comp'],
                    layers=data.get('layers',[]))
    class AssetUnpickler(CurrentUnpickler):
        def find_class(self, module, name):
            if module == 'builtins' and name == 'bytearray':
                return bytearray
            if module == 'engine.serialization' and name.startswith('load_'):
                if name == 'load_CModel':
                    return model_record
                if name == 'load_CComponentDefinition':return self.definition
                function = globals().get(name)
                if callable(function):
                    return function
            raise pickle.UnpicklingError('Unsupported asset record: ' + module + '.' + name)
    with open(filename, 'rb') as stream:
        _check_header(stream)
        reader=AssetUnpickler(stream)
        data = reader.load()
        curve_groups.extend(reader.curves)
    if not isinstance(data, dict):
        raise ValueError('Asset does not contain DeepDraw model data')
    # Create the wrapper through the factory, whose ownership contract is known.
    # Some native builds return an owning Python wrapper from LoadDataAsComponent.
    for material in data['materials_ls']:
        model.addMaterial(material)
    for definition in data['compdef_ls']:
        model.addDefinition(definition)
    # Canonical single-component resources already carry their own definition.
    # Reuse it instead of introducing a file-container level on every insertion.
    restore_sections(reader.sections)
    entities = data['entity_ls']
    if unwrap_canonical and len(entities) == 1 and isinstance(entities[0], core.CComponentInstance):
        import json
        instance = entities[0]
        definition = instance.GetDefinition()
        try:
            hint = json.loads(definition.agent_hint)
        except (ValueError, TypeError):
            hint = {}
        standard = hint.get('asset_standard', {}) if isinstance(hint, dict) else {}
        identity = all((instance.GetTransform().Transform(core.CVector3D(*p))-
                        core.CVector3D(*p)).Length() < 1e-9
                       for p in ((0,0,0),(1,0,0),(0,1,0),(0,0,1)))
        if (standard.get('structure_version') == 2 and identity and
                instance.GetMaterial() is None and not instance.IsHide()):
            definition.file_path = filename
            restore_layers(model,data.get('layers',[]))
            restore_curves(model,curve_groups)
            return definition
    factory = core.CEntityFactory(model)
    component = factory.NewComponentDefinition()
    component.name = os.path.basename(filename)
    component.description = data.get('description', '')
    component.agent_hint = data.get('agent', '')
    component.is_dynamic_comp = data.get('is_dynamic_comp', False)
    component.dynamic_comp = data.get('dynamic_comp', '')
    component.file_path = filename
    model.addDefinition(component)
    for entity in data['entity_ls']:
        component.AddEntity(entity)
    for name, members in data.get('named_sets', {}).items():
        component.AddNamedSet(name, members)
    restore_curves(model,curve_groups)
    restore_layers(model,data.get('layers',[]))
    return component
    


def restore_sections(records):
    for component, sections in records:
        existing = {e.GetID() for e in component.EnumEntities()}
        for section in sections:
            if section.GetID() not in existing:component.AddEntity(section)
