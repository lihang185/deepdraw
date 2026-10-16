"""SketchUp SDK -> current editor2 geometry -> versioned education DIM."""
from pathlib import Path
import math
import tempfile

from engine import core, model_files, serialization
from .native import load

CM_PER_INCH = 2.54


class ModelImporter:
    def __init__(self, model, texture_directory):
        self.model = model
        self.factory = core.CEntityFactory(model)
        self.texture_directory = Path(texture_directory)
        self.entities = {}
        self.definitions = {}
        self.materials = {}
        self.textures = {}
        self.references = []

    @staticmethod
    def vector(value, scale=1.0):
        return core.CVector3D(value.x * scale, value.y * scale, value.z * scale)

    @staticmethod
    def transform(value):
        data = value.GetData()
        if len(data) != 16 or not all(math.isfinite(v) for v in data) or data[15] == 0:
            raise ValueError('Invalid SketchUp instance transformation')
        if any(data[i] != 0 for i in (3, 7, 11)):
            raise ValueError('Perspective SketchUp instance transformations are unsupported')
        matrix = core.CMatrix()
        # SDK stores basis vectors in columns. SetRow would transpose the
        # linear part in editor2. Normalize the homogeneous divisor because
        # editor2.scale multiplies coordinates, whereas SDK data[15] divides.
        divisor = data[15]
        for axis in range(3):
            matrix.SetAxis(axis, core.CVector3D(*(data[axis*4+i] / divisor for i in range(3))))
        matrix.SetRow(3, core.CVector3D(*(data[12+i] * CM_PER_INCH / divisor for i in range(3))))
        matrix.scale = 1.0
        matrix.is_identity = matrix.IsIdentity()
        matrix.is_orthogonal = matrix.IsOrthogonal()
        return matrix

    def vertex(self, source):
        key = source._handle_id
        if key not in self.entities:
            self.entities[key] = self.factory.NewVertex(self.vector(source.GetPosition(), CM_PER_INCH))
        return self.entities[key]

    def edge(self, source):
        key = source._handle_id
        if key not in self.entities:
            edge = self.factory.NewEdge(self.vertex(source.GetStartVertex()),
                                        self.vertex(source.GetEndVertex()), False)
            self.entities[key] = edge
            edge.SetHide(source.GetHidden())
            edge.SetSoft(source.GetSoft())
            edge.SetSmooth(source.GetSmooth())
        return self.entities[key]

    def loop(self, source):
        loop = self.factory.NewLoop()
        self.references.append(loop)
        loop.SetIsOuterLoop(source.IsOuterLoop())
        loop.SetIsConvex(source.IsConvex())
        for use in source.GetEdgeUses():
            edge_use = self.factory.NewEdgeUse(self.edge(use.GetEdge()), use.IsReversed())
            self.references.append(edge_use)
            loop.AddEdgeUseToTail(edge_use)
        return loop

    def texture_coords(self, source):
        material = source.GetFrontMaterial()
        texture = material.GetTexture() if material else None
        if texture is None:
            return None
        helper = source.GetUVHelper()
        try:
            matrix = core.CMatrix33.Load(helper.GetFrontTextureMatrix().GetData())
        finally:
            helper.Release()
        matrix.set(2, 0, matrix.get(2, 0) * CM_PER_INCH)
        matrix.set(2, 1, matrix.get(2, 1) * CM_PER_INCH)
        scale = core.CMatrix33.NewFromScale(1.0 / texture.GetScaleU(), 1.0 / texture.GetScaleV())
        matrix = matrix.Multiply(scale)
        matrix.Reverse()
        coords = serialization.load_CFaceTextureCoords(matrix).AddToUndoManager()
        self.references.append(coords)
        return coords

    def face(self, source):
        key = source._handle_id
        if key not in self.entities:
            face = self.factory.NewFace()
            self.entities[key] = face
            face.SetHide(source.GetHidden())
            face.AddLoop(self.loop(source.GetOuterLoop()))
            for loop in source.GetInnerLoops():
                face.AddLoop(self.loop(loop))
            plane = source.GetPlane()
            face.SetPlane(core.CPlane(plane.x, plane.y, plane.z, plane.w * CM_PER_INCH))
            face.SetMaterial(self.material(source.GetFrontMaterial()))
            face.SetTextureCoords(self.texture_coords(source))
        return self.entities[key]

    def texture(self, source):
        if source is None:
            return None
        key = source._handle_id
        if key not in self.textures:
            source_name = Path(source.GetFileName())
            # The SDK chooses its encoder from the destination extension.
            # Keep JPEG (and other source formats) instead of expanding to PNG.
            suffix = source_name.suffix.lower() or '.png'
            path = self.texture_directory / (str(key) + suffix)
            if not source.WriteToFile(str(path)):
                raise RuntimeError('Cannot extract SketchUp texture: ' + source.GetFileName())
            dib = core.CDib.Load(bytearray(path.read_bytes()))
            self.references.append(dib)
            texture = core.CTexture.Load(source_name.stem + suffix,
                                         CM_PER_INCH / source.GetScaleU(),
                                         CM_PER_INCH / source.GetScaleV(), dib)
            self.textures[key] = texture
        return self.textures[key]

    def material(self, source):
        if source is None:
            return None
        key = source._handle_id
        if key not in self.materials:
            material = serialization.load_CMaterial(source.GetName(), self.vector(source.GetColor()),
                                                    source.GetUseOpacity(), source.GetOpacity(),
                                                    self.texture(source.GetTexture()))
            self.materials[key] = material
            self.model.addMaterial(material)
        return self.materials[key]

    def definition(self, source):
        key = source._handle_id
        if key not in self.definitions:
            definition = self.factory.NewComponentDefinition()
            # Register before recursing to preserve shared nested definitions.
            self.definitions[key] = definition
            self.model.addDefinition(definition)
            definition.name = source.GetName()
            definition.description = source.GetDescription()
            definition.file_path = source.GetPath()
            self.component(source.GetEntities(), definition)
        return self.definitions[key]

    def instance(self, source, is_group=False, is_image=False):
        instance = self.factory.NewComponentInstance()
        self.entities[source._handle_id] = instance
        instance.name = source.GetName()
        instance.SetHide(source.GetHidden())
        instance.SetTransform(self.transform(source.GetTransform()))
        instance.SetMaterial(self.material(source.GetMaterial()))
        instance.SetDefinition(self.definition(source.GetDefinition()))
        instance.is_group = is_group
        instance.is_image = is_image
        instance.dynamic_info = ''
        return instance

    def component(self, source, target):
        for edge in source.GetEdges():
            target.AddEntity(self.edge(edge))
        for face in source.GetFaces():
            target.AddEntity(self.face(face))
        for instance in source.GetInstances():
            target.AddEntity(self.instance(instance))
        for group in source.GetGroups():
            target.AddEntity(self.instance(group, is_group=True))
        for image in source.GetImages():
            target.AddEntity(self.instance(image, is_image=True))

    def build(self, source):
        for material in source.GetMaterialList():
            self.material(material)
        for definition in source.GetComponentDefinitionList() + source.GetGroupDefinitionList():
            self.definition(definition)
        top = self.model.GetTopComponent()
        top.name = source.GetName()
        top.description = load('suapi_extra').sumodel_get_description(source)
        self.component(source.GetEntities(), top)


def convert(source_path, output_path):
    source_path, output_path = Path(source_path).resolve(), Path(output_path).resolve()
    if source_path == output_path:
        raise ValueError('SKP source and DIM output must differ')
    if output_path.suffix.lower() != '.dim':
        raise ValueError('Education import output must use .dim')
    source = load('suapi').SUModel.LoadFromFile(str(source_path))
    model = None
    importer = None
    try:
        model = core.CModel()
        with tempfile.TemporaryDirectory(prefix='deepdraw-skp-textures-') as scratch:
            importer = ModelImporter(model, scratch)
            importer.build(source)
            model_files.save_sketchup_model(model, str(output_path))
    finally:
        if model is not None:
            model.Release()
        importer = None
        source.Release()
