#!/usr/bin/env python3
"""Source-only curated public board; never an executor or installed CLI command.

Closed field contracts live beside this tool in schemas/*.json. JSON Schema
checks shape; this module also checks byte caps, safe integers, exact identities,
read-start minima, and 48-hour expiry. Registry declarations are curator input,
not live facts or execution/publication authority. All samples are fictional.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys

# Support direct source-checkout invocation, without installing the tool.
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_contribute import core, find, receipts, tipjar

UTC = dt.timezone.utc
SAFE = 9007199254740991
CONTROLLER = 'nkovanen/tipjar'
REGISTRY_LIMIT = 1024 * 1024
BOARD_LIMIT = 4 * 1024 * 1024
DIRECTORY_LIMIT = 1024 * 1024
COUNT_KEYS = ('unknown_tips', 'unknown_repositories', 'excluded_tips',
              'excluded_repositories', 'omitted_tips', 'omitted_repositories',
              'omitted_directory_observations')


def require(condition):
    if not condition:
        raise core.ProtocolError('invalid_board', 'Invalid bounded board data or inconsistent identities/times')


def utcnow():
    return dt.datetime.now(UTC)


def timestamp(value):
    require(isinstance(value, str) and receipts.TIME.fullmatch(value))
    try:
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise core.ProtocolError('invalid_board', 'Invalid UTC board timestamp') from None


def iso(value):
    require(isinstance(value, dt.datetime) and value.utcoffset() == dt.timedelta(0))
    return value.isoformat().replace('+00:00', 'Z')


def encode(value):
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise core.ProtocolError('invalid_board', 'Invalid board JSON') from None


def _bounded(data, limit):
    if not isinstance(data, bytes):
        data = encode(data)
    require(len(data) <= limit)
    try:
        return core.strict_json(data.decode('utf-8'))
    except UnicodeError:
        raise core.ProtocolError('invalid_board', 'Invalid UTF-8 board JSON') from None


def _shape(value, name):
    schema = json.loads((Path(__file__).parent / 'schemas' / (name + '.schema.json')).read_text('utf-8'))
    require(not core.schema_errors(value, schema))
    # The library's deliberately small schema validator does not implement maximum.
    def safe(item):
        if type(item) is int:
            require(0 <= item <= SAFE)
        elif isinstance(item, dict):
            for v in item.values(): safe(v)
        elif isinstance(item, list):
            for v in item: safe(v)
    safe(value)


def _bindings(tips, repositories):
    ids, names, prs, numbers = {}, {}, {}, {}
    for item in [*repositories, *tips]:
        rid, name = item['repository_id'], item['repository']
        require(ids.setdefault(rid, name) == name and names.setdefault(name.casefold(), rid) == rid)
    for item in tips:
        rid, pid, number, aid = (item[k] for k in ('repository_id','pull_request_id','number','author_id'))
        require(prs.setdefault(pid, (rid, number, aid)) == (rid, number, aid))
        require(numbers.setdefault((rid, number), pid) == pid)


def validate_registry(data: bytes) -> dict:
    value = _bounded(data, REGISTRY_LIMIT)
    _shape(value, 'tipjar-board-registry')
    require(len({t['author_id'] for t in value['tips']}) <= 100)
    _bindings(value['tips'], value['repositories'])
    issues, issue_numbers, controllers = {}, {}, set()
    for t in value['tips']:
        s = t['submission']; controllers.add(s['controller_repository_id'])
        pin = (s['number'], t['author_id'], s['body_sha256'])
        require(issues.setdefault(s['issue_id'], pin) == pin)
        require(issue_numbers.setdefault(s['number'], s['issue_id']) == s['issue_id'])
    require(len(controllers) <= 1)
    return value


def validate_board(data, *, now=None) -> dict:
    """Strict parse and semantic validation; expired served state is still readable.

    Expiry is enforced separately by require_fresh, so replacing an overdue
    served snapshot remains possible. Neither function authenticates supplied data.
    """
    value = _bounded(data, BOARD_LIMIT)
    _shape(value, 'tipjar-board')
    now = now or utcnow()
    generated = timestamp(value['generated_at'])
    require(generated <= now)
    repositories = value['repositories']
    require(len({r['repository_id'] for r in repositories}) == len(repositories))
    repo_map = {r['repository_id']: r for r in repositories}
    augmented = []
    for t in value['tips']:
        require(t['repository_id'] in repo_map)
        augmented.append(dict(t, repository=repo_map[t['repository_id']]['repository']))
    _bindings(augmented, repositories)
    require(len({(t['repository_id'], t['pull_request_id']) for t in augmented}) == len(augmented))
    all_checks = []
    author_names, author_ids = {}, {}
    for t in augmented:
        require(t['url'] == f"https://github.com/{t['repository']}/pull/{t['number']}")
        aid, login = t['author_id'], t['author_login']
        require(author_names.setdefault(aid, login) == login and author_ids.setdefault(login.casefold(), aid) == aid)
        checks = [timestamp(c) for c in t['checks'].values()]
        require(timestamp(t['verified_at']) == min(checks))
        require(timestamp(t['merged_at']) <= timestamp(t['checks']['pull_request']))
        all_checks.extend(checks)
    for r in repositories:
        all_checks.append(timestamp(r['verified_at']))
        language = r['primary_language']
        require(language is None or not any(ord(c) < 32 or ord(c) == 127 for c in language))
    directory = value['directory']; seen = set()
    require(len(encode(directory)) <= DIRECTORY_LIMIT)
    for obs in directory['observations']:
        rid = obs['repository_id']
        require(rid not in seen and rid in repo_map and repo_map[rid]['repository'] == obs['repository'])
        seen.add(rid)
        checks = [timestamp(c) for c in obs['checks']]
        require(timestamp(obs['verified_at']) == min(checks))
        all_checks.extend(checks)
        jar, source, state = obs['jar'], obs['source'], obs['disposition']
        if state in ('unknown', 'excluded'):
            require(jar is None and source is None)
        else:
            require(jar is not None and tipjar._complete_report(jar))
            require(jar['repository'] == obs['repository'] and jar['state'] == state)
            require(timestamp(_canonical_time(jar['fetched_at'])) <= generated)
            if state == 'undeclared':
                require(source is None)
            elif source is not None:
                require(source == {'kind':'manifest', 'path':'.tipjar.json', 'commit':jar['commit'], 'sha256':jar['sha256']})
    require(all(c <= generated for c in all_checks))
    require(timestamp(value['expires_at']) == (min(all_checks) if all_checks else generated) + dt.timedelta(hours=48))
    cov = value['coverage']
    partial = (any(cov[k] for k in COUNT_KEYS if k.startswith(('unknown_', 'omitted_'))) or
               not directory['complete'] or directory['search_failed'] or directory['server_incomplete'] or directory['truncated'])
    require(cov['partial'] == bool(partial))
    require(not directory['complete'] or not (directory['search_failed'] or directory['server_incomplete'] or
                                             directory['truncated'] or any(o['disposition']=='unknown' for o in directory['observations'])))
    return value


def _canonical_time(value):
    # Canonical jar reports use ISO offsets; the board's own timestamps use Z.
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(parsed.utcoffset() == dt.timedelta(0))
        return iso(parsed)
    except (ValueError, TypeError, AttributeError):
        raise core.ProtocolError('invalid_board', 'Invalid reader timestamp') from None


def require_fresh(value, *, now=None):
    now = now or utcnow()
    validate_board(value, now=now)
    require(now < timestamp(value['expires_at']))
    return value


def summarize(tips: list[dict], *, now: dt.datetime, period: str) -> dict:
    """Derive scores only from selected tips; duplicate consistent PRs count once."""
    require(period in ('month', '30d', 'all'))
    start = now.replace(day=1,hour=0,minute=0,second=0,microsecond=0) if period=='month' else now-dt.timedelta(days=30) if period=='30d' else dt.datetime.min.replace(tzinfo=UTC)
    unique, bindings, numbers = {}, {}, {}
    for t in tips:
        rid,pid,number,aid = (t[k] for k in ('repository_id','pull_request_id','number','author_id'))
        require(bindings.setdefault(pid,(rid,number,aid)) == (rid,number,aid))
        require(numbers.setdefault((rid,number),pid)==pid)
        unique.setdefault((rid,pid),t)
    selected = [t for t in unique.values() if start <= timestamp(t['merged_at']) <= now]
    people, projects = {}, {}
    for t in selected:
        p = people.setdefault(t['author_id'], {'author_id':t['author_id'],'points':0,'_repos':set()})
        p['points']+=1; p['_repos'].add(t['repository_id'])
        r = projects.setdefault(t['repository_id'], {'repository_id':t['repository_id'],'tips':0,'_authors':set(),'latest_merge':t['merged_at']})
        r['tips']+=1; r['_authors'].add(t['author_id'])
        if timestamp(t['merged_at']) > timestamp(r['latest_merge']): r['latest_merge']=t['merged_at']
    for p in people.values(): p['projects']=len(p.pop('_repos'))
    for r in projects.values(): r['contributors']=len(r.pop('_authors'))
    def ranked(items, score, identity):
        rows = sorted(items.values(),key=lambda x:(-x[score],x[identity]))
        previous = None; rank=0
        for index,row in enumerate(rows,1):
            if row[score] != previous: rank=index
            previous=row[score];row['rank']=rank
        return rows
    return {'people':ranked(people,'points','author_id'),'projects':ranked(projects,'tips','repository_id')}
