"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

from requests.adapters import HTTPAdapter
from urllib3 import Retry


def get_retry_adapter() -> HTTPAdapter:
    return HTTPAdapter(
        max_retries=Retry(
            total=3,
            backoff_factor=1.0,
            backoff_jitter=0.5,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
    )
