# -*- coding: utf-8 -*-
from app import config

class TestAdminTokenType:
    # テスト対象API
    apiurl = '/v2/Admin/Tokens/Type'

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, session):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json["data"] == {
            "IbetStraightBond": config.BOND_TOKEN_ENABLED,
            "IbetShare": config.SHARE_TOKEN_ENABLED,
            "IbetMembership": config.MEMBERSHIP_TOKEN_ENABLED,
            "IbetCoupon": config.COUPON_TOKEN_ENABLED
        }
