"""Generate every Designer form and the single Qt resource module.

Use the engine's Python 3.8 environment. --check compares generated files without
changing them. All controllers/forms live in app.ui, so imports are relative.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'app/ui'


def tool(name):
    local = Path(sys.executable).parent / 'Scripts' / (name + '.exe')
    executable = str(local) if local.exists() else shutil.which(name)
    if not executable:
        raise SystemExit('Missing ' + name + '; use Python 3.8 with PySide2 installed')
    return executable


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    jobs = [([tool('pyside2-uic'), '--from-imports', str(form)],
             UI / ('Ui_' + form.stem + '.py')) for form in sorted(UI.glob('*.ui'))]
    jobs.append(([tool('pyside2-rcc'), str(ROOT / 'assets/resources.qrc')], UI / 'resources_rc.py'))
    errors = []
    with tempfile.TemporaryDirectory() as directory:
        for command, output in jobs:
            temporary = Path(directory) / output.name
            subprocess.run(command + ['-o', str(temporary)], check=True)
            generated = temporary.read_text(encoding='utf-8')
            if args.check:
                if not output.exists() or output.read_text(encoding='utf-8') != generated:
                    errors.append(str(output.relative_to(ROOT)))
            else:
                output.write_text(generated, encoding='utf-8')
    if errors:
        raise SystemExit('Regenerate UI/resources: ' + ', '.join(errors))
    print('Designer forms and resources OK')


if __name__ == '__main__':
    main()
