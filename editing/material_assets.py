"""Native material operations for the education UI."""
from pathlib import Path
from engine import core
class MaterialAssets:
    def __init__(self, context):
        self.s = context

    def update_material(self, material_id, changes):
        """Edit in place; native property setters record changes for undo."""
        self.s.edit.require_operation()
        material = next((self.s.model.getMaterial(i) for i in range(self.s.model.getNumMaterials())
                         if self.s.model.getMaterial(i).GetID() == material_id
                         and not self.s.model.getMaterial(i).IsMarkedDeleted()), None)
        if material is None:
            raise ValueError('Scene material no longer exists')
        texture = material.GetTexture()
        if any(key in changes for key in ('texture_path', 'size_u', 'size_v')):
            if changes.get('texture_path'):
                dib = core.CDib.Load(bytearray(Path(changes['texture_path']).read_bytes()))
                name = changes.get('texture', Path(changes['texture_path']).name)
            elif texture is not None:
                dib, name = texture.GetDib(), texture.name
            else:
                raise ValueError('请先选择贴图，再修改贴图尺寸')
            texture = core.CTexture.Load(name, float(changes.get('size_u', texture.size_u if texture else 100)),
                                         float(changes.get('size_v', texture.size_v if texture else 100)), dib)
        material.Record(True)
        for key in ('color', 'edge_color'):
            if key in changes:
                setattr(material, key, core.CVector3D(*(v / 255.0 for v in changes[key])))
        for key in ('use_opacity', 'use_edge_color', 'opacity'):
            if key in changes:
                setattr(material, key, changes[key])
        if 'name' in changes:
            material.name = changes['name']
        if any(key in changes for key in ('texture_path', 'size_u', 'size_v')):
            material.SetTexture(texture)
        self.s.edit.touch(self.s.wrap(self.s.model.GetTopComponent()))
        return self.s.edit._report({'action': 'update_material', 'material_id': material.GetID()})


    def create_material(self, asset):
        self.s.edit.require_operation()
        if not isinstance(asset, dict):
            raise TypeError("Expected a material record from the catalog")
        item = asset
        if item['kind'] != 'material':
            raise ValueError('Expected a material asset')
        material = self._create_material(item)
        return self.s.edit._report({'action': 'create_material', 'material_id': material.GetID()})


    def _create_material(self, item):
        info = item['properties']
        texture = None
        if info.get('texture_path') or info.get('texture_bytes'):
            data = info.get('texture_bytes') or Path(info['texture_path']).read_bytes()
            dib = core.CDib.Load(bytearray(data))
            texture = core.CTexture.Load(info['texture'], float(info['size_u']), float(info['size_v']), dib)
        import math
        import re
        from engine.qt import QtGui
        base_name = info['name']
        existing = [self.s.model.getMaterial(i) for i in range(self.s.model.getNumMaterials())
                    if not self.s.model.getMaterial(i).IsMarkedDeleted()]
        def same_number(a, b):
            return math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-6)
        def same_color(native, values):
            return all(same_number(a, b / 255.0) for a, b in zip((native.x, native.y, native.z), values))
        def same_parameters(candidate):
            if not same_color(candidate.color, info['color']):
                return False
            if bool(candidate.use_opacity) != bool(info.get('use_opacity', False)) or not same_number(candidate.opacity, info.get('opacity', 1)):
                return False
            if bool(candidate.use_edge_color) != bool(info.get('use_edge_color', info.get('use_line_color', False))):
                return False
            if not same_color(candidate.edge_color, info.get('edge_color', info.get('line_color', [0, 0, 0]))):
                return False
            current = candidate.GetTexture()
            if (current is None) != (texture is None):
                return False
            if current is None:
                return True
            if not same_number(current.size_u, texture.size_u) or not same_number(current.size_v, texture.size_v):
                return False
            first = QtGui.QImage.fromData(bytes(current.GetDib().GetData())).convertToFormat(QtGui.QImage.Format_RGBA8888)
            second = QtGui.QImage.fromData(bytes(texture.GetDib().GetData())).convertToFormat(QtGui.QImage.Format_RGBA8888)
            return not first.isNull() and not second.isNull() and first == second
        for candidate in existing:
            if (candidate.name == base_name or re.fullmatch(re.escape(base_name) + r'_\d+', candidate.name)) and same_parameters(candidate):
                return candidate
        names = {candidate.name for candidate in existing}
        name, suffix = base_name, 1
        while name in names:
            name = '{}_{:02d}'.format(base_name, suffix)
            suffix += 1
        material = core.CMaterial.Load(name, core.CVector3D(*(v/255.0 for v in info['color'])),
                                       bool(info.get('use_opacity', False)), float(info.get('opacity', 1)), texture)
        material.use_edge_color = bool(info.get('use_edge_color', info.get('use_line_color', False)))
        material.edge_color = core.CVector3D(*(v / 255.0 for v in
            info.get('edge_color', info.get('line_color', [0, 0, 0]))))
        self.s.model.addMaterial(material)
        return material


