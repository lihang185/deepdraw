"""Education material browser using the current client's Designer interface."""
from pathlib import Path
from engine.qt import QtCore, QtGui, QtWidgets
from engine.mutation_guard import human_callback, check_mutation
from editing.material_catalog import Catalog, add_root
from .Ui_material_library_dock import Ui_MaterialLibraryDock

class MaterialLibraryDock(QtWidgets.QDockWidget, Ui_MaterialLibraryDock):
    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.catalog = Catalog()
        self.scene_material = None
        self.setupUi(self)
        self.setObjectName('materialLibrary')
        self.setWindowTitle('材质库')
        self.material_texture_choose.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton))
        self.material_parameters.setEnabled(False)
        self.message.hide()
        if hasattr(self, 'search'):
            self.search.textChanged.connect(self.populate)
        self.refresh()
        self.show_scene_material(None)
        if hasattr(host, 'about_to_release'):
            host.about_to_release.connect(self.clear_scene_material)


    @QtCore.Slot()
    @human_callback
    def on_folder_button_clicked(self):
        self.choose_folder()


    @QtCore.Slot()
    @human_callback
    def on_refresh_button_clicked(self):
        self.refresh()


    @QtCore.Slot()
    @human_callback
    def on_apply_clicked(self):
        try:
            check_mutation()
            from engine.tools.tool_brush import BrushTool
            self.host.activate_tool(BrushTool)
            self.host.view.active_tool.set_material(None)
            self.show_scene_material(None)
            self.show_message('')
        except Exception as error:
            self.show_message(str(error))


    @QtCore.Slot()
    @human_callback
    def on_new_material_clicked(self):
        self.create_brush_material()


    @human_callback
    def create_brush_material(self, asset=None):
        try:
            check_mutation()
            dd = self.host.editing
            if dd.edit.active is not None:
                raise RuntimeError('请先确认或取消当前放置/编辑操作')
            if asset is None:
                names = {dd.model.getMaterial(i).name for i in range(dd.model.getNumMaterials())}
                name, number = '新建材质', 1
                while name in names:
                    number += 1
                    name = '新建材质 {}'.format(number)
                asset = dict(kind='material', name=name, properties=dict(name=name, color=[255, 255, 255]))
            with dd.edit.operation('新建材质 ' + asset['name']):
                result = dd.assets.create_material(asset)
            material = next(dd.model.getMaterial(i) for i in range(dd.model.getNumMaterials())
                            if dd.model.getMaterial(i).GetID() == result['material_id'])
            from engine.tools.tool_brush import BrushTool
            self.host.activate_tool(BrushTool)
            self.host.view.active_tool.set_material(material)
            self.host.view.MarkDirty()
            self.host.view.update()
            self.show_scene_material(material)
            self.show_message('')
        except Exception as error:
            self.show_message(str(error))


    def clear_scene_material(self):
        self.show_scene_material(None)


    def show_material_snapshot(self, asset):
        item = QtWidgets.QListWidgetItem(asset['name'])
        item.setData(QtCore.Qt.UserRole, asset)
        self.display_material(item)
        self.scene_material = asset


    def show_scene_material(self, material):
        def rgb(value):
            return [max(0, min(255, round(v * 255))) for v in (value.x, value.y, value.z)]
        properties = dict(name=material.name if material is not None else '默认材质',
                          color=rgb(material.color) if material is not None else [255, 255, 255],
                          use_opacity=bool(material.use_opacity) if material is not None else False,
                          opacity=float(material.opacity) if material is not None else 1.0,
                          edge_color=rgb(material.edge_color) if material is not None else [0, 0, 0],
                          use_edge_color=bool(material.use_edge_color) if material is not None else False)
        texture = material.GetTexture() if material is not None else None
        if texture is not None:
            properties.update(texture=texture.name or '内嵌贴图', size_u=texture.size_u,
                              size_v=texture.size_v, texture_bytes=bytes(texture.GetDib().GetData()))
        self.show_material_snapshot(dict(kind='material', name=properties['name'],
            path=str(Path.cwd() / 'scene-material'), properties=properties, scene_material=True,
            material_id=material.GetID() if material is not None else None,
            default_material=material is None,
            session_token=getattr(getattr(self.host, 'editing', None), 'token', None)))
        self.material_parameters.setEnabled(material is not None)


    def save_material_changes(self, changes, asset=None):
        asset = asset or self.scene_material
        if asset is None or asset.get('material_id') is None:
            return
        try:
            check_mutation()
            dd = self.host.editing
            if asset.get('session_token') != dd.token:
                raise ValueError('场景已切换，请重新拾取材质')
            material = next((dd.model.getMaterial(i) for i in range(dd.model.getNumMaterials())
                             if dd.model.getMaterial(i).GetID() == asset['material_id']
                             and not dd.model.getMaterial(i).IsMarkedDeleted()), None)
            if material is None:
                self.clear_scene_material()
                raise ValueError('材质已失效，请重新拾取')
            if 'texture' in changes:
                changes = dict(changes, texture_path=str((Path(asset['path']).parent / changes['texture']).resolve()))
            with dd.edit.operation('修改材质 ' + material.name):
                result = dd.assets.update_material(material.GetID(), changes)
            self.host.view.MarkDirty()
            self.host.view.update()
            material = next(dd.model.getMaterial(i) for i in range(dd.model.getNumMaterials())
                            if dd.model.getMaterial(i).GetID() == result['material_id'])
            brush = self.host.view.active_tool
            if getattr(brush, 'material_id', None) == asset['material_id']:
                brush.material_id = material.GetID()
            self.show_scene_material(material)
            self.show_message('')
        except Exception as error:
            self.show_message(str(error))


    @QtCore.Slot()
    @human_callback
    def on_material_name_editingFinished(self):
        if self.scene_material is None or self.scene_material.get('material_id') is None:
            return
        name = self.material_name.text().strip()
        old_name = self.scene_material['name']
        if not name:
            self.material_name.setText(old_name)
            return
        if name != old_name:
            self.save_material_changes({'name': name})


    @QtCore.Slot()
    @human_callback
    def on_material_texture_choose_clicked(self):
        asset = self.scene_material
        if asset is None:
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, '选择贴图', str(Path(asset['path']).parent),
            '图片 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)')
        if not path:
            return
        if QtGui.QPixmap(path).isNull():
            self.show_message('无法读取所选贴图')
            return
        import os
        try:
            texture = os.path.relpath(path, str(Path(asset['path']).parent))
        except ValueError:
            texture = str(Path(path).resolve())
        properties = asset['properties']
        self.save_material_changes(dict(texture=texture,
            size_u=properties.get('size_u', 100), size_v=properties.get('size_v', 100)), asset)


    @QtCore.Slot()
    @human_callback
    def on_material_size_u_editingFinished(self):
        self.save_material_changes({'size_u': self.material_size_u.value()})


    @QtCore.Slot()
    @human_callback
    def on_material_size_v_editingFinished(self):
        self.save_material_changes({'size_v': self.material_size_v.value()})


    @QtCore.Slot(bool)
    @human_callback
    def on_material_use_opacity_clicked(self, checked):
        self.save_material_changes({'use_opacity': checked})


    @QtCore.Slot(int)
    @human_callback
    def on_material_opacity_valueChanged(self, value):
        self.material_opacity_value.setText('{:.2f}'.format(value / 100.0))
        if not self.material_opacity.isSliderDown():
            self.save_material_changes({'opacity': value / 100.0})


    @QtCore.Slot()
    @human_callback
    def on_material_opacity_sliderReleased(self):
        self.save_material_changes({'opacity': self.material_opacity.value() / 100.0})


    @QtCore.Slot(bool)
    @human_callback
    def on_material_use_line_color_clicked(self, checked):
        self.save_material_changes({'use_edge_color': checked})


    @QtCore.Slot()
    @human_callback
    def on_material_line_color_clicked(self):
        asset = self.scene_material
        if asset is None:
            return
        properties = asset['properties']
        rgb = properties.get('edge_color', properties.get('line_color', [0, 0, 0]))
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(*rgb), self, '选择线段颜色')
        if color.isValid():
            self.save_material_changes({'edge_color': [color.red(), color.green(), color.blue()]}, asset)


    @QtCore.Slot()
    @human_callback
    def on_material_color_clicked(self):
        asset = self.scene_material
        if asset is None:
            return
        if asset['kind'] != 'material':
            return
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(*asset['properties'].get('color', [255, 255, 255])),
            self, '选择材质颜色')
        if not color.isValid():
            return
        self.save_material_changes({'color': [color.red(), color.green(), color.blue()]}, asset)


    @QtCore.Slot(QtWidgets.QListWidgetItem)
    @human_callback
    def on_items_itemDoubleClicked(self, item):
        self.create_brush_material(item.data(QtCore.Qt.UserRole))


    def choose_folder(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, '添加本地资源目录')
        if directory:
            add_root(directory)
            self.refresh()


    def refresh(self):
        try:
            selected=self.items.currentItem()
            ident=selected.data(QtCore.Qt.UserRole)['id'] if selected else None
            self.catalog.refresh()
            self.populate()
            if ident:
                for i in range(self.items.count()):
                    if self.items.item(i).data(QtCore.Qt.UserRole)['id']==ident:
                        self.items.setCurrentRow(i)
                        break
        except Exception as error:
            self.show_message(str(error))


    def populate(self, *args):
        self.items.clear()
        if hasattr(self, 'apply'):
            self.apply.setText('默认材质')
            self.apply.setEnabled(True)
        for asset in self.catalog.search(self.search.text() if hasattr(self, 'search') else '', 'material', limit=None):
            item = QtWidgets.QListWidgetItem(asset['name'])
            item.setData(QtCore.Qt.UserRole, asset)
            item.setToolTip(asset['description'] or asset['name'])
            image = self.pixmap(asset)
            item.setIcon(QtGui.QIcon(image))
            self.items.addItem(item)


    def pixmap(self, asset):
        image = QtGui.QPixmap(asset['preview']) if asset.get('preview') else QtGui.QPixmap()
        if image.isNull():
            image = QtGui.QPixmap(96, 96)
            color = asset.get('properties', {}).get('color', [210, 219, 229])
            image.fill(QtGui.QColor(*color))
        return image.scaled(220, 150, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)


    def display_material(self, item):
        self.material_name.clear()
        self.material_color.setEnabled(item is not None and
                                       item.data(QtCore.Qt.UserRole)['kind'] == 'material')
        self.material_color.setText('未选择材质')
        self.material_color.setStyleSheet('')
        self.material_texture.clear()
        self.material_texture.setToolTip('')
        self.material_texture_preview.clear()
        self.material_parameters.setEnabled(item is not None)
        blockers = [QtCore.QSignalBlocker(widget) for widget in (self.material_size_u, self.material_size_v,
                    self.material_use_opacity, self.material_opacity, self.material_use_line_color)]
        if item is None:
            return
        asset = item.data(QtCore.Qt.UserRole)
        properties = asset.get('properties', {})
        self.material_name.setText(properties.get('name', asset.get('name', '')))
        rgb = properties.get('color')
        if rgb is not None:
            color = QtGui.QColor(*rgb)
            self.material_color.setText('RGB ({}, {}, {})  {}'.format(*rgb[:3], color.name().upper()))
            foreground = '#000000' if color.lightness() > 128 else '#FFFFFF'
            self.material_color.setStyleSheet(
                'background-color: {}; color: {}; padding: 3px;'.format(color.name(), foreground))
        else:
            self.material_color.setText('未设置')
        texture = properties.get('texture_path') or properties.get('texture')
        self.material_texture.setText(Path(texture).name if texture else '无贴图')
        self.material_texture.setCursorPosition(0)
        self.material_texture.setToolTip(texture or '无贴图')
        if texture:
            preview = QtGui.QPixmap()
            if properties.get('texture_bytes'):
                preview.loadFromData(properties['texture_bytes'])
            else:
                preview.load(texture)
            if preview.isNull():
                self.material_texture_preview.setText('贴图无法加载')
            else:
                self.material_texture_preview.setPixmap(preview.scaled(
                    270, 150, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        else:
            preview = QtGui.QPixmap(270, 150)
            preview.fill(QtGui.QColor(*rgb) if rgb is not None else QtGui.QColor('#D2DBE5'))
            painter = QtGui.QPainter(preview)
            painter.setFont(self.font())
            badge = '默认' if asset.get('default_material') else '纯色'
            width = painter.fontMetrics().horizontalAdvance(badge) + 12
            rect = QtCore.QRect(270 - width - 4, 126, width, 20)
            painter.fillRect(rect, QtGui.QColor(0, 0, 0, 170))
            painter.setPen(QtGui.QColor('white'))
            painter.drawText(rect, QtCore.Qt.AlignCenter, badge)
            painter.end()
            self.material_texture_preview.setPixmap(preview)
        for name in ('size_u', 'size_v'):
            getattr(self, 'material_' + name).setValue(float(properties.get(name, 100)))
        self.material_use_opacity.setChecked(bool(properties.get('use_opacity', False)))
        opacity = float(properties.get('opacity', 1.0))
        self.material_opacity.setValue(round(opacity * 100))
        self.material_opacity_value.setText('{:.2f}'.format(opacity))
        self.material_opacity.setToolTip('opacity：0 为完全透明，1 为完全不透明')
        line_color = properties.get('edge_color', properties.get('line_color', [0, 0, 0]))
        color = QtGui.QColor(*line_color)
        self.material_line_color.setText('RGB ({}, {}, {})  {}'.format(*line_color[:3], color.name().upper()))
        foreground = '#000000' if color.lightness() > 128 else '#FFFFFF'
        self.material_line_color.setStyleSheet('background-color: {}; color: {}; padding: 3px;'.format(color.name(), foreground))
        custom = properties.get('use_edge_color', properties.get('use_line_color', False))
        self.material_use_line_color.setChecked(bool(custom))
        self.material_line_color.setEnabled(bool(custom))
        if not hasattr(self, '_material_parameters_height'):
            self.materialParametersLayout.invalidate()
            self._material_parameters_height = self.material_parameters.sizeHint().height()
            self.material_parameters.setFixedHeight(self._material_parameters_height)
        return
    def show_message(self, text):
        self.message.setText(text)
        self.message.setVisible(bool(text))


