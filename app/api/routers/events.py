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

from typing import Annotated, Any, TypeAlias, TypedDict, cast

from eth_typing import HexStr
from fastapi import APIRouter, Depends, Path, Query
from web3.contract.async_contract import AsyncContractEvent
from web3.exceptions import Web3ValidationError
from web3.types import EventData

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
)
from app.model.type import EthereumAddress
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response
from app.utils.web3_utils import AsyncWeb3Wrapper

LOG = log.get_logger()
async_web3 = AsyncWeb3Wrapper()
REQUEST_BLOCK_RANGE_LIMIT = 10000

router = APIRouter(prefix="/Events", tags=["contract_log"])


class EventLogData(TypedDict):
    event: str
    args: dict[str, Any]
    transaction_hash: str
    block_number: int
    block_timestamp: int
    log_index: int


EventFilters: TypeAlias = dict[str, Any]


async def _collect_event_logs(
    contract_name: str,
    contract_address: str,
    attr_list: list[str],
    from_block: int,
    to_block: int,
    argument_filters: EventFilters,
) -> list[EventLogData]:
    contract = AsyncContract.get_contract(
        contract_name=contract_name,
        address=contract_address,
    )

    tmp_list: list[EventLogData] = []
    for attr in attr_list:
        contract_event = getattr(contract.events, attr, None)
        if not isinstance(contract_event, AsyncContractEvent):
            raise InvalidParameterError("invalid event log")
        events: list[EventData]
        try:
            events = list(
                await contract_event.get_logs(
                    from_block=from_block,
                    to_block=to_block,
                    argument_filters=argument_filters,
                )
            )
        except Web3ValidationError:
            events = []
        for event in events:
            block_number = int(event["blockNumber"])
            log_index = int(event["logIndex"])
            block_data = await async_web3.eth.get_block(block_number)
            block_timestamp_raw = block_data.get("timestamp")
            if block_timestamp_raw is None:
                raise InvalidParameterError("invalid event log")
            block_timestamp = int(block_timestamp_raw)
            transaction_hash = HexStr(event["transactionHash"].to_0x_hex())
            tmp_list.append(
                cast(
                    EventLogData,
                    {
                        "event": event["event"],
                        "args": dict(event["args"]),
                        "transaction_hash": str(transaction_hash),
                        "block_number": block_number,
                        "block_timestamp": block_timestamp,
                        "log_index": log_index,
                    },
                )
            )
    return sorted(tmp_list, key=lambda x: (x["block_number"], x["log_index"]))


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
    request_query: Annotated[E2EMessagingEventsQuery, Query()],
):
    """
    Returns a list of E2EMessaging event logs.
    """
    if request_query.to_block - request_query.from_block > REQUEST_BLOCK_RANGE_LIMIT:
        raise RequestBlockRangeLimitExceededError(
            "Search request range is over the limit"
        )

    # Validate
    argument_filters_dict: EventFilters = {}
    if request_query.argument_filters:
        try:
            parsed_filters = E2EMessagingEventArguments.model_validate_json(
                request_query.argument_filters
            ).model_dump(exclude_none=True)
            argument_filters_dict = {
                str(key): value for key, value in parsed_filters.items()
            }
        except Exception:
            raise InvalidParameterError("invalid argument_filters")

    # Get event logs
    if request_query.event == "Message":
        attr_list = ["Message"]
    elif request_query.event == "PublicKeyUpdated":
        attr_list = ["PublicKeyUpdated"]
    else:  # All events
        attr_list = ["PublicKeyUpdated", "Message"]

    resp_json = await _collect_event_logs(
        contract_name="E2EMessaging",
        contract_address=str(config.E2E_MESSAGING_CONTRACT_ADDRESS),
        attr_list=attr_list,
        from_block=request_query.from_block,
        to_block=request_query.to_block,
        argument_filters=argument_filters_dict,
    )
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
    request_query: Annotated[IbetEscrowEventsQuery, Query()],
):
    """
    Returns a list of IbetEscrow event logs.
    """
    if request_query.to_block - request_query.from_block > REQUEST_BLOCK_RANGE_LIMIT:
        raise RequestBlockRangeLimitExceededError(
            "Search request range is over the limit"
        )

    # Validate
    argument_filters_dict: EventFilters = {}
    if request_query.argument_filters:
        try:
            parsed_filters = EscrowEventArguments.model_validate_json(
                request_query.argument_filters
            ).model_dump(exclude_none=True)
            argument_filters_dict = {
                str(key): value for key, value in parsed_filters.items()
            }
        except Exception:
            raise InvalidParameterError("invalid argument_filters")

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

    resp_json = await _collect_event_logs(
        contract_name="IbetEscrow",
        contract_address=str(config.IBET_ESCROW_CONTRACT_ADDRESS),
        attr_list=attr_list,
        from_block=request_query.from_block,
        to_block=request_query.to_block,
        argument_filters=argument_filters_dict,
    )
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
    request_query: Annotated[IbetSecurityTokenEscrowEventsQuery, Query()],
):
    """
    Returns a list of IbetSecurityTokenEscrow event logs.
    """
    # Validate
    if request_query.to_block - request_query.from_block > REQUEST_BLOCK_RANGE_LIMIT:
        raise RequestBlockRangeLimitExceededError(
            "Search request range is over the limit"
        )

    argument_filters_dict: EventFilters = {}
    if request_query.argument_filters:
        try:
            parsed_filters = EscrowEventArguments.model_validate_json(
                request_query.argument_filters
            ).model_dump(exclude_none=True)
            argument_filters_dict = {
                str(key): value for key, value in parsed_filters.items()
            }
        except Exception:
            raise InvalidParameterError("invalid argument_filters")

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

    resp_json = await _collect_event_logs(
        contract_name="IbetSecurityTokenEscrow",
        contract_address=str(config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS),
        attr_list=attr_list,
        from_block=request_query.from_block,
        to_block=request_query.to_block,
        argument_filters=argument_filters_dict,
    )
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
async def list_all_ibet_security_token_dvp_event_logs(
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

    argument_filters_dict: EventFilters = {}
    if request_query.argument_filters:
        try:
            parsed_filters = IbetSecurityTokenDVPEventArguments.model_validate_json(
                request_query.argument_filters
            ).model_dump(exclude_none=True)
            argument_filters_dict = {
                str(key): value for key, value in parsed_filters.items()
            }
        except Exception:
            raise InvalidParameterError("invalid argument_filters")

    if config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS is None:
        raise DataNotExistsError
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

    resp_json = await _collect_event_logs(
        contract_name="IbetSecurityTokenDVP",
        contract_address=str(config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS),
        attr_list=attr_list,
        from_block=request_query.from_block,
        to_block=request_query.to_block,
        argument_filters=argument_filters_dict,
    )
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
    token_address: Annotated[EthereumAddress, Path(description="Token address")],
    request_query: Annotated[IbetSecurityTokenInterfaceEventsQuery, Query()],
):
    """
    Returns a list of IbetSecurityTokenInterface event logs.
    """
    # Validate
    if request_query.to_block - request_query.from_block > REQUEST_BLOCK_RANGE_LIMIT:
        raise RequestBlockRangeLimitExceededError(
            "Search request range is over the limit"
        )

    argument_filters_dict: EventFilters = {}
    if request_query.argument_filters:
        try:
            parsed_filters = SecurityTokenEventArguments.model_validate_json(
                request_query.argument_filters, strict=True
            ).root.model_dump(exclude_none=True)
            argument_filters_dict = {
                str(key): value for key, value in parsed_filters.items()
            }
        except Exception:
            raise InvalidParameterError("invalid argument_filters")

    if request_query.event is None:
        attr_list = [
            event_type.value for event_type in IbetSecurityTokenInterfaceEventType
        ]
    else:
        attr_list = [request_query.event.value]

    resp_json = await _collect_event_logs(
        contract_name="IbetSecurityTokenInterface",
        contract_address=str(token_address),
        attr_list=attr_list,
        from_block=request_query.from_block,
        to_block=request_query.to_block,
        argument_filters=argument_filters_dict,
    )
    return json_response({**SuccessResponse.default(), "data": resp_json})
