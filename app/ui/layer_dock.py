"""Native model layer list. UI retains IDs, never native objects between callbacks."""
from engine import core
from engine.qt import QtCore,QtGui,QtWidgets
from engine.mutation_guard import human_callback,check_mutation
from .Ui_layer_dock import Ui_LayerDock


class LayerDock(QtWidgets.QDockWidget,Ui_LayerDock):
    def __init__(self,host):
        super().__init__(host);self.host=host;self.snapshot=None;self.setupUi(self)
        self.scene_snapshot = None
        self.panelSplitter.setSizes([320, 220])
        self.layers.verticalHeader().hide()
        self.layers.horizontalHeader().setSectionResizeMode(0,QtWidgets.QHeaderView.Stretch)
        for col in (1,2):self.layers.horizontalHeader().setSectionResizeMode(col,QtWidgets.QHeaderView.ResizeToContents)
        self.timer=QtCore.QTimer(self);self.timer.setInterval(250);self.timer.timeout.connect(self.refresh)
        self.visibilityChanged.connect(self.visibility_changed)
        host.about_to_release.connect(self.clear)
        host.model_changed.connect(self.refresh)

    def visibility_changed(self,visible):
        if visible:self.refresh();self.timer.start()
        else:self.timer.stop()

    def clear(self):
        self.snapshot=None;self.layers.blockSignals(True);self.layers.setRowCount(0);self.layers.blockSignals(False)
        self.scene_snapshot = None
        self.scenes.clear()

    def ready(self):
        session=self.host.editing
        return session is not None and session.alive and not self.host.input_busy and session.edit.active is None

    def live(self):return [e for e in self.host.view.model.GetLayers() if not e.IsMarkedDeleted()]

    def resolve(self,ident):
        return next((e for e in self.live() if e.GetID()==ident),None)

    @human_callback
    def refresh(self):
        if not self.ready():return
        self.refresh_scenes()
        rows=[(None,'默认图层',False,(.7,.7,.7))]
        for layer in self.live():
            color=layer.mtl.color if layer.mtl is not None else core.CVector3D(.7,.7,.7)
            rows.append((layer.GetID(),layer.name,layer.is_hide,tuple(color.ToTuple())))
        key=(self.host.editing.token,rows)
        if key==self.snapshot:return
        selected=self.layers.item(self.layers.currentRow(),0)
        ident=selected.data(QtCore.Qt.UserRole) if selected else None
        self.layers.blockSignals(True)
        try:
            self.layers.setRowCount(len(rows))
            for row,(uid,name,hidden,color) in enumerate(rows):
                item=QtWidgets.QTableWidgetItem(name);item.setData(QtCore.Qt.UserRole,uid);self.layers.setItem(row,0,item)
                visible=QtWidgets.QTableWidgetItem();visible.setFlags(QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsUserCheckable)
                visible.setCheckState(QtCore.Qt.Unchecked if hidden else QtCore.Qt.Checked);self.layers.setItem(row,1,visible)
                swatch=QtWidgets.QTableWidgetItem();swatch.setFlags(QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable)
                swatch.setBackground(QtGui.QColor.fromRgbF(*[max(0,min(1,c)) for c in color]));swatch.setToolTip('双击修改图层颜色');self.layers.setItem(row,2,swatch)
                if uid is None:
                    item.setFlags(QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable)
                    visible.setFlags(QtCore.Qt.ItemIsSelectable)
                    swatch.setToolTip('默认图层')
                if uid==ident:self.layers.selectRow(row)
            self.snapshot=key
        finally:self.layers.blockSignals(False)

    def refresh_scenes(self, select=None):
        from engine.scenes import read
        rows = [(s['id'], s['name']) for s in read(self.host.view.model)]
        key = (self.host.editing.token, rows)
        if key == self.scene_snapshot and select is None:
            return
        selected = select or self.scene_id()
        self.scenes.blockSignals(True)
        try:
            self.scenes.clear()
            for ident, name in rows:
                item = QtWidgets.QListWidgetItem(name)
                item.setData(QtCore.Qt.UserRole, ident)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                self.scenes.addItem(item)
                if ident == selected:
                    self.scenes.setCurrentItem(item)
            self.scene_snapshot = key
        finally:
            self.scenes.blockSignals(False)

    def scene_id(self):
        item = self.scenes.currentItem()
        return item.data(QtCore.Qt.UserRole) if item else None

    def edit_scene(self, action, name=None):
        ident = self.host.scenes.edit(action, self.scene_id(), name)
        self.refresh_scenes(ident)

    @QtCore.Slot()
    @human_callback
    def on_addSceneButton_clicked(self):
        self.host.run_action(self.edit_scene, 'add')

    @QtCore.Slot()
    @human_callback
    def on_deleteSceneButton_clicked(self):
        self.host.run_action(self.edit_scene, 'delete')

    @QtCore.Slot()
    @human_callback
    def on_updateSceneButton_clicked(self):
        self.host.run_action(self.edit_scene, 'update')

    @QtCore.Slot()
    @human_callback
    def on_applySceneButton_clicked(self):
        self.host.run_action(self.host.scenes.apply, self.scene_id())
        self.refresh()

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    @human_callback
    def on_scenes_itemDoubleClicked(self, item):
        self.host.run_action(self.host.scenes.apply, item.data(QtCore.Qt.UserRole))
        self.refresh()

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    @human_callback
    def on_scenes_itemChanged(self, item):
        self.host.run_action(self.edit_scene, 'rename', item.text())
        self.scene_snapshot = None
        self.refresh()

    def change(self,label,callback):
        check_mutation()
        if not self.ready():raise ValueError('请先完成当前操作')
        dd=self.host.editing
        with dd.edit.operation(label):
            callback()
            dd.edit.touch(dd.wrap(dd.model.GetTopComponent()))
        self.host.view.MarkDirty();self.host.view.update();self.refresh()

    @QtCore.Slot()
    def on_addButton_clicked(self):self.host.run_action(self.add_layer)

    def add_layer(self):
        def create():
            model=self.host.view.model;names={e.name for e in self.live()};i=1
            while '图层%d'%i in names:i+=1
            factory=core.CEntityFactory(model)
            layer=factory.NewLayer() if hasattr(factory,'NewLayer') else core.CLayer.Load('',False,None).AddToUndoManager()
            layer.name='图层%d'%i;model.addLayer(layer)
        self.change('新建图层',create)

    @QtCore.Slot()
    def on_deleteButton_clicked(self):self.host.run_action(self.delete_layer)

    def delete_layer(self):
        item=self.layers.item(self.layers.currentRow(),0)
        if item is None:return
        if item.data(QtCore.Qt.UserRole) is None:raise ValueError('默认图层不能删除')
        check_mutation()
        if not self.ready():raise ValueError('请先完成当前操作')
        ident=item.data(QtCore.Qt.UserRole)
        layer=self.resolve(ident)
        if layer is None:return
        def members(target):
            model=self.host.view.model
            return [(comp,e) for comp in [model.GetTopComponent()]+list(model.GetDefinitionList())
                    if not comp.IsMarkedDeleted() for e in comp.EnumEntities()
                    if isinstance(e,core.CDrawingElement) and not e.IsMarkedDeleted()
                    and e.GetLayer()==target]
        occupied=bool(members(layer))
        if occupied:
            state=(self.host.editing.token,self.host.editing.revision)
            # Never retain native pointers across the modal event loop.
            layer=None
            answer=QtWidgets.QMessageBox.question(
                self,'删除图层','图层里有对象，是否将对象移至默认图层并删除此图层？',
                QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.Cancel,QtWidgets.QMessageBox.Cancel)
            if answer!=QtWidgets.QMessageBox.Yes:return
            check_mutation()
            if not self.ready() or state!=(self.host.editing.token,self.host.editing.revision):
                raise ValueError('模型已改变，请重新删除图层')
            layer=self.resolve(ident)
            if layer is None:raise ValueError('图层已不存在')
        def remove():
            touched=set()
            for comp,entity in members(layer):
                entity.Record(True)
                entity.SetLayer(None)
                if comp.GetID() not in touched:
                    self.host.editing.edit.touch(self.host.editing.wrap(comp))
                    touched.add(comp.GetID())
            layer.DeleteByUndoManager()
        self.change('删除图层并移至默认图层' if occupied else '删除图层',remove)

    @QtCore.Slot()
    def on_assignButton_clicked(self):self.host.run_action(self.assign_selection)

    def assign_selection(self):
        item=self.layers.item(self.layers.currentRow(),0)
        if item is None:raise ValueError('请先在列表中选择目标图层')
        layer=self.resolve(item.data(QtCore.Qt.UserRole))
        model=self.host.view.model;selected=list(model.GetSelection())
        if (layer is None and item.data(QtCore.Qt.UserRole) is not None) or not selected:raise ValueError('请先选择场景对象和目标图层')
        if any(not isinstance(e,core.CDrawingElement) or e.IsMarkedDeleted()
               or e.GetParentComponent()!=model.GetActiveComponent() for e in selected):
            raise ValueError('只能分配当前编辑层的图形对象')
        def assign():
            for entity in selected:
                entity.Record(True)
                entity.SetLayer(layer)
            self.host.editing.edit.touch(self.host.editing.wrap(model.GetActiveComponent()))
        self.change('分配图层',assign)

    @QtCore.Slot(QtWidgets.QTableWidgetItem)
    def on_layers_itemChanged(self,item):
        def edit():
            identity=self.layers.item(item.row(),0)
            layer=self.resolve(identity.data(QtCore.Qt.UserRole))
            if layer is None:return
            if item.column()==0:
                name=item.text().strip()
                if not name or name=='默认图层' or any(e!=layer and e.name==name for e in self.live()):raise ValueError('图层名称不能为空或重复')
                self.change('重命名图层',lambda:setattr(layer,'name',name))
            elif item.column()==1:self.change('图层可见性',lambda:setattr(layer,'is_hide',item.checkState()!=QtCore.Qt.Checked))
        self.host.run_action(edit)
        self.snapshot=None;self.refresh()

    @QtCore.Slot(int,int)
    def on_layers_cellDoubleClicked(self,row,column):
        if column==2:self.host.run_action(self.choose_color,row)

    def choose_color(self,row):
        item=self.layers.item(row,0)
        if item is None or not self.ready():return
        ident=item.data(QtCore.Qt.UserRole)
        if ident is None:return
        token=self.host.editing.token
        revision=self.host.editing.revision
        color=QtWidgets.QColorDialog.getColor(self.layers.item(row,2).background().color(),self,'图层颜色')
        if not color.isValid():return
        check_mutation()
        if not self.ready() or self.host.editing.token!=token or self.host.editing.revision!=revision:
            raise ValueError('模型已改变，请重新选择图层颜色')
        layer=self.resolve(ident)
        if layer is None:raise ValueError('图层已不存在')
        def assign():
            material=core.CMaterial.Load('图层颜色：'+layer.name,core.CVector3D(color.redF(),color.greenF(),color.blueF()),False,1.,None)
            self.host.view.model.addMaterial(material);layer.mtl=material
        self.change('图层颜色',assign)
