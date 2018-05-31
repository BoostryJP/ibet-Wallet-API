# -*- coding: utf-8 -*-

import falcon
from web3.auto import w3
from eth_account.messages import defunct_hash_message
from .signature import create_canonical_request
from app.errors import InvalidParameterError

class VerifySignature(object):
    """
    署名検証及び認証を行うHookです
    リクエストの署名を検証し、req.context["address"]にアドレスを格納します。
    """
    
    HEADER_SIGNATURE_KEY = "X-ibet-Signature"
    
    def _get_request_body(self, req):
        if "raw_data" in req.context:
            return req.context["raw_data"]
        return "{}"

    def _get_query_string(self, req):
        kvs = []
        for k, v in sorted(req.params.items()):
            kvs.append(k + "=" + v)

        if len(kvs) == 0:
            return ""
        return "?" + "&".join(kvs)
            
    def _canonical_request(self, req):
        request_body = self._get_request_body(req)
        request_body_hash = w3.sha3(text=request_body).hex()
        canonical_request = req.method + "\n" +\
                            req.path + "\n" +\
                            self._get_query_string(req) + "\n" +\
                            request_body_hash
        return canonical_request

    def __call__(self, req, resp, resource, params):
        signature = req.get_header(VerifySignature.HEADER_SIGNATURE_KEY)
        if signature is None:
            raise InvalidParameterError("signature is empty")

        canonical_request = self._canonical_request(req)

        req.context["address"] = w3.eth.account.recoverHash(
            defunct_hash_message(text=canonical_request),
            signature=signature,
        )
