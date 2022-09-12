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
from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError
from app import config
from app.contracts import Contract

LOG = log.get_logger()


# ------------------------------
# 受領用銀行口座登録状況参照
# ------------------------------
class PaymentAccount(BaseResource):
    """
    Endpoint: /User/PaymentAccount
    """
    def on_get(self, req, res, **kwargs):
        request_json = PaymentAccount.validate(req)

        pg_contract = Contract.get_contract(
            contract_name="PaymentGateway",
            address=config.PAYMENT_GATEWAY_CONTRACT_ADDRESS
        )

        # 口座登録・承認状況を参照
        account_info = Contract.call_function(
            contract=pg_contract,
            function_name="payment_accounts",
            args=(
                to_checksum_address(request_json["account_address"]),
                to_checksum_address(request_json["agent_address"]),
            ),
        )
        if account_info[0] == "0x0000000000000000000000000000000000000000":
            response_json = {
                "account_address": request_json["account_address"],
                "agent_address": request_json["agent_address"],
                "approval_status": 0
            }
        else:
            response_json = {
                "account_address": account_info[0],
                "agent_address": account_info[1],
                "approval_status": account_info[3]
            }

        self.on_success(res, response_json)

    @staticmethod
    def validate(req):
        request_json = {
            "account_address": req.get_param("account_address"),
            "agent_address": req.get_param("agent_address")
        }

        validator = Validator({
            "account_address": {"type": "string", "empty": False, "required": True},
            "agent_address": {"type": "string", "empty": False, "required": True}
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json["account_address"]):
            raise InvalidParameterError

        if not Web3.isAddress(request_json["agent_address"]):
            raise InvalidParameterError

        return request_json


# ------------------------------
# 名簿用個人情報参照
# ------------------------------
class PersonalInfo(BaseResource):
    """
    Endpoint: /User/PersonalInfo
    """
    def on_get(self, req, res, **kwargs):
        # Validation
        request_json = PersonalInfo.validate(req)

        # Get PersonalInfo contract
        if request_json["personal_info_address"] is not None:
            _personal_info_address = request_json["personal_info_address"]
        else:
            _personal_info_address = config.PERSONAL_INFO_CONTRACT_ADDRESS
        personal_info_contract = Contract.get_contract(
            contract_name="PersonalInfo",
            address=_personal_info_address
        )

        # Get registration status of personal information
        info = Contract.call_function(
            contract=personal_info_contract,
            function_name="personal_info",
            args=(
                to_checksum_address(request_json["account_address"]),
                to_checksum_address(request_json["owner_address"]),
            ),
        )
        if info[0] == config.ZERO_ADDRESS:
            response_json = {
                "account_address": request_json["account_address"],
                "owner_address": request_json["owner_address"],
                "registered": False
            }
        else:
            response_json = {
                "account_address": info[0],
                "owner_address": info[1],
                "registered": True
            }

        self.on_success(res, response_json)

    @staticmethod
    def validate(req):
        request_json = {
            "personal_info_address": req.get_param("personal_info_address"),
            "account_address": req.get_param("account_address"),
            "owner_address": req.get_param("owner_address")
        }

        validator = Validator({
            "personal_info_address": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "account_address": {
                "type": "string",
                "empty": False,
                "required": True
            },
            "owner_address": {
                "type": "string",
                "empty": False,
                "required": True
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if request_json["personal_info_address"] is not None and not Web3.isAddress(request_json["account_address"]):
            raise InvalidParameterError

        if not Web3.isAddress(request_json["account_address"]):
            raise InvalidParameterError

        if not Web3.isAddress(request_json["owner_address"]):
            raise InvalidParameterError

        return request_json
