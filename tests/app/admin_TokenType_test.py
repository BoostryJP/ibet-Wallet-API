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

from app import config


class TestAdminTokenType:
    # テスト対象API
    apiurl = '/Admin/Tokens/Type'

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client: TestClient, session: Session):
        resp = client.get(self.apiurl)

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "IbetStraightBond": config.BOND_TOKEN_ENABLED,
            "IbetShare": config.SHARE_TOKEN_ENABLED,
            "IbetMembership": config.MEMBERSHIP_TOKEN_ENABLED,
            "IbetCoupon": config.COUPON_TOKEN_ENABLED
        }
