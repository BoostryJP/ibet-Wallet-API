from app.model import Push
from datetime import datetime

from app import log
LOG = log.get_logger()

class TestV1Push():
    # テスト対象API
    apiurl = "/v1/Push/UpdateDevice"

    private_key = "0000000000000000000000000000000000000000000000000000000000000001"
    address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    def _insert_test_data(self, session):
        p = Push()
        p.device_id = "tanmatukoyuuid"
        p.account_address = self.address
        p.device_token = "aaa"
        p.device_endpoint_arn = "aaa"
        session.add(p)

    # ＜正常系1_1＞
    # device token新規登録
    def test_normal_1_1(self, client, session):
        resp = client.simulate_auth_post(self.apiurl,
            json={
                "device_id": "aiueoaiui",
                "device_token": "aiueo",
            },
            private_key=self.private_key)
        LOG.debug(resp.json)

        assert resp.status_code == 200

