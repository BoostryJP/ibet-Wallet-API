class TokenList:
    def __init__(self, contract):
        self.contract = contract

    def is_registered(self, address):
        res = self.contract.functions.getTokenByAddress(address).call()
        return not (res[0] == "0x0000000000000000000000000000000000000000")
        
