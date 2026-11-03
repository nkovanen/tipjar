"""Offline helper interoperability: all host decisions below are synthetic."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_contribute import cli, core, outputs
from tests import test_external_tip_e2e as route_fixture


class ExternalHelperJourneyTests(unittest.TestCase):
    def test_helper_matrix_for_welcome_and_explicit_undeclared(self):
        for welcome in (True, False):
            with self.subTest(welcome=welcome), tempfile.TemporaryDirectory() as directory:
                route = route_fixture.ExternalTipEndToEndTests()
                route.setUp()
                self.addCleanup(route.doCleanups)
                route.prepare_reviewed(welcome)
                directory = Path(directory)
                task = directory / 'task.json'
                context = directory / 'context.json'
                evidence = directory / 'evidence.json'
                payload = directory / 'payload.json'

                def call(argv, expected, schema):
                    context.write_text(json.dumps(route.context))
                    stdout = io.StringIO()
                    with context.open() as stdin, patch.object(cli.sys, 'stdin', stdin), patch.object(core, 'GitHub', return_value=route.client), contextlib.redirect_stdout(stdout):
                        code = cli.main(argv)
                    result = json.loads(stdout.getvalue())
                    self.assertEqual(code, expected, result)
                    if schema is not None:
                        self.assertEqual(core.schema_errors(result, outputs.output_schema(schema)), [], result)
                    return result

                raw = directory / 'prepared.json'
                prepared = call(['prepare', 'acme/photos#12', '--schema-version', '0.3', '--fork', 'human/photos', '--head-ref', 'tip-12', '--output', str(raw)], 0, 'prepare')
                self.assertEqual(prepared['contract']['schema_version'], '0.3')
                call(['lint', str(raw)], 1, 'lint')
                task.write_text(json.dumps(route.task))
                call(['lint', str(task)], 0, 'lint')
                for command, expected in (('drift', 1), ('authorization-request', 2), ('pr-body', 1)):
                    argv = [command, str(task)]
                    if command == 'pr-body':
                        argv += ['--output', str(directory / 'body.md')]
                    result = call(argv, expected, 'error')
                    self.assertIn('error', result)
                self.assertFalse((directory / 'body.md').exists())
                common = ['verify', str(task), '--repo-dir', str(route.root), '--host-context-stdin']
                result = call(common + ['--stage', 'implementation'], 0, 'verify')
                self.assertTrue(result['implementation_ready'])
                e, p = route.implement_and_authorize()
                result = call(['scope-check', str(task), '--repo-dir', str(route.root), '--base', route.base], 0, 'scope-check')
                self.assertTrue(result['within_scope'])
                result = call(['evidence', 'init', str(task), '--repo-dir', str(route.root), '--base', route.base, '--output', str(evidence)], 0, 'evidence-init')
                self.assertFalse(result['evidence_valid'])
                skeleton = json.loads(evidence.read_text())
                self.assertEqual(skeleton['schema_version'], '0.2')
                self.assertEqual(skeleton['independent_review']['status'], 'pending')
                payload.write_text(json.dumps(p))
                publication = common + ['--evidence', str(evidence), '--publication-payload', str(payload)]
                result = call(publication + ['--stage', 'draft'], 1, 'verify')
                self.assertFalse(result['draft_create_ready'])
                evidence.write_text(json.dumps(e))
                result = call(publication + ['--stage', 'draft'], 0, 'verify')
                self.assertTrue(result['draft_create_ready'])
                route.publish(e, p)  # Mutates fake API state only; no GitHub write.
                route.refresh_observations()
                result = call(publication + ['--stage', 'published'], 0, 'verify')
                self.assertTrue(result['publication_verified'])
                self.assertEqual(result['next_action'], 'return_draft')
                for name in ('prepare', 'lint', 'drift', 'scope-check', 'evidence-init', 'pr-body', 'authorization-request', 'verify', 'error'):
                    self.assertEqual(call(['schema', name], 0, None), outputs.output_schema(name))
