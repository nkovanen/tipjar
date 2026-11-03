"""A delayed artifact must never restore an older board or bypass fresh source checks."""
import copy
import importlib
import io
import json
import subprocess
import sys
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

SHA = 'a' * 40
NOW = datetime(2026, 11, 3, 18, tzinfo=timezone.utc)


def snapshot(generated='2026-11-03T17:00:00Z', expires='2026-11-05T17:00:00Z'):
    return {
        'format': 'tipjar-board/1', 'generated_at': generated, 'expires_at': expires,
        'rules_version': 1, 'source_commit': SHA,
        'coverage': dict(exhaustive=False, partial=False, unknown_tips=0,
                         unknown_repositories=0, excluded_tips=0, excluded_repositories=0,
                         omitted_tips=0, omitted_repositories=0, omitted_directory_observations=0),
        'tips': [], 'repositories': [],
        'directory': dict(complete=True, search_failed=False, server_incomplete=False,
                          truncated=False, observations=[]),
    }


class DeployTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = importlib.import_module('tools.tipjar_board_deploy')

    def check(self, candidate=None, served=None, **kwargs):
        return self.tool.check_publication(candidate or snapshot(),
                                           snapshot('2026-11-03T16:00:00Z', '2026-11-05T16:00:00Z')
                                           if served is None else served,
                                           current_source=SHA, now=NOW, **kwargs)

    def test_newer_fresh_generation_is_accepted(self):
        self.check()

    def test_equal_and_older_generations_are_rejected(self):
        for generated, expires in [('2026-11-03T17:00:00Z', '2026-11-05T17:00:00Z'),
                                   ('2026-11-03T17:30:00Z', '2026-11-05T17:30:00Z')]:
            with self.subTest(generated=generated), self.assertRaises(ValueError):
                self.check(served=snapshot(generated, expires))

    def test_wrong_source_and_expiry_crossed_during_queue_are_rejected(self):
        bad = snapshot()
        bad['source_commit'] = 'b' * 40
        with self.assertRaises(ValueError):
            self.check(candidate=bad)
        with self.assertRaises(ValueError):
            self.check(candidate=snapshot('2026-11-01T18:00:00Z', '2026-11-03T18:00:00Z'))

    def test_old_expired_served_board_can_be_replaced(self):
        self.check(served=snapshot('2026-10-30T17:00:00Z', '2026-11-01T17:00:00Z'))

    def test_first_404_requires_explicit_bootstrap(self):
        with self.assertRaises(ValueError):
            self.tool.check_publication(snapshot(), None, current_source=SHA, now=NOW)
        self.tool.check_publication(snapshot(), None, current_source=SHA, now=NOW, bootstrap=True)

    def test_bootstrap_does_not_excuse_malformed_or_future_state(self):
        for served in [b'not json', b'{"format":"tipjar-board/1","format":"tipjar-board/1"}',
                       dict(snapshot(), unexpected=True),
                       snapshot('2026-11-04T17:00:00Z', '2026-11-06T17:00:00Z')]:
            with self.subTest(served=served), self.assertRaises(ValueError):
                self.check(served=served, bootstrap=True)

    def test_artifact_reads_one_regular_root_board_without_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'artifact.tar'
            data = json.dumps(snapshot()).encode()
            with tarfile.open(path, 'w') as archive:
                info = tarfile.TarInfo('./board.json')
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            self.assertEqual(self.tool.read_artifact(path), data)
            for name, kind in [('nested/board.json', tarfile.REGTYPE),
                               ('board.json', tarfile.SYMTYPE)]:
                with tarfile.open(path, 'w') as archive:
                    info = tarfile.TarInfo(name)
                    info.type = kind
                    archive.addfile(info)
                with self.subTest(name=name), self.assertRaises(ValueError):
                    self.tool.read_artifact(path)
            with tarfile.open(path, 'w') as archive:
                for name in ['board.json', './board.json']:
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
            with self.assertRaises(ValueError):
                self.tool.read_artifact(path)

    def test_default_branch_identity_is_checked_before_using_ref(self):
        repo = dict(id=1444643470, full_name='nkovanen/tipjar', private=False,
                    visibility='public', default_branch='main')
        ref = dict(ref='refs/heads/main', object=dict(type='commit', sha=SHA))
        calls = []
        def fetch(host, path, limit):
            calls.append((host, path))
            return 200, json.dumps(repo if len(calls) == 1 else ref).encode()
        with patch.object(self.tool, 'fetch', fetch):
            self.assertEqual(self.tool.current_source(), SHA)
        self.assertEqual(calls, [('api.github.com', '/repos/nkovanen/tipjar'),
                                 ('api.github.com', '/repos/nkovanen/tipjar/git/ref/heads/main')])
        for changed in [dict(id=1), dict(private=True), dict(visibility='private'),
                        dict(full_name='elsewhere/repo'), dict(default_branch='../bad')]:
            calls.clear()
            original = copy.deepcopy(repo)
            repo.update(changed)
            with patch.object(self.tool, 'fetch', fetch), self.assertRaises(ValueError):
                self.tool.current_source()
            repo = original
            self.assertEqual(len(calls), 1)

    def test_https_read_is_bounded_unauthenticated_and_never_follows_redirects(self):
        calls = []
        class Response:
            status = 302
            def read1(self, amount):
                calls.append(('read', amount))
                return b''
        class Connection:
            sock = None
            def __init__(self, host, timeout):
                calls.append(('connect', host, timeout))
            def request(self, method, path, headers):
                calls.append(('request', method, path, headers))
            def getresponse(self):
                return Response()
            def close(self):
                calls.append(('close',))
        with patch.object(self.tool.http.client, 'HTTPSConnection', Connection):
            self.assertEqual(self.tool.fetch('nkovanen.github.io', '/tipjar/board.json', 8), (302, b''))
            self.assertEqual(calls[0], ('connect', 'nkovanen.github.io', 30))
            request = calls[1]
            self.assertEqual(request[:3], ('request', 'GET', '/tipjar/board.json'))
            self.assertNotIn('Authorization', request[3])
            self.assertIn('no-cache', request[3]['Cache-Control'])
            self.assertEqual(len([call for call in calls if call[0] == 'request']), 1)
            with patch.object(Response, 'read1', return_value=b'x' * 9), self.assertRaises(ValueError):
                self.tool.fetch('nkovanen.github.io', '/tipjar/board.json', 8)
            with patch.object(self.tool.time, 'monotonic', side_effect=[0, 31]), self.assertRaises(ValueError):
                self.tool.fetch('nkovanen.github.io', '/tipjar/board.json', 8)
            calls.clear()
            with self.assertRaises(ValueError):
                self.tool.fetch('example.com', '/arbitrary', 8)
            self.assertEqual(calls, [])

    def test_local_postbuild_cli_refuses_stale_source_without_network(self):
        generated = datetime.now(timezone.utc).replace(microsecond=0)
        from datetime import timedelta
        board = snapshot(generated.isoformat().replace('+00:00', 'Z'),
                         (generated + timedelta(hours=48)).isoformat().replace('+00:00', 'Z'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'board.json'
            path.write_text(json.dumps(board), encoding='utf-8')
            script = Path(self.tool.__file__)
            for source, expected in [(SHA, 0), ('b' * 40, 1)]:
                result = subprocess.run([sys.executable, str(script), '--board', str(path),
                                         '--source-commit', source], capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertNotIn('Traceback', result.stderr)
            path.write_bytes(b'not JSON')
            result = subprocess.run([sys.executable, str(script), '--board', str(path),
                                     '--source-commit', SHA], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn('Traceback', result.stderr)

    def test_expiry_crossed_while_validating_blocks_final_output(self):
        times = iter([NOW, datetime(2026, 11, 5, 17, tzinfo=timezone.utc)])
        class Clock:
            @staticmethod
            def now(zone):
                return next(times)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'board.json'
            path.write_text(json.dumps(snapshot()), encoding='utf-8')
            with patch.object(self.tool, 'datetime', Clock), patch('sys.stderr', io.StringIO()):
                self.assertEqual(self.tool.main(['--board', str(path), '--source-commit', SHA]), 1)

    def test_unreadable_current_state_and_redirect_fail_even_with_bootstrap(self):
        for status in [301, 403, 429, 500]:
            with self.subTest(status=status), patch.object(self.tool, 'fetch', return_value=(status, b'')):
                with self.assertRaises(ValueError):
                    self.tool.served_board()
        with patch.object(self.tool, 'fetch', return_value=(404, b'')):
            self.assertIsNone(self.tool.served_board())
        with patch.object(self.tool, 'fetch', side_effect=OSError('timeout')):
            with self.assertRaises(ValueError):
                self.tool.served_board()


if __name__ == '__main__':
    unittest.main()
