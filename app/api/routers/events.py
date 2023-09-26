"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""
from typing import Annotated

from eth_utils import to_checksum_address
from fastapi import APIRouter, Depends, Path
from web3 import Web3

from app import config, log
from app.contracts import Contract
from app.errors import InvalidParameterError, RequestBlockRangeLimitExceededError
from app.model.schema import (
    E2EMessagingEventArguments,
    E2EMessagingEventsQuery,
    EscrowEventArguments,
    IbetEscrowEventsQuery,
    IbetSecurityTokenEscrowEventsQuery,
    IbetSecurityTokenInterfaceEventsQuery,
    IbetSecurityTokenInterfaceEventType,
    ListAllEventsResponse,
    SecurityTokenEventArguments,
)
from app.model.schema.base import GenericSuccessResponse, SuccessResponse
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response
from app.utils.web3_utils import Web3Wrapper

LOG = log.get_logger()
web3 = Web3Wrapper()
REQUEST_BLOCK_RANGE_LIMIT = 10000

router = APIRouter(prefix="/Events", tags=["contract_log"])


# /Events/E2EMessaging


@router.get(
    "/E2EMessaging",
    summary="List all E2EMessaging event logs",
    operation_id="E2EMessagingEvents",
    response_model=GenericSuccessResponse[ListAllEventsResponse],
    responses=get_routers_responses(
        InvalidParameterError, RequestBlockRangeLimitExceededError
    ),
)
def list_all_e2e_messaging_event_logs(
    request_query: E2EMessagingEventsQuery = Depends(),
):
    """List all E2EMessaging event logs"""
    if request_query.to_block - request_query.from_block > REQUEST_BLOCK_RANGE_LIMIT:
        raise RequestBlockRangeLimitExceededError(
            "Search request range is over the limit"
        )

    # Validate
    argument_filters_dict = {}
    if request_query.argument_filters:
        try:
            argument_filters_dict = E2EMessagingEventArguments.parse_raw(
                request_query.argument_filters
            ).dict(exclude_none=True)
        except Exception:
            raise InvalidParameterError("invalid argument_filters")

    # Get event logs
    contract = Contract.get_contract(
        contract_name="E2EMessaging", address=str(config.E2E_MESSAGING_CONTRACT_ADDRESS)
    )
    if request_query.event == "Message":
        attr_list = ["Message"]
    elif request_query.event == "PublicKeyUpdated":
        attr_list = ["PublicKeyUpdated"]
    else:  # All events
        attr_list = ["PublicKeyUpdated", "Message"]

    tmp_list = []
    for attr in attr_list:
        contract_event = getattr(contract.events, attr)
        events = contract_event.get_logs(
            fromBlock=request_query.from_block,
            toBlock=request_query.to_block,
            argument_filters=argument_filters_dict,
        )
        for event in events:
            block_number = event["blockNumber"]
            block_timestamp = web3.eth.get_block(block_number)["timestamp"]
            tmp_list.append(
                {
                    "event": event["event"],
                    "args": dict(event["args"]),
                    "transaction_hash": event["transactionHash"].hex(),
                    "block_number": block_number,
                    "block_timestamp": block_timestamp,
                    "log_index": event["logIndex"],
                }
            )

    # Sort: block_number > log_index
    resp_json = sorted(tmp_list, key=lambda x: (x["block_number"], x["log_index"]))
    return json_response({**SuccessResponse.default(), "data": resp_json})


# /Events/IbetEscrow
@router.get(
    "/IbetEscrow",
    summary="List all IbetEscrow event logs",
    operation_id="IbetEscrowEvents",
    response_model=GenericSuccessResponse[ListAllEventsResponse],
    responses=get_routers_responses(
        InvalidParameterError, RequestBlockRangeLimitExceededError
    ),
)
def list_all_ibet_escrow_event_logs(request_query: IbetEscrowEventsQuery = Depends()):
    """List all IbetEscrow event logs"""
    if request_query.to_block - request_query.from_block > REQUEST_BLOCK_RANGE_LIMIT:
        raise RequestBlockRangeLimitExceededError(
            "Search request range is over the limit"
        )

    # Validate
    argument_filters_dict = {}
    if request_query.argument_filters:
        try:
            argument_filters_dict = EscrowEventArguments.parse_raw(
                request_query.argument_filters
            ).dict(exclude_none=True)
        except:
            raise InvalidParameterError("invalid argument_filters")

    contract = Contract.get_contract(
        contract_name="IbetEscrow", address=str(config.IBET_ESCROW_CONTRACT_ADDRESS)
    )
    if request_query.event == "Deposited":
        attr_list = ["Deposited"]
    elif request_query.event == "Withdrawn":
        attr_list = ["Withdrawn"]
    elif request_query.event == "EscrowCreated":
        attr_list = ["EscrowCreated"]
    elif request_query.event == "EscrowCanceled":
        attr_list = ["EscrowCanceled"]
    elif request_query.event == "EscrowFinished":
        attr_list = ["EscrowFinished"]
    else:  # All events
        attr_list = [
            "Deposited",
            "Withdrawn",
            "EscrowCreated",
            "EscrowCanceled",
            "EscrowFinished",
        ]

    tmp_list = []
    for attr in attr_list:
        contract_event = getattr(contract.events, attr)
        events = contract_event.get_logs(
            fromBlock=request_query.from_block,
            toBlock=request_query.to_block,
            argument_filters=argument_filters_dict,
        )
        for event in events:
            block_number = event["blockNumber"]
            block_timestamp = web3.eth.get_block(block_number)["timestamp"]
            tmp_list.append(
                {
                    "event": event["event"],
                    "args": dict(event["args"]),
                    "transaction_hash": event["transactionHash"].hex(),
                    "block_number": block_number,
                    "block_timestamp": block_timestamp,
                    "log_index": event["logIndex"],
                }
            )

    # Sort: block_number > log_index
    resp_json = sorted(tmp_list, key=lambda x: (x["block_number"], x["log_index"]))
    return json_response({**SuccessResponse.default(), "data": resp_json})


# /Events/IbetSecurityTokenEscrow
@router.get(
    "/IbetSecurityTokenEscrow",
    summary="List all IbetSecurityTokenEscrow event logs",
    operation_id="IbetSecurityTokenEscrowEvents",
    response_model=GenericSuccessResponse[ListAllEventsResponse],
    responses=get_routers_responses(
        InvalidParameterError, RequestBlockRangeLimitExceededError
    ),
)
def list_all_ibet_security_token_escrow_event_logs(
    request_query: IbetSecurityTokenEscrowEventsQuery = Depends(),
):
    """List all IbetSecurityTokenEscrow event logs"""
    # Validate
    if request_query.to_block - request_query.from_block > REQUEST_BLOCK_RANGE_LIMIT:
        raise RequestBlockRangeLimitExceededError(
            "Search request range is over the limit"
        )

    argument_filters_dict = {}
    if request_query.argument_filters:
        try:
            argument_filters_dict = EscrowEventArguments.parse_raw(
                request_query.argument_filters
            ).dict(exclude_none=True)
        except:
            raise InvalidParameterError("invalid argument_filters")

    contract = Contract.get_contract(
        contract_name="IbetSecurityTokenEscrow",
        address=str(config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS),
    )
    if request_query.event == "Deposited":
        attr_list = ["Deposited"]
    elif request_query.event == "Withdrawn":
        attr_list = ["Withdrawn"]
    elif request_query.event == "EscrowCreated":
        attr_list = ["EscrowCreated"]
    elif request_query.event == "EscrowCanceled":
        attr_list = ["EscrowCanceled"]
    elif request_query.event == "EscrowFinished":
        attr_list = ["EscrowFinished"]
    elif request_query.event == "ApplyForTransfer":
        attr_list = ["ApplyForTransfer"]
    elif request_query.event == "CancelTransfer":
        attr_list = ["CancelTransfer"]
    elif request_query.event == "ApproveTransfer":
        attr_list = ["ApproveTransfer"]
    else:  # All events
        attr_list = [
            "Deposited",
            "Withdrawn",
            "EscrowCreated",
            "EscrowCanceled",
            "EscrowFinished",
            "ApplyForTransfer",
            "CancelTransfer",
            "ApproveTransfer",
        ]

    tmp_list = []
    for attr in attr_list:
        contract_event = getattr(contract.events, attr)
        events = contract_event.get_logs(
            fromBlock=request_query.from_block,
            toBlock=request_query.to_block,
            argument_filters=argument_filters_dict,
        )
        for event in events:
            block_number = event["blockNumber"]
            block_timestamp = web3.eth.get_block(block_number)["timestamp"]
            tmp_list.append(
                {
                    "event": event["event"],
                    "args": dict(event["args"]),
                    "transaction_hash": event["transactionHash"].hex(),
                    "block_number": block_number,
                    "block_timestamp": block_timestamp,
                    "log_index": event["logIndex"],
                }
            )

    # Sort: block_number > log_index
    resp_json = sorted(tmp_list, key=lambda x: (x["block_number"], x["log_index"]))
    return json_response({**SuccessResponse.default(), "data": resp_json})


# /Events/IbetSecurityTokenInterface/{token_address}
@router.get(
    "/IbetSecurityTokenInterface/{token_address}",
    summary="List all IbetSecurityTokenInterface event logs",
    operation_id="IbetSecurityTokenInterfaceEvents",
    response_model=GenericSuccessResponse[ListAllEventsResponse],
    responses=get_routers_responses(
        InvalidParameterError, RequestBlockRangeLimitExceededError
    ),
)
def list_all_ibet_security_token_interface_event_logs(
    token_address: Annotated[str, Path(description="Token address")],
    request_query: IbetSecurityTokenInterfaceEventsQuery = Depends(),
):
    """List all IbetSecurityTokenInterface event logs"""
    # Validate
    if request_query.to_block - request_query.from_block > REQUEST_BLOCK_RANGE_LIMIT:
        raise RequestBlockRangeLimitExceededError(
            "Search request range is over the limit"
        )

    argument_filters_dict = {}
    if request_query.argument_filters:
        try:
            argument_filters_dict = SecurityTokenEventArguments.parse_raw(
                request_query.argument_filters,
            ).__root__.dict(exclude_none=True)
        except Exception:
            raise InvalidParameterError("invalid argument_filters")

    try:
        token_address = to_checksum_address(token_address)
        if not Web3.is_address(token_address):
            description = "invalid token_address"
            raise InvalidParameterError(description=description)
    except:
        description = "invalid token_address"
        raise InvalidParameterError(description=description)

    contract = Contract.get_contract(
        contract_name="IbetSecurityTokenInterface", address=str(token_address)
    )
    if request_query.event is None:
        attr_list = [event_type for event_type in IbetSecurityTokenInterfaceEventType]
    else:
        attr_list = [request_query.event.value]

    tmp_list = []
    for attr in attr_list:
        contract_event = getattr(contract.events, attr)
        events = contract_event.get_logs(
            fromBlock=request_query.from_block,
            toBlock=request_query.to_block,
            argument_filters=argument_filters_dict,
        )
        for event in events:
            block_number = event["blockNumber"]
            block_timestamp = web3.eth.get_block(block_number)["timestamp"]
            tmp_list.append(
                {
                    "event": event["event"],
                    "args": dict(event["args"]),
                    "transaction_hash": event["transactionHash"].hex(),
                    "block_number": block_number,
                    "block_timestamp": block_timestamp,
                    "log_index": event["logIndex"],
                }
            )

    # Sort: block_number > log_index
    resp_json = sorted(tmp_list, key=lambda x: (x["block_number"], x["log_index"]))
    return json_response({**SuccessResponse.default(), "data": resp_json})
