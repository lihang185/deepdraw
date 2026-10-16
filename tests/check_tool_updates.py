"""Education tool commit and nested vertex snap regression, real native engine."""
import sys,time,traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from engine import core
from engine.qt import QtCore,QtGui,QtWidgets
from app.main_window import EditorMainWindow
from app.ui.load_progress_dialog import LoadProgressDialog
from engine.tools.tool_draw_line import DrawLineTool
from engine.tools.tool_move import MoveTool
from engine.tools.move_snap import vertex_at
app=QtWidgets.QApplication([]);w=EditorMainWindow();w.show();errors=[]
def run():
 try:
  v=w.view;dd=w.editing;V=core.CVector3D
  with dd.edit.operation('fixture'):
   parent=dd.build.component('parent')
   child=dd.build.component('child',parent=parent.definition)
   edge=dd.build.line((0,0,0),(10,0,0),target=child.definition).native
   m=core.CMatrix();m.Translate(30,40,20);child.native.SetTransform(m)
   m=core.CMatrix();m.Scale3(2,2,2);m.Translate(100,80,0);parent.native.SetTransform(m)
  w.fit_view();v.ComputeCameraMatrix()
  class Picker:
   def Reset(self):pass
   def SinglePick(self,*args):pass
   def GetPicked(self):return [SimpleNamespace(e=edge,inst_path=[parent.native,child.native])]
  world=parent.native.GetTransform().Transform(child.native.GetTransform().Transform(V()))
  def snap():
   q=(v.ComputeProjectMatrix()*v.ComputeCameraMatrix()[0]).map(QtGui.QVector3D(*world.ToTuple()))
   pos=QtCore.QPoint(round((q.x()+1)*v.width()/2-.5),round((1-q.y())*v.height()/2-.5))
   return vertex_at(v,Picker(),pos,set())
  assert (snap()-world).Length()<1e-6
  w.model.OpenComponent(parent.native)
  assert (snap()-child.native.GetTransform().Transform(V())).Length()<1e-6
  w.model.CloseComponent()
  print('NESTED_COMPONENT_VERTEX_SNAP_OK',flush=True)
  w.model.SetSelection([parent.native])
  move=MoveTool(v);move.activate();move.copy_mode=True
  move.begin_move(V());move.preview_point(V(10,20,0));move.finish_move()
  assert len(list(w.model.GetTopComponent().EnumChildren()))==2
  dd.edit.undo();assert len(list(w.model.GetTopComponent().EnumChildren()))==1
  dd.edit.redo();assert len(list(w.model.GetTopComponent().EnumChildren()))==2
  print('MOVE_COPY_UNDO_REDO_OK',flush=True)
  if len(sys.argv)>1:
   with patch.object(LoadProgressDialog,'ask_initialize',lambda self:False):w.load_file(sys.argv[1])
   v=w.view;dd=w.editing
  changes=[];original=v.pipeline.apply_render_change
  def changed(c):changes.append(c);return original(c)
  with patch.object(v.pipeline,'apply_render_change',changed),patch.object(v,'MarkDirty',side_effect=AssertionError('global invalidation')):
   tool=DrawLineTool(v);tool.activate();tool.prev_point=V(1000000,0,0);tool.cur_point=V(1000010,0,0)
   start=time.perf_counter();tool.add_new_line();elapsed=time.perf_counter()-start
   assert any(c.local_geometry for c in changes)
   print('DRAW_LINE_COMMIT_SECONDS',round(elapsed,4),flush=True)
   edge=next(e for e in w.model.GetActiveComponent().EnumEntities() if isinstance(e,core.CEdge) and (e.GetStartVertex().Pos()-V(1000000,0,0)).Length()<.01)
   start=time.perf_counter();w.erase_entities([edge],'delete regression')
   print('DELETE_COMMIT_SECONDS',round(time.perf_counter()-start,4),flush=True)
  dd.edit.undo();dd.edit.redo()
  print('TOOL_LOCAL_UPDATES_UNDO_REDO_OK',flush=True)
 except Exception:errors.append(traceback.format_exc());print(errors[-1],flush=True)
 finally:w.release_model();w.hide();app.quit()
QtCore.QTimer.singleShot(1200,run);app.exec_();sys.exit(bool(errors))

