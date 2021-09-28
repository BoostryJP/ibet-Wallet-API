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
from cerberus import Validator

from app import (
    log,
    config
)
from app.api.common import BaseResource
from app.contracts import Contract
from app.errors import InvalidParameterError

LOG = log.get_logger()


# /Events/E2EMessaging
class E2EMessagingEvents(BaseResource):
    """E2EMessaging Event Logs"""

    def on_get(self, req, res, account_address=None):
        """List all event logs"""
        LOG.info("v3.events.E2EMassagingEvents")

        # Validate Request Data
        request_json = self.validate(req)

        # Get event logs
        contract = Contract.get_contract(
            contract_name="E2EMessaging",
            address=config.E2E_MESSAGING_CONTRACT_ADDRESS
        )
        if request_json["event"] == "Message":
            attr_list = ["Message"]
        elif request_json["event"] == "PublicKeyUpdated":
            attr_list = ["PublicKeyUpdated"]
        else:  # All events
            attr_list = ["PublicKeyUpdated", "Message"]

        tmp_list = []
        for attr in attr_list:
            contract_event = getattr(contract.events, attr)
            events = contract_event.getLogs(
                fromBlock=request_json["from_block"],
                toBlock=request_json["to_block"]
            )
            for event in events:
                tmp_list.append({
                    "event": event["event"],
                    "args": dict(event["args"]),
                    "transaction_hash": event["transactionHash"].hex(),
                    "block_number": event["blockNumber"],
                    "log_index": event["logIndex"]
                })

        # Sort: block_number > log_index
        resp_json = sorted(
            tmp_list,
            key=lambda x: (x["block_number"], x["log_index"])
        )

        self.on_success(res, resp_json)

    @staticmethod
    def validate(req):
        request_json = {
            "from_block": req.get_param("from_block"),
            "to_block": req.get_param("to_block"),
            "event": req.get_param("event")
        }

        validator = Validator({
            "from_block": {
                "type": "integer",
                "coerce": int,
                "min": 1,
                "required": True
            },
            "to_block": {
                "type": "integer",
                "coerce": int,
                "min": 1,
                "required": True
            },
            "event": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": ["Message", "PublicKeyUpdated"]
            }
        })
        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if int(request_json["from_block"]) > int(request_json["to_block"]):
            raise InvalidParameterError("to_block must be greater than or equal to the from_block")

        return validator.document


# /Events/IbetEscrow
class IbetEscrowEvents(BaseResource):
    """IbetEscrow Event Logs"""

    def on_get(self, req, res, account_address=None):
        """List all event logs"""
        LOG.info("v3.events.IbetEscrowEvents")

        # Validate Request Data
        request_json = self.validate(req)

        # Get event logs
        contract = Contract.get_contract(
            contract_name="IbetEscrow",
            address=config.IBET_ESCROW_CONTRACT_ADDRESS
        )
        if request_json["event"] == "Deposited":
            attr_list = ["Deposited"]
        elif request_json["event"] == "Withdrawn":
            attr_list = ["Withdrawn"]
        elif request_json["event"] == "EscrowCreated":
            attr_list = ["EscrowCreated"]
        elif request_json["event"] == "EscrowCanceled":
            attr_list = ["EscrowCanceled"]
        elif request_json["event"] == "EscrowFinished":
            attr_list = ["EscrowFinished"]
        else:  # All events
            attr_list = [
                "Deposited",
                "Withdrawn",
                "EscrowCreated",
                "EscrowCanceled",
                "EscrowFinished"
            ]

        tmp_list = []
        for attr in attr_list:
            contract_event = getattr(contract.events, attr)
            events = contract_event.getLogs(
                fromBlock=request_json["from_block"],
                toBlock=request_json["to_block"]
            )
            for event in events:
                tmp_list.append({
                    "event": event["event"],
                    "args": dict(event["args"]),
                    "transaction_hash": event["transactionHash"].hex(),
                    "block_number": event["blockNumber"],
                    "log_index": event["logIndex"]
                })

        # Sort: block_number > log_index
        resp_json = sorted(
            tmp_list,
            key=lambda x: (x["block_number"], x["log_index"])
        )

        self.on_success(res, resp_json)

    @staticmethod
    def validate(req):
        request_json = {
            "from_block": req.get_param("from_block"),
            "to_block": req.get_param("to_block"),
            "event": req.get_param("event")
        }

        validator = Validator({
            "from_block": {
                "type": "integer",
                "coerce": int,
                "min": 1,
                "required": True
            },
            "to_block": {
                "type": "integer",
                "coerce": int,
                "min": 1,
                "required": True
            },
            "event": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": [
                    "Deposited",
                    "Withdrawn",
                    "EscrowCreated",
                    "EscrowCanceled",
                    "EscrowFinished"
                ]
            }
        })
        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if int(request_json["from_block"]) > int(request_json["to_block"]):
            raise InvalidParameterError("to_block must be greater than or equal to the from_block")

        return validator.document
