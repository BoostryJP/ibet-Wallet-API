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

import os
import sys

from migrate.versioning.shell import main
from migrate.exceptions import DatabaseAlreadyControlledError, DatabaseNotControlledError

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from app import config

if __name__ == '__main__':
    try:
        main(
            debug='False',
            url=config.DATABASE_URL,
            repository='.'
        )
        print("[INFO] Successfully completed.")
    except DatabaseAlreadyControlledError:
        print("[WARNING] The database has already been initialized.")
        print("[INFO] Successfully completed.")
    except DatabaseNotControlledError:
        print("[ERROR] The database has not been initialized.")
        exit(1)
    except Exception as err:
        print(f"[ERROR] {err}")
        exit(1)
