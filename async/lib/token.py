import json
from app.contracts import Contract

class TokenFactory:
    def __init__(self, web3):
        self.web3 = web3

    def get_straight_bond(self, address):
        contract = Contract.get_contract('IbetStraightBond', address)
        return Token(contract)

    def get_share(self, address):
        contract = Contract.get_contract('IbetShare', address)
        return Token(contract)

    def get_membership(self, address):
        contract = Contract.get_contract('IbetMembership', address)
        return Token(contract)

    def get_coupon(self, address):
        contract = Contract.get_contract('IbetCoupon', address)
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
