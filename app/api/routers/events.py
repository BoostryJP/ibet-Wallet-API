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

from fastapi import APIRouter, Depends, Path
from web3.exceptions import Web3ValidationError

from app import config, log
from app.contracts import AsyncContract
from app.errors import (
    DataNotExistsError,
    InvalidParameterError,
    RequestBlockRangeLimitExceededError,
)
from app.model.schema import (
    E2EMessagingEventArguments,
    E2EMessagingEventsQuery,
    EscrowEventArguments,
    IbetEscrowEventsQuery,
    IbetSecurityTokenDVPEventArguments,
    IbetSecurityTokenDVPEventsQuery,
    IbetSecurityTokenEscrowEventsQuery,
    IbetSecurityTokenInterfaceEventsQuery,
    IbetSecurityTokenInterfaceEventType,
    ListAllEventsResponse,
    SecurityTokenEventArguments,
)
from app.model.schema.base import (
    GenericSuccessResponse,
    SuccessResponse,
    ValidatedEthereumAddress,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response
from app.utils.web3_utils import AsyncWeb3Wrapper

LOG = log.get_logger()
async_web3 = AsyncWeb3Wrapper()
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
async def list_all_e2e_messaging_event_logs(
    request_query: E2EMessagingEventsQuery = Depends(),
):
    """
    Returns a list of E2EMessaging event logs.
    """
    if request_query.to_block - request_query.from_block > REQUEST_BLOCK_RANGE_LIMIT:
        raise RequestBlockRangeLimitExceededError(
            "Search request range is over the limit"
        )

    # Validate
    argument_filters_dict = {}
    if request_query.argument_filters:
        try:
            argument_filters_dict = E2EMessagingEventArguments.model_validate_json(
                request_query.argument_filters
            ).model_dump(exclude_none=True)
        except Exception:
            raise InvalidParameterError("invalid argument_filters")

    # Get event logs
    contract = AsyncContract.get_contract(
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
        try:
            events = await contract_event.get_logs(
                fromBlock=request_query.from_block,
                toBlock=request_query.to_block,
                argument_filters=argument_filters_dict,
            )
        except Web3ValidationError:
            events = []
        for event in events:
            block_number = event["blockNumber"]
            block_timestamp = (await async_web3.eth.get_block(block_number))[
                "timestamp"
            ]
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
async def list_all_ibet_escrow_event_logs(
    request_query: IbetEscrowEventsQuery = Depends(),
):
    """
    Returns a list of IbetEscrow event logs.
    """
    if request_query.to_block - request_query.from_block > REQUEST_BLOCK_RANGE_LIMIT:
        raise RequestBlockRangeLimitExceededError(
            "Search request range is over the limit"
        )

    # Validate
    argument_filters_dict = {}
    if request_query.argument_filters:
        try:
            argument_filters_dict = EscrowEventArguments.model_validate_json(
                request_query.argument_filters
            ).model_dump(exclude_none=True)
        except:
            raise InvalidParameterError("invalid argument_filters")

    contract = AsyncContract.get_contract(
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
        try:
            events = await contract_event.get_logs(
                fromBlock=request_query.from_block,
                toBlock=request_query.to_block,
                argument_filters=argument_filters_dict,
            )
        except Web3ValidationError:
            events = []
        for event in events:
            block_number = event["blockNumber"]
            block_timestamp = (await async_web3.eth.get_block(block_number))[
                "timestamp"
            ]
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
async def list_all_ibet_security_token_escrow_event_logs(
    request_query: IbetSecurityTokenEscrowEventsQuery = Depends(),
):
    """
    Returns a list of IbetSecurityTokenEscrow event logs.
    """
    # Validate
    if request_query.to_block - request_query.from_block > REQUEST_BLOCK_RANGE_LIMIT:
        raise RequestBlockRangeLimitExceededError(
            "Search request range is over the limit"
        )

    argument_filters_dict = {}
    if request_query.argument_filters:
        try:
            argument_filters_dict = EscrowEventArguments.model_validate_json(
                request_query.argument_filters
            ).model_dump(exclude_none=True)
        except:
            raise InvalidParameterError("invalid argument_filters")

    contract = AsyncContract.get_contract(
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
        try:
            events = await contract_event.get_logs(
                fromBlock=request_query.from_block,
                toBlock=request_query.to_block,
                argument_filters=argument_filters_dict,
            )
        except Web3ValidationError:
            events = []
        for event in events:
            block_number = event["blockNumber"]
            block_timestamp = (await async_web3.eth.get_block(block_number))[
                "timestamp"
            ]
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


# /Events/IbetSecurityTokenDVP
@router.get(
    "/IbetSecurityTokenDVP",
    summary="List all IbetSecurityTokenDVP event logs",
    operation_id="IbetSecurityTokenDVPEvents",
    response_model=GenericSuccessResponse[ListAllEventsResponse],
    responses=get_routers_responses(
        InvalidParameterError, RequestBlockRangeLimitExceededError, DataNotExistsError
    ),
)
async def list_all_ibet_security_token_escrow_event_logs(
    request_query: IbetSecurityTokenDVPEventsQuery = Depends(),
):
    """
    Returns a list of IbetSecurityTokenDVP event logs.
    """
    # Validate
    if request_query.to_block - request_query.from_block > REQUEST_BLOCK_RANGE_LIMIT:
        raise RequestBlockRangeLimitExceededError(
            "Search request range is over the limit"
        )

    argument_filters_dict = {}
    if request_query.argument_filters:
        try:
            argument_filters_dict = (
                IbetSecurityTokenDVPEventArguments.model_validate_json(
                    request_query.argument_filters
                ).model_dump(exclude_none=True)
            )
        except:
            raise InvalidParameterError("invalid argument_filters")

    if config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS is None:
        raise DataNotExistsError
    contract = AsyncContract.get_contract(
        contract_name="IbetSecurityTokenDVP",
        address=str(config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS),
    )
    if request_query.event == "Deposited":
        attr_list = ["Deposited"]
    elif request_query.event == "Withdrawn":
        attr_list = ["Withdrawn"]
    elif request_query.event == "DeliveryCreated":
        attr_list = ["DeliveryCreated"]
    elif request_query.event == "DeliveryCanceled":
        attr_list = ["DeliveryCanceled"]
    elif request_query.event == "DeliveryConfirmed":
        attr_list = ["DeliveryConfirmed"]
    elif request_query.event == "DeliveryFinished":
        attr_list = ["DeliveryFinished"]
    elif request_query.event == "DeliveryAborted":
        attr_list = ["DeliveryAborted"]
    else:  # All events
        attr_list = [
            "Deposited",
            "Withdrawn",
            "DeliveryCreated",
            "DeliveryCanceled",
            "DeliveryConfirmed",
            "DeliveryFinished",
            "DeliveryAborted",
        ]

    tmp_list = []
    for attr in attr_list:
        contract_event = getattr(contract.events, attr)
        try:
            events = await contract_event.get_logs(
                fromBlock=request_query.from_block,
                toBlock=request_query.to_block,
                argument_filters=argument_filters_dict,
            )
        except Web3ValidationError:
            events = []
        for event in events:
            block_number = event["blockNumber"]
            block_timestamp = (await async_web3.eth.get_block(block_number))[
                "timestamp"
            ]
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
async def list_all_ibet_security_token_interface_event_logs(
    token_address: Annotated[
        ValidatedEthereumAddress, Path(description="Token address")
    ],
    request_query: IbetSecurityTokenInterfaceEventsQuery = Depends(),
):
    """
    Returns a list of IbetSecurityTokenInterface event logs.
    """
    # Validate
    if request_query.to_block - request_query.from_block > REQUEST_BLOCK_RANGE_LIMIT:
        raise RequestBlockRangeLimitExceededError(
            "Search request range is over the limit"
        )

    argument_filters_dict = {}
    if request_query.argument_filters:
        try:
            argument_filters_dict = SecurityTokenEventArguments.model_validate_json(
                request_query.argument_filters, strict=True
            ).root.model_dump(exclude_none=True)
        except Exception:
            raise InvalidParameterError("invalid argument_filters")

    contract = AsyncContract.get_contract(
        contract_name="IbetSecurityTokenInterface", address=str(token_address)
    )
    if request_query.event is None:
        attr_list = [event_type for event_type in IbetSecurityTokenInterfaceEventType]
    else:
        attr_list = [request_query.event.value]

    tmp_list = []
    for attr in attr_list:
        contract_event = getattr(contract.events, attr)
        try:
            events = await contract_event.get_logs(
                fromBlock=request_query.from_block,
                toBlock=request_query.to_block,
                argument_filters=argument_filters_dict,
            )
        except Web3ValidationError:
            events = []
        for event in events:
            block_number = event["blockNumber"]
            block_timestamp = (await async_web3.eth.get_block(block_number))[
                "timestamp"
            ]
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
