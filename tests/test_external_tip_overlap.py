import unittest
from agent_contribute import core, external_tip


class DetailBudgetTests(unittest.TestCase):
    def test_failed_detail_attempts_share_the_same_fifty_request_cap(self):
        class Unavailable:
            calls=0
            def request(self,endpoint):
                self.calls+=1
                raise core.ProtocolError('api_error','Fixture unavailable detail')
        client=Unavailable();budget=external_tip._DetailBudget(client,50)
        for number in range(1,61):
            with self.assertRaises(core.ProtocolError):budget.request(f'repos/acme/photos/pulls/{number}')
        self.assertEqual(client.calls,50)
