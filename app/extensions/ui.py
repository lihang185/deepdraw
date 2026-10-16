from PySide2 import QtCore
from PySide2 import QtGui
from PySide2.QtWidgets import QToolBar, QAction, QMessageBox
from PySide2.QtCore import Slot

class UICommand(QAction):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.triggered.connect(self.on_triggered)
    
    def set_ico(self, icon_path):
        icon1 = QtGui.QIcon()
        icon1.addFile(icon_path, QtCore.QSize(), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setIcon(icon1)
    
    def set_tool_tip(self, text):
        self.setToolTip(text)
    
    @Slot()
    def on_triggered(self):
        self.parent().run_action(self.callback)

class UIManager:
    def __init__(self, main_window):
        self.name = "plugins"
        self.main_window = main_window
        self.toolbar_ls = []
    
    @classmethod
    def create(cls, main_window):
        cls._instance = UIManager(main_window)
        return cls._instance
    
    @classmethod
    def instance(cls):
        return cls._instance
    
    def new_toolbar(self, name):
        toolBar = QToolBar(self.main_window)
        toolBar.setObjectName(name)
        toolBar.setWindowTitle(name)
        toolBar.setMovable(True)
        toolBar.setIconSize(QtCore.QSize(32, 32))
        self.toolbar_ls.append(toolBar)
        
        self.main_window.addToolBar(QtCore.Qt.TopToolBarArea, toolBar)
        
        return toolBar
    
    def new_command(self, name, callback):
        command = UICommand(self.main_window, callback)
        command.setObjectName(name)
        return command
    
    def get_main_window(self):
        return self.main_window
    
    def set_status_bar(self, msg):
        self.main_window.statusBar().showMessage(msg)
    
    def message_box(self, msg, title="提示信息"):
        QMessageBox.information(None, title, msg)

