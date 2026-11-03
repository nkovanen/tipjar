"""Fictional board inputs; no network, enrollment, or execution authority."""
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import unittest

from agent_contribute import core
from tools import tipjar_board as board

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 3, 12, tzinfo=UTC)
FIXTURES = Path(__file__).parent / 'fixtures' / 'tipjar-board'


def fixture(name='valid'):
    return json.loads((FIXTURES / (name + '.json')).read_text())


def registry():
    return {'format': 'tipjar-board-registry/1', 'tips': [{
        'repository_id': 101, 'repository': 'fictional-demo/welcoming-jar',
        'pull_request_id': 201, 'number': 7, 'author_id': 301,
        'submission': {'controller_repository': 'nkovanen/tipjar',
                       'controller_repository_id': 1444643470, 'issue_id': 401,
                       'number': 11, 'body_sha256': hashlib.sha256(b'FICTIONAL DEMO consent\n').hexdigest()},
        'agent_assistance': 'self-declared', 'author_controls_repository': False}],
        'repositories': [], 'exclusions': []}


def encoded(value):
    return json.dumps(value).encode()


class ContractTests(unittest.TestCase):
    def test_registry_closed_bounded_and_unicode_strict(self):
        self.assertEqual(board.validate_registry(encoded(registry())), registry())
        for mutate in [lambda r: r.update(format='future'), lambda r: r.update(extra=1),
                       lambda r: r['tips'][0].update(author_id=True),
                       lambda r: r['tips'][0].update(author_id=9007199254740992),
                       lambda r: r['tips'][0].update(author_controls_repository=True),
                       lambda r: r['tips'][0]['submission'].update(url='https://evil.invalid')]:
            value = registry(); mutate(value)
            with self.subTest(value=value), self.assertRaises(core.ProtocolError):
                board.validate_registry(encoded(value))
        for data in [b'{"format":1,"format":2}', b'{"x":{"x":1,"x":2}}', b'\xff', b' ' * (1048576 + 1), b'{"x":"\\ud800"}']:
            with self.subTest(data=data[:50]), self.assertRaises(core.ProtocolError):
                board.validate_registry(data)

    def test_registry_deduplicates_consistent_prs_but_rejects_conflicting_pins(self):
        value = registry(); value['tips'] *= 2
        self.assertEqual(len(board.validate_registry(encoded(value))['tips']), 2)
        for key,new in [('number', 8), ('author_id', 302), ('repository_id', 102), ('repository', 'fictional-demo/renamed')]:
            value = registry(); other = copy.deepcopy(value['tips'][0]); other[key] = new; value['tips'].append(other)
            with self.subTest(key=key), self.assertRaises(core.ProtocolError):
                board.validate_registry(encoded(value))
        value = registry(); value['tips'] *= 501
        with self.assertRaises(core.ProtocolError): board.validate_registry(encoded(value))

    def test_snapshot_strict_identity_checks_expiry_and_old_served_state(self):
        for name in ('empty', 'valid', 'partial'):
            self.assertEqual(board.validate_board(encoded(fixture(name)), now=NOW), fixture(name))
        for change in [lambda b: b.update(expires_at='2026-11-05T12:00:01Z'),
                       lambda b: b['tips'][0].update(url='https://evil.invalid'),
                       lambda b: b['tips'][0].update(verified_at='2026-11-03T11:59:59Z'),
                       lambda b: b['tips'][0]['checks'].update(consent='2026-11-03T12:00:01Z'),
                       lambda b: b['directory']['observations'][0]['source'].update(path='README.md'),
                       lambda b: b['directory']['observations'][0].update(repository_id=102),
                       lambda b: b['repositories'][0].update(repository_id=9007199254740992),
                       lambda b: b['tips'][0].update(size={'additions': True, 'deletions': 0, 'changed_files': 0})]:
            value = fixture(); change(value)
            with self.subTest(value=value), self.assertRaises(core.ProtocolError): board.validate_board(value, now=NOW)
        expired = NOW + dt.timedelta(days=3)
        board.validate_board(fixture(), now=expired)
        with self.assertRaises(core.ProtocolError): board.require_fresh(fixture(), now=expired)

    def test_jar_utc_timestamp_spellings_preserve_snapshot_and_fail_closed(self):
        for fetched_at in ('2026-11-03T12:00:00Z', '2026-11-03T12:00:00+00:00'):
            value = fixture()
            value['directory']['observations'][0]['jar']['fetched_at'] = fetched_at
            original = encoded(value)
            with self.subTest(fetched_at=fetched_at):
                self.assertEqual(board.validate_board(value, now=NOW), value)
                self.assertEqual(board.validate_board(original, now=NOW), value)
                self.assertEqual(encoded(value), original)
        for fetched_at in ('2026-11-03T12:00:00', '2026-11-03T12:00:00+01:00',
                           '2026-11-03T12:00:01Z', 'invalidZ'):
            value = fixture()
            value['directory']['observations'][0]['jar']['fetched_at'] = fetched_at
            with self.subTest(fetched_at=fetched_at), self.assertRaises(core.ProtocolError):
                board.validate_board(value, now=NOW)

    def test_aggregation_dedup_ties_and_utc_periods(self):
        tip = fixture()['tips'][0]
        tips = [tip, copy.deepcopy(tip)]
        for pid,rid,author,merged in [(202,102,301,'2026-11-01T00:00:00Z'),
                                      (203,102,301,'2026-10-31T23:59:59Z'),
                                      (204,103,302,'2026-11-02T00:00:00Z'),
                                      (205,103,302,'2026-11-02T00:00:00Z')]:
            t = copy.deepcopy(tip); t.update(pull_request_id=pid,number=pid,repository_id=rid,author_id=author,merged_at=merged); tips.append(t)
        alltime = board.summarize(tips, now=NOW, period='all')
        self.assertEqual([(p['author_id'],p['points'],p['projects'],p['rank']) for p in alltime['people']], [(301,3,2,1),(302,2,1,2)])
        month = board.summarize(tips, now=NOW, period='month')
        self.assertEqual([(p['author_id'],p['points'],p['rank']) for p in month['people']], [(301,2,1),(302,2,1)])
        t = copy.deepcopy(tip); t['merged_at']='2026-10-04T12:00:00Z'
        self.assertEqual(board.summarize([t], now=NOW, period='30d')['people'][0]['points'],1)
        t['merged_at']='2026-10-04T11:59:59Z'
        self.assertEqual(board.summarize([t], now=NOW, period='30d')['people'],[])


class FakeGitHub:
    """Only the GitHub subprocess boundary is fake; all readers run normally."""
    def __init__(self):
        self.calls = []
        self.overrides = {}
        self.meta = {'id':101,'full_name':'fictional-demo/welcoming-jar','private':False,'visibility':'public',
                     'owner':{'id':501,'login':'fictional-demo'},'default_branch':'main','archived':False,'disabled':False,'language':'Python'}
        self.pr = {'id':201,'number':7,'html_url':'https://github.com/fictional-demo/welcoming-jar/pull/7',
                   'user':{'id':301,'login':'fictional-giver','type':'User'},'state':'closed','draft':False,'merged':True,
                   'merged_at':'2026-11-02T10:00:00Z','closed_at':'2026-11-02T10:00:00Z','merge_commit_sha':'e'*40,
                   'merged_by':{'id':601,'login':'fictional-maintainer','type':'User'},
                   'base':{'repo':copy.deepcopy(self.meta),'sha':'f'*40,'ref':'main'},
                   'head':{'sha':'1'*40,'ref':'fictional-fix'},'additions':5,'deletions':2,'changed_files':1}
        self.issue = {'id':401,'number':11,'html_url':'https://github.com/nkovanen/tipjar/issues/11',
                      'user':{'id':301,'login':'fictional-giver','type':'User'},'body':'FICTIONAL DEMO consent\n'}
        self.controller = {'id':1444643470,'full_name':'nkovanen/tipjar','private':False,'visibility':'public',
                           'owner':{'id':701,'login':'nkovanen'}}
        self.manifest = b'{"schema_version":"0.1","status":"welcome"}'
        self.search = {'total_count':0,'incomplete_results':False,'items':[]}

    def request_once(self, endpoint):
        import base64
        self.calls.append(endpoint)
        if endpoint in self.overrides:
            result = self.overrides[endpoint]
            if callable(result): result = result()
            if isinstance(result, Exception): raise result
            return copy.deepcopy(result)
        if endpoint.startswith('search/code?'):
            if 'filename%3AREADME.md' in endpoint:
                return {'total_count':0,'incomplete_results':False,'items':[]}
            return copy.deepcopy(self.search)
        if endpoint == 'repos/nkovanen/tipjar': return copy.deepcopy(self.controller)
        if endpoint == 'repos/nkovanen/tipjar/issues/11': return copy.deepcopy(self.issue)
        if endpoint == 'repos/fictional-demo/welcoming-jar': return copy.deepcopy(self.meta)
        if endpoint == 'repos/fictional-demo/welcoming-jar/pulls/7': return copy.deepcopy(self.pr)
        if endpoint.endswith('/commits/main'): return {'sha':'b'*40,'commit':{'tree':{'sha':'2'*40}}}
        blob = hashlib.sha1(b'blob '+str(len(self.manifest)).encode()+b'\0'+self.manifest).hexdigest()
        if '/git/trees/' in endpoint: return {'sha':'2'*40,'truncated':False,'tree':[{'path':'.tipjar.json','type':'blob','mode':'100644','sha':blob}]}
        if '/contents/' in endpoint: return {'type':'file','encoding':'base64','path':'.tipjar.json','sha':blob,'size':len(self.manifest),'content':base64.b64encode(self.manifest).decode()}
        raise core.ProtocolError('api_error','FICTIONAL PRIVATE ERROR MUST NOT LEAK')


COLLECT_NOW = dt.datetime(2026, 11, 4, 12, tzinfo=UTC)


def collect(client=None, reg=None, **options):
    return board.collect(reg or registry(), client or FakeGitHub(), now=COLLECT_NOW,
                         source_commit='a'*40, controller_id=1444643470, **options)


class CollectorTests(unittest.TestCase):
    def test_fresh_consent_merge_and_same_response_size(self):
        client = FakeGitHub(); result = collect(client)
        self.assertEqual(len(result['tips']),1)
        self.assertEqual(result['tips'][0]['size'],{'additions':5,'deletions':2,'changed_files':1})
        self.assertEqual(result['tips'][0]['submission_url'],'https://github.com/nkovanen/tipjar/issues/11')
        self.assertEqual(result['directory']['observations'][0]['disposition'],'welcome')
        self.assertEqual(client.calls.count('repos/fictional-demo/welcoming-jar/pulls/7'),1)
        board.require_fresh(result,now=COLLECT_NOW)

    def test_edited_unicode_newline_missing_and_spoofed_consent_suppress_tip(self):
        for change in [lambda c:c.issue.update(body='FICTIONAL DEMO consent\r\n'),
                       lambda c:c.issue.update(body=None), lambda c:c.issue.update(id=402),
                       lambda c:c.issue.update(number=12), lambda c:c.issue['user'].update(id=302),
                       lambda c:c.issue.update(pull_request={}),lambda c:c.issue.update(html_url='https://evil.invalid'),
                       lambda c:c.controller.update(id=1),lambda c:c.controller.update(full_name='someone/else'),
                       lambda c:c.controller.update(private=True),
                       lambda c:c.overrides.update({'repos/nkovanen/tipjar/issues/11':core.ProtocolError('api_error','secret')})]:
            c=FakeGitHub();change(c)
            with self.subTest(change=change):
                result=collect(c);self.assertEqual(result['tips'],[])
                self.assertTrue(result['coverage']['partial']); self.assertNotIn('secret',json.dumps(result))
        c=FakeGitHub();c.issue['body']='e\u0301';r=registry();r['tips'][0]['submission']['body_sha256']=hashlib.sha256('\u00e9'.encode()).hexdigest()
        self.assertEqual(collect(c,r)['tips'],[])

    def test_private_identity_merge_and_size_fail_closed(self):
        for change in [lambda c:c.meta.update(private=True),lambda c:c.meta.update(visibility='private'),
                       lambda c:c.pr['base']['repo'].update(private=True),lambda c:c.pr['base']['repo'].update(visibility='private'),
                       lambda c:c.pr.update(id=202),lambda c:c.pr.update(number=8),
                       lambda c:c.pr['user'].update(id=302),lambda c:c.pr['user'].update(type='Bot'),
                       lambda c:c.pr.update(draft=True),lambda c:c.pr.update(merged=False),
                       lambda c:c.pr['merged_by'].update(id=301),lambda c:c.meta['owner'].update(id=301),
                       lambda c:c.pr.update(merged_at='2099-01-01T00:00:00Z'),
                       lambda c:c.pr.update(closed_at='2026-11-01T00:00:00Z'),
                       lambda c:c.pr.update(additions=True),lambda c:c.pr.update(changed_files=9007199254740992),
                       lambda c:c.meta.update(full_name='fictional-demo/renamed')]:
            c=FakeGitHub();change(c)
            with self.subTest(change=change): self.assertEqual(collect(c)['tips'],[])
        c=FakeGitHub();c.pr.pop('additions');c.pr['deletions']=None
        self.assertEqual(collect(c)['tips'][0]['size'],{'additions':None,'deletions':None,'changed_files':1})

    def test_exclusions_and_duplicate_pr_do_not_create_points(self):
        r=registry();r['tips']*=2
        self.assertEqual(len(collect(reg=r)['tips']),1)
        for exclusion in [{'kind':'tip','repository_id':101,'pull_request_id':201,'reason':'reverted'},
                          {'kind':'repository','repository_id':101,'reason':'owner_opt_out'},
                          {'kind':'author','author_id':301,'reason':'withdrawal'}]:
            r=registry();r['exclusions']=[exclusion]
            result=collect(reg=r);self.assertEqual(result['tips'],[])
            if exclusion['kind']=='repository': self.assertEqual(result['repositories'],[])

    def test_closed_and_unknown_jar_retain_public_history(self):
        c=FakeGitHub();c.manifest=b'{"schema_version":"0.1","status":"closed"}'
        result=collect(c);self.assertEqual(len(result['tips']),1)
        self.assertEqual(result['directory']['observations'][0]['disposition'],'closed')
        c=FakeGitHub();c.overrides['repos/fictional-demo/welcoming-jar/commits/main']=core.ProtocolError('api_error','secret')
        result=collect(c);self.assertEqual(len(result['tips']),1)
        self.assertEqual(result['directory']['observations'][0]['disposition'],'unknown')
        self.assertIsNone(result['directory']['observations'][0]['jar'])

    def test_final_private_recheck_scrubs_all_joined_rows(self):
        c=FakeGitHub();calls=0
        def metadata():
            nonlocal calls
            calls+=1
            return dict(c.meta, private=calls>=3, visibility='private' if calls>=3 else 'public')
        c.overrides['repos/fictional-demo/welcoming-jar']=metadata
        result=collect(c)
        self.assertEqual(result['tips'],[]);self.assertEqual(result['repositories'],[])
        self.assertEqual(result['directory']['observations'],[])
        self.assertNotIn('fictional-demo',json.dumps(result))

    def test_failed_search_retains_partial_flags_without_rows(self):
        c=FakeGitHub();c.overrides['search/code?q=filename%3A.tipjar.json+path%3A%2F&per_page=5&page=1']=core.ProtocolError('api_error','private name')
        r={'format':'tipjar-board-registry/1','tips':[],'repositories':[],'exclusions':[]}
        result=collect(c,r)
        self.assertTrue(result['directory']['search_failed']);self.assertFalse(result['directory']['complete'])
        self.assertTrue(result['coverage']['partial']);self.assertEqual(result['tips'],[])

    def test_budget_counts_failed_both_methods_no_retry_and_safe_routes(self):
        c=FakeGitHub();b=board.BudgetClient(c,limit=2,clock=lambda:COLLECT_NOW)
        with self.assertRaises(core.ProtocolError): b.request('repos/fictional-demo/missing',attempts=999)
        b.request_once('repos/nkovanen/tipjar')
        with self.assertRaises(core.ProtocolError): b.request('repos/nkovanen/tipjar')
        self.assertEqual(len(c.calls),2)
        c=FakeGitHub();b=board.BudgetClient(c,clock=lambda:COLLECT_NOW)
        for _ in range(5000):b.request_once('repos/nkovanen/tipjar')
        with self.assertRaises(core.ProtocolError):b.request_once('repos/nkovanen/tipjar')
        self.assertEqual(len(c.calls),5000)
        for endpoint in ['https://evil.invalid','repos/a/b;whoami','/repos/a/b','repos/a/b/../../user','user','repos/a/b?x=1']:
            with self.subTest(endpoint=endpoint), self.assertRaises(core.ProtocolError):board.BudgetClient(c).request(endpoint)

    def test_read_starts_drive_minimum_and_expiry_crossing_blocks(self):
        class Clock:
            def __init__(self,step):self.value=COLLECT_NOW;self.step=step
            def __call__(self):
                result=self.value;self.value+=self.step;return result
        result=collect(clock=Clock(dt.timedelta(seconds=1)))
        tip=result['tips'][0]
        self.assertEqual(tip['verified_at'],min(tip['checks'].values()))
        self.assertEqual(result['expires_at'],'2026-11-06T12:00:00Z')
        with self.assertRaises(core.ProtocolError):collect(clock=Clock(dt.timedelta(hours=12)))

    def test_exclusive_output_and_invalid_registry_never_publish(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'registry.json';output=Path(temp)/'board.json';path.write_bytes(encoded(registry()))
            args=['--registry',str(path),'--output',str(output),'--source-commit','a'*40,'--controller-id','1444643470']
            with patch.object(board.core,'GitHub',return_value=FakeGitHub()):self.assertEqual(board.main(args),0)
            before=output.read_bytes()
            with patch.object(board.core,'GitHub',return_value=FakeGitHub()):self.assertNotEqual(board.main(args),0)
            self.assertEqual(output.read_bytes(),before)
            output.unlink();path.write_text('{"format":"future"}')
            with patch.object(board.core,'GitHub',return_value=FakeGitHub()):self.assertNotEqual(board.main(args),0)
            self.assertFalse(output.exists())


class SelectionAndProjectionTests(unittest.TestCase):
    def test_private_pr_base_scrubs_identifying_directory_payload(self):
        c=FakeGitHub();c.pr['base']['repo']['private']=True
        result=collect(c)
        self.assertEqual(result['repositories'],[])
        self.assertEqual(result['directory']['observations'],[])
        self.assertNotIn('fictional-demo',json.dumps(result))

    def test_truncated_search_is_publishable_partial(self):
        c=FakeGitHub();c.search['total_count']=5
        result=collect(c)
        self.assertTrue(result['directory']['truncated'])
        self.assertFalse(result['directory']['complete'])
        self.assertTrue(result['coverage']['partial'])
        self.assertEqual(len(result['tips']),1)

    def test_null_private_search_hits_are_aggregate_only(self):
        c=FakeGitHub();c.search={'total_count':2,'incomplete_results':True,'items':[
            {'repository':{'id':900,'full_name':'private-demo/hidden','private':True,'owner':{'id':901,'login':'private-demo'}}},None]}
        result=collect(c)
        self.assertTrue(result['directory']['server_incomplete'])
        self.assertEqual(result['coverage']['unknown_repositories'],1)
        self.assertEqual(result['coverage']['excluded_repositories'],1)
        self.assertNotIn('private-demo',json.dumps(result))
        self.assertNotIn(900,[r['repository_id'] for r in result['repositories']])

    def test_whole_groups_admit_first_200_and_exact_omitted_counts(self):
        tips=[];repos={};observations=[]
        for rid in reversed(range(1,202)):
            repos[rid]={'repository_id':rid}
            tips.append({'repository_id':rid,'pull_request_id':rid})
            observations.append({'repository_id':rid})
        directory=fixture('empty')['directory'];coverage=fixture('empty')['coverage']
        chosen,rows,obs=board._selection(tips,repos,observations,directory,coverage)
        self.assertEqual([r['repository_id'] for r in rows],list(range(1,201)))
        self.assertEqual(len(chosen),200);self.assertEqual(len(obs),200)
        self.assertEqual((coverage['omitted_tips'],coverage['omitted_repositories'],coverage['omitted_directory_observations']),(1,1,1))
        # A large group cannot fit the byte cap; skip it and continue numerically.
        observations=[{'repository_id':1,'padding':'x'*1048576},{'repository_id':2}]
        coverage=fixture('empty')['coverage']
        chosen,rows,obs=board._selection(tips[:0],{1:{'repository_id':1},2:{'repository_id':2}},observations,directory,coverage)
        self.assertEqual(rows,[{'repository_id':2}])

    def test_duplicate_or_conflicting_directory_identity_rejects_envelope(self):
        value=fixture();value['directory']['observations']*=2
        with self.assertRaises(core.ProtocolError):board.validate_board(value,now=NOW)
        c=FakeGitHub();c.search={'total_count':1,'incomplete_results':False,'items':[
            {'repository':dict(c.meta,id=102),'name':'.tipjar.json','path':'.tipjar.json','sha':'c'*40}]}
        with self.assertRaises(core.ProtocolError):collect(c)

    def test_submissions_can_renew_consent_but_never_multiply_points(self):
        c=FakeGitHub();c.issue['body']='edited old issue'
        r=registry();new=copy.deepcopy(r['tips'][0]);new['submission'].update(issue_id=402,number=12)
        r['tips'].append(new)
        c.overrides['repos/nkovanen/tipjar/issues/12']=dict(c.issue,id=402,number=12,body='FICTIONAL DEMO consent\n',html_url='https://github.com/nkovanen/tipjar/issues/12')
        result=collect(c,r)
        self.assertEqual(len(result['tips']),1)
        self.assertEqual(result['tips'][0]['submission_url'],'https://github.com/nkovanen/tipjar/issues/12')

    def test_private_during_indexed_search_invalidates_earlier_public_tip(self):
        c=FakeGitHub();c.search={'total_count':1,'incomplete_results':False,'items':[
            {'repository':dict(c.meta,private=True),'name':'.tipjar.json','path':'.tipjar.json','sha':'c'*40}]}
        result=collect(c)
        self.assertEqual(result['tips'],[])
        self.assertEqual(result['repositories'],[])


class IndependentSchemaTests(unittest.TestCase):
    def test_closed_board_schemas_with_independent_ajv(self):
        import os
        import shutil
        import subprocess
        module=os.environ.get('TIPJAR_PARITY_AJV','ajv/dist/2020')
        required='TIPJAR_PARITY_AJV' in os.environ
        if not shutil.which('node'):
            if required:self.fail('Required board parity needs Node')
            self.skipTest('Optional board parity needs Node/Ajv')
        probe=subprocess.run(['node','-e','require(process.argv[1])',module],capture_output=True,timeout=15)
        if probe.returncode:
            if required:self.fail('Required board parity cannot load Ajv')
            self.skipTest('Optional board parity needs Ajv2020')
        script="""const fs=require('fs'),Ajv=require(process.argv[1]);const {schema,cases}=JSON.parse(fs.readFileSync(0,'utf8'));const validate=new Ajv({strict:true}).compile(schema);process.stdout.write(JSON.stringify(cases.map(x=>validate(x))));"""
        for name,good in [('tipjar-board',fixture()),('tipjar-board-registry',registry()),('tipjar-board-v2',v2_fixture())]:
            cases=[good];expected=[True]
            for mutation in [lambda v:v.update(unexpected=True),lambda v:v.update(format='unknown'),
                             lambda v:v['tips'][0].update(author_id=True),
                             lambda v:v['tips'][0].update(author_id=9007199254740992)]:
                v=copy.deepcopy(good);mutation(v);cases.append(v);expected.append(False)
            if name in ('tipjar-board','tipjar-board-v2'):
                v=copy.deepcopy(good);v['source_commit']='X'+'a'*40;cases.append(v);expected.append(False)
                v=copy.deepcopy(good);v['source_commit']='a'*39+'z';cases.append(v);expected.append(False)
            else:
                v=copy.deepcopy(good);v['tips'][0]['repository']='!fictional-demo/welcoming-jar';cases.append(v);expected.append(False)
            schema=json.loads((Path(board.__file__).parent/'schemas'/(name+'.schema.json')).read_text())
            result=subprocess.run(['node','-e',script,module],input=json.dumps({'schema':schema,'cases':cases}),text=True,capture_output=True,check=True,timeout=15)
            self.assertEqual(json.loads(result.stdout),expected)


class BoundaryRegressionTests(unittest.TestCase):
    def test_one_submission_issue_cannot_enroll_two_different_prs(self):
        r=registry();other=copy.deepcopy(r['tips'][0]);other.update(pull_request_id=202,number=8)
        r['tips'].append(other)
        with self.assertRaises(core.ProtocolError):board.validate_registry(r)

    def test_future_reader_shape_refuses_whole_collection(self):
        from unittest.mock import patch
        jar=fixture()['directory']['observations'][0]['jar']
        jar['source_kind']='readme'
        with patch.object(board.tipjar,'read_jar',return_value=jar):
            with self.assertRaises(core.ProtocolError) as raised:collect()
        self.assertEqual(raised.exception.code,'unsupported_board_reader')

    def test_invalid_default_branch_never_enters_a_get_route(self):
        c=FakeGitHub();c.meta['default_branch']='../user'
        result=collect(c)
        self.assertEqual(result['repositories'],[])
        self.assertFalse(any('/commits/' in route for route in c.calls))

    def test_registry_author_limit(self):
        r=registry();original=r['tips'][0]
        r['tips']=[]
        for n in range(101):
            t=copy.deepcopy(original);t.update(pull_request_id=200+n,number=1+n,author_id=300+n)
            t['submission'].update(issue_id=400+n,number=1+n);r['tips'].append(t)
        with self.assertRaises(core.ProtocolError):board.validate_registry(r)

    def test_curator_updates_renamed_hint_with_same_numeric_repo_id(self):
        c=FakeGitHub();r=registry();name='fictional-demo/renamed'
        r['tips'][0]['repository']=name;c.meta['full_name']=name
        c.pr['base']['repo']['full_name']=name;c.pr['html_url']='https://github.com/'+name+'/pull/7'
        c.overrides['repos/'+name]=c.meta
        c.overrides['repos/'+name+'/pulls/7']=c.pr
        result=collect(c,r)
        self.assertEqual(len(result['tips']),1)
        self.assertEqual(result['repositories'][0]['repository_id'],101)
        self.assertEqual(result['repositories'][0]['repository'],name)

    def test_full_truncated_index_keeps_partial_even_with_duplicate_hits(self):
        c=FakeGitHub();hit={'repository':c.meta,'name':'.tipjar.json','path':'.tipjar.json','sha':'c'*40}
        c.search={'total_count':6,'incomplete_results':False,'items':[hit]*5}
        result=collect(c)
        self.assertTrue(result['directory']['truncated'])
        self.assertFalse(result['directory']['complete'])
        self.assertEqual(len(result['tips']),1)


V2_FIXTURES = FIXTURES / 'v2'
MANIFEST_SEARCH = 'search/code?q=filename%3A.tipjar.json+path%3A%2F&per_page=5&page=1'
README_SEARCH = 'search/code?q=%22tipjar%3Awelcome%3Av1%22+filename%3AREADME.md+path%3A%2F&per_page=5&page=1'
README_WELCOME = (b'<!-- tipjar:welcome:v1 -->\n'
    b'[![Agent-work tips welcome](https://nkovanen.github.io/tipjar/brand/agent-work-welcome.svg)]'
    b'(https://nkovanen.github.io/tipjar/?repo=fictional-demo%2Fwelcoming-jar)\n\n# FICTIONAL DEMO\n')


def v2_fixture(name='readme-welcome'):
    return json.loads((V2_FIXTURES / (name + '.json')).read_text())


class InvitationGitHub(FakeGitHub):
    """Real canonical invitation2 reader over fictional pinned trees/content."""
    def __init__(self, files=None):
        super().__init__()
        self.files = {'.tipjar.json': self.manifest} if files is None else files

    def request_once(self, endpoint):
        import base64
        if endpoint in self.overrides:
            return super().request_once(endpoint)
        if '/git/trees/' in endpoint:
            self.calls.append(endpoint)
            return {'sha':'2'*40,'truncated':False,'tree':[
                {'path':path,'type':'blob','mode':'100644','size':len(data),
                 'sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()}
                for path,data in self.files.items()]}
        if '/contents/' in endpoint:
            self.calls.append(endpoint)
            path=endpoint.split('/contents/')[1].split('?')[0]
            data=self.files[path]
            return {'type':'file','path':path,'encoding':'base64','size':len(data),
                    'sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),
                    'content':base64.b64encode(data).decode()}
        return super().request_once(endpoint)


class Board2ContractTests(unittest.TestCase):
    def test_shared_corpus_preserves_parse_and_freshness_contract(self):
        index=json.loads((V2_FIXTURES/'corpus.json').read_text())
        now=dt.datetime.fromisoformat(index['now'].replace('Z','+00:00'))
        for case in index['cases']:
            data=(V2_FIXTURES/case['file']).read_bytes()
            with self.subTest(file=case['file']):
                try:
                    value=board.validate_board(data,now=now)
                    valid=True
                except core.ProtocolError:valid=False
                self.assertEqual(valid,case['valid'])
                try:
                    board.require_fresh(data,now=now)
                    fresh=True
                except core.ProtocolError:fresh=False
                self.assertEqual(fresh,case['fresh'])
                if valid:self.assertEqual(value,json.loads(data))

    def test_both_versions_validate_without_current_reader_validation(self):
        from unittest.mock import patch
        with patch.object(board.tipjar,'_complete_report',side_effect=AssertionError('mutable reader validator used')), \
             patch.object(board.tipjar,'parse_manifest',side_effect=core.ProtocolError('future_parser','Current parser changed')):
            board.validate_board(fixture(),now=NOW)
            board.validate_board(v2_fixture('manifest-welcome'),now=NOW)
            board.validate_board(v2_fixture(),now=NOW)
        self.assertEqual(board.summarize(fixture()['tips'],now=NOW,period='all'),
                         board.summarize(v2_fixture()['tips'],now=NOW,period='all'))

    def test_archived_board1_still_requires_pinned_commit_without_mutable_reader(self):
        from unittest.mock import patch
        value=fixture();obs=value['directory']['observations'][0]
        obs['jar']['commit']=None;obs['source']=None
        with patch.object(board.tipjar,'_complete_report',side_effect=AssertionError('mutable validator used')):
            with self.assertRaises(core.ProtocolError):board.validate_board(value,now=NOW)

    def test_v2_source_complete_requires_all_pins_and_matches_raw_jar(self):
        for name in ('manifest-welcome','readme-welcome','readme-undeclared','absent'):
            for field,new in [('source',None),('repository_id',102)]:
                value=v2_fixture(name);value['directory']['observations'][0][field]=new
                with self.subTest(name=name,field=field),self.assertRaises(core.ProtocolError):
                    board.validate_board(value,now=NOW)
        for field,new in [('commit','e'*40),('blob_sha','e'*40),('tree_sha','e'*40),('sha256','e'*64)]:
            value=v2_fixture();value['directory']['observations'][0]['source'][field]=new
            with self.subTest(field=field),self.assertRaises(core.ProtocolError):board.validate_board(value,now=NOW)

    def test_unknown_formats_duplicate_keys_and_future_times_fail_closed(self):
        for data in [b'{"format":"tipjar-board/2","format":"tipjar-board/1"}',
                     (V2_FIXTURES/'readme-welcome.json').read_bytes().replace(b'"tree_sha":',b'"tree_sha":"' + b'a'*40 + b'","tree_sha":',1)]:
            with self.assertRaises(core.ProtocolError):board.validate_board(data,now=NOW)
        for stamp in ('2026-11-03T12:00:01Z','2026-11-03T12:00:00','2026-11-03T12:00:00+01:00', '20261103T120000+00:00'):
            value=v2_fixture();value['directory']['observations'][0]['jar']['fetched_at']=stamp
            with self.subTest(stamp=stamp),self.assertRaises(core.ProtocolError):board.validate_board(value,now=NOW)
        for stamp in ('2026-11-03T12:00:00Z','2026-11-03T12:00:00+00:00'):
            value=v2_fixture();value['directory']['observations'][0]['jar']['fetched_at']=stamp
            self.assertEqual(board.validate_board(value,now=NOW),value)


class Board2CollectorTests(unittest.TestCase):
    def test_reader2_manifest_readme_plain_and_absent_sources(self):
        for files,kind,state,path in [({'.tipjar.json':b'{"schema_version":"0.1","status":"welcome"}'},'manifest','welcome','.tipjar.json'),
                                    ({'README.md':README_WELCOME},'readme','welcome','README.md'),
                                    ({'README.md':b'# FICTIONAL DEMO\n'},'readme','undeclared','README.md'),
                                    ({},'absent','undeclared',None)]:
            with self.subTest(kind=kind,state=state):
                c=InvitationGitHub(files);result=collect(c)
                self.assertEqual(result['format'],'tipjar-board/2')
                self.assertEqual(len(result['tips']),1)
                obs=result['directory']['observations'][0]
                self.assertEqual(obs['disposition'],state)
                self.assertEqual(obs['source']['kind'],kind)
                self.assertEqual(obs['source']['path'],path)
                self.assertEqual(obs['source']['tree_sha'],'2'*40)
                self.assertEqual(obs['jar']['repository_id'],101)
                self.assertEqual(set(obs['source']),{'kind','path','commit','tree_sha','blob_sha','sha256'})
                if path:
                    import hashlib
                    self.assertEqual(obs['source']['sha256'],hashlib.sha256(files[path]).hexdigest())
                else:self.assertIsNone(obs['source']['blob_sha']);self.assertIsNone(obs['source']['sha256'])
                self.assertEqual([e for e in c.calls if e.startswith('search/code?')],[MANIFEST_SEARCH,README_SEARCH])

    def test_canonical_manifest_precedence_and_copied_or_invalid_readme(self):
        for files,state in [({'.tipjar.json':b'{"schema_version":"0.1","status":"closed"}','README.md':README_WELCOME},'closed'),
                            ({'.tipjar.json':b'bad manifest','README.md':README_WELCOME},'unknown'),
                            ({'.tipjar.json':b'{"schema_version":"99","status":"welcome"}','README.md':README_WELCOME},'unknown'),
                            ({'README.md':README_WELCOME.replace(b'fictional-demo%2Fwelcoming-jar',b'copied-parent%2Fproject')},'unknown'),
                            ({'README.md':README_WELCOME+README_WELCOME},'unknown')]:
            with self.subTest(state=state,files=list(files)):
                c=InvitationGitHub(files);result=collect(c);obs=result['directory']['observations'][0]
                self.assertEqual(obs['disposition'],state);self.assertEqual(len(result['tips']),1)
                if state=='unknown':self.assertIsNone(obs['jar']);self.assertIsNone(obs['source'])
                else:self.assertEqual(obs['source']['kind'],'manifest')
                if '.tipjar.json' in files:self.assertFalse(any('/contents/README.md?' in x for x in c.calls))

    def test_second_readme_search_private_hit_scrubs_earlier_public_tip(self):
        c=InvitationGitHub({'README.md':README_WELCOME})
        c.overrides[README_SEARCH]={'total_count':1,'incomplete_results':False,'items':[
            {'repository':dict(c.meta,private=True),'path':'README.md','name':'README.md','sha':'c'*40}]}
        result=collect(c)
        # The PR read succeeds before the second search; all later metadata stays public.
        self.assertLess(c.calls.index('repos/fictional-demo/welcoming-jar/pulls/7'),c.calls.index(README_SEARCH))
        self.assertEqual(result['tips'],[]);self.assertEqual(result['repositories'],[])
        self.assertEqual(result['directory']['observations'],[])
        self.assertNotIn('fictional-demo',json.dumps(result))
        self.assertEqual(result['coverage']['unknown_tips'],1)

    def test_both_raw_searches_capture_private_ids_before_finder_scrubs_them(self):
        for endpoint in (MANIFEST_SEARCH,README_SEARCH):
            for visibility in ({'private':True},{'private':False,'visibility':'internal'}):
                c=InvitationGitHub();c.overrides[endpoint]={'items':[{'repository':dict(c.meta,**visibility)}]}
                b=board.BudgetClient(c,clock=lambda:COLLECT_NOW)
                b.request_once(endpoint)
                b.request('repos/fictional-demo/welcoming-jar')
                with self.subTest(endpoint=endpoint,visibility=visibility):
                    self.assertIn(101,b.private_ids);self.assertIn('fictional-demo/welcoming-jar',b.private_names)

    def test_each_search_failure_is_partial_and_preserved_without_rows(self):
        empty={'format':'tipjar-board-registry/1','tips':[],'repositories':[],'exclusions':[]}
        for failed in (MANIFEST_SEARCH,README_SEARCH):
            c=InvitationGitHub();c.overrides[failed]=core.ProtocolError('api_error','FICTIONAL PRIVATE ERROR')
            result=collect(c,empty)
            with self.subTest(failed=failed):
                self.assertTrue(result['coverage']['partial']);self.assertTrue(result['directory']['search_failed'])
                self.assertFalse(result['directory']['complete']);self.assertEqual(result['tips'],[])
                self.assertEqual(c.calls[-2:],[MANIFEST_SEARCH,README_SEARCH])
                self.assertNotIn('PRIVATE ERROR',json.dumps(result))

    def test_both_searches_dedup_same_repository_and_preserve_partial_flags(self):
        c=InvitationGitHub({'README.md':README_WELCOME})
        for endpoint,path in [(MANIFEST_SEARCH,'.tipjar.json'),(README_SEARCH,'README.md')]:
            c.overrides[endpoint]={'total_count':6,'incomplete_results':True,'items':[
                {'repository':c.meta,'name':path,'path':path,'sha':'c'*40}]}
        result=collect(c)
        self.assertEqual(len(result['tips']),1);self.assertEqual(len(result['repositories']),1)
        self.assertEqual(len(result['directory']['observations']),1)
        self.assertTrue(result['directory']['server_incomplete']);self.assertTrue(result['directory']['truncated'])
        self.assertFalse(result['directory']['complete'])

    def test_readme_read_start_is_retained_with_final_recheck_and_conservative_expiry(self):
        class Clock:
            def __init__(self):self.value=COLLECT_NOW
            def __call__(self):
                v=self.value;self.value+=dt.timedelta(seconds=1);return v
        c=InvitationGitHub({'README.md':README_WELCOME});clock=Clock()
        result=collect(c,clock=clock)
        obs=result['directory']['observations'][0]
        self.assertEqual(len(obs['checks']),5)  # metadata, commit, tree, README, final metadata
        self.assertEqual(obs['verified_at'],obs['checks'][0])
        content_index=c.calls.index('repos/fictional-demo/welcoming-jar/contents/README.md?ref='+'b'*40)
        self.assertEqual(obs['checks'][3],(COLLECT_NOW+dt.timedelta(seconds=content_index)).isoformat().replace('+00:00','Z'))
        self.assertEqual(result['expires_at'],'2026-11-06T12:00:00Z')
        self.assertEqual(c.calls[-1],'repos/fictional-demo/welcoming-jar')

    def test_current_emission_ignores_changed_library_default_and_rejects_unknown_report(self):
        from unittest.mock import patch
        original=board.tipjar.read_jar
        seen=[]
        def read(*args,**kwargs):
            seen.append(kwargs.get('invitation_protocol'))
            return original(*args,**kwargs)
        with patch.object(board.tipjar,'read_jar',side_effect=read):
            result=collect(InvitationGitHub())
        self.assertEqual(result['format'],'tipjar-board/2')
        self.assertTrue(seen);self.assertEqual(set(seen),{'tipjar-invitation/2'})
        jar=v2_fixture()['directory']['observations'][0]['jar'];jar['new_field']='future'
        with patch.object(board.tipjar,'read_jar',return_value=jar):
            with self.assertRaises(core.ProtocolError) as raised:collect(InvitationGitHub())
        self.assertEqual(raised.exception.code,'unsupported_board_reader')


class FrozenManifestTests(unittest.TestCase):
    def test_frozen_manifest_unicode_uniqueness_bounds_and_status(self):
        from unittest.mock import patch
        # Independent expected results, including the original Unicode White_Space boundary.
        cases = [({}, True), ({'wanted':['\ufeff']}, True), ({'wanted':['\u0085x']}, True),
                 ({'wanted':['😀'*500]}, True), ({'wanted':['x'*500]*2}, False),
                 ({'wanted':['\u0085']}, False), ({'boundaries':['\u2003']}, False),
                 ({'wanted':['\x1cx']}, False), ({'wanted':['x\x7f']}, False),
                 ({'wanted':['x'*501]}, False), ({'wanted':['']}, False),
                 ({'wanted':['item'+str(n) for n in range(17)]}, False),
                 ({'status':'closed'}, False), ({'schema_version':'2'}, False), ({'unexpected':True}, False),
                 ({'wanted':['😀'*500+str(n) for n in range(16)]}, False)]
        # Two individually valid arrays can exceed the original16384-byte manifest cap.
        oversized = {'wanted':[('😀'*498)+str(n) for n in range(8)],
                     'boundaries':[('😀'*498)+str(n) for n in range(8,16)]}
        self.assertTrue(all(len(text) <= 500 for texts in oversized.values() for text in texts))
        cases.append((oversized,False))
        for base in (fixture(), v2_fixture('manifest-welcome')):
            for change, expected in cases:
                value=copy.deepcopy(base)
                value['directory']['observations'][0]['jar']['manifest']={'schema_version':'0.1','status':'welcome',**change}
                with self.subTest(format=value['format'],change=repr(change)[:80]), \
                     patch.object(board.tipjar,'parse_manifest',side_effect=AssertionError('mutable parser used')), \
                     patch.object(board.tipjar,'_complete_report',side_effect=AssertionError('mutable report validator used')):
                    try:
                        board.validate_board(value,now=NOW);accepted=True
                    except core.ProtocolError:accepted=False
                    self.assertEqual(accepted,expected)
