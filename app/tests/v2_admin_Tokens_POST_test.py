# -*- coding: utf-8 -*-
import json

from app.model import Listing, ExecutableContract


class TestAdminTokensPOST:
    # テスト対象API
    apiurl = '/v2/Admin/Tokens'

    token_1 = {
        "contract_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
        "is_public": True,
        "max_holding_quantity": 100,
        "max_sell_amount": 50000,
        "owner_address": "0x56f63dc2351BeC560a429f0C646d64Ca718e11D6"
    }

    token_2 = {
        "contract_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
        "is_public": True,
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
        request_params = self.token_1
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        listing = session.query(Listing). \
            filter(Listing.token_address == self.token_1["contract_address"]). \
            first()
        assert listing.token_address == self.token_1["contract_address"]
        assert listing.is_public == self.token_1["is_public"]
        assert listing.max_holding_quantity == self.token_1["max_holding_quantity"]
        assert listing.max_sell_amount == self.token_1["max_sell_amount"]
        assert listing.owner_address == self.token_1["owner_address"]

        executable_contract = session.query(ExecutableContract). \
            filter(ExecutableContract.contract_address == self.token_1["contract_address"]). \
            first()
        assert executable_contract.contract_address == self.token_1["contract_address"]

    # <Normal_2>
    # 任意設定項目なし
    def test_normal_2(self, client, session):
        request_params = self.token_2
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        listing = session.query(Listing). \
            filter(Listing.token_address == self.token_2["contract_address"]). \
            first()
        assert listing.token_address == self.token_2["contract_address"]
        assert listing.is_public == self.token_2["is_public"]
        assert listing.max_holding_quantity is None
        assert listing.max_sell_amount is None
        assert listing.owner_address == self.token_2["owner_address"]

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # headersなし
    # 400（InvalidParameterError）
    def test_error_1(self, client, session):
        request_params = self.token_1
        headers = {}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜Error_2＞
    # 入力値なし
    # 400（InvalidParameterError）
    def test_error_2(self, client, session):
        request_params = {}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'contract_address': 'required field',
                'is_public': 'required field',
                'owner_address': 'required field'
            }
        }

    # ＜Error_3_1＞
    # contract_addressのフォーマット誤り
    # 400（InvalidParameterError）
    def test_error_3_1(self, client, session):
        request_params = {
            "contract_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7",  # アドレスが短い
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "owner_address": "0x56f63dc2351BeC560a429f0C646d64Ca718e11D6"
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'Invalid contract address'
        }

    # ＜Error_3_2＞
    # owner_addressのフォーマット誤り
    # 400（InvalidParameterError）
    def test_error_3_2(self, client, session):
        request_params = {
            "contract_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "owner_address": "0x56f63dc2351BeC560a429f0C646d64Ca718e11D"  # アドレスが短い
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'Invalid owner address'
        }

    # ＜Error_3_3＞
    # 入力値の型誤り
    # 400（InvalidParameterError）
    def test_error_3_3(self, client, session):
        request_params = {
            "contract_address": 1234,
            "is_public": "True",
            "max_holding_quantity": "100",
            "max_sell_amount": "50000",
            "owner_address": 1234
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'contract_address': 'must be of string type',
                'is_public': 'must be of boolean type',
                'max_holding_quantity': 'must be of integer type',
                'max_sell_amount': 'must be of integer type',
                'owner_address': 'must be of string type'
            }
        }

    # <Error_4>
    # 指定のcontract_addressのレコードが listing テーブルに既に登録済
    def test_error_4(self, client, session):
        token = {
            "token_address": self.token_1["contract_address"],
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "owner_address": "0x56f63dc2351BeC560a429f0C646d64Ca718e11D6"
        }
        self.insert_listing_data(session, token)

        request_params = self.token_1
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'contract_address already exist'
        }

    # <Error_5>
    # 指定のcontract_addressのレコードが executable_contract テーブルに既に登録済
    def test_error_5(self, client, session):
        contract = {
            "contract_address": self.token_1["contract_address"],
        }
        self.insert_executable_contract_data(session, contract)

        request_params = self.token_1
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'contract_address already exist'
        }
