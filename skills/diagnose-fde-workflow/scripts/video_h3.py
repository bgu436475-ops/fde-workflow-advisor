#!/usr/bin/env python3
"""H3 asynchronous video adapter. No bundled credentials; standard library only."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            before = urllib.parse.urlsplit(req.full_url)
            after = urllib.parse.urlsplit(newurl)
            if (before.scheme, before.netloc) != (after.scheme, after.netloc):
                redirected.remove_header('Authorization')
        return redirected


def clean(value, secret):
    if isinstance(value, dict):
        return {k: ('[hidden]' if re.search(r'api.?key|token|secret|authorization', k, re.I)
                    else clean(v, secret)) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v, secret) for v in value]
    return value.replace(secret, '[hidden]') if isinstance(value, str) and secret else value


class Client:
    def __init__(self, base, key):
        parsed = urllib.parse.urlsplit(base)
        if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('H3_BASE_URL must be an HTTPS API base without credentials or query parameters')
        if not key:
            raise ValueError('Configure H3_API_KEY in the host secret environment')
        self.base = base.rstrip('/')
        self.key = key
        self.opener = urllib.request.build_opener(SafeRedirect())

    def request(self, path, payload=None, binary=False):
        headers = {'Authorization': 'Bearer ' + self.key, 'Accept': 'video/mp4' if binary else 'application/json'}
        if payload is not None:
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request(self.base + path,
                                         data=None if payload is None else json.dumps(payload).encode('utf-8'),
                                         headers=headers)
        try:
            with self.opener.open(request, timeout=50) as response:
                if binary:
                    return response.read()
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            body = exc.read(8000).decode('utf-8', errors='replace').replace(self.key, '[hidden]')
            raise ValueError('H3 HTTP %s: %s' % (exc.code, body)) from None


def task_id(value):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,180}', value):
        raise argparse.ArgumentTypeError('Invalid video task ID')
    return value


def read_config(hidden):
    if not hidden:
        return {'base_url': os.environ.get('H3_BASE_URL', ''), 'api_key': os.environ.get('H3_API_KEY', '')}
    original = None
    if sys.stdin.isatty() and os.name == 'posix':
        import termios
        import copy
        settings = termios.tcgetattr(sys.stdin.fileno())
        original = copy.deepcopy(settings)
        settings[3] &= ~termios.ECHO
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, settings)
    print('Ready for API configuration on stdin (hidden).', flush=True)
    try:
        return json.loads(sys.stdin.readline())
    finally:
        if original is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, original)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config-stdin', action='store_true', help='Read host-supplied secret config from stdin; never include secrets in arguments')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('models')
    create = sub.add_parser('create')
    create.add_argument('--prompt-file', type=Path, required=True)
    create.add_argument('--model', default='h3-text')
    create.add_argument('--seconds', type=int, default=4)
    create.add_argument('--size', default='1280x720')
    create.add_argument('--output', type=Path, required=True, help='New task receipt file; submissions are never automatically retried')
    status = sub.add_parser('status')
    status.add_argument('id', type=task_id)
    download = sub.add_parser('download')
    download.add_argument('id', type=task_id)
    download.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    key = ''
    try:
        config = read_config(args.config_stdin)
        key = config.get('api_key', '')
        client = Client(config.get('base_url', ''), key)
        if args.command == 'models':
            result = client.request('/models')
        elif args.command == 'create':
            if args.output.exists():
                raise ValueError('Receipt already exists; inspect its task ID instead of resubmitting')
            prompt = args.prompt_file.read_text(encoding='utf-8').strip()
            if not prompt or len(prompt) > 15000 or not 1 <= args.seconds <= 30:
                raise ValueError('Use a nonempty prompt up to 15000 characters and 1–30 seconds; model limits may be narrower')
            result = client.request('/videos', {'model': args.model, 'prompt': prompt,
                                               'seconds': str(args.seconds), 'size': args.size})
            safe = clean(result, key)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('x', encoding='utf-8') as f:
                json.dump(safe, f, ensure_ascii=False, indent=2)
        elif args.command == 'status':
            result = client.request('/videos/' + args.id)
        else:
            if args.output.exists():
                raise ValueError('Output already exists; choose a new filename')
            meta = client.request('/videos/' + args.id)
            if meta.get('status') != 'completed':
                raise ValueError('Video is not completed; current status: ' + str(meta.get('status')))
            data = client.request('/videos/' + args.id + '/content', binary=True)
            if not data or (data.lstrip().startswith(b'{') or data.lstrip().startswith(b'<')):
                raise ValueError('Content endpoint did not return video bytes')
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('xb') as f:
                f.write(data)
            result = {'id': args.id, 'status': 'downloaded', 'path': str(args.output.resolve()), 'bytes': len(data)}
        print(json.dumps(clean(result, key), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, urllib.error.URLError) as exc:
        print(json.dumps({'error': str(exc).replace(key, '[hidden]') if key else str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
