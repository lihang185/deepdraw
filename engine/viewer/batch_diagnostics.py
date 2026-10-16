"""On-demand batch diagnostics. Never called by rendering or with the panel hidden."""
from collections import Counter
from time import perf_counter
from engine import core
from .subtree_batches import MIN_NODES,MAX_NODES,MAX_ENTITIES,MIN_SCENE_NODES

REASONS=('编辑路径祖先','合批开关关闭','场景未达合批门槛','图片实例/子树',
         '动画实例/子树','动态变换子树','透明材质/子树','子树节点超过上限',
         '图元数超过上限','子树节点不足','子树空间跨度过大','其他安全限制')

def diagnose(pipeline):
    from .render_pipeline import visible_entity
    start=perf_counter();scene=pipeline._world_scene;manager=pipeline.resource_owner.subtree_batches
    active=scene.paths[scene.context_path];memo={}
    def unsafe(comp):
        if comp in memo:return memo[comp]
        reasons=set();memo[comp]=reasons
        if comp.GetNumFaces():
            for entity in comp.EnumEntities():
                if isinstance(entity,core.CFace) and visible_entity(entity):
                    material=entity.GetMaterial()
                    if material is not None and material.use_opacity:
                        reasons.add('透明材质/子树');break
        for inst in comp.EnumChildren():
            if not visible_entity(inst):continue
            if inst.is_image:reasons.add('图片实例/子树')
            if inst.dynamic_info:reasons.add('动画实例/子树')
            if inst in manager.dynamic:reasons.add('动态变换子树')
            material=inst.GetMaterial()
            if material is not None and material.use_opacity:reasons.add('透明材质/子树')
            reasons.update(unsafe(inst.GetDefinition()))
        return reasons
    counts=Counter();branches=Counter();batched=saved=partial=0
    enabled=scene.native.enabled_indices()
    for i in enabled:
        node=scene.raw_nodes[i]
        if i<=active<scene.ends[i]:reason='编辑路径祖先'
        elif i in scene.batch_nodes:
            batched+=1;saved+=scene.ends[i]-i-1
            partial+=i in scene.partial_batches
            continue
        elif not getattr(pipeline.view,'subtree_batching',True):reason='合批开关关闭'
        elif len(scene.raw_nodes)-1<getattr(pipeline.view,'batch_min_scene_nodes',MIN_SCENE_NODES):reason='场景未达合批门槛'
        else:
            inst=node.get_inst()
            count,entities,safe,_,_=manager.plan(node.comp)
            if inst is not None and inst.is_image:reason='图片实例/子树'
            elif inst is not None and inst.dynamic_info:reason='动画实例/子树'
            elif node.mtl is not None and node.mtl.use_opacity:reason='透明材质/子树'
            elif count>MAX_NODES:reason='子树节点超过上限'
            elif entities>MAX_ENTITIES:reason='图元数超过上限'
            elif count<MIN_NODES:reason='子树节点不足'
            elif not safe:
                causes=unsafe(node.comp)
                reason=next((r for r in REASONS if r in causes),'其他安全限制')
            elif not manager.spatially_compact(node.comp):reason='子树空间跨度过大'
            else:reason='其他安全限制'
        counts[reason]+=1
        if scene.ends[i]>i+1:branches[reason]+=1
    return dict(counts=counts,branches=branches,batched=batched,partial=partial,saved=saved,nodes=len(enabled),
                milliseconds=(perf_counter()-start)*1000)
