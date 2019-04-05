# -*- coding: utf-8 -*-

class TokenBase():
    tokenAddress: str
    tokenTemplate: str
    ownerAddress: str
    companyName: str
    rsaPublickey: str
    name: str
    symbol: str
    totalSupply: str
    imageUrl: object
    creditCardAvailability: bool
    bankPaymentAvailability: bool

class BondToken(TokenBase):
    faceValue: str
    interestRate: str
    interestPaymentDate1: str
    interestPaymentDate2: str
    interestPaymentDate3: str
    interestPaymentDate4: str
    interestPaymentDate5: str
    interestPaymentDate6: str
    interestPaymentDate7: str
    interestPaymentDate8: str
    interestPaymentDate9: str
    interestPaymentDate10: str
    interestPaymentDate11: str
    interestPaymentDate12: str
    redemptionDate: str
    redemptionAmount: str
    returnDate: str
    returnAmount: str
    purpose: str
    certification: str

class MembershipToken(TokenBase):
    details: str
    returnDetails: str
    expirationDate: str
    memo: str
    transferable: str
    status: str
    initialOfferingStatus: str

class CouponToken(TokenBase):
    details: str
    returnDetails: str
    expirationDate: str
    memo: str
    transferable: str
    status: str
    initialOfferingStatus: str