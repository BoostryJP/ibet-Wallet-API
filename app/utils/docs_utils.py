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

from collections.abc import Callable
from functools import lru_cache
from typing import Any, Literal, Type, TypeGuard, TypeVar, Union, get_type_hints

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, create_model

from app.errors import AppError


class ErrorInfo(BaseModel):
    code: int = Field(...)
    message: str = Field(...)
    description: str | dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    meta: ErrorInfo
    details: dict[str, Any] | None = None


class RequestValidationErrorDict(BaseModel):
    loc: list[str]
    msg: str
    type: str


class RequestValidationErrorInfo(BaseModel):
    code: int = Field(..., examples=[88])
    message: str = Field(..., examples=["Invalid Parameter"])
    description: list[RequestValidationErrorDict]


class RequestValidationErrorResponse(BaseModel):
    meta: RequestValidationErrorInfo
    details: dict[str, Any] | None = None


AppErrorType = TypeVar("AppErrorType", bound=AppError)


@lru_cache(None)
def create_error_model(app_error: Type[AppError]) -> Type[ErrorResponse]:
    """
    This function creates Pydantic Model from AppError.
    * create_model() generates a different model each time when called,
      so cache is enabled.

    @param app_error: AppError defined in ibet-Wallet-API
    @return: pydantic Model created dynamically
    """

    base_name = app_error.error_type.replace(" ", "").replace("-", "").replace("/", "")
    description_hint = get_type_hints(app_error).get("description")
    if description_hint is not None:
        description = (
            description_hint,
            Field(default=None),
        )
    else:
        description = (dict[str, Any] | None, Field(default=None))
    metainfo_model = create_model(
        f"{base_name}Metainfo",
        message=(Literal[app_error.message], Field(..., examples=[app_error.message])),
        code=(
            Literal[app_error.error_code],
            Field(..., examples=[app_error.error_code]),
        ),
        description=description,
    )
    error_model = create_model(
        f"{base_name}Response",
        meta=(
            metainfo_model,
            Field(
                ...,
            ),
        ),
        details=(dict[str, Any] | None, Field(default=None, examples=[None])),
        __base__=ErrorResponse,
    )
    return error_model


def get_routers_responses(
    *args: Type[AppErrorType],
) -> dict[int | str, dict[str, Any]]:
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
    ret: dict[int | str, dict[str, Any]] = {
        400: {"model": RequestValidationErrorResponse}
    }
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


def custom_openapi(app: FastAPI) -> Callable[[], dict[str, Any]]:
    def openapi() -> dict[str, Any]:
        openapi_schema_raw = app.openapi_schema
        if openapi_schema_raw is None:
            openapi_schema_raw = get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                description=app.description,
                routes=app.routes,
                tags=app.openapi_tags,
                servers=app.servers,
            )
        openapi_schema: dict[str, object] = dict(openapi_schema_raw)

        def _is_str_dict(value: object) -> TypeGuard[dict[str, object]]:
            return isinstance(value, dict)

        def _is_list(value: object) -> TypeGuard[list[object]]:
            return isinstance(value, list)

        def _get(src: dict[str, object], *keys: str) -> object | None:
            tmp_src = src
            for idx, key in enumerate(keys):
                ret = tmp_src.get(key)
                if ret is None:
                    return None
                if idx == len(keys) - 1:
                    return ret
                if _is_str_dict(ret):
                    tmp_src = ret
                    continue
                return None
            return None

        paths = _get(openapi_schema, "paths")
        if _is_str_dict(paths):
            for path_info in paths.values():
                if not _is_str_dict(path_info):
                    continue
                for router in path_info.values():
                    if not _is_str_dict(router):
                        continue
                    # Remove Default Validation Error Response Structure
                    # NOTE:
                    # HTTPValidationError is automatically added to APIs docs that have path, header, query,
                    # and body parameters.
                    # But HTTPValidationError does not have 'meta',
                    # and some APIs do not generate a Validation Error(API with no-required string parameter only, etc).
                    resp_422 = _get(router, "responses", "422")
                    if _is_str_dict(resp_422):
                        ref = _get(
                            resp_422, "content", "application/json", "schema", "$ref"
                        )
                        if (
                            isinstance(ref, str)
                            and ref == "#/components/schemas/HTTPValidationError"
                        ):
                            responses = router.get("responses")
                            if _is_str_dict(responses):
                                responses.pop("422", None)

                    # Remove empty response's contents
                    responses = _get(router, "responses")
                    if _is_str_dict(responses):
                        for resp in responses.values():
                            if not _is_str_dict(resp):
                                continue
                            schema = _get(resp, "content", "application/json", "schema")
                            if schema == {}:
                                resp.pop("content", None)
                            if _is_str_dict(schema):
                                any_of = _get(schema, "anyOf")
                                if _is_list(any_of):
                                    ref_items: list[dict[str, object]] = []
                                    for item in any_of:
                                        if _is_str_dict(item) and "$ref" in item:
                                            ref_items.append(item)
                                        else:
                                            ref_items = []
                                            break
                                    if ref_items:
                                        schema["anyOf"] = sorted(
                                            ref_items,
                                            key=lambda item: str(item.get("$ref", "")),
                                        )

        return openapi_schema

    return openapi
