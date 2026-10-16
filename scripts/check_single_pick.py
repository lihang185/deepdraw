"""Education-only native GL, world picking and scaled numerical input checks."""
import sys,traceback,math
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from engine import core
from engine.qt import QtCore,QtGui,QtWidgets
from app.main_window import EditorMainWindow
from engine.coordinates import to_world,to_local,world_length,active_matrix,affine
from engine.tools.drawing_support import infer
from engine.tools.tool_draw_line import DrawLineTool
from engine.tools.tool_draw_rect import DrawRectTool
from engine.tools.tool_draw_circle import DrawCircleTool
from engine.tools.tool_move import MoveTool
from engine.tools.tool_offset import OffsetTool
from engine.tools.tool_section import SectionTool
from engine.tools.tool_push import PushTool
app=QtWidgets.QApplication([]);h=EditorMainWindow();h.show();errors=[]

def run():
 try:
  dd=h.editing;v=h.view;model=v.model;V=core.CVector3D
  def surface(name,points,parent=None):
   obj=dd.build.component(name,parent=parent)
   edges=dd.build.polyline(points,target=obj.definition,closed=True)
   obj.definition.native.CheckModel([e.native for e in edges],None)
   return obj
  with dd.edit.operation('fixture'):
   group=dd.build.component('scaled')
   child=surface('inside',[(0,0,0),(40,0,0),(40,30,0),(0,30,0)],group.definition)
   outside=surface('outside',[(-60,-60,35),(-15,-60,35),(-15,-20,35),(-60,-20,35)])
   matrix=core.CMatrix();matrix.SetAxis(0,V(0,2,0));matrix.SetAxis(1,V(-3,0,0));matrix.SetAxis(2,V(0,0,4));matrix.SetRow(3,V(185,40,25))
   group.native.SetTransform(matrix);dd.edit.touch(group)
  v.camera.position=QtGui.QVector3D(260,-380,450);v.camera.target=QtGui.QVector3D(50,30,30);v.camera.up=QtGui.QVector3D(0,0,1);v.camera.compute()
  def state():return tuple(tuple(getattr(v.camera,n).toTuple()) for n in ('position','target','up'))
  before=state();v.OpenComponent(group.native);v.OpenComponent(child.native);assert state()==before
  v.repaint();v.makeCurrent();v.paint_off_screen();v.doneCurrent()
  point=V(-39,-37,35);q=(v.ComputeProjectMatrix()*v.ComputeCameraMatrix()[0]).map(QtGui.QVector3D(*point.ToTuple()))
  pos=QtCore.QPoint(round((q.x()+1)*v.width()/2-.5),round((1-q.y())*v.height()/2-.5))
  from engine.tools.tool_select import SelectTool
  h.activate_tool(SelectTool)
  selection_tool=v.active_tool
  selection_tool.on_left_button_down(pos,QtCore.Qt.NoModifier)
  selection_tool.on_left_button_up(pos)
  assert not list(v.model.GetSelection()), 'Selection must exclude outside geometry'
  center=to_world(v,V(20,15,0))
  projected=(v.ComputeProjectMatrix()*v.ComputeCameraMatrix()[0]).map(QtGui.QVector3D(*center.ToTuple()))
  inside_pos=QtCore.QPoint(round((projected.x()+1)*v.width()/2-.5),round((1-projected.y())*v.height()/2-.5))
  selection_tool.on_left_button_down(inside_pos,QtCore.Qt.NoModifier)
  selection_tool.on_left_button_up(inside_pos)
  assert list(v.model.GetSelection()), 'Scoped single pick must find the active face'
  picker=selection_tool.pick_helper
  for only_active in (True,False):
      picker.Reset()
      assert picker.SinglePick(inside_pos.x(),inside_pos.y(),9,None,only_active), ('Inside face missing',only_active)
      hit=picker.PickedFace()
      assert hit is not None and hit.e.GetParentComponent()==v.model.GetActiveComponent()
      print('INSIDE_FACE_OK',only_active,hit.e.GetID(),flush=True)
  picker.Reset()
  assert not picker.SinglePick(pos.x(),pos.y(),9,None,True), 'Active-only pick included outside geometry'
  picker.Reset()
  assert picker.SinglePick(pos.x(),pos.y(),9,None,False), 'World pick excluded outside geometry'
  hit=picker.PickedFace()
  assert hit is not None and hit.e.GetParentComponent()!=v.model.GetActiveComponent()
  print('SINGLE_PICK_TRANSFORMED_NESTED_COMPONENT_AND_OUTSIDE_SCOPE_OK',flush=True)

 except Exception:errors.append(traceback.format_exc())
 finally:h.cancel_tool();h.release_model();h.hide();app.quit()
QtCore.QTimer.singleShot(1800,run);app.exec_()
for error in errors:print(error)
sys.exit(bool(errors))
