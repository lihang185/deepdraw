"""Native action wiring, nearest quadrant, placement/scale and history checks."""
import sys,tempfile,traceback,math
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from engine import core
from engine.qt import QtCore,QtWidgets
from PySide2.QtTest import QTest
from app.main_window import EditorMainWindow
app=QtWidgets.QApplication([])
h=EditorMainWindow();h.show()
errors=[]
def run():
    try:
        dd=h.editing;model=h.view.model;V=core.CVector3D
        angles=[0,20,80,180,270,350,45,-45]
        expected=[90,90,180,270,0,90,180,90]
        with dd.edit.operation('fixtures'):
            objects=[]
            for i,angle in enumerate(angles):
                obj=dd.build.component('q'+str(i)).native
                dd.build.line((0,0,0),(10,10,10),target=dd.wrap(obj.GetDefinition()))
                a=math.radians(angle);m=core.CMatrix()
                m.SetAxis(0,V(2*math.cos(a),2*math.sin(a),0))
                m.SetAxis(1,V(-3*math.sin(a),3*math.cos(a),0));m.SetAxis(2,V(0,0,4))
                m.SetRow(3,V(i*50,17,23));obj.SetTransform(m);objects.append(obj)
        def check(values):
            for i,angle in enumerate(values):
                obj=dd.scene.named('q'+str(i)).one().native;m=obj.GetTransform();o=m.Transform(V())
                assert (o-V(i*50,17,23)).Length()<1e-6
                axes=[m.Transform(V(*p))-o for p in ((1,0,0),(0,1,0),(0,0,1))]
                for axis,size in zip(axes,(2,3,4)):assert abs(axis.Length()-size)<1e-6
                actual=math.degrees(math.atan2(axes[0].y,axes[0].x))%360
                assert abs((actual-angle+180)%360-180)<1e-6,(actual,angle)
        assert h.actionRotateNextQuadrant.shortcut().toString()=='Q'
        assert h.actionRotateNextQuadrant in h.menuTools.actions()
        model.SetSelection([objects[0]])
        h.show();h.activateWindow();h.view.setFocus()
        loop=QtCore.QEventLoop();QtCore.QTimer.singleShot(100,loop.quit);loop.exec_()
        QTest.keyClick(h.view,QtCore.Qt.Key_Q)
        for obj in objects[1:]:
            model.SetSelection([obj]);h.actionRotateNextQuadrant.trigger()
        check(expected)
        for _ in objects:dd.edit.undo()
        check(angles)
        for _ in objects:dd.edit.redo()
        check(expected)
        selected=[dd.scene.named('q'+str(i)).one().native for i in range(len(angles))]
        model.SetSelection(selected)
        original=[obj.GetTransform() for obj in selected]
        boxes=[dd.inspect.bounds(dd.wrap(obj)) for obj in selected]
        cx=(min(b['min'][0] for b in boxes)+max(b['max'][0] for b in boxes))/2
        cy=(min(b['min'][1] for b in boxes)+max(b['max'][1] for b in boxes))/2
        def check_group(turns):
            a=math.radians(90*turns)
            for i,initial in enumerate(original):
                current=dd.scene.named('q'+str(i)).one().native.GetTransform()
                for local in (V(),V(1,0,0),V(0,1,0),V(0,0,1)):
                    p=initial.Transform(local);dx,dy=p.x-cx,p.y-cy
                    expected_point=V(cx+dx*math.cos(a)-dy*math.sin(a),cy+dx*math.sin(a)+dy*math.cos(a),p.z)
                    assert (current.Transform(local)-expected_point).Length()<1e-6
        QTest.keyClick(h.view,QtCore.Qt.Key_Q);check_group(1)
        dd.edit.undo();check_group(0)
        dd.edit.redo();check_group(1)
        model.SetSelection([dd.scene.named('q'+str(i)).one().native for i in range(len(angles))])
        for turn in (2,3,4):
            h.actionRotateNextQuadrant.trigger();check_group(turn)
        from engine.tools.tool_rotate import RotateTool
        selected=[dd.scene.named('q'+str(i)).one().native for i in range(len(angles))]
        model.SetSelection(selected);h.activate_tool(RotateTool);tool=h.view.active_tool
        tool.center=V(15,25,0);tool.plane=core.CPlane(V(0,0,1),tool.center)
        tool.begin_rotate()
        before=[(e.GetID(),m) for e,m in tool.targets]
        tool.preview_angle(90)
        for ident,initial in before:
            entity=model.GetActiveComponent().GetEntityById(ident)
            for local in (V(),V(1,0,0),V(0,1,0)):
                p=initial.Transform(local)-tool.center
                expected=tool.center+V(-p.y,p.x,p.z)
                assert (entity.GetTransform().Transform(local)-expected).Length()<1e-6,(entity.GetTransform().Transform(local).ToTuple(),expected.ToTuple(),tool.transaction is None)
        tool.on_cancel()
        for ident,initial in before:
            entity=model.GetActiveComponent().GetEntityById(ident)
            assert (entity.GetTransform().Transform(V())-initial.Transform(V())).Length()<1e-6
        print('QUADRANT_AND_ROTATE_SHARED_PIVOT_OK',flush=True)
    except Exception:errors.append(traceback.format_exc())
    finally:h.cancel_tool();h.release_model();h.hide();app.quit();app.quit()
QtCore.QTimer.singleShot(1800,run)
app.exec_()
for error in errors:print(error)
sys.exit(bool(errors))
