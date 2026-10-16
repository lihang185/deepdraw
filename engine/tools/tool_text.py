"""Text creation shares the component placement transaction, including cancellation."""
from .tool_comp_place import ComponentPlaceTool
from editing.text import build_definition


class TextPlaceTool(ComponentPlaceTool):
    def set_plan(self,plan):
        self.plan=plan

    def preview_point(self,point):
        if self.comp_def is None and getattr(self,'plan',None) is not None:
            self.begin_transaction('创建文字')
            self.comp_def=build_definition(self.view.mainWindow.editing,self.plan)
            self.plan=None
        super().preview_point(point)
