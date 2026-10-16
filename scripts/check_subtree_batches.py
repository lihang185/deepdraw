"""Real GL regression for shared subtree batches and edit invalidation."""
import sys,tempfile,traceback
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from engine import core
from engine.qt import QtCore,QtWidgets,QOpenGLFramebufferObject,QOpenGLFramebufferObjectFormat
from app.main_window import EditorMainWindow
app=QtWidgets.QApplication([])
host=EditorMainWindow();host.show()
output=Path(tempfile.mkdtemp(prefix='subtree-batches-',dir=str(root/'runtime')))
errors=[]
def run():
    try:
        dd=host.editing;v=host.view;p=v.pipeline;V=core.CVector3D
        v.batch_min_scene_nodes=0
        with dd.edit.operation('batch fixture'):
            leaf=dd.build.component('source')
            edges=dd.build.polyline([(0,0,0),(15,0,0),(15,18,0),(0,18,0)],target=leaf.definition,closed=True)
            leaf.definition.native.CheckModel([e.native for e in edges],None)
            leaf.native.SetHide(True)
            assembly=dd.build.component('assembly')
            factory=core.CEntityFactory(dd.model);children=[]
            for i in range(4):
                inst=factory.NewComponentInstance();inst.SetDefinition(leaf.definition.native)
                matrix=core.CMatrix();matrix.Translate(i*24,0,0);inst.SetTransform(matrix)
                assembly.definition.native.AddEntity(inst);children.append(inst)
            mirror=core.CMatrix();mirror.Scale3(-1,1,1);mirror.Translate(95,0,0)
            children[3].SetTransform(mirror)
            red=core.CMaterial.Load('red',V(.8,.15,.1),False,1,None);dd.model.addMaterial(red)
            children[1].SetMaterial(red)
            twin=factory.NewComponentInstance();twin.SetDefinition(assembly.definition.native)
            matrix=core.CMatrix();matrix.Translate(0,55,0);twin.SetTransform(matrix);dd.model.GetTopComponent().AddEntity(twin)
            dd.edit.touch(assembly.definition);dd.edit.touch(dd.scene.root)
        host.fit_view()
        def capture(enabled=True):
            v.subtree_batching=enabled
            v.makeCurrent()
            fmt=QOpenGLFramebufferObjectFormat();fmt.setAttachment(QOpenGLFramebufferObject.CombinedDepthStencil)
            fbo=QOpenGLFramebufferObject(480,480,fmt);assert fbo.bind()
            v.is_offscreen_render=True;v.offscreen_width=v.offscreen_height=480
            v.paint_off_screen();img=fbo.toImage().copy();img.save(str(output/'capture.png'))
            fbo.release();del fbo;v.is_offscreen_render=False;v.doneCurrent()
            return np.asarray(Image.open(output/'capture.png')).copy()
        def compare(label):
            b=capture(True);a=capture(False);rebuilt=capture(True)
            np.testing.assert_array_equal(b,rebuilt)
            delta=np.abs(a.astype(int)-b.astype(int))
            fraction=np.any(delta[:,:,:3]>8,axis=2).mean()
            assert fraction<.003,(label,fraction)
            print(label,'pixel_error',fraction,flush=True)
        compare('initial')
        assert len(p._instance_scene.nodes)==2
        cache=p.subtree_batches.caches[assembly.definition.native]
        assert cache.model_cache.build_count==1
        builds=cache.model_cache.build_count
        dd.selection.set(assembly);capture();assert cache.model_cache.build_count==builds
        compare('selection');dd.selection.clear()
        with dd.edit.operation('move root'):
            matrix=core.CMatrix();matrix.Translate(8,0,0);dd.edit.set_transform(assembly,matrix)
        capture();assert cache.model_cache.build_count==builds
        compare('root movement')
        face=next(e for e in leaf.definition.native.EnumEntities() if isinstance(e,core.CFace))
        v.model.OpenComponent(assembly.native);v.MarkViewDirty();compare('open with outer batch')
        v.model.CloseComponent();v.MarkViewDirty();compare('close with cached batch')
        red.use_opacity=True;compare('transparent material excludes subtree')
        red.use_opacity=False;compare('opaque material restores subtree')
        builds=cache.model_cache.build_count
        with dd.edit.operation('baked face visibility'):
            face.SetHide(True);dd.edit.touch(leaf.definition)
        compare('baked geometry invalidation')
        assert cache.model_cache.build_count==builds+1
        with dd.edit.operation('restore baked face'):
            face.SetHide(False);dd.edit.touch(leaf.definition)
        compare('restore baked geometry')
        with dd.edit.operation('mirror child'):
            matrix=core.CMatrix();matrix.Scale3(-1,1,1);matrix.Translate(45,0,0)
            dd.edit.set_transform(dd.wrap(children[2]),matrix)
        compare('child movement splits batch')
        assert children[2] in p.subtree_batches.dynamic
        assert len(p._instance_scene.nodes)>2
        revision=p.resource_revision
        for distance in (2,5,0):
            motion=core.CMatrix();motion.Translate(0,0,distance);children[2].m2=motion
            p.mark_instance_transform_dirty(children[2]);capture()
            assert p.resource_revision==revision, 'Dynamic branch rebuilt scene repeatedly'
        compare('animation after split')
        assembly_native=assembly.native;leaf_native=leaf.native
        dd.edit.undo();compare('undo')
        dd.edit.redo();compare('redo')
        assembly=dd.wrap(assembly_native);leaf=dd.wrap(leaf_native)
        v.model.OpenComponent(assembly.native);v.MarkViewDirty();compare('open component')
        v.model.CloseComponent();v.MarkViewDirty();compare('close component')
        # A geometry edit must update both shared occurrences, not unrelated data.
        face=next(e for e in leaf.definition.native.EnumEntities() if isinstance(e,core.CFace))
        with dd.edit.operation('hide face'):
            face.SetHide(True);dd.edit.touch(leaf.definition)
        compare('hidden face')
        host.configure_shadows(True);compare('shadow')
        print('SUBTREE_BATCH_PIXELS_SELECTION_TRANSFORM_NAVIGATION_HISTORY_SHADOW_OK',flush=True)
    except Exception:errors.append(traceback.format_exc());print(errors[-1],flush=True)
    finally:host.cancel_tool();host.release_model();host.hide();app.quit()
QtCore.QTimer.singleShot(1800,run);app.exec_();sys.exit(bool(errors))

