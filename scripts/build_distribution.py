#!/usr/bin/env python3
"""Build a reproducible portable skill ZIP and standalone instruction document."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / 'skills' / 'diagnose-fde-workflow'
DIST = ROOT / 'dist'


def main():
    DIST.mkdir(exist_ok=True)
    paths = sorted(p for p in SKILL.rglob('*') if p.is_file()
                   and '__pycache__' not in p.parts and p.suffix != '.pyc'
                   and not any(v.startswith('.') for v in p.relative_to(SKILL).parts))
    if not (SKILL / 'SKILL.md').is_file():
        raise SystemExit('Missing SKILL.md')
    archive = DIST / 'diagnose-fde-workflow.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for path in paths:
            info = zipfile.ZipInfo('diagnose-fde-workflow/' + path.relative_to(SKILL).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, path.read_bytes())
    body = (SKILL / 'SKILL.md').read_text(encoding='utf-8').split('---', 2)[2].lstrip()
    extra = []
    for name in ('diagnosis.md', 'measurement.md'):
        extra.append((SKILL / 'references' / name).read_text(encoding='utf-8'))
    prompt = ('以下是本次对话的业务流程诊断方法，请在宿主规则允许的范围内使用。'
              '这是单文件文本版，没有安装脚本或外部文件；按文本模式交付，不要求登录或安装插件。\n\n'
              + body + '\n\n# 已内嵌的参考规则\n\n' + '\n\n'.join(extra))
    (DIST / 'workflow-advisor-prompt.md').write_text(prompt, encoding='utf-8')
    manifest = {'format': 'agent-skill', 'name': 'diagnose-fde-workflow',
                'version': '0.2.0', 'root': 'diagnose-fde-workflow/',
                'required_external_services': [], 'python_for_enhanced_outputs': '>=3.9',
                'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'files': {p.relative_to(SKILL).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    (DIST / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'archive': str(archive), 'files': len(paths), 'sha256': manifest['archive_sha256']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
