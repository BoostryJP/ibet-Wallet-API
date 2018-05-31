import falcon
from falcon import testing
from app.utils.hooks import verify_signature

class HandlerMock():
    @falcon.before(verify_signature)
    def on_post(self, req, resp):
        resp.body = "OK"
        resp.status = falcon.HTTP_200

class TestHooks():
    def test_verify_signature(self):
        app = falcon.API()
        app.add_route("/v1/Register", HandlerMock())

        cli = testing.TestClient(app)
        res = cli.simulate_post(
            "/v1/Register",
            params={
                'name': 'abcd',
                'password': 123,
            },
            headers={
                'X-ibet-Signature': '0x17ed8fde8f26cada2dcab1fff517b75c5f868971341b74d92cbb3f122b63dc9248f5394ef83a7d648a6ef470ec80bb4f8714c99933a8c96c94a0f6eed343405d1c',
            }
        )
        assert res.status_code == 200
