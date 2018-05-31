import pytest

from app.utils.signature import create_canonical_request

class TestSignature():
    # <正常系>
    def test_create_canonical_request(self):
        method = "POST"
        request_path = "/v1/Register"
        query_string = "?name=abcd&password=123"
        request_body = '{"address": "Tokyo, Japan"}'

        canonical_request = "POST\n/v1/Register\n?name=abcd&password=123\n0x52ad0e3321005743b6b295527ce806c16182efad29b51aa219a500a4ffdcc869"
        assert create_canonical_request(
            method=method,
            request_path=request_path,
            query_string=query_string,
            request_body=request_body
        ) == canonical_request


