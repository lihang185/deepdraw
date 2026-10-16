"""Smoke-test a built Windows client and its isolated SKP converter.

Usage: python scripts/check_package.py path/to/DeepDrawEducation.exe
Only the child process created by this check is inspected and closed.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def windows_for(pid):
    user32 = ctypes.windll.user32
    windows = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    @callback_type
    def collect(hwnd, unused):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title, 512)
            windows.append((hwnd, title.value))
        return True
    user32.EnumWindows(collect, 0)
    return windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    exe = args.executable.resolve()
    report = ROOT/'runtime/test-results/package.json'
    report.parent.mkdir(parents=True, exist_ok=True)
    result = dict(executable=str(exe), startup=False, clean_exit=False, skp_conversion=False)
    with tempfile.TemporaryDirectory() as directory:
        process = subprocess.Popen([str(exe)], cwd=directory)
        try:
            window = None
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('Packaged client exited during startup: '+str(process.returncode))
                window = next((hwnd for hwnd,title in windows_for(process.pid) if title=='DeepDraw 教育版'), None)
                if window is not None:
                    break
                time.sleep(.1)
            if window is None:
                raise RuntimeError('No main window: '+repr(windows_for(process.pid)))
            time.sleep(2)
            from PySide2 import QtGui
            app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])
            image = app.primaryScreen().grabWindow(window)
            assert not image.isNull()
            image.save(str(report.with_name('packaged-window.png')))
            assert process.poll() is None
            result['startup'] = True
            ctypes.windll.user32.PostMessageW(wintypes.HWND(window), 0x0010, 0, 0)
            assert process.wait(timeout=15) == 0
            result['clean_exit'] = True
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
        legacy = exe.parent/'_internal/importers/sketchup'
        output = Path(directory)/'import.dim'
        converted = subprocess.run([str(exe),'--convert-skp',str(legacy),str(ROOT/'data/ren.skp'),str(output)],
                                   cwd=directory, timeout=45, capture_output=True)
        assert converted.returncode == 0, converted.stderr
        assert output.is_file() and output.stat().st_size > 100
        sys.path.insert(0,str(ROOT))
        from engine import core, model_files
        model = core.CModel()
        assert model_files.load_sketchup_model(model,str(output))
        assert list(model.GetTopComponent().EnumEntities())
        model.Release()
        result['skp_conversion'] = True
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Packaged GUI startup / clean exit / isolated SKP conversion PASS')


if __name__ == '__main__':
    main()
