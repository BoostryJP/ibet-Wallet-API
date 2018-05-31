# Signature verification methods
# Specification: https://github.com/N-Village/tmr-node/issues/103

from web3 import Web3

def create_canonical_request(method, request_path, query_string = "", request_body = ""):
    request_body_hash = Web3.sha3(text=request_body).hex()
    canoncal_request = method + "\n" +\
                       request_path + "\n"+\
                       query_string + "\n"+\
                       request_body_hash
    return canoncal_request

