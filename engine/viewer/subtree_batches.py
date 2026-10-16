"""Bounded definition-local subtree batches shared by repeated occurrences.

Only rendering is flattened. Model hierarchy, picking and editing are untouched.
Changing a baked child invalidates its batch and keeps that branch dynamic thereafter.
"""
from engine import core

MIN_NODES = 4
MAX_NODES = 512
MAX_ENTITIES = 30000
MIN_SCENE_NODES = 1024
MAX_SPATIAL_SPAN = 4.0


def compact_bounds(boxes):
    if len(boxes)<2:return True
    largest=max(sum((b[2*c+1]-b[2*c])**2 for c in range(3)) for b in boxes)
    span=sum((max(b[2*c+1] for b in boxes)-min(b[2*c] for b in boxes))**2 for c in range(3))
    return span<=MAX_SPATIAL_SPAN**2*largest


class SubtreeBatches:
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.plans = {}
        self.transparency = {}
        self.spatial = {}
        self.caches = {}
        self.dynamic = set()

    def plan(self, comp):
        if comp in self.plans:
            return self.plans[comp]
        from .render_pipeline import visible_entity
        # Guard malformed recursive definitions; no flattening across cycles.
        self.plans[comp] = (MAX_NODES + 1, MAX_ENTITIES + 1, False, frozenset(), frozenset())
        self.transparency[comp] = False
        transparent = False
        count, entities, safe = 1, comp.GetNumEdges() + comp.GetNumFaces(), True
        definitions, instances = {comp}, set()
        cached = self.pipeline.component_map.get(comp)
        if cached is not None and not cached.dirty:
            transparent = cached.model_cache.HasGeomtry(3)
        elif getattr(self.pipeline, '_initial_geometry', None) is not None:
            groups, _ = self.pipeline.initial_geometry(comp)
            transparent = any(m is not None and m.use_opacity for m in groups)
        else:
            for entity in (comp.EnumEntities() if comp.GetNumFaces() else ()):
                if isinstance(entity, core.CFace) and visible_entity(entity):
                    material = entity.GetMaterial()
                    if material is not None and material.use_opacity:
                        transparent = True
        for inst in comp.EnumChildren():
            if not visible_entity(inst):
                continue
            instances.add(inst)
            child_count, child_entities, child_safe, defs, children = self.plan(inst.GetDefinition())
            transparent = transparent or self.transparency[inst.GetDefinition()]
            definitions.update(defs); instances.update(children)
            count += child_count; entities += child_entities
            material = inst.GetMaterial()
            transparent = transparent or (material is not None and material.use_opacity)
            safe = (safe and child_safe and inst not in self.dynamic and not inst.is_image
                    and not bool(inst.dynamic_info))
        result = count, entities, safe, frozenset(definitions), frozenset(instances)
        self.plans[comp] = result
        self.transparency[comp] = transparent
        return result

    def spatially_compact(self, comp):
        # Definition-local and camera-independent; compute once per revision.
        if comp in self.spatial:return self.spatial[comp]
        from .render_pipeline import visible_entity
        children=[inst for inst in comp.EnumChildren() if visible_entity(inst)]
        # A wrapper must not swallow a branch already rejected for dispersion.
        if any(not self.spatially_compact(inst.GetDefinition()) for inst in children):
            self.spatial[comp]=False
            return False
        if comp.GetNumEdges() or comp.GetNumFaces():
            self.spatial[comp]=True
            return True
        boxes=[]
        for inst in children:
            b=inst.GetDefinition().GetBoundingBox()
            if b.min_x>b.max_x or b.min_y>b.max_y or b.min_z>b.max_z:continue
            matrix=inst.GetTransform()
            points=[matrix.Transform(core.CVector3D(x,y,z))
                    for x in (b.min_x,b.max_x) for y in (b.min_y,b.max_y)
                    for z in (b.min_z,b.max_z)]
            boxes.append(tuple(v for axis in ('x','y','z')
                               for v in (min(getattr(p,axis) for p in points),
                                         max(getattr(p,axis) for p in points))))
        result=compact_bounds(boxes)
        self.spatial[comp]=result
        return result

    def compact(self, nodes):
        if len(nodes) < getattr(self.pipeline.view, 'batch_min_scene_nodes', MIN_SCENE_NODES):
            return nodes
        active = self.pipeline.model.GetActiveComponentPath()
        active_ids = tuple(active.Get(i).GetID() for i in range(active.Length()))
        result = []
        skip = None
        for node in nodes:
            path = tuple(i.GetID() for i in (node.inst_path or []))
            if skip is not None and path[:len(skip)] == skip:
                continue
            skip = None
            # Empty paths can be outer ancestors of the active editing context.
            # Their subtree deliberately excludes the active branch: never bake it.
            if not path or hasattr(node, 'entities'):
                result.append(node); continue
            count, entities, safe, definitions, instances = self.plan(node.comp)
            root_inst = node.get_inst()
            if not (safe and not self.transparency[node.comp] and MIN_NODES <= count <= MAX_NODES and entities <= MAX_ENTITIES
                    and not root_inst.is_image and not bool(root_inst.dynamic_info)
                    and not (node.mtl is not None and node.mtl.use_opacity)):
                result.append(node); continue
            # Do not batch a partially enumerated outer subtree on the active path.
            if active_ids[:len(path)] == path:
                result.append(node); continue
            if not self.spatially_compact(node.comp):
                result.append(node); continue
            cache = self.caches.get(node.comp)
            if cache is None:
                from .render_pipeline import RenderComponent
                cache = RenderComponent(node.comp, self.pipeline)
                cache.batch_definitions = definitions
                cache.batch_instances = instances
                self.caches[node.comp] = cache
            cache.batch_definitions = definitions
            cache.batch_instances = instances
            clone = self.pipeline.InstancePathNode(node.inst_path, node.comp, node.matrix, node.mtl)
            clone.batch_component = cache
            result.append(clone)
            skip = path
        return result

    def candidate(self, node):
        """Context-independent batch; the native tree expands edited ancestors."""
        inst = node.get_inst()
        if inst is None or inst.is_image or inst.dynamic_info:
            return None
        count, entities, safe, definitions, instances = self.plan(node.comp)
        if (not getattr(self.pipeline.view,'mixed_subtree_batching',True)
                and (self.transparency[node.comp] or (node.mtl is not None and node.mtl.use_opacity))):
            return None
        if not (safe and MIN_NODES <= count <= MAX_NODES and entities <= MAX_ENTITIES):
            return None
        if not self.spatially_compact(node.comp):
            return None
        cache = self.caches.get(node.comp)
        if cache is None:
            from .render_pipeline import RenderComponent
            cache = RenderComponent(node.comp, self.pipeline)
            self.caches[node.comp] = cache
        cache.batch_definitions = definitions
        cache.batch_instances = instances
        return cache

    def ensure(self, cache):
        if cache.dirty:
            cache.clear_geom()
            for node in self.pipeline.RecursiveRnumInstance(None, cache.comp, core.CMatrix(), None):
                cache.add_node(node)
            # Transparent faces retain their original per-instance submissions.
            # Do not duplicate explicit transparent geometry in the opaque batch.
            cache.dict_mats_opacity.clear()
            cache.build(self.pipeline.view.gl)
        return cache

    def invalidate(self, change):
        comps, instances = set(change.components), set(change.instances)
        affected = []
        split = False
        for comp, cache in self.caches.items():
            internal = instances.intersection(cache.batch_instances)
            if internal - self.dynamic:
                self.dynamic.update(internal)
                split = True
            if (change.all_geometry or (change.scene and not comps) or internal
                    or comps.intersection(cache.batch_definitions)):
                affected.append(comp)
        # Notifications may arrive without a GL context. Rebuild lazily on draw.
        for comp in affected:
            self.caches[comp].mark_dirty()
        if comps or change.all_geometry or change.scene or split:
            if change.all_geometry or change.scene:
                self.plans.clear()
                self.transparency.clear()
                self.spatial.clear()
            else:
                # A local edit cannot change unrelated definitions' plans.
                # Includes ancestors and shared occurrences via dependency sets.
                invalid = [comp for comp, plan in self.plans.items()
                           if comps.intersection(plan[3]) or instances.intersection(plan[4])]
                for comp in invalid:
                    self.plans.pop(comp, None)
                    self.transparency.pop(comp, None)
                    self.spatial.pop(comp, None)
        return split

    def close(self):
        for cache in self.caches.values():
            cache.model_cache.close()
        self.spatial.clear()
        self.caches.clear(); self.plans.clear(); self.transparency.clear(); self.dynamic.clear()

    def statistics(self):
        stats = [c.model_cache.statistics() for c in self.caches.values()]
        return dict(definitions=len(stats), builds=sum(s['build_count'] for s in stats),
                    build_seconds=sum(s['build_seconds'] for s in stats))
