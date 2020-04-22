class TestV2TokenABI():
    """
    Test Case for v2.token_abi.~~
    """

    # テスト対象API
    apiurl_base = '/v2/ABI'

    # ＜正常系1＞
    #   普通債券ABI取得
    def test_straightbondabi_normal(self, client, session, shared_contract):
        apiurl = self.apiurl_base + '/StraightBond'
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] is not None

    # ＜正常系2＞
    #   株式ABI取得
    def test_shareabi_normal(self, client, session, shared_contract):
        apiurl = self.apiurl_base + '/Share'
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] is not None

    # ＜正常系3＞
    #   会員権ABI取得
    def test_membershipabi_normal(self, client, session, shared_contract):
        apiurl = self.apiurl_base + '/Membership'
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] is not None

    # ＜正常系4＞
    #   クーポンABI取得
    def test_couponabi_normal(self, client, session, shared_contract):
        apiurl = self.apiurl_base + '/Coupon'
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] is not None

    # ＜異常系＞
    #   存在しないABI
    def test_couponabi_normal(self, client, session, shared_contract):
        apiurl = self.apiurl_base + '/Unknown'
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 404