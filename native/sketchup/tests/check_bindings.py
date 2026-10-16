"""Run in CPython 3.8 x64; each native scenario runs in its own process."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
NATIVE = ROOT / 'importers/sketchup'


def sdk():
    sys.path.insert(0, str(NATIVE))
    global dll_directory
    dll_directory = os.add_dll_directory(str(NATIVE))
    import suapi
    import suapi_extra
    for module in (suapi, suapi_extra):
        assert module.__binding__ == 'pybind11'
        assert Path(module.__file__).parent == NATIVE
    return suapi, suapi_extra


def raises(function, types=(RuntimeError, ValueError, TypeError)):
    try:
        function()
    except types:
        return
    raise AssertionError('Invalid input was accepted')


def handles(directory):
    s, extra = sdk()
    sys.path.insert(0,str(ROOT))
    from matrix_oracle import check_import_math
    check_import_math()
    source = ROOT / 'data/ren.skp'
    for _ in range(10):
        model = s.SUModel.LoadFromFile(str(source))
        assert model.GetName() == extra.sumodel_get_name(model)
        assert len(extra.sumodel_get_dib(model)) > 0
        definitions = model.GetComponentDefinitionList()
        assert len(definitions) == 1 and definitions[0].GetNumFaces() == 1
        entities = model.GetEntities()
        pointer = model.GetPtr()
        model.Release()
        model.Release()
        raises(entities.GetFaces)
        raises(lambda: extra.sumodel_get_name(pointer))
        raises(lambda: definitions[0].GetEdges())
    raises(lambda: extra.sumodel_get_dib(123))
    raises(lambda: s.SUModel.LoadFromFile(str(directory/'missing.skp')))
    raises(lambda: s.SUModel.LoadFromBuffer(b'not a SketchUp file'))
    model = s.SUModel.LoadFromBuffer(source.read_bytes())
    assert model.GetEntities().GetNumInstances() == 1
    model.Release()


def fixture(directory):
    s, extra = sdk()
    model = s.SUModel.Create()
    material = s.SUMaterial.Create()
    material.SetName('教育版材质')
    material.SetColor(s.CVector3D(0.25, 0.5, 0.75))
    material.SetUseOpacity(True)
    material.SetOpacity(0.7)
    model.AddMaterial(material)
    definition = s.SUComponentDefinition.Create()
    definition.SetName('带孔共享组件')
    model.AddComponentDefinition(definition)
    geom = s.SUGeometryInput.Create()
    for x, y in [(0,0),(10,0),(10,10),(0,10),(2,2),(2,4),(4,4),(4,2)]:
        geom.AddVertex(s.CVector3D(x,y,0))
    outer = s.SULoopInput.Create()
    for i in range(4): outer.AddVertexIndex(i)
    outer.EdgeSetSoft(0, True)
    outer.EdgeSetSmooth(0, True)
    index = geom.AddFace(outer)
    raises(lambda: outer.AddVertexIndex(0))
    hole = s.SULoopInput.Create()
    for i in range(4,8): hole.AddVertexIndex(i)
    geom.FaceAddInnerLoop(index,hole)
    geom.FaceSetFrontMaterial(index,material,None)
    definition.GetEntities().Fill(geom,True)
    geom.Release()
    for shift in (0,20):
        instance=definition.CreateInstance()
        # Rotation plus non-uniform scale must survive both import and export.
        instance.SetTransform(s.CMatrix.NewFromData(
            [0,2,0,0,-3,0,0,0,0,0,0.5,0,shift,7,9,1]))
        model.GetEntities().AddInstance(instance)
    path=directory/'中文模型.skp'
    assert model.SaveToFile2017(str(path))
    model.Release()
    raises(material.GetName)
    model=s.SUModel.LoadFromFile(str(path))
    assert model.GetEntities().GetNumInstances()==2
    defs=model.GetComponentDefinitionList()
    assert len(defs)==1 and defs[0].GetName()=='带孔共享组件'
    face=defs[0].GetFaces()[0]
    assert len(face.GetInnerLoops())==1
    assert face.GetFrontMaterial().GetName()=='教育版材质'
    assert abs(face.GetFrontMaterial().GetOpacity()-0.7)<1e-8
    assert any(edge.GetSoft() and edge.GetSmooth() for edge in defs[0].GetEdges())
    model.Release()


def conversion(directory):
    sdk()
    import convert
    for source,output in [(directory/'中文模型.skp',directory/'converted.dim'),
                          (ROOT/'data/ren.skp',directory/'textured.dim')]:
        sys.argv=['convert',str(NATIVE),str(source),str(output)]
        convert.main()
        from engine.dim_format import read_payload
        version,stream=read_payload(output)
        stream.close()
        assert version==3
    assert not {'sbksueditor','binary_file_v2','editor_cpp_loader','su_algo'} & set(sys.modules)
    import ctypes
    ctypes.windll.kernel32.GetModuleHandleW.restype=ctypes.c_void_p
    assert not ctypes.windll.kernel32.GetModuleHandleW('DeepDrawAPI.dll')
    assert not ctypes.windll.kernel32.GetModuleHandleW('libshiboken.dll')


def entry_points(directory):
    for entry in ([str(NATIVE/'convert.py')], [str(ROOT/'editor.py'),'--convert-skp']):
        output=directory/'entry.dim'
        command=[sys.executable,'-u','-X','faulthandler']+entry+[str(NATIVE),str(directory/'中文模型.skp'),str(output)]
        subprocess.run(command,check=True,cwd=directory,timeout=60)
        original=output.read_bytes()
        command[-2]=str(directory/'missing.skp')
        result=subprocess.run(command,cwd=directory,capture_output=True,timeout=60)
        assert result.returncode!=0
        assert output.read_bytes()==original


def current_engine(directory):
    sys.path.insert(0,str(ROOT))
    from PySide2.QtWidgets import QApplication
    app=QApplication([])
    from engine import core, model_files
    core.CModel.InitSystem()
    model=core.CModel()
    model_files.load_sketchup_model(model,str(directory/'converted.dim'))
    entities=list(model.GetTopComponent().EnumEntities())
    assert len(entities)==2
    definition=entities[0].GetDefinition()
    assert definition.GetID()==entities[1].GetDefinition().GetID()
    edges=[e for e in definition.EnumEntities() if isinstance(e,core.CEdge)]
    xs=[v.Pos().x for edge in edges for v in (edge.GetStartVertex(),edge.GetEndVertex())]
    assert abs(max(xs)-min(xs)-25.4)<1e-6
    model_files.save_sketchup_model(model,str(directory/'current.dim'))
    from engine.dim_format import read_payload
    version,stream=read_payload(directory/'current.dim')
    stream.close()
    assert version==3
    # The UI inserts this file as a component into an existing document.
    asset=model_files.load_sketchup_model_as_component(model,str(directory/'converted.dim'))
    assert len(list(asset.EnumEntities()))==2
    from engine import sketchup_export
    assert sketchup_export.export_scene_to_file(model,directory/'往返.skp')
    assert sketchup_export.export_selection_to_file(model,directory/'空选择.skp')
    model.SetSelection(entities)
    assert sketchup_export.export_selection_to_file(model,directory/'选择.skp')
    raises(lambda: sketchup_export.export_scene_to_file(model.GetPtr(),directory/'bad.skp'))
    assert 'sbksueditor' not in sys.modules
    import ctypes
    ctypes.windll.kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    assert not ctypes.windll.kernel32.GetModuleHandleW('DeepDrawAPI.dll')
    model.Release()
    s,extra=sdk()
    for filename in ('往返.skp','选择.skp'):
        result=s.SUModel.LoadFromFile(str(directory/filename))
        assert result.GetEntities().GetNumInstances()==2
        defs=result.GetComponentDefinitionList()
        assert len(defs)==1
        assert len(defs[0].GetFaces()[0].GetInnerLoops())==1
        assert abs(defs[0].GetFaces()[0].GetFrontMaterial().GetOpacity()-0.7)<1e-8
        if filename=='往返.skp':
            from matrix_oracle import sdk_point, assert_point
            original=s.SUModel.LoadFromFile(str(directory/'中文模型.skp'))
            for before,after in zip(original.GetEntities().GetInstances(),result.GetEntities().GetInstances()):
                for point in ((0,0,0),(1,2,3),(-2,4,1)):
                    assert_point(sdk_point(after.GetTransform().GetData(),point),
                                 sdk_point(before.GetTransform().GetData(),point),'SKP export round trip')
            original.Release()
        result.Release()
    result=s.SUModel.LoadFromFile(str(directory/'空选择.skp'))
    assert result.GetEntities().GetNumInstances()==0
    result.Release()
    model=core.CModel()
    model_files.load_sketchup_model(model,str(directory/'textured.dim'))
    assert sketchup_export.export_scene_to_file(model,directory/'textured.skp')
    model.Release()
    original=s.SUModel.LoadFromFile(str(ROOT/'data/ren.skp'))
    result=s.SUModel.LoadFromFile(str(directory/'textured.skp'))
    a=original.GetMaterialList()[0].GetTexture()
    b=result.GetMaterialList()[0].GetTexture()
    assert a.GetImageDataSize()==b.GetImageDataSize()
    assert a.GetData()==b.GetData()
    assert abs(a.GetScaleU()-b.GetScaleU())<1e-8
    assert abs(a.GetScaleV()-b.GetScaleV())<1e-8
    original.Release()
    result.Release()
    assert 'sbksueditor' not in sys.modules


if __name__=='__main__':
    if len(sys.argv)>1:
        scenario=sys.argv[1]
        globals()[scenario](Path(sys.argv[2]))
        print('PASS',scenario,flush=True)
    else:
        with tempfile.TemporaryDirectory(prefix='deepdraw-skp-') as temp:
            for scenario in ('handles','fixture','conversion','entry_points','current_engine'):
                subprocess.run([sys.executable,'-u','-X','faulthandler',__file__,scenario,temp],check=True,cwd=ROOT)
