import unittest
from unittest.mock import patch
from agent_contribute import core
from tests.test_external_tip_authorization import fixture
from tests.test_external_tip_prepare import ExternalGitHub


class ExternalEvidenceTests(unittest.TestCase):
    def test_full_common_evidence_errors_retained(self):
        from agent_contribute import external_tip
        t,f,c=fixture()
        with patch.object(external_tip,'live_facts',return_value=f), patch.object(core,'check_evidence',return_value=['sentinel A','sentinel B']) as check:
            r=external_tip.verify(t,{},client=ExternalGitHub(),context=c)
        self.assertEqual(r['evidence_errors'],['sentinel A','sentinel B'])
        self.assertEqual(check.call_args.kwargs['schema_version'],'0.2')
        self.assertEqual(check.call_args.kwargs['attestations'],())
        self.assertFalse(r['draft_create_ready'])

    def test_invalid_task_does_not_invent_identities(self):
        from agent_contribute import external_tip
        r=external_tip.verify({'schema_version':'0.3'})
        self.assertIsNone(r['source_identity'])
        self.assertIsNone(r['credential_actor'])
        self.assertFalse(r['implementation_ready'])
