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
        pin = (s['number'], t['author_id'], s['body_sha256'], t['repository_id'], t['pull_request_id'])
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


class BudgetClient:
    """One uncached invocation per method, including failures; no application retry.

    The underlying gh transport has its own fixed GET argv, 8 MiB response and
    30-second timeout. This cap counts gh invocations, not redirects/raw HTTP.
    Only the latest repository/PR payload is retained for same-response checks.
    """
    def __init__(self, client=None, *, limit=5000, clock=None):
        require(type(limit) is int and 0 <= limit <= 5000)
        self.client = client if client is not None else core.GitHub(use_cache=False)
        if hasattr(self.client, 'use_cache'):
            self.client.use_cache = False
        self.limit = limit
        self.clock = clock or utcnow
        self.events = []
        self.last_repository = None
        self.last_pr = None
        self.private_ids = set()
        self.private_names = set()

    def request(self, endpoint, attempts=1):
        return self.request_once(endpoint)

    def request_once(self, endpoint):
        name = r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}'
        route = (r'repos/' + name + r'(?:/(?:issues|pulls)/[1-9][0-9]{0,15}|/commits/(?:[A-Za-z0-9_.-]|%[0-9A-Fa-f]{2}){1,3072}'
                 r'|/git/trees/[0-9a-f]{40}\?recursive=1|/contents/\.tipjar\.json\?ref=[0-9a-f]{40})?')
        search = 'search/code?q=filename%3A.tipjar.json+path%3A%2F&per_page=10&page=1'
        require(isinstance(endpoint,str) and (endpoint == search or re.fullmatch(route, endpoint)))
        if len(self.events) >= self.limit:
            raise core.ProtocolError('board_budget', 'Board GET invocation budget exhausted')
        self.events.append((endpoint, iso(self.clock())))
        value = self.client.request_once(endpoint)
        def remember(meta, route_name=None):
            if not isinstance(meta, dict) or not (meta.get('private') is True or meta.get('visibility') in ('private', 'internal')):
                return
            if type(meta.get('id')) is int and 0 < meta['id'] <= SAFE:
                self.private_ids.add(meta['id'])
            if isinstance(meta.get('full_name'), str):
                self.private_names.add(meta['full_name'].casefold())
            if route_name is not None:
                self.private_names.add(route_name.casefold())
        route_name = '/'.join(endpoint.split('/')[1:3]) if endpoint.startswith('repos/') else None
        remember(value, route_name)
        if isinstance(value, dict):
            base = value.get('base')
            if isinstance(base, dict): remember(base.get('repo'), route_name)
            if endpoint == search and isinstance(value.get('items'), list):
                for hit in value['items'][:10]:
                    if isinstance(hit, dict): remember(hit.get('repository'))
        if re.fullmatch(r'repos/' + name, endpoint):
            self.last_repository = value
        if re.fullmatch(r'repos/' + name + r'/pulls/[1-9][0-9]{0,15}', endpoint):
            self.last_pr = value
        return value


def _public_meta(meta, rid, name):
    require(isinstance(meta,dict))
    require(meta.get('private') is False and meta.get('visibility') == 'public')
    require(meta.get('id') == rid and type(meta.get('id')) is int and meta.get('full_name') == name)
    identity = find._identity(meta)
    require(identity[0] <= SAFE and identity[2] <= SAFE)
    language = meta.get('language')
    require(language is None or isinstance(language,str) and 1<=len(language)<=100 and
            not any(ord(c)<32 or ord(c)==127 for c in language))
    return identity


def _excluded(tip, exclusions):
    return any((x['kind']=='repository' and x['repository_id']==tip['repository_id']) or
               (x['kind']=='author' and x['author_id']==tip.get('author_id')) or
               (x['kind']=='tip' and (x['repository_id'],x['pull_request_id']) ==
                (tip['repository_id'],tip.get('pull_request_id'))) for x in exclusions)


def _consent(t, controller, controller_id, client):
    s = t['submission']
    _public_meta(controller, controller_id, CONTROLLER)
    require(s['controller_repository_id'] == controller_id)
    value = client.request_once(f"repos/{CONTROLLER}/issues/{s['number']}")
    require(isinstance(value,dict) and 'pull_request' not in value)
    require(type(value.get('id')) is int and value['id'] == s['issue_id'] and
            type(value.get('number')) is int and value['number'] == s['number'])
    actor = value.get('user')
    require(isinstance(actor,dict) and type(actor.get('id')) is int and actor['id']==t['author_id'] and actor.get('type')=='User')
    require(value.get('html_url') == f"https://github.com/{CONTROLLER}/issues/{s['number']}")
    body = value.get('body')
    require(isinstance(body,str))
    try:
        digest=hashlib.sha256(body.encode('utf-8')).hexdigest()
    except UnicodeError:
        raise core.ProtocolError('invalid_board','Invalid consent body encoding') from None
    require(digest == s['body_sha256'])


def _tip(t, receipt, meta, pr, checks):
    rid, pid, aid, name = t['repository_id'],t['pull_request_id'],t['author_id'],t['repository']
    identity = _public_meta(meta,rid,name)
    require(identity[2] != aid)
    require(isinstance(pr,dict) and isinstance(pr.get('base'),dict))
    base_identity = _public_meta(pr['base'].get('repo'),rid,name)
    require(base_identity == identity)
    observed = receipt['pull_request']
    require(observed['id'] == pid and observed['author']['id'] == aid and observed['author']['type']=='User')
    require(observed['state']=='merged' and observed['draft'] is False)
    merger = observed['merge']['merged_by']
    require(merger is not None and type(merger['id']) is int and 0 < merger['id'] <= SAFE and merger['id']!=aid)
    require(timestamp(observed['merge']['merged_at']) <= timestamp(checks['pull_request']))
    size={}
    for key in ('additions','deletions','changed_files'):
        value=pr.get(key)
        require(value is None or type(value) is int and 0<=value<=SAFE)
        size[key]=value
    return {'repository_id':rid,'pull_request_id':pid,'number':t['number'],
            'url':f"https://github.com/{name}/pull/{t['number']}",
            'author_id':aid,'author_login':observed['author']['login'],
            'merged_at':observed['merge']['merged_at'],'checks':checks,
            'verified_at':min(checks.values(),key=timestamp),
            'submission_url':f"https://github.com/{CONTROLLER}/issues/{t['submission']['number']}",
            'agent_assistance':'self-declared','size':size}


def _directory(reads, candidate):
    """Fresh canonical reader followed by metadata recheck, even for closed jars."""
    rid,name=candidate['repository_id'],candidate['repository']
    endpoint='repos/'+name
    start=len(reads.events)
    meta=reads.request_once(endpoint)
    identity=_public_meta(meta,rid,name)
    find._metadata(meta, {'identity':identity})
    for key in ('archived','disabled'):
        require(type(meta.get(key)) is bool)
    branch=meta.get('default_branch')
    require(isinstance(branch,str) and branch.strip())
    jar=None
    if meta['archived'] or meta['disabled']:
        state='excluded'
    else:
        jar=tipjar.read_jar(name,reads,metadata=meta)
        # Refuse future reader contracts rather than guessing their provenance.
        if set(jar) != {'repository','default_branch','commit','path','blob_sha','sha256','fetched_at','state','complete','manifest','errors','notice'}:
            raise core.ProtocolError('unsupported_board_reader','Unsupported canonical reader contract for board/1')
        state=jar['state'] if tipjar._complete_report(jar) else 'unknown'
        if state=='unknown':jar=None
    final=reads.request_once(endpoint)
    require(_public_meta(final,rid,name)==identity)
    require(final.get('default_branch')==branch and type(final.get('archived')) is bool and type(final.get('disabled')) is bool)
    if final['archived'] or final['disabled']:
        state='excluded';jar=None
    checks=[event[1] for event in reads.events[start:]]
    source=None
    if jar is not None and state in ('welcome','closed'):
        source={'kind':'manifest','path':jar['path'],'commit':jar['commit'],'sha256':jar['sha256']}
    obs={'repository_id':rid,'repository':name,'disposition':state,'verified_at':min(checks,key=timestamp),
         'checks':checks,'jar':jar,'source':source}
    repo={'repository_id':rid,'repository':name,'primary_language':final.get('language'),'verified_at':checks[0]}
    return obs,repo


def _selection(tips, repositories, observations, directory, coverage):
    """Admit whole repo groups by numeric ID; never retain an orphaned tip."""
    selected_tips=[];selected_repos=[];selected_obs=[]
    grouped={}
    for t in tips:grouped.setdefault(t['repository_id'],[]).append(t)
    obs_by_id={o['repository_id']:o for o in observations}
    for rid in sorted(repositories):
        group=sorted(grouped.get(rid,[]),key=lambda t:t['pull_request_id'])
        obs=obs_by_id.get(rid)
        trial=dict(directory,observations=selected_obs+([obs] if obs else []))
        if (len(selected_repos)>=200 or len(selected_tips)+len(group)>500 or
                len(trial['observations'])>200 or len(encode(trial))>DIRECTORY_LIMIT):
            coverage['omitted_repositories']+=1
            coverage['omitted_tips']+=len(group)
            coverage['omitted_directory_observations']+=int(obs is not None)
            continue
        selected_repos.append(repositories[rid]);selected_tips.extend(group)
        if obs is not None:selected_obs.append(obs)
    return selected_tips,selected_repos,selected_obs


def collect(registry: dict, client=None, *, now=None, source_commit, controller_id, clock=None) -> dict:
    """Observe fresh opt-ins and merges; per-item unknowns produce partial coverage.

    source_commit/controller_id must come from the trusted controller workflow,
    never submission text. A supplied client is a trust boundary, like the native
    library API: a fabricated fake response cannot establish actual GitHub facts.
    """
    registry=validate_registry(registry)
    require(isinstance(source_commit,str) and re.fullmatch('[0-9a-f]{40}',source_commit))
    require(type(controller_id) is int and 0<controller_id<=SAFE)
    clock=clock or ((lambda:now) if now is not None else utcnow)
    reads=BudgetClient(client,clock=clock)
    coverage={'exhaustive':False,'partial':False,**{k:0 for k in COUNT_KEYS}}
    controller_time=None
    try:
        controller=reads.request_once('repos/'+CONTROLLER)
        controller_time=reads.events[-1][1]
        _public_meta(controller,controller_id,CONTROLLER)
    except core.ProtocolError:
        controller=None
    tips={};repositories={};candidates={};invalidated=set()
    for candidate in registry['repositories']:
        candidates[candidate['repository_id']]=candidate
    groups={}
    for t in registry['tips']:
        groups.setdefault((t['repository_id'],t['pull_request_id']),[]).append(t)
        candidates[t['repository_id']]={'repository_id':t['repository_id'],'repository':t['repository']}
    for key,submissions in sorted(groups.items()):
        if _excluded(submissions[0],registry['exclusions']):
            coverage['excluded_tips']+=1
            continue
        for t in sorted(submissions,key=lambda t:t['submission']['number']):
            try:
                start=len(reads.events)
                _consent(t,controller,controller_id,reads)
                consent_time=reads.events[start][1]
                receipt=receipts.observe(f"{t['repository']}#{t['number']}",reads)
                checks={'controller':controller_time,'consent':consent_time,
                        'repository':reads.events[-2][1],'pull_request':reads.events[-1][1]}
                tip=_tip(t,receipt,reads.last_repository,reads.last_pr,checks)
                # Validate one tip's public shape before letting it enter aggregation.
                schema=json.loads((Path(__file__).parent/'schemas/tipjar-board.schema.json').read_text('utf-8'))
                require(not core.schema_errors(tip,schema['properties']['tips']['items']))
                tips[key]=tip
                repositories[t['repository_id']]={'repository_id':t['repository_id'],'repository':t['repository'],
                    'primary_language':reads.last_repository.get('language'),'verified_at':checks['repository']}
                break
            except core.ProtocolError:
                continue
        if key not in tips:coverage['unknown_tips']+=1
    report=find.find_jars(reads)
    require(report.get('format')=='find-jars-report/1')
    directory={'complete':bool(report['complete']),'search_failed':'search_failed' in report['errors'],
               'server_incomplete':bool(report['search'].get('incomplete_results')),
               'truncated':bool(report['search'].get('truncated') or report['search'].get('short_page')),'observations':[]}
    # Validate conflicts before admitting any search candidate. Identity-free hits
    # remain aggregate unknown/excluded counts, never public rows.
    names={c['repository'].casefold():rid for rid,c in candidates.items()}
    for obs in report['observations']:
        rid,name=obs.get('repository_id'),obs.get('repository')
        if type(rid) is not int or not 0<rid<=SAFE or not isinstance(name,str):
            coverage['excluded_repositories' if obs.get('disposition')=='excluded' else 'unknown_repositories']+=1
            continue
        core.parse_repository(name)
        require(rid not in candidates or candidates[rid]['repository']==name)
        require(names.setdefault(name.casefold(),rid)==rid)
        candidates[rid]={'repository_id':rid,'repository':name}
    if directory['search_failed'] or directory['server_incomplete'] or directory['truncated']:
        directory['complete']=False
    observations=[]
    for rid,candidate in sorted(candidates.items()):
        if _excluded(candidate,registry['exclusions']):
            coverage['excluded_repositories']+=1
            repositories.pop(rid,None)
            continue
        try:
            require(rid not in reads.private_ids and candidate['repository'].casefold() not in reads.private_names)
            obs,repo=_directory(reads,candidate)
            # Every check on a retained repository contributes conservatively.
            if rid in repositories:
                repo['verified_at']=min(repo['verified_at'],repositories[rid]['verified_at'],key=timestamp)
            repositories[rid]=repo;observations.append(obs)
            if obs['disposition']=='unknown':
                coverage['unknown_repositories']+=1;directory['complete']=False
        except core.ProtocolError as exc:
            if exc.code == 'unsupported_board_reader': raise
            # The final read may reveal a move/private repo. Never retain earlier
            # payloads or tips for a candidate that cannot be rechecked public.
            invalidated.add(rid);repositories.pop(rid,None)
            coverage['unknown_repositories']+=1;directory['complete']=False
    invalidated.update(rid for rid, candidate in candidates.items() if rid in reads.private_ids or candidate['repository'].casefold() in reads.private_names)
    observations=[o for o in observations if o['repository_id'] not in invalidated]
    for rid in invalidated: repositories.pop(rid,None)
    for key in list(tips):
        if key[0] in invalidated or key[0] not in repositories:
            del tips[key];coverage['unknown_tips']+=1
    selected_tips,selected_repos,selected_obs=_selection(list(tips.values()),repositories,observations,directory,coverage)
    directory['observations']=selected_obs
    if coverage['omitted_directory_observations']:directory['complete']=False
    coverage['partial']=bool(any(coverage[k] for k in COUNT_KEYS if k.startswith(('unknown_','omitted_'))) or
                             not directory['complete'] or directory['search_failed'] or directory['server_incomplete'] or directory['truncated'])
    generated=clock()
    times=[timestamp(r['verified_at']) for r in selected_repos]
    times.extend(timestamp(c) for t in selected_tips for c in t['checks'].values())
    times.extend(timestamp(c) for o in selected_obs for c in o['checks'])
    result={'format':'tipjar-board/1','generated_at':iso(generated),
            'expires_at':iso((min(times) if times else generated)+dt.timedelta(hours=48)),
            'rules_version':1,'source_commit':source_commit,'coverage':coverage,
            'tips':selected_tips,'repositories':selected_repos,'directory':directory}
    return require_fresh(result,now=clock())


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--source-commit',required=True)
    parser.add_argument('--controller-id',required=True,type=int)
    args=parser.parse_args(argv)
    try:
        require(not args.output.exists() and not args.output.is_symlink())
        # Refuse a symlink leaf and bound reads before JSON parsing.
        descriptor=os.open(args.registry,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
        import stat
        with os.fdopen(descriptor,'rb') as handle:
            require(stat.S_ISREG(os.fstat(handle.fileno()).st_mode))
            registry=validate_registry(handle.read(REGISTRY_LIMIT+1))
        result=collect(registry,source_commit=args.source_commit,controller_id=args.controller_id)
        data=encode(result)+b'\n'
        require(len(data)<=BOARD_LIMIT)
        require_fresh(result)
        # O_EXCL protects existing files and symlink leaves; failed writes clean
        # up only the file created here, never a prior snapshot.
        with args.output.open('xb') as handle:
            try:
                handle.write(data)
                handle.flush()
                require_fresh(result)
            except BaseException:
                args.output.unlink()
                raise
        return 0
    except (core.ProtocolError,OSError):
        print('Board collection refused: invalid, unavailable, expired, or existing output.',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
