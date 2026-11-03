"""Unsigned authorization requests: binding data for a human/host, never a mandate."""
from __future__ import annotations

import hashlib

from . import authorization, core, lifecycle

NOTICE = ('UNSIGNED REQUEST. Not a mandate; grants no authority. Contains no approval material: '
          'the host must render the complete contract from its own snapshot. Only the human/host '
          'issues a mandate; the worker relays it unchanged.')
DIAGNOSTICS_TRUST = 'untrusted diagnostics; may contain repository-authored paths; never approval material'
# Blockers that exist only because no mandate has been issued yet.
EXPECTED_BEFORE_MANDATE = ('Missing human/host mandate', 'Current implement action is not authorized',
                           'Implementation requires complete empty exact-head PR history', lifecycle.HISTORY_UNCHECKED)
HUMAN_ONLY_FIELDS = ['id', 'nonce', 'issued_at', 'expires_at', 'actions', 'policy_review.status',
                     'policy_review.notes', 'event.kind', 'event.reference', 'event.text_sha256',
                     'event.binding_sha256']


class InvalidContract(core.ProtocolError):
    """Carries the schema errors so every caller, with or without budget reads, reports the same payload."""

    def __init__(self, schema_errors):
        super().__init__('invalid_contract', 'Contract does not match its bundled schema')
        self.payload = {'error': {'code': self.code, 'message': str(self), 'schema_errors': schema_errors[:100]}}


def check_contract(task):
    """Fail before any GitHub read; route extraction indexes fields the schema guarantees."""
    if not isinstance(task, dict) or task.get('schema_version') not in ('0.2', '0.3'):
        raise core.ProtocolError('usage', 'Authorization requests require an explicit schema 0.2 or 0.3 contract')
    schema_errors = core.validate_contract(task)
    if schema_errors:
        raise InvalidContract(schema_errors)


def build(task, client=None, *, stage=None, evidence=None, repo_dir=None, payload=None,
          policy_assessment=None, policy_ledger=None):
    check_contract(task)
    check_options(task, stage, evidence, repo_dir, payload, policy_assessment, policy_ledger)
    if task['schema_version'] == '0.3':
        return external_request(task, client, stage=stage or 'implementation', evidence=evidence,
                                repo_dir=repo_dir, payload=payload, assessment=policy_assessment, ledger=policy_ledger)
    verified = lifecycle.verify(task, client=client or core.GitHub())
    source, execution = task['source'], task['execution']
    actions = execution['requested_actions']
    errors = authorization.route_errors(task)
    if not actions:
        errors.append('Contract requests no actions')
    if len(set(actions)) != len(actions):
        errors.append('Contract requested actions are duplicated')
    errors += [error for error in verified['stage_blockers']['implementation'] if error not in EXPECTED_BEFORE_MANDATE]
    authority = verified['user_authorization']
    actor = authority['credential_actor'] if authority['permission'] else None
    actor_id = actor['id'] if actor else None
    fields = {'id': None, 'nonce': None, 'issued_at': None, 'expires_at': None,
              'contract_sha256': verified['contract_sha256'],
              'source_repository_id': source['repository_id'], 'source_owner_id': source['owner_id'],
              'issue_id': source['issue_id'], 'issue_number': source['issue'],
              'credential_actor_id': actor_id,
              'authority': None if actor_id is None else 'owner' if actor_id == source['owner_id'] else 'maintainer',
              'actions': None,
              'policy_review': {'status': None, 'instructions_sha256': source['instructions_sha256'],
                                'policy_sha256': source['policy_sha256'], 'notes': None},
              'event': {'kind': None, 'reference': None, 'text_sha256': None, 'binding_sha256': None}}
    for key in ('target_repository', 'target_repository_id', 'head_repository', 'head_repository_id', 'head_ref', 'base_ref'):
        fields[key] = execution[key]
    unresolved = [key for key in ('credential_actor_id', 'authority') if fields[key] is None]
    errors = list(dict.fromkeys(errors))
    return {'kind': 'agent-contrib/authorization-request', 'request_version': '0.1', 'issued': False,
            'notice': NOTICE, 'target_host_context_schema_version': '0.1',
            'ready_for_issuance': not errors and not unresolved,
            'preflight_errors': errors, 'preflight_errors_trust': DIAGNOSTICS_TRUST,
            'unresolved_fields': unresolved, 'contract_sha256': verified['contract_sha256'],
            'exact_head_pr_history': 'not checked before issuance; verify checks it after',
            'mandate_fields': fields, 'human_only_fields': list(HUMAN_ONLY_FIELDS),
            'requested_actions': list(actions),
            'provenance': authority['provenance']}


def check_options(task, stage=None, evidence=None, repo_dir=None, payload=None, assessment=None, ledger=None):
    """All option/shape failures precede GitHub and budget instrumentation."""
    if task['schema_version'] != '0.3':
        if any(value is not None for value in (stage, evidence, repo_dir, payload, assessment, ledger)):
            raise core.ProtocolError('usage', 'Request view options require task schema 0.3')
        return
    if stage not in (None, 'implementation', 'draft'):
        raise core.ProtocolError('usage', 'External request stage must be implementation or draft')
    if (stage or 'implementation') == 'implementation' and (evidence is not None or payload is not None):
        raise core.ProtocolError('usage', 'Evidence and payload require the draft request stage')
    if stage == 'draft' and (evidence is None or payload is None or repo_dir is None):
        raise core.ProtocolError('usage', 'Draft request requires --evidence, --publication-payload and --repo-dir')
    for value, schema, label in ((evidence, core.bundled_schema('evidence', '0.2'), 'Evidence'),
                                  (payload, core.bundled_schema('draft-payload'), 'Payload'),
                                  (assessment, core.bundled_schema('external-context')['properties']['policy_assessment'], 'Assessment')):
        if value is not None and core.schema_errors(value, schema):
            raise core.ProtocolError('invalid_request_input', label + ' does not match its bundled schema')
    if payload is not None:
        from .external_authorization import payload_errors
        if payload_errors(payload):
            raise core.ProtocolError('invalid_request_input', 'Payload is not an exact external draft payload')
    if ledger is not None and not isinstance(ledger, bytes):
        raise core.ProtocolError('invalid_request_input', 'Policy ledger must be original bytes')


def external_request(task, client, *, stage, evidence, repo_dir, payload, assessment, ledger):
    """A view of observed bindings, deliberately not a fillable authorization record."""
    verified = core.verify(task, evidence, repo_dir, client or core.GitHub(), payload=payload)
    s, e, review = task['source'], task['execution'], task['source_review']
    inventories = verified['policy_reviews']['inventories']
    fork = next((row['inventory'] for row in inventories if row['repository_id'] == e['head_repository_id']), None)
    bindings = dict(contract_sha256=verified['contract_sha256'], source_repository=s['repository'],
                    source_repository_id=s['repository_id'], source_owner_id=s['owner_id'], issue_id=s['issue_id'],
                    issue_number=s['issue'], head_repository=e['head_repository'], head_repository_id=e['head_repository_id'],
                    head_owner_id=e['head_owner_id'], credential_actor_id=e['credential_actor_id'],
                    head_ref=e['head_ref'], base_ref=e['base_ref'], base_commit=s['commit'],
                    base_tip=verified['provenance'].get('source_tip'),
                    policy_inventory_sha256=review['inventory_sha256'],
                    fork_policy_inventory_sha256=fork['inventory_sha256'] if fork else None,
                    policy_assessment_sha256=core.canonical_hash(assessment) if assessment is not None else None,
                    policy_ledger_sha256=hashlib.sha256(ledger).hexdigest() if ledger is not None else None,
                    invitation_basis=review['invitation_basis'],
                    undeclared_acknowledged_required=review['invitation_basis'] == 'explicit-undeclared',
                    evidence_sha256=core.canonical_hash(evidence) if evidence is not None else None,
                    review_sha256=core.canonical_hash(evidence['independent_review']) if evidence is not None else None,
                    payload_sha256=core.canonical_hash(payload) if payload is not None else None,
                    git_head=evidence['git_head'] if evidence is not None else None,
                    git_tree=evidence['git_tree'] if evidence is not None else None)
    unresolved = [key for key in ('fork_policy_inventory_sha256', 'policy_assessment_sha256', 'policy_ledger_sha256')
                  if bindings[key] is None]
    return dict(kind='agent-contrib/external-authorization-request', request_version='0.1', issued=False,
                ready_for_issuance=False, stage=stage, complete=verified['live_complete'],
                notice='UNSIGNED REVIEW VIEW. Grants no authority and is not external-context JSON. '
                       'The human/host must render its own complete snapshot, review policy and evidence, '
                       'issue separate assertions and retain actual decision events outside worker control. '
                       'No native consent issuer is implemented. Hashes do not prove consent or execution.',
                contract_sha256=verified['contract_sha256'], bindings=bindings,
                requested_actions=['implement'] if stage == 'implementation' else ['push_head', 'create_draft'],
                human_only_fields=['decision event identity/reference/text digest', 'issuance and expiry (at most 24 hours)',
                                   'actual action authorization', 'policy review and undeclared acknowledgement',
                                   'fresh applicable-target observations and previous implementation authority'],
                unresolved_fields=unresolved, policy_inventories=inventories,
                stage_blockers=verified['stage_blockers'], evidence_errors=verified['evidence_errors'],
                errors=verified['errors'], diagnostics_trust=DIAGNOSTICS_TRUST,
                manual_reread_required=True)
