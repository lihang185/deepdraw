"""Read-only text returned by str(entity), the same representation as print(entity)."""
from engine.qt import QtCore, QtWidgets
from .Ui_object_properties_dialog import Ui_ObjectPropertiesDialog

class ObjectPropertiesDialog(QtWidgets.QDialog, Ui_ObjectPropertiesDialog):
    def __init__(self, parent, text):
        super().__init__(parent)
        self.setupUi(self)
        self.properties_text.setPlainText(text)

    @QtCore.Slot()
    def on_buttons_rejected(self):
        self.reject()
