# -*- coding: utf-8 -*-
import json

from app.model import Listing, ExecutableContract


class TestAdminTokenPOST:
    # テスト対象API
    apiurl_base = '/v2/Admin/Token/'

    default_token = {
        "token_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
        "is_public": True,
        "max_holding_quantity": 100,
        "max_sell_amount": 50000,
        "owner_address": "0x56f63dc2351BeC560a429f0C646d64Ca718e11D6"
    }

    @staticmethod
    def insert_listing_data(session, _token):
        token = Listing()
        token.token_address = _token["token_address"]
        token.is_public = _token["is_public"]
        token.max_holding_quantity = _token["max_holding_quantity"]
        token.max_sell_amount = _token["max_sell_amount"]
        token.owner_address = _token["owner_address"]
        session.add(token)

    @staticmethod
    def insert_executable_contract_data(session, _contract):
        contract = ExecutableContract()
        contract.contract_address = _contract["contract_address"]
        session.add(contract)

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client, session):
        token = self.default_token
        self.insert_listing_data(session, token)

        request_params = {
            "is_public": False,
            "max_holding_quantity": 200,
            "max_sell_amount": 25000,
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D660590"
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + token["token_address"]
        resp = client.simulate_post(apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        listing = session.query(Listing). \
            filter(Listing.token_address == token["token_address"]). \
            first()
        assert listing.token_address == token["token_address"]
        assert listing.is_public == request_params["is_public"]
        assert listing.max_holding_quantity == request_params["max_holding_quantity"]
        assert listing.max_sell_amount == request_params["max_sell_amount"]
        assert listing.owner_address == request_params["owner_address"]


    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # headersなし
    # 400（InvalidParameterError）
    def test_error_1(self, client, session):
        request_params = {
            "is_public": False,
            "max_holding_quantity": 200,
            "max_sell_amount": 25000,
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D660590"
        }
        headers = {}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + self.default_token["token_address"]
        resp = client.simulate_post(apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜Error_2_1＞
    # contract_addressのフォーマット誤り
    # 400（InvalidParameterError）
    def test_error_2_1(self, client, session):
        request_params = {
            "is_public": False,
            "max_holding_quantity": 200,
            "max_sell_amount": 25000,
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D660590"
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7"  # アドレスが短い
        resp = client.simulate_post(apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'Invalid contract address'
        }

    # ＜Error_2_2＞
    # owner_addressのフォーマット誤り
    # 400（InvalidParameterError）
    def test_error_2_2(self, client, session):
        request_params = {
            "is_public": False,
            "max_holding_quantity": 200,
            "max_sell_amount": 25000,
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D66059"  # アドレスが短い
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + self.default_token["token_address"]
        resp = client.simulate_post(apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'Invalid owner address'
        }

    # ＜Error_2_3＞
    # 入力値の型誤り
    # 400（InvalidParameterError）
    def test_error_2_3(self, client, session):
        request_params = {
            "is_public": "False",
            "max_holding_quantity": "200",
            "max_sell_amount": "25000",
            "owner_address": 1234
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + self.default_token["token_address"]
        resp = client.simulate_post(apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'is_public': 'must be of boolean type',
                'max_holding_quantity': 'must be of integer type',
                'max_sell_amount': 'must be of integer type',
                'owner_address': 'must be of string type'
            }
        }

    # <Error_3>
    # 更新対象のレコードが存在しない
    # 404
    def test_error_3(self, client, session):
        request_params = {
            "is_public": False,
            "max_holding_quantity": 200,
            "max_sell_amount": 25000,
            "owner_address": "0x34C987DDe783EfbFe1E573727165E6c15D660590"
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        apiurl = self.apiurl_base + self.default_token["token_address"]
        resp = client.simulate_post(apiurl, headers=headers, body=request_body)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 30,
            'message': 'Data Not Exists',
            'description': 'Record does not exist'
        }
