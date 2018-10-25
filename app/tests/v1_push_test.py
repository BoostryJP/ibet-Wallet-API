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
        "device_id": "aiueoaiui",
        "device_token": "65ae6c04ebcb60f1547980c6e42921139cc95251d484657e40bb571ecceb2c28",
    }
    upd_data_2 = {
        "device_id": "aiueoaiui",
        "device_token": "65ae6c04ebcb60f1547980c6e42921139cc95251d484657e40bb571ecceb2c29",
    }
    del_data_1 = {
        "device_id": "aiueoaiui"
    }

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
        flag = Flase
        client = boto3.client('sns')
        try:
            response = client.get_endpoint_attributes(
                EndpointArn=device_endpoint_arn
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                flag = True
        assert flag
