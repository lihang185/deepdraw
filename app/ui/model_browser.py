"""Education model library: click to preview, double-click to place."""
import json
from pathlib import Path

from engine.qt import QtCore, QtGui, QtWidgets
from app.paths import DATA
from .Ui_model_browser import Ui_Form


class ModelBrowser(QtWidgets.QWidget, Ui_Form):
    model_requested = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.comLists.itemClicked.connect(self.show_model)
        self.comLists.itemDoubleClicked.connect(self.insert_model)
        self.load_library(DATA / 'components.json')

    def load_library(self, manifest):
        manifest = Path(manifest)
        self.comLists.clear()
        if not manifest.is_file():
            return
        for model in json.loads(manifest.read_text(encoding='utf-8-sig'))['list']:
            record = dict(model, directory=str(manifest.parent))
            item = QtWidgets.QListWidgetItem('{}\n{}'.format(model['name'], model.get('desc', '')))
            item.setData(QtCore.Qt.UserRole, record)
            preview = manifest.parent / (model['file'] + '.png')
            pixmap = QtGui.QPixmap(str(preview))
            if not pixmap.isNull():
                item.setIcon(QtGui.QIcon(pixmap.scaled(64, 64, QtCore.Qt.KeepAspectRatio,
                                                     QtCore.Qt.SmoothTransformation)))
            self.comLists.addItem(item)

    def show_model(self, item):
        model = item.data(QtCore.Qt.UserRole)
        preview = Path(model['directory']) / (model['file'] + '.png')
        pixmap = QtGui.QPixmap(str(preview))
        self.comPaint.clear()
        if not pixmap.isNull():
            self.comPaint.setPixmap(pixmap.scaled(92, 92, QtCore.Qt.KeepAspectRatio,
                                                 QtCore.Qt.SmoothTransformation))
            self.comPaint.setAlignment(QtCore.Qt.AlignCenter)
        self.comName.setText(model['name'])
        self.comDescription.setText(model.get('desc', ''))

    def insert_model(self, item):
        self.show_model(item)
        model = item.data(QtCore.Qt.UserRole)
        path = Path(model['directory']) / (model['file'] + '.dim')
        self.model_requested.emit(str(path))
