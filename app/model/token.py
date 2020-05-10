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
    interest_rate: float
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
    redemption_value: int
    return_date: str
    return_amount: str
    purpose: str
    isRedeemed: bool
    transferable: bool
    certification: str
    initial_offering_status: bool
    max_holding_quantity: int
    max_sell_amount: int


class ShareToken(TokenBase):
    issue_price: int
    dividend_information: object
    cancellation_date: str
    reference_urls: object
    memo: str
    transferable: bool
    offering_status: bool
    reference_urls: object
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
    max_holding_quantity: int
    max_sell_amount: int
