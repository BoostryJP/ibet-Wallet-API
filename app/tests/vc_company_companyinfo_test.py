# -*- coding: utf-8 -*-

"""
発行会社情報参照API
/v1/Company/{eth_address}
"""


class TestV1CompanyCompanyInfo:
    # テスト対象API
    apiurl_base = '/v1/Company/'

    # 正常系1-1： 発行会社リストに指定したアドレスの情報が存在
    def test_normal_1_1(self, client):
        eth_address = '0x29c35223e8b1fef8b4392bee0eee692de47b0205'
        apiurl = self.apiurl_base + eth_address

        resp = client.simulate_get(apiurl)
        assumed_body = {
            "address": "0x29c35223e8b1fef8b4392bee0eee692de47b0205",
            "corporate_name": "Dsa123",
            "enode": "d27f4b9e02e8482aece2ebcec72acc739d80e99ffdcae6bdc224ce309d23c23fccd09970aca5ba91304b4fea986d808bf018b8a4aada960f3e10be9b741b8cb1",
            "ip_address": "XXX.XXX.XXX.XXX",
            "rsa_publickey": "-----BEGIN PUBLIC KEY-----\nMIIFIjANBgkqhkiG9w0BAQEFAAOCBQ8AMIIFCgKCBQEAtiBUQ2vdYvIqnCdUzKIC\np7jIYVtJy8KGniy6ktE0DTcYG70pFYkGDyI043meSB6Lkk0rNWaKBn3wyz4lx2oX\n3JySFyXR4vE4DNTEKS0htImO4RuK4M50v7LOfB8VphXzu9JkdVuN8LuMx6L6dhsd\nTN/aUvXULvjOy9AJekl24s44w4BgEfGj/uBYNAmiNmpM3lnIdJOg1T+4aEShHyVN\n98dv1DZ1Hh0YhMmqHqRGIzAQ6pKoly2xSVEmwBV4l2O3XEZ8ErVNgHdi6BRQrIBl\n+zQn5TysSGv5TIO1ahztUIygrzX7aEa+QnF1ROBBJ8yBW0VjjKI2Oh3wDT8ROaWb\ntB7gYQlMX9St/HJvGKaDKPDGurMFsEZeeD9Y4GWlFFkQplKIC3Kr4u6TIxcAZyG3\ntIz1IZomm/Lh9eiFiAbOMLYPdPCzh1A6uCRoJuqrNXYbE2egpLsKSkEe4VAcdaPo\nVuOXLpbDaew0cvXQR5IklHGGPPGVqQV1cmJWIqF5b1bzqziu2No+TLZceUd3N9Eh\nQIYVG4rbX2I/x2/WFeG5RHl9Zc/iSUomUqpnGY3ved61smb7uklF/7ueyj8TIm7O\ncJxhYjj+szXxV2RJyxLvSPzloQ4GDI9wd0zlya2CoYgAONJ7wm82b1LrLLhfpns2\ndSsN8htFX83p0dNn6f8ssKgA3rFbFFnBTQyFxlHO/An4qZflXtk1GsEc56g3mJFp\nrFANLpyum5mkHo9TbkL3K4mRGM1DGcLXWJwFUjDxS/OvjzDXw2dNiyrPeClvTpAb\npFfw/zqVd7ZrnTFg26bpUmM8flc6IRji49veOOMM7jMJN7mmu/pLd/Pg22oez23G\n6QsPDvqqXgjyg1NGo7natX6gyAYMpWZWOHj+Y2lffzcJYUo+wPFt/xNkAuCcDZem\nAiicfsGfniE67G1nfmwkykVwk9rTFCO8SnFei8wMpEAMYETYOS4ldavLfhY6mrF1\nItA5mlkMI84v3ROqPSp3s6F9oGYzPi5zMcgc67wIFGgaPb6i8+puui6BUbj83qOU\nKuKoQAGe9+NRnAkWSpbX07cX6XkPieTkBHEYfGaQTQOnsSs++PIk3kH5Arfjk0R5\nu1ZluzVdOXUn8D5WPfh9UFzqyXzo1HOIHxDkPejpPlNzO1w6qVQC+UiR/R2iug/U\n7StoLz476tQOwbfmnzUA6AbOKjRgN5laRoBac4BbGPJisGysOBruL7lgrw0XVtnh\nknChXfSYezxz/EtiGmO40HKAGudHDkz4gmPDkF4wlIyfDbQZOnNohz4zuOjr9Yi/\nJQVpqKxug2LXyJp38UaxL1LIT6ZyJSsaSrKAB21tsYAbksyPCVS6L6jkz8lsnlYg\nLj7lj6HQcbN8WO72+Z8Ddj/cPXJwEq4OTbtkPiPdcvSZjcBR9f3TmrQjDG0ROspt\nI/m4KhWfm7ed+eZKA1IqygFRyi6i0w6p+VbeBNgXqAiQI5GkDHqAiqv4OVyZoQB8\neunu5qM49r6bw6DJCqlg6lZDCptdKWtNBo9zgEegrJ/3oVI7x0kE7KQ4gPo5uY7j\nvBqGwjw0fIGPjrP/JKIQqGvm/ETwlfPwVbmCsvEHbqEY+6f84TnmolgjPMnbar6Q\nSDuvqVApY7yNCEue5X0pLRAd+287VBVVvsOsZVOSj02w4PGIlsg2Y33BbcpwESzr\n4McG/dPyTRFv9mYtFPpyV50CAwEAAQ==\n-----END PUBLIC KEY-----",
            "homepage": "https://www.aaaa.com/jp/"
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # エラー系1-1： 発行会社リストに指定したアドレスの情報が存在しない
    def test_error_1_1(self, client):
        eth_address = '0x865de50bb0f21c3f318b736c04d2b6ff7dea3bf1'
        apiurl = self.apiurl_base + eth_address

        resp = client.simulate_get(apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": "eth_address: " + eth_address
        }

    # エラー系2-1： 無効なアドレス
    def test_error_2_1(self, client):
        eth_address = '0x865de50bb0f21c3f318b736c04d2b6ff7dea3bf'  # アドレスが短い
        apiurl = self.apiurl_base + eth_address

        resp = client.simulate_get(apiurl)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "invalid eth_address"
        }
