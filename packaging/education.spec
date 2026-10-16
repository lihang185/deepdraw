# Independent education build. Run from the project root via build_education.cmd.
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).parent
native = root / 'engine/native/cp38'
binaries = [(str(native/name), 'engine/native/cp38') for name in
            ('editor2.cp38-win_amd64.pyd', 'deepdraw_render.pyd', 'deepdraw_fileio.dll')]
binaries += [(str(path), 'importers/sketchup')
             for path in (root/'importers/sketchup').iterdir()
             if path.is_file() and path.suffix.lower() in ('.pyd', '.dll')]
# Model libraries, textures and user plugins stay external beside the executable.
# UI icons are already compiled into app.ui.resources_rc.
datas = []
hiddenimports = collect_submodules('engine.tools') + collect_submodules('editing')
hiddenimports += collect_submodules('app.ui') + ['app.extensions.api', 'importers.sketchup.convert',
    'importers.sketchup.import_model', 'importers.sketchup.native', 'engine.sketchup_export']
a = Analysis([str(root/'editor.py')],
    pathex=[str(root), str(native)], binaries=binaries, datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['sbksueditor','binary_file_v2','service','modeling','mcp','onethingai'],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='DeepDrawEducation',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, icon=str(root/'assets/app.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='DeepDrawEducation')
