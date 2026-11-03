#!/usr/bin/env python3
"""Exercise the published archive in a fresh path, without third-party Python packages."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    manifest = json.loads((ROOT / 'dist/manifest.json').read_text(encoding='utf-8'))
    archive = ROOT / 'dist/diagnose-fde-workflow.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['archive_sha256']
    count = 1
    with tempfile.TemporaryDirectory(prefix='fde portable ') as folder:
        tmp = Path(folder)
        with zipfile.ZipFile(archive) as z:
            expected = {manifest['root'] + n for n in manifest['files']}
            assert set(z.namelist()) == expected
            for name in z.namelist():
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
                rel = name.removeprefix(manifest['root'])
                assert hashlib.sha256(z.read(name)).hexdigest() == manifest['files'][rel]
                assert z.read(name) == (ROOT / 'skills/diagnose-fde-workflow' / rel).read_bytes()
            z.extractall(tmp)
        count += 1
        skill = tmp / 'diagnose-fde-workflow'
        assert (skill / 'SKILL.md').is_file()
        count += 1
        script = skill / 'scripts/quickstart.py'

        def run(*args):
            result = subprocess.run([sys.executable, '-S', str(script), *map(str, args)],
                                    cwd=tmp, capture_output=True, text=True, encoding='utf-8')
            return result.returncode, json.loads(result.stdout)

        dest = tmp / 'demo output'
        code, result = run('--output', dest)
        assert code == 0 and result['valid'] and result['demo']
        assert all((dest / n).is_file() for n in result['files'])
        metrics = result['metrics']
        assert abs(metrics['before_min'] - 20) < 1e-8 and abs(metrics['after_min'] - 7.6) < 1e-8
        assert '尚未生成' in (dest / 'storyboard.md').read_text(encoding='utf-8')
        count += 1

        before = (dest / 'scene.html').read_bytes()
        code, result = run('--output', dest)
        assert code == 2 and not result['valid'] and (dest / 'scene.html').read_bytes() == before
        count += 1
        code, result = run('--output', skill / 'output')
        assert code == 2 and not (skill / 'output').exists()
        count += 1

        model = json.loads((skill / 'assets/quotation-example.json').read_text(encoding='utf-8'))
        custom = tmp / 'custom model.json'
        model['metrics'] = None
        custom.write_text(json.dumps(model, ensure_ascii=False), encoding='utf-8')
        code, result = run('--model', custom, '--output', tmp / 'unknown output')
        assert code == 0 and not result['demo'] and not result['metrics']['available']
        count += 1

        model = json.loads((skill / 'assets/quotation-example.json').read_text(encoding='utf-8'))
        model['metrics']['routes'][0]['weight'] = 0.4
        custom.write_text(json.dumps(model), encoding='utf-8')
        invalid_dest = tmp / 'invalid output'
        code, result = run('--model', custom, '--output', invalid_dest)
        assert code == 2 and not result['valid'] and not invalid_dest.exists()
        count += 1

        code, result = run('--model', tmp / 'missing.json', '--output', tmp / 'missing output')
        assert code == 2 and not result['valid']
        count += 1
    print(json.dumps({'passed': count, 'third_party_python_packages': False,
                      'checks': ['archive checksum', 'resource and source parity', 'entry point',
                                 'offline fresh-path execution with spaces', 'no overwrite',
                                 'no customer output in installed skill', 'missing metrics',
                                 'invalid model', 'missing input']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
