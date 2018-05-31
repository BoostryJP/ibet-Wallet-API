import pytest
import falcon
from falcon import testing
from app.utils.hooks import VerifySignature
from app.middleware.translator import JSONTranslator
from app.errors import InvalidParameterError

class TestVerifySignature():
    class HandlerMock():
        @falcon.before(VerifySignature())
        def on_post(self, req, resp):
            resp.body = req.context["address"]
            resp.status = falcon.HTTP_200

    def setup_class(self):
        app = falcon.API(middleware=[JSONTranslator()])
        app.add_route("/v1/Register", TestVerifySignature.HandlerMock())
        self.cli = testing.TestClient(app)

    # <正常系1>
    # クエリ文字列あり、RequestBodyあり
    def test_verify_signature_1(self):
        res = self.cli.simulate_post(
            "/v1/Register",
            params={
                'password': 123,
                'name': 'abcd',
            },
            body='{"address": "Tokyo, Japan"}',
            headers={
                'Content-Type': 'application/json',
                'X-ibet-Signature': '0x17ed8fde8f26cada2dcab1fff517b75c5f868971341b74d92cbb3f122b63dc9248f5394ef83a7d648a6ef470ec80bb4f8714c99933a8c96c94a0f6eed343405d1c',
            }
        )
        
        assert res.status_code == 200
        assert res.text == "0xBE65f2024C1De5CCCe3b20e38Cf93a0A9Bcbbf8a"

    
    # <正常系2>
    # クエリ文字列あり、RequestBodyなし
    def test_verify_signature_2(self):
        res = self.cli.simulate_post(
            "/v1/Register",
            params={
                'password': 123,
                'name': 'abcd',
            },
            headers={
                'X-ibet-Signature': '0xb50a7a85e7def69e480a09e597fd4f62c5b79ac5b557d648cb9e1b99ee756bed0d1838b64ee9237e40ab2cb771768bdbd0c502c2db8294e968b36d905b35a9781b',
            }
        )
        
        assert res.status_code == 200
        assert res.text == "0xBE65f2024C1De5CCCe3b20e38Cf93a0A9Bcbbf8a"

    # <正常系3>
    # クエリ文字列なし、RequestBodyあり
    def test_verify_signature_3(self):
        res = self.cli.simulate_post(
            "/v1/Register",
            body='{"address": "Tokyo, Japan"}',
            headers={
                'Content-Type': 'application/json',
                'X-ibet-Signature': '0x88082776c6ea43c3e3dcc9cf1c523d74e373ecd170fb32d688415b3c5905d3562aa3e2a2cad77bffec938681d365beed2cbc0d54dfb08b6e974acb82fd5c27cc1c',
            }
        )
        
        assert res.status_code == 200
        assert res.text == "0xBE65f2024C1De5CCCe3b20e38Cf93a0A9Bcbbf8a"

    # <正常系4>
    # クエリ文字列なし、RequestBodyなし
    def test_verify_signature_4(self):
        res = self.cli.simulate_post(
            "/v1/Register",
            headers={
                'X-ibet-Signature': '0xaf7117049ab338ea7fa432439172a0e2f5cd02cec8d673dac6b7abc10b6c969c53d3f8846c452581ccdb8712607d9fe3da9fe7b64ee778d2233d29ea102b9d0a1b',
            }
        )
        
        assert res.status_code == 200
        assert res.text == "0xBE65f2024C1De5CCCe3b20e38Cf93a0A9Bcbbf8a"

    # <異常系1>
    # 署名が間違っている
    def test_verify_signature_error_1(self):
        res = self.cli.simulate_post(
            "/v1/Register",
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
        assert res.text != "0xBE65f2024C1De5CCCe3b20e38Cf93a0A9Bcbbf8a"
        
    # <異常系2>
    # 署名が空
    def test_verify_signature_error_2(self):
        with pytest.raises(InvalidParameterError):
            self.cli.simulate_post(
                "/v1/Register",
                params={
                    'password': 123,
                    'name': 'abcd',
                },
                body='{"address": "Tokyo, Japan"}',
                headers={
                    'Content-Type': 'application/json',
                }
            )
