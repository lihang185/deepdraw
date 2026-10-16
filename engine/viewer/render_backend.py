"""Scene-to-render boundary. The independent renderer is required."""
import importlib
from time import perf_counter
from engine import core

try:
    native = importlib.import_module('deepdraw_render')
except ImportError as error:
    raise ImportError('Install the matching deepdraw_render.pyd in engine/native/cp38') from error
if native.API_VERSION != 1 or not hasattr(core.core, 'borrow_entity'):
    raise ImportError('Renderer API version 1 and editor2.borrow_entity are required')
if not hasattr(native, 'DrawList') or not hasattr(native.DrawList, 'set_edit_context'):
    raise ImportError('Rebuild and install deepdraw_render.pyd with persistent editing context support')
if not hasattr(native, 'ComponentBuildSession'):
    raise ImportError('Install the updated deepdraw_render.pyd with ComponentBuildSession support and restart the client')
NAME = 'independent'


class NodeTransform:
    """Lazy Python view of a native world transform; overlays read only what they use."""
    def __init__(self, matrix):
        self._matrix = matrix
        self._transform_source = None
        self._transform_revision = -1
        self._gl_matrix = None
        self._mirror = False

    def bind_transform(self, source, index):
        self._transform_source = source
        self._transform_index = index
        self._transform_revision = -1

    def _sync_transform(self):
        source = self._transform_source
        if source is None or self._transform_revision == source.transform_revision:
            return
        values = source.world_matrix(self._transform_index)
        matrix = core.CMatrix()
        for c in range(3):
            matrix.SetAxis(c, core.CVector3D(values[c], values[3+c], values[6+c]))
        matrix.SetRow(3, core.CVector3D(*values[9:]))
        self._matrix = matrix
        self._gl_matrix = [values[r*3+c] if r<3 else 0 for c in range(3) for r in range(4)] + values[9:] + [1]
        a,b,c,d,e,f,g,h,i = values[:9]
        self._mirror = a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g) < 0
        self._transform_revision = source.transform_revision

    @property
    def matrix(self):
        self._sync_transform()
        return self._matrix

    @matrix.setter
    def matrix(self, value):
        self._matrix = value
        self._transform_source = None

    @property
    def gl_matrix(self):
        self._sync_transform()
        return self._gl_matrix

    @gl_matrix.setter
    def gl_matrix(self, value):
        self._gl_matrix = value

    @property
    def mirror(self):
        self._sync_transform()
        return self._mirror

    @mirror.setter
    def mirror(self, value):
        self._mirror = value


class SceneDrawList:
    """Python publishes edits; native hierarchy propagates transforms and bounds."""
    def __init__(self, pipeline, nodes, root_matrix=None, compact=True, reuse=None):
        self.root_matrix = root_matrix or core.CMatrix()
        self.native = native.DrawList()
        self.raw_nodes = nodes
        self.definition_parents = {}
        self.instances = set()
        raw_paths, local_matrices, bounds = {}, {}, {}
        old_snapshots=getattr(reuse,'build_snapshots',{})
        self.build_snapshots={}
        reuse_paths = not compact and getattr(pipeline.view, 'python_scene_fast_path', True)
        node_paths = ([old_snapshots[node][0] if node in old_snapshots else
                       tuple(inst.GetID() for inst in (node.inst_path or [])) for node in nodes]
                      if reuse_paths else None)
        hierarchy = []
        active_path=pipeline.model.GetActiveComponentPath()
        active_ids=tuple(active_path.Get(i).GetID() for i in range(active_path.Length()))
        needs_bounds=set()
        for index, node in enumerate(nodes):
            ids=node_paths[index] if reuse_paths else tuple(i.GetID() for i in (node.inst_path or []))
            if active_ids[:len(ids)]!=ids:needs_bounds.add(node.comp)
        for index, node in enumerate(nodes):
            path = node_paths[index] if reuse_paths else tuple(inst.GetID() for inst in (node.inst_path or []))
            parent = raw_paths.get(path[:-1], -1) if path else -1
            raw_paths[path] = index
            inst = node.get_inst()
            previous=old_snapshots.get(node)
            if inst is not None:
                self.instances.add(inst)
                if inst not in local_matrices:
                    local_matrices[inst] = (previous[1] if previous else
                        affine12(inst.GetTransform().Multiply(inst.GetAnimationTransform())))
                local = local_matrices[inst]
            else:
                local = affine12(core.CMatrix())
            if node.comp not in bounds:
                bounds[node.comp] = (component_bounds(node.comp) if compact or node.comp in needs_bounds
                                     else (1,-1,1,-1,1,-1))
            if parent >= 0:
                self.definition_parents.setdefault(node.comp, set()).add(nodes[parent].comp)
            hierarchy.append((parent, inst.GetID() if inst is not None else -1,
                              node.comp.GetID(), local, bounds[node.comp]))
            self.build_snapshots[node]=(path,local)
        owner = pipeline.resource_owner
        if compact and getattr(pipeline.view, 'subtree_batching', True):
            nodes = owner.subtree_batches.compact(nodes)
        self.nodes = nodes
        self.pending = {}
        rows, paths, mapping, pending_indices = [], {}, [], []
        identity = (1,0,0,0,1,0,0,0,1,0,0,0)
        for index, node in enumerate(nodes):
            component = getattr(node, 'batch_component', None) or pipeline.get_rt_component(node.comp)
            if compact:
                pipeline.prepare_node(node, component)
                m = node.gl_matrix
                affine = [m[c*4+r] for r in range(3) for c in range(3)] + m[12:15]
            else:
                # set_hierarchy computes the final world transform natively.
                node.model_cache = component.model_cache
                node.material = pipeline.get_rt_material(node.mtl)
                affine = identity
            if component.dirty:
                self.pending[component] = node
                pending_indices.append(index)
            path = node_paths[index] if reuse_paths else tuple(inst.GetID() for inst in (node.inst_path or []))
            parent = paths.get(path[:-1], -1) if path else -1
            paths[path] = index
            inst = node.get_inst()
            rows.append((node.model_cache._cache, node.material._native, affine,
                         bounds[node.comp], parent, path[0] if path else -1, bool(inst and inst.is_image)))
            mapping.append(raw_paths[path])
        self.bounds = bounds
        self.native.set(rows)
        self.native.set_hierarchy(hierarchy, mapping, affine12(self.root_matrix))
        self.native.set_pending(pending_indices, True)
        for index, node in enumerate(self.raw_nodes):
            node.bind_transform(self.native, index)
        if not reuse_paths:
            for node, index in zip(nodes, mapping):
                node.bind_transform(self.native, index)
        self.raw_paths = raw_paths
        self.parents = [row[0] for row in hierarchy]
        self.selection_key = None

    def update_instances(self, changed, skip_bounds=()):
        changed = self.instances.intersection(changed)
        if not changed:
            return
        self.build_snapshots={}
        # Engine bounds include descendants. Refresh unique ancestor definitions,
        # not every occurrence; C++ handles all occurrence transforms and refits.
        definitions = set()
        pending = [inst.GetDefinition() for inst in changed]
        for inst in changed:
            parent = inst.GetParentComponent()
            if parent is not None:
                pending.append(parent)
        while pending:
            comp = pending.pop()
            if comp in definitions:
                continue
            definitions.add(comp)
            pending.extend(self.definition_parents.get(comp, ()))
        bound_changes = []
        snapshots = {}
        for comp in definitions:
            if comp not in self.bounds or comp in skip_bounds:
                continue
            box = component_bounds(comp)
            snapshots[comp] = box
            if box != self.bounds[comp]:
                bound_changes.append((comp.GetID(), box))
        self.native.update_instances(
            [(inst.GetID(), affine12(inst.GetTransform().Multiply(inst.GetAnimationTransform()))) for inst in changed],
            bound_changes)
        self.bounds.update(snapshots)

    def cull(self, planes, pipeline):
        self.native.cull(planes)
        if self.pending:
            visible_pending = self.native.visible_pending()
            for index in visible_pending:
                node = self.nodes[index]
                component = getattr(node, 'batch_component', None) or pipeline.get_rt_component(node.comp)
                if component in self.pending:
                    if hasattr(node, 'batch_component'):
                        pipeline.resource_owner.subtree_batches.ensure(component)
                    else:
                        pipeline.ensure_component(node.comp)
                    del self.pending[component]
            self.native.set_pending(visible_pending, False)

    def select(self, selection):
        key = tuple(sorted(e.GetID() for e in selection))
        if key != self.selection_key:
            self.native.set_selection(key)
            selected = set(key)
            for node in self.nodes:
                node.is_selected = bool(node.inst_path and node.inst_path[0].GetID() in selected)
            self.selection_key = key


def component_bounds(comp):
    box = comp.GetBoundingBox()
    return (box.min_x, box.max_x, box.min_y, box.max_y, box.min_z, box.max_z)


def affine12(matrix):
    # Evaluate the transform instead of copying cached native matrix flags.
    # This includes native scale and fixes the translation/row convention.
    zero = matrix.Transform(core.CVector3D(0, 0, 0))
    axes = [matrix.Transform(core.CVector3D(*axis)) for axis in
            ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    x,y,z=axes
    ox,oy,oz=zero.x,zero.y,zero.z
    return [x.x-ox,y.x-ox,z.x-ox,x.y-oy,y.y-oy,z.y-oy,
            x.z-oz,y.z-oz,z.z-oz,ox,oy,oz]


def material_values(material):
    m = material.m
    texture = m.GetTexture() if m is not None else None
    color = m.color if m is not None else None
    return (material.type,
            (color.x, color.y, color.z) if color is not None else (1, 1, 1),
            bool(m.use_opacity) if m is not None else False,
            float(m.opacity) if m is not None else 1.0,
            material.gl_tex,
            (texture.size_u, texture.size_v) if texture is not None else (1, 1))


def material_snapshot(material):
    """Qt texture ownership stays with RMaterial; the DLL copies numeric state."""
    return native.Material(*material_values(material))


class MeshCache:
    def __init__(self):
        self._cache = native.MeshCache()
        self._materials = []
        self._passes = (False,) * 4
        self.build_count = 0
        self.build_seconds = 0.0
        self.draw_count = 0
        self.skipped_draw_count = 0

    def build(self, faces, edges, session=None):
        # faces: [(entities, native_matrix, RMaterial or None, is_image)]
        # edges: [(entities, native_matrix)]
        materials = [m for _, _, m, _ in faces if m is not None]
        borrow = core.core.borrow_entity
        started = perf_counter()
        self._cache.build(
            [([borrow(e) for e in entities], affine12(matrix),
              m._native if m is not None else None)
             for entities, matrix, m, _ in faces],
            [([borrow(e) for e in entities], affine12(matrix))
             for entities, matrix in edges], session)
        # Retain Qt texture owners as long as GPU batches reference their IDs.
        self._materials = materials
        self._passes = tuple(self._cache.has_geometry(p) for p in range(4))
        self.build_count += 1
        self.build_seconds += perf_counter() - started

    def build_component(self, comp, session, materials):
        started = perf_counter()
        identifiers = self._cache.build_component(core.core.borrow_entity(comp), session)
        if identifiers is None:
            return False
        self._materials = [materials[i] for i in identifiers]
        self._passes = tuple(self._cache.has_geometry(p) for p in range(4))
        self.build_count += 1
        self.build_seconds += perf_counter() - started
        return True

    def Draw(self, pass_index):
        if not 0 <= pass_index < 4:
            raise ValueError('pass must be in [0, 3]')
        if self._passes[pass_index]:
            self._cache.draw(pass_index)
            self.draw_count += 1
        else:
            self.skipped_draw_count += 1

    def HasGeomtry(self, pass_index):
        if not 0 <= pass_index < 4:
            raise ValueError('pass must be in [0, 3]')
        return self._passes[pass_index]

    def close(self):
        self._cache.close()
        self._materials = []
        self._passes = (False,) * 4

    def uses_material(self, material):
        return material in self._materials

    def statistics(self):
        return dict(build_count=self.build_count, build_seconds=self.build_seconds,
                    draw_count=self.draw_count, skipped_draw_count=self.skipped_draw_count)


def init_opengl():
    native.init_opengl()


class ViewClip:
    def __init__(self, *planes):
        self.planes = [tuple(getattr(p, k) for k in ('x', 'y', 'z', 'w')) for p in planes]

    @classmethod
    def from_equations(cls, planes):
        result = cls()
        result.planes = [tuple(plane) for plane in planes]
        return result

    def SetFarClip(self, plane):
        self.planes = self.planes[:5] + [tuple(getattr(plane, k) for k in ('x', 'y', 'z', 'w'))]

    def filter_instances(self, instances):
        bounds, transforms = [], []
        for inst in instances:
            box = inst.GetDefinition().GetBoundingBox()
            bounds.append((box.min_x, box.max_x, box.min_y, box.max_y, box.min_z, box.max_z))
            transforms.append(affine12(inst.GetTransform().Multiply(inst.GetAnimationTransform())))
        return [instances[i] for i in native.filter_bounds(self.planes, bounds, transforms)]

class NodeRange:
    """Non-copying diagnostic view of occurrences in the current editing scope."""
    def __init__(self, scene, ranges):
        self.scene, self.ranges = scene, ranges
    def __len__(self):
        return sum(end-start for start,end in self.ranges)
    def __iter__(self):
        scene = self.scene
        for start,end in self.ranges:
            for i in range(start,end):
                node = scene.raw_nodes[i]
                path = node.inst_path or []
                depth = len(scene.context_path)
                node.is_selected = (len(path)>depth and path[depth].GetID() in scene.selected_ids
                                    and tuple(e.GetID() for e in path[:depth])==scene.context_path)
                yield node
    def __getitem__(self, index):
        if index<0:index+=len(self)
        if index<0 or index>=len(self):raise IndexError(index)
        for start,end in self.ranges:
            if index<end-start:return self.scene.raw_nodes[start+index]
            index-=end-start
        raise IndexError(index)
    def clear(self):
        self.ranges=()
        self.scene=None


class SceneScope:
    """Two draw scopes backed by one persistent native tree."""
    def __init__(self, scene, part):
        import weakref
        self.scene, self.part = weakref.proxy(scene), part
    @property
    def native(self):
        return self
    @property
    def nodes(self):
        return [self.scene.raw_nodes[i] for i in self.scene.native.enabled_indices(self.part)]
    def statistics(self):
        return self.scene.native.statistics(self.part)
    def visible_indices(self):
        return self.scene.native.visible_indices(self.part)
    def draw(self, ipass, mirror, outer, xray):
        self.scene.native.draw(ipass,mirror,self.part==1,xray)
    def draw_opaque(self, mirror):
        self.scene.native.draw_opaque(mirror,self.part)
    def update_instances(self, changed):
        self.scene.update_instances(changed)


class WorldScene(SceneDrawList):
    """Keep all occurrences resident across component navigation."""
    def __init__(self, pipeline, nodes, reuse=None):
        super().__init__(pipeline,nodes,compact=False,reuse=reuse)
        self.paths=self.raw_paths
        self.ends=list(range(1,len(nodes)+1))
        for path,i in reversed(list(self.paths.items())):
            if path:
                parent=self.paths[path[:-1]]
                self.ends[parent]=max(self.ends[parent],self.ends[i])
        self.guides=[(i,n) for i,n in enumerate(nodes) if n.comp.HasGuideLine()]
        self.guide_components={n.comp for _,n in self.guides}
        self.batch_nodes={}
        self.partial_batches=set()
        self.context_path=None
        self.selected_ids=set()
        owner=pipeline.resource_owner
        from .subtree_batches import MIN_SCENE_NODES
        batching=(getattr(pipeline.view,'subtree_batching',True) and
                  len(nodes)-1>=getattr(pipeline.view,'batch_min_scene_nodes',MIN_SCENE_NODES))
        rows=[]
        # A definition's child instances recur under every shared occurrence.
        # Snapshot their policy once per build, with inherited opacity in the
        # key because it affects candidate eligibility in the reference mode.
        instance_data={}
        candidates={}
        self.batch_snapshots={}
        old_batches=getattr(reuse,'batch_snapshots',{})
        if reuse is not None and batching != getattr(reuse,'batching_enabled',False):old_batches={}
        self.batching_enabled=batching
        for i,node in enumerate(nodes):
            if node in old_batches:
                batch,row=old_batches[node]
                if batch is not None:self.batch_nodes[i]=batch
                if row[4]:self.partial_batches.add(i)
                # Pending flags can change after the previous frame warmed VBOs.
                row=row[:3]+(bool(batch is not None and batch.dirty),row[4])
                rows.append(row);self.batch_snapshots[node]=(batch,row)
                continue
            inst=node.get_inst()
            if inst not in instance_data:
                material=inst.GetMaterial() if inst is not None else None
                instance_data[inst]=(inst.GetID() if inst is not None else -1,
                    pipeline.get_rt_material(material)._native if material is not None else None)
            ident,local_material=instance_data[inst]
            opacity=bool(node.mtl is not None and node.mtl.use_opacity)
            key=(inst,opacity)
            if key not in candidates:
                candidates[key]=owner.subtree_batches.candidate(node) if batching else None
            batch=candidates[key]
            if batch is not None:self.batch_nodes[i]=batch
            partial=bool(batch is not None and (owner.subtree_batches.transparency[node.comp]
                         or (node.mtl is not None and node.mtl.use_opacity)))
            if partial:self.partial_batches.add(i)
            rows.append((ident,local_material,
                         batch.model_cache._cache if batch is not None else None,
                         bool(batch is not None and batch.dirty),partial))
            self.batch_snapshots[node]=(batch,rows[-1])
        self.native.set_editing_data(rows)
        self.inner=SceneScope(self,0)
        self.outer=SceneScope(self,1)

    def changed_branch_nodes(self, pipeline, components):
        """Re-enumerate changed definitions and ancestors; retain other ranges."""
        affected=set(components)
        pending=list(affected)
        while pending:
            for parent in self.definition_parents.get(pending.pop(),()):
                if parent not in affected:affected.add(parent);pending.append(parent)
        result=[];children={};identity=core.CMatrix()
        from .render_pipeline import visible_entity
        # force refreshes children of changed containers (grouping may move
        # their local origins even when their own definition stays unchanged).
        stack=[(None,(),pipeline.top_comp,None,False)]
        while stack:
            path,ids,comp,material,force=stack.pop()
            old_index=self.paths.get(ids)
            old=self.raw_nodes[old_index] if old_index is not None else None
            if (not force and comp not in affected and old is not None
                    and old.comp==comp and old.mtl==material):
                result.extend(self.raw_nodes[old_index:self.ends[old_index]])
                continue
            result.append(pipeline.InstancePathNode(path,comp,identity,material))
            if comp not in children:
                children[comp]=[(inst,inst.GetID(),inst.GetDefinition(),inst.GetMaterial())
                                for inst in comp.EnumChildren() if visible_entity(inst)]
            for inst,ident,definition,local in reversed(children[comp]):
                stack.append(((path or [])+[inst],ids+(ident,),definition,local or material,
                              comp in components))
        self.branch_reused_nodes=sum(node in self.build_snapshots for node in result)
        return result

    def initialize_all(self, pipeline, progress):
        """Warm batches even outside the camera; clear every native pending bit."""
        batches=list(dict.fromkeys(self.batch_nodes.values()))
        for index, batch in enumerate(batches):
            pipeline.resource_owner.subtree_batches.ensure(batch)
            progress('初始化合批缓存', index+1, len(batches))
        self.native.set_pending(list(range(len(self.raw_nodes))),False)
        self.native.clear_batch_pending(list(self.batch_nodes))
        self.pending.clear()

    def refresh_materials(self, pipeline):
        """Python owns inheritance/batch policy; only publish changed snapshots."""
        self.batch_snapshots={}
        from .subtree_batches import MIN_SCENE_NODES
        owner=pipeline.resource_owner
        batching=(getattr(pipeline.view,'subtree_batching',True) and
                  len(self.raw_nodes)-1>=getattr(pipeline.view,'batch_min_scene_nodes',MIN_SCENE_NODES))
        inherited=[];locals_by_instance={};updates=[];rows=[]
        self.batch_nodes={};self.partial_batches=set()
        for i,node in enumerate(self.raw_nodes):
            inst=node.get_inst()
            if inst not in locals_by_instance:
                material=inst.GetMaterial() if inst is not None else None
                locals_by_instance[inst]=(material,
                    pipeline.get_rt_material(material)._native if material is not None else None,
                    inst.GetID() if inst is not None else -1)
            local,snapshot,ident=locals_by_instance[inst]
            parent=self.parents[i]
            material=local or (inherited[parent] if parent>=0 else None)
            inherited.append(material)
            if material!=node.mtl:
                node.mtl=material
                node.material=pipeline.get_rt_material(material)
                updates.append((i,node.material._native))
            batch=owner.subtree_batches.candidate(node) if batching else None
            if batch is not None:self.batch_nodes[i]=batch
            partial=bool(batch is not None and (owner.subtree_batches.transparency[node.comp]
                         or (material is not None and material.use_opacity)))
            if partial:self.partial_batches.add(i)
            rows.append((ident,snapshot,batch.model_cache._cache if batch is not None else None,
                         bool(batch is not None and batch.dirty),partial))
        self.native.update_materials(updates)
        self.native.set_editing_data(rows)
        if self.context_path is not None:
            self.native.set_edit_context(self.paths[self.context_path],pipeline.default_material._native)
        self.selection_key=None

    def refresh_local_geometry(self, pipeline, components):
        self.batch_snapshots={}
        for comp in components:pipeline.ensure_component(comp)
        guides_changed=False
        for comp in components:
            has_guides=bool(comp.HasGuideLine())
            if has_guides != (comp in self.guide_components):
                guides_changed=True
                if has_guides:self.guide_components.add(comp)
                else:self.guide_components.discard(comp)
        if guides_changed:
            # Only first/last guide changes membership, never every frame.
            self.guides=[(i,n) for i,n in enumerate(self.raw_nodes) if n.comp in self.guide_components]
            if self.context_path is not None:self.update_guide_scope(pipeline)
        for batch in set(self.batch_nodes.values()):
            if batch.dirty and components.intersection(batch.batch_definitions):
                pipeline.resource_owner.subtree_batches.ensure(batch)

    def set_context(self, pipeline, path):
        if path==self.context_path:return False
        # Bounds become relevant only when an edited component leaves the
        # active path. Query those definitions now, never the active ancestors.
        old_path=self.context_path
        if old_path is not None:
            updates={}
            for length in range(1,len(old_path)+1):
                prefix=old_path[:length]
                if path[:length]==prefix:continue
                comp=self.raw_nodes[self.paths[prefix]].comp
                updates[comp]=component_bounds(comp)
            if updates:
                self.native.update_instances([],[(c.GetID(),b) for c,b in updates.items()])
                self.bounds.update(updates)
        index=self.paths[path]
        self.native.set_edit_context(index,pipeline.get_rt_material(None)._native)
        self.context_path=path
        self.selection_key=None
        end=self.ends[index]
        pipeline.instance_nodes=NodeRange(self,((index+1,end),))
        pipeline.outer_nodes=NodeRange(self,((0,index),(end,len(self.raw_nodes))))
        self.update_guide_scope(pipeline)
        return True

    def update_guide_scope(self, pipeline):
        index=self.paths[self.context_path]
        end=self.ends[index]
        pipeline._instance_guides=[n for i,n in self.guides if index<i<end]
        pipeline._outer_guides=[n for i,n in self.guides if i<index or i>=end]

    def select(self, selection):
        key=tuple(sorted(e.GetID() for e in selection))
        if key!=self.selection_key:
            self.native.set_selection(key)
            self.selected_ids=set(key)
            self.selection_key=key

    def cull(self, planes, pipeline):
        start=perf_counter()
        camera=pipeline.view.camera.position
        self.native.set_size_filter((camera.x(),camera.y(),camera.z()),
                                    getattr(pipeline.view,'small_object_percent',2.5)/100.0)
        self.native.cull([] if getattr(pipeline.view, 'test_disable_frustum_culling', False) else planes)
        self.last_cull_ms=(perf_counter()-start)*1000
        start=perf_counter()
        direct=self.native.visible_pending()
        for index in direct:
            node=self.raw_nodes[index]
            pipeline.ensure_component(node.comp)
        self.native.set_pending(direct,False)
        batches=self.native.visible_batch_pending()
        for index in batches:
            pipeline.resource_owner.subtree_batches.ensure(self.batch_nodes[index])
        self.native.clear_batch_pending(batches)
        self.last_geometry_ms=(perf_counter()-start)*1000
