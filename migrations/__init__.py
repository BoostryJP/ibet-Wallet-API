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


def skip_based_on_legacy_engine_version(op, filename: str, is_downgrade=False):
    """
    This judges to upgrade/downgrade instances sqlalchemy-migrate migrations applied.
    """
    conf = op.get_context().config
    version = conf.get_main_option("sqlalchemy_migrate_version")
    if version:
        if int(version) == 0:
            # NOTE: If sqlalchemy-migrate is not used, then not skipped
            return False

        if is_downgrade is True:
            # NOTE: If sqlalchemy-migrate current version is less than migration file, downgrade is skipped
            return int(version) < int(filename.split("_", 1)[0])

        # NOTE: If sqlalchemy-migrate current version is equal or greater than migration file, upgrade is skipped
        return int(version) >= int(filename.split("_", 1)[0])
    return False
