"""Opt-in floating statistics. Hiding the dock detaches collection and stops its timer."""
from engine.qt import QtCore,QtWidgets
from engine.viewer.render_stats import RenderStats
from .Ui_render_stats_dock import Ui_RenderStatsDock

METRICS=(('total','主渲染 CPU (ms)',True),('update','场景更新 (ms)',True),
         ('enumerate_ms','  节点枚举 (ms)',True),('tree_ms','  建树 (ms)',True),
         ('context_ms','  编辑路径切换 (ms)',True),('cull_ms','  视锥裁剪 (ms)',True),
         ('geometry_ms','  几何缓存构建 (ms)',True),('faces','不透明面 (ms)',True),
         ('edges','边线 / 辅助线 (ms)',True),('transparent','透明面 (ms)',True),
         ('shadow','阴影准备 / 叠加 (ms)',True),('selection','选择 / 包围框 (ms)',True),
         ('nodes','显示节点数（合批后）',False),('visible','可见节点数',False),
         ('plane_tests','bbox 平面测试次数',False),('draw_calls','VBO glDraw 调用数',False),
         ('triangles','提交三角形数',False),('lines','提交线段数',False),
         ('size_rejected','小物体过滤节点数（含子树）',False))
STAGES=(('opaque','不透明面'),('edges','边线/辅助线'),('transparent','透明面'),
        ('shadow','阴影'),('selection','选择/包围框'),('update','场景更新'),('other','其他'))

class RenderStatsDock(QtWidgets.QDockWidget,Ui_RenderStatsDock):
    def __init__(self,host):
        super().__init__(host);self.host=host;self.setupUi(self)
        self.metrics.setRowCount(len(METRICS));self.metrics.verticalHeader().hide()
        self.metrics.horizontalHeader().setSectionResizeMode(0,QtWidgets.QHeaderView.Stretch)
        for col in (1,2):self.metrics.horizontalHeader().setSectionResizeMode(col,QtWidgets.QHeaderView.ResizeToContents)
        for row,(_,label,_) in enumerate(METRICS):
            for col,text in enumerate((label,'—','—')):self.metrics.setItem(row,col,QtWidgets.QTableWidgetItem(text))
        self.stages.setRowCount(len(STAGES))
        for row,(_,label) in enumerate(STAGES):
            for col,text in enumerate((label,'—','—','—')):self.stages.setItem(row,col,QtWidgets.QTableWidgetItem(text))
        for table in (self.stages,self.batchReasons):
            table.verticalHeader().hide()
            table.horizontalHeader().setSectionResizeMode(0,QtWidgets.QHeaderView.Stretch)
            for col in range(1,table.columnCount()):table.horizontalHeader().setSectionResizeMode(col,QtWidgets.QHeaderView.ResizeToContents)
        self.batch_key=None
        self.tabs.currentChanged.connect(self.refresh_batches)
        self.timer=QtCore.QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.refresh)
        self.visibilityChanged.connect(self.visibility_changed)
        self.noCull.setChecked(host.actionTest4.isChecked())
        self.smallObjectPercent.setValue(getattr(host.view,'small_object_percent',2.5))
        host.actionTest4.toggled.connect(self.noCull.setChecked)
        host.about_to_release.connect(self.reset)
    def reset(self):
        self.batch_key=None;self.batchReasons.setRowCount(0);self.batchSummary.setText('等待场景就绪…')
        for row in range(len(STAGES)):
            for col in (1,2,3):self.stages.item(row,col).setText('—')
        stats=getattr(self.host.view,'render_stats',None)
        if stats is not None:stats.reset()
        self.summary.setText('等待视图刷新…')
        for row in range(len(METRICS)):
            for col in (1,2):self.metrics.item(row,col).setText('—')
    def visibility_changed(self,visible):
        self.host.actionRenderStats.setChecked(visible)
        if visible:
            self.host.view.render_stats=RenderStats();self.reset();self.timer.start();self.host.view.update()
        else:
            self.timer.stop();self.host.view.render_stats=None
            self.noEdges.setChecked(False);self.noShadows.setChecked(False)
            self.noTransparent.setChecked(False)
    def refresh(self):
        stats=getattr(self.host.view,'render_stats',None)
        if stats is None:return
        self.refresh_batches()
        result=stats.take()
        if result is None:
            self.summary.setText('无新绘制帧 · 保留上次结果');return
        means,maxima,fps,frames=result
        self.summary.setText('实际刷新 %.1f FPS · 本周期 %d 帧（静止时按需刷新）'%(fps,frames))
        for row,(key,_,decimal) in enumerate(METRICS):
            for col,values in ((1,means),(2,maxima)):
                value=values.get(key)
                self.metrics.item(row,col).setText('—' if value is None else
                    ('%.3f'%value if decimal else format(round(value),',')))
        for row,(stage,_) in enumerate(STAGES):
            for col,field in enumerate(('calls','triangles','lines'),1):
                self.stages.item(row,col).setText(format(round(means.get(stage+'_'+field,0)),','))
    def refresh_batches(self,*args):
        if not self.isVisible() or self.tabs.currentWidget()!=self.batchesTab:return
        if self.host.input_busy or self.host.editing is None or self.host.editing.edit.active is not None:return
        pipeline=self.host.view.pipeline
        scene=getattr(pipeline,'_world_scene',None)
        if scene is None or scene.context_path is None:return
        key=(id(scene),pipeline.resource_revision,scene.context_path)
        if key==self.batch_key:return
        from engine.viewer.batch_diagnostics import diagnose,REASONS
        result=diagnose(pipeline);self.batch_key=key
        from engine.viewer.subtree_batches import MIN_NODES,MAX_NODES,MAX_ENTITIES
        self.batchSummary.setText(
            '面/边线显示节点：{nodes:,} · 合批节点：{batched:,}\n其中分阶段合批：{partial:,}（透明面保留原顺序）\n面/边线合并省去：{saved:,} 个节点 · 诊断耗时：{milliseconds:.1f} ms'.format(**result)
            +'\n子树门槛：%d–%d 节点，边＋面数量 ≤ %s'%(MIN_NODES,MAX_NODES,format(MAX_ENTITIES,',')))
        rows=[r for r in REASONS if result['counts'][r]]
        self.batchReasons.setRowCount(len(rows))
        for row,reason in enumerate(rows):
            for col,text in enumerate((reason,format(result['counts'][reason],','),format(result['branches'][reason],','))):
                self.batchReasons.setItem(row,col,QtWidgets.QTableWidgetItem(text))
    @QtCore.Slot(bool)
    def on_noCull_toggled(self,checked):
        if self.host.actionTest4.isChecked()!=checked:self.host.actionTest4.trigger()
    @QtCore.Slot(float)
    def on_smallObjectPercent_valueChanged(self,value):
        self.host.view.small_object_percent=value;self.host.view.update()
    @QtCore.Slot(bool)
    def on_noEdges_toggled(self,checked):
        self.host.view.test_hide_edges=checked;self.host.view.update()
    @QtCore.Slot(bool)
    def on_noShadows_toggled(self,checked):
        self.host.view.test_disable_shadows=checked;self.host.view.update()
    @QtCore.Slot(bool)
    def on_noTransparent_toggled(self,checked):
        self.host.view.test_hide_transparent=checked;self.host.view.update()
