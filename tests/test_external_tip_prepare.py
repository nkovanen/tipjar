import base64
import copy
import unittest
from agent_contribute import core, cache
from tests.test_authorization import CandidateGitHub


class ExternalGitHub(CandidateGitHub):
    def __init__(self):
        super().__init__()
        self.metadata.update(private=False, archived=False, disabled=False)
        self.fork = dict(full_name='human/photos', id=202, default_branch='main', fork=True,
                         has_issues=False, private=False, archived=False, disabled=False,
                         owner=dict(id=7, login='human', type='User'), permissions={'push':True},
                         parent=copy.deepcopy(self.metadata))

    def request(self, endpoint):
        if endpoint in self.failed:
            raise core.ProtocolError('api_error', 'Fixture unavailable GET')
        if endpoint == 'repos/human/photos':
            self.calls.append(endpoint)
            return copy.deepcopy(self.fork)
        if '/git/ref/heads/' in endpoint:
            self.calls.append(endpoint)
            exc=core.ProtocolError('api_error','GET 404');exc.http_status=404;raise exc
        if endpoint.endswith('/timeline') or endpoint.endswith('/comments') or '/timeline?' in endpoint or '/comments?' in endpoint:
            self.calls.append(endpoint)
            return []
        original_endpoint=endpoint
        if endpoint.startswith('repos/human/photos/'):
            endpoint=endpoint.replace('repos/human/photos/','repos/acme/photos/',1)
        value=super().request(endpoint)
        if '/git/trees/' in endpoint:
            for entry in value.get('tree',[]):
                if entry['path'] == 'README.md': entry['sha']=cache.blob_sha(b'Ordinary project guidance.')
        if original_endpoint != endpoint:
            self.calls[-1]=original_endpoint
        if '/contents/' in endpoint and '.agent-contrib.json' not in endpoint:
            data=b'Ordinary project guidance.'
            value.update(content=base64.b64encode(data).decode(),size=len(data))
            if value.get('path') == 'README.md': value['sha'] = cache.blob_sha(data)
        if endpoint=='repos/acme/photos/issues/12':value['assignees']=[]
        return value


class ExternalPrepareTests(unittest.TestCase):
    def test_prepare_pending_welcome_and_undeclared(self):
        from agent_contribute import external_tip
        client=ExternalGitHub()
        task=external_tip.prepare('acme/photos#12','human/photos','tip-12',client)
        self.assertEqual(core.validate_contract(task),[])
        self.assertEqual(task['status'],'draft')
        self.assertEqual(task['source_review']['invitation_basis'],'explicit-undeclared')
        self.assertEqual(task['execution']['head_repository_id'],202)
        self.assertNotIn('implementation',task)
        self.assertFalse(core.lint(task)['reviewed'])

    def test_unsafe_fork_parent_and_boolean_ids_block(self):
        from agent_contribute import external_tip
        for value in (True,999):
            client=ExternalGitHub();client.fork['parent']['id']=value
            with self.assertRaises(core.ProtocolError):
                external_tip.prepare('acme/photos#12','human/photos','tip-12',client)

    def test_preparation_requires_complete_ownership_and_empty_histories(self):
        from agent_contribute import external_tip
        client=ExternalGitHub();client.failed.add('repos/acme/photos/issues/12/timeline?per_page=100&page=1')
        with self.assertRaises(core.ProtocolError):external_tip.prepare('acme/photos#12','human/photos','tip-12',client)
