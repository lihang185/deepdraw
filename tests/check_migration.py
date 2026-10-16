import sys,tempfile,traceback
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from engine.qt import QtCore,QtGui,QtWidgets
from engine import core,model_files
from app.main_window import EditorMainWindow
from app.ui.load_progress_dialog import LoadProgressDialog
app=QtWidgets.QApplication([]);w=EditorMainWindow();w.show();errors=[]
out=root/('runtime/migration-kowloon-check' if len(sys.argv)>1 else 'runtime/migration-check');out.mkdir(exist_ok=True)
def run():
 try:
  assert w.ready,w.startup_error
  old=root/'data/test2_box.dim'
  with patch('app.main_window.LARGE_SCENE_BYTES',0),patch.object(LoadProgressDialog,'ask_initialize',lambda self:True):
   w.load_file(old)
  w.save_model(path=str(out/'roundtrip.dim'))
  w.load_file(out/'roundtrip.dim')
  with patch('app.main_window.LARGE_SCENE_BYTES',0),patch.object(LoadProgressDialog,'ask_initialize',lambda self:False):
   w.load_file(out/'roundtrip.dim')
  temporary=core.CModel()
  try:model_files.save_sketchup_model(temporary,str(out/'native.dim'),native=True)
  finally:temporary.Release()
  w.load_file(out/'native.dim')
  w.save_model(path=str(out/'native_again.dim'))
  assert (out/'native_again.dim').read_bytes().startswith(b'DeepDrawNative\r\n')
  w.load_file(out/'roundtrip.dim')
  print('EDUCATION_DAI_LOAD_SAVE_WARM_SKIP_NATIVE_OK',flush=True)
  if len(sys.argv)>1:
   with patch.object(LoadProgressDialog,'ask_initialize',lambda self:True):w.load_file(sys.argv[1])
   print('EDUCATION_KOWLOON_WARM_OK',flush=True)
  w.fit_view()
  assert not w.model.HasError(), 'loaded model reports error'
  w.view.makeCurrent()
  fbo=QtGui.QOpenGLFramebufferObject(w.view.width(), w.view.height(), QtGui.QOpenGLFramebufferObject.CombinedDepthStencil)
  assert fbo.bind()
  w.view.paint_off_screen();w.view.gl.glFinish()
  image=fbo.toImage();image.save(str(out/'capture.png'))
  fbo.release();del fbo;w.view.doneCurrent()
  assert len({image.pixel(x,y) for x in range(0,image.width(),4) for y in range(0,image.height(),4)})>2, 'blank render' 
  w.actionRenderStats.setChecked(True);w.on_actionRenderStats_triggered()
  dock=w.render_stats_dock
  assert w.view.render_stats is not None
  dock.smallObjectPercent.setValue(2.5)
  w.view.repaint()
  dock.hide()
  assert w.view.render_stats is None and not dock.timer.isActive()
  print('EDUCATION_DRAW_STATS_OK',flush=True)
  current=w.model
  bad=out/'bad.dim';bad.write_bytes(b'bad')
  try:w.load_file(bad)
  except Exception:pass
  else:raise AssertionError('corrupt file accepted')
  assert w.model is current and not w.input_busy and not w.view.loading_model
 except Exception:errors.append(traceback.format_exc());print(errors[-1],flush=True)
 finally:
  w.release_model();w.hide();app.quit()
QtCore.QTimer.singleShot(1800,run);app.exec_();sys.exit(bool(errors))
