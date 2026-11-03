#!/usr/bin/env python3
"""Offline demonstration or custom-model run; Python standard library only."""
import argparse
import json
from pathlib import Path
import sys

import workflow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, help='UTF-8 workflow JSON; default is hypothetical demo')
    parser.add_argument('--output', required=True, type=Path, help='New or empty task directory')
    args = parser.parse_args()
    skill = Path(__file__).resolve().parent.parent
    try:
        dest = args.output.expanduser().resolve()
        if dest == skill or skill in dest.parents:
            raise ValueError('输出目录不能位于已安装的技能目录内')
        if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
            raise ValueError('输出目录已存在内容，请换一个空目录；不会覆盖已有文件')
        source = args.model or skill / 'assets' / 'quotation-example.json'
        model = json.loads(source.read_text(encoding='utf-8'))
        errors = workflow.validate(model)
        if errors:
            print(json.dumps({'valid': False, 'errors': errors}, ensure_ascii=False, indent=2))
            return 2
        result = workflow.calculate(model)
        dest.mkdir(parents=True, exist_ok=True)
        (dest / 'workflow.json').write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding='utf-8')
        (dest / 'metrics.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        workflow.render(model, dest / 'scene.html')
        workflow.storyboard(model, dest / 'storyboard.md')
        print(json.dumps({'valid': True, 'demo': args.model is None,
                          'output': str(dest), 'metrics': result,
                          'files': ['workflow.json', 'metrics.json', 'scene.html', 'scene.svg', 'storyboard.md']},
                         ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'valid': False, 'errors': [str(exc)]}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
