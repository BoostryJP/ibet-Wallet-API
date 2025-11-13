# cSpell:ignore ibet
import pytest
from eth_utils.address import to_checksum_address
from pydantic import ValidationError

from app.model.type.token_list import TokenListItem


def test_token_list_item_addresses_are_converted_to_checksum():
    raw_token_address = "0x000000000000000000000000000000000000dead"
    raw_issuer_address = "0x000000000000000000000000000000000000beef"

    item = TokenListItem(
        token_template="ibetBond",
        product_type=0,
        token_address=raw_token_address,
        key_manager=[],
        issuer_address=raw_issuer_address,
    )

    assert item.token_address == to_checksum_address(raw_token_address)
    assert item.issuer_address == to_checksum_address(raw_issuer_address)


@pytest.mark.parametrize(
    "token_address",
    [
        "invalid-address",
        "0x123",  # too short
    ],
)
@pytest.mark.parametrize(
    "issuer_address",
    [
        "invalid-address",
        "0x456",  # too short
    ],
)
def test_token_list_item_rejects_invalid_addresses(token_address, issuer_address):
    with pytest.raises(ValidationError):
        TokenListItem(
            token_template="ibetBond",
            product_type=0,
            token_address=token_address,
            key_manager=[],
            issuer_address=issuer_address,
        )
