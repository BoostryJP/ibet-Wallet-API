# -*- coding: utf-8 -*-

class TokenBase():
    token_address: str
    token_template: str
    owner_address: str
    company_name: str
    rsa_publickey: str
    name: str
    symbol: str
    total_supply: int
    image_url: object
    payment_method_credit_card: bool
    payment_method_bank: bool
    contact_information: str
    privacy_policy: str


class BondToken(TokenBase):
    face_value: int
    interest_rate: int
    interest_payment_date1: str
    interest_payment_date2: str
    interest_payment_date3: str
    interest_payment_date4: str
    interest_payment_date5: str
    interest_payment_date6: str
    interest_payment_date7: str
    interest_payment_date8: str
    interest_payment_date9: str
    interest_payment_date10: str
    interest_payment_date11: str
    interest_payment_date12: str
    redemption_date: str
    redemption_amount: int
    return_date: str
    return_amount: str
    purpose: str
    certification: str


class BondTokenV2(TokenBase):
    face_value: int
    interest_rate: int
    interest_payment_date1: str
    interest_payment_date2: str
    interest_payment_date3: str
    interest_payment_date4: str
    interest_payment_date5: str
    interest_payment_date6: str
    interest_payment_date7: str
    interest_payment_date8: str
    interest_payment_date9: str
    interest_payment_date10: str
    interest_payment_date11: str
    interest_payment_date12: str
    redemption_date: str
    redemption_amount: int
    return_date: str
    return_amount: str
    purpose: str
    certification: str
    max_holding_quantity: int
    max_sell_amount: int


class MembershipToken(TokenBase):
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: str
    status: str
    initial_offering_status: str


class MembershipTokenV2(TokenBase):
    """
    version2
    """
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: str
    status: str
    initial_offering_status: str
    max_holding_quantity: int
    max_sell_amount: int


class CouponToken(TokenBase):
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: str
    status: str
    initial_offering_status: str


class CouponTokenV2(TokenBase):
    """
    version2
    """
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: str
    status: str
    initial_offering_status: str
    max_holding_quantity: int
    max_sell_amount: int


class MRFToken(TokenBase):
    details: str
    memo: str
    status: str
    initial_offering_status: str


class JDRToken(TokenBase):
    details: str
    memo: str
    status: str
    initial_offering_status: str
