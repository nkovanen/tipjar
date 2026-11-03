"""Exact source grammar, scoped identity and pinned invitation provenance."""
import base64
import hashlib
import unittest
from agent_contribute import cache, tipjar
from tests.test_tipjar import Fake, responses, COMMIT, TREE

IMAGE = 'https://nkovanen.github.io/tipjar/brand/agent-work-welcome.svg'
PREFIX = '<!-- tipjar:welcome:v1 -->\n[![Agent-work tips welcome](' + IMAGE + ')](https://nkovanen.github.io/tipjar/?repo=acme%2Fproject)\n\n'

class ReadmeTests(unittest.TestCase):
    def parse(self, text):
        from agent_contribute.readme_invitation import parse_readme_invitation
        return parse_readme_invitation(text.encode(), 'acme/project')['state']

    def test_exact_prefix_and_original_bytes(self):
        for suffix in ('', '# Project\n', 'This is an example.\nNo agent contributions.\n'):
            for ending in ('\n', '\r\n'):
                self.assertEqual(self.parse((PREFIX + suffix).replace('\n', ending)), 'welcome')
        for text in ('# Plain', '\ufeff# Plain\r\nMixed\n', PREFIX.split('\n')[1], 'tipjar:welcom:v1'):
            self.assertEqual(self.parse(text), 'undeclared')

    def test_reserved_intent_never_fuzzy_or_inherited(self):
        cases = ['\ufeff' + PREFIX, ' ' + PREFIX, '\n' + PREFIX, '> ' + PREFIX,
                 '```\n' + PREFIX + '```', '<div>' + PREFIX, PREFIX[:-1],
                 PREFIX.replace(':v1', ':v2'), PREFIX + 'tipjar:welcome',
                 PREFIX.replace('acme%2Fproject', 'parent%2Fproject'),
                 PREFIX.replace('%2F', '%2f'), PREFIX.replace('https://nkovanen.', 'https://evil.'),
                 PREFIX.replace('\n', '\r\n', 1), PREFIX.replace('\n', '\r')]
        for text in cases:
            with self.subTest(text=text): self.assertEqual(self.parse(text), 'unknown')

    def client(self, raw=PREFIX.encode(), manifest=False):
        data = responses(entries=[])
        data['repos/acme/project']['id'] = 42
        path = '.tipjar.json' if manifest else 'README.md'
        if manifest: raw = b'{"schema_version":"0.1","status":"closed"}'
        blob = cache.blob_sha(raw)
        data[f'repos/acme/project/git/trees/{TREE}?recursive=1']['tree'] = [dict(path=path,type='blob',mode='100644',sha=blob,size=len(raw))]
        data[f'repos/acme/project/contents/{path}?ref={COMMIT}'] = dict(type='file',encoding='base64',path=path,sha=blob,size=len(raw),content=base64.b64encode(raw).decode())
        return Fake(data)

    def test_pinned_source_and_manifest_precedence(self):
        for raw, state in ((PREFIX.encode(), 'welcome'), (b'# Plain', 'undeclared')):
            client = self.client(raw)
            result = tipjar.read_jar('acme/project', client)
            self.assertEqual(result['state'], state)
            self.assertEqual(result['path'], 'README.md')
            self.assertEqual(result['source_kind'], 'readme')
            self.assertEqual(result['repository_id'], 42)
            self.assertEqual(result['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertTrue(tipjar._complete_report(result))
            self.assertEqual(len(client.calls), 4)
        result = tipjar.read_jar('acme/project', self.client(manifest=True))
        self.assertEqual((result['state'], result['source_kind']), ('closed', 'manifest'))

    def test_identity_and_content_fail_closed_without_false_digest(self):
        for field, value in (('sha', 'f'*40), ('size', 0), ('path', 'other'), ('content', '!')):
            client = self.client()
            client.data[f'repos/acme/project/contents/README.md?ref={COMMIT}'][field] = value
            result = tipjar.read_jar('acme/project', client)
            self.assertEqual((result['state'], result['complete'], result['sha256']), ('unknown', False, None))
        for value in (None, True, 0):
            client = self.client(); client.data['repos/acme/project']['id'] = value
            result = tipjar.read_jar('acme/project', client)
            self.assertEqual(result['state'], 'unknown')
            self.assertIsNone(result['commit'])

class VersionAndPolicyTests(unittest.TestCase):
    def test_only_exact_image_occurrence_is_exempt_before_dedup(self):
        from agent_contribute import policy
        for ending in ('\n', '\r\n'):
            text = (PREFIX + '\nNo agent contributions.\n' + IMAGE).replace('\n', ending)
            links = policy.scan(text, 'README.md', invitation_repository='acme/project')['links']
            self.assertEqual(sum(x['url'] == IMAGE for x in links), 1)
            self.assertTrue(any('?repo=' in x['url'] for x in links))
            clean = policy.scan(PREFIX, 'README.md', invitation_repository='acme/project')['links']
            self.assertFalse(any(x['url'] == IMAGE for x in clean))
            legacy = policy.scan(PREFIX, 'README.md')['links']
            self.assertTrue(any(x['url'] == IMAGE for x in legacy))

    def test_legacy_read_does_not_read_readme(self):
        client = ReadmeTests().client()
        result = tipjar.read_jar('acme/project', client, invitation_protocol=tipjar.LEGACY)
        self.assertEqual(result['state'], 'undeclared')
        self.assertNotIn('source_kind', result)
        self.assertEqual(len(client.calls), 3)

class BadgeTests(unittest.TestCase):
    def test_offline_badge_exact_and_canonical(self):
        from agent_contribute import onboarding
        report = onboarding.badge('Acme/Project')
        self.assertEqual(report['snippet'], PREFIX)
        self.assertEqual(report['repository'], 'acme/project')
        self.assertIn('README.md', report['notice'])

class OriginalSpanTests(unittest.TestCase):
    def test_sanitized_instruction_cannot_recognize_an_invalid_original_prefix(self):
        from agent_contribute import core, policy
        from tests.test_policy import PolicyGitHub
        for raw in ('\ufeff'+PREFIX, PREFIX.replace('\n','\r\n',1)):
            raw = raw.replace('acme%2Fproject','acme%2Fphotos')
            client = PolicyGitHub({'README.md':raw})
            instructions = [dict(path='README.md',sha256=hashlib.sha256(raw.encode()).hexdigest(),untrusted_text=core.safe_text(raw))]
            result = policy.report('acme/photos',COMMIT,instructions,client)
            self.assertTrue(any(x['what'] == IMAGE for x in result['unassessed']))

class IndependentForkTests(unittest.TestCase):
    def test_fresh_fork_inventory_must_match_its_own_snapshot_identity_and_pin(self):
        import copy
        from unittest.mock import patch
        from agent_contribute import core, external_tip, policy
        from tests.test_external_tip_prepare import ExternalGitHub
        original = policy.report
        def forged(*args, **kwargs):
            inv = original(*args, **kwargs)
            if args[0] == 'human/photos':
                inv = copy.deepcopy(inv)
                inv['tipjar']['repository_id'] = 999
            return inv
        with patch.object(policy,'report',side_effect=forged), self.assertRaises(core.ProtocolError):
            external_tip.prepare('acme/photos#12','human/photos','tip-12',ExternalGitHub())

class TwoSearchTests(unittest.TestCase):
    def client(self, first, second, data=None):
        from tests.test_find import Fake
        class Client(Fake):
            def request_once(self, endpoint):
                if 'filename%3AREADME.md' in endpoint:
                    import copy
                    self.calls.append(endpoint)
                    if isinstance(second, Exception): raise second
                    return copy.deepcopy(second)
                return super().request_once(endpoint)
        return Client(first, data)

    def readme_hit(self, **kwargs):
        from tests.test_find import hit
        value = hit(**kwargs);value.update(path='README.md',name='README.md',sha='d'*40)
        return value

    def test_cross_search_paths_share_one_independent_inspection(self):
        from agent_contribute.find import find_jars
        from tests.test_find import hit,page
        client = self.client(page([hit()]),page([self.readme_hit()]),ReadmeTests().client().data)
        result = find_jars(client)
        self.assertTrue(result['complete'])
        self.assertEqual(len(result['observations']),1)
        self.assertEqual(result['observations'][0]['jar']['source_kind'],'readme')
        self.assertEqual(result['requests'],dict(search=2,core=5))
        self.assertEqual(len(client.calls),7)

    def test_failed_search_retains_other_verified_welcome(self):
        from agent_contribute import core
        from agent_contribute.find import find_jars
        from tests.test_find import page
        client = self.client(core.ProtocolError('api_error','untrusted diagnostic'),page([self.readme_hit()]),ReadmeTests().client().data)
        result = find_jars(client)
        self.assertFalse(result['complete'])
        self.assertEqual(result['observations'][0]['disposition'],'welcome')
        self.assertEqual(result['searches'][0]['errors'],['search_failed'])
        self.assertEqual(result['searches'][1]['errors'],[])
        self.assertEqual(result['requests']['search'],2)

    def test_cross_search_private_and_identity_conflicts_never_inspect(self):
        from agent_contribute.find import find_jars
        from tests.test_find import hit,page
        import json
        for private in (False,True):
            other = self.readme_hit(repo_id=1 if private else 2)
            if private:other['repository']['private']=True
            client = self.client(page([hit()]),page([other]))
            result = find_jars(client)
            self.assertFalse(result['complete'])
            self.assertEqual(result['requests'],dict(search=2,core=0))
            self.assertNotIn('acme/project',json.dumps(result))

class OutputVersionTests(unittest.TestCase):
    def test_unknown_output_version_fails_closed(self):
        from agent_contribute import core,outputs
        with self.assertRaises(core.ProtocolError):outputs.output_schema('jar',version='5')

class HistoricalArtifactsTests(unittest.TestCase):
    def test_every_published_schema_and_output_one_through_three_is_unchanged(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        frozen = json.loads((root/'tests/fixtures/readme-historical-schemas.json').read_text())
        for name,expected in frozen.items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),expected,name)

    def test_published_legacy_task_needs_no_new_numeric_invitation_identity(self):
        from agent_contribute import core
        from tests.test_protocol import FakeGitHub,ready_contract
        class Legacy(FakeGitHub):
            def request(self, endpoint):
                value = super().request(endpoint)
                if endpoint == 'repos/acme/photos':value.pop('id',None)
                return value
        task,_ = ready_contract()
        result = core.verify(task,client=Legacy({'schema_version':'0.1','agent_approved_labels':['agent-ok'],'label_authority':'repository-label-permission'},['agent-ok']))
        self.assertTrue(result['execution_ready'],result['errors'])

class HistoricalInventoryTests(unittest.TestCase):
    def test_format_four_never_relabels_its_changed_scan_as_historical_hashes(self):
        from agent_contribute import policy
        from tests.test_policy import PolicyGitHub
        text = PREFIX.replace('acme%2Fproject','acme%2Fphotos')
        files = {'README.md':text}
        historical, current = {}, {}
        policy.report('acme/photos',COMMIT,[],PolicyGitHub(files),inventory_format=3,hashes=historical)
        policy.report('acme/photos',COMMIT,[],PolicyGitHub(files),inventory_format=4,hashes=current)
        for version,digest in historical.items():self.assertEqual(current.get(version),digest)

class TimestampCompatibilityTests(unittest.TestCase):
    def test_utc_z_reports_validate_on_python_310(self):
        import datetime as dt
        from unittest.mock import patch
        real = dt.datetime
        class Python310(real):
            @classmethod
            def fromisoformat(cls,value):
                if value.endswith('Z'):raise ValueError('Python 3.10 has no terminal Z support')
                return real.fromisoformat(value)
        for protocol in (tipjar.LEGACY,tipjar.CURRENT):
            report = tipjar.read_jar('acme/project',Fake(),invitation_protocol=protocol)
            report['fetched_at'] = '2026-11-03T12:00:00Z'
            with patch.object(tipjar.dt,'datetime',Python310):
                self.assertTrue(tipjar._complete_report(report))
            report['fetched_at'] = '2026-11-03T12:00:00+00:00'
            with patch.object(tipjar.dt,'datetime',Python310):
                self.assertTrue(tipjar._complete_report(report))

class BoundedManifestReportTests(unittest.TestCase):
    def test_valid_near_bound_manifest_is_not_rejected_by_reserialization_spacing(self):
        import json
        manifest=dict(schema_version='0.1',status='welcome',wanted=[str(n)+'x'*499 for n in range(16)],boundaries=[str(n)+'y'*499 for n in range(16)])
        # Use single-character ids so each string is within the 500-character bound.
        manifest['wanted']=[chr(65+n)+'x'*499 for n in range(16)]
        manifest['boundaries']=[chr(65+n)+'y'*499 for n in range(16)]
        encode=lambda:json.dumps(manifest,ensure_ascii=False,separators=(',',':')).encode()
        extra=tipjar.MAX_BYTES-len(encode())-1
        manifest['boundaries'][0]='A'+'é'*extra+'y'*(499-extra)
        data=encode()
        self.assertEqual(len(data),tipjar.MAX_BYTES-1)
        result=tipjar.read_jar('acme/project',Fake(responses(data)))
        self.assertEqual(result['state'],'welcome')
        self.assertTrue(tipjar._complete_report(result))

class TreeSizeReviewTests(unittest.TestCase):
    def test_selected_tree_size_must_equal_verified_bytes_for_both_new_sources(self):
        for manifest in (False,True):
            with self.subTest(manifest=manifest):
                client=ReadmeTests().client(manifest=manifest)
                entry=client.data[f'repos/acme/project/git/trees/{TREE}?recursive=1']['tree'][0]
                entry['size']=0
                result=tipjar.read_jar('acme/project',client)
                self.assertEqual((result['state'],result['complete']),('unknown',False))
                self.assertIsNone(result['sha256'])
                self.assertEqual(result['blob_sha'],entry['sha'])

    def test_published_legacy_size_handling_is_unchanged(self):
        client=ReadmeTests().client(manifest=True)
        client.data[f'repos/acme/project/git/trees/{TREE}?recursive=1']['tree'][0]['size']=0
        result=tipjar.read_jar('acme/project',client,invitation_protocol=tipjar.LEGACY)
        self.assertEqual((result['state'],result['complete']),('closed',True))
