import unittest
from agent_contribute import core


class ExternalSchemaTests(unittest.TestCase):
    def test_exact_supported_versions(self):
        self.assertEqual(core.SUPPORTED_SCHEMA_VERSIONS, ('0.1', '0.2', '0.3'))
        self.assertEqual(core.bundled_schema('task', '0.3')['properties']['schema_version'], {'const': '0.3'})
        with self.assertRaises(core.ProtocolError):
            core.bundled_schema('evidence', '0.3')

    def test_03_evidence_is_02(self):
        self.assertEqual(core.evidence_version('0.3'), '0.2')
        with self.assertRaises(core.ProtocolError):
            core.evidence_version('0.4')

    def test_context_authorizations_both_bind_fork_inventory(self):
        schema = core.bundled_schema('external-context', '0.1')
        for name in ('implementation', 'publication_authorization'):
            self.assertIn('fork_policy_inventory_sha256', schema['properties'][name]['required'])
            self.assertFalse(schema['properties'][name]['additionalProperties'])
