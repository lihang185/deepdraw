"""Optional SKP corpus check: import/read each asset and compare topology counts."""
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]


def check(source_path, output):
    sys.path.insert(0,str(ROOT))
    from PySide2.QtWidgets import QApplication
    app=QApplication([])
    from engine import core, model_files
    from importers.sketchup.native import load
    from importers.sketchup.import_model import convert
    core.CModel.InitSystem()
    convert(source_path,output)
    source=load('suapi').SUModel.LoadFromFile(str(source_path))
    expected=[0,0,0,0]  # edges, faces, instances, loops
    seen=set()
    def sdk_component(component):
        for face in component.GetFaces():
            expected[1]+=1
            expected[3]+=1+len(face.GetInnerLoops())
        expected[0]+=component.GetNumEdges()
        instances=component.GetInstances()+component.GetGroups()+component.GetImages()
        expected[2]+=len(instances)
        for instance in instances:
            sdk_definition(instance.GetDefinition())
    def sdk_definition(definition):
        if definition._handle_id not in seen:
            seen.add(definition._handle_id)
            sdk_component(definition.GetEntities())
    sdk_component(source.GetEntities())
    for definition in source.GetComponentDefinitionList()+source.GetGroupDefinitionList():
        sdk_definition(definition)
    model=core.CModel()
    try:
        model_files.load_sketchup_model(model,str(output))
        actual=[0,0,0,0]
        for component in [model.GetTopComponent()]+list(model.GetDefinitionList()):
            for entity in component.EnumEntities():
                if isinstance(entity,core.CEdge):actual[0]+=1
                elif isinstance(entity,core.CFace):
                    actual[1]+=1
                    actual[3]+=entity.GetNumLoops()
                elif isinstance(entity,core.CComponentInstance):actual[2]+=1
        assert actual==expected,(source_path.name,expected,actual)
        from matrix_oracle import check_instances
        check_instances(source,model)
        assert 'sbksueditor' not in sys.modules
    finally:
        model.Release()
        source.Release()


if __name__=='__main__':
    if len(sys.argv)==3:
        check(Path(sys.argv[1]),Path(sys.argv[2]))
    else:
        failures=[]
        sources=sorted((ROOT/'data').rglob('*.skp'))
        with tempfile.TemporaryDirectory(prefix='deepdraw-skp-corpus-') as temp:
            for source in sources:
                result=subprocess.run([sys.executable,'-X','faulthandler',__file__,str(source),
                                       str(Path(temp)/'model.dim')],cwd=ROOT,capture_output=True,timeout=180)
                if result.returncode:
                    failures.append(source.name)
                    print('FAIL',source.name,result.stderr.decode('utf8',errors='replace')[-1600:],flush=True)
                else:print('PASS',source.name,flush=True)
        print('RESULT',len(sources)-len(failures),'/',len(sources),flush=True)
        if failures:raise SystemExit(1)
