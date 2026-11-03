import copy
import datetime as dt
import unittest
from agent_contribute import core, external_authorization as a
from tests.test_external_tip_authorization import fixture, NOW


class PolicyObservationTests(unittest.TestCase):
    def applicable(self):
        t,f,c=fixture();row=c['policy_assessment']['entries'][0]
        row['disposition']='assessed-applicable'
        target=dict(role='applicable-target',uri='https://policy.example.invalid/contribution',revision='immutable-v1',content_sha256='d'*64,quote='Contributions follow this workflow.',observed_at=NOW.isoformat())
        row['evidence'].append(target)
        c['implementation']['policy_assessment_sha256']=core.canonical_hash(c['policy_assessment'])
        c['policy_observations'].update(policy_assessment_sha256=core.canonical_hash(c['policy_assessment']),implementation_sha256=core.canonical_hash(c['implementation']))
        c['policy_observations']['entries']=[{k:target[k] for k in ('uri','revision','content_sha256','observed_at')}|{'status':'read'}]
        return t,f,c

    def test_applicable_target_requires_exact_fresh_successful_reread(self):
        t,f,c=self.applicable();self.assertEqual(a.assessment_errors(t,c,f,NOW),[])
        for key,value in [('status','unreadable'),('content_sha256','e'*64),('revision','changed'),('observed_at',(NOW-dt.timedelta(minutes=16)).isoformat()),('observed_at',(NOW+dt.timedelta(seconds=1)).isoformat())]:
            changed=copy.deepcopy(c);changed['policy_observations']['entries'][0][key]=value
            self.assertTrue(a.assessment_errors(t,changed,f,NOW),(key,value))

    def test_hiding_sources_or_unavailable_owner_cannot_be_assessed_away(self):
        for key,value in [('limits_hide_sources',True),('omitted_sources',[{'anything':'omitted'}]),('owner_lookup',dict(status='unavailable'))]:
            t,f,c=fixture();f['inventories'][0]['inventory'][key]=value
            self.assertTrue(a.assessment_errors(t,c,f,NOW))

    def test_owner404_disposition_cannot_hide_another_reference(self):
        t,f,c=fixture();c['policy_assessment']['entries'][0]['disposition']='owner-lookup-404'
        self.assertTrue(a.assessment_errors(t,c,f,NOW))

    def test_expiry_is_current_not_historical_authority(self):
        t,f,c=fixture();c['implementation'].update(issued_at=(NOW-dt.timedelta(hours=2)).isoformat(),expires_at=(NOW-dt.timedelta(hours=1)).isoformat())
        c['policy_observations']['implementation_sha256']=core.canonical_hash(c['implementation'])
        r=a.check(t,c,f,now=NOW)
        self.assertTrue(r['implementation_historical'],r)
        self.assertFalse(r['implementation_current'])

    def test_review_requirement_can_be_assessed_but_explicit_ban_cannot(self):
        from agent_contribute import external_tip
        t,f,c=fixture()
        # Source-linked review obligations are not a refusal of contributions.
        inv=f['inventories'][0]['inventory']
        inv['hints']=[dict(kind='possible_pr_restriction',source=0,untrusted_excerpt='PRs must be reviewed by maintainers.')]
        row=c['policy_assessment']['entries'][0];row['disposition']='assessed-applicable'
        row['evidence'][0]['quote']='PRs must be reviewed by maintainers.'
        ev=copy.deepcopy(row['evidence'][0]);ev.update(role='applicable-target',quote='PRs must be reviewed by maintainers.')
        row['evidence'].append(ev)
        c['implementation']['policy_assessment_sha256']=core.canonical_hash(c['policy_assessment'])
        c['policy_observations'].update(policy_assessment_sha256=core.canonical_hash(c['policy_assessment']),implementation_sha256=core.canonical_hash(c['implementation']))
        c['policy_observations']['entries']=[{k:ev[k] for k in ('uri','revision','content_sha256','observed_at')}|{'status':'read'}]
        self.assertEqual(a.assessment_errors(t,c,f,NOW),[])
        for text in ('No AI contributions.','Agent contributions are prohibited.','Only maintainers may submit pull requests.'):
            inv['hints'][0]['untrusted_excerpt']=text
            self.assertTrue(external_tip.inventory_errors(inv),text)
