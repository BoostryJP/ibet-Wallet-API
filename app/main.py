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

import ctypes
from contextlib import asynccontextmanager
from ctypes.util import find_library
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from pydantic_core import ArgsKwargs, ErrorDetails
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from app import log
from app.api.routers import (
    admin as routers_admin,
    bc_explorer as routers_bc_explorer,
    company_info as routers_company_info,
    contract_abi as routers_contract_abi,
    dex_market as routers_dex_market,
    dex_order_list as routers_dex_order_list,
    e2e_message as routers_e2e_message,
    eth as routers_eth,
    events as routers_events,
    messaging as routers_mail,
    node_info as routers_node_info,
    notification as routers_notification,
    position as routers_position,
    position_lock as routers_position_lock,
    public_info as routers_public_info,
    token as routers_token,
    token_bond as routers_token_bond,
    token_coupon as routers_token_coupon,
    token_lock as routers_token_lock,
    token_membership as routers_token_membership,
    token_share as routers_token_share,
    user_info as routers_user_info,
)
from app.config import BRAND_NAME, PROFILING_MODE
from app.errors import (
    AppError,
    DataConflictError,
    DataNotExistsError,
    InvalidParameterError,
    NotSupportedError,
    ServiceUnavailable,
    SuspendedTokenError,
)
from app.middleware import (
    CacheControlMiddleware,
    ResponseLoggerMiddleware,
    StripTrailingSlashMiddleware,
)
from app.utils import o11y
from app.utils.docs_utils import custom_openapi

LOG = log.get_logger()

tags_metadata: list[dict[str, str]] = [
    {"name": "root", "description": ""},
    {
        "name": "public_info",
        "description": "Public shared information within the ibet consortium",
    },
    {
        "name": "company_info",
        "description": "Public information about ibet token issuers",
    },
    {"name": "admin", "description": "System administration"},
    {"name": "node_info", "description": "Information about blockchain and contracts"},
    {"name": "abi", "description": "Contract ABIs"},
    {"name": "eth_rpc", "description": "Ethereum RPC"},
    {"name": "token_info", "description": "Detailed information for listed tokens"},
    {"name": "user_info", "description": "User information"},
    {"name": "user_position", "description": "User's token balance"},
    {"name": "user_notification", "description": "Notifications for users"},
    {"name": "contract_log", "description": "Contract event logs"},
    {
        "name": "dex",
        "description": "Trade related functions on IbetExchange (Only for utility tokens)",
    },
    {"name": "messaging", "description": "Messaging functions with external systems"},
]


def on_startup() -> None:
    if PROFILING_MODE is True:
        o11y.setup_pyroscope()


async def on_shutdown() -> None:
    pass


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    on_startup()
    yield
    await on_shutdown()


app = FastAPI(
    title="ibet Wallet API",
    description="RPC services that provides utility tools for building a wallet system on ibet network",
    terms_of_service="",
    version="25.12.0",
    contact={"email": "dev@boostry.co.jp"},
    license_info={
        "name": "Apache 2.0",
        "url": "http://www.apache.org/licenses/LICENSE-2.0.html",
    },
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

app.openapi = custom_openapi(app)  # type: ignore

libc = ctypes.CDLL(find_library("c"))


###############################################################
# ROUTER
###############################################################


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    libc.malloc_trim(0)
    return {"server": BRAND_NAME}


app.include_router(routers_public_info.router)
app.include_router(routers_company_info.router)
app.include_router(routers_admin.router)
app.include_router(routers_node_info.router)
app.include_router(routers_bc_explorer.router)
app.include_router(routers_contract_abi.router)
app.include_router(routers_user_info.router)
app.include_router(routers_eth.router)
app.include_router(routers_token_bond.router)
app.include_router(routers_token_share.router)
app.include_router(routers_token_membership.router)
app.include_router(routers_token_coupon.router)
app.include_router(routers_token.router)
app.include_router(routers_token_lock.router)
app.include_router(routers_position_lock.router)
app.include_router(routers_position.router)
app.include_router(routers_notification.router)
app.include_router(routers_e2e_message.router)
app.include_router(routers_mail.router)
app.include_router(routers_events.router)
app.include_router(routers_dex_market.router)
app.include_router(routers_dex_order_list.router)


###############################################################
# MIDDLEWARE
###############################################################

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CacheControlMiddleware)
app.add_middleware(ResponseLoggerMiddleware)
app.add_middleware(StripTrailingSlashMiddleware)

if PROFILING_MODE is True:
    o11y.setup_otel(app=app)

###############################################################
# EXCEPTION
###############################################################


# 500:InternalServerError
@app.exception_handler(Exception)
async def internal_server_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    meta = {"code": 1, "title": "InternalServerError"}
    LOG.error(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder({"meta": meta}),
    )


# 429:TooManyRequests
@app.exception_handler(OperationalError)
async def too_many_request_error_handler(
    request: Request, exc: OperationalError
) -> JSONResponse:
    meta = {"code": 1, "title": "TooManyRequestsError"}
    orig = exc.orig
    if orig is not None and orig.args == ("FATAL:  sorry, too many clients already\n",):
        # NOTE: If postgres is used and has run out of connections, exception above would be thrown.

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=jsonable_encoder({"meta": meta}),
        )
    elif orig is not None and orig.args and orig.args[0] == 1040:
        # NOTE: If MySQL is used and has run out of connections, exception below would be thrown.
        #       sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (1040, 'Too many connections')
        #       sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) (1040, 'ny connections')

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=jsonable_encoder({"meta": meta}),
        )
    raise exc from None


# 400:InvalidParameterError
@app.exception_handler(InvalidParameterError)
async def invalid_parameter_error_handler(
    request: Request, exc: InvalidParameterError
) -> JSONResponse:
    meta = (
        {"code": exc.error_code, "message": exc.message, "description": exc.description}
        if exc.description
        else {"code": exc.error_code, "message": exc.message}
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"meta": meta}),
    )


# 400:SuspendedTokenError
@app.exception_handler(SuspendedTokenError)
async def send_transaction_error_handler(
    request: Request, exc: SuspendedTokenError
) -> JSONResponse:
    meta = {
        "code": exc.error_code,
        "message": exc.message,
        "description": exc.description,
    }
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder({"meta": meta}),
    )


# 404:NotSupported
@app.exception_handler(NotSupportedError)
async def not_supported_error_handler(
    request: Request, exc: NotSupportedError
) -> JSONResponse:
    meta = {
        "code": exc.error_code,
        "message": exc.message,
        "description": exc.description,
    }
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=jsonable_encoder({"meta": meta}),
    )


# 400-503: AppError
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    meta = (
        {"code": exc.error_code, "message": exc.message, "description": exc.description}
        if exc.description
        else {"code": exc.error_code, "message": exc.message}
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"meta": meta}),
    )


# 404:NotFound
@app.exception_handler(404)
async def not_found_error_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    meta = {"code": 1, "message": "NotFound"}
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=jsonable_encoder({"meta": meta, "detail": exc.detail}),
    )


# 405:MethodNotAllowed
@app.exception_handler(405)
async def method_not_allowed_error_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    meta = {
        "code": 1,
        "message": "Method Not Allowed",
        "description": f"method: {request.method}, url: {request.url.path}",
    }
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content=jsonable_encoder({"meta": meta}),
    )


# 409:DataConflict
@app.exception_handler(DataConflictError)
async def data_conflict_error_handler(
    request: Request, exc: DataConflictError
) -> JSONResponse:
    meta = (
        {"code": exc.error_code, "message": exc.message, "description": exc.description}
        if exc.description
        else {"code": exc.error_code, "message": exc.message}
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=jsonable_encoder({"meta": meta}),
    )


# 404:DataNotExistsError
@app.exception_handler(DataNotExistsError)
async def data_not_exists_error_handler(
    request: Request, exc: DataNotExistsError
) -> JSONResponse:
    meta = (
        {"code": exc.error_code, "message": exc.message, "description": exc.description}
        if exc.description
        else {"code": exc.error_code, "message": exc.message}
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=jsonable_encoder({"meta": meta}),
    )


def convert_errors(
    e: ValidationError | RequestValidationError,
) -> list[ErrorDetails]:
    new_errors: list[ErrorDetails] = []
    for error in e.errors():
        # "url" field which Pydantic V2 adds when validation error occurs is not needed for API response.
        # https://docs.pydantic.dev/2.1/errors/errors/
        if "url" in error.keys():
            error.pop("url", None)

        # "input" field generated from GET query model_validator is ArgsKwargs instance.
        # This cannot be serialized to json as it is, so nested field should be picked.
        # https://docs.pydantic.dev/2.1/errors/errors/
        if "input" in error.keys() and isinstance(error["input"], ArgsKwargs):
            error["input"] = error["input"].kwargs
        new_errors.append(error)
    return new_errors


# 400:RequestValidationError
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    meta = {
        "code": 88,
        "message": "Invalid Parameter",
        "description": convert_errors(exc),
    }
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder({"meta": meta}),
    )


# 400:ValidationError
# NOTE: for exceptions raised directly from Pydantic validation
@app.exception_handler(ValidationError)
async def query_validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    meta = {
        "code": 88,
        "message": "Invalid Parameter",
        "description": convert_errors(exc),
    }
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder({"meta": meta}),
    )


# 503:ServiceUnavailable
@app.exception_handler(ServiceUnavailable)
async def service_unavailable_error_handler(
    request: Request, exc: ServiceUnavailable
) -> JSONResponse:
    meta = {
        "code": 503,
        "message": "Service Unavailable",
        "description": exc.description,
    }
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=jsonable_encoder({"meta": meta}),
    )


LOG.info("Service started successfully")
