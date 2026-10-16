"""Education asset browsers hosted in the shared tabbed sidebar."""
from engine.qt import QtWidgets
from .Ui_model_library_dock import Ui_ModelLibraryDock

class ModelLibraryDock(QtWidgets.QDockWidget, Ui_ModelLibraryDock):
    def __init__(self, host, browser, name, title):
        super().__init__(host)
        self.setupUi(self)
        self.setObjectName(name)
        self.setWindowTitle(title)
        self.browser = browser
        self.contentLayout.addWidget(browser)

