import copy
import datetime as dt
import unittest
from agent_contribute import core

NOW=dt.datetime.now(dt.timezone.utc)


def fixture(t=None, f=None):
    from agent_contribute import external_tip
    from tests.test_external_tip_prepare import ExternalGitHub
    if t is None:
        c=ExternalGitHub();t=external_tip.prepare('acme/photos#12','human/photos','tip-12',c)
        f=external_tip.live_facts(t,None,c)
    assessment={'inventories':[], 'entries':[]}
    for bound in f['inventories']:
        inv=bound['inventory'];rid=bound['repository_id'];digest=inv['inventory_sha256']
        assessment['inventories'].append(dict(repository_id=rid,inventory_format=4,inventory_sha256=digest))
        seen=set()
        for item in inv['sources_scanned']+inv['unassessed']:
            identity=item['identity_sha256']
            if identity in seen:continue
            seen.add(identity)
            if 'path' in item:
                ev=dict(role='referring-context',uri=f"https://github.com/{item['repository']}/blob/{item['commit']}/{item['path']}",revision=item['commit'],content_sha256=item['sha256'],quote='Ordinary project guidance.',observed_at=NOW.isoformat())
                disposition='inapplicable'
            else:
                ev=dict(role='inventory-observation',uri=f'inventory://{rid}/{digest}',revision=None,content_sha256=digest,quote=core.canonical_hash(inv['owner_lookup']),observed_at=NOW.isoformat())
                disposition='owner-lookup-404'
            assessment['entries'].append(dict(repository_id=rid,inventory_sha256=digest,identity_sha256=identity,disposition=disposition,reason='Synthetic evidence of actual source context',evidence=[ev]))
    record=dict(id='fixture-implementation',issued_at=(NOW-dt.timedelta(minutes=2)).isoformat(),expires_at=(NOW+dt.timedelta(hours=1)).isoformat(),event_reference='fixture://decision/1',event_text_sha256='b'*64,contract_sha256=core.canonical_hash(t),credential_actor_id=7,policy_inventory_sha256=t['source_review']['inventory_sha256'],fork_policy_inventory_sha256=f['inventories'][1]['inventory']['inventory_sha256'],policy_assessment_sha256=core.canonical_hash(assessment),policy_ledger_sha256='c'*64,invitation_basis='explicit-undeclared',undeclared_acknowledged=True,actions=['implement'],policy_review=dict(status='clear',reviewer='fixture human',notes='Read applicable workflow',ledger_sha256='c'*64))
    obs=dict(policy_assessment_sha256=core.canonical_hash(assessment),policy_inventory_sha256=record['policy_inventory_sha256'],fork_policy_inventory_sha256=record['fork_policy_inventory_sha256'],implementation_sha256=core.canonical_hash(record),publication_authorization_sha256=None,entries=[])
    return t,f,dict(schema_version='0.1',implementation=record,policy_assessment=assessment,policy_observations=obs)


class ExternalAuthorizationTests(unittest.TestCase):
    def test_complete_assessment_and_scoped_assertion(self):
        from agent_contribute import external_authorization as a
        t,f,c=fixture();r=a.check(t,c,f,now=NOW)
        self.assertTrue(r['implementation_current'],r)
        self.assertFalse(r['publication_current'])

    def test_nojar_requires_explicit_acknowledgement(self):
        from agent_contribute import external_authorization as a
        t,f,c=fixture();c['implementation']['undeclared_acknowledged']=False
        self.assertFalse(a.check(t,c,f,now=NOW)['implementation_current'])

    def test_unaccounted_duplicate_or_wrong_inventory_identity_blocks(self):
        from agent_contribute import external_authorization as a
        for mutation in ('missing','duplicate','wrong','unresolved'):
            t,f,c=fixture();rows=c['policy_assessment']['entries']
            if mutation=='missing':rows.pop()
            if mutation=='duplicate':rows.append(copy.deepcopy(rows[0]))
            if mutation=='wrong':rows[0]['identity_sha256']='0'*64
            if mutation=='unresolved':rows[0]['disposition']='unresolved'
            self.assertTrue(a.assessment_errors(t,c,f,NOW),mutation)

    def test_fork_inventory_binding_is_mandatory(self):
        from agent_contribute import external_authorization as a
        t,f,c=fixture();c['implementation']['fork_policy_inventory_sha256']='0'*64
        self.assertFalse(a.check(t,c,f,now=NOW)['implementation_current'])
