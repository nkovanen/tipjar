"""Explicit external contribution route. Reads facts; never executes or publishes."""
from __future__ import annotations

import datetime as dt
import re
from urllib.parse import quote

from . import authorization as auth, core, policy, tipjar


class _DetailBudget:
    """Count attempted detail GETs, including failures, across ownership and numeric reconciliation."""
    def __init__(self, client, limit):
        self.client, self.limit, self.attempts = client, limit, 0

    def request(self, endpoint):
        if re.fullmatch(r'repos/[^/]+/[^/]+/pulls/[1-9][0-9]*', endpoint):
            if self.attempts >= self.limit:
                raise core.ProtocolError('external_detail_limit', 'Shared cross-reference detail request cap reached')
            self.attempts += 1
        return self.client.request(endpoint)


def identities(repository, fork, client):
    actor = core.require(client.request('user'), dict, 'credential actor')
    if (not auth.positive(actor.get('id')) or actor.get('type') != 'User' or
            not isinstance(actor.get('login'), str) or not auth._LOGIN.fullmatch(actor['login'])):
        raise core.ProtocolError('credential_identity', 'External tips require a personal credential')
    source = auth.repository_identity(repository, client)
    target = auth.repository_identity(fork, client)
    for meta in (source, target):
        if any(meta.get(k) is not False for k in ('private', 'archived', 'disabled')):
            raise core.ProtocolError('external_route', 'Source and fork must be known public, active repositories')
    parent = core.require(target.get('parent'), dict, 'fork parent')
    parent_owner = core.require(parent.get('owner'), dict, 'fork parent owner')
    permissions = core.require(target.get('permissions'), dict, 'fork permissions')
    if (source.get('has_issues') is not True or target.get('fork') is not True or
            target['id'] == source['id'] or target['owner']['type'] != 'User' or
            target['owner']['id'] != actor['id'] or target['owner']['login'] != actor['login'] or
            permissions.get('push') is not True or
            not auth.positive(parent.get('id')) or not auth.positive(parent_owner.get('id')) or
            (parent.get('id'), parent.get('full_name'), parent_owner.get('id'),
             parent_owner.get('login'), parent_owner.get('type')) !=
            (source['id'], repository, source['owner']['id'], source['owner']['login'], source['owner']['type'])):
        raise core.ProtocolError('external_route', 'Requires an immediate personal-owned writable fork of the explicit issue source')
    return source, target, {k: actor[k] for k in ('id', 'login', 'type')}


def known_restriction(hint):
    """Conservative refusal/eligibility observations; a host assessment cannot override them."""
    text = hint.get('untrusted_excerpt', '').casefold()
    refusal = r'\b(?:no|never|not|reject\w*|refus\w*|forbid\w*|prohibit\w*|bann?\w*|disallow\w*|closed)\b'
    agent = r'\b(?:ai|agent[ -]?(?:generated|assisted)?|agents|llm|automated|bot)\b'
    contribution = r'\b(?:contribution\w*|pull requests?|prs?|patches?|submissions?)\b'
    # Review obligations are assessed by their source row; eligibility/refusal remains a hard boundary.
    return (bool(re.search(refusal, text) and re.search(agent, text) and re.search(contribution, text)) or
            bool(re.search(r'\b(?:only|limited|restricted|invitation)\b', text) and
                 re.search(r'\b(?:maintainers?|members?|collaborators?|owners?|team)\b', text) and
                 re.search(r'\b(?:submit|open|create|contribut|send)', text)))


def inventory_errors(inventory):
    errors = []
    if inventory.get('inventory_format') != 3:
        errors.append('Policy inventory format must be 3')
    if inventory.get('limits_hide_sources') is not False or inventory.get('omitted_sources'):
        errors.append('Policy inventory hides or omits applicable sources')
    if inventory.get('owner_lookup', {}).get('status') not in ('read', 'not_found_or_inaccessible', 'not_applicable'):
        errors.append('Owner policy lookup is unresolved')
    # A prose assessment cannot waive a known prohibition or unread source.
    for hint in inventory.get('hints', []):
        if hint.get('kind') in policy.STOP_HINTS and known_restriction(hint):
            errors.append('Known contribution refusal or eligibility restriction: ' + hint['kind'])
    for item in inventory.get('unassessed', []):
        if any(word in item['reason'] for word in ('read failed', 'exceeds', 'malformed', 'not read')):
            errors.append('Unread or unresolved policy source: ' + item['what'])
    return errors


def prepare(reference, fork, head_ref, client=None):
    repository, number = core.parse_issue(reference)
    fork = core.parse_repository(fork)
    client = client or core.GitHub()
    source, target, actor = identities(repository, fork, client)
    if (not auth.valid_ref(head_ref) or head_ref in (source['default_branch'], target['default_branch'])):
        raise core.ProtocolError('invalid_ref', 'A new contribution head ref is required')
    snapshot = core.repository_snapshot(repository, client, source)
    issue = auth.issue_identity(repository, number, client)
    inspected = core.inspect_from_snapshot(snapshot, issue)
    inv = policy.for_inspected(inspected, client)
    errors = inspected['errors'] + inspected['exclusions'] + tipjar.preparation_errors(snapshot['tipjar']) + inventory_errors(inv)
    fork_snapshot = core.repository_snapshot(fork, client, target)
    fork_inv = policy.report(fork, fork_snapshot['commit'], fork_snapshot['instructions'], client,
                             default_branch=target['default_branch'], tipjar_report=fork_snapshot['tipjar'])
    errors += fork_snapshot['errors'] + inventory_errors(fork_inv)
    if errors:
        raise core.ProtocolError('external_preparation', '; '.join(errors))
    task = core.prepare(inspected)
    task.update(schema_version='0.3')
    task['source'].update(repository_id=source['id'], owner_id=source['owner']['id'], issue_id=issue['id'],
                          policy_sha256=auth.policy_hash(inspected['provenance']))
    jar = snapshot['tipjar']
    task['source_review'] = dict(inventory_format=3, inventory_sha256=inv['inventory_sha256'],
                                  invitation_basis='welcome' if jar['state'] == 'welcome' else 'explicit-undeclared',
                                  jar_state=jar['state'], jar_sha256=jar['sha256'])
    task['execution'] = dict(mode='external-tip', target_repository=fork, target_repository_id=target['id'],
                            head_repository=fork, head_repository_id=target['id'], head_owner_id=actor['id'],
                            credential_actor_id=actor['id'], head_ref=head_ref, base_ref=source['default_branch'],
                            requested_actions=['implement', 'push_head', 'create_draft'])
    for item in task['discovery']['duplicate_prs']:
        item['repository'] = repository
    task['questions'][-1] = 'Review both complete policy inventories and scoped work; obtain separate host implementation authority.'
    facts = live_facts(task, None, client)
    preparation = list(facts['errors'])
    if facts['remote_head'] is not None:
        preparation.append('Preparation requires a new unpublished fork head branch')
    if facts['duplicates'] or facts['cross_references']:
        preparation.append('Existing open overlap or cross-reference blocks external preparation')
    for name in (repository, fork):
        endpoint = (f'repos/{name}/pulls?state=all&head=' + quote(fork.split('/')[0] + ':' + head_ref, safe='')
                    + '&sort=created&direction=asc')
        history = core.paginate(client, endpoint)
        preparation += history['errors']
        if not history['complete'] or history['items']:
            preparation.append('Preparation requires complete empty exact-head history in source and fork')
    if preparation:
        raise core.ProtocolError('external_preparation', '; '.join(preparation))
    return task


def route_errors(task):
    s, e, r = task['source'], task['execution'], task['source_review']
    errors = []
    if (e['target_repository'] != e['head_repository'] or e['target_repository_id'] != e['head_repository_id'] or
            e['head_repository_id'] == s['repository_id'] or e['head_owner_id'] != e['credential_actor_id'] or
            not auth.valid_ref(e['head_ref']) or not auth.valid_ref(e['base_ref']) or
            e['base_ref'] != s['default_branch'] or e['head_ref'] == e['base_ref']):
        errors.append('External route refs or identities are invalid')
    if (r['invitation_basis'], r['jar_state']) not in (('welcome', 'welcome'), ('explicit-undeclared', 'undeclared')) or (
            (r['jar_state'] == 'undeclared') != (r['jar_sha256'] is None)):
        errors.append('External source invitation binding is invalid')
    return errors


def remote_head(task, client):
    e = task['execution']
    endpoint = f"repos/{e['head_repository']}/git/ref/heads/{quote(e['head_ref'], safe='')}"
    try:
        ref = core.require(client.request(endpoint), dict, 'head ref')
    except core.ProtocolError as exc:
        if getattr(exc, 'http_status', None) == 404:
            return None
        raise
    obj = core.require(ref.get('object'), dict, 'head ref object')
    if ref.get('ref') != 'refs/heads/' + e['head_ref'] or obj.get('type') != 'commit' or not core.SHA.fullmatch(str(obj.get('sha', ''))):
        raise core.ProtocolError('external_head', 'Malformed exact fork head ref')
    commit = core.require(client.request(f"repos/{e['head_repository']}/git/commits/{obj['sha']}"), dict, 'fork head commit')
    tree = core.require(commit.get('tree'), dict, 'fork head tree').get('sha')
    if commit.get('sha') != obj['sha'] or not isinstance(tree, str) or not core.SHA.fullmatch(tree):
        raise core.ProtocolError('external_head', 'Fork head commit/tree unresolved')
    return dict(sha=obj['sha'], tree=tree)


def checkout_initial(task, directory):
    if directory is None:
        return ['Implementation requires a safe initial checkout']
    try:
        head = core.open_checkout(directory)
        e = task['execution']
        if core.git_read(directory, 'symbolic-ref', 'HEAD') != 'refs/heads/' + e['head_ref']:
            raise core.ProtocolError('external_checkout', 'Initial checkout branch differs')
        if head != task['source']['commit'] or core.worktree_dirty(directory, head):
            raise core.ProtocolError('external_checkout', 'Initial checkout must be clean at the exact source commit')
        core.git_read(directory, 'cat-file', '-e', head + '^{commit}')
        if core.git_read(directory, 'rev-parse', '--is-shallow-repository') != 'false' or core.has_gitlink(directory, head):
            raise core.ProtocolError('external_checkout', 'Requires full history without gitlinks')
        remotes = core.git_read(directory, 'config', '--local', '--get-regexp', r'^remote\..*\.url$')
        urls = [line.split(None, 1)[1] for line in remotes.splitlines() if len(line.split(None, 1)) == 2]
        pattern = r'(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)' + re.escape(e['target_repository']) + r'(?:\.git)?/?'
        if not any(re.fullmatch(pattern, url) for url in urls):
            raise core.ProtocolError('external_checkout', 'Initial checkout lacks the exact fork remote')
        return []
    except core.ProtocolError as exc:
        return [str(exc)]


def live_facts(task, directory, client):
    s, e = task['source'], task['execution']
    facts = dict(source_identity=None, fork_identity=None, credential_actor=None, inventories=[],
                 errors=[], initial_errors=checkout_initial(task, directory), duplicates=[], cross_references=[],
                 provenance={}, base_tip=None, remote_head=None)
    errors = facts['errors']
    try:
        source, fork, actor = identities(s['repository'], e['head_repository'], client)
        facts.update(source_identity=dict(repository=source['full_name'], repository_id=source['id'], owner_id=source['owner']['id']),
                     fork_identity=dict(repository=fork['full_name'], repository_id=fork['id'], owner_id=fork['owner']['id']), credential_actor=actor)
        if (source['id'], source['owner']['id'], fork['id'], fork['owner']['id'], actor['id']) != (
                s['repository_id'], s['owner_id'], e['head_repository_id'], e['head_owner_id'], e['credential_actor_id']):
            errors.append('Pinned numeric source/fork/actor identity changed')
        if source['default_branch'] != e['base_ref'] or e['head_ref'] == fork['default_branch']:
            errors.append('Source/fork default ref changed or head is default')
        issue = auth.issue_identity(s['repository'], s['issue'], client)
        if issue['id'] != s['issue_id'] or core.issue_hash(issue) != s['issue_sha256']:
            errors.append('Pinned issue identity or content changed')
        if 'assignees' not in issue or not isinstance(issue['assignees'], list):
            errors.append('Issue assignees unresolved')
        elif issue['assignees']:
            errors.append('Issue has assignees')
        snapshot = core.repository_snapshot(s['repository'], client, source)
        facts['base_tip'] = snapshot['commit']
        inspected = core.inspect_from_snapshot(snapshot, issue)
        facts['repository_approval'] = inspected['approval']
        errors += inspected['errors'] + inspected['exclusions']
        if core.compare_relation(client, s['repository'], snapshot['commit'], s['commit']) not in ('identical', 'behind'):
            errors.append('Source commit no longer belongs to default branch history')
        historical = core.repository_snapshot(s['repository'], client, source, commit=s['commit'])
        errors += ['Historical source: ' + x for x in historical['errors']]
        for baseline in (snapshot, historical):
            if baseline['instructions_sha256'] != s['instructions_sha256']:
                errors.append('Pinned instructions changed or baseline differs')
            if auth.policy_hash(baseline) != s['policy_sha256']:
                errors.append('Pinned label policy changed')
            errors += tipjar.preparation_errors(baseline['tipjar'])
            jar = baseline['tipjar']
            if (jar['state'], jar['sha256']) != (task['source_review']['jar_state'], task['source_review']['jar_sha256']):
                errors.append('Pinned jar declaration changed')
            inv = policy.report(s['repository'], baseline['commit'], baseline['instructions'], client,
                                default_branch=source['default_branch'], tipjar_report=jar)
            errors += inventory_errors(inv)
            if inv['inventory_sha256'] != task['source_review']['inventory_sha256']:
                errors.append('Pinned source policy inventory changed')
        source_inv = inv
        fork_snapshot = core.repository_snapshot(e['head_repository'], client, fork)
        errors += fork_snapshot['errors']
        fork_inv = policy.report(e['head_repository'], fork_snapshot['commit'], fork_snapshot['instructions'], client,
                                 default_branch=fork['default_branch'], tipjar_report=fork_snapshot['tipjar'])
        errors += inventory_errors(fork_inv)
        facts['inventories'] = [dict(repository_id=s['repository_id'], repository=s['repository'], inventory=source_inv),
                                dict(repository_id=e['head_repository_id'], repository=e['head_repository'], inventory=fork_inv)]
        facts['duplicates'] = [dict(x, repository=s['repository']) for x in inspected['duplicates']]
        facts['duplicates'] += [dict(x, repository=e['head_repository']) for x in core.duplicate_prs(
            s['repository'], issue, fork_snapshot['pr_index'], pr_repository=e['head_repository'])]
        facts['open_ids'] = {}
        facts['open_prs'] = {}
        for name, rid, snap in ((s['repository'], s['repository_id'], snapshot),
                                (e['head_repository'], e['head_repository_id'], fork_snapshot)):
            for pr in snap['pulls']:
                number = pr.get('number')
                key = (name, number) if type(number) is int else None
                if (not auth.positive(pr.get('id')) or not auth.positive(number) or key in facts['open_ids'] or
                        pr.get('html_url') != f'https://github.com/{name}/pull/{number}' or pr.get('state') != 'open' or
                        not isinstance(pr.get('base'), dict) or not isinstance(pr['base'].get('repo'), dict) or
                        (pr['base']['repo'].get('id'), pr['base']['repo'].get('full_name')) != (rid, name)):
                    errors.append('Malformed or conflicting complete open PR scan identity')
                    continue
                facts['open_ids'][key] = pr['id']
                facts['open_prs'][key] = pr
        from . import ownership
        detail_client = _DetailBudget(client, ownership.MAX_PR_DETAILS)
        signals = ownership.ownership_signals(s['repository'], s['issue'], detail_client)
        facts['ownership'] = signals
        errors += signals['errors']
        if signals['claims']:
            errors.append('Detected issue ownership claim')
        if signals['resolution_signals']['possibly_already_fixed']:
            errors.append('Possible merged upstream fix')
        # Both ordinary detail reads and numeric-identity reads share the existing cap.
        open_refs = [x for x in signals['cross_referenced_prs'] if x['state'] == 'open']
        if detail_client.attempts + len(open_refs) > ownership.MAX_PR_DETAILS:
            errors.append('Cross-reference numeric identity detail limit exceeded')
        else:
            from .pr_identity import _pr_facts
            for item in open_refs:
                detail = _pr_facts(detail_client.request(f"repos/{item['repository']}/pulls/{item['number']}"), detail=True)
                if (detail['number'], detail['url'], detail['base_repository'], detail['base_repository_id'], detail['state']) != (
                        item['number'], item['url'], item['repository'], item['repository_id'], item['state']):
                    errors.append('Cross-reference detail identity disagrees')
                facts['cross_references'].append(dict(item, pr_id=detail['id']))
        facts['remote_head'] = remote_head(task, client)
        facts['provenance'] = dict(source_commit=s['commit'], source_tip=snapshot['commit'], fork_tip=fork_snapshot['commit'])
    except core.ProtocolError as exc:
        errors.append(str(exc))
    return facts


def publication_binding(task, context):
    s, e = task['source'], task['execution']
    record = context.get('publication_authorization', context['implementation'])
    return dict(source_repository=s['repository'], source_repository_id=s['repository_id'], source_owner_id=s['owner_id'],
                head_repository=e['head_repository'], head_repository_id=e['head_repository_id'],
                head_owner_id=e['head_owner_id'], credential_actor_id=e['credential_actor_id'],
                head_ref=e['head_ref'], base_ref=e['base_ref'], contract_sha256=core.canonical_hash(task),
                publication_authorization_sha256=core.canonical_hash(record), issued_at=record['issued_at'], expires_at=record['expires_at'])


def ledger_errors(context, evidence, directory):
    from pathlib import Path
    if not isinstance(context, dict) or 'implementation' not in context:
        return ['Policy ledger requires implementation authority']
    if not isinstance(evidence, dict) or core.schema_errors(evidence, core.bundled_schema('evidence', '0.2')) or directory is None:
        return ['Final compliance and initial policy ledger artifacts are required']
    initial = context['implementation']['policy_ledger_sha256']
    assessment = core.canonical_hash(context['policy_assessment'])
    initial_found, final_found = False, False
    errors = []
    for item in evidence['artifacts']:
        try:
            path = (Path(directory) / item['path']).resolve()
            if not path.is_relative_to(Path(directory).resolve()):
                raise OSError('Artifact escapes checkout')
            data = core.read_regular(path, 32 * 1024 * 1024)
            if core.hashlib.sha256(data).hexdigest() != item['sha256']:
                raise OSError('Artifact hash changed')
            if item['sha256'] == initial:
                initial_found = assessment.encode() in data
            elif assessment.encode() in data and evidence['git_head'].encode() in data:
                final_found = True
        except OSError as exc:
            errors.append('Ledger artifact unreadable: ' + str(exc))
    if not initial_found:
        errors.append('Initial policy ledger artifact must retain its approved bytes and assessment hash')
    if not final_found:
        errors.append('Separate final compliance artifact must bind final head and assessment')
    return errors


def verify(task, evidence=None, repo_dir=None, client=None, *, context=None, payload=None):
    from . import external_authorization, lifecycle, pr_identity
    errors = core.validate_contract(task)
    result = dict(report='external-tip-report/1', schema_version='0.3', schema_valid=not errors,
                  contract_sha256=None, source_identity=None, fork_identity=None, credential_actor=None,
                  source_invitation=None, repository_approval=dict(status='unknown', reason='Not refreshed'),
                  policy_reviews=dict(inventories=[], assessment=None, observations=None, errors=[]),
                  live_complete=False, implementation_ready=False, technical_evidence_valid=False,
                  independent_review=dict(valid=False, status='pending', errors=[]), draft_create_ready=False,
                  publication_verified=False, publication=dict(status='unknown', own_pr=None, url=None, errors=[]),
                  stage_blockers=dict(implementation=[], draft=[], published=[]), errors=errors, evidence_errors=[],
                  provenance={}, next_action='resolve_blockers',
                  trust=['Human/host assertions do not authenticate consent, identity of issuer or prose truth.',
                         'Technical evidence and review are self-attested; host must enforce single use.',
                         'Prior-work and policy detection are bounded; GET snapshots are not atomic.'])
    if errors:
        result['stage_blockers'] = {k: list(errors) for k in result['stage_blockers']}
        return result
    client = client or core.GitHub()
    digest = result['contract_sha256'] = core.canonical_hash(task)
    common = core.reviewed_contract_errors(task, '0.3')
    facts = live_facts(task, repo_dir, client)
    common += facts['errors']
    for key in ('source_identity', 'fork_identity', 'credential_actor', 'provenance'):
        result[key] = facts[key]
    result['source_invitation'] = dict(basis=task['source_review']['invitation_basis'],
                                       state=task['source_review']['jar_state'], digest=task['source_review']['jar_sha256'])
    result['repository_approval'] = facts.get('repository_approval', result['repository_approval'])
    result['policy_reviews']['inventories'] = facts['inventories']
    publication = dict(status='unknown', verified=False, creation_clear=False, own_pr=None, detail=None, errors=['External history requires valid context'])
    valid_context = not external_authorization.context_errors(context)
    if valid_context:
        result['policy_reviews'].update(assessment=context['policy_assessment'], observations=context['policy_observations'])
        publication = pr_identity.check_external_publication(publication_binding(task, context), context.get('publication_claim'),
                                                              evidence.get('git_head') if isinstance(evidence, dict) else None, client)
    technical_errors = []
    if evidence is not None:
        technical_errors = core.check_evidence(task, evidence, repo_dir, digest, current_commit=facts['base_tip'],
                                               client=client, schema_version='0.2', attestations=())
        if not core.schema_errors(evidence, core.bundled_schema('evidence', '0.2')) and evidence['base_commit'] != task['source']['commit']:
            technical_errors.append('External evidence base must equal the exact prepared source commit')
    else:
        technical_errors = ['Final evidence 0.2 is required']
    result['evidence_errors'] = technical_errors
    result['technical_evidence_valid'] = not technical_errors
    # Read identity/payload/tree/base again before judging expiry and host-observation freshness.
    pub_errors = list(publication['errors'])
    if publication['verified']:
        detail = publication['detail']
        try:
            own_key = (task['source']['repository'], publication['own_pr']['number'])
            open_pr = facts.get('open_prs', {}).get(own_key)
            if pr_identity._pr_facts(open_pr) != pr_identity._pr_facts(detail):
                pub_errors.append('Open scan and exact publication detail disagree')
        except core.ProtocolError as exc:
            pub_errors.append(str(exc))
        payload_errors = external_authorization.payload_errors(payload)
        if payload_errors:
            pub_errors.extend('Publication payload ' + error for error in payload_errors)
        elif any(detail.get(k) != payload[k] for k in ('title', 'body', 'draft', 'maintainer_can_modify')):
            pub_errors.append('Published exact title/body/draft/maintainer-edit payload differs')
        remote = facts['remote_head']
        if not remote or not isinstance(evidence, dict) or (remote['sha'], remote['tree']) != (evidence.get('git_head'), evidence.get('git_tree')):
            pub_errors.append('Published fork head/tree differs from evidence')
        try:
            record = context['publication_authorization']
            for base in (record['base_tip'], detail['base']['sha']):
                if core.compare_relation(client, task['source']['repository'], facts['base_tip'], base) not in ('behind', 'identical'):
                    pub_errors.append('Authorized or observed base no longer belongs to source history')
            if core.compare_relation(client, task['source']['repository'], detail['base']['sha'], task['source']['commit']) not in ('behind', 'identical'):
                pub_errors.append('Published base does not contain source commit')
            again = client.request(f"repos/{task['source']['repository']}/pulls/{publication['own_pr']['number']}")
            if again != detail:
                pub_errors.append('External final detail reread changed')
        except (core.ProtocolError, KeyError) as exc:
            pub_errors.append(str(exc))
    # Ledger/artifact reads can block too; action time is sampled only after every blocking read.
    final_ledger_errors = (ledger_errors(context, evidence, repo_dir) if valid_context else
                           ['Valid external context is required'])
    now = dt.datetime.now(dt.timezone.utc)
    authority = external_authorization.check(task, context, facts, evidence=evidence, payload=payload, now=now)
    result['policy_reviews']['errors'] = authority['assessment_errors']
    result['independent_review'] = lifecycle.independent_review(task, evidence, now)
    common += authority['errors']
    overlap_errors = []
    own = publication['own_pr'] if publication['verified'] and not pub_errors and authority['publication_historical'] else None
    def exact_own(item, numeric):
        return own is not None and (item['repository'], item['number'], item['url'], numeric) == (
            own['repository'], own['number'], own['url'], own['id'])
    for item in facts['duplicates']:
        numeric = facts.get('open_ids', {}).get((item['repository'], item['number']))
        if not exact_own(item, numeric):
            overlap_errors.append('Open PR overlap: ' + item['url'])
    for item in facts['cross_references']:
        numeric = facts.get('open_ids', {}).get((item['repository'], item['number']))
        if not (exact_own(item, item['pr_id']) and numeric == item['pr_id'] and item['repository_id'] == own['repository_id']):
            overlap_errors.append('Open cross-referenced PR: ' + item['url'])
    common += overlap_errors
    implementation = common + facts['initial_errors'] + authority['implementation_errors'] + list(publication['errors'])
    if not authority['implementation_current']:
        implementation.append('Current scoped implementation authorization is required')
    if not publication['creation_clear'] or facts['remote_head'] is not None:
        implementation.append('Initial branch must be unpublished and have no exact-head PR history')
    final = common + technical_errors + result['independent_review']['errors']
    if not result['independent_review']['valid']:
        final.append('Valid independent review is required')
    if not authority['implementation_historical']:
        final.append('Historically valid implementation authorization is required')
    final += final_ledger_errors
    draft = final + pub_errors + authority['publication_errors']
    published = final + pub_errors
    if not authority['publication_current']:
        draft.append('Current exact publication authorization is required')
    if not publication['creation_clear']:
        draft.append('New external draft creation requires empty source and fork histories')
    if valid_context and context.get('publication_authorization', {}).get('base_tip') != facts['base_tip']:
        draft.append('Current source base tip differs from publication authorization')
    remote = facts['remote_head']
    if remote and (not isinstance(evidence, dict) or (remote['sha'], remote['tree']) != (evidence.get('git_head'), evidence.get('git_tree'))):
        draft.append('Remote fork head/tree differs from authorized evidence')
    if not authority['publication_historical']:
        published.append('Historically valid exact publication authorization is required')
    if not publication['verified']:
        published.append('Exact upstream draft has not been observed')
    result.update(live_complete=not facts['errors'], implementation_ready=not implementation,
                  draft_create_ready=not draft, publication_verified=not published,
                  stage_blockers=dict(implementation=implementation, draft=draft, published=published), errors=common,
                  publication=dict(status=publication['status'], own_pr=publication['own_pr'],
                                   url=own['url'] if own else None, errors=pub_errors))
    if result['publication_verified']:
        result['next_action'] = 'return_draft'
    elif result['draft_create_ready']:
        result['next_action'] = 'host_publish_exact_draft'
    elif result['implementation_ready']:
        result['next_action'] = 'host_implement_scoped_work'
    return result
