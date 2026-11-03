"""Closed external host assertions. These checks authenticate neither consent nor prose truth."""
from __future__ import annotations

import datetime as dt
import re
from urllib.parse import quote

from . import authorization as auth, core


def context_errors(context):
    return core.schema_errors(context, core.bundled_schema('external-context', '0.1'))


def source_uri(source):
    return f"https://github.com/{source['repository']}/blob/{source['commit']}/{quote(source['path'], safe='/')}"


def assessment_errors(task, context, facts, now):
    errors = context_errors(context)
    if errors:
        return errors
    assessment, observations = context['policy_assessment'], context['policy_observations']
    bound = facts.get('inventories', [])
    if len(bound) != 2:
        return ['Both complete policy inventories are required']
    expected_inventories = [dict(repository_id=b['repository_id'], inventory_format=4,
                                  inventory_sha256=b['inventory']['inventory_sha256']) for b in bound]
    if sorted(assessment['inventories'], key=lambda x: x['repository_id']) != sorted(expected_inventories, key=lambda x: x['repository_id']):
        errors.append('Assessment must bind exactly both live inventories')
    expected = {}
    for b in bound:
        inv = b['inventory']
        from .external_tip import inventory_errors
        errors += inventory_errors(inv)
        for item in inv['sources_scanned'] + inv['unassessed']:
            key = (b['repository_id'], inv['inventory_sha256'], item['identity_sha256'])
            expected.setdefault(key, []).append((item, inv))
    actual = {}
    applicable = {}
    for row in assessment['entries']:
        key = (row['repository_id'], row['inventory_sha256'], row['identity_sha256'])
        if key in actual:
            errors.append('Duplicate policy assessment identity')
        actual[key] = row
        if row['disposition'] in ('unresolved', 'prohibited'):
            errors.append('Policy assessment contains unresolved or prohibited policy')
        if key not in expected:
            errors.append('Unknown policy assessment identity')
            continue
        evidence = row['evidence']
        for ev in evidence:
            try:
                if auth.timestamp(ev['observed_at']) > now:
                    raise ValueError('Policy evidence timestamp is in the future')
            except (ValueError, OverflowError) as exc:
                errors.append(str(exc))
        items = expected[key]
        if row['disposition'] == 'owner-lookup-404':
            for item, inv in items:
                owner = inv['owner_lookup']
                if ('what' not in item or item['what'] != owner.get('repository') or
                        owner['status'] != 'not_found_or_inaccessible' or
                        item['reason'] != 'owner .github repository not found or inaccessible' or not any(
                            ev['role'] == 'inventory-observation' and ev['uri'] == f'inventory://{key[0]}/{key[1]}' and
                            ev['content_sha256'] == key[1] and ev['revision'] is None and
                            ev['quote'] == core.canonical_hash(owner) for ev in evidence)):
                    errors.append('owner-lookup-404 disposition does not match the exact inventory observation')
            continue
        # Every row needs the actual referring/source context. A failed target read cannot supply it.
        for item, inv in items:
            if 'path' in item:
                sources = [item]
            else:
                origin = item.get('from')
                sources = [s for s in inv['sources_scanned'] if f"{s['repository']}:{s['path']}" == origin]
            if not sources or not any(ev['role'] == 'referring-context' and ev['uri'] == source_uri(s) and
                                       ev['revision'] == s['commit'] and ev['content_sha256'] == s['sha256']
                                       for s in sources for ev in evidence):
                errors.append('Policy disposition lacks digest-bound actual referring context')
        targets = [ev for ev in evidence if ev['role'] == 'applicable-target']
        if row['disposition'] == 'assessed-applicable' and not targets:
            errors.append('Applicable policy requires target evidence')
        for ev in targets:
            k = (ev['uri'], ev['revision'])
            if k in applicable and applicable[k] != ev['content_sha256']:
                errors.append('Applicable target has conflicting content digests')
            applicable[k] = ev['content_sha256']
    # A potential restriction is resolved only in its exact source context, never by a blanket clear flag.
    for b in bound:
        inv = b['inventory']
        for hint in inv.get('hints', []):
            if hint.get('kind') not in ('possible_agent_restriction', 'possible_ai_restriction', 'possible_pr_restriction'):
                continue
            index = hint.get('source')
            if type(index) is not int or not 0 <= index < len(inv['sources_scanned']):
                errors.append('Restriction hint source identity unresolved')
                continue
            source = inv['sources_scanned'][index]
            row = actual.get((b['repository_id'], inv['inventory_sha256'], source['identity_sha256']))
            if row is None or row['disposition'] not in ('false-positive', 'inapplicable', 'assessed-applicable') or not any(
                    ev['role'] == 'referring-context' and ev['uri'] == source_uri(source) and
                    hint['untrusted_excerpt'] in ev['quote'] for ev in row['evidence']):
                errors.append('Potential policy restriction lacks an evidenced source-context disposition')
    if set(actual) != set(expected):
        errors.append('Every retained source and unassessed identity must be accounted for exactly')
    impl = context['implementation']
    pub = context.get('publication_authorization')
    expected_obs = dict(policy_assessment_sha256=core.canonical_hash(assessment),
                        policy_inventory_sha256=expected_inventories[0]['inventory_sha256'],
                        fork_policy_inventory_sha256=expected_inventories[1]['inventory_sha256'],
                        implementation_sha256=core.canonical_hash(impl),
                        publication_authorization_sha256=core.canonical_hash(pub) if pub else None)
    for key, value in expected_obs.items():
        if observations[key] != value:
            errors.append('Fresh policy observations binding differs: ' + key)
    seen = set()
    for obs in observations['entries']:
        k = (obs['uri'], obs['revision'])
        if k in seen or k not in applicable:
            errors.append('Unknown or duplicate fresh policy observation')
        seen.add(k)
        if obs['status'] != 'read' or obs['content_sha256'] != applicable.get(k):
            errors.append('Applicable external policy changed or unreadable')
        try:
            age = now - auth.timestamp(obs['observed_at'])
            if not dt.timedelta(0) <= age <= dt.timedelta(minutes=15):
                raise ValueError('Fresh policy observation is future or older than 15 minutes')
        except (ValueError, OverflowError) as exc:
            errors.append(str(exc))
    if seen != set(applicable):
        errors.append('Fresh observations must cover exactly every applicable policy target')
    return errors


def payload_errors(payload):
    errors = core.schema_errors(payload, core.bundled_schema('draft-payload', '0.1'))
    if errors:
        return errors
    if re.search(r'[\x00-\x1f\x7f]', payload['title']):
        errors.append('Payload title contains control characters')
    try:
        if len(payload['body'].encode('utf-8')) > 60000:
            errors.append('Payload body exceeds 60000 UTF-8 bytes')
    except UnicodeError:
        errors.append('Payload must contain valid UTF-8')
    return errors


def check(task, context, facts, *, evidence=None, payload=None, now):
    result = dict(implementation_historical=False, implementation_current=False,
                  publication_historical=False, publication_current=False,
                  implementation_sha256=None, publication_authorization_sha256=None,
                  errors=[], implementation_errors=[], publication_errors=[], assessment_errors=[])
    errors = context_errors(context)
    if errors:
        result['errors'] = errors
        return result
    assessed = result['assessment_errors'] = assessment_errors(task, context, facts, now)
    impl, pub = context['implementation'], context.get('publication_authorization')
    result['implementation_sha256'] = core.canonical_hash(impl)
    if pub:
        result['publication_authorization_sha256'] = core.canonical_hash(pub)
    invs = facts.get('inventories', [])
    expected = dict(contract_sha256=core.canonical_hash(task), credential_actor_id=task['execution']['credential_actor_id'],
                    policy_inventory_sha256=task['source_review']['inventory_sha256'],
                    fork_policy_inventory_sha256=invs[1]['inventory']['inventory_sha256'] if len(invs) == 2 else None,
                    policy_assessment_sha256=core.canonical_hash(context['policy_assessment']),
                    policy_ledger_sha256=impl['policy_review']['ledger_sha256'],
                    invitation_basis=task['source_review']['invitation_basis'],
                    undeclared_acknowledged=task['source_review']['invitation_basis'] == 'explicit-undeclared')
    intervals = {}
    for name, record in (('implementation', impl), ('publication', pub)):
        errs = result[name + '_errors']
        if record is None:
            errs.append('Missing separate publication authorization')
            continue
        for key, value in expected.items():
            if record[key] != value:
                errs.append(name + ' authorization binding differs: ' + key)
        if (facts.get('credential_actor') or {}).get('id') != record['credential_actor_id']:
            errs.append('Authorization actor differs from current credential')
        try:
            intervals[name] = auth.interval(record, now)
        except (ValueError, OverflowError) as exc:
            errs.append(str(exc))
        if name == 'publication':
            if evidence is None or core.schema_errors(evidence, core.bundled_schema('evidence', '0.2')):
                errs.append('Publication requires complete evidence 0.2')
            else:
                exact = dict(evidence_sha256=core.canonical_hash(evidence), review_sha256=core.canonical_hash(evidence['independent_review']),
                             git_head=evidence['git_head'], git_tree=evidence['git_tree'], base_commit=evidence['base_commit'],
                             payload_sha256=core.canonical_hash(payload))
                for key, value in exact.items():
                    if record[key] != value:
                        errs.append('Publication exact result binding differs: ' + key)
                try:
                    issued = auth.timestamp(record['issued_at'])
                    if (record['id'] == impl['id'] or record['event_reference'] == impl['event_reference'] or
                            issued <= auth.timestamp(impl['issued_at']) or
                            issued < auth.timestamp(evidence['independent_review']['reviewed_at']) or any(
                                issued < auth.timestamp(v['finished_at']) for v in evidence['validations'])):
                        raise ValueError('Publication must be a distinct later decision after validation and review')
                except (ValueError, OverflowError) as exc:
                    errs.append(str(exc))
            errs += payload_errors(payload)
        result[name + '_historical'] = not errs and not assessed
        result[name + '_current'] = result[name + '_historical'] and now < intervals[name][1]
        if name in intervals and now >= intervals[name][1]:
            errs.append(name + ' authorization expired for new actions')
    result['errors'] = list(assessed)
    return result
