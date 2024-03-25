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

from functools import lru_cache
from typing import Any, Type, TypeVar, Union

from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, create_model

from app.errors import AppError


class ErrorInfo(BaseModel):
    code: int = Field(...)
    message: str = Field(...)
    description: str | dict | None = None


class ErrorResponse(BaseModel):
    meta: ErrorInfo
    details: dict | None = None


class RequestValidationErrorDict(BaseModel):
    loc: list[str]
    msg: str
    type: str


class RequestValidationErrorInfo(ErrorInfo):
    code: int = Field(..., examples=[88])
    message: str = Field(..., examples=["Invalid Parameter"])
    description: list[RequestValidationErrorDict]


class RequestValidationErrorResponse(BaseModel):
    meta: RequestValidationErrorInfo
    details: dict | None = None


AppErrorType = TypeVar("AppErrorType", bound=AppError)


@lru_cache(None)
def create_error_model(app_error: Type[AppError]):
    """
    This function creates Pydantic Model from AppError.
    * create_model() generates a different model each time when called,
      so cache is enabled.

    @param app_error: AppError defined in ibet-Wallet-API
    @return: pydantic Model created dynamically
    """

    metainfo_model = create_model(
        f"{app_error.error_type.strip()}Metainfo",
        code=(int, Field(..., examples=[app_error.error_code])),
        message=(str, Field(..., examples=[app_error.message])),
    )
    error_model = create_model(
        f"{app_error.error_type.strip()}Response",
        meta=(
            metainfo_model,
            Field(
                ...,
            ),
        ),
        details=(dict | None, Field(default=None, examples=[None])),
    )
    return error_model


def get_routers_responses(*args: Type[AppErrorType]):
    """
    This function returns responses dictionary to be used for openapi document.
    Supposed to be used in router decorator.

    @param args: tuple of AppError
    @return: responses dict
    """
    responses_per_status_code: dict[int, list[Type[AppError]]] = {}
    for arg in args:
        if not responses_per_status_code.get(arg.status_code):
            responses_per_status_code[arg.status_code] = [arg]
        else:
            responses_per_status_code[arg.status_code].append(arg)

    # NOTE: set RequestValidationError as default 400 error
    ret: dict[int, dict] = {400: {"model": RequestValidationErrorResponse}}
    for status_code, res in responses_per_status_code.items():
        error_models: list[Type[ErrorResponse]] = []
        for response in res:
            error_models.append(create_error_model(response))

        if len(error_models) > 0:
            if status_code == 400:
                ret[status_code] = {
                    "model": Union[
                        tuple(error_models) + (RequestValidationErrorResponse,)
                    ]
                }
            else:
                ret[status_code] = {"model": Union[tuple(error_models)]}
    return ret


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
                        ref = _get(
                            resp_422, "content", "application/json", "schema", "$ref"
                        )
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
