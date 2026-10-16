"""Education plugin API backed by the current engine."""
from engine.core import *
from engine.core import core as cppcore
from PySide2.QtCore import QObject as ActionTarget, Slot as Action
from app.extensions.ui import UIManager
from app.extensions.manager import SimpleExtensionManager
UI = UIManager.instance()
ExtensionManager = SimpleExtensionManager.instance()

class IViewObserver:
    def onViewChanged(self, view):
        pass
