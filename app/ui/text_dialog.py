from engine.qt import QtCore,QtGui,QtWidgets
from .Ui_text_dialog import Ui_TextDialog
from editing.text import outline


class TextDialog(QtWidgets.QDialog,Ui_TextDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.fontInput.setCurrentFont(QtGui.QFont('Microsoft YaHei'))
        self.plan=None

    @QtCore.Slot(bool)
    def on_extrudeInput_toggled(self,checked):
        self.depthInput.setEnabled(checked)

    @QtCore.Slot()
    def on_buttons_accepted(self):
        try:
            self.plan=outline(self.textInput.toPlainText(),self.fontInput.currentFont(),
                              self.heightInput.value(),self.depthInput.value() if self.extrudeInput.isChecked() else 0,
                              error_percent=self.errorInput.value())
        except ValueError as exc:
            self.errorLabel.setText(str(exc));return
        self.accept()

    @QtCore.Slot()
    def on_buttons_rejected(self):
        self.reject()
