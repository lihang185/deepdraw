"""Single education entry point, shared by source and packaged application."""
import sys

# Keep Qt alive until interpreter shutdown: extension managers retain windows.
_application = None

def main():
    global _application
    if len(sys.argv) > 1 and sys.argv[1] == '--convert-skp':
        del sys.argv[1]
        from importers.sketchup.convert import main as convert
        convert()
        return 0
    from PySide2 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    _application = app
    app.setApplicationName('DeepDraw Education')
    from app.main_window import EditorMainWindow
    from app.paths import DATA
    startup = DATA / 'ren.dim'
    window=EditorMainWindow(startup_model=startup if startup.is_file() else None)
    window.show()
    return app.exec_()
