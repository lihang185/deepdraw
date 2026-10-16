import sys
from PySide2 import QtWidgets
from PySide2.QtCore import Slot
from Ui_main_window import Ui_MainWindow

import core
from tool_select import SelectTool
from tool_draw_line import DrawLineTool
from tool_draw_rect import DrawRectTool
from tool_push import PushTool
from tool_offset import OffsetTool
from tool_guide_line import GuideLineTool
import operations



class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
    
    def init_system(self):
        self.init_empty_model()
        
        self.select_tool = SelectTool(self.view)
        self.draw_line_tool = DrawLineTool(self.view)
        self.draw_rect_tool = DrawRectTool(self.view)
        self.push_tool = PushTool(self.view)
        self.offset_tool = OffsetTool(self.view)
        self.guide_line_tool = GuideLineTool(self.view)
        
        self.view.SetActiveTool(self.select_tool)
        
        try:
            hwnd = int(self.winId())
            core.license.start(hwnd, "1.0")
        except core.license.LicenseError:
            QtWidgets.QMessageBox.critical(
                self,
                "授权失败",
                "无法启用受保护功能，请在官网上下载最新版本\n\n"
            )
            sys.exit(1)

    def closeEvent(self, event):
        self.view.ReleaseModel()
        model = core.active_model()
        model.DisableUndo()
        model.Release()
        model.Deactivate()

        super().closeEvent(event)
    
    def init_empty_model(self):
        model = core.CModel()
        model.Activate()
        model.EnableUndo()
        core.set_active_model(model)
        # for view
        self.view.BindModel(model)
    
    #==================
    # Tool icon
    #==================
    @Slot()
    def on_actionSelect_triggered(self):
        self.view.SetActiveTool(self.select_tool)
    
    @Slot()
    def on_actionDrawLine_triggered(self):
        self.view.SetActiveTool(self.draw_line_tool)
    
    @Slot()
    def on_actionDrawRectangle_triggered(self):
        self.view.SetActiveTool(self.draw_rect_tool)
    
    @Slot()
    def on_actionPushPull_triggered(self):
        self.view.SetActiveTool(self.push_tool)
    
    @Slot()
    def on_actionOffset_triggered(self):
        self.view.SetActiveTool(self.offset_tool)
    
    @Slot()
    def on_actionGuideLine_triggered(self):
        self.view.SetActiveTool(self.guide_line_tool)
    
    @Slot()
    def on_actionUndo_triggered(self):
        #print("Undo")
        model = core.active_model()
        model.UndoManager().Undo()

        model.ClearSelection()
        self.view.MarkDirty()
        self.view.repaint()

    @Slot()
    def on_actionRedo_triggered(self):
        #print("Redo")
        model = core.active_model()
        model.UndoManager().Redo()

        model.ClearSelection()
        self.view.MarkDirty()
        self.view.repaint()
    
    @Slot()
    def on_actionTest_triggered(self):
        model = core.active_model()
        comp = model.GetActiveComponent()
        
        p1 = core.CVector3D(10, 10, 0)
        p2 = core.CVector3D(200, 10, 0)
        p3 = core.CVector3D(200, 200, 0)
        p4 = core.CVector3D(10, 200, 0)
        
        edge1 = comp.AddLine(p1, p2)
        edge2 = comp.AddLine(p2, p3)
        edge3 = comp.AddLine(p3, p4)
        edge4 = comp.AddLine(p4, p1)

        edge_ls = [edge1, edge2, edge3, edge4]
        comp.CheckModel(edge_ls, None)
        
        self.view.MarkDirty()
        self.view.repaint()

    #==================
    # Menu command
    #==================
    @Slot()
    def on_actionDelete_triggered(self):
        model = core.active_model()
        operations.op_delete_selected(model)
        # update view
        self.view.MarkDirty()
        self.view.repaint()


    @Slot()
    def on_actionDeleteAllGuide_triggered(self):
        model = core.active_model()
        operations.op_delete_all_guide_lines(model)
        # update view
        self.view.MarkDirty()
        self.view.repaint()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    MainWindow = MainWindow()
    MainWindow.show()
    MainWindow.init_system()
    sys.exit(app.exec_())
