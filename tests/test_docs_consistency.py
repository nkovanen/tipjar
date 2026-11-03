"""Cheap documentation checks: the documented surface matches the installed parser and links resolve."""
import argparse
import pathlib
import re
import unittest

from tests.test_cli_help import built_parser

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = [ROOT / 'README.md', ROOT / 'CHANGELOG.md', ROOT / 'CONTRIBUTING.md', ROOT / 'SECURITY.md',
        *sorted((ROOT / 'docs').rglob('*.md'))]


def commands():
    names = []
    for action in built_parser()._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                nested = [a for a in sub._actions if isinstance(a, argparse._SubParsersAction)]
                names += [name + ' ' + child for a in nested for child in a.choices] if nested else [name]
    return names


class DocsConsistencyTests(unittest.TestCase):
    def test_readme_and_command_reference_name_every_command(self):
        readme = (ROOT / 'README.md').read_text('utf-8')
        reference = (ROOT / 'docs' / 'cli.md').read_text('utf-8')
        for name in commands():
            with self.subTest(command=name):
                self.assertIn('`' + name, readme)
                self.assertIn('agent-contrib ' + name, reference)

    def test_no_document_installs_a_nonexistent_release_tag(self):
        for path in DOCS:
            with self.subTest(path=path.name):
                self.assertNotRegex(path.read_text('utf-8'), r'@v0\.3\.0')
        self.assertIn('agent-contrib/releases/tag/v0.2.0', (ROOT / 'README.md').read_text('utf-8'))

    def test_candidate_install_and_compatibility_are_explicit(self):
        for name in ('README.md', 'docs/installation.md'):
            with self.subTest(doc=name):
                text = (ROOT / name).read_text('utf-8')
                self.assertIn('tipjar.git@main', text)
                self.assertIn('agent-contrib --version', text)
                self.assertIn('tipjar --version', text)
                self.assertIn('unreleased candidate', text)
        readme = (ROOT / 'README.md').read_text('utf-8')
        self.assertLess(readme.index('pipx install'), readme.index('agent-contrib skill --output'))
        self.assertIn('not live yet', readme)
        self.assertIn('https://nkovanen.github.io/tipjar/', readme)
        self.assertIn('distribution remains `agent-contrib`', readme)
        self.assertIn('Python module remains', readme)

    def test_pinned_candidate_selects_the_agent_environment(self):
        text = (ROOT / 'docs/installation.md').read_text('utf-8')
        entry = 'export PATH="$HOME/.local/share/agent-contrib-candidate/bin:$PATH"'
        self.assertIn(entry, text)
        self.assertIn('agent-contrib --version', text[text.index(entry):])
        self.assertIn('tipjar.git@PUSHED_FULL_COMMIT_SHA', text)
        self.assertNotIn('/tmp/agent-contrib-candidate', text)

    def test_ranking_and_compatibility_claims_are_qualified(self):
        readme = (ROOT / 'README.md').read_text('utf-8')
        changelog = (ROOT / 'CHANGELOG.md').read_text('utf-8')
        for text in (readme, changelog):
            self.assertNotRegex(text, r'never change a gate, approval or\s+ordering')
            self.assertNotRegex(text, r'change no gate, approval or ordering')
            self.assertRegex(text, r'`--signals`\s+re-ranks')
        for name in ('README.md', 'docs/architecture.md'):
            self.assertIn('CHANGELOG.md#compatibility-notes', (ROOT / name).read_text('utf-8'))
        self.assertNotIn('Default `discover` output and read order are frozen by goldens and unchanged', changelog)

    def test_relative_links_resolve(self):
        for path in DOCS:
            for target in re.findall(r'\]\(([^)#\s]+)(?:#[^)]*)?\)', path.read_text('utf-8')):
                if '://' in target or target.startswith('mailto:'):
                    continue
                with self.subTest(path=path.name, target=target):
                    self.assertTrue((path.parent / target).exists())

    def test_markdown_anchors_resolve(self):
        # The regrouped docs/cli.md relies on heading anchors; a renamed heading must not leave a dead link.
        def anchors(path):
            seen, found, fenced = {}, set(), False
            for text_line in path.read_text('utf-8').split('\n'):
                if text_line.startswith('```'):
                    fenced = not fenced
                heading = None if fenced else re.match(r'#{1,6} (.+)', text_line)
                if heading:
                    slug = re.sub(r'[^\w\- ]', '', heading.group(1).strip().lower()).replace(' ', '-')
                    found.add(slug if slug not in seen else f'{slug}-{seen[slug]}')
                    seen[slug] = seen.get(slug, 0) + 1
            return found
        for path in DOCS:
            for target, fragment in re.findall(r'\]\(([^)#\s]*)#([^)\s]+)\)', path.read_text('utf-8')):
                if '://' in target:
                    continue
                destination = path.parent / target if target else path
                if destination.suffix != '.md':
                    continue
                with self.subTest(path=path.name, link=target + '#' + fragment):
                    self.assertIn(fragment, anchors(destination))
        self.assertIn('command-index', anchors(ROOT / 'docs' / 'cli.md'))

    def test_product_map_lists_shipped_output_schemas_as_implemented(self):
        # Dogfood 3 F45: the map still listed the shipped output schemas as missing.
        from agent_contribute import outputs
        text = (ROOT / 'docs' / 'product-map.md').read_text('utf-8')
        implemented = text.split('### Implemented')[1].split('### Partly implemented')[0]
        self.assertTrue(outputs.SCHEMAS)
        self.assertIn('G1 ', implemented)
        self.assertNotIn('Missing: output JSON Schemas', text)
        self.assertNotIn('G1 output schemas', text)

    def test_product_status_preserves_history_and_current_boundaries(self):
        text = (ROOT / 'docs/product-map.md').read_text('utf-8')
        self.assertIn('agent-contrib/blob/ae206ce0ef079cd369dda0803a4374ca177516bd/docs/product-map.md', text)
        for phrase in ('`discover --limit`', 'machine-readable opt-out', 'no native human/host mandate issuer',
                       'unreleased candidate', 'read-only', 'not live yet'):
            self.assertIn(phrase, text)

    def test_current_status_includes_integrated_external_tips_and_cards(self):
        for name in ('README.md', 'docs/product-map.md'):
            with self.subTest(doc=name):
                text = (ROOT / name).read_text('utf-8')
                self.assertIn('external-tips.md', text)
                self.assertIn('0.3', text)
                self.assertRegex(text, r'`(?:tipjar )?card\b')
        installation = (ROOT / 'docs/installation.md').read_text('utf-8')
        self.assertIn('external-tip task schema **0.3**', installation)
        self.assertIn('Active output schemas are **3**', installation)
        self.assertNotIn('upstream-route gap still applies', (ROOT / 'docs/getting-started.md').read_text('utf-8'))

    def test_product_map_does_not_list_shipped_output_schemas_as_missing(self):
        # F45: G1 kept saying "Missing: output JSON Schemas" after schemas/output/1 and `schema` shipped.
        text = (ROOT / 'docs' / 'product-map.md').read_text('utf-8')
        self.assertTrue((ROOT / 'agent_contribute' / 'schemas' / 'output' / '1' / 'verify.schema.json').exists())
        missing = [line for line in text.splitlines() if 'Missing:' in line]
        self.assertFalse([line for line in missing if re.search(r'(?i)output (json )?schemas?|output-schema version', line)])


    def test_label_approval_docs_state_what_is_and_is_not_verified(self):
        # #9: policy 0.1 checks label presence only; no document may imply a verified or maintainer-applied label.
        flat = lambda path: ' '.join((ROOT / path).read_text('utf-8').split())
        texts = {path: flat(path) for path in ('README.md', 'SECURITY.md', 'docs/maintainers.md',
                                               'agent_contribute/instructions.md')}
        for path, text in texts.items():
            with self.subTest(path=path):
                self.assertIn('does not verify who applied it', text)
                self.assertNotIn('maintainer-approved', text)
        maintainers = texts['docs/maintainers.md']
        self.assertIn('suitable only if every principal who can label issues is trusted to approve agent work',
                      maintainers)
        self.assertIn('A dedicated label name restricts nothing', maintainers)
        self.assertIn('do not opt in under this policy', maintainers)
        # R9-07/R9-08: events name an actor; what is unverifiable is its authority and label binding.
        for path in ('README.md', 'SECURITY.md', 'agent_contribute/instructions.md'):
            with self.subTest(path=path):
                self.assertNotIn('cannot tell the CLI who', texts[path])
                self.assertRegex(texts[path], r'Public (issue )?events name an? (event |labeling )?actor')
        self.assertIn('configured label is currently present on the issue under the default-branch policy',
                      maintainers)
        self.assertIn('triage, write and higher roles, custom roles or grants that allow labelling', maintainers)
        self.assertIn('use the schema 0.2 mandate route', maintainers)
        design = flat('docs/design/2026-11-02-actor-verified-approval.md')
        self.assertIn('R9-05', design)
        self.assertIn('R9-06', design)
        self.assertIn('documented limitation; labeling-actor authority cannot be verified from public REST data',
                      flat('docs/product-map.md'))

if __name__ == '__main__':
    unittest.main()
