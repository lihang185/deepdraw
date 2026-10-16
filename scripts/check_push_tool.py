"""Exercise native face picking and real push mouse preview in a scaled component."""
import sys, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import core
from engine.qt import QtCore, QtGui, QtWidgets
from engine.coordinates import to_world, world_length
from engine.tools.tool_push import PushTool
from app.main_window import EditorMainWindow
app = QtWidgets.QApplication([])
h = EditorMainWindow(); h.show()
errors = []
def run():
    try:
        v = h.view; dd = h.editing; V = core.CVector3D
        with dd.edit.operation('push fixture'):
            obj = dd.build.component('scaled push')
            edges = dd.build.polyline([(0,0,0),(40,0,0),(40,30,0),(0,30,0)], target=obj.definition, closed=True)
            obj.definition.native.CheckModel([e.native for e in edges], None)
            matrix = core.CMatrix()
            matrix.SetAxis(0,V(2,0,0)); matrix.SetAxis(1,V(0,3,0)); matrix.SetAxis(2,V(0,0,4))
            obj.native.SetTransform(matrix); dd.edit.touch(obj)
        v.camera.position=QtGui.QVector3D(160,-240,280)
        v.camera.target=QtGui.QVector3D(40,45,0)
        v.camera.up=QtGui.QVector3D(0,0,1); v.camera.compute()
        v.OpenComponent(obj.native)
        v.makeCurrent(); v.paint_off_screen(); v.doneCurrent()
        def pixel(p):
            q=(v.ComputeProjectMatrix()*v.ComputeCameraMatrix()[0]).map(QtGui.QVector3D(*to_world(v,p).ToTuple()))
            return QtCore.QPoint(round((q.x()+1)*v.width()/2-.5),round((1-q.y())*v.height()/2-.5))
        messages=[]; original_status=v.setStatusBar
        def status(text):
            messages.append(text); original_status(text)
        v.setStatusBar=status
        h.activate_tool(PushTool); t=v.active_tool
        t.on_left_button_down(pixel(V(20,15,0)),QtCore.Qt.NoModifier)
        assert t.is_begin, messages
        t.on_mouse_move(pixel(V(20,15,12)),QtCore.Qt.NoModifier)
        assert t.is_begin and abs(t.distance)>core.EPS, messages
        assert any('推拉距离' in s for s in messages), messages
        direction=t.direction
        t.enterValue(10)
        assert not t.is_begin, messages
        vertices=[vertex for e in obj.definition.native.EnumEntities() if isinstance(e,core.CEdge) for vertex in (e.GetStartVertex(), e.GetEndVertex())]
        heights=[e.Pos().Dot(direction) for e in vertices]
        assert abs((max(heights)-min(heights))*world_length(v,direction)-10)<1e-5, heights
        print('NATIVE_PUSH_MOUSE_PREVIEW_AND_WORLD_10CM_OK',flush=True)
    except Exception:
        errors.append(traceback.format_exc())
    finally:
        h.cancel_tool(); h.release_model(); h.hide(); app.quit()
QtCore.QTimer.singleShot(1800,run)
app.exec_()
for error in errors: print(error)
sys.exit(bool(errors))

