"""Fictional curator observations, never enrollment or consent authority."""
import copy
import datetime as dt
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from agent_contribute import core
from tests.test_tipjar_board import FakeGitHub

NOW = dt.datetime(2026, 11, 4, 12, tzinfo=dt.timezone.utc)
REFERENCE = 'fictional-demo/welcoming-jar#7'
ROUTES = ['repos/nkovanen/tipjar', 'repos/nkovanen/tipjar/issues/11',
          'repos/fictional-demo/welcoming-jar', 'repos/fictional-demo/welcoming-jar/pulls/7',
          'repos/nkovanen/tipjar/issues/11', 'repos/fictional-demo/welcoming-jar', 'repos/nkovanen/tipjar']


class IntakeCase(unittest.TestCase):
    def tool(self):
        self.assertTrue((Path(__file__).resolve().parents[1] / 'tools/tipjar_board_intake.py').is_file(),
                        'The approved intake helper is not implemented')
        return importlib.import_module('tools.tipjar_board_intake')

    def observe(self, client=None):
        return self.tool().intake(11, REFERENCE, client or FakeGitHub(), clock=lambda: NOW)

class IntakeTests(IntakeCase):
    def test_exact_bytes_fixed_calls_and_no_declaration_authority(self):
        client = FakeGitHub()
        client.issue['body'] = 'FICTIONAL DEMO\r\ne\u0301 café \n'
        result = self.observe(client)
        self.assertEqual(client.calls, ROUTES)
        self.assertEqual(set(result), {'format','status','generated_at','checks','pins','submission_body','review_checklist'})
        self.assertEqual((result['format'], result['status']), ('tipjar-board-intake/1','review-required'))
        self.assertEqual(result['submission_body'], 'FICTIONAL DEMO\r\ne\u0301 café \n')
        self.assertEqual(result['pins'], {
            'repository_id':101,'repository':'fictional-demo/welcoming-jar','pull_request_id':201,
            'number':7,'author_id':301,'submission':{'controller_repository':'nkovanen/tipjar',
            'controller_repository_id':1444643470,'issue_id':401,'number':11,
            'body_sha256':hashlib.sha256('FICTIONAL DEMO\r\ne\u0301 café \n'.encode('utf-8')).hexdigest()}})
        self.assertEqual(result['checks'], ['2026-11-04T12:00:00Z'] * 7)
        self.assertEqual(len(result['review_checklist']), 5)
        from tools.tipjar_board import validate_registry
        for invalid in [result, dict(format='tipjar-board-registry/1',tips=[result['pins']],repositories=[],exclusions=[])]:
            with self.assertRaises(core.ProtocolError): validate_registry(invalid)

    def test_observed_body_change_refuses_but_equal_bytes_do_not_prove_edit_history(self):
        client = FakeGitHub()
        first = copy.deepcopy(client.issue)
        client.overrides[ROUTES[1]] = lambda: first if client.calls.count(ROUTES[1]) == 1 else dict(first, body='changed')
        with self.assertRaises(core.ProtocolError): self.observe(client)
        self.assertEqual(len(client.calls), 5)
        for body in ['edited before first read', 'restored identical bytes', '- [ ] unchecked\nI withdraw', '<script>$(command)</script>\x1b[31m']:
            client = FakeGitHub(); client.issue['body'] = body
            self.assertEqual(self.observe(client)['submission_body'], body)

    def test_final_public_rechecks_reject_private_or_identity_changes(self):
        for route, field, changed, first_count in [(ROUTES[2],'private',True,1), (ROUTES[2],'id',999,1),
                                                 (ROUTES[0],'visibility','private',1), (ROUTES[0],'id',1,1)]:
            client = FakeGitHub()
            original = copy.deepcopy(client.meta if route==ROUTES[2] else client.controller)
            client.overrides[route] = lambda: original if client.calls.count(route)==first_count else dict(original,**{field:changed})
            with self.subTest(route=route, field=field), self.assertRaises(core.ProtocolError): self.observe(client)

    def test_guard_rejects_wrong_order_extra_routes_and_eighth_call_for_both_methods(self):
        tool = self.tool()
        for method in ('request','request_once'):
            client=FakeGitHub(); guard=tool.IntakeClient(11,REFERENCE,client,clock=lambda:NOW)
            with self.subTest(method=method):
                with self.assertRaises(core.ProtocolError): getattr(guard,method)('search/code?q=anything')
                self.assertEqual(client.calls, [])
                for route in ROUTES: getattr(guard,method)(route)
                with self.assertRaises(core.ProtocolError): getattr(guard,method)(ROUTES[0])
                self.assertEqual(client.calls, ROUTES)
            client=FakeGitHub(); guard=tool.IntakeClient(11,REFERENCE,client)
            with self.assertRaises(core.ProtocolError): getattr(guard,method)(ROUTES[1])
            self.assertEqual(client.calls, [])


    def test_issue_identity_and_merged_eligibility_matrix(self):
        mutations = [lambda c:c.controller.update(id=True), lambda c:c.controller.update(full_name='other/controller'),
                     lambda c:c.issue.update(pull_request={}), lambda c:c.issue.update(id=0),
                     lambda c:c.issue.update(number=True), lambda c:c.issue.update(html_url='https://evil.invalid'),
                     lambda c:c.issue['user'].update(id=302), lambda c:c.issue['user'].update(type='Bot'),
                     lambda c:c.pr['user'].update(type='Bot'), lambda c:c.pr.update(id=9007199254740992),
                     lambda c:c.meta['owner'].update(id=301), lambda c:c.pr['merged_by'].update(id=301),
                     lambda c:c.pr.update(state='open'), lambda c:c.pr.update(draft=True),
                     lambda c:c.pr.update(merged=False), lambda c:c.pr.update(merge_commit_sha=None),
                     lambda c:c.pr.update(merged_at='2099-01-01T00:00:00Z'),
                     lambda c:c.pr['base']['repo'].update(visibility='private'),
                     lambda c:c.meta.update(full_name='fictional-demo/renamed')]
        for mutate in mutations:
            client=FakeGitHub(); mutate(client)
            with self.subTest(mutate=mutations.index(mutate)), self.assertRaises(core.ProtocolError):
                self.observe(client)
            self.assertLessEqual(len(client.calls),7)

    def test_failed_invocations_do_not_retry_or_continue(self):
        for index in range(7):
            client=FakeGitHub(); route=ROUTES[index]
            original=client.request_once
            def fail(endpoint):
                if len(client.calls)==index:
                    client.calls.append(endpoint)
                    raise core.ProtocolError('api_error','PRIVATE rate limit')
                return original(endpoint)
            client.request_once=fail
            with self.subTest(index=index), self.assertRaises(core.ProtocolError): self.observe(client)
            self.assertEqual(client.calls,ROUTES[:index+1])

    def test_real_get_transport_fixed_argv_and_malformed_responses_fail_closed(self):
        import types
        tool=self.tool(); api=FakeGitHub(); calls=[]
        def run(argv,**kwargs):
            self.assertEqual(argv[:6],['gh','api','--hostname','github.com','--method','GET'])
            self.assertEqual(len(argv),7)
            self.assertFalse(kwargs['shell'])
            calls.append(argv[6])
            kwargs['stdout'].write(json.dumps(api.request_once(argv[6])).encode('utf-8'))
            return types.SimpleNamespace(returncode=0)
        with patch.object(core.subprocess,'run',run):
            tool.intake(11,REFERENCE,clock=lambda:NOW)
        self.assertEqual(calls,ROUTES)
        for raw in [b'{"id":1,"id":2}',b'{"id":NaN}',b'\xff',b'not-json']:
            calls.clear()
            def malformed(argv,**kwargs):
                calls.append(argv[6]); kwargs['stdout'].write(raw)
                return types.SimpleNamespace(returncode=0)
            with patch.object(core.subprocess,'run',malformed), self.assertRaises(core.ProtocolError):
                tool.intake(11,REFERENCE,clock=lambda:NOW)
            self.assertEqual(calls,ROUTES[:1])


class OutputTests(IntakeCase):
    def run_main(self, path, client=None, extra=()):
        tool=self.tool(); client=client or FakeGitHub()
        stdout,stderr=io.StringIO(),io.StringIO()
        with patch.object(core,'GitHub',return_value=client), patch('sys.stdout',stdout), patch('sys.stderr',stderr):
            code=tool.main(['--submission','11','--pull-request',REFERENCE,'--output',str(path),*extra])
        return code,stdout.getvalue(),stderr.getvalue(),client

    def test_private_new_file_and_fixed_stdout_even_for_control_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'output\x1b[31m\n.json'
            code,out,err,client=self.run_main(path)
            self.assertEqual((code,out,err),(0,'review-required\n',''))
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            self.assertEqual(json.loads(path.read_bytes())['status'],'review-required')
            self.assertEqual(client.calls,ROUTES)

    def test_existing_symlink_nonregular_and_unsafe_parent_rejected_before_get(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); existing=base/'keep'; existing.write_bytes(b'keep')
            link=base/'link'; link.symlink_to(existing)
            dangling=base/'dangling'; dangling.symlink_to(base/'absent')
            parent=base/'parent'; parent.symlink_to(base,target_is_directory=True)
            for path in [Path('/'),existing,link,dangling,base,parent/'new',base/'absent'/'new']:
                with self.subTest(path=path):
                    code,out,err,client=self.run_main(path)
                    self.assertEqual(code,1); self.assertEqual(out,''); self.assertNotIn(str(path),err)
                    self.assertEqual(client.calls,[])
                    self.assertEqual(existing.read_bytes(),b'keep')

    def test_concurrent_output_creation_is_not_overwritten_or_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'candidate.json'; client=FakeGitHub()
            original=copy.deepcopy(client.controller)
            def reply():
                if client.calls.count(ROUTES[0])==2: path.write_bytes(b'concurrent data')
                return original
            client.overrides[ROUTES[0]]=reply
            code,out,err,_=self.run_main(path,client)
            self.assertEqual((code,out),(1,'')); self.assertEqual(path.read_bytes(),b'concurrent data')

    def test_failed_write_cleans_only_this_invocations_file(self):
        tool=self.tool(); real_fdopen=os.fdopen
        class BrokenWrite:
            def __init__(self,fd,mode): self.file=real_fdopen(fd,mode)
            def __enter__(self): return self
            def __exit__(self,*args): self.file.close()
            def write(self,data):
                self.file.write(data[:5]); self.file.flush()
                raise OSError('PRIVATE arbitrary error must not leak')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'candidate.json'
            with patch.object(tool.os,'fdopen',BrokenWrite): code,out,err,_=self.run_main(path)
            self.assertEqual((code,out),(1,'')); self.assertFalse(path.exists())
            self.assertNotIn('PRIVATE',err)

    def test_cleanup_preserves_a_replacement_file_after_failed_write(self):
        tool=self.tool(); real_fdopen=os.fdopen
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'candidate.json'
            class ReplacedWrite:
                def __init__(self,fd,mode): self.file=real_fdopen(fd,mode)
                def __enter__(self): return self
                def __exit__(self,*args): self.file.close()
                def write(self,data):
                    self.file.write(data[:5]); self.file.flush()
                    path.unlink(); path.write_bytes(b'replacement data')
                    raise OSError('write failed after replacement')
            with patch.object(tool.os,'fdopen',ReplacedWrite): code,out,err,_=self.run_main(path)
            self.assertEqual((code,out),(1,'')); self.assertEqual(path.read_bytes(),b'replacement data')

    def test_invalid_cli_is_fixed_usage_error_without_network_or_terminal_echo(self):
        tool=self.tool()
        for args in [[],['--unknown\x1b[31m'],['--submission','0','--pull-request',REFERENCE,'--output','unused'],
                     ['--submission','11','--pull-request','bad\nreference','--output','unused']]:
            with patch.object(core,'GitHub') as github, patch('sys.stderr',io.StringIO()) as err:
                with self.assertRaises(SystemExit) as raised: tool.main(args)
                self.assertEqual(raised.exception.code,2)
                self.assertEqual(err.getvalue(),'Submission intake usage error.\n')
                github.assert_not_called()

    def test_failed_observation_and_oversize_leave_no_output(self):
        tool=self.tool()
        with tempfile.TemporaryDirectory() as directory:
            for body in [None,123,'\ud800','x'*(256*1024+1)]:
                client=FakeGitHub(); client.issue['body']=body; path=Path(directory)/'candidate.json'
                with self.subTest(bodytype=type(body).__name__):
                    code,out,err,_=self.run_main(path,client)
                    self.assertEqual((code,out),(1,'')); self.assertFalse(path.exists())
                    self.assertNotIn('Traceback',err)
            with patch.object(tool,'OUTPUT_LIMIT',10):
                code,out,err,_=self.run_main(path)
                self.assertEqual((code,out),(1,'')); self.assertFalse(path.exists())


if __name__ == '__main__': unittest.main()
