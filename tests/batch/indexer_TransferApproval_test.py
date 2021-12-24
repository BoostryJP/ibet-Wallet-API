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
import pytest
from unittest import mock
from unittest.mock import MagicMock
from datetime import datetime

from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.contracts import Contract
from app.model.db import (
    Listing,
    IDXTransferApproval
)
from batch import indexer_TransferApproval
from tests.account_config import eth_account
from tests.contract_modules import (
    transfer_token,
    issue_share_token,
    register_share_list
)
from tests.utils import PersonalInfoUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    indexer_TransferApproval.TOKEN_LIST_CONTRACT_ADDRESS = shared_contract["TokenList"]["address"]
    return indexer_TransferApproval


@pytest.fixture(scope="function")
def processor(test_module, session):
    _sink = test_module.Sinks()
    _sink.register(test_module.DBSink(session))
    processor = test_module.Processor(_sink, session)
    processor.initial_sync()
    return processor


class TestProcessor:
    issuer = eth_account["issuer"]
    account1 = eth_account["user1"]
    account2 = eth_account["user2"]
    escrow_agent = eth_account["agent"]

    @staticmethod
    def issue_token_share(issuer,
                          exchange_contract,
                          personal_info_contract,
                          token_list_contract):
        if exchange_contract is None:
            exchange_contract_address = config.ZERO_ADDRESS
        else:
            exchange_contract_address = exchange_contract.address
        # Issue token
        args = {
            "name": "テスト株式",
            "symbol": "SHARE",
            "tradableExchange": exchange_contract_address,
            "personalInfoAddress": personal_info_contract.get("address", config.ZERO_ADDRESS),
            "issuePrice": 1000,
            "principalValue": 1000,
            "totalSupply": 1000000,
            "dividends": 101,
            "dividendRecordDate": "20200401",
            "dividendPaymentDate": "20200502",
            "cancellationDate": "20200603",
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
            "memo": "メモ",
            "transferable": True
        }
        _token = issue_share_token(issuer, args)
        register_share_list(issuer, _token, token_list_contract)

        token_contract = Contract.get_contract(
            contract_name="IbetShare",
            address=_token["address"]
        )

        return token_contract

    @staticmethod
    def list_token(db_session, token_address):
        _listing = Listing()
        _listing.token_address = token_address
        _listing.is_public = True
        _listing.owner_address = TestProcessor.issuer["account_address"]
        db_session.add(_listing)

    @staticmethod
    def register_personal_info(account_address,
                               link_address,
                               personal_info_contract):
        PersonalInfoUtils.register(
            tx_from=account_address,
            personal_info_address=personal_info_contract["address"],
            link_address=link_address
        )

    @staticmethod
    def set_transfer_approval_required(token_contract, required):
        token_contract.functions.setTransferApprovalRequired(
            required
        ).transact({
            'from': TestProcessor.issuer['account_address']
        })

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # Single Token
    #  - ApplyForTransfer
    def test_normal_1_1(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        self.list_token(
            token_address=token.address,
            db_session=session
        )

        # Register personal info
        self.register_personal_info(
            account_address=self.account1["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )
        self.register_personal_info(
            account_address=self.account2["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )

        # Transfer token: from issuer to account1
        transfer_token(
            token_contract=token,
            from_address=self.issuer["account_address"],
            to_address=self.account1["account_address"],
            amount=10000
        )

        # Change transfer approval required to True
        self.set_transfer_approval_required(
            token_contract=token,
            required=True
        )

        # Apply for transfer
        token.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "978266096"  # 2000/12/31 12:34:56
        ).transact({
            "from": self.account1["account_address"]
        })

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 2000
        assert _transfer_approval.application_datetime == \
               datetime.strptime("2000/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

    # <Normal_1_2>
    # Single Token
    #  - ApplyForTransfer
    #  - ApproveTransfer
    def test_normal_1_2(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue Token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        self.list_token(
            token_address=token.address,
            db_session=session
        )

        # Register personal info
        self.register_personal_info(
            account_address=self.account1["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )
        self.register_personal_info(
            account_address=self.account2["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )

        # Transfer token: from issuer to account1
        transfer_token(
            token_contract=token,
            from_address=self.issuer["account_address"],
            to_address=self.account1["account_address"],
            amount=10000
        )

        # Change transfer approval required to True
        self.set_transfer_approval_required(
            token_contract=token,
            required=True
        )

        # Apply for transfer
        token.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "978266096"  # 2000/12/31 12:34:56
        ).transact({
            "from": self.account1["account_address"]
        })

        # Approve transfer
        token.functions.approveTransfer(
            0,
            "1609418096"  # 2020/12/31 12:34:56
        ).transact({
            "from": self.issuer["account_address"]
        })

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 2000
        assert _transfer_approval.application_datetime == \
               datetime.strptime("2000/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime == \
               datetime.strptime("2020/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.approval_blocktimestamp is not None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

    # <Normal_1_3>
    # Single Token
    #  - ApplyForTransfer
    #  - CancelTransfer
    def test_normal_1_3(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        self.list_token(
            token_address=token.address,
            db_session=session
        )

        # Register personal info
        self.register_personal_info(
            account_address=self.account1["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )
        self.register_personal_info(
            account_address=self.account2["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )

        # Transfer token: from issuer to account1
        transfer_token(
            token_contract=token,
            from_address=self.issuer["account_address"],
            to_address=self.account1["account_address"],
            amount=10000
        )

        # Change transfer approval required to True
        self.set_transfer_approval_required(
            token_contract=token,
            required=True
        )

        # Apply for transfer
        token.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "978266096"
        ).transact({
            "from": self.account1["account_address"]
        })

        # Cancel transfer
        token.functions.cancelTransfer(
            0,
            "test_data"
        ).transact({
            "from": self.issuer["account_address"]
        })

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 2000
        assert _transfer_approval.application_datetime == \
               datetime.strptime("2000/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

    # <Normal_1_4>
    # Multi Token
    #  - ApplyForTransfer
    #  - ApproveTransfer
    def test_normal_1_4(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue Token
        token_1 = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        self.list_token(
            token_address=token_1.address,
            db_session=session
        )

        token_2 = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        self.list_token(
            token_address=token_2.address,
            db_session=session
        )

        # Register personal info
        self.register_personal_info(
            account_address=self.account1["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )
        self.register_personal_info(
            account_address=self.account2["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )

        # Transfer token: from issuer to account1
        transfer_token(
            token_contract=token_1,
            from_address=self.issuer["account_address"],
            to_address=self.account1["account_address"],
            amount=10000
        )
        transfer_token(
            token_contract=token_2,
            from_address=self.issuer["account_address"],
            to_address=self.account1["account_address"],
            amount=10000
        )

        # Change transfer approval required to True
        self.set_transfer_approval_required(
            token_contract=token_1,
            required=True
        )
        self.set_transfer_approval_required(
            token_contract=token_2,
            required=True
        )

        # Apply for transfer
        token_1.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "978266096"  # 2000/12/31 12:34:56
        ).transact({
            "from": self.account1["account_address"]
        })
        token_2.functions.applyForTransfer(
            self.account2["account_address"],
            3000,
            "978266097"  # 2000/12/31 12:34:57
        ).transact({
            "from": self.account1["account_address"]
        })

        # Approve transfer
        token_1.functions.approveTransfer(
            0,
            "1609418096"  # 2020/12/31 12:34:56
        ).transact({
            "from": self.issuer["account_address"]
        })
        token_2.functions.approveTransfer(
            0,
            "1609418097"  # 2020/12/31 12:34:57
        ).transact({
            "from": self.issuer["account_address"]
        })

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 2

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token_1.address
        assert _transfer_approval.exchange_address is None
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 2000
        assert _transfer_approval.application_datetime == \
               datetime.strptime("2000/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime == \
               datetime.strptime("2020/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.approval_blocktimestamp is not None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

        _transfer_approval = _transfer_approval_list[1]
        assert _transfer_approval.id == 2
        assert _transfer_approval.token_address == token_2.address
        assert _transfer_approval.application_id == 0
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 3000
        assert _transfer_approval.application_datetime == \
               datetime.strptime("2000/12/31 12:34:57", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime == \
               datetime.strptime("2020/12/31 12:34:57", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.approval_blocktimestamp is not None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

    # <Normal_1_5>
    # No event logs
    def test_normal_1_5(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        self.list_token(
            token_address=token.address,
            db_session=session
        )

        # Register personal info
        self.register_personal_info(
            account_address=self.account1["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )
        self.register_personal_info(
            account_address=self.account2["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )

        # Transfer token: from issuer to account1
        transfer_token(
            token_contract=token,
            from_address=self.issuer["account_address"],
            to_address=self.account1["account_address"],
            amount=10000
        )

        # Change transfer approval required to True
        self.set_transfer_approval_required(
            token_contract=token,
            required=True
        )

        # ApplyForTransfer events not emitted
        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 0

    # <Normal_1_6>
    # Not listed token
    def test_normal_1_6(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )

        # Register personal info
        self.register_personal_info(
            account_address=self.account1["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )
        self.register_personal_info(
            account_address=self.account2["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )

        # Transfer token: from issuer to account1
        transfer_token(
            token_contract=token,
            from_address=self.issuer["account_address"],
            to_address=self.account1["account_address"],
            amount=10000
        )

        # Change transfer approval required to True
        self.set_transfer_approval_required(
            token_contract=token,
            required=True
        )

        # Apply for transfer
        token.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "978266096"  # 2000/12/31 12:34:56
        ).transact({
            "from": self.account1["account_address"]
        })

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 0

    # <Normal_2_1>
    # IbetSecurityTokenEscrow
    #  - ApplyForTransfer
    def test_normal_2_1(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        st_escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=st_escrow_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        self.list_token(
            token_address=token.address,
            db_session=session
        )

        # Register personal info
        self.register_personal_info(
            account_address=self.account1["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )
        self.register_personal_info(
            account_address=self.account2["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )

        # Transfer token: from issuer to account1
        transfer_token(
            token_contract=token,
            from_address=self.issuer["account_address"],
            to_address=self.account1["account_address"],
            amount=10000
        )

        # Change transfer approval required to True
        self.set_transfer_approval_required(
            token_contract=token,
            required=True
        )

        # Deposit token to escrow
        transfer_token(
            token_contract=token,
            from_address=self.account1["account_address"],
            to_address=st_escrow_contract.address,
            amount=10000
        )

        # Create escrow
        st_escrow_contract.functions.createEscrow(
            token.address,
            self.account2["account_address"],
            10000,
            self.escrow_agent["account_address"],
            "978266096",  # 2000/12/31 12:34:56
            "test_escrow_data"
        ).transact({
            "from": self.account1["account_address"]
        })

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address == st_escrow_contract.address
        assert _transfer_approval.application_id == st_escrow_contract.functions.latestEscrowId().call()
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 10000
        assert _transfer_approval.application_datetime == \
               datetime.strptime("2000/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is None

    # <Normal_2_2>
    # IbetSecurityTokenEscrow
    #  - ApplyForTransfer
    #  - CancelTransfer
    def test_normal_2_2(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        st_escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=st_escrow_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        self.list_token(
            token_address=token.address,
            db_session=session
        )

        # Register personal info
        self.register_personal_info(
            account_address=self.account1["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )
        self.register_personal_info(
            account_address=self.account2["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )

        # Transfer token: from issuer to account1
        transfer_token(
            token_contract=token,
            from_address=self.issuer["account_address"],
            to_address=self.account1["account_address"],
            amount=10000
        )

        # Change transfer approval required to True
        self.set_transfer_approval_required(
            token_contract=token,
            required=True
        )

        # Deposit token to escrow
        transfer_token(
            token_contract=token,
            from_address=self.account1["account_address"],
            to_address=st_escrow_contract.address,
            amount=10000
        )

        # Create escrow
        st_escrow_contract.functions.createEscrow(
            token.address,
            self.account2["account_address"],
            10000,
            self.escrow_agent["account_address"],
            "978266096",  # 2000/12/31 12:34:56
            "test_escrow_data"
        ).transact({
            "from": self.account1["account_address"]
        })

        # Cancel escrow
        escrow_id = st_escrow_contract.functions.latestEscrowId().call()
        st_escrow_contract.functions.cancelEscrow(
            escrow_id
        ).transact({
            "from": self.account1["account_address"]
        })

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address == st_escrow_contract.address
        assert _transfer_approval.application_id == escrow_id
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 10000
        assert _transfer_approval.application_datetime == \
               datetime.strptime("2000/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is True
        assert _transfer_approval.transfer_approved is None

    # <Normal_2_3>
    # IbetSecurityTokenEscrow
    #  - ApplyForTransfer
    #  - ApproveTransfer
    def test_normal_2_3(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        st_escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=st_escrow_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        self.list_token(
            token_address=token.address,
            db_session=session
        )

        # Register personal info
        self.register_personal_info(
            account_address=self.account1["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )
        self.register_personal_info(
            account_address=self.account2["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )

        # Transfer token: from issuer to account1
        transfer_token(
            token_contract=token,
            from_address=self.issuer["account_address"],
            to_address=self.account1["account_address"],
            amount=10000
        )

        # Change transfer approval required to True
        self.set_transfer_approval_required(
            token_contract=token,
            required=True
        )

        # Deposit token to escrow
        transfer_token(
            token_contract=token,
            from_address=self.account1["account_address"],
            to_address=st_escrow_contract.address,
            amount=10000
        )

        # Create escrow
        st_escrow_contract.functions.createEscrow(
            token.address,
            self.account2["account_address"],
            10000,
            self.escrow_agent["account_address"],
            "978266096",  # 2000/12/31 12:34:56
            "test_escrow_data"
        ).transact({
            "from": self.account1["account_address"]
        })

        escrow_id = st_escrow_contract.functions.latestEscrowId().call()

        # Approve transfer
        st_escrow_contract.functions.approveTransfer(
            escrow_id,
            "1609418096"  # 2020/12/31 12:34:56
        ).transact({
            "from": self.issuer["account_address"]
        })

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address == st_escrow_contract.address
        assert _transfer_approval.application_id == escrow_id
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 10000
        assert _transfer_approval.application_datetime == \
               datetime.strptime("2000/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime is None
        assert _transfer_approval.approval_blocktimestamp is None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

    # <Normal_2_4>
    # IbetSecurityTokenEscrow
    #  - ApplyForTransfer
    #  - FinishTransfer
    def test_normal_2_4(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        st_escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=st_escrow_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        self.list_token(
            token_address=token.address,
            db_session=session
        )

        # Register personal info
        self.register_personal_info(
            account_address=self.account1["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )
        self.register_personal_info(
            account_address=self.account2["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )

        # Transfer token: from issuer to account1
        transfer_token(
            token_contract=token,
            from_address=self.issuer["account_address"],
            to_address=self.account1["account_address"],
            amount=10000
        )

        # Change transfer approval required to True
        self.set_transfer_approval_required(
            token_contract=token,
            required=True
        )

        # Deposit token to escrow
        transfer_token(
            token_contract=token,
            from_address=self.account1["account_address"],
            to_address=st_escrow_contract.address,
            amount=10000
        )

        # Create escrow
        st_escrow_contract.functions.createEscrow(
            token.address,
            self.account2["account_address"],
            10000,
            self.escrow_agent["account_address"],
            "978266096",  # 2000/12/31 12:34:56
            "test_escrow_data"
        ).transact({
            "from": self.account1["account_address"]
        })

        escrow_id = st_escrow_contract.functions.latestEscrowId().call()

        # Approve transfer
        st_escrow_contract.functions.approveTransfer(
            escrow_id,
            "1609418096"  # 2020/12/31 12:34:56
        ).transact({
            "from": self.issuer["account_address"]
        })

        # Finish escrow
        st_escrow_contract.functions.finishEscrow(
            escrow_id
        ).transact({
            "from": self.escrow_agent["account_address"]
        })

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 1

        _transfer_approval = _transfer_approval_list[0]
        assert _transfer_approval.id == 1
        assert _transfer_approval.token_address == token.address
        assert _transfer_approval.exchange_address == st_escrow_contract.address
        assert _transfer_approval.application_id == escrow_id
        assert _transfer_approval.from_address == self.account1["account_address"]
        assert _transfer_approval.to_address == self.account2["account_address"]
        assert _transfer_approval.value == 10000
        assert _transfer_approval.application_datetime == \
               datetime.strptime("2000/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.application_blocktimestamp is not None
        assert _transfer_approval.approval_datetime == \
               datetime.strptime("2020/12/31 12:34:56", '%Y/%m/%d %H:%M:%S')
        assert _transfer_approval.approval_blocktimestamp is not None
        assert _transfer_approval.cancelled is None
        assert _transfer_approval.transfer_approved is True

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Exception on getting logs
    @mock.patch("web3.contract.ContractEvent.getLogs", MagicMock(side_effect=Exception()))
    def test_error_1(self, processor, shared_contract, session):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Issue token
        token = self.issue_token_share(
            issuer=self.issuer,
            exchange_contract=None,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        self.list_token(
            token_address=token.address,
            db_session=session
        )

        # Register personal info
        self.register_personal_info(
            account_address=self.account1["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )
        self.register_personal_info(
            account_address=self.account2["account_address"],
            link_address=self.issuer["account_address"],
            personal_info_contract=personal_info_contract
        )

        # Transfer token: from issuer to account1
        transfer_token(
            token_contract=token,
            from_address=self.issuer["account_address"],
            to_address=self.account1["account_address"],
            amount=10000
        )

        # Change transfer approval required to True
        self.set_transfer_approval_required(
            token_contract=token,
            required=True
        )

        # Apply for transfer
        token.functions.applyForTransfer(
            self.account2["account_address"],
            2000,
            "978266096"  # 2000/12/31 12:34:56
        ).transact({
            "from": self.account1["account_address"]
        })

        # Run target process
        processor.sync_new_logs()

        # Assertion
        _transfer_approval_list = session.query(IDXTransferApproval). \
            order_by(IDXTransferApproval.created). \
            all()
        assert len(_transfer_approval_list) == 0
