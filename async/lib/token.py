import json
from app import config

class TokenFactory:
    def __init__(self, web3):
        self.web3 = web3

    def get_straight_bond(self, address):
        abi = json.loads(config.STRAIGHT_BOND_ABI["abi"])
        contract = self.web3.eth.contract(
            address = address,
            abi = abi,
        )
        return Token(contract)

class Token:
    def __init__(self, contract):
        self.contract = contract

    @property
    def name(self):
        return self.contract.functions.name().call()


    @property
    def owner_address(self):
        return self.contract.functions.owner().call()
