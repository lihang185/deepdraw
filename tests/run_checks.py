"""Run the education migration checks using its own Python/native environment."""
import ast,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for directory in ('app','editing','engine','tests'):
 for path in (root/directory).rglob('*.py'):
  if '__pycache__' not in path.parts:ast.parse(path.read_text(encoding='utf-8-sig'),str(path))
for test in ('check_file_versions.py','check_native_v2_curves_layers.py','check_scene_file_layers.py','check_migration.py','check_tool_updates.py'):
 subprocess.run([sys.executable,str(root/'tests'/test)],cwd=str(root),check=True)
subprocess.run([sys.executable,str(root/'scripts/build_ui.py'),'--check'],cwd=str(root),check=True)
print('EDUCATION_MIGRATION_CHECKS_OK')
