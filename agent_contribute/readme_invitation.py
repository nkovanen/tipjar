"""The fixed readme-welcome/1 source prefix; no Markdown or network interpretation."""
from urllib.parse import quote
from . import core

IMAGE = 'https://nkovanen.github.io/tipjar/brand/agent-work-welcome.svg'
MARKER = '<!-- tipjar:welcome:v1 -->'
MAX_BYTES = 131072


def snippet(repository):
    repository = core.parse_repository(repository).lower()
    return (MARKER + '\n[![Agent-work tips welcome](' + IMAGE +
            ')](https://nkovanen.github.io/tipjar/?repo=' + quote(repository, safe='') + ')\n\n')


def parse_readme_invitation(data: bytes, repository: str) -> dict:
    unknown = dict(state='unknown', badge=None, errors=['Unresolved README invitation; use one exact scoped prefix at byte zero'])
    if not isinstance(data, bytes) or len(data) > MAX_BYTES:
        return unknown
    try:
        text = data.decode('utf-8')
    except UnicodeError:
        return unknown
    if 'tipjar:welcome' not in text:
        return dict(state='undeclared', badge=None, errors=[])
    normalized = text.replace('\r\n', '\n')
    if ('\r' in normalized or '\r\n' in text and '\n' in text.replace('\r\n', '') or
            text.count('tipjar:welcome') != 1 or not normalized.startswith(snippet(repository))):
        return unknown
    return dict(state='welcome', badge=dict(protocol='readme-welcome/1',
                                           repository=core.parse_repository(repository).lower()), errors=[])


def decorative_span(text, repository):
    """Original character span of the exact image URL, before any URL deduplication."""
    if parse_readme_invitation(text.encode('utf-8'), repository)['state'] != 'welcome':
        return None
    start = text.index(IMAGE)
    return start, start + len(IMAGE)
