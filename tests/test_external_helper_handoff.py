"""All authorization records in these offline tests are synthetic, never consent."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_contribute import cli, core, outputs
from tests import test_external_tip_e2e as fixtures


class ExternalHandoffTests(unittest.TestCase):
    def setUp(self):
        self.route = fixtures.ExternalTipEndToEndTests()
        self.route.setUp()
        self.addCleanup(self.route.doCleanups)
        self.route.prepare_reviewed()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.task = self.write('task.json', self.route.task)

    def write(self, name, data):
        path = self.directory / name
        path.write_text(json.dumps(data))
        return str(path)

    def call(self, argv, schema=None, stdin=None):
        out = io.StringIO()
        with open(self.write('stdin.json', stdin)) as stream, patch.object(core, 'GitHub', return_value=self.route.client), patch.object(cli.sys, 'stdin', stream), contextlib.redirect_stdout(out):
            status = cli.main(argv)
        result = json.loads(out.getvalue())
        if schema:
            self.assertEqual(core.schema_errors(result, outputs.output_schema(schema)), [], result)
        return status, result

    def test_unsigned_implementation_view_binds_both_inventories_and_cannot_authorize(self):
        status, request = self.call(['authorization-request', self.task, '--repo-dir', str(self.route.root)], 'authorization-request')
        self.assertEqual(status, 0, request)
        self.assertEqual(request['kind'], 'agent-contrib/external-authorization-request')
        self.assertIs(request['issued'], False)
        self.assertIs(request['ready_for_issuance'], False)
        self.assertEqual(request['bindings']['contract_sha256'], core.canonical_hash(self.route.task))
        self.assertEqual(request['bindings']['invitation_basis'], 'explicit-undeclared')
        self.assertIs(request['bindings']['undeclared_acknowledged_required'], True)
        self.assertEqual(len(request['policy_inventories']), 2)
        self.assertIsNone(request['bindings']['policy_assessment_sha256'])
        self.assertNotIn('implementation', request)
        self.assertNotIn('policy_review', request)
        status, result = self.call(['verify', self.task, '--stage', 'implementation', '--repo-dir', str(self.route.root), '--host-context-stdin'], 'verify', request)
        self.assertEqual(status, 1)
        self.assertFalse(result['implementation_ready'])

    def test_exact_publication_view_hashes_and_pending_authority(self):
        evidence, payload = self.route.implement_and_authorize()
        assessment = self.route.context['policy_assessment']
        ledger = self.directory / 'policy.md'
        ledger.write_bytes(self.route.ledger)
        argv = ['authorization-request', self.task, '--stage', 'draft', '--repo-dir', str(self.route.root), '--evidence', self.write('e.json', evidence), '--publication-payload', self.write('p.json', payload), '--policy-assessment', self.write('a.json', assessment), '--policy-ledger', str(ledger)]
        status, request = self.call(argv, 'authorization-request')
        self.assertEqual(status, 0, request)
        b = request['bindings']
        for field, value in [('evidence_sha256', evidence), ('review_sha256', evidence['independent_review']), ('payload_sha256', payload), ('policy_assessment_sha256', assessment)]:
            self.assertEqual(b[field], core.canonical_hash(value))
        self.assertEqual(b['policy_ledger_sha256'], hashlib.sha256(self.route.ledger).hexdigest())
        self.assertEqual(b['git_head'], evidence['git_head'])
        self.assertEqual(request['requested_actions'], ['push_head', 'create_draft'])
        self.assertTrue(request['stage_blockers']['draft'])
        self.assertIs(request['ready_for_issuance'], False)

    def test_invalid_options_and_payload_fail_before_api(self):
        for extra in (['--stage', 'draft'], ['--publication-payload', self.write('bad.json', {})], ['--stage', 'published']):
            with self.subTest(extra=extra):
                self.route.client.calls.clear()
                status, result = self.call(['authorization-request', self.task] + extra, 'error')
                self.assertNotEqual(status, 0, result)
                self.assertEqual(self.route.client.calls, [])

    def test_drift_exposes_source_and_fork_inventory_limits(self):
        status, result = self.call(['drift', self.task], 'drift')
        self.assertEqual(status, 0, result)
        self.assertFalse(result['drifted'])
        self.assertEqual(result['repository_policy_drift']['expected_sha256'], self.route.task['source_review']['inventory_sha256'])
        self.assertIsNone(result['external']['fork_policy']['changed'])
        self.assertTrue(result['external']['manual_reread_required'])
        self.route.client.contents['AGENTS.md'] += b' Changed requirement.'
        status, result = self.call(['drift', self.task], 'drift')
        self.assertTrue(result['drifted'])

    def test_body_renders_external_limits_and_preserves_exclusive_write(self):
        evidence, _ = self.route.implement_and_authorize()
        target = self.directory / 'body.md'
        argv = ['pr-body', self.task, '--evidence', self.write('e.json', evidence), '--repo-dir', str(self.route.root), '--output', str(target)]
        status, result = self.call(argv, 'pr-body')
        self.assertEqual(status, 0, result)
        body = target.read_bytes()
        self.assertEqual(result['sha256'], hashlib.sha256(body).hexdigest())
        for text in ('External tip', 'self-attested', 'host context', 'Pending', 'human/photos', 'all-state'):
            self.assertIn(text, body.decode())
        self.assertNotIn('Final human sign-off', body.decode())
        status, _ = self.call(argv, 'error')
        self.assertEqual(status, 1)
        self.assertEqual(target.read_bytes(), body)

    def test_closing_option_is_unsupported_before_reads(self):
        self.route.client.calls.clear()
        status, _ = self.call(['pr-body', self.task, '--closes', '--output', str(self.directory / 'body.md')], 'error')
        self.assertEqual(status, 2)
        self.assertEqual(self.route.client.calls, [])

    def test_jar_drift_compares_reviewed_task_bytes_not_reconstructed_baseline(self):
        self.route.client.contents['.tipjar.json'] = b'{"schema_version":"0.1","status":"welcome"}'
        status, result = self.call(['drift', self.task], 'drift')
        self.assertIs(result['tipjar']['changed'], True)
        self.assertEqual(result['tipjar']['reviewed'], {'state': 'undeclared', 'sha256': None})
        self.assertTrue(result['drifted'])

    def test_unsigned_publication_view_cannot_authorize_even_inside_a_context(self):
        e, p = self.route.implement_and_authorize()
        status, request = self.call(['authorization-request', self.task, '--stage', 'draft', '--repo-dir', str(self.route.root), '--evidence', self.write('e.json', e), '--publication-payload', self.write('p.json', p)], 'authorization-request')
        self.assertEqual(status, 0)
        context = copy.deepcopy(self.route.context)
        for candidate in (request, dict(context, publication_authorization=request), dict(context, publication_authorization=request['bindings'])):
            status, result = self.call(['verify', self.task, '--stage', 'draft', '--repo-dir', str(self.route.root), '--evidence', self.write('verify-e.json', e), '--publication-payload', self.write('verify-p.json', p), '--host-context-stdin'], 'verify', candidate)
            self.assertEqual(status, 1)
            self.assertFalse(result['draft_create_ready'])

    def test_malformed_drift_contract_is_structured_before_budget_or_api(self):
        invalid = dict(self.route.task, source_review=[])
        self.route.client.calls.clear()
        status, result = self.call(['--report-budget', 'drift', self.write('invalid.json', invalid), '--policy-sha256', 'a' * 64], 'error')
        self.assertEqual(status, 1)
        self.assertEqual(result['error']['code'], 'invalid_contract')
        self.assertEqual(self.route.client.calls, [])
