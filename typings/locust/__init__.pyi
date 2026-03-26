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

from typing import Any, Callable, Protocol, TypeVar, overload

class Response(Protocol):
    content: bytes

class HttpSession(Protocol):
    def get(self, url: str, **kwargs: Any) -> Response: ...
    def post(self, url: str, **kwargs: Any) -> Response: ...

class TaskSet:
    client: HttpSession

class HttpLocust:
    task_set: type[TaskSet]
    min_wait: int
    max_wait: int

F = TypeVar("F", bound=Callable[..., Any])

@overload
def task(weight: int = ...) -> Callable[[F], F]: ...
@overload
def task(func: F) -> F: ...
