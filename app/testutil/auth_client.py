import json as j

from falcon import testing
from web3.auto import w3
from eth_account.messages import defunct_hash_message


class TestAuthClient(testing.TestClient):
    HEADER_SIGNATURE_KEY = "X-ibet-Signature"

    def __init__(self, app):
        super(TestAuthClient, self).__init__(app)

    def _canonical_request(self, method, path, request_body, query_string):
        if request_body is None:
            request_body = j.dumps({}, separators=(",", ":"))

        if query_string != "":
            query_string = "?" + query_string

        request_body_hash = w3.sha3(text=request_body).hex()
        canonical_request = method + "\n" + \
                            path + "\n" + \
                            query_string + "\n" + \
                            request_body_hash

        return canonical_request

    def _generate_signature(self, private_key, **kwargs):
        canonical_request = self._canonical_request(**kwargs)
        message_hash = defunct_hash_message(text=canonical_request)
        signed_message = w3.eth.account.signHash(message_hash, private_key=private_key)
        return signed_message["signature"].hex()

    def _params_to_query_string(self, params):
        kvs = []
        for k, v in sorted(params.items()):
            kvs.append(k + "=" + v)

        if len(kvs) == 0:
            return ""
        return "&".join(kvs)

    def simulate_auth_get(self, path, private_key, params=None, query_string=None):
        if query_string is None:
            query_string = ""
        if not (params is None):
            query_string = self._params_to_query_string(params)

        signature = self._generate_signature(
            private_key, method="GET", path=path, request_body=None,
            query_string=query_string
        )
        return self.simulate_get(
            path, params=params, query_string=query_string,
            headers={TestAuthClient.HEADER_SIGNATURE_KEY: signature}
        )

    def simulate_auth_post(self, path, private_key, body=None, json=None):
        canonical_body = body
        if not (json is None):
            canonical_body = j.dumps(json, separators=(",", ":"))

        signature = self._generate_signature(
            private_key, method="POST", path=path, request_body=canonical_body,
            query_string=""
        )
        return self.simulate_post(
            path, body=body, json=json,
            headers={TestAuthClient.HEADER_SIGNATURE_KEY: signature}
        )

    def generate_ibet_signature(self, path, private_key, params=None, json=None):
        query_string = ""
        request_body = None
        if params is not None:
            query_string = self._params_to_query_string(params)
        if json is not None:
            request_body = j.dumps(json, separators=(",", ":"))

        signature = self._generate_signature(
            private_key, method="POST", path=path,
            request_body=request_body,
            query_string=query_string
        )
        return signature
