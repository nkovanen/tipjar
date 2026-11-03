import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from agent_contribute import cli, core
from tests.test_external_tip_prepare import ExternalGitHub


class ExternalCliTests(unittest.TestCase):
    def call(self,args):
        out=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(io.StringIO()):code=cli.main(args)
        return code,json.loads(out.getvalue())

    def test_prepare_explicit_route_and_stage_required(self):
        with tempfile.TemporaryDirectory() as d,patch.object(core,'GitHub',return_value=ExternalGitHub()):
            path=str(Path(d)/'task.json')
            code,result=self.call(['prepare','acme/photos#12','--schema-version','0.3','--fork','human/photos','--head-ref','tip-12','--output',path])
            self.assertEqual(code,0,result)
            self.assertEqual(result['contract']['schema_version'],'0.3')
            code,result=self.call(['verify',path])
            self.assertEqual(code,2,result)
            code,result=self.call(['verify',path,'--stage','implementation'])
            self.assertEqual(code,1,result)
            self.assertEqual(result['report'],'external-tip-report/1')

    def test_draft_payload_required(self):
        from agent_contribute import external_tip
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'task.json';path.write_text(json.dumps(external_tip.prepare('acme/photos#12','human/photos','tip-12',ExternalGitHub())))
            for args in (['verify',str(path),'--stage','draft'],):
                code,result=self.call(args);self.assertEqual(code,2,result)
