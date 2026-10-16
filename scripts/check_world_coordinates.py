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
  debug_picker=selection_tool.pick_helper
  for only_active in (True,False):
      debug_picker.Reset()
      found=debug_picker.SinglePick(inside_pos.x(),inside_pos.y(),9,None,only_active)
      debug_hit=debug_picker.BestPick()
      print('SINGLE_PICK',only_active,found,None if debug_hit is None else (str(type(debug_hit.e)),debug_hit.e.GetParentComponent()==v.model.GetActiveComponent()),flush=True)
  for mode in (1,2):
      debug_picker.MultiSelect(v.width()//2,v.height()//2,v.width()-1,v.height()-1,mode)
      selected=list(debug_picker.GetSelected())
      print('MULTI_SELECT',mode,len(selected),[e.GetParentComponent()==v.model.GetActiveComponent() for e in selected],flush=True)
  assert list(v.model.GetSelection()), 'Scoped single pick must find the active face'
  for begin,end in [(QtCore.QPoint(0,0),QtCore.QPoint(v.width()-1,v.height()-1)),(QtCore.QPoint(v.width()-1,v.height()-1),QtCore.QPoint(0,0))]:
      selection_tool.on_left_button_down(begin,QtCore.Qt.NoModifier)
      selection_tool.on_left_button_up(end)
      scoped=list(v.model.GetSelection())
      assert scoped and all(e.GetParentComponent()==v.model.GetActiveComponent() for e in scoped), 'Scoped rectangle selection failed'
  v.model.ClearSelection()
  # Small rectangles verify projected location, not just whole-viewport membership.
  for mode in (1,2):
      debug_picker.MultiSelect(pos.x(),pos.y(),12,12,mode)
      assert not list(debug_picker.GetSelected()), 'Outside-only rectangle selected active geometry'
  edge_point=to_world(v,V(20,0,0))
  edge_projected=(v.ComputeProjectMatrix()*v.ComputeCameraMatrix()[0]).map(QtGui.QVector3D(*edge_point.ToTuple()))
  edge_x=round((edge_projected.x()+1)*v.width()/2-.5)
  edge_y=round((1-edge_projected.y())*v.height()/2-.5)
  debug_picker.MultiSelect(edge_x,edge_y,20,20,1)
  small_cross=list(debug_picker.GetSelected())
  print('SMALL_CROSS_ENTITIES',[(type(e).__name__,e.GetID()) for e in small_cross],flush=True)
  assert any(isinstance(e,core.CEdge) for e in small_cross), 'Small crossing rectangle missed transformed edge'
  assert all(e.GetParentComponent()==v.model.GetActiveComponent() for e in small_cross)
  debug_picker.MultiSelect(inside_pos.x(),inside_pos.y(),12,12,2)
  assert not any(isinstance(e,core.CFace) for e in debug_picker.GetSelected()), 'Inside mode accepted a partially enclosed face'
  print('MULTI_SELECT_SMALL_RECTANGLE_POSITION_AND_MODE_OK',flush=True)
  print('SCOPED_SINGLE_PICK_AND_BOTH_RECTANGLE_MODES_OK',flush=True)
  finder=core.CInputPointFinder(v.view_proxy);finder.Reset();assert finder.Inference(pos.x(),pos.y(),None,None)
  local=infer(v,finder,pos);actual=finder.Position();print('NATIVE_POSITION',actual.ToTuple(),flush=True)
  assert finder.snap_type==core.SnapType.face and (actual-point).Length()<2
  assert (to_world(v,local)-actual).Length()<1e-6
  ray=v.ComputePickRay(pos.x(),pos.y());native_ray=finder.pick_helper.GetPickRay()
  assert (ray.PointAt(0)-native_ray.PointAt(0)).Length()<1e-6
  h.activate_tool(SectionTool);v.active_tool.on_mouse_move(pos,QtCore.Qt.NoModifier);assert v.active_tool.plane is not None
  h.activate_tool(DrawLineTool);t=v.active_tool;t.prev_point=V(0,0,10);t.cur_point=V(1,0,10);t.first_point=t.prev_point
  start=t.prev_point;t.enterValue('10cm');assert abs(world_length(v,t.prev_point-start)-10)<1e-6
  assert abs((t.prev_point-start).Length()-5)<1e-6
  h.activate_tool(DrawRectTool);t=v.active_tool;t.state=2;t.start_point=V();t.end_point=V(1,1,0);t.dir_s=V(1,0,0);t.dir_t=V(0,1,0)
  captured=[];t.draw_rect_operation=lambda a,b:captured.extend(t.points(a,b));t.enterValue('10cm,12cm')
  assert abs(world_length(v,captured[1]-captured[0])-10)<1e-6
  assert abs(world_length(v,captured[3]-captured[0])-12)<1e-6
  h.activate_tool(DrawCircleTool);t=v.active_tool;t.center=V();t.end_point=V(1,0,0);t.plane=core.CPlane(V(0,0,1),V());t.dir_s=V(1,0,0);t.dir_t=V(0,1,0)
  captured=[];t.commit=lambda:captured.extend(t.points());t.enterValue('10cm,24')
  assert all(abs(world_length(v,p)-10)<1e-6 for p in captured)
  from engine.tools.tool_draw_arc import DrawArcTool
  from engine.tools.tool_guide_line import GuideLineTool
  h.activate_tool(DrawArcTool);t=v.active_tool;t.a=V();t.b=V(10,0,0);t.plane=core.CPlane(V(0,0,1),V());t.hover=V(5,5/3,0)
  assert abs(t.height()-5)<1e-6
  arc=[to_world(v,p) for p in t.arc_points(5)]
  a,b=to_world(v,t.a),to_world(v,t.b);direction=(b-a).Normalized()
  assert abs(max((p-a).Cross(direction).Length() for p in arc)-5)<.05
  h.activate_tool(GuideLineTool);t=v.active_tool;t.snap_line=True;t.line_origin=V();t.end_point=V(0,1,0);t.line_dir=V(1,0,0)
  captured=[];t.create_guide_line=lambda p,d:captured.append(p);t.enterValue('10cm')
  assert abs(world_length(v,captured[0])-10)<1e-6
  face=next(e for e in model.GetActiveComponent().EnumEntities() if isinstance(e,core.CFace))
  h.activate_tool(OffsetTool);t=v.active_tool;t.target_face=face;t.compute_offset(5)
  # Every new world vertex lies five cm from a pair of source supporting lines.
  world=[to_world(v,p) for p in t.offset_points]
  for p in world:
   distances=[]
   for eu in face.GetOuterLoop().EnumEdgeUse():
    a,b=to_world(v,eu.GetStartVertex().Pos()),to_world(v,eu.GetEndVertex().Pos())
    distances.append((p-a).Cross((b-a).Normalized()).Length())
   assert sum(abs(d-5)<1e-6 for d in distances)>=2
  h.activate_tool(PushTool);t=v.active_tool;t.transaction=object();t.direction=V(0,0,1);t.distance=1
  values=[];t.preview_distance=values.append;t.commit=lambda:setattr(t,'transaction',None);t.activate=lambda:None;t.enterValue(10)
  assert abs(values[0]-2.5)<1e-6
  v.CloseComponent();assert state()==before
  model.SetSelection([child.native]);h.activate_tool(MoveTool);t=v.active_tool;t.locked_axis='X';t.begin_move(V());t.preview_point(V(1,0,0));initial=child.native.GetTransform().Transform(V());t.enterValue('10cm')
  moved=child.native.GetTransform().Transform(V());assert abs(world_length(v,moved)-10)<1e-5
  assert abs(moved.y)<1e-6 and abs(moved.z)<1e-6
  v.CloseComponent();assert state()==before
  h.fit_view();v.repaint();v.makeCurrent()
  assert not model.HasError()
  print('CAMERA',state(),flush=True)
  from engine.qt import QOpenGLFramebufferObject,QOpenGLFramebufferObjectFormat
  fmt=QOpenGLFramebufferObjectFormat();fmt.setAttachment(QOpenGLFramebufferObject.CombinedDepthStencil)
  fbo=QOpenGLFramebufferObject(640,480,fmt);assert fbo.bind()
  v.is_offscreen_render=True;v.offscreen_width=640;v.offscreen_height=480
  v.gl.glViewport(0,0,640,480);v.paint_off_screen();image=fbo.toImage().copy()
  assert any(image.pixelColor(x,y).red()<230 for x in range(0,640,3) for y in range(0,480,3)),'Empty render'
  output=root/'runtime/world-coordinates.png';output.parent.mkdir(exist_ok=True);image.save(str(output))
  fbo.release();del fbo;v.is_offscreen_render=False;v.doneCurrent()
  print('EDUCATION_WORLD_PICK_RENDER_NUMERIC_LENGTH_LOCAL_AXES_OK',flush=True)
 except Exception:errors.append(traceback.format_exc())
 finally:h.cancel_tool();h.release_model();h.hide();app.quit()
QtCore.QTimer.singleShot(1800,run);app.exec_()
for error in errors:print(error)
sys.exit(bool(errors))
