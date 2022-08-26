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
from typing import (
    List,
    Dict,
    Any
)

from pydantic import BaseModel
from fastapi.openapi.utils import get_openapi
from fastapi.exceptions import RequestValidationError

from app.errors import (
    InvalidParameterError,
    DatabaseError,
    NotSupportedError,
    DataNotExistsError,
    SuspendedTokenError,
    DataConflictError,
    ServiceUnavailable
)


class MetaModel(BaseModel):
    code: int
    title: str


class Error400MetaModel(MetaModel):
    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["code"]["examples"] = [88, 20]
            properties["title"]["examples"] = ["InvalidParameterError", "SuspendedTokenError"]


class Error400Model(BaseModel):
    meta: Error400MetaModel
    detail: str


class Error404MetaModel(MetaModel):
    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["code"]["examples"] = [10, 30]
            properties["title"]["examples"] = ["DataNotExists", "NotSupported"]


class Error404Model(BaseModel):
    meta: Error404MetaModel
    detail: str


class Error409MetaModel(MetaModel):
    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["code"]["example"] = 40
            properties["title"]["example"] = "DataConflict"


class Error409Model(BaseModel):
    meta: Error409MetaModel
    detail: str


class Error422MetaModel(MetaModel):
    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["code"]["example"] = 1
            properties["title"]["example"] = "RequestValidationError"


class Error422DetailModel(BaseModel):
    loc: List[str]
    msg: str
    type: str

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["loc"]["example"] = ["header", "issuer-address"]  # FIXME
            properties["msg"]["example"] = "field required"
            properties["type"]["example"] = "value_error.missing"


class Error422Model(BaseModel):
    meta: Error422MetaModel
    detail: List[Error422DetailModel]


class Error500MetaModel(MetaModel):
    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["code"]["example"] = 500
            properties["title"]["example"] = "Unknown Error"


class Error500Model(BaseModel):
    meta: Error500MetaModel
    detail: str


class Error503MetaModel(MetaModel):
    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], _) -> None:
            properties = schema["properties"]
            properties["code"]["example"] = 503
            properties["title"]["example"] = "Service Unavailable"


class Error503Model(BaseModel):
    meta: Error503MetaModel
    detail: str


DEFAULT_RESPONSE = {
    400: {
        "description": "Invalid Parameter Error",
        "model": Error400Model
    },
    404: {
        "description": "Not Found Error",
        "model": Error404Model
    },
    409: {
        "description": "Data Conflict",
        "model": Error409Model
    },
    422: {
        "description": "RequestValidationError",
        "model": Error422Model
    },
    500: {
        "description": "InternalServerError",
        "model": Error500Model
    },
    503: {
        "description": "ServiceUnavailable",
        "model": Error503Model
    }
}


def get_routers_responses(*args):
    responses = {}
    for arg in args:
        if isinstance(arg, int):
            responses[arg] = DEFAULT_RESPONSE.get(arg, {})
        elif arg == InvalidParameterError:
            responses[400] = DEFAULT_RESPONSE[400]
        elif arg == SuspendedTokenError:
            responses[400] = DEFAULT_RESPONSE[400]
        elif arg == NotSupportedError:
            responses[404] = DEFAULT_RESPONSE[404]
        elif arg == DataNotExistsError:
            responses[404] = DEFAULT_RESPONSE[404]
        elif arg == DataConflictError:
            responses[409] = DEFAULT_RESPONSE[409]
        elif arg == RequestValidationError:
            responses[422] = DEFAULT_RESPONSE[422]
        elif arg == DatabaseError:
            responses[500] = DEFAULT_RESPONSE[500]
        elif arg == ServiceUnavailable:
            responses[503] = DEFAULT_RESPONSE[503]

    return responses


def custom_openapi(app):
    def openapi():
        openapi_schema = app.openapi_schema
        if openapi_schema is None:
            openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                description=app.description,
                routes=app.routes,
                tags=app.openapi_tags,
                servers=app.servers,
            )

        def _get(src: dict[str, Any], *keys):
            tmp_src = src
            for key in keys:
                ret = tmp_src.get(key)
                if ret is None:
                    return None
                tmp_src = ret
            return tmp_src

        paths = _get(openapi_schema, "paths")
        if paths is not None:
            for path_info in paths.values():
                for router in path_info.values():

                    # Remove Default Validation Error Response Structure
                    # NOTE:
                    # HTTPValidationError is automatically added to APIs docs that have path, header, query,
                    # and body parameters.
                    # But HTTPValidationError does not have 'meta',
                    # and some APIs do not generate a Validation Error(API with no-required string parameter only, etc).
                    resp_422 = _get(router, "responses", "422")
                    if resp_422 is not None:
                        ref = _get(resp_422, "content", "application/json", "schema", "$ref")
                        if ref == "#/components/schemas/HTTPValidationError":
                            router["responses"].pop("422")

                    # Remove empty response's contents
                    responses = _get(router, "responses")
                    for resp in responses.values():
                        schema = _get(resp, "content", "application/json", "schema")
                        if schema == {}:
                            resp.pop("content")

        return openapi_schema

    return openapi
