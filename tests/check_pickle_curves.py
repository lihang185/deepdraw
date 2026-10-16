"""Real native curve/arc pickle round trips, component import and legacy groups."""
import gc,math,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from engine import core,serialization as s
V=core.CVector3D

def curves(comp):
    return list({e.GetCurve().GetID():e.GetCurve() for e in comp.EnumEntities()
                 if isinstance(e,core.CEdge) and e.GetCurve() is not None}.values())

def signature(comp):
    result=[]
    for c in curves(comp):
        edges=list(c.GetEdges())
        assert edges and all(e.GetCurve()==c and e.GetParentComponent()==comp for e in edges)
        assert c.GetParentComponent()==comp
        data=(type(c).__name__,c.is_polygon,len(edges),
              c.GetFirstEdge().GetStartVertex().Pos().ToTuple(),
              c.GetLastEdge().GetEndVertex().Pos().ToTuple())
        if isinstance(c,core.CArcCurve):
            a=c.arc
            data+=(a.center.ToTuple(),a.xaxis.ToTuple(),a.yaxis.ToTuple(),
                   (a.plane.x,a.plane.y,a.plane.z,a.plane.w),a.radius,a.start_angle,a.end_angle)
        result.append(data)
    return sorted(result)

models=[]
try:
    model=core.CModel();models.append(model);model.Activate();core.set_active_model(model)
    factory=core.CEntityFactory(model);top=model.GetTopComponent()
    definition=factory.NewComponentDefinition();model.addDefinition(definition)
    for polygon,arc,closed,comp in ((False,False,False,top),(True,False,True,top),
                                    (False,True,False,definition),(False,True,True,definition)):
        offset=60*len(curves(comp));start=.25;end=start+(2*math.pi if closed else 1.8)
        n=12;angles=[start+(end-start)*i/n for i in range(n if closed else n+1)]
        vertices=[factory.NewVertex(V(offset+20*math.cos(a),20*math.sin(a),3)) for a in angles]
        edges=[]
        for i in range(n):
            e=factory.NewEdge(vertices[i],vertices[(i+1)%len(vertices)],True)
            comp.AddEntity(e);edges.append(e)
        c=factory.NewArcCurve() if arc else factory.NewCurve()
        c.SetParentComponent(comp)
        for e in edges:e.SetCurve(c)
        c.UpdateEdgeLink(edges[0]);c.is_polygon=polygon
        if arc:
            a=s.load_CArc3d(V(offset,0,3),V(1,0,0),core.CPlane.Load(0,0,1,-3),20,V(0,1,0),start,end)
            c.arc=a
    for i in range(2):
        inst=factory.NewComponentInstance();inst.SetDefinition(definition);top.AddEntity(inst)
    # Model ownership must survive releasing every temporary geometry wrapper.
    del vertices,edges,e,c,a,inst
    gc.collect()
    expected=(signature(top),signature(definition))
    with tempfile.TemporaryDirectory() as directory:
        path=str(Path(directory)/'curves.dim');s.save_sketchup_model(model,path)
        loaded=core.CModel();models.append(loaded);s.load_sketchup_model(loaded,path)
        gc.collect()
        lt=loaded.GetTopComponent();instances=list(lt.EnumChildren())
        assert instances[0].GetDefinition()==instances[1].GetDefinition()
        assert (signature(lt),signature(instances[0].GetDefinition()))==expected
        # Persist again after temporary arc values and pickle memo are gone.
        second=str(Path(directory)/'again.dim');s.save_sketchup_model(loaded,second)
        target=core.CModel();models.append(target)
        imported=s.load_sketchup_model_as_component(target,second)
        assert (signature(imported),signature(next(iter(imported.EnumChildren())).GetDefinition()))==expected
        # Legacy edge-only records still use the original reconstruction.
        legacy=core.CModel();models.append(legacy);f=core.CEntityFactory(legacy)
        e=f.NewEdge(f.NewVertex(V()),f.NewVertex(V(1,0,0)),True);legacy.GetTopComponent().AddEntity(e)
        s.restore_curves(legacy,[[e]])
        assert len(curves(legacy.GetTopComponent()))==1
    print('PICKLE_CURVE_ARC_POLYGON_CIRCLE_SHARED_IMPORT_LIFETIME_LEGACY_OK',flush=True)
except BaseException:
    import traceback
    traceback.print_exc()
    raise
finally:
    for model in reversed(models):model.Release()
