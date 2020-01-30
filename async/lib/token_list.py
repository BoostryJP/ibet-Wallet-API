class TokenList:
    def __init__(self, contract):
        self.contract = contract

    def is_registered(self, address):
        res = self.contract.functions.getTokenByAddress(address).call()
        return not (res[0] == "0x0000000000000000000000000000000000000000")

    def get_token(self, address):
        res = self.contract.functions.getTokenByAddress(address).call()  # token_address, token_template, owner_address
        return res
