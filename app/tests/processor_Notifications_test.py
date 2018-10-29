import boto3
from botocore.exceptions import ClientError
from app.model import Push
from datetime import datetime
from app import config
from .account_config import eth_account
from .contract_modules import issue_bond_token, offer_bond_token, \
    register_personalinfo, register_whitelist, take_buy_bond_token, get_latest_orderid, \
    membership_issue, membership_offer, membership_get_latest_orderid, \
    membership_take_buy
from app import log
from async.processor_Notifications import WatchWhiteListRegister
LOG = log.get_logger()

class TestProcessorNotifications():
    url_UpdateDevice = "/v1/Push/UpdateDevice"
    url_DeleteDevice = "/v1/Push/DeleteDevice"
    upd_data_1 = {
        "device_id": "25D451DF-7BC1-63AD-A267-678ACDC1D123",
        "device_token": "65ae6c04ebcb60f1547980c6e42921139cc95251d484657e40bb571ecceb2c28",
    }
    del_data_1 = {
        "device_id": "25D451DF-7BC1-63AD-A267-678ACDC1D123",
    }
    private_key = "0000000000000000000000000000000000000000000000000000000000000001"
    address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"


    # ＜正常系1_1＞
    # Push通知確認
    def test_normal_1_1(self, client, session, shared_contract):
        config.DB_AUTOCOMMIT = True
        config.WHITE_LIST_CONTRACT_ADDRESS = shared_contract['WhiteList']['address']
        trader = eth_account['trader']
        white_list = shared_contract['WhiteList']

        # push用デバイス登録
        resp = client.simulate_auth_post(self.url_UpdateDevice,
            json=self.upd_data_1,
            private_key=self.private_key)
        assert resp.status_code == 200

        # DBのaddressを書き換え
        query = session.query(Push). \
            filter(Push.device_id == self.upd_data_1['device_id'])
        tmpdata = query.first()
        tmpdata.account_address = trader['account_address']
        session.merge(tmpdata)
        session.commit()

        # whitelistの登録
        register_whitelist(trader, white_list)

        # # push検知
        wwr = WatchWhiteListRegister()
        wwr.loop()

        # sns endpointの削除
        resp = client.simulate_auth_post(self.url_DeleteDevice,
        json=self.upd_data_1,
        private_key=self.private_key)

        config.DB_AUTOCOMMIT = False
