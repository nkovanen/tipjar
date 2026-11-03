"""Public site entrypoints and dependency-free board regressions."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PublicSiteTests(unittest.TestCase):
    def test_landing_connects_public_board_and_preserved_local_directory(self):
        landing = (ROOT / 'web/index.html').read_text()
        self.assertTrue((ROOT / 'web/directory.html').exists(), 'preserve the local directory at directory.html')
        directory = (ROOT / 'web/directory.html').read_text()
        self.assertIn('href="leaderboard.html"', landing)
        self.assertIn('href="directory.html', landing)
        self.assertNotIn('app.js', landing)
        self.assertIn("connect-src 'none'", directory)
        self.assertIn('id="snapshot"', directory)
        self.assertIn('id="manifest-form"', directory)
        self.assertIn('app.js', directory)

    @unittest.skipUnless(shutil.which('node'), 'Node required for board tests')
    def test_board_model(self):
        result = subprocess.run(['node', 'tests/web/leaderboard.test.cjs'], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
