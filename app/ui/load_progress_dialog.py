"""Loading UI refresh with user input, timers and model mutation excluded."""
import time
from engine.qt import QtCore, QtWidgets
from .Ui_load_progress_dialog import Ui_LoadProgressDialog
from engine.mutation_guard import human_callback


class LoadProgressDialog(QtWidgets.QDialog, Ui_LoadProgressDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)
        self.started = time.monotonic()
        self.last_update = 0
        self.choice_label.hide()
        self.choice_buttons.hide()
        self.choice_loop = None

    def ask_initialize(self):
        self.status_label.setText('模型读取完成')
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.choice_label.show()
        self.choice_buttons.show()
        self.adjustSize()
        self.initialize_button.setFocus()
        self.initialize_requested = False
        self.choice_loop = QtCore.QEventLoop(self)
        try:
            self.choice_loop.exec_()
            return self.initialize_requested
        finally:
            self.choice_loop.deleteLater()
            self.choice_loop = None
            self.choice_label.hide()
            self.choice_buttons.hide()
            self.adjustSize()

    @QtCore.Slot()
    @human_callback
    def on_initialize_button_clicked(self):
        if self.choice_loop is not None:
            self.initialize_requested = True
            self.choice_loop.quit()

    @QtCore.Slot()
    @human_callback
    def on_skip_button_clicked(self):
        if self.choice_loop is not None:
            self.choice_loop.quit()

    def reject(self):
        if self.choice_loop is not None:self.choice_loop.quit()

    def update_progress(self, stage, current=0, total=0):
        now = time.monotonic()
        if stage == getattr(self, 'stage', None) and current != total and now-self.last_update < .15:return
        self.stage = stage
        self.last_update = now
        self.status_label.setText('正在' + stage + '……')
        self.progress_bar.setRange(0, 100 if total else 0)
        if total:self.progress_bar.setValue(min(100, int(current*100/total)))
        detail = ('%.1f / %.1f MB · ' % (current/1048576, total/1048576)
                  if total and stage == '读取模型' else
                  '%d / %d 个组件 · ' % (current,total) if total else '')
        self.detail_label.setText(detail + '已用时 %d 秒' % (now-self.started))
        from engine.mutation_guard import suspend_mutations
        # repaint alone does not deliver the platform expose/backing-store events.
        # The document blocks service jobs; the view/pipeline block all drawing.
        with suspend_mutations():
            QtWidgets.QApplication.processEvents(
                QtCore.QEventLoop.ExcludeUserInputEvents |
                QtCore.QEventLoop.ExcludeSocketNotifiers |
                QtCore.QEventLoop.X11ExcludeTimers)
        self.repaint()
