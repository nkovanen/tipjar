"""Generated fictional observations cross the actual artifact and browser contract."""
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from tests.test_tipjar_board import COLLECT_NOW, FakeGitHub, registry
from tools import tipjar_board as board, tipjar_board_deploy as deploy

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node required for cross-language integration')
class PublicBoardIntegrationTests(unittest.TestCase):
    def test_collector_artifact_parser_and_projection(self):
        for populated in (False, True):
            with self.subTest(populated=populated), tempfile.TemporaryDirectory() as tmp:
                reg = registry()
                if not populated:
                    reg['tips'] = []
                result = board.collect(reg, FakeGitHub(), now=COLLECT_NOW,
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
                checked = deploy.check_publication(candidate, None, current_source='a' * 40,
                                                    now=COLLECT_NOW, bootstrap=True)
                expected = board.summarize(checked['tips'], now=COLLECT_NOW, period='all')
                # Execute the production JS parser, not a second Python model.
                script = """
const fs = require('node:fs'), m = require('./web/leaderboard-model.js');
const now = new Date('2026-11-04T12:00:00Z');
const b = m.parseBoard(fs.readFileSync(0, 'utf8'), now);
process.stdout.write(JSON.stringify({ranks:m.rankBoard(b, 'all', now),
    welcome:m.welcoming(b, now).length, tips:b.tips.length}));
"""
                parsed = subprocess.run(['node', '-e', script], input=candidate.decode(),
                                        cwd=ROOT, capture_output=True, text=True, timeout=30)
                self.assertEqual(parsed.returncode, 0, parsed.stderr)
                projection = json.loads(parsed.stdout)
                self.assertEqual(projection['tips'], int(populated))
                self.assertEqual(projection['welcome'], int(populated))
                # Presentation adds labels and milestones; compare shared scoring facts.
                for kind, identity, score in [('people', 'author_id', 'points'),
                                               ('projects', 'repository_id', 'tips')]:
                    fields = (identity, score, 'rank')
                    self.assertEqual(
                        [tuple(row[k] for k in fields) for row in projection['ranks'][kind]],
                        [tuple(row[k] for k in fields) for row in expected[kind]])
