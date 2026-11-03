"""The reviewed external route must preserve the complete product-wave schema registry."""
import contextlib
import copy
import io
import importlib.resources
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_contribute import cli, core, outputs
from tests import test_external_tip_e2e as journeys


class ExternalWaveRegistryTests(unittest.TestCase):
    def test_active_three_covers_every_frozen_two_command(self):
        root = importlib.resources.files('agent_contribute').joinpath('schemas/output')
        frozen_names = {p.name.removesuffix('.schema.json') for p in root.joinpath('2').iterdir()}
        self.assertEqual(outputs.VERSION, '3')
        self.assertTrue({'dependencies', 'find', 'impact', 'init', 'jar-check', 'receipt', 'session'} <= frozen_names)
        self.assertEqual(set(outputs.SCHEMAS), frozen_names)
        self.assertEqual({p.name.removesuffix('.schema.json') for p in root.joinpath('3').iterdir()}, frozen_names)
        for name in frozen_names:
            with self.subTest(name=name):
                self.assertEqual(outputs.output_schema(name)['$id'], f'urn:agent-contrib:output:3:{name}')

    def test_cloned_wave_shapes_change_only_the_schema_id(self):
        root = importlib.resources.files('agent_contribute').joinpath('schemas/output/2')
        for name in ('dependencies', 'find', 'impact', 'init', 'jar-check', 'receipt', 'session'):
            with self.subTest(name=name):
                expected = json.loads(root.joinpath(name + '.schema.json').read_text('utf-8'))
                expected['$id'] = f'urn:agent-contrib:output:3:{name}'
                self.assertEqual(outputs.output_schema(name), expected)

    def test_external_unions_retain_reviewed_variants(self):
        verify = outputs.output_schema('verify')
        self.assertIn({'$ref': '#/$defs/external_tip_report'}, verify['anyOf'])
        request = outputs.output_schema('authorization-request')
        self.assertGreater(len(request['anyOf']), 1)
        drift = outputs.output_schema('drift')
        self.assertIn('external', drift['properties'])
        self.assertIn('reviewed', drift['properties']['tipjar']['properties'])
        self.assertIn('manual_reread_required', drift['properties']['external']['required'])


class ExternalWaveCliJourneyTests(unittest.TestCase):
    def test_both_invitation_paths_use_helpers_without_promoting_unsigned_views(self):
        for welcome in (False, True):
            with self.subTest(welcome=welcome):
                route = journeys.ExternalTipEndToEndTests()
                route.setUp()
                try:
                    route.prepare_reviewed(welcome)
                    with tempfile.TemporaryDirectory() as directory:
                        directory = Path(directory)
                        def write(name, value):
                            path = directory / name
                            path.write_text(json.dumps(value))
                            return str(path)
                        task = write('task.json', route.task)
                        def call(args, context=None):
                            output = io.StringIO()
                            context_file = write('context.json', context)
                            with open(context_file) as stdin, patch.object(cli.sys, 'stdin', stdin), \
                                    patch.object(core, 'GitHub', return_value=route.client), contextlib.redirect_stdout(output):
                                code = cli.main(args)
                            return code, json.loads(output.getvalue())
                        implementation = ['verify', task, '--stage', 'implementation', '--repo-dir', str(route.root), '--host-context-stdin']
                        code, view = call(['authorization-request', task, '--repo-dir', str(route.root)])
                        self.assertEqual(code, 0, view)
                        self.assertFalse(view['issued'])
                        self.assertFalse(view['ready_for_issuance'])
                        code, blocked = call(implementation, view)
                        self.assertEqual(code, 1, blocked)
                        self.assertFalse(blocked['implementation_ready'])
                        code, permitted = call(implementation, route.context)
                        self.assertEqual(code, 0, permitted)
                        evidence, payload = route.implement_and_authorize()
                        evidence_file = write('evidence.json', evidence)
                        body_file = directory / 'body.md'
                        code, rendered = call(['pr-body', task, '--repo-dir', str(route.root), '--evidence', evidence_file, '--output', str(body_file)])
                        self.assertEqual(code, 0, rendered)
                        payload['body'] = body_file.read_text()
                        # A synthetic host decision covers the exact helper-rendered body.
                        route.context['publication_authorization']['payload_sha256'] = core.canonical_hash(payload)
                        route.refresh_observations()
                        payload_file = write('payload.json', payload)
                        code, publication_view = call(['authorization-request', task, '--stage', 'draft', '--repo-dir', str(route.root), '--evidence', evidence_file, '--publication-payload', payload_file])
                        self.assertEqual(code, 0, publication_view)
                        self.assertFalse(publication_view['issued'])
                        args = ['verify', task, '--stage', 'draft', '--repo-dir', str(route.root), '--evidence', evidence_file, '--publication-payload', payload_file, '--host-context-stdin']
                        unsigned_context = copy.deepcopy(route.context)
                        unsigned_context['publication_authorization'] = publication_view
                        code, blocked = call(args, unsigned_context)
                        self.assertEqual(code, 1, blocked)
                        self.assertFalse(blocked['draft_create_ready'])
                        code, permitted = call(args, route.context)
                        self.assertEqual(code, 0, permitted)
                        self.assertTrue(permitted['draft_create_ready'])
                        route.publish(evidence, payload)
                        args[args.index('draft')] = 'published'
                        code, observed = call(args, route.context)
                        self.assertEqual(code, 0, observed)
                        self.assertTrue(observed['publication_verified'])
                        self.assertEqual(observed['next_action'], 'return_draft')
                finally:
                    route.doCleanups()
