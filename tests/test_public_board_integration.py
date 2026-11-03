"""Generated fictional observations cross the actual artifact and browser contract."""
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from tests.test_tipjar_board import COLLECT_NOW, InvitationGitHub, README_WELCOME, registry
from tools import tipjar_board as board, tipjar_board_deploy as deploy

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node required for cross-language integration')
class PublicBoardIntegrationTests(unittest.TestCase):
    def test_collector_artifact_parser_and_projection(self):
        cases = [
            ('empty', {}, False, False, 0, None),
            ('manifest', {'.tipjar.json': b'{"schema_version":"0.1","status":"welcome"}'}, True, True, 1, '.tipjar.json'),
            ('readme-welcome', {'README.md': README_WELCOME}, True, True, 1, 'README.md'),
            ('readme-plain', {'README.md': b'# FICTIONAL DEMO\n'}, True, True, 0, 'README.md'),
            ('absent', {}, True, True, 0, None),
            ('readme-no-tips', {'README.md': README_WELCOME}, False, True, 1, 'README.md'),
        ]
        for name, files, populated, candidate_repo, welcomes, source_path in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                reg = registry()
                if not populated:
                    reg['tips'] = []
                if candidate_repo:
                    reg['repositories'] = [{'repository_id': 101, 'repository': 'fictional-demo/welcoming-jar'}]
                result = board.collect(reg, InvitationGitHub(files), now=COLLECT_NOW,
                                       source_commit='a' * 40, controller_id=1444643470)
                payload = board.encode(result)
                artifact = Path(tmp) / 'artifact.tar'
                with tarfile.open(artifact, 'w') as archive:
                    info = tarfile.TarInfo('./board.json')
                    info.size = len(payload)
                    archive.addfile(info, io.BytesIO(payload))
                    for path in sorted((ROOT / 'web').rglob('*')):
                        if path.is_file():
                            archive.add(path, arcname='./' + str(path.relative_to(ROOT / 'web')))
                candidate = deploy.read_artifact(artifact)
                self.assertEqual(candidate, payload)
                served = (ROOT / 'tests/fixtures/tipjar-board/empty.json').read_bytes()
                checked = deploy.check_publication(candidate, served, current_source='a' * 40,
                                                    now=COLLECT_NOW)
                # Use the production model shipped inside this very Pages artifact.
                model_path = Path(tmp) / 'leaderboard-model.cjs'
                with tarfile.open(artifact) as archive:
                    model_path.write_bytes(archive.extractfile('./leaderboard-model.js').read())
                    (Path(tmp) / 'model.js').write_bytes(archive.extractfile('./model.js').read())
                expected = board.summarize(checked['tips'], now=COLLECT_NOW, period='all')
                # Execute the production JS parser, not a second Python model.
                script = """
const fs = require('node:fs'), m = require(process.argv[1]);
const now = new Date('2026-11-04T12:00:00Z');
const b = m.parseBoard(fs.readFileSync(0, 'utf8'), now);
process.stdout.write(JSON.stringify({ranks:m.rankBoard(b, 'all', now),
    welcome:m.welcoming(b, now).length, tips:b.tips.length, format:b.format,
    sources:b.directory.observations.map(m.sourceURL)}));
"""
                parsed = subprocess.run(['node', '-e', script, str(model_path)], input=candidate.decode(),
                                        cwd=ROOT, capture_output=True, text=True, timeout=30)
                self.assertEqual(parsed.returncode, 0, parsed.stderr)
                projection = json.loads(parsed.stdout)
                self.assertEqual(projection['tips'], int(populated))
                self.assertEqual(projection['welcome'], welcomes)
                self.assertEqual(projection['format'], 'tipjar-board/2')
                expected_source = ('https://github.com/fictional-demo/welcoming-jar/blob/'
                                   + 'b' * 40 + '/' + source_path) if source_path else None
                self.assertEqual(projection['sources'], [expected_source] if candidate_repo else [])
                # Presentation adds labels and milestones; compare shared scoring facts.
                for kind, identity, score in [('people', 'author_id', 'points'),
                                               ('projects', 'repository_id', 'tips')]:
                    fields = (identity, score, 'rank')
                    self.assertEqual(
                        [tuple(row[k] for k in fields) for row in projection['ranks'][kind]],
                        [tuple(row[k] for k in fields) for row in expected[kind]])


class WelcomeSuggestionFormTests(unittest.TestCase):
    def test_public_suggestion_collects_no_ownership_or_contact_claim(self):
        path = ROOT / '.github/ISSUE_TEMPLATE/suggest-jar.yml'
        self.assertTrue(path.is_file(), 'suggestion link needs its own issue form')
        form = path.read_text()
        self.assertIn('Anyone may suggest a public repository. You do not need to own or maintain it.', form)
        self.assertIn('It does not list a project, opt anyone into scoring, verify ownership, or authorize work or publication.', form)
        self.assertIn('GitHub publishes your account and issue text.', form)
        self.assertIn('Public issues and history may persist.', form)
        self.assertIn('label: Public repository (owner/repo)', form)
        self.assertIn('label: Public invitation location', form)
        self.assertEqual(form.count('- type: input'), 2)
        self.assertEqual(form.count('required: true'), 2, 'repository and acknowledgement only')
        self.assertIn('not a claim of project ownership or permission to contribute.', form)
        self.assertNotRegex(form, r'(?m)^(labels|assignees):')
