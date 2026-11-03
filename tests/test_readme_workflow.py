"""Full external-tip and CLI journeys using independently scoped README invitations."""
import base64
import copy
import contextlib
import io
import tempfile
from pathlib import Path
import json
import unittest
from unittest.mock import patch
from urllib.parse import unquote
from agent_contribute import core, external_tip, readme_invitation, tipjar
from tests import test_external_tip_e2e as route


class ReadmeRouteGitHub(route.RouteGitHub):
    def __init__(self, commit, welcome=False):
        super().__init__(commit, False)
        self.contents['README.md'] = readme_invitation.snippet('acme/photos').encode() + self.contents['README.md']
        self.fork_readme = readme_invitation.snippet('human/photos').encode() + b'# Fork\n'

    def request(self, endpoint):
        if endpoint.startswith('repos/human/photos/'):
            if '/git/trees/' in endpoint:
                value = super().request(endpoint)
                for entry in value['tree']:
                    if entry['path'] == 'README.md': entry['sha'] = tipjar.cache.blob_sha(self.fork_readme)
                return value
            if '/contents/README.md?' in endpoint:
                self.calls.append(endpoint)
                data = self.fork_readme
                return dict(type='file',path='README.md',encoding='base64',size=len(data),sha=tipjar.cache.blob_sha(data),content=base64.b64encode(data).decode())
        return super().request(endpoint)


class ReadmeWorkflowTests(unittest.TestCase):
    def make_route(self):
        r = route.ExternalTipEndToEndTests()
        r.setUp()
        self.addCleanup(r.doCleanups)
        # Keep the existing host-ledger fixture's six background references:
        # five original examples become four plus the onboarding destination.
        class Fixture(ReadmeRouteGitHub):
            refs = route.RouteGitHub.refs[:-1]
        with patch.object(route, 'RouteGitHub', Fixture):
            r.prepare_reviewed(True)
        return r

    def cli_verify(self, r, stage, evidence=None, payload=None):
        from agent_contribute import cli
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,value in (('task',r.task),('context',r.context),('evidence',evidence),('payload',payload)):
                (root/(name+'.json')).write_text(json.dumps(value))
            argv=['verify',str(root/'task.json'),'--stage',stage,'--repo-dir',str(r.root),'--host-context-stdin']
            if evidence is not None:argv += ['--evidence',str(root/'evidence.json'),'--publication-payload',str(root/'payload.json')]
            output=io.StringIO()
            with (root/'context.json').open() as stdin,patch.object(cli.sys,'stdin',stdin),patch.object(core,'GitHub',return_value=r.client),contextlib.redirect_stdout(output):
                code=cli.main(argv)
            result=json.loads(output.getvalue())
            self.assertEqual(code,0,result)
            return result

    def test_complete_implementation_draft_published_and_cli_journey(self):
        r = self.make_route()
        self.assertEqual(r.task['source_review']['jar_source_kind'], 'readme')
        self.assertEqual(r.task['source_review']['inventory_format'], 4)
        result = r.verify()
        self.assertTrue(result['implementation_ready'],result['stage_blockers'])
        self.assertTrue(self.cli_verify(r,'implementation')['implementation_ready'])
        e,p = r.implement_and_authorize()
        result = r.verify(e,p)
        self.assertTrue(result['draft_create_ready'],result['stage_blockers'])
        self.assertTrue(self.cli_verify(r,'draft',e,p)['draft_create_ready'])
        r.publish(e,p);r.refresh_observations()
        self.assertTrue(r.verify(e,p)['publication_verified'])
        self.assertTrue(self.cli_verify(r,'published',e,p)['publication_verified'])

    def test_copied_fork_blocks_until_owner_corrects_or_removes_header(self):
        r = route.ExternalTipEndToEndTests();r.setUp();self.addCleanup(r.doCleanups)
        c = ReadmeRouteGitHub(r.base)
        c.fork_readme = c.contents['README.md']
        with self.assertRaises(core.ProtocolError): external_tip.prepare('acme/photos#12','human/photos','tip-12',c)
        for text in (b'# Fork without declaration\n',readme_invitation.snippet('human/photos').encode()):
            c.fork_readme = text
            task = external_tip.prepare('acme/photos#12','human/photos','tip-12',c)
            self.assertEqual(task['source_review']['jar_state'],'welcome')

    def test_all_live_gates_block_header_drift_and_source_kind_switch(self):
        for mutation in ('edit','removed','manifest','fork-copy'):
            with self.subTest(mutation=mutation):
                r = self.make_route();e,p = r.implement_and_authorize()
                if mutation == 'edit':r.client.contents['README.md'] += b'\nUnrelated README edit\n'
                elif mutation == 'removed':r.client.contents['README.md'] = b'# No invitation\n'
                elif mutation == 'manifest':r.client.contents['.tipjar.json'] = b'{"schema_version":"0.1","status":"welcome"}'
                else:r.client.fork_readme = r.client.contents['README.md']
                result = r.verify(e,p)
                for key in ('implementation_ready','draft_create_ready','publication_verified'):
                    self.assertFalse(result[key],result)
                self.assertTrue(result['errors'])

    def test_old_unpublished_draft_requires_explicit_repreparation(self):
        r = self.make_route()
        old = copy.deepcopy(r.task)
        old['source_review']['inventory_format'] = 3
        for key in ('jar_source_kind','jar_path','jar_blob_sha','jar_manifest_present'):
            old['source_review'].pop(key)
        self.assertTrue(any('reprepare' in e for e in core.validate_contract(old)))

class LegacyPreparationCliReviewTests(unittest.TestCase):
    def setUp(self):
        self.route=route.ExternalTipEndToEndTests();self.route.setUp();self.addCleanup(self.route.doCleanups)
        self.client=ReadmeRouteGitHub(self.route.base)

    def prepare(self,version,client=None):
        from agent_contribute import cli
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'task.json';stdout=io.StringIO()
            argv=['prepare','acme/photos#12','--schema-version',version,'--output',str(output)]
            if version=='0.3':argv += ['--fork','human/photos','--head-ref','tip-12']
            with patch.object(core,'GitHub',return_value=client or self.client),contextlib.redirect_stdout(stdout):
                code=cli.main(argv)
            return code,json.loads(stdout.getvalue()),output.exists()

    def test_legacy_cli_preparation_ignores_copied_readme_intent_without_new_reads(self):
        self.client.contents['README.md']=readme_invitation.snippet('other/photos').encode()
        for version in ('0.1','0.2'):
            with self.subTest(version=version):
                self.client.calls.clear()
                code,result,written=self.prepare(version)
                self.assertEqual(code,0,result)
                self.assertTrue(written)
                self.assertEqual(result['tipjar']['state'],'undeclared')
                self.assertNotIn('source_kind',result['tipjar'])
                self.assertEqual(result['repository_policy']['inventory_format'],3)
                self.assertEqual(sum('/contents/README.md?' in x for x in self.client.calls),1)
                self.assertEqual(result['contract']['execution']['mode'],'pending')

    def test_legacy_and_current_positive_controls_and_current_copy_refusal(self):
        for version in ('0.1','0.2','0.3'):
            with self.subTest(version=version):
                code,result,written=self.prepare(version)
                self.assertEqual(code,0,result);self.assertTrue(written)
                if version=='0.3':self.assertEqual(result['contract']['source_review']['jar_source_kind'],'readme')
                else:self.assertEqual(result['tipjar']['state'],'undeclared')
        self.client.contents['README.md']=readme_invitation.snippet('other/photos').encode()
        code,result,written=self.prepare('0.3')
        self.assertEqual(code,1);self.assertFalse(written)

    def test_legacy_cli_still_blocks_closed_manifest(self):
        self.client.contents['.tipjar.json']=b'{"schema_version":"0.1","status":"closed"}'
        for version in ('0.1','0.2'):
            code,result,written=self.prepare(version)
            self.assertEqual(code,1);self.assertFalse(written)
