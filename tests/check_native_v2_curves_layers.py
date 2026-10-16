"""Run with engine Python 3.8 AFTER deploying the ABI2 engine and file DLL together."""
import gc
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import core, serialization as pickle_io

V = core.CVector3D


def signature(model):
    result = []
    comp = model.GetTopComponent()
    seen = set()
    for edge in comp.EnumEntities():
        if not isinstance(edge, core.CEdge):
            continue
        curve = edge.GetCurve()
        if curve is None or curve.GetID() in seen:
            continue
        seen.add(curve.GetID())
        edges = list(curve.GetEdges())
        assert curve.GetParentComponent() == comp
        assert all(e.GetCurve() == curve for e in edges)
        data = (type(curve).__name__, curve.is_polygon, len(edges),
                curve.GetFirstEdge().GetStartVertex().Pos().ToTuple(),
                curve.GetLastEdge().GetEndVertex().Pos().ToTuple(),
                tuple(e.GetLayer().name if e.GetLayer() else None for e in edges))
        if isinstance(curve, core.CArcCurve):
            a = curve.arc
            data += (a.center.ToTuple(), a.xaxis.ToTuple(), a.yaxis.ToTuple(),
                     (a.plane.x, a.plane.y, a.plane.z, a.plane.w),
                     a.radius, a.start_angle, a.end_angle)
        result.append(data)
    return sorted(result), [(l.name, l.is_hide) for l in model.GetLayers()]


models = []
try:
    model = core.CModel()
    models.append(model)
    model.Activate()
    core.set_active_model(model)
    factory = core.CEntityFactory(model)
    top = model.GetTopComponent()
    layer = core.CLayer.Load('curve layer', True, None)
    model.addLayer(layer)
    model.addLayer(core.CLayer.Load('empty layer', False, None))
    for index, (arc, closed, polygon) in enumerate(((False, False, False),
                                                    (False, True, True),
                                                    (True, False, False),
                                                    (True, True, False))):
        start = .25
        end = start + (2 * math.pi if closed else 1.8)
        angles = [start + (end-start)*i/12 for i in range(12 if closed else 13)]
        vertices = [factory.NewVertex(V(index*60 + 20*math.cos(a), 20*math.sin(a), 3))
                    for a in angles]
        edges = []
        for i in range(12):
            edge = factory.NewEdge(vertices[i], vertices[(i+1) % len(vertices)], True)
            top.AddEntity(edge)
            edge.SetLayer(layer if index % 2 else None)
            edges.append(edge)
        curve = factory.NewArcCurve() if arc else factory.NewCurve()
        curve.SetParentComponent(top)
        for edge in edges:
            edge.SetCurve(curve)
        curve.UpdateEdgeLink(edges[0])
        curve.is_polygon = polygon
        if arc:
            curve.arc = pickle_io.load_CArc3d(V(index*60, 0, 3), V(1, 0, 0),
                core.CPlane.Load(0, 0, 1, -3), 20, V(0, 1, 0), start, end)
    del vertices, edges, edge, curve
    gc.collect()
    expected = signature(model)
    with tempfile.TemporaryDirectory() as directory:
        native = str(Path(directory)/'native.dim')
        pickled = str(Path(directory)/'pickle.dim')
        assert model.SaveNativeFile(native) == (0, '')
        pickle_io.save_sketchup_model(model, pickled)
        for is_native, path in ((True, native), (False, pickled)):
            loaded = core.CModel()
            models.append(loaded)
            if is_native:
                assert loaded.ReadNativeFile(path) == (0, '')
            else:
                pickle_io.load_sketchup_model(loaded, path)
            gc.collect()
            assert signature(loaded) == expected, (is_native, signature(loaded), expected)
            again = str(Path(directory)/('again_%s.dim' % is_native))
            assert loaded.SaveNativeFile(again) == (0, '')
            assert Path(again).read_bytes() == Path(native).read_bytes()
    print('NATIVE_V2_PICKLE_CURVE_LAYER_PARITY_OK', flush=True)
finally:
    for model in reversed(models):
        model.Release()

