from engine.coordinates import transform_plane
import os, sys
from engine.qt import QtGui, QOpenGLTexture
QImage = QtGui.QImage

from engine import core
from . import render_backend
from . import overlays
from .render_changes import RenderChange
from engine.coordinates import active_matrix, local_drawing

#import render
import time


#
DEBUG_INFO = False
Print_Time = False


def visible_entity(entity):
    if entity.IsMarkedDeleted() or entity.IsHide():
        return False
    if isinstance(entity,(core.CGuideLine,core.CSectionPlane)):
        return True
    layer = entity.GetLayer()
    return layer is None or (not layer.IsMarkedDeleted() and not layer.is_hide)



class RMaterial:
    def __init__(self):
        self.m = None
        self.gl_tex = 0
        self.type = self.Type_Default
        self._native = None
        
    Type_Default = 0
    Type_Color = 1
    Type_Texture = 2

    def LoadMaterial(self, m, gl):
        self.gl = gl
        self.m = m
        
        if m is None:
            self.type = RMaterial.Type_Default
        else:
            texture = m.GetTexture()
            if texture:
                texname = texture.name;
                if DEBUG_INFO:
                    print("Material:%s load texture" % ascii(texname))
                #imgpath = abspath(texname)
                dib = texture.GetDib()
                ok, self.gl_tex_obj = self.LoadImageFromDib(dib)
                if ok:
                    self.type = RMaterial.Type_Texture
                    self.gl_tex = self.gl_tex_obj.textureId()
                else:
                    self.type = RMaterial.Type_Color
            else:
                self.type = RMaterial.Type_Color
                
            # Rendering must not rewrite scene opacity settings. In particular,
            # rebuilding observation caches must preserve the user's checkbox.
    
        self._native = render_backend.material_snapshot(self)
        self._values = render_backend.material_values(self)

    def refresh_snapshot(self):
        values = render_backend.material_values(self)
        regroup = values[2] != self._values[2]
        if values != self._values:
            self._native.update(render_backend.native.Material(*values))
            self._values = values
        return regroup

    def Bind(self):
        self._native.bind()

    def IsOpacity(self):
        return self._native.is_transparent()

    def IsDefault(self):
        return self.type == self.Type_Default

    ############
    # Material Binding
    # Lighting
    # 材质 & 灯光
    ############
    def LoadImageFromFile(self, filepath):
        fix_path = os.path.join(sys.data_path, os.path.basename(filepath))
        try:
            with open(fix_path, 'rb') as hf:
                data = hf.read()
        except Exception as e:
            print(f"load texture {fix_path} exception, {e}")
            return False, None
        
        image = QImage()
        valid = image.loadFromData(data)
        if not valid:
            return False, None
            
        gl_tex_obj = QOpenGLTexture(image.mirrored())
        return True, gl_tex_obj
    
    def LoadImageFromDib(self, dib):
        data = dib.GetData()
        
        image = QImage()
        valid = image.loadFromData(data)
        if not valid:
            return False, None
        
        gl_tex_obj = QOpenGLTexture(image.mirrored())
        return True, gl_tex_obj


class RenderComponent:
    def __init__(self, comp, model):
        self.comp = comp
        self.model = model
        self.dirty = True
        #
        self.instances = []
        
        self.clear_geom()
        self.model_cache = render_backend.MeshCache()
    
    def is_dirty(self):
        return self.dirty
    
    def mark_dirty(self):
        self.section_geometry_revision = getattr(self, 'section_geometry_revision', 0) + 1
        self.dirty = True
        self.flat_geometry = None

    
    def clear_geom(self):
        self.nomat_ls = []
        self.dict_mats_normal = {}
        self.dict_mats_opacity = {}
        self.edge_group_ls = []
    
    def add_node(self, node):
        prepared = getattr(self.model, '_initial_geometry', None)
        if prepared is not None and not hasattr(node, 'entities'):
            groups, edges = self.model.initial_geometry(node.comp)
            for material, faces in groups.items():
                material = material or node.mtl
                if material is None:
                    self.nomat_ls.append((faces, node))
                else:
                    self.add_faces(faces, self.model.get_rt_material(material), node)
            inst = node.get_inst()
            if edges and not (inst and inst.is_image):
                self.add_edges(edges, node.matrix)
            return
        self.classify_face(node)
        self.add_edge_group(node)
    
    def classify_face(self, node):
        comp = node.comp
        if comp.GetNumFaces() == 0:
            return
        
        # classify by material
        nomat = []
        dict_mats = {}
        
        for e in (node.entities if hasattr(node, 'entities') else comp.EnumEntities()):
            if type(e) is core.CFace and visible_entity(e):
                #if e.GetHidden(): continue

                mtl = e.GetMaterial() or node.mtl
                if mtl is None:
                    nomat.append(e)
                else:
                    rm = self.model.get_rt_material(mtl)
                    ls = dict_mats.setdefault(rm, [])
                    ls.append(e)
        
        if nomat:
            item = nomat, node
            self.nomat_ls.append(item)

        for mtl, list1 in dict_mats.items():
            if mtl:
                self.add_faces(list1, mtl, node)

    
    def add_edge_group(self, node):
        if node.comp.GetNumEdges() == 0:
            return
        edge_ls = []
        # 这里针对image要特殊处理一下
        inst = node.get_inst()
        if inst and inst.is_image:
            return
        for e in (node.entities if hasattr(node, 'entities') else node.comp.EnumEntities()):
            if type(e) is core.CEdge and visible_entity(e):
                edge_ls.append(e)
        if edge_ls:
            self.add_edges(edge_ls, node.matrix)

    def add_faces(self, face_ls, mtl, node):
        if not face_ls:
            return
        
        # 分类&过滤
        if mtl and mtl.IsOpacity():
            target_dict = self.dict_mats_opacity
        else:
            target_dict = self.dict_mats_normal
            
        if mtl not in target_dict:
            target_dict[mtl] = []
        
        item = face_ls, node
        
        target_dict[mtl].append(item)
    
    def add_edges(self, edge_ls, m ):
        item = edge_ls, m
        self.edge_group_ls.append(item)

    def build(self, gl):
        if self.dirty:
            # Assembly-only definitions have no GPU data. Moving their children
            # must not generate empty uploads or count as a geometry rebuild.
            if (self.nomat_ls or self.dict_mats_normal or self.dict_mats_opacity
                    or self.edge_group_ls or any(self.model_cache.HasGeomtry(p) for p in range(4))):
                self.build_by_cpp()
            self.clear_geom()
            self.dirty = False
    
    def build_by_cpp(self):
        faces = [(entities, node.matrix, None, False)
                 for entities, node in self.nomat_ls]
        for groups in (self.dict_mats_normal, self.dict_mats_opacity):
            for material, entries in groups.items():
                for entities, node in entries:
                    inst = node.get_inst()
                    faces.append((entities, node.matrix, material,
                                  bool(inst and inst.is_image)))
        self.model_cache.build(faces, self.edge_group_ls,
                               getattr(self.model, '_mesh_build_session', None))


class RenderPipeline(core.IChangeListener):
    ##
    def __init__(self, model, view, resource_owner=None):
        super().__init__()
        
        self.model = model
        self.view = view
        self.open_path = []
        self.face_overlay = overlays.FaceOverlayCache()
        self.resource_owner = resource_owner or self
        self.resource_revision = 0
        self.transform_revision = 0
        from .dimension_labels import LabelCache
        self.label_cache = LabelCache()
        self._changed_instances = set()
        self._shadow_pass = None
        self.instance_nodes = []
        self.outer_nodes = []
        if resource_owner is None:
            from .subtree_batches import SubtreeBatches
            self.subtree_batches = SubtreeBatches(self)
        else:
            self.subtree_batches = resource_owner.subtree_batches

        # draw options
        self.is_draw_camera_target = False

        #----------------------#
        # Materials
        self.material_map = {}
        # default Material
        m = RMaterial()
        m.LoadMaterial(None, view.gl)
        self.default_material = m
        self.material_map[None] = m

        #----------------------#
        # ComponentDefinitions
        self.component_map = {}
        if resource_owner is not None:
            self.material_map = resource_owner.material_map
            self.default_material = resource_owner.default_material
            self.component_map = resource_owner.component_map
        
        #----------------------#
        # TopComponent
        self.top_comp = self.model.GetTopComponent()
        
        # draw_mode
        self.use_stencil = False
        self.xray_mode = False
        
    ########################
    # IChangeListener
    #
    ########################
    def ContainerUpdate(self, comp):
        self.mark_comp_dirty(comp)

    def Release(self):
        # Break Python cycles and drop native render caches while the model is alive.
        self._instance_scene = self._outer_scene = self._world_scene = None
        self._scene_key = None
        if self._shadow_pass is not None:
            self._shadow_pass.close()
            self._shadow_pass = None
        if self.resource_owner is self:
            self.subtree_batches.close()
        components = list(self.component_map.values()) if self.resource_owner is self else []
        for component in components:
            if component is not None:
                component.clear_geom()
                component.instances.clear()
                component.model_cache.close()
                component.model_cache = None
                component.comp = None
                component.model = None
        if self.resource_owner is self:
            self.component_map.clear()
            self.material_map.clear()
        self.component_map = {}
        self.material_map = {}
        self.instance_nodes.clear()
        self.outer_nodes.clear()
        self._instance_guides = self._outer_guides = []
        self._section_entities = ()
        self._section_entities_key = None
        self._changed_instances.clear()
        self.default_material = None
        self.open_path.clear()
        self.face_overlay.clear()
        self.top_comp = None
        self.model = None
        self.view = None

    def release_gl_resources(self):
        """Called with this view's context current, before Qt destroys it."""
        self._instance_scene = self._outer_scene = self._world_scene = None
        self._scene_key = None
        if self._shadow_pass is not None:
            self._shadow_pass.close()
        if hasattr(self, 'clear_records'):
            self.clear_records()
            self.invalidate()
        if self.resource_owner is not self:
            return
        self.subtree_batches.close()
        for component in self.component_map.values():
            component.model_cache.close()
        for material in self.material_map.values():
            texture = getattr(material, 'gl_tex_obj', None)
            if texture is not None:
                texture.destroy()
        self.material_map.clear()
        self.default_material = RMaterial()
        self.default_material.LoadMaterial(None, self.view.gl)
        self.material_map[None] = self.default_material
        self.apply_render_change(RenderChange(all_geometry=True))
    
    ########################
    # Load & Save
    #
    ########################
    def get_rt_material(self, m):
        if self.resource_owner is not self:
            return self.resource_owner.get_rt_material(m)
        if m not in self.material_map:
            rm = RMaterial()
            rm.LoadMaterial(m, self.view.gl)
            self.material_map[m] = rm
            return rm
        else:
            return self.material_map[m]

    def sync_material_snapshots(self):
        # Batches retain the same native snapshot object; refresh it before any
        # draw. Transparency changes additionally alter the pass partition.
        if self.resource_owner is not self:
            self.resource_owner.sync_material_snapshots()
            self.default_material = self.resource_owner.default_material
            return
        regroup = []
        for material in self.material_map.values():
            if material.refresh_snapshot():
                regroup.append(material)
        if regroup:
            affected = tuple(component.comp for component in self.component_map.values()
                             if any(component.model_cache.uses_material(m) for m in regroup))
            # Inherited instance materials can change pass membership even when
            # no local mesh directly references the material.
            self.apply_render_change(RenderChange(components=affected, scene=True))
    
    def get_rt_component(self, comp):
        if self.resource_owner is not self:
            return self.resource_owner.get_rt_component(comp)
        if comp not in self.component_map:
            d = RenderComponent(comp, self)
            self.component_map[comp] = d
            return d
        else:
            return self.component_map[comp]

    def render_statistics(self):
        caches = [c.model_cache for c in self.component_map.values()]
        caches.extend(c.model_cache for c in self.subtree_batches.caches.values())
        caches.extend(c.model_cache for r in getattr(self, 'records', []) for c in r.owned_caches)
        values = [cache.statistics() for cache in caches if cache is not None]
        scene = getattr(self, '_world_scene', None)
        native_draws = scene.native.statistics()['draws'] if scene is not None else 0
        return dict(cache_count=len(values),
                    build_count=sum(v['build_count'] for v in values),
                    build_seconds=sum(v['build_seconds'] for v in values),
                    draw_count=sum(v['draw_count'] for v in values) + native_draws,
                    skipped_draw_count=sum(v['skipped_draw_count'] for v in values),
                    selection_mesh_builds=self.face_overlay.mesh_builds)

    def InitRT(self):
        for m in self.model.GetMaterials():
            self.get_rt_material(m)
        
        for comp_def in self.model.GetDefinitionList():
            if comp_def.IsMarkedDeleted():
                continue
            self.get_rt_component(comp_def)
        
        # top comp
        self.top_comp = self.model.GetTopComponent()
       
        # root node
        #self.open_inst = self.get_root()

    def add_new_instance(self, comp_def):
        fac = core.CEntityFactory(self.model)
        inst = fac.NewComponentInstance()
        tm = core.CMatrix()
        tm.SetRow(3, core.CVector3D(0, 0, 0))
        inst.SetTransform(tm)
        inst.SetMaterial(None)
        inst.SetDefinition(comp_def)

        self.model.GetTopComponent().AddEntity(inst)
        return inst

    ########################
    # Recursive
    # 
    ########################
    class InstancePathNode(render_backend.NodeTransform):
        def __init__(self, inst_path, comp, matrix, mtl):
            super().__init__(matrix)
            self.is_top = ( not inst_path )
            self.inst_path = inst_path
            self.comp = comp
            self.matrix = matrix
            self.mtl = mtl
        
        def get_inst(self):
            if self.inst_path:
                return self.inst_path[-1]
            return None

        def has_entities(self):
            return self.comp.GetNumEntities() > self.comp.GetNumChildren()

    def RecursiveRnumInstance(self, inst_path, comp, matrix, mtl):
        node = RenderPipeline.InstancePathNode(inst_path, comp, matrix, mtl)
        yield node
        #
        for inst2 in comp.EnumChildren():
            if not visible_entity(inst2):
                continue
            m2 = matrix.Multiply(inst2.GetTransform().Multiply(inst2.GetAnimationTransform()))
            if inst_path is None:
                inst_path2 = [inst2]
            else:
                inst_path2 = inst_path + [inst2]
            mtl2 = inst2.GetMaterial() or mtl
            n_comp = inst2.GetDefinition()
            yield from self.RecursiveRnumInstance(inst_path2, n_comp, m2, mtl2)

    def world_scene_nodes(self):
        """WorldScene binds native transforms before any consumer reads matrices.

        Snapshot children once per definition during this traversal only. Keep
        the general recursive enumerator unchanged for batching and other users.
        """
        children = {}
        identity = core.CMatrix()
        stack = [(None, self.top_comp, None)]
        while stack:
            path, comp, material = stack.pop()
            yield self.InstancePathNode(path, comp, identity, material)
            if comp not in children:
                children[comp] = [(inst, inst.GetDefinition(), inst.GetMaterial())
                                  for inst in comp.EnumChildren() if visible_entity(inst)]
            for inst, definition, local_material in reversed(children[comp]):
                stack.append(((path or []) + [inst], definition, local_material or material))

    def RecursiveRnumInstance2(self, active_path, inst_path, comp, matrix, mtl):
        #
        if self.compare_instance_path(active_path, inst_path):
            return
        #
        node = RenderPipeline.InstancePathNode(inst_path, comp, matrix, mtl)
        yield node
        #
        for inst2 in comp.EnumChildren():
            if not visible_entity(inst2):
                continue
            m2 = matrix.Multiply(inst2.GetTransform().Multiply(inst2.GetAnimationTransform()))
            if inst_path is None:
                inst_path2 = [inst2]
            else:
                inst_path2 = inst_path + [inst2]
            mtl2 = inst2.GetMaterial() or mtl
            n_comp = inst2.GetDefinition()
            yield from self.RecursiveRnumInstance2(active_path, inst_path2, n_comp, m2, mtl2)

    def compare_instance_path(self, active_path, inst_path ):
        if not inst_path:
            return active_path.Length() == 0
        
        if len(inst_path) != active_path.Length():
            return False
        #
        path_len = len(inst_path)
        for i in range(path_len):
            a = inst_path[i]
            b = active_path.Get(i)
            if a != b:
                return False
        #
        return True;
        
    ########################
    # ViewClip
    #
    ########################
    def ComputeViewClip(self):
        # Extract the six inward planes from the exact clip transform used for
        # drawing. Pick-ray endpoints have an unrelated finite helper length.
        # Projection also accounts for the offscreen aspect ratio when capturing.
        matrix = self.view.ComputeProjectMatrix() * self.view.ComputeCameraMatrix()[0]
        rows = [matrix.row(i) for i in range(4)]
        planes = []
        for axis in range(3):
            for sign in (1, -1):
                row = rows[3] + rows[axis] * sign
                planes.append((row.x(), row.y(), row.z(), row.w()))
        return render_backend.ViewClip.from_equations(planes)

    def ComputePickVolume(self, x, y, width, height):
        
        camera_forward = self.view.GetCameraForward()
        camera_up = self.view.GetCameraUp()
        camera_right = camera_forward.Cross(camera_up)
        camera_right.Normalize()
        
        orig, dir, end = self.view.ComputeCameraRay(x-(width/2), y)
        normal = dir.Cross(camera_up)
        p1 = core.CPlane(normal, orig)
        
        orig, dir, end = self.view.ComputeCameraRay(x+(width/2), y)
        normal = camera_up.Cross(dir)
        p2 = core.CPlane(normal, orig)
        
        orig, dir, end = self.view.ComputeCameraRay(x, y-(height/2))
        normal = dir.Cross(camera_right)
        p3 = core.CPlane(normal, orig)
        
        orig, dir, end = self.view.ComputeCameraRay(x, y+(height/2))
        normal = camera_right.Cross(dir)
        p4 = core.CPlane(normal, orig)

        orig, dir, end = self.view.ComputeCameraRay(x, y)
        p5 = core.CPlane(dir, orig)
        #p6 = plane_from_normal_point(-dir, end)
        
        geomfilter = render_backend.ViewClip(p1, p2, p3, p4, p5)
        
        return geomfilter


    ########################
    # mark_dirty
    #
    ########################
    def mark_dirty(self):
        self.mark_comp_dirty(self.model.GetActiveComponent())
    
    def mark_comp_dirty(self, comp):
        self.mark_components_dirty((comp,))

    def mark_components_dirty(self, components):
        self.apply_render_change(RenderChange(components=tuple(components)))

    def apply_render_change(self, change):
        """One notification per edit; all shared-resource changes go to the owner."""
        if self.resource_owner is not self:
            return self.resource_owner.apply_render_change(change)
        components = set(change.components)
        instances = set(change.instances)
        if change.all_geometry or change.scene:
            self._branch_changes=None
        elif getattr(self,'_branch_changes',set()) is not None:
            pending=getattr(self,'_branch_changes',set())
            pending.update(components)
            self._branch_changes=pending
        split_batch = self.subtree_batches.invalidate(change)
        resources_changed = bool(components or change.all_geometry or change.scene or split_batch)
        if not (resources_changed or instances or change.overlays):
            return
        if resources_changed:
            # Pure face/edge drawing and push previews cannot change label
            # metadata, occurrence hierarchy or instance transforms.
            if not change.local_geometry:
                self.label_revision = getattr(self, 'label_revision', 0) + 1
            old_key = getattr(self, '_scene_key', None)
            resident = getattr(self, '_world_scene', None)
            self.resource_revision += 1
            if change.all_geometry:
                caches = list(self.component_map.values())
            else:
                caches = [self.get_rt_component(comp) for comp in components]
            for cache in caches:
                cache.mark_dirty()
            material_update = (change.material_only and getattr(self.view,'incremental_material_updates',True)
                               and hasattr(render_backend.native.DrawList,'update_materials'))
            if ((change.local_geometry or material_update) and resident is not None and old_key is not None
                    and not change.all_geometry and not change.scene and not instances
                    and not split_batch and old_key[0] == self.resource_revision-1):
                # Local drawing cannot add/remove/reparent component instances.
                # Retain occurrence hierarchy and unaffected descendant caches.
                self._scene_key = (self.resource_revision,) + old_key[1:]
                pending = getattr(self, '_local_geometry_changes', set())
                pending.update(components)
                self._local_geometry_changes = pending
                if material_update:self._pending_material_update = True
            else:
                self._local_geometry_changes = set()
                self._pending_material_update = False
        if instances:
            self.transform_revision += 1
            self._changed_instances.update(instances)
            if self._shadow_pass is not None:
                self._shadow_pass.changed.update(instances)
        self.section_geometry_revision = getattr(self, 'section_geometry_revision', 0) + 1
        if resources_changed or instances:
            observer = getattr(self.view, 'observation', None)
            if observer is not None:
                observer.invalidate()
    
    def mark_outer_path_dirty(self):
        self.apply_render_change(RenderChange(overlays=True))

    def mark_instance_transform_dirty(self, inst):
        self.apply_render_change(RenderChange(instances=(inst,)))
    
    def sync_layer_visibility(self):
        if self.resource_owner is not self:
            return self.resource_owner.sync_layer_visibility()
        layers = list(self.model.GetLayers())
        key = tuple((e.GetID(), e.IsMarkedDeleted(), e.is_hide) for e in layers)
        if key != getattr(self, '_layer_visibility_key', None):
            self._layer_visibility_key = key
            self.apply_render_change(RenderChange(all_geometry=True))

    def check_selection_validity(self):
        #================
        # 安全检查
        # 遇到很多bug是图元删除了
        # Selection还在导致的奔溃
        #================
        for e in self.model.GetSelection():
            if e.IsMarkedDeleted():
                raise RuntimeError(
                    f"当前Selection包含已标记删除的图元：id={e.GetID()}"
                )

    ########################
    # Draw
    #
    ########################
    def draw(self):
        if getattr(self.view, 'loading_model', False):
            return
        self.sync_material_snapshots()
        self.sync_layer_visibility()
        from engine.tools.tool_section import draw_section_frame
        gl = self.view.gl
        active = self.model.GetActiveComponent()
        section_key = (active, self.resource_revision)
        if getattr(self, '_section_entities_key', None) != section_key:
            self._section_entities = tuple(e for e in active.EnumEntities() if isinstance(e, core.CSectionPlane))
            self._section_entities_key = section_key
        sections = [e for e in self._section_entities if visible_entity(e)]
        self.section_limit = int(gl.glGetIntegerv(gl.GL_MAX_CLIP_PLANES))
        active_sections = ([e for e in sections if e.is_active][:self.section_limit]
                           if getattr(self.view,'section_cut_enabled',True) else [])
        self._shadow_allowed = not active_sections
        gl.glPushAttrib(gl.GL_TRANSFORM_BIT | gl.GL_ENABLE_BIT)
        try:
            for index in range(self.section_limit):
                gl.glDisable(gl.GL_CLIP_PLANE0 + index)
            for index, section in enumerate(active_sections):
                plane = transform_plane(active_matrix(self.view),section.plane)
                gl.glClipPlane(gl.GL_CLIP_PLANE0 + index, (plane.x, plane.y, plane.z, plane.w))
                gl.glEnable(gl.GL_CLIP_PLANE0 + index)
            self._draw_model()
            from .human_sections import draw_boundaries
            draw_boundaries(self, active_sections)
            for index in range(self.section_limit):
                gl.glDisable(gl.GL_CLIP_PLANE0 + index)
            selected = {e.GetID() for e in self.model.GetSelection()}
            with local_drawing(self.view,gl):
                for section in (sections if getattr(self.view,'show_section_planes',True) else []):
                    draw_section_frame(gl, section.plane, section.bounds, selected=section.GetID() in selected)
        finally:
            gl.glPopAttrib()

    def _draw_model(self):
        gl = self.view.gl
        view = self.view
        stats=getattr(view,'render_stats',None)
        if stats is not None and not stats.active:stats=None
        shadow_prepare_ms=shadow_receive_ms=0.0
        
        total_st = time.perf_counter()
        self.draw_inst = 0.0
        
        self.check_selection_validity()
        
        # camera
        cam_pos = view.camera.position
        cam_dir = view.camera.forward
        light_pos = cam_pos + cam_dir * -2000
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, (light_pos.x(), light_pos.y(), light_pos.z(), 1.0))
        
        # draw target
        if self.is_draw_camera_target:
            gl.glDisable(gl.GL_TEXTURE_2D)
            target_pos = view.camera.GetTarget()
            self.draw_camera_target(target_pos, gl)
        
        # filter by viewclipo
        st = time.perf_counter()
        viewclip = self.ComputeViewClip()
        time_filter_inst = (time.perf_counter() - st) * 1000
        
        # update
        st = time.perf_counter()
        if stats is not None:stats.stage('update')
        self.update_model_cache(viewclip, gl)
        if stats is not None:stats.stage('shadow')
        if stats is not None:shadow_started=time.perf_counter()
        shadow = self.prepare_shadow()
        if stats is not None:shadow_prepare_ms=(time.perf_counter()-shadow_started)*1000
        time_update = (time.perf_counter() - st) * 1000
        if stats is not None:stats.stage('opaque')
        
        #
        st = time.perf_counter()
        self.SetLighting(True, gl)
        if shadow:
            from .shadows import affine
            world_from_frame = affine(core.CMatrix())
            shadow.set_light(self, world_from_frame)
        self.default_material.Bind()

        # 绘制面
        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
        gl.glPolygonOffset(1.0, 1.0)
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_NORMAL_ARRAY)
        gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)
        
        if not self.xray_mode:
            self.draw_pass(0, viewclip, gl)
        self.draw_pass(1, viewclip, gl)
        if shadow:
            if stats is not None:shadow_started=time.perf_counter()
            if stats is not None:stats.stage('shadow')
            shadow.receive(self, world_from_frame, self.draw_shadow_receivers)
            if stats is not None:shadow_receive_ms=(time.perf_counter()-shadow_started)*1000
            if stats is not None:stats.stage('opaque')
        
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glDisableClientState(gl.GL_NORMAL_ARRAY)
        gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)

        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
        
        self.SetLighting(False, gl)
        gl.glDisable(gl.GL_TEXTURE_2D)
        
        time_draw_pass0 = (time.perf_counter() - st) * 1000

        # 绘制线
        if stats is not None:stats.stage('edges')
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        
        st = time.perf_counter()
        gl.glColor3f(0, 0, 0)
        if not getattr(view,'test_hide_edges',False):
            self.draw_pass(2, viewclip, gl)
        time_draw_pass1 = (time.perf_counter() - st) * 1000
        if stats is not None:selection_started=time.perf_counter()
        if stats is not None:stats.stage('selection')
        
        #==============
        #  绘制Selection
        #==============
        with local_drawing(self.view,gl):
            self.draw_selected(gl)

        #==============
        #  绘制BoundingBox
        #==============
        for e in self.model.GetSelection():
            if type(e) is core.CComponentInstance:
                if not visible_entity(e):continue
                box=e.GetDefinition().GetBoundingBox()
                matrix=active_matrix(self.view).Multiply(e.GetTransform().Multiply(e.GetAnimationTransform()))
                # Selection geometry belongs to the active component; render in world.
                points=[matrix.Transform(core.CVector3D(x,y,z))
                        for x in (box.min_x,box.max_x) for y in (box.min_y,box.max_y)
                        for z in (box.min_z,box.max_z)]
                gl.glPushAttrib(gl.GL_CURRENT_BIT | gl.GL_LINE_BIT | gl.GL_DEPTH_BUFFER_BIT)
                gl.glDisable(gl.GL_DEPTH_TEST)
                gl.glColor3f(0.1,0.55,1.0)
                gl.glLineWidth(2)
                gl.glBegin(gl.GL_LINES)
                for i in range(8):
                    for bit in (1,2,4):
                        j=i^bit
                        if i<j:
                            for p in (points[i],points[j]):gl.glVertex3f(p.x,p.y,p.z)
                gl.glEnd()
                gl.glPopAttrib()
        
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        
        # 绘制半透明的面
        if stats is not None:stats.stage('transparent')
        if stats is not None:selection_ms=(time.perf_counter()-selection_started)*1000
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_NORMAL_ARRAY)
        gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)
        
        st = time.perf_counter()
        gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA)
        #gl.glDepthMask(gl.GL_FALSE)
        gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)

        
        if self.xray_mode:
            gl.glDisable(gl.GL_TEXTURE_2D);
            gl.glColor4f(1, 1, 1, 0.3);
            #gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_DIFFUSE, (1.0, 1.0, 1.0, 0.3));
            self.draw_pass(0, viewclip, gl)
        if not getattr(view,'test_hide_transparent',False):
            self.draw_pass(3, viewclip, gl)
        
        gl.glDisable(gl.GL_BLEND)
        #gl.glDepthMask(gl.GL_TRUE)
        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL)
        
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glDisableClientState(gl.GL_NORMAL_ARRAY)
        gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)
        
        # restore
        self.default_material.Bind()
        time_draw_pass2 = (time.perf_counter() - st) * 1000
        if stats is not None:stats.stage('other')
        
        total_dt = (time.perf_counter() - total_st) * 1000
        if stats is not None:
            stats.phases.update(update=time_update-shadow_prepare_ms,
                                faces=time_draw_pass0-shadow_receive_ms,
                                edges=time_draw_pass1,transparent=time_draw_pass2,
                                shadow=shadow_prepare_ms+shadow_receive_ms,selection=selection_ms)
        add_part = (time_filter_inst + time_draw_pass0 + time_draw_pass1 + time_draw_pass2) / total_dt * 100
        if Print_Time:
            print(f"filter: {time_filter_inst:.2f}, update: {time_update:.2f}, pass0: {time_draw_pass0:.2f}, pass1: {time_draw_pass1:.2f}, pass2: {time_draw_pass2:.2f}, totoal: {total_dt:.2f}, add: {add_part:.2f}")
            print(f"draw time: {self.draw_inst*1000:.2f}")

    def draw_camera_target(self, target, gl):
        #S = self.view.camera_zoom * 0.02
        S = 4
        p = target
        
        gl.glColor3f(1.0, 0.0, 0.0)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(p.x-S, p.y, p.z )
        gl.glVertex3d(p.x+S, p.y, p.z )
        gl.glEnd()
        

        gl.glColor3f(0.0, 1.0, 0.0)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(p.x,  p.y-S,  p.z )
        gl.glVertex3d(p.x,  p.y+S,  p.z )
        gl.glEnd()
        
        gl.glColor3f(0.0, 0.0, 1.0)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3d(p.x,  p.y,  p.z  )
        gl.glVertex3d(p.x,  p.y,  p.z+S*4 )
        gl.glEnd()
        
        pt = core.CVector3D(target.x, target.y, target.z)
        pt.z +=  S*4 + S*0.5
        overlays.draw_diamond(gl, pt, S * 0.5)

    
    def update_model_cache(self, view_clip, gl, warm_only=False):
        started = time.perf_counter()
        timings = dict(enumerate_ms=0.0, tree_ms=0.0, context_ms=0.0)
        path = self.model.GetActiveComponentPath()
        path_key = tuple(path.Get(i).GetID() for i in range(path.Length()))
        key = (self.resource_revision, getattr(self.view, 'subtree_batching', True),
               getattr(self.view, 'mixed_subtree_batching', True),
               getattr(self.view, 'batch_min_scene_nodes', 1024),
               getattr(self.view, 'python_scene_fast_path', True))
        if key != getattr(self, '_scene_key', None):
            stamp = time.perf_counter()
            previous=getattr(self,'_world_scene',None)
            old_key=getattr(self,'_scene_key',None)
            changes=getattr(self,'_branch_changes',None)
            reuse=(previous if previous is not None and old_key is not None
                   and key[1:]==old_key[1:] and changes is not None
                   and getattr(self.view,'incremental_scene_branches',True)
                   and getattr(self.view,'python_scene_fast_path',True)
                   and not self._changed_instances else None)
            nodes = (reuse.changed_branch_nodes(self,changes) if reuse is not None else
                     list(self.world_scene_nodes() if getattr(self.view, 'python_scene_fast_path', True)
                          else self.RecursiveRnumInstance(None, self.top_comp, core.CMatrix(), None)))
            timings['enumerate_ms'] = (time.perf_counter()-stamp)*1000
            stamp = time.perf_counter()
            self._world_scene = render_backend.WorldScene(self, nodes,reuse=reuse)
            self.branch_reused_nodes=getattr(reuse,'branch_reused_nodes',0)
            self._branch_changes=set()
            self._instance_scene = self._world_scene.inner
            self._outer_scene = self._world_scene.outer
            self._changed_instances.clear()
            self._scene_key = key
            self.scene_rebuilds = getattr(self, 'scene_rebuilds', 0) + 1
            timings['tree_ms'] = (time.perf_counter()-stamp)*1000
        scene = self._world_scene
        if getattr(self, '_pending_material_update', False):
            scene.refresh_materials(self)
            self._pending_material_update = False
        local_changes = getattr(self, '_local_geometry_changes', set())
        if local_changes:
            scene.refresh_local_geometry(self, local_changes)
            self._local_geometry_changes = set()
        if self._changed_instances:
            editing_components={self.model.GetTopComponent(), self.model.GetActiveComponent()}
            editing_components.update(path.Get(i).GetDefinition() for i in range(path.Length()))
            scene.update_instances(self._changed_instances, skip_bounds=editing_components)
            self._changed_instances.clear()
        stamp = time.perf_counter()
        scene.set_context(self, path_key)
        timings['context_ms'] = (time.perf_counter()-stamp)*1000
        scene.select(self.model.GetSelection())
        if warm_only:
            scene.last_geometry_ms = scene.last_cull_ms = 0.0
        else:
            scene.cull(view_clip.planes, self)
        stamp = time.perf_counter()
        self.ensure_component(self.model.GetActiveComponent())
        timings['geometry_ms'] = scene.last_geometry_ms + (time.perf_counter()-stamp)*1000
        timings['cull_ms'] = scene.last_cull_ms
        timings['total_ms'] = (time.perf_counter()-started)*1000
        self.cache_timings = timings

    def scene_statistics(self):
        return dict(timings=getattr(self, 'cache_timings', {}),
                    batches=self.subtree_batches.statistics(),
                    rebuilds=getattr(self, 'scene_rebuilds', 0),
                    branch_reused_nodes=getattr(self, 'branch_reused_nodes', 0),
                    instances=self._instance_scene.native.statistics() if getattr(self, '_instance_scene', None) else {},
                    outer=self._outer_scene.native.statistics() if getattr(self, '_outer_scene', None) else {})

    def shadow_pass(self):
        owner = self.resource_owner
        if owner._shadow_pass is None:
            from .shadows import ShadowPass
            owner._shadow_pass = ShadowPass(owner)
        return owner._shadow_pass

    def shadow_statistics(self):
        shadow = self.resource_owner._shadow_pass
        return dict(enabled=getattr(self.view,'shadows_enabled',False),
                    resolution=getattr(self.view,'shadow_resolution',2048),
                    map_updates=shadow.native.updates if shadow else 0,
                    light_nodes=len(shadow.scene.nodes) if shadow and shadow.scene else 0)

    def prepare_shadow(self):
        if getattr(self.view,'test_disable_shadows',False):return None
        if (not getattr(self.view, 'shadows_enabled', False) or self.xray_mode
                or not getattr(self, '_shadow_allowed', True)):
            return None
        shadow = self.shadow_pass()
        return shadow if shadow.prepare() else None

    def draw_shadow_receivers(self):
        gl = self.view.gl
        with local_drawing(self.view,gl):
            self.get_rt_component(self.model.GetActiveComponent()).model_cache._cache.draw_opaque(True)
        self._instance_scene.native.draw_opaque(False)
        self._outer_scene.native.draw_opaque(False)

    def ensure_component(self, comp):
        component = self.get_rt_component(comp)
        if component.dirty:
            session = getattr(self, '_component_build_session', None)
            if (session is not None and (comp.GetNumEdges() or comp.GetNumFaces())
                    and component.model_cache.build_component(comp, session, self._build_materials)):
                component.clear_geom()
                component.dirty = False
                return component
            component.clear_geom()
            component.add_node(self.InstancePathNode(None, comp, core.CMatrix(), None))
            component.build(self.view.gl)
        return component

    def initial_geometry(self, comp):
        """Startup-only classification; occurrence transforms/materials stay separate."""
        if comp not in self._initial_geometry:
            groups, edges = {}, []
            for entity in comp.EnumEntities():
                if type(entity) is core.CFace and visible_entity(entity):
                    groups.setdefault(entity.GetMaterial(), []).append(entity)
                elif type(entity) is core.CEdge and visible_entity(entity):
                    edges.append(entity)
            self._initial_geometry[comp] = groups, edges
        return self._initial_geometry[comp]

    def initialize_geometry(self, progress):
        """Warm every reachable definition once, regardless of camera visibility."""
        report_progress = progress
        def progress(*args):
            # Qt event processing/repainting can leave another widget's context
            # current. All subsequent mesh uploads must belong to this view.
            try:
                report_progress(*args)
            finally:
                self.view.makeCurrent()
        ordered=[];seen=set()
        def visit(comp):
            if comp.GetID() in seen:return
            seen.add(comp.GetID())
            for entity in comp.EnumChildren():
                visit(entity.GetDefinition())
            ordered.append(comp)
        visit(self.model.GetTopComponent())
        self.view.makeCurrent()
        self._initial_geometry = {} if getattr(self.view, 'reuse_initial_geometry', True) else None
        try:
            self._mesh_build_session = None
            self.sync_material_snapshots()
            self.sync_layer_visibility()
            self._build_materials = {m.GetID(): rm for m, rm in self.material_map.items() if m is not None}
            self._component_build_session = (render_backend.native.ComponentBuildSession(
                [(core.core.borrow_entity(m), rm._native) for m, rm in self.material_map.items() if m is not None])
                if getattr(self.view, 'native_component_build', True) else None)
            for index, comp in enumerate(ordered):
                for entity in comp.EnumChildren():
                    self.get_rt_material(entity.GetMaterial())
                comp.ComputeBoundingBox()
                # MeshCache invokes native ComputeMesh and retains its result;
                # computing a separate temporary mesh here would discard it.
                self.ensure_component(comp)
                progress('初始化几何', index+1, len(ordered))
            progress('构建场景绘制树', 0, 0)
            self._component_build_session = None
            # Use the same persistent scene/key as normal drawing, otherwise
            # the first frame would throw away the warmed hierarchy.
            self.update_model_cache(None, self.view.gl, warm_only=True)
            # Spend the bounded mesh budget on repeated batch geometry rather
            # than filling it with definitions visited only once during warmup.
            self._mesh_build_session = (render_backend.native.MeshBuildSession()
                                       if getattr(self.view, 'reuse_initial_meshes', True) else None)
            self._world_scene.initialize_all(self, progress)
            progress('提交显示缓存', 0, 0)
            self.view.gl.glFinish()
        finally:
            self._component_build_session = None
            self._build_materials = None
            session = getattr(self, '_mesh_build_session', None)
            self.initial_mesh_statistics = (dict(hits=session.hits, misses=session.misses,
                                                 estimated_bytes=session.estimated_bytes)
                                            if session is not None else {})
            self._mesh_build_session = None
            session = None  # Also release when an exception traceback retains this frame.
            # Never retain entity wrappers across edits, deletion, or undo.
            self._initial_geometry = None
            self.view.doneCurrent()

    def prepare_node(self, node, component=None):
        node.model_cache = (component or self.ensure_component(node.comp)).model_cache
        node.material = self.get_rt_material(node.mtl)
        from .matrices import gl_matrix
        node.gl_matrix = gl_matrix(node.matrix)
        node.mirror = self.test_mirror(node.matrix)

    def draw_node(self, node, ipass, gl, parent_mirror=False):
        # Inherited material belongs to an occurrence, not its shared VBO.
        inst = node.get_inst()
        if ipass == 2 and inst is not None and inst.is_image:
            return
        inherited_transparent = node.material.IsOpacity()
        passes = ([0, 3] if inherited_transparent else [3]) if ipass == 3 else [ipass]
        if ipass == 0 and inherited_transparent:
            return
        if not any(node.model_cache.HasGeomtry(p) for p in passes):
            for p in passes:
                node.model_cache.Draw(p)  # Account for skipped submissions.
            return
        gl.glPushAttrib(gl.GL_POLYGON_BIT)
        gl.glPushMatrix()
        try:
            gl.glMultMatrixd(node.gl_matrix)
            gl.glFrontFace(gl.GL_CW if node.mirror != parent_mirror else gl.GL_CCW)
            for p in passes:
                if p == 0:
                    node.material.Bind()
                    if ipass == 0 and getattr(self, 'xray_mode', False):
                        gl.glDisable(gl.GL_TEXTURE_2D)
                        gl.glColor4f(1, 1, 1, .3)
                node.model_cache.Draw(p)
        finally:
            gl.glPopMatrix()
            gl.glPopAttrib()
    
    def SetLighting(self, on_off, gl):
        #gl.glEnable(gl.GL_AUTO_NORMAL)
        #gl.glEnable(gl.GL_CULL_FACE)
        #gl.glFrontFace(gl.GL_CCW)

        if on_off:
            gl.glEnable(gl.GL_NORMALIZE)
            gl.glEnable(gl.GL_LIGHTING)
            gl.glEnable(gl.GL_LIGHT0)
            gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, (0.6, 0.6, 0.6, 1.0))
            gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, (0.3, 0.3, 0.3, 1.0))
            gl.glLightModeli(gl.GL_LIGHT_MODEL_TWO_SIDE, gl.GL_TRUE)
            gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0) )       
            gl.glMaterialfv(gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT, (1.0, 1.0, 1.0, 1.0) )       
        else:
            gl.glDisable(gl.GL_NORMALIZE)
            gl.glDisable(gl.GL_LIGHTING)
            gl.glDisable(gl.GL_LIGHT0)

    
    def draw_pass(self, ipass, viewclip, gl):
        if self.model.GetActivePathLength() > 0:
            self.draw_outer_part(ipass, gl)
        with local_drawing(self.view,gl):
            self.draw_active_comp(self.model.GetActiveComponent(), ipass, gl)
        self.draw_insts(ipass, gl)
        if ipass == 2:
            self.draw_node_guides(self._instance_guides, gl)

    def draw_insts(self, ipass, gl):
        self._instance_scene.native.draw(ipass, False, False, self.xray_mode)

    def test_mirror(self, m):
        xaxis = m.GetAxis(0)
        yaxis = m.GetAxis(1)
        zaxis = m.GetAxis(2)
        
        dir = xaxis.Cross(yaxis)
        if dir.Dot(zaxis) < 0.0:
            return True
        
        return False

    def draw_outer_part(self, ipass, gl):
        self._outer_scene.native.draw(ipass, False, True, self.xray_mode)
        if ipass == 2:
            # Every instance occurrence already has its world model matrix.
            self.draw_node_guides(self._outer_guides, gl)

    def draw_node_guides(self, nodes, gl):
        if not getattr(self.view, "show_guides", True):return
        for node in nodes:
            if not self.guide_lines(node.comp):
                continue
            values = render_backend.affine12(node.matrix)
            matrix = [values[r*3+c] if r < 3 else 0.0
                      for c in range(3) for r in range(4)] + values[9:] + [1.0]
            gl.glPushMatrix()
            try:
                gl.glMultMatrixd(matrix)
                self.draw_guides(node.comp, gl)
            finally:
                gl.glPopMatrix()

    def guide_lines(self, comp):
        # Native direct-entity count avoids enumeration even on a cold cache.
        if not comp.HasGuideLine():
            return ()
        cache = self.get_rt_component(comp)
        revision = getattr(cache, 'section_geometry_revision', 0)
        if getattr(cache, '_guide_revision', None) != revision:
            cache._guide_lines = tuple((tuple(e.orig.ToTuple()), tuple(e.dir.ToTuple()))
                for e in comp.EnumEntities() if isinstance(e, core.CGuideLine) and visible_entity(e))
            cache._guide_revision = revision
        return cache._guide_lines

    def draw_active_comp(self, comp, ipass, gl):
        #
        comp_d = self.get_rt_component(comp)
        mc = comp_d.model_cache
        
        if ipass == 2:
            gl.glColor3f(0, 0, 0)
        
        st = time.perf_counter()
        if ipass == 0 and not self.xray_mode:
            self.default_material.Bind()
        mc.Draw(ipass)
        self.draw_inst += time.perf_counter() - st

        #==============
        #  绘制辅助线
        #==============
        if ipass == 2:
            self.draw_guides(comp, gl)

    def draw_guides(self, comp, gl):
        if not getattr(self.view, "show_guides", True):return
        guides = self.guide_lines(comp)
        if not guides:
            return
        gl.glPushAttrib(gl.GL_ENABLE_BIT | gl.GL_LINE_BIT | gl.GL_CURRENT_BIT)
        try:
            gl.glColor3f(0, 0, 0)
            gl.glLineStipple(1, 0x0707)
            gl.glEnable(gl.GL_LINE_STIPPLE)
            for origin, direction in guides:
                overlays.draw_guide(gl, core.CVector3D(*origin), core.CVector3D(*direction), 2000)
        finally:
            gl.glPopAttrib()

    def draw_selected(self, gl):
        # Face
        if self.use_stencil:
            self.draw_face_selected_stencil(gl)
        else:
            self.draw_face_selected(gl)
        
        # Edge
        self.draw_edges_selected(gl)
        
        # Guide
        self.draw_guide_line_selected(gl)
    
    def draw_overlay_faces(self, gl, faces):
        comp = self.model.GetActiveComponent()
        cache = self.get_rt_component(comp)
        revision = (comp.GetID(), getattr(cache, 'section_geometry_revision', 0),
                    getattr(self, 'section_geometry_revision', 0))
        self.face_overlay.draw(gl, faces, revision)

    def draw_face_selected(self, gl):
        self.draw_face_selection(gl, stencil=False)

    def draw_face_selected_stencil(self, gl):
        self.draw_face_selection(gl, stencil=True)

    def draw_face_selection(self, gl, stencil=False):
        faces = [e for e in self.model.GetSelection()
                 if type(e) is core.CFace and visible_entity(e)]
        if not faces:
            return
        gl.glPushAttrib(gl.GL_ENABLE_BIT | gl.GL_CURRENT_BIT | gl.GL_POLYGON_BIT |
                        gl.GL_DEPTH_BUFFER_BIT | gl.GL_COLOR_BUFFER_BIT | gl.GL_STENCIL_BUFFER_BIT)
        try:
            gl.glDisable(gl.GL_TEXTURE_2D)
            gl.glEnable(gl.GL_DEPTH_TEST)
            gl.glDepthFunc(gl.GL_LEQUAL)
            gl.glDepthMask(False)
            # The base face uses (+1,+1). Reusing that depth bias makes the
            # CPU overlay compete with the native mesh at rounding boundaries.
            gl.glEnable(gl.GL_POLYGON_OFFSET_FILL)
            gl.glPolygonOffset(-1., -1.)
            if stencil:
                gl.glEnable(gl.GL_STENCIL_TEST)
                gl.glStencilFunc(gl.GL_EQUAL, 1, 0xFF)
                gl.glColor3f(0, 0, 1)
            else:
                gl.glEnable(gl.GL_BLEND)
                gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
                gl.glColor4f(0.43, 0.57, 0.74, 0.3)
            self.draw_overlay_faces(gl, faces)
        finally:
            gl.glPopAttrib()

    def draw_edges_selected(self, gl):
        selection = self.model.GetSelection()
        
        gl.glLineWidth(2)
        gl.glColor3f(0, 0, 1)
        gl.glBegin(gl.GL_LINES)
        for e in filter(lambda e:type(e) is core.CEdge and visible_entity(e), selection):
            v1 = e.GetStartVertex()
            v2 = e.GetEndVertex()
            gl.glVertex3f(v1.p.x, v1.p.y, v1.p.z )
            gl.glVertex3f(v2.p.x, v2.p.y, v2.p.z )
        gl.glEnd()
        gl.glLineWidth(1)

    ########################
    # draw_guide_lines_selected
    # 绘制辅助线
    ########################
    def draw_guide_line_selected(self, gl):
        selection = self.model.GetSelection()
        
        # Stripple
        stipple = 0x0707
        gl.glLineStipple(1, stipple)
        gl.glEnable(gl.GL_LINE_STIPPLE)
        #
        gl.glLineWidth(2)
        gl.glColor3f(0.0, 0.0, 1.0)
        for e in filter(lambda e:type(e) is core.CGuideLine and visible_entity(e), selection):
            overlays.draw_guide(gl, e.orig, e.dir, 2000)
        gl.glLineWidth(1)
        gl.glDisable(gl.GL_LINE_STIPPLE)

