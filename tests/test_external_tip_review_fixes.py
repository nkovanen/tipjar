"""Independent regressions for the four Terra boundary findings; all authority is synthetic."""
import contextlib
import copy
import datetime as dt
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_contribute import cli, core, external_tip, outputs
from tests import test_external_tip_e2e as journeys


class ExternalReviewFixTests(unittest.TestCase):
    def setUp(self):
        self.journey = journeys.ExternalTipEndToEndTests()
        self.journey.setUp()
        self.addCleanup(self.journey.doCleanups)
        self.journey.prepare_reviewed()

    def assert_blocked_report(self, result):
        self.assertEqual(core.schema_errors(result, outputs.output_schema('verify')), [])
        for gate in ('implementation_ready', 'draft_create_ready', 'publication_verified'):
            self.assertFalse(result[gate], gate)
        self.assertTrue(result['errors'] or any(result['stage_blockers'].values()))

    def delayed_ledger(self, case):
        j = self.journey
        evidence, payload = j.implement_and_authorize()
        instant = dt.datetime.now(dt.timezone.utc)
        clock = [instant]
        class Clock(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return clock[0].astimezone(tz)
        if case == 'expiry':
            j.context['publication_authorization']['expires_at'] = (instant + dt.timedelta(seconds=2)).isoformat()
            j.refresh_observations()
            for obs in j.context['policy_observations']['entries']:
                obs['observed_at'] = instant.isoformat()
        else:
            for obs in j.context['policy_observations']['entries']:
                obs['observed_at'] = (instant - dt.timedelta(minutes=15) + dt.timedelta(seconds=1)).isoformat()
        read_ledger = external_tip.ledger_errors
        def delayed(*args):
            result = read_ledger(*args)
            # Controlled delay after actual artifact reads; no wall-clock scheduling race.
            clock[0] += dt.timedelta(seconds=3)
            return result
        with patch.object(external_tip.dt, 'datetime', Clock):
            self.assertTrue(j.verify(evidence, payload)['draft_create_ready'])
            with patch.object(external_tip, 'ledger_errors', side_effect=delayed) as read:
                result = j.verify(evidence, payload)
        self.assertEqual(read.call_count, 1)
        self.assertFalse(result['draft_create_ready'], result['stage_blockers'])
        blockers = ' '.join(result['stage_blockers']['draft'])
        self.assertIn('expired' if case == 'expiry' else '15 minutes', blockers)

    def test_publication_expiry_during_final_ledger_reads_blocks(self):
        self.delayed_ledger('expiry')

    def test_observation_freshness_during_final_ledger_reads_blocks(self):
        self.delayed_ledger('observations')

    def test_nested_fork_shapes_block_preparation_and_verification(self):
        j = self.journey
        original = copy.deepcopy(j.client.fork)
        for field in ('parent', 'permissions', 'parent.owner'):
            for value in (None, [], '', 0, False):
                for phase in ('prepare', 'verify'):
                    with self.subTest(field=field, value=value, phase=phase):
                        j.client.fork = copy.deepcopy(original)
                        if field == 'parent.owner':
                            j.client.fork['parent']['owner'] = value
                        else:
                            j.client.fork[field] = value
                        if phase == 'prepare':
                            with self.assertRaises(core.ProtocolError):
                                external_tip.prepare('acme/photos#12', 'human/photos', 'tip-12', j.client)
                        else:
                            self.assert_blocked_report(j.verify())

    def test_malformed_published_payload_values_fail_closed_in_library(self):
        j = self.journey
        evidence, payload = j.implement_and_authorize()
        j.publish(evidence, payload)
        self.assertTrue(j.verify(evidence, payload)['publication_verified'])
        for value in ([], 'payload', 7, True, None):
            with self.subTest(value=value):
                self.assert_blocked_report(j.verify(evidence, value))

    def test_malformed_published_payload_values_fail_closed_in_cli(self):
        j = self.journey
        evidence, payload = j.implement_and_authorize()
        j.publish(evidence, payload)
        self.assertTrue(j.verify(evidence, payload)['publication_verified'])
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            for name, value in (('task', j.task), ('evidence', evidence), ('context', j.context)):
                (directory / (name + '.json')).write_text(json.dumps(value))
            for value in ([], 'payload', 7, True, None):
                with self.subTest(value=value):
                    (directory / 'payload.json').write_text(json.dumps(value))
                    args = ['verify', str(directory / 'task.json'), '--stage', 'published',
                            '--repo-dir', str(j.root), '--evidence', str(directory / 'evidence.json'),
                            '--publication-payload', str(directory / 'payload.json'), '--host-context-stdin']
                    output = io.StringIO()
                    with (directory / 'context.json').open() as stdin, patch.object(cli.sys, 'stdin', stdin), \
                            patch.object(core, 'GitHub', return_value=j.client), contextlib.redirect_stdout(output):
                        code = cli.main(args)
                    self.assertEqual(code, 1)
                    self.assert_blocked_report(json.loads(output.getvalue()))

    def test_malformed_policy_context_has_schema_valid_report_and_diagnostics(self):
        j = self.journey
        original = copy.deepcopy(j.context)
        for field in ('policy_assessment', 'policy_observations'):
            for value in ([], 'context', 7, True, None, {}, {'unknown': 'property'}):
                with self.subTest(field=field, value=value):
                    j.context = copy.deepcopy(original)
                    j.context[field] = value
                    result = j.verify()
                    self.assert_blocked_report(result)
                    output_field = 'assessment' if field == 'policy_assessment' else 'observations'
                    self.assertIsNone(result['policy_reviews'][output_field])
                    self.assertTrue(any('policy_' in error for error in result['errors']))
