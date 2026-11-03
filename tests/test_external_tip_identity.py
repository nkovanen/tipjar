import datetime as dt
import unittest
from agent_contribute import core, pr_identity
from tests.test_external_tip_prepare import ExternalGitHub


class ExternalHistoryTests(unittest.TestCase):
    def binding(self):
        now=dt.datetime.now(dt.timezone.utc)
        return dict(source_repository='acme/photos',source_repository_id=101,source_owner_id=7,
                    head_repository='human/photos',head_repository_id=202,head_owner_id=7,credential_actor_id=7,
                    head_ref='tip-12',base_ref='main',contract_sha256='a'*64,publication_authorization_sha256='b'*64,
                    issued_at=(now-dt.timedelta(minutes=1)).isoformat(),expires_at=(now+dt.timedelta(hours=1)).isoformat())

    def test_empty_histories_scan_both_without_base_filter(self):
        c=ExternalGitHub();r=pr_identity.check_external_publication(self.binding(),None,'a'*40,c)
        self.assertTrue(r['creation_clear'],r)
        paths=[x for x in c.calls if 'state=all' in x]
        self.assertEqual(len(paths),2)
        self.assertTrue(any('repos/human/photos/pulls?' in x for x in paths))
        self.assertFalse(any('&base=' in x for x in paths))

    def test_old_same_repo_wrapper_still_rejects_cross_repo(self):
        b=self.binding();c=ExternalGitHub()
        self.assertFalse(pr_identity.check_publication(b,None,None,c)['creation_clear'])
        self.assertEqual(c.calls,[])
