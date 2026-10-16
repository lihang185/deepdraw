"""Native selection after grouping, undo, redo and rollback."""
import sys,traceback
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from engine import core
from engine.qt import QtCore,QtWidgets
from app.main_window import EditorMainWindow
app=QtWidgets.QApplication([])
h=EditorMainWindow();h.show()
errors=[]
def run():
    try:
        assert h.ready, h.startup_error or 'Editor initialization not ready'
        from engine.native import editor2
        from datetime import datetime
        binding=Path(editor2.__file__)
        print('ENGINE',str(binding),'MODIFIED',datetime.fromtimestamp(binding.stat().st_mtime),flush=True)
        from engine.qt import QtGui
        from engine.tools.tool_select import SelectTool
        dd=h.editing;model=h.view.model;V=core.CVector3D
        with dd.edit.operation('fixtures'):
            for i in range(3):
                obj=dd.build.component('part'+str(i)).native
                dd.build.line((0,0,0),(30,30,30),target=dd.wrap(obj.GetDefinition()))
                m=core.CMatrix();m.Translate(200+i*80,100,0);obj.SetTransform(m)
        ids=[dd.scene.named('part'+str(i)).one().id for i in range(3)]
        def dump(stage):
            rows=[]
            for e in model.GetTopComponent().EnumEntities():
                if isinstance(e,core.CComponentInstance):
                    parent=e.GetParentComponent()
                    rows.append(dict(id=e.GetID(),name=e.name,deleted=e.IsMarkedDeleted(),
                                     parent=None if parent is None else parent.GetID()))
            print('ROOT_INSTANCES',stage,rows,flush=True)
        dump('before group')
        h.fit_view();h.view.repaint()
        def check(stage):
            h.activate_tool(SelectTool)
            for i,ident in enumerate(ids):
                parent=model.GetTopComponent().GetEntityById(ident).GetParentComponent()
                print('PICK_TARGET',stage,ident,'parent',None if parent is None else parent.GetID(),flush=True)
                point=V(215+i*80,115,15)
                q=(h.view.ComputeProjectMatrix()*h.view.ComputeCameraMatrix()[0]).map(QtGui.QVector3D(*point.ToTuple()))
                pos=QtCore.QPoint(round((q.x()+1)*h.view.width()/2-.5),round((1-q.y())*h.view.height()/2-.5))
                tool=h.view.active_tool
                picker=core.CPickHelper(h.view.view_proxy)
                picker.SinglePick(pos.x(),pos.y(),9,None, True)
                best=picker.BestPick()
                path=[] if not best else list(best.inst_path)+[best.e]
                print('NATIVE_PICK',stage,ident,[
                    (e.GetID(),type(e).__name__,None if e.GetParentComponent() is None else e.GetParentComponent().GetID())
                    for e in path],flush=True)
                print('PROMOTED',[e.GetID() for e in path if isinstance(e,core.CDrawingElement)
                    and e.GetParentComponent()==model.GetActiveComponent()],flush=True)
                tool.on_left_button_down(pos,QtCore.Qt.NoModifier);tool.on_left_button_up(pos)
                selected=[e.GetID() for e in model.GetSelection()]
                assert ident in selected,(stage,ident,selected)
            print('PICK_OK',stage,flush=True)
        check('before')
        model.SetSelection([model.GetTopComponent().GetEntityById(i) for i in ids])
        with dd.edit.operation('group'):
            group=dd.edit.group()
            print('NEW_GROUP_ID',group.id,'ORIGINAL_IDS',ids,flush=True)
        dump('grouped')
        h.view.repaint()
        dd.edit.undo();h.view.repaint()
        dump('undo')
        check('undo')
        dd.edit.redo();h.view.repaint()
        dd.edit.undo();h.view.repaint();check('redo undo')
        model.SetSelection([model.GetTopComponent().GetEntityById(i) for i in ids])
        try:
            with dd.edit.operation('cancel group'):
                dd.edit.group()
                raise RuntimeError('test rollback')
        except RuntimeError as error:
            assert str(error)=='test rollback'
        h.view.repaint();check('rollback')
    except Exception:errors.append(traceback.format_exc())
    finally:h.cancel_tool();h.release_model();h.hide();app.quit()
QtCore.QTimer.singleShot(1800,run)
app.exec_()
for error in errors:print(error)
sys.exit(bool(errors))
