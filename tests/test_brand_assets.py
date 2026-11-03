"""Keep embeddable brand assets inert and their local preview self-contained."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


BRAND = Path(__file__).resolve().parents[1] / 'web' / 'brand'


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.images.append(dict(attrs))


class BrandAssetTests(unittest.TestCase):
    def test_svg_assets_are_accessible_and_inert(self):
        assets = list(BRAND.glob('*.svg'))
        self.assertTrue(assets)
        allowed = {'svg', 'title', 'desc', 'g', 'path', 'rect', 'text'}
        for path in assets:
            with self.subTest(asset=path.name):
                raw = path.read_text()
                self.assertNotRegex(raw, r'<!|<\?')
                root = ET.fromstring(raw)
                self.assertEqual(root.tag, '{http://www.w3.org/2000/svg}svg')
                self.assertEqual(root.get('role'), 'img')
                self.assertEqual(len(root.get('viewBox').split()), 4)
                ids = {node.get('id'): node for node in root.iter() if node.get('id')}
                for label in root.get('aria-labelledby').split():
                    self.assertIn(label, ids)
                    self.assertTrue(''.join(ids[label].itertext()).strip())
                for node in root.iter():
                    self.assertIn(node.tag.split('}')[-1], allowed)
                    for name, value in node.attrib.items():
                        local = name.split('}')[-1].lower()
                        self.assertFalse(local.startswith('on'), name)
                        self.assertNotIn(local, {'href', 'src', 'style'})
                        self.assertNotRegex(value.lower(), r'url\s*\(|https?:|data:|javascript:')

    def test_preview_images_resolve_locally_with_alt_text(self):
        parser = Images()
        parser.feed((BRAND / 'preview.html').read_text())
        self.assertTrue(parser.images)
        self.assertEqual({image['src'] for image in parser.images},
                         {path.name for path in BRAND.glob('*.svg')})
        for image in parser.images:
            with self.subTest(src=image['src']):
                self.assertTrue(image.get('alt', '').strip())
                self.assertEqual(Path(image['src']).name, image['src'])
                self.assertTrue((BRAND / image['src']).is_file())

    def test_invitation_snippets_require_a_repository_destination(self):
        docs = (BRAND / 'README.md').read_text()
        snippets = re.findall(r'```markdown\n(.*?)```', docs, re.S)
        self.assertEqual(len(snippets), 2)
        invitation_links = re.findall(r'\)\]\(([^)]+)\)', snippets[1])
        self.assertEqual(invitation_links,
                         ['REPOSITORY_INVITATION_URL', 'REPOSITORY_INVITATION_URL'])
        for name in ('wordmark', 'agent-work-welcome', 'invitation-card'):
            self.assertIn(f'REVIEWED_COMMIT_SHA/web/brand/{name}.svg', docs)
