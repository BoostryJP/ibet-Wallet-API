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

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.model.db import TokenList


class TestListAllPublicListedTokens:
    """
    Test Case for token.ListAllPublicListedTokens
    """

    # Test API
    api_url = "/PublicInfo/Tokens"

    ###########################################################################
    # Normal
    ###########################################################################

    token_address_1 = "0xE883a6F441Ad5682D37Df31d34fC012bcb07A741"
    token_address_2 = "0xE883A6f441AD5682D37df31d34FC012bcB07a742"
    token_address_3 = "0xe883a6f441AD5682d37dF31D34fc012bCB07A743"
    token_address_4 = "0xe883A6F441AD5682d37dF31d34fc012BcB07a744"
    token_address_5 = "0xe883A6F441AD5682d37df31D34fc012BcB07A745"
    issuer_address_1 = "0x1234567890aBcDEF1234567890abCDef12345678"

    # ＜Normal_1＞
    # 0 Record
    def test_normal_1(self, client: TestClient, session: Session):
        resp = client.get(self.api_url, params={})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 0, "limit": None, "offset": None, "total": 0},
            "tokens": [],
        }

    # ＜Normal_2＞
    # Multiple Records
    def test_normal_2(self, client: TestClient, session: Session):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_2
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_3
        _token_list_item.token_template = "ibetShare"
        _token_list_item.key_manager = ["1111111111111"]
        _token_list_item.product_type = 5
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_4
        _token_list_item.token_template = "ibetMembership"
        _token_list_item.key_manager = []
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_5
        _token_list_item.token_template = "ibetCoupon"
        _token_list_item.key_manager = []
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        session.commit()

        resp = client.get(self.api_url, params={})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 5, "limit": None, "offset": None, "total": 5},
            "tokens": [
                {
                    "key_manager": ["0000000000000"],
                    "product_type": 1,
                    "token_address": self.token_address_1,
                    "token_template": "ibetBond",
                    "issuer_address": None,
                },
                {
                    "key_manager": ["0000000000000"],
                    "product_type": 1,
                    "token_address": self.token_address_2,
                    "token_template": "ibetBond",
                    "issuer_address": None,
                },
                {
                    "key_manager": ["1111111111111"],
                    "product_type": 5,
                    "token_address": self.token_address_3,
                    "token_template": "ibetShare",
                    "issuer_address": None,
                },
                {
                    "key_manager": [],
                    "product_type": 1,
                    "token_address": self.token_address_4,
                    "token_template": "ibetMembership",
                    "issuer_address": None,
                },
                {
                    "key_manager": [],
                    "product_type": 1,
                    "token_address": self.token_address_5,
                    "token_template": "ibetCoupon",
                    "issuer_address": None,
                },
            ],
        }

    # ＜Normal_3_1＞
    # Filter: token_template (ibetBond)
    def test_normal_3_1(
        self,
        client: TestClient,
        session: Session,
    ):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_2
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_3
        _token_list_item.token_template = "ibetShare"
        _token_list_item.key_manager = ["1111111111111"]
        _token_list_item.product_type = 5
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_4
        _token_list_item.token_template = "ibetMembership"
        _token_list_item.key_manager = []
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_5
        _token_list_item.token_template = "ibetCoupon"
        _token_list_item.key_manager = []
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        session.commit()

        resp = client.get(self.api_url, params={"token_template": "ibetBond"})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 2, "limit": None, "offset": None, "total": 5},
            "tokens": [
                {
                    "key_manager": ["0000000000000"],
                    "product_type": 1,
                    "token_address": self.token_address_1,
                    "token_template": "ibetBond",
                    "issuer_address": None,
                },
                {
                    "key_manager": ["0000000000000"],
                    "product_type": 1,
                    "token_address": self.token_address_2,
                    "token_template": "ibetBond",
                    "issuer_address": None,
                },
            ],
        }

    # ＜Normal_3_2＞
    # Filter: token_template (ibetShare)
    def test_normal_3_2(
        self,
        client: TestClient,
        session: Session,
    ):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_2
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_3
        _token_list_item.token_template = "ibetShare"
        _token_list_item.key_manager = ["1111111111111"]
        _token_list_item.product_type = 5
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_4
        _token_list_item.token_template = "ibetMembership"
        _token_list_item.key_manager = []
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_5
        _token_list_item.token_template = "ibetCoupon"
        _token_list_item.key_manager = []
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        session.commit()

        resp = client.get(self.api_url, params={"token_template": "ibetShare"})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 5},
            "tokens": [
                {
                    "key_manager": ["1111111111111"],
                    "product_type": 5,
                    "token_address": self.token_address_3,
                    "token_template": "ibetShare",
                    "issuer_address": None,
                },
            ],
        }

    # ＜Normal_3_3＞
    # Filter: token_template (ibetMembership)
    def test_normal_3_3(
        self,
        client: TestClient,
        session: Session,
    ):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_2
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_3
        _token_list_item.token_template = "ibetShare"
        _token_list_item.key_manager = ["1111111111111"]
        _token_list_item.product_type = 5
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_4
        _token_list_item.token_template = "ibetMembership"
        _token_list_item.key_manager = []
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_5
        _token_list_item.token_template = "ibetCoupon"
        _token_list_item.key_manager = []
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        session.commit()

        resp = client.get(self.api_url, params={"token_template": "ibetMembership"})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 5},
            "tokens": [
                {
                    "key_manager": [],
                    "product_type": 1,
                    "token_address": self.token_address_4,
                    "token_template": "ibetMembership",
                    "issuer_address": None,
                },
            ],
        }

    # ＜Normal_3_4＞
    # Filter: token_template (ibetCoupon)
    def test_normal_3_4(
        self,
        client: TestClient,
        session: Session,
    ):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_2
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_3
        _token_list_item.token_template = "ibetShare"
        _token_list_item.key_manager = ["1111111111111"]
        _token_list_item.product_type = 5
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_4
        _token_list_item.token_template = "ibetMembership"
        _token_list_item.key_manager = []
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_5
        _token_list_item.token_template = "ibetCoupon"
        _token_list_item.key_manager = []
        _token_list_item.product_type = 1
        session.add(_token_list_item)

        session.commit()

        resp = client.get(self.api_url, params={"token_template": "ibetCoupon"})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 5},
            "tokens": [
                {
                    "key_manager": [],
                    "product_type": 1,
                    "token_address": self.token_address_5,
                    "token_template": "ibetCoupon",
                    "issuer_address": None,
                },
            ],
        }

    # ＜Normal_4＞
    # Offset
    def test_normal_4(
        self,
        client: TestClient,
        session: Session,
    ):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_2
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_3
        _token_list_item.token_template = "ibetShare"
        _token_list_item.key_manager = ["1111111111111"]
        _token_list_item.product_type = 5
        session.add(_token_list_item)
        session.commit()

        resp = client.get(self.api_url, params={"offset": 2})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 3, "limit": None, "offset": 2, "total": 3},
            "tokens": [
                {
                    "key_manager": ["1111111111111"],
                    "product_type": 5,
                    "token_address": self.token_address_3,
                    "token_template": "ibetShare",
                    "issuer_address": None,
                },
            ],
        }

    # ＜Normal_5＞
    # Limit
    def test_normal_5(
        self,
        client: TestClient,
        session: Session,
    ):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_2
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_3
        _token_list_item.token_template = "ibetShare"
        _token_list_item.key_manager = ["1111111111111"]
        _token_list_item.product_type = 5
        session.add(_token_list_item)
        session.commit()

        resp = client.get(self.api_url, params={"limit": 1})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 3, "limit": 1, "offset": None, "total": 3},
            "tokens": [
                {
                    "key_manager": ["0000000000000"],
                    "product_type": 1,
                    "token_address": self.token_address_1,
                    "token_template": "ibetBond",
                    "issuer_address": None,
                },
            ],
        }

    # ＜Normal_6＞
    # issuer_address (not null)
    def test_normal_6(
        self,
        client: TestClient,
        session: Session,
    ):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        _token_list_item.issuer_address = self.issuer_address_1
        session.add(_token_list_item)
        session.commit()

        resp = client.get(self.api_url, params={})

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "result_set": {"count": 1, "limit": None, "offset": None, "total": 1},
            "tokens": [
                {
                    "key_manager": ["0000000000000"],
                    "product_type": 1,
                    "token_address": self.token_address_1,
                    "token_template": "ibetBond",
                    "issuer_address": self.issuer_address_1,
                }
            ],
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # InvalidParameterError
    # event: unallowed value
    def test_error_1(self, client: TestClient, session: Session):
        resp = client.get(self.api_url, params={"token_template": "invalid_value"})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "literal_error",
                    "loc": ["query", "token_template"],
                    "msg": "Input should be 'ibetBond', 'ibetShare', 'ibetMembership' or 'ibetCoupon'",
                    "input": "invalid_value",
                    "ctx": {
                        "expected": "'ibetBond', 'ibetShare', 'ibetMembership' or 'ibetCoupon'"
                    },
                }
            ],
        }
