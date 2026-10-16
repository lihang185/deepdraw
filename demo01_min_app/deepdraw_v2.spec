# Build with build_exe.cmd; model data stays external.
from pathlib import Path
root = Path(SPECPATH)
a = Analysis([str(root/'main.py')], pathex=[str(root)],
    binaries=[(str(p), '.') for p in root.iterdir() if p.suffix.lower() in ('.pyd', '.dll')], datas=[],
    hiddenimports=['core', 'editor2', 'render_pipeline',
                   'push_pull_controller', 'PySide2.QtGui'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='DeepDrawV2',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='DeepDrawV2')
