"""DAI-only routing, native/pickle round trips and legacy suffix rejection."""
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import core,model_files,serialization
models=[]
try:
 m=core.CModel();models.append(m);m.Activate();core.set_active_model(m)
 m.GetTopComponent().description='DAI only'
 with tempfile.TemporaryDirectory() as folder:
  for native in (False,True):
   path=Path(folder)/('native.dim' if native else 'pickle.dim')
   model_files.save_sketchup_model(m,str(path),native=native)
   n=core.CModel();models.append(n);model_files.load_sketchup_model(n,str(path))
   assert n.GetTopComponent().description=='DAI only'
  for reader in (model_files.load_sketchup_model,model_files.load_sketchup_model_as_component,serialization.load_sketchup_model):
   try:reader(m,str(Path(folder)/'old.dai'))
   except ValueError:pass
   else:raise AssertionError('DAI accepted')
  for native in (False,True):
   try:model_files.save_sketchup_model(m,str(Path(folder)/'old.dai'),native=native)
   except ValueError:pass
   else:raise AssertionError('DAI write accepted')
  bad=Path(folder)/'bad.dim';bad.write_bytes(b'not a model')
  try:model_files.load_sketchup_model(m,str(bad))
  except ValueError:pass
  else:raise AssertionError('corrupt DAI accepted')
 print('DAI_ONLY_FORMAT_CHECKS_OK',flush=True)
finally:
 for m in reversed(models):m.Release()
 core.set_active_model(None)
