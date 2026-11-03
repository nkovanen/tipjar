"""Offline full route fixtures; assertions here represent synthetic host decisions only."""
import base64
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from urllib.parse import unquote

from agent_contribute import core, external_tip, workspace, tipjar
from tests.test_external_tip_prepare import ExternalGitHub
from tests.test_external_tip_authorization import fixture
from tests.test_protocol import ready_contract


def stamp():return dt.datetime.now(dt.timezone.utc).isoformat()
def digest(data):return hashlib.sha256(data).hexdigest()


class RouteGitHub(ExternalGitHub):
    refs=['docs/architecture-notes.md','docs/releasing.md','docs/cli.md',
          'docs/host-authorization.md','docs/lightcraft-case-study.md']

    def __init__(self, commit, welcome=False):
        super().__init__();self.commit=commit;self.welcome=welcome;self.published=None;self.remote=None
        self.contents={p:b'Ordinary project guidance.' for p in ['README.md','AGENTS.md','CONTRIBUTING.md']}
        self.contents['README.md']=('\n'.join(f'Background example [contribution workflow for {p}]({p})' for p in self.refs)).encode()
        self.contents.update({p:b'Example documentation.' for p in self.refs})
        if welcome:self.contents['.tipjar.json']=b'{"schema_version":"0.1","status":"welcome"}'
        self.foreign_history=[];self.other_prs=[];self.wrong_cross_id=False

    def request_once(self, endpoint):return self.request(endpoint)

    def request(self, endpoint):
        self.calls.append(endpoint)
        path=endpoint.split('?')[0]
        if any(x in endpoint for x in self.failed):raise core.ProtocolError('api_error','Fixture read failed')
        source=path.startswith('repos/acme/photos/')
        if '/git/trees/' in path:
            return dict(sha='c'*40,truncated=False,tree=[dict(path=p,type='blob',mode='100644',sha=tipjar.cache.blob_sha(data)) for p,data in self.contents.items()])
        if '/contents/' in path:
            name=unquote(path.split('/contents/')[1]);data=self.contents[name]
            return dict(type='file',path=name,encoding='base64',size=len(data),sha=tipjar.cache.blob_sha(data),content=base64.b64encode(data).decode())
        if '/git/ref/heads/' in path:
            if self.remote:return dict(ref='refs/heads/tip-12',object=dict(type='commit',sha=self.remote[0]))
            exc=core.ProtocolError('api_error','GET 404');exc.http_status=404;raise exc
        if '/git/commits/' in path and self.remote:return dict(sha=self.remote[0],tree=dict(sha=self.remote[1]))
        if path.endswith('/pulls'):
            if 'state=all' in endpoint:
                if not source:return copy.deepcopy(self.foreign_history)
                return [copy.deepcopy(self.published)] if self.published else []
            return ([copy.deepcopy(self.published)] if source and self.published else [])+copy.deepcopy(self.other_prs)
        if path.endswith('/pulls/30'):
            result=copy.deepcopy(self.published)
            if self.wrong_cross_id and '/timeline' not in endpoint:result['id']=9999
            return result
        if path.endswith('/timeline'):
            return [dict(id=901,event='cross-referenced',source=dict(issue=dict(number=30,pull_request={},repository=dict(full_name='acme/photos',id=101))))] if self.published else []
        if path.endswith('/comments'):return []
        return super().request(endpoint)


class ExternalTipEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.git('init','-q');(self.root/'base.txt').write_text('Source base')
        self.git('add','.');self.git('commit','-q','-m','source')
        self.base=self.git('rev-parse','HEAD');self.git('checkout','-q','-b','tip-12')
        self.git('remote','add','origin','https://github.com/human/photos.git')

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.root),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',*args],text=True).strip()

    def prepare_reviewed(self,welcome=False):
        self.client=RouteGitHub(self.base,welcome)
        self.task=external_tip.prepare('acme/photos#12','human/photos','tip-12',self.client)
        spec,_=ready_contract()
        for key in ('status','objective','behavior_criteria','code_locations','constraints','prohibited_changes','validation','prerequisites','done','questions'):
            self.task[key]=copy.deepcopy(spec[key])
        self.task['scope']=dict(allowed_paths=['src/**','compliance/**'],prohibited_paths=['.github/**'])
        facts=external_tip.live_facts(self.task,str(self.root),self.client)
        self.assertEqual(facts['errors'],[])
        # Five concrete background references plus the exact owner .github 404 remain raw.
        self.assertEqual(len(facts['inventories'][0]['inventory']['unassessed']),6)
        _,_,self.context=fixture(self.task,facts)
        if welcome:
            self.context['implementation'].update(invitation_basis='welcome',undeclared_acknowledged=False)
        for row in self.context['policy_assessment']['entries']:
            inv=next(b['inventory'] for b in facts['inventories'] if b['repository_id']==row['repository_id'])
            item=next(x for x in inv['sources_scanned']+inv['unassessed'] if x['identity_sha256']==row['identity_sha256'])
            if 'path' not in item and item.get('from') is None:continue
            source=item if 'path' in item else next(x for x in inv['sources_scanned'] if f"{x['repository']}:{x['path']}"==item['from'])
            row['evidence']=[dict(role='referring-context',uri=f"https://github.com/{source['repository']}/blob/{source['commit']}/{source['path']}",revision=source['commit'],content_sha256=source['sha256'],quote='Background example' if source['path']=='README.md' else 'Ordinary project guidance.',observed_at=stamp())]
            row['disposition']='inapplicable'
            # Applicable contribution/release sources are actually read by the fake host, never the CLI.
            target_path = item.get('what') if item.get('what') in ('docs/releasing.md','docs/host-authorization.md') else source['path'] if source['path'] in ('AGENTS.md','CONTRIBUTING.md') else None
            if target_path:
                target_bytes = self.client.contents[target_path]
                row['disposition']='assessed-applicable'
                row['reason']='Host read applicable contribution workflow; constraints retained in policy ledger'
                row['evidence'].append(dict(role='applicable-target',uri=f"https://github.com/{source['repository']}/blob/{source['commit']}/{target_path}",revision=source['commit'],content_sha256=digest(target_bytes),quote=target_bytes.decode(),observed_at=stamp()))
        assessment=core.canonical_hash(self.context['policy_assessment'])
        self.ledger=('Reviewed policy assessment '+assessment+'\nFixture permitted constraints and workflow.').encode()
        self.context['implementation'].update(policy_ledger_sha256=digest(self.ledger),policy_assessment_sha256=assessment)
        self.context['implementation']['policy_review']['ledger_sha256']=digest(self.ledger)
        self.refresh_observations()

    def refresh_observations(self):
        c=self.context;i=c['implementation'];p=c.get('publication_authorization')
        targets={(e['uri'],e['revision']):e for row in c['policy_assessment']['entries'] for e in row['evidence'] if e['role']=='applicable-target'}
        c['policy_observations']['entries']=[{k:e[k] for k in ('uri','revision','content_sha256')}|dict(status='read',observed_at=stamp()) for e in targets.values()]
        c['policy_observations'].update(policy_assessment_sha256=core.canonical_hash(c['policy_assessment']),implementation_sha256=core.canonical_hash(i),publication_authorization_sha256=core.canonical_hash(p) if p else None)

    def verify(self,evidence=None,payload=None):
        return core.verify(self.task,evidence,str(self.root),self.client,host_context=self.context,payload=payload)

    def implement_and_authorize(self):
        (self.root/'src').mkdir();(self.root/'src/thumb.rs').write_text('Reviewed fixture implementation')
        (self.root/'compliance').mkdir();(self.root/'compliance/policy.md').write_bytes(self.ledger)
        (self.root/'compliance/.gitignore').write_text('final.txt\n')
        self.git('add','.');self.git('commit','-q','-m','scoped fixture change')
        evidence=workspace.evidence_skeleton(self.task,str(self.root),self.base)
        self.assertEqual(evidence['schema_version'],'0.2');self.assertEqual(evidence['independent_review']['status'],'pending')
        head=evidence['git_head']
        # Final host review artifact is ignored, so it can bind the already committed head without a hash cycle.
        final=('Final compliance '+self.context['implementation']['policy_assessment_sha256']+' head '+head).encode()
        (self.root/'compliance/final.txt').write_bytes(final)
        evidence.update(implementer='fixture builder',artifacts=[dict(path='compliance/policy.md',sha256=digest(self.ledger)),dict(path='compliance/final.txt',sha256=digest(final))])
        for v in evidence['validations']:
            v.update(status='passed',exit_code=0,skipped=0,output='Fixture test output',started_at=stamp(),finished_at=stamp(),tool_version='Fixture Python',git_head=head,tests_run=1)
        for row in evidence['criteria']:row.update(status='passed',evidence='Fixture behavior checked')
        evidence['independent_review'].update(status='passed',reviewer='fixture independent reviewer',notes='Checked final diff, ledger and evidence',git_head=head,contract_sha256=core.canonical_hash(self.task),reviewed_at=stamp())
        payload=dict(schema_version='0.1',title='Reviewed contribution',body='Agent-assisted fixture. Refs #12',draft=True,maintainer_can_modify=False)
        pub=copy.deepcopy(self.context['implementation']);pub.pop('policy_review')
        pub.update(id='fixture-publication',event_reference='fixture://decision/2',issued_at=stamp(),actions=['push_head','create_draft'],evidence_sha256=core.canonical_hash(evidence),review_sha256=core.canonical_hash(evidence['independent_review']),git_head=head,git_tree=evidence['git_tree'],base_commit=self.base,base_tip=self.base,payload_sha256=core.canonical_hash(payload))
        self.context['publication_authorization']=pub;self.refresh_observations()
        return evidence,payload

    def publish(self,e,p):
        self.client.remote=(e['git_head'],e['git_tree'])
        self.client.published=dict(id=3001,number=30,html_url='https://github.com/acme/photos/pull/30',state='open',draft=True,merged=False,merged_at=None,closed_at=None,created_at=stamp(),user=dict(id=7,login='human',type='User'),title=p['title'],body=p['body'],maintainer_can_modify=False,head=dict(repo=dict(id=202,full_name='human/photos'),ref='tip-12',sha=e['git_head']),base=dict(repo=dict(id=101,full_name='acme/photos'),ref='main',sha=self.base))
        self.context['publication_claim']=dict(repository_id=101,pr_number=30,pr_id=3001,head_sha=e['git_head'],contract_sha256=core.canonical_hash(self.task),publication_authorization_sha256=core.canonical_hash(self.context['publication_authorization']))

    def journey(self,welcome):
        self.prepare_reviewed(welcome)
        r=self.verify();self.assertTrue(r['implementation_ready'],r['stage_blockers'])
        self.assertEqual(r['repository_approval']['status'],'candidate')
        e,p=self.implement_and_authorize()
        r=self.verify(e,p);self.assertTrue(r['draft_create_ready'],r['stage_blockers']);self.assertFalse(r['implementation_ready'])
        self.publish(e,p)
        r=self.verify(e,p);self.assertTrue(r['publication_verified'],r['stage_blockers'])
        self.assertEqual(r['next_action'],'return_draft');self.assertFalse(r['draft_create_ready'])
        self.assertTrue(any('/timeline?' in x for x in self.client.calls))
        self.assertFalse(any(x.startswith(('https:', 'http:')) for x in self.client.calls))
        return e,p

    def test_undeclared_complete_journey(self):self.journey(False)
    def test_welcome_complete_journey(self):self.journey(True)

    def test_changed_payload_head_and_unrelated_overlap_block(self):
        e,p=self.journey(False)
        changed=dict(p,body=p['body']+' changed')
        self.assertFalse(self.verify(e,changed)['publication_verified'])
        self.client.other_prs=[dict(id=4001,number=40,title='Fix thumbnail bounds',body='Refs #12',html_url='https://github.com/acme/photos/pull/40',head={'ref':'other'})]
        self.assertFalse(self.verify(e,p)['publication_verified'])

    def test_other_base_and_fork_history_block(self):
        self.prepare_reviewed();e,p=self.implement_and_authorize()
        self.assertTrue(self.verify(e,p)['draft_create_ready'])
        self.publish(e,p)
        prior=copy.deepcopy(self.client.published);prior.update(number=31,id=3101,state='closed',closed_at=stamp())
        prior['base'].update(ref='release',repo=dict(id=202,full_name='human/photos'))
        prior['html_url']='https://github.com/human/photos/pull/31'
        self.client.foreign_history=[prior]
        self.assertFalse(self.verify(e,p)['publication_verified'])

    def test_same_reviewer_prevalidation_review_and_missing_artifacts_block(self):
        self.prepare_reviewed();e,p=self.implement_and_authorize()
        for mutation in ('reviewer','review_time','artifact','skipped','argv','base','task_hash','tree','dirty','branch'):
            changed=copy.deepcopy(e)
            if mutation=='reviewer':changed['independent_review']['reviewer']=changed['implementer']
            if mutation=='review_time':changed['independent_review']['reviewed_at']='2020-01-01T00:00:00Z'
            if mutation=='artifact':changed['artifacts']=[]
            if mutation=='skipped':changed['validations'][0]['skipped']=1
            if mutation=='argv':changed['validations'][0]['argv']=['touch','/tmp/never-run']
            if mutation=='base':changed['base_commit']='a'*40
            if mutation=='task_hash':changed['contract_sha256']='b'*64
            if mutation=='tree':changed['git_tree']='c'*40
            if mutation=='dirty':(self.root/'src/thumb.rs').write_text('dirty')
            if mutation=='branch':self.git('checkout','-q','-b','wrong-branch')
            self.assertFalse(self.verify(changed,p)['draft_create_ready'],mutation)
            if mutation=='dirty':self.git('checkout','--','src/thumb.rs')

    def test_publication_binding_replay_mutations_block(self):
        self.prepare_reviewed();e,p=self.implement_and_authorize()
        original=copy.deepcopy(self.context)
        for key,value in [('id',original['implementation']['id']),('event_reference',original['implementation']['event_reference']),('fork_policy_inventory_sha256','0'*64),('evidence_sha256','0'*64),('review_sha256','0'*64),('payload_sha256','0'*64),('git_head','a'*40),('base_tip','b'*40),('undeclared_acknowledged',False)]:
            self.context=copy.deepcopy(original);self.context['publication_authorization'][key]=value;self.refresh_observations()
            self.assertFalse(self.verify(e,p)['draft_create_ready'],key)

    def test_partial_scan_or_closed_issue_blocks(self):
        self.prepare_reviewed();self.client.failed.add('/timeline')
        self.assertFalse(self.verify()['implementation_ready'])

    def test_wrong_numeric_cross_reference_identity_blocks(self):
        e,p=self.journey(False);self.client.wrong_cross_id=True
        self.assertFalse(self.verify(e,p)['publication_verified'])

    def test_open_scan_detail_race_blocks_recognition(self):
        e,p=self.journey(False)
        original=self.client.request
        def moved(endpoint):
            data=original(endpoint)
            if '/pulls?state=open' in endpoint and 'acme/photos' in endpoint and data:
                data[0]['head']['sha']='a'*40
            return data
        self.client.request=moved
        self.assertFalse(self.verify(e,p)['publication_verified'])

    def test_validation_argv_is_data_and_transport_only_reads(self):
        from unittest.mock import patch
        self.prepare_reviewed()
        self.task['validation'][0]['argv']=['sh','-c','touch /tmp/external-tip-never-execute']
        self.context['implementation']['contract_sha256']=core.canonical_hash(self.task);self.refresh_observations()
        e,p=self.implement_and_authorize()
        original=subprocess.run
        with patch.object(subprocess,'run',wraps=original) as run:
            result=self.verify(e,p)
        self.assertTrue(result['draft_create_ready'],result['stage_blockers'])
        self.assertTrue(run.call_args_list)
        for call in run.call_args_list:
            self.assertEqual(call.args[0][0],'git')
        self.assertTrue(all(not x.startswith(('https:','http:')) for x in self.client.calls))

    def test_publication_payload_utf8_bounds_and_control_title_block(self):
        self.prepare_reviewed();e,p=self.implement_and_authorize()
        for changed in (dict(p,title='unsafe\nheading'),dict(p,body='界'*20001),dict(p,maintainer_can_modify=True),dict(p,draft=False)):
            self.assertFalse(self.verify(e,changed)['draft_create_ready'])

    def test_policy_and_jar_bytes_drift_block(self):
        self.prepare_reviewed(True)
        self.client.contents['.tipjar.json']=b'{ "schema_version":"0.1", "status":"welcome"}'
        self.assertFalse(self.verify()['implementation_ready'])
        self.client.contents['.tipjar.json']=b'{"schema_version":"0.1","status":"closed"}'
        self.assertFalse(self.verify()['implementation_ready'])

    def test_history_source_other_base_blocks_new_creation(self):
        self.prepare_reviewed();e,p=self.implement_and_authorize();self.publish(e,p)
        self.context.pop('publication_claim')
        self.client.published['base']['ref']='release'
        self.client.published.update(state='closed',closed_at=stamp())
        self.assertFalse(self.verify(e,p)['draft_create_ready'])

    def test_complete_cli_stages_with_explicit_bounded_stdin(self):
        import contextlib
        import io
        from unittest.mock import patch
        from agent_contribute import cli
        self.prepare_reviewed()
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);task_path=d/'task.json';context_path=d/'context.json';payload_path=d/'payload.json';evidence_path=d/'evidence.json'
            task_path.write_text(json.dumps(self.task))
            def call(stage,evidence=None,payload=None,text=False):
                context_path.write_text(json.dumps(self.context))
                argv=(['--format','text'] if text else [])+['verify',str(task_path),'--stage',stage,'--repo-dir',str(self.root),'--host-context-stdin']
                if evidence is not None:
                    evidence_path.write_text(json.dumps(evidence));argv+=['--evidence',str(evidence_path)]
                if payload is not None:
                    payload_path.write_text(json.dumps(payload));argv+=['--publication-payload',str(payload_path)]
                output=io.StringIO()
                with context_path.open() as stdin,patch.object(cli.sys,'stdin',stdin),patch.object(core,'GitHub',return_value=self.client),contextlib.redirect_stdout(output):
                    status=cli.main(argv)
                result=output.getvalue() if text else json.loads(output.getvalue())
                self.assertEqual(status,0,result)
                return result
            self.assertTrue(call('implementation')['implementation_ready'])
            e,p=self.implement_and_authorize()
            self.assertTrue(call('draft',e,p)['draft_create_ready'])
            self.publish(e,p)
            self.assertTrue(call('published',e,p)['publication_verified'])
            text=call('published',e,p,text=True)
            self.assertIn('publication_verified: yes',text)
            self.assertNotIn('completion_ready',text)
