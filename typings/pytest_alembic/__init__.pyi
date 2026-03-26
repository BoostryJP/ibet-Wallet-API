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

class AlembicConfig:
    def set_main_option(self, name: str, value: str) -> None: ...

class Config:
    alembic_config: AlembicConfig

class MigrationContext:
    config: Config

    def migrate_up_to(self, revision: str) -> str | None: ...
    def migrate_down_to(self, revision: str) -> str | None: ...
