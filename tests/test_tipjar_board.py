"""Fictional board inputs; no network, enrollment, or execution authority."""
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import unittest

from agent_contribute import core
from tools import tipjar_board as board

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 3, 12, tzinfo=UTC)
FIXTURES = Path(__file__).parent / 'fixtures' / 'tipjar-board'


def fixture(name='valid'):
    return json.loads((FIXTURES / (name + '.json')).read_text())


def registry():
    return {'format': 'tipjar-board-registry/1', 'tips': [{
        'repository_id': 101, 'repository': 'fictional-demo/welcoming-jar',
        'pull_request_id': 201, 'number': 7, 'author_id': 301,
        'submission': {'controller_repository': 'nkovanen/tipjar',
                       'controller_repository_id': 1444643470, 'issue_id': 401,
                       'number': 11, 'body_sha256': hashlib.sha256(b'FICTIONAL DEMO consent\n').hexdigest()},
        'agent_assistance': 'self-declared', 'author_controls_repository': False}],
        'repositories': [], 'exclusions': []}


def encoded(value):
    return json.dumps(value).encode()


class ContractTests(unittest.TestCase):
    def test_registry_closed_bounded_and_unicode_strict(self):
        self.assertEqual(board.validate_registry(encoded(registry())), registry())
        for mutate in [lambda r: r.update(format='future'), lambda r: r.update(extra=1),
                       lambda r: r['tips'][0].update(author_id=True),
                       lambda r: r['tips'][0].update(author_id=9007199254740992),
                       lambda r: r['tips'][0].update(author_controls_repository=True),
                       lambda r: r['tips'][0]['submission'].update(url='https://evil.invalid')]:
            value = registry(); mutate(value)
            with self.subTest(value=value), self.assertRaises(core.ProtocolError):
                board.validate_registry(encoded(value))
        for data in [b'{"format":1,"format":2}', b'{"x":{"x":1,"x":2}}', b'\xff', b' ' * (1048576 + 1), b'{"x":"\\ud800"}']:
            with self.subTest(data=data[:50]), self.assertRaises(core.ProtocolError):
                board.validate_registry(data)

    def test_registry_deduplicates_consistent_prs_but_rejects_conflicting_pins(self):
        value = registry(); value['tips'] *= 2
        self.assertEqual(len(board.validate_registry(encoded(value))['tips']), 2)
        for key,new in [('number', 8), ('author_id', 302), ('repository_id', 102), ('repository', 'fictional-demo/renamed')]:
            value = registry(); other = copy.deepcopy(value['tips'][0]); other[key] = new; value['tips'].append(other)
            with self.subTest(key=key), self.assertRaises(core.ProtocolError):
                board.validate_registry(encoded(value))
        value = registry(); value['tips'] *= 501
        with self.assertRaises(core.ProtocolError): board.validate_registry(encoded(value))

    def test_snapshot_strict_identity_checks_expiry_and_old_served_state(self):
        for name in ('empty', 'valid', 'partial'):
            self.assertEqual(board.validate_board(encoded(fixture(name)), now=NOW), fixture(name))
        for change in [lambda b: b.update(expires_at='2026-11-05T12:00:01Z'),
                       lambda b: b['tips'][0].update(url='https://evil.invalid'),
                       lambda b: b['tips'][0].update(verified_at='2026-11-03T11:59:59Z'),
                       lambda b: b['tips'][0]['checks'].update(consent='2026-11-03T12:00:01Z'),
                       lambda b: b['directory']['observations'][0]['source'].update(path='README.md'),
                       lambda b: b['directory']['observations'][0].update(repository_id=102),
                       lambda b: b['repositories'][0].update(repository_id=9007199254740992),
                       lambda b: b['tips'][0].update(size={'additions': True, 'deletions': 0, 'changed_files': 0})]:
            value = fixture(); change(value)
            with self.subTest(value=value), self.assertRaises(core.ProtocolError): board.validate_board(value, now=NOW)
        expired = NOW + dt.timedelta(days=3)
        board.validate_board(fixture(), now=expired)
        with self.assertRaises(core.ProtocolError): board.require_fresh(fixture(), now=expired)

    def test_aggregation_dedup_ties_and_utc_periods(self):
        tip = fixture()['tips'][0]
        tips = [tip, copy.deepcopy(tip)]
        for pid,rid,author,merged in [(202,102,301,'2026-11-01T00:00:00Z'),
                                      (203,102,301,'2026-10-31T23:59:59Z'),
                                      (204,103,302,'2026-11-02T00:00:00Z'),
                                      (205,103,302,'2026-11-02T00:00:00Z')]:
            t = copy.deepcopy(tip); t.update(pull_request_id=pid,number=pid,repository_id=rid,author_id=author,merged_at=merged); tips.append(t)
        alltime = board.summarize(tips, now=NOW, period='all')
        self.assertEqual([(p['author_id'],p['points'],p['projects'],p['rank']) for p in alltime['people']], [(301,3,2,1),(302,2,1,2)])
        month = board.summarize(tips, now=NOW, period='month')
        self.assertEqual([(p['author_id'],p['points'],p['rank']) for p in month['people']], [(301,2,1),(302,2,1)])
        t = copy.deepcopy(tip); t['merged_at']='2026-10-04T12:00:00Z'
        self.assertEqual(board.summarize([t], now=NOW, period='30d')['people'][0]['points'],1)
        t['merged_at']='2026-10-04T11:59:59Z'
        self.assertEqual(board.summarize([t], now=NOW, period='30d')['people'],[])
