# -*- coding: utf-8 -*-

import falcon
from web3.auto import w3
from eth_account.messages import defunct_hash_message
from .signature import create_canonical_request

HEADER_SIGNATURE_KEY = "X-ibet-Signature"
def verify_signature(req, resp, resource, params):
    # リクエスト情報の取得
    method = req.method
    request_path = req.path
    query_string = ""
    if len(req.query_string) > 0:
        query_string = "?" + req.query_string
    request_body = ""
    if "raw_data" in req.context:
        request_body = req.context["raw_data"]
    
    signature = req.get_header(HEADER_SIGNATURE_KEY, default="")
    
    canonical_request = create_canonical_request(
        method=method,
        request_path=request_path,
        query_string=query_string,
        request_body=request_body,
    )
    print(canonical_request)

    # 署名の検証
    req.context["address"] = w3.eth.account.recoverHash(
        defunct_hash_message(text=canonical_request),
        signature=signature,
    )
