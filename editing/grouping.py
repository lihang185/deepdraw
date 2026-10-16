"""Group/explode one editing level; clone topology before deleting originals."""
from engine import core
from .reference import locked

def clone_entities(dd, entities, target, matrix=None, material=None, touch_target=True):
    factory=core.CEntityFactory(dd.model)
    matrix=matrix or core.CMatrix()
    vertices={};edges={};created=[];mapping={};curves={}
    def vertex(v):
        if v.GetID() not in vertices:
            vertices[v.GetID()]=factory.NewVertex(matrix.Transform(v.Pos()))
        return vertices[v.GetID()]
    def edge(e):
        if e.GetID() not in edges:
            new=factory.NewEdge(vertex(e.GetStartVertex()),vertex(e.GetEndVertex()),True)
            new.SetHide(e.IsHide());new.SetSoft(e.IsSoft());new.SetSmooth(e.IsSmooth())
            target.AddEntity(new);edges[e.GetID()]=new;created.append(new);mapping[e.GetID()]=new
            curve=e.GetCurve()
            if curve is not None:
                curves.setdefault(curve.GetID(),[]).append(new)
        return edges[e.GetID()]
    for e in entities:
        if isinstance(e,core.CEdge):edge(e)
        elif isinstance(e,core.CFace):
            new=factory.NewFace()
            for loop in e.EnumLoops():
                copied=factory.NewLoop();copied.SetIsOuterLoop(loop.IsOuterLoop())
                for use in loop.EnumEdgeUse():
                    copied.AddEdgeUseToTail(factory.NewEdgeUse(edge(use.GetEdge()),use.IsEdgeReversed()))
                new.AddLoop(copied)
            new.SetMaterial(e.GetMaterial() or material)
            new.SetHide(e.IsHide());new.UpdatePlane()
            # New loops default to convex. Recompute in the transformed face plane
            # so concave boundaries use tessellation after both group and explode.
            for copied in new.EnumLoops():
                copied.ComputeIsConvex(new.GetPlane().GetNormal())
            target.AddEntity(new)
            coords=e.GetTextureCoords()
            if coords is not None:
                # UV matrices are 2D homogeneous (3x3), not model transforms.
                # Fit the map from the new face basis back to the original UVs.
                import numpy as np
                old_projection=core.UVHelper(e,e.GetMaterial() or material).ComputeProjectionToFaceSpace(e)
                new_projection=core.UVHelper(new,new.GetMaterial()).ComputeProjectionToFaceSpace(new)
                points=[v.Pos() for v in e.EnumVertices()]
                source=[];uvs=[]
                for point in points:
                    old=old_projection.Transform(point);local=new_projection.Transform(matrix.Transform(point))
                    uv=coords.GetFrontTextureCoords().Reversed().Transform(core.CVector3D(old.x,old.y,1))
                    source.append([local.x,local.y,1]);uvs.append(uv.ToTuple())
                values,_,rank,_=np.linalg.lstsq(np.asarray(source),np.asarray(uvs),rcond=None)
                if rank<3:raise ValueError('Cannot preserve UVs on a degenerate face')
                uv=core.CMatrix33.Load(np.linalg.inv(values).ravel().tolist())
                new.SetTextureCoords(core.CFaceTextureCoords.Load(uv).AddToUndoManager())
            created.append(new);mapping[e.GetID()]=new
        elif isinstance(e,core.CComponentInstance):
            new=factory.NewComponentInstance()
            new.SetDefinition(clone_group_definition(dd,e.GetDefinition()) if e.is_group else e.GetDefinition())
            original=e.GetTransform();composed=core.CMatrix()
            origin=matrix.Transform(original.Transform(core.CVector3D(0,0,0)))
            for axis,point in enumerate((core.CVector3D(1,0,0),core.CVector3D(0,1,0),core.CVector3D(0,0,1))):
                composed.SetAxis(axis,matrix.Transform(original.Transform(point))-origin)
            composed.SetRow(3,origin)
            new.SetTransform(composed);new.SetMaterial(e.GetMaterial() or material)
            new.name=e.name;new.is_group=e.is_group;new.is_image=e.is_image;new.SetHide(e.IsHide())
            target.AddEntity(new);created.append(new);mapping[e.GetID()]=new
        elif isinstance(e,core.CGuideLine):
            new=factory.NewGuideLine();new.orig=matrix.Transform(e.orig)
            new.dir=(matrix.Transform(e.orig+e.dir)-new.orig).Normalized();new.SetHide(e.IsHide())
            target.AddEntity(new);created.append(new);mapping[e.GetID()]=new
        else:raise ValueError('不支持成组/解组的对象：'+type(e).__name__)
    from engine.serialization import restore_curves
    restore_curves(dd.model,list(curves.values()))
    if touch_target:
        dd.edit.touch(dd.wrap(target))
    return created,mapping

def selected(dd,target=None):
    dd.edit.require_operation()
    parent=dd.model.GetActiveComponent()
    items=list(dd.model.GetSelection()) if target is None else list(dd.unwrap(target))
    if not items or any(e.IsMarkedDeleted() or e.GetParentComponent()!=parent for e in items):
        raise ValueError('请先选择当前编辑层的对象')
    if locked(parent) or any(isinstance(e,core.CComponentInstance) and locked(e.GetDefinition()) for e in items):
        raise ValueError('不能修改锁定参照图')
    return parent,items

def group(dd,target=None,name='Group'):
    parent,items=selected(dd,target)
    from engine.comp_maker import ComponentMaker
    wrapper=dd.wrap(parent);base=name;index=1
    while name in wrapper.names():name=base+str(index);index+=1
    named={key:[e.id for e in wrapper.named(key)] for key in wrapper.names()}
    maker=ComponentMaker(items,dd.model)
    definition=maker.create_comp_def(name)
    dd.model.ClearSelection()
    maker.separate_from()
    maker.add_to_component(definition)
    maker.set_center_point(definition)
    instance=maker.make_instance(definition)
    instance.name=name
    parent.AddEntity(instance)
    result=dd.wrap(instance)
    dd.scene.name(name,result,wrapper)
    for key,ids in named.items():
        members=[maker.mapping[ident] for ident in ids if ident in maker.mapping]
        if members:dd.scene.name(key,[dd.wrap(e) for e in members],result.definition)
    dd.edit.touch(wrapper);dd.edit.touch(result.definition)
    dd.model.SetSelection([instance])
    return result


def explode(dd,target=None):
    parent,items=selected(dd,target)
    if any(not isinstance(e,core.CComponentInstance) for e in items):
        raise ValueError('解组请仅选择组或组件')
    result=[]
    dd.model.ClearSelection()
    for inst in items:
        definition=inst.GetDefinition()
        copied,mapping=clone_entities(dd,list(definition.EnumEntities()),parent,inst.GetTransform(),inst.GetMaterial())
        wrapper=dd.wrap(definition)
        for name in wrapper.names():
            members=[mapping[e.id] for e in wrapper.named(name) if e.id in mapping]
            parent_wrapper=dd.wrap(parent)
            if members:
                key=name;index=1
                while key in parent_wrapper.names():key=name+'_'+str(index);index+=1
                dd.scene.name(key,[dd.wrap(e) for e in members],parent_wrapper)
        inst.Erase(parent);result.extend(copied)
    # Weld with existing parent geometry and find/split faces.
    geometry=[e for e in result if isinstance(e,(core.CEdge,core.CFace))]
    if geometry:parent.CheckModel(geometry,None)
    dd.model.ClearSelection()
    #dd.model.SetSelection([e for e in result if not e.IsMarkedDeleted()])
    return [dd.wrap(e) for e in result if not e.IsMarkedDeleted()]


def clone_group_definition(dd, source):
    """Copy group contents; nested groups own copies, ordinary components stay linked."""
    target=core.CEntityFactory(dd.model).NewComponentDefinition()
    dd.model.addDefinition(target)
    for field in ('name','description','agent_hint','is_dynamic_comp','dynamic_comp'):
        setattr(target,field,getattr(source,field))
    target.file_path=''  # A private group copy is not an imported library definition.
    _,mapping=clone_entities(dd,list(source.EnumEntities()),target)
    from engine.serialization import save_named_sets
    for name,members in save_named_sets(source).items():
        target.AddNamedSet(name,[mapping[e.GetID()] for e in members if e.GetID() in mapping])
    return target
