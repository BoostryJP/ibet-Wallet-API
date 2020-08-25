# -*- coding: utf-8 -*-
from app.model import Listing, ExecutableContract


class TestAdminTokensDELETE:
    # テスト対象API
    apiurl_base = '/v2/Admin/Token/'

    @staticmethod
    def insert_listing_data(session, _token):
        token = Listing()
        token.token_address = _token["token_address"]
        token.is_public = _token["is_public"]
        token.max_holding_quantity = _token["max_holding_quantity"]
        token.max_sell_amount = _token["max_sell_amount"]
        token.owner_address = _token["owner_address"]
        session.add(token)

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, session):
        token = {
            "token_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "owner_address": "0x56f63dc2351BeC560a429f0C646d64Ca718e11D6"
        }
        self.insert_listing_data(session, token)

        apiurl = self.apiurl_base + token["token_address"]
        resp = client.simulate_delete(apiurl)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        listing = session.query(Listing).\
            filter(Listing.token_address == token["token_address"]).\
            all()
        assert listing == []

        executable_contract = session.query(ExecutableContract). \
            filter(ExecutableContract.contract_address == token["token_address"]). \
            all()
        assert executable_contract == []
