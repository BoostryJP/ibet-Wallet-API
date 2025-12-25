# cSpell:ignore publickey

import pytest
from eth_utils.address import to_checksum_address
from pydantic import ValidationError

from app.model.type.company_list import CompanyListItem


def test_company_list_item_address_is_converted_to_checksum():
    raw_address = "0x000000000000000000000000000000000000dead"

    item = CompanyListItem.model_validate(
        {
            "address": raw_address,
            "corporate_name": "Example Corp",
            "rsa_publickey": "dummy_key",
        }
    )

    assert item.address == to_checksum_address(raw_address)


def test_company_list_item_rejects_invalid_address():
    with pytest.raises(ValidationError):
        CompanyListItem(
            address="invalid-address",
            corporate_name="Example Corp",
            rsa_publickey="dummy_key",
        )


def test_company_list_item_homepage_none_defaults_to_empty_string():
    raw_address = "0x000000000000000000000000000000000000dead"

    item = CompanyListItem.model_validate(
        {
            "address": raw_address,
            "corporate_name": "Example Corp",
            "rsa_publickey": "dummy_key",
            "homepage": None,
        }
    )

    assert item.homepage == ""
