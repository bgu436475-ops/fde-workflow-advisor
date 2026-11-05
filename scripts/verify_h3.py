"""Offline H3 adapter checks; never makes a paid or network request."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.request

SOURCE = Path(__file__).resolve().parents[1] / 'skills/diagnose-fde-workflow/scripts/video_h3.py'
spec = importlib.util.spec_from_file_location('video_h3', SOURCE)
h3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h3)


class AdapterTests(unittest.TestCase):
    def invoke(self, args, responder):
        output = io.StringIO()
        config = io.StringIO(json.dumps({'base_url': 'https://h3.example/v1', 'api_key': 'test-only-key'}) + '\n')
        with patch.object(sys, 'argv', ['video_h3.py', '--config-stdin'] + args), patch.object(sys, 'stdin', config), patch.object(h3.Client, 'request', side_effect=responder) as mock, contextlib.redirect_stdout(output):
            code = h3.main()
        return code, output.getvalue(), mock

    def test_create_receipt_and_no_resubmit(self):
        with tempfile.TemporaryDirectory() as d:
            prompt, receipt = Path(d) / 'prompt.txt', Path(d) / 'receipt.json'
            prompt.write_text('same order, clear exception handoff', encoding='utf-8')
            args = ['create', '--prompt-file', str(prompt), '--output', str(receipt)]
            code, output, mock = self.invoke(args, lambda *a, **k: {'id': 'video_test', 'status': 'queued'})
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(receipt.read_text())['id'], 'video_test')
            self.assertEqual(mock.call_args.args[1]['seconds'], '4')
            self.assertEqual(mock.call_args.args[1]['model'], 'h3-text')
            code, output, mock = self.invoke(args, lambda *a, **k: self.fail('duplicate submission'))
            self.assertEqual(code, 2)
            mock.assert_not_called()

    def test_pending_download_does_not_fetch_content(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'video.mp4'
            code, output, mock = self.invoke(['download', 'video_test', '--output', str(target)], lambda *a, **k: {'status': 'queued'})
            self.assertEqual(code, 2)
            self.assertFalse(target.exists())
            self.assertEqual(mock.call_count, 1)

    def test_completed_download(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'video.mp4'
            def responder(path, **kwargs):
                return b'\x00\x00\x00\x18ftypmp42' if kwargs.get('binary') else {'status': 'completed'}
            code, output, mock = self.invoke(['download', 'video_test', '--output', str(target)], responder)
            self.assertEqual(code, 0)
            self.assertEqual(target.read_bytes(), b'\x00\x00\x00\x18ftypmp42')

    def test_output_redaction(self):
        code, output, _ = self.invoke(['status', 'video_test'], lambda *a: {'status': 'failed', 'api_key': 'test-only-key', 'message': 'test-only-key is invalid'})
        self.assertEqual(code, 0)
        self.assertNotIn('test-only-key', output)

    def test_configuration_validation(self):
        for base in ['http://h3.example', 'https://user:pass@h3.example', 'https://h3.example/?token=x']:
            with self.assertRaises(ValueError):
                h3.Client(base, 'test-only-key')

    def test_cross_origin_redirect_removes_authorization(self):
        request = urllib.request.Request('https://h3.example/video', headers={'Authorization': 'Bearer test-only-key'})
        redirected = h3.SafeRedirect().redirect_request(request, None, 302, 'Found', {}, 'https://cdn.example/video.mp4')
        self.assertIsNone(redirected.get_header('Authorization'))

    def test_same_origin_redirect_keeps_authorization(self):
        request = urllib.request.Request('https://h3.example/video', headers={'Authorization': 'Bearer test-only-key'})
        redirected = h3.SafeRedirect().redirect_request(request, None, 302, 'Found', {}, 'https://h3.example/video2')
        self.assertEqual(redirected.get_header('Authorization'), 'Bearer test-only-key')


if __name__ == '__main__':
    unittest.main()
