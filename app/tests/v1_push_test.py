import boto3
from botocore.exceptions import ClientError

from app.model import Push
from datetime import datetime
from app import config
from app import log
LOG = log.get_logger()

class TestV1Push():
    # テスト対象API
    url_UpdateDevice = "/v1/Push/UpdateDevice"
    url_DeleteDevice = "/v1/Push/DeleteDevice"

    private_key = "0000000000000000000000000000000000000000000000000000000000000001"
    address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    private_key_2 = "0000000000000000000000000000000000000000000000000000000000000002"
    address_2 = "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF"

    upd_data_1 = {
        "device_id": "25D451DF-7BC1-63AD-A267-678ACDC1D10F",
        "device_token": "65ae6c04ebcb60f1547980c6e42921139cc95251d484657e40bb571ecceb2c28",
    }
    upd_data_2 = {
        "device_id": "25D451DF-7BC1-63AD-A267-678ACDC1D10F",
        "device_token": "65ae6c04ebcb60f1547980c6e42921139cc95251d484657e40bb571ecceb2c29",
    }
    del_data_1 = {
        "device_id": "25D451DF-7BC1-63AD-A267-678ACDC1D10F"
    }

    # 最初のケースだけ設定変更
    def test_setup(self, client):
        config.DB_AUTOCOMMIT = True
        assert True

    # ＜正常系1_1＞
    # device token新規登録
    def test_normal_1_1(self, client, session):
        resp = client.simulate_auth_post(self.url_UpdateDevice,
            json=self.upd_data_1,
            private_key=self.private_key)

        # DB確認
        query = session.query(Push). \
            filter(Push.device_id == self.upd_data_1['device_id'])
        tmpdata = query.first()
        assert resp.status_code == 200
        assert tmpdata.device_id == self.upd_data_1['device_id']
        assert tmpdata.device_token == self.upd_data_1['device_token']
        assert tmpdata.account_address == self.address

        # SNS確認
        client = boto3.client('sns')
        response = client.get_endpoint_attributes(
            EndpointArn=tmpdata.device_endpoint_arn
        )
        assert response is not None

    # ＜正常系1_2＞
    # device token更新登録(トークン変更))
    def test_normal_1_2(self, client, session):
        resp = client.simulate_auth_post(self.url_UpdateDevice,
            json=self.upd_data_2,
            private_key=self.private_key)

        # DB確認
        query = session.query(Push). \
            filter(Push.device_id == self.upd_data_2['device_id'])
        tmpdata = query.first()
        assert resp.status_code == 200
        assert tmpdata.device_id == self.upd_data_2['device_id']
        assert tmpdata.device_token == self.upd_data_2['device_token']
        assert tmpdata.account_address == self.address

        # SNS確認
        client = boto3.client('sns')
        response = client.get_endpoint_attributes(
            EndpointArn=tmpdata.device_endpoint_arn
        )
        assert response is not None

    # ＜正常系1_3＞
    # device token更新登録(eth address変更)))
    def test_normal_1_3(self, client, session):
        resp = client.simulate_auth_post(self.url_UpdateDevice,
            json=self.upd_data_2,
            private_key=self.private_key_2)

        # DB確認
        query = session.query(Push). \
            filter(Push.device_id == self.upd_data_2['device_id'])
        tmpdata = query.first()
        assert resp.status_code == 200
        assert tmpdata.device_id == self.upd_data_2['device_id']
        assert tmpdata.device_token == self.upd_data_2['device_token']
        assert tmpdata.account_address == self.address_2

        # SNS確認
        client = boto3.client('sns')
        response = client.get_endpoint_attributes(
            EndpointArn=tmpdata.device_endpoint_arn
        )
        assert response is not None

    # ＜正常系2_1＞
    # device token削除
    def test_normal_2_1(self, client, session):
        # 削除するARNの取得
        query = session.query(Push). \
            filter(Push.device_id == self.del_data_1['device_id'])
        tmpdata = query.first()
        device_endpoint_arn = tmpdata.device_endpoint_arn

        # 削除リクエスト
        resp = client.simulate_auth_post(self.url_DeleteDevice,
        json=self.del_data_1,
        private_key=self.private_key)

        # DB確認
        query = session.query(Push). \
            filter(Push.device_id == self.del_data_1['device_id'])
        tmpdata = query.first()
        assert resp.status_code == 200
        assert tmpdata is None

        # SNS確認
        flag = False
        client = boto3.client('sns')
        try:
            client.get_endpoint_attributes(
                EndpointArn=device_endpoint_arn
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFound':
                flag = True
        assert flag

    # ＜エラー系1_1＞
    # 【UpdateDevice】存在しないdevice tokenを削除
    # DBには存在するが、SNSには存在しない
    def test_error_1_1(self, client, session):
        # 存在しないデータを登録
        device_data = Push()
        device_data.device_id = self.del_data_1['device_id']
        device_data.account_address = self.address
        device_data.device_token = self.upd_data_1['device_token']
        device_data.device_endpoint_arn = 'arn:aws:sns:ap-northeast-1:241627671680:endpoint/APNS_SANDBOX/ionpush/50847470-27dd-3bc7-9768-fb31c1ff93b4'
        session.add(device_data)
        session.commit()

        # 更新リクエスト
        resp = client.simulate_auth_post(self.url_UpdateDevice,
            json=self.upd_data_2,
            private_key=self.private_key)

        assert resp.status_code == 404
        assert resp.json["meta"] ==  {
            'code': 50,
            'message': 'SNS NotFoundError'
        }

        # DBが更新されていないことを確認
        query = session.query(Push). \
            filter(Push.device_id == self.del_data_1['device_id'])
        tmpdata = query.first()
        assert tmpdata.device_token != self.upd_data_2['device_token']
 
    # ＜エラー系1_3＞
    # 【DeleteDevice】存在しないdevice tokenを削除
    # DBには存在するが、SNSには存在しない
    def test_error_1_3(self, client, session):
        # 存在しないデータを登録
        device_data = Push()
        device_data.device_id = self.del_data_1['device_id']
        device_data.account_address = self.address
        device_data.device_token = self.upd_data_1['device_token']
        device_data.device_endpoint_arn = 'arn:aws:sns:ap-northeast-1:241627671680:endpoint/APNS_SANDBOX/ionpush/50847470-27dd-3bc7-9768-fb31c1ff93b4'
        session.add(device_data)
        session.commit()

        # 削除リクエスト
        resp = client.simulate_auth_post(self.url_DeleteDevice,
            json=self.del_data_1,
            private_key=self.private_key)

        assert resp.status_code == 404
        assert resp.json["meta"] ==  {
            'code': 50,
            'message': 'SNS NotFoundError'
        }
    
    # ＜エラー系2-1＞
    # 【UpdateDevice】ヘッダー（Signature）なし
    def test_error_2_1(self, client, session):
        resp = client.simulate_post(
            self.url_UpdateDevice
        )
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'signature is empty'
        }

    # ＜エラー系2-2＞
    # 【DeleteDevice】ヘッダー（Signature）なし
    def test_error_2_2(self, client, session):
        resp = client.simulate_post(
            self.url_DeleteDevice
        )
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'signature is empty'
        }

    # ＜エラー系3-1＞
    # 【UpdateDevice】必須項目なし：device_id
    def test_error_3_1(self, client, session):
        resp = client.simulate_auth_post(
            self.url_UpdateDevice,
            json={
                "device_token": "65ae6c04ebcb60f1547980c6e42921139cc95251d484657e40bb571ecceb2c28",
            },
            private_key=self.private_key
        )
        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'device_id': 'required field'
            }
        }

    # ＜エラー系3-2＞
    # 【UpdateDevice】必須項目なし：device_token
    def test_error_3_2(self, client, session):
        resp = client.simulate_auth_post(
            self.url_UpdateDevice,
            json={
                "device_id": "25D451DF-7BC1-63AD-A267-678ACDC1D10F"
            },
            private_key=self.private_key
        )
        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'device_token': 'required field'
            }
        }

    # ＜エラー系3-3＞
    # 【DeleteDevice】必須項目なし：device_id
    def test_error_3_3(self, client, session):
        resp = client.simulate_auth_post(
            self.url_DeleteDevice,
            json={},
            private_key=self.private_key
        )
        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'device_id': 'required field'
            }
        }

    # ＜エラー系3-4＞
    # 【UpdateDevice】空白：device_id
    def test_error_3_4(self, client, session):
        resp = client.simulate_auth_post(
            self.url_UpdateDevice,
            json = {
                "device_id": "",
                "device_token": "65ae6c04ebcb60f1547980c6e42921139cc95251d484657e40bb571ecceb2c28",
            },
            private_key = self.private_key
        )
        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'device_id': 'empty values not allowed'
            }
        }

    # ＜エラー系3-5＞
    # 【UpdateDevice】空白：device_token
    def test_error_3_5(self, client, session):
        resp = client.simulate_auth_post(
            self.url_UpdateDevice,
            json = {
                "device_id": "25D451DF-7BC1-63AD-A267-678ACDC1D10F",
                "device_token": "",
            },
            private_key = self.private_key
        )
        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'device_token': 'empty values not allowed'
            }
        }

    # ＜エラー系3-6＞
    # 【DeleteDevice】空白：device_id
    def test_error_3_6(self, client, session):
        resp = client.simulate_auth_post(
            self.url_DeleteDevice,
            json = {
                "device_id": ""
            },
            private_key = self.private_key
        )
        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'device_id': 'empty values not allowed'
            }
        }

    # ＜エラー系3-7＞
    # 【UpdateDevice】数字：device_id
    def test_error_3_7(self, client, session):
        resp = client.simulate_auth_post(
            self.url_UpdateDevice,
            json = {
                "device_id": 1234,
                "device_token": "65ae6c04ebcb60f1547980c6e42921139cc95251d484657e40bb571ecceb2c28",
            },
            private_key = self.private_key
        )
        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'device_id': 'must be of string type'
            }
        }

    # ＜エラー系3-8＞
    # 【UpdateDevice】数字：device_token
    def test_error_3_8(self, client, session):
        resp = client.simulate_auth_post(
            self.url_UpdateDevice,
            json = {
                "device_id": "25D451DF-7BC1-63AD-A267-678ACDC1D10F",
                "device_token": 1234,
            },
            private_key = self.private_key
        )
        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'device_token': 'must be of string type'
            }
        }

    # ＜エラー系3-9＞
    # 【DeleteDevice】数字：device_id
    def test_error_3_9(self, client, session):
        resp = client.simulate_auth_post(
            self.url_DeleteDevice,
            json = {
                "device_id": 1234,
            },
            private_key = self.private_key
        )
        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'device_id': 'must be of string type'
            }
        }

    # 最後のケース　設定変更
    def test_teardown(self, client):
        config.DB_AUTOCOMMIT = False
        assert True
