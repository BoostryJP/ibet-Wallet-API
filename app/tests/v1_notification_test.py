class TestV1Notification():
    # テスト対象API
    apiurl = "/v1/Notifications"

    accounts = [

    ]
    private_key = "0000000000000000000000000000000000000000000000000000000000000001"
    address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    def test_notification_normal_1(self, client, session):
        resp = client.simulate_auth_get(self.apiurl, private_key=TestV1Notification.private_key)
        assert resp.status_code == 200
