"""Recursively convert SKP files to adjacent DAI files with the current engine.

Existing DAI files are backed up under runtime/skp-batch/<run>/backup before
replacement. Each file uses an isolated worker; failures leave its DAI intact.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.serialization import MAGIC


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def write_report(path, report):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(str(temporary), str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT, help='Input tree (default: education data)')
    parser.add_argument('--overwrite', action='store_true', help='Replace existing DAI files')
    parser.add_argument('--timeout', type=int, default=600, help='Seconds allowed per file')
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 8) or struct.calcsize('P') != 8:
        parser.error('Use CPython 3.8 x64, matching the education engine')
    directory = args.directory.resolve()
    if not directory.is_dir() or args.timeout <= 0:
        parser.error('Input directory must exist and timeout must be positive')
    sources = sorted((p for p in directory.rglob('*') if p.is_file() and p.suffix.lower() == '.skp' and not set(p.relative_to(directory).parts).intersection({'runtime','build','dist','output','.git'})),
                     key=lambda p: str(p).casefold())
    run_parent = ROOT/'runtime/skp-batch'
    run_parent.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=datetime.now().strftime('%Y%m%d-%H%M%S-'), dir=str(run_parent)))
    report_path = run/'report.json'
    report = dict(directory=str(directory), interpreter=sys.executable, total=len(sources),
                  succeeded=0, failed=0, status='running', results=[])
    write_report(report_path, report)
    runtime = ROOT/'importers/sketchup'
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    print('Found {} SKP files. Report: {}'.format(len(sources), report_path), flush=True)
    for index, source in enumerate(sources, 1):
        relative = source.relative_to(directory)
        destination = source.with_suffix('.dim')
        if destination.exists() and not args.overwrite:
            print('KEEP '+str(destination), flush=True)
            continue
        started = time.monotonic()
        record = dict(source=str(source), output=str(destination), status='failed')
        log = run/'logs'/relative.with_suffix('.log')
        log.parent.mkdir(parents=True, exist_ok=True)
        record['log'] = str(log)
        try:
            record['source_sha256'] = digest(source)
            # Stage beside the destination so replacement is atomic on its volume.
            with tempfile.TemporaryDirectory(prefix='.skp-convert-', dir=str(source.parent)) as scratch:
                staged = Path(scratch)/'converted.dim'
                command = [sys.executable, '-u', '-X', 'faulthandler', str(runtime/'convert.py'),
                           str(runtime), str(source), str(staged)]
                with log.open('wb') as stream:
                    result = subprocess.run(command, cwd=str(ROOT), env=env, stdout=stream,
                                            stderr=subprocess.STDOUT, timeout=args.timeout)
                if result.returncode:
                    raise RuntimeError('Import worker exited with code {}; see log'.format(result.returncode))
                with staged.open('rb') as stream:
                    if stream.read(len(MAGIC)) != MAGIC:
                        raise ValueError('Invalid DAI output header')
                if digest(source) != record['source_sha256']:
                    raise RuntimeError('Source SKP changed during conversion; output not replaced')
                record['output_sha256'] = digest(staged)
                if destination.exists():
                    backup = run/'backup'/relative.with_suffix('.dim')
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    record['previous_sha256'] = digest(destination)
                    shutil.copy2(str(destination), str(backup))
                    if digest(backup) != record['previous_sha256']:
                        raise RuntimeError('Backup verification failed; output not replaced')
                    record['backup'] = str(backup)
                os.replace(str(staged), str(destination))
            record['status'] = 'succeeded'
            report['succeeded'] += 1
            print('[{}/{}] OK {}'.format(index, len(sources), relative), flush=True)
        except Exception as error:
            record['error'] = str(error)
            report['failed'] += 1
            print('[{}/{}] FAILED {}: {}'.format(index, len(sources), relative, error), flush=True)
        record['seconds'] = round(time.monotonic() - started, 3)
        report['results'].append(record)
        write_report(report_path, report)
    report['status'] = 'completed' if not report['failed'] else 'completed_with_errors'
    write_report(report_path, report)
    print('Finished: {} succeeded, {} failed. Report: {}'.format(report['succeeded'], report['failed'], report_path), flush=True)
    return 1 if report['failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
