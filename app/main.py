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
from fastapi import (
    FastAPI,
    Request,
    status
)
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app import log
from app.config import BRAND_NAME
from app.api.routers import (
    admin as routers_admin,
    node_info as routers_node_info,
    contract_abi as routers_contract_abi,
    company_info as routers_company_info,
    user_info as routers_user_info,
    eth as routers_eth,
    token_bond as routers_token_bond,
    token_share as routers_token_share,
    token_membership as routers_token_membership,
    token_coupon as routers_token_coupon,
    token as routers_token,
    position as routers_position,
    notification as routers_notification,
    e2e_message as routers_e2e_message,
    events as routers_events,
    dex_market as routers_dex_market,
    dex_order_list as routers_dex_order_list
)
from app.errors import (
    AppError,
    InvalidParameterError,
    SuspendedTokenError,
    NotSupportedError,
    DataNotExistsError,
    DataConflictError,
    ServiceUnavailable
)
from app.middleware import (
    ResponseLoggerMiddleware,
    StripTrailingSlashMiddleware
)
from app.utils.docs_utils import custom_openapi

LOG = log.get_logger()

tags_metadata = [
    {
        "name": "Root"
    },
    {
        "name": "Admin",
        "description": "System administration"
    },
    {
        "name": "NodeInfo",
        "description": "Information about blockchain and contracts"
    },
    {
        "name": "ABI",
        "description": "Contract ABIs"
    },
    {
        "name": "Companies",
        "description": "Company information"
    },
    {
        "name": "User",
        "description": "User information"
    },
    {
        "name": "Eth",
        "description": "Blockchain Transactions"
    },
    {
        "name": "Token",
        "description": "Attribute information of the listed tokens"
    },
    {
        "name": "Position",
        "description": "Token balance held by the user"
    },
    {
        "name": "Notifications",
        "description": "Notifications for users"
    },
    {
        "name": "E2EMessage",
        "description": "Features related to the E2EMessaging contract"
    },
    {
        "name": "Events",
        "description": "Contract event logs"
    },
    {
        "name": "IbetExchange",
        "description": "Trade related features on IbetExchange"
    }
]

app = FastAPI(
    title="ibet Wallet API",
    terms_of_service="",
    version="22.9.0",
    contact={"email": "dev@boostry.co.jp"},
    license_info={"name": "Apache 2.0", "url": "http://www.apache.org/licenses/LICENSE-2.0.html"},
    openapi_tags=tags_metadata
)

app.openapi = custom_openapi(app)  # type: ignore


###############################################################
# ROUTER
###############################################################

@app.get("/", tags=["Root"])
def root():
    return {"server": BRAND_NAME}


app.include_router(routers_admin.router)
app.include_router(routers_node_info.router)
app.include_router(routers_contract_abi.router)
app.include_router(routers_company_info.router)
app.include_router(routers_user_info.router)
app.include_router(routers_eth.router)
app.include_router(routers_token_bond.router)
app.include_router(routers_token_share.router)
app.include_router(routers_token_membership.router)
app.include_router(routers_token_coupon.router)
app.include_router(routers_token.router)
app.include_router(routers_position.router)
app.include_router(routers_notification.router)
app.include_router(routers_e2e_message.router)
app.include_router(routers_events.router)
app.include_router(routers_dex_market.router)
app.include_router(routers_dex_order_list.router)


###############################################################
# MIDDLEWARE
###############################################################

response_logger = ResponseLoggerMiddleware()
strip_trailing_slash = StripTrailingSlashMiddleware()
app.add_middleware(BaseHTTPMiddleware, dispatch=strip_trailing_slash)
app.add_middleware(BaseHTTPMiddleware, dispatch=response_logger)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


###############################################################
# EXCEPTION
###############################################################

# 500:InternalServerError
@app.exception_handler(Exception)
async def internal_server_error_handler(request: Request, exc: Exception):
    meta = {
        "code": 1,
        "title": "InternalServerError"
    }
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder({"meta": meta}),
    )


# 400:InvalidParameterError
@app.exception_handler(InvalidParameterError)
async def invalid_parameter_error_handler(request: Request, exc: InvalidParameterError):
    meta = {
        "code": exc.error_code,
        "message": exc.message
    }
    if getattr(exc, "description"):
        meta["description"] = exc.description

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"meta": meta}),
    )


# 400:SuspendedTokenError
@app.exception_handler(SuspendedTokenError)
async def send_transaction_error_handler(request: Request, exc: SuspendedTokenError):
    meta = {
        "code": exc.error_code,
        "message": exc.message,
        "description": exc.description
    }
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder({"meta": meta}),
    )


# 404:NotSupported
@app.exception_handler(NotSupportedError)
async def not_supported_error_handler(request: Request, exc: NotSupportedError):
    meta = {
        "code": exc.error_code,
        "message": exc.message,
        "description": exc.description
    }
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=jsonable_encoder({"meta": meta}),
    )


# 400-503: AppError
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    meta = {
        "code": exc.error_code,
        "message": exc.message
    }
    if getattr(exc, "description"):
        meta["description"] = exc.description

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"meta": meta}),
    )


# 404:NotFound
@app.exception_handler(404)
async def not_found_error_handler(request: Request, exc: StarletteHTTPException):
    meta = {
        "code": 1,
        "message": "NotFound"
    }
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=jsonable_encoder({"meta": meta, "detail": exc.detail}),
    )


# 405:MethodNotAllowed
@app.exception_handler(405)
async def method_not_allowed_error_handler(request: Request, exc: StarletteHTTPException):
    meta = {
        "code": 1,
        "message": "Method Not Allowed",
        "description": f"method: {request.method}, url: {request.url.path}"
    }
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content=jsonable_encoder({"meta": meta}),
    )


# 409:DataConflict
@app.exception_handler(DataConflictError)
async def data_conflict_error_handler(request: Request, exc: DataConflictError):
    meta = {
        "code": exc.error_code,
        "message": exc.message
    }
    if getattr(exc, "description"):
        meta["description"] = exc.description

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=jsonable_encoder({"meta": meta}),
    )


# 404:DataNotExistsError
@app.exception_handler(DataNotExistsError)
async def data_not_exists_error_handler(request: Request, exc: DataNotExistsError):
    meta = {
        "code": exc.error_code,
        "message": exc.message
    }
    if getattr(exc, "description"):
        meta["description"] = exc.description
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=jsonable_encoder({"meta": meta}),
    )


# 422:RequestValidationError
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    meta = {
        "code": 1,
        "message": "Request Validation Error",
        "description": exc.errors()
    }
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder({"meta": meta}),
    )


# 503:ServiceUnavailable
@app.exception_handler(ServiceUnavailable)
async def service_unavailable_error_handler(request: Request, exc: ServiceUnavailable):
    meta = {
        "code": 503,
        "message": "Service Unavailable",
        "description": exc.description
    }
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=jsonable_encoder({"meta": meta}),
    )

LOG.info("Service started successfully")
