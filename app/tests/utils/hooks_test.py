import pytest
import falcon
from falcon import testing
from app.utils.hooks import VerifySignature
from app.middleware.translator import JSONTranslator
from app.errors import InvalidParameterError


class TestVerifySignature:

    apiurl = "/v1/Register"
    private_key = "0000000000000000000000000000000000000000000000000000000000000001"
    address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

    class HandlerMock:
        @falcon.before(VerifySignature())
        def on_post(self, req, resp):
            resp.body = req.context["address"]
            resp.status = falcon.HTTP_200

    def setup_class(self):
        app = falcon.API(middleware=[JSONTranslator()])
        app.add_route(self.apiurl, TestVerifySignature.HandlerMock())
        self.cli = testing.TestClient(app)

    # <正常系1>
    # クエリ文字列あり、RequestBodyあり
    def test_verify_signature_1(self, client):
        signature = client.generate_ibet_signature(
            self.apiurl,
            private_key=TestVerifySignature.private_key,
            params={'password':'123','name':'abcd'},
            json={"address":"Tokyo, Japan"}  # NOTE:空白なしのJSONフォーマット
        )

        res = self.cli.simulate_post(
            self.apiurl,
            params={
                'password': 123,
                'name': 'abcd',
            },
            body='{"address":"Tokyo, Japan"}',  # NOTE:空白なしのJSONフォーマット
            headers={
                'Content-Type': 'application/json',
                'X-ibet-Signature': signature,
            }
        )

        assert res.status_code == 200
        assert res.text == self.address

    # <正常系2>
    # クエリ文字列あり、RequestBodyなし
    def test_verify_signature_2(self, client):
        signature = client.generate_ibet_signature(
            self.apiurl,
            private_key=TestVerifySignature.private_key,
            params={'password':'123','name':'abcd'}
        )

        res = self.cli.simulate_post(
            self.apiurl,
            params={
                'password': 123,
                'name': 'abcd',
            },
            headers={
                'X-ibet-Signature': signature,
            }
        )

        assert res.status_code == 200
        assert res.text == self.address

    # <正常系3>
    # クエリ文字列なし、RequestBodyあり
    def test_verify_signature_3(self, client):
        signature = client.generate_ibet_signature(
            self.apiurl,
            private_key=TestVerifySignature.private_key,
            json={"address":"Tokyo, Japan"}  # NOTE:空白なしのJSONフォーマット
        )

        res = self.cli.simulate_post(
            self.apiurl,
            body='{"address":"Tokyo, Japan"}',  # NOTE:空白なしのJSONフォーマット
            headers={
                'Content-Type': 'application/json',
                'X-ibet-Signature': signature,
            }
        )

        assert res.status_code == 200
        assert res.text == self.address

    # <正常系4>
    # クエリ文字列なし、RequestBodyなし
    def test_verify_signature_4(self, client):
        signature = client.generate_ibet_signature(
            self.apiurl,
            private_key=TestVerifySignature.private_key
        )

        res = self.cli.simulate_post(
            self.apiurl,
            headers={
                'X-ibet-Signature': signature
            }
        )

        assert res.status_code == 200
        assert res.text == self.address

    # <異常系1>
    # 署名が間違っている
    def test_verify_signature_error_1(self):
        res = self.cli.simulate_post(
            self.apiurl,
            params={
                'password': 123,
                'name': 'abcd',
            },
            body='{"address": "Tokyo, Japan"}',
            headers={
                'Content-Type': 'application/json',
                'X-ibet-Signature': '0xaf7117049ab338ea7fa432439172a0e2f5cd02cec8d673dac6b7abc10b6c969c53d3f8846c452581ccdb8712607d9fe3da9fe7b64ee778d2233d29ea102b9d0a1b',
            }
        )

        assert res.status_code == 200
        assert res.text != self.address

    # <異常系2>
    # 署名が空
    def test_verify_signature_error_2(self):
        with pytest.raises(InvalidParameterError):
            self.cli.simulate_post(
                self.apiurl,
                params={
                    'password': 123,
                    'name': 'abcd',
                },
                body='{"address":"Tokyo, Japan"}',
                headers={
                    'Content-Type': 'application/json',
                }
            )

    # <異常系3
    # 署名のフォーマットが不正
    def test_verify_signature_error_3(self):
        with pytest.raises(InvalidParameterError):
            self.cli.simulate_post(
                self.apiurl,
                params={
                    'password': 123,
                    'name': 'abcd',
                },
                body='{"address":"Tokyo, Japan"}',
                headers={
                    'Content-Type': 'application/json',
                    'X-ibet-Signature': '0xaf7117049ab338ea7f',
                }
            )
