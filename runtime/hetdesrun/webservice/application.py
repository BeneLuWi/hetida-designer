# -*- coding: utf-8 -*-
from typing import Callable
import logging
import json

from fastapi import FastAPI, HTTPException

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware

from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response


from hetdesrun import VERSION
from hetdesrun.webservice.config import runtime_config

from hetdesrun.service.runtime_router import runtime_router

from hetdesrun.adapters.local_file.webservice import local_file_adapter_router

from hetdesrun.backend.service.info_router import info_router
from hetdesrun.backend.service.adapter_router import adapter_router
from hetdesrun.backend.service.base_item_router import base_item_router
from hetdesrun.backend.service.transformation_router import transformation_router
from hetdesrun.backend.service.component_router import component_router
from hetdesrun.backend.service.workflow_router import workflow_router
from hetdesrun.backend.service.wiring_router import wiring_router
from hetdesrun.backend.service.documentation_router import documentation_router


if runtime_config.hd_kafka_consumer_enabled:
    from hetdesrun.backend.kafka.consumer import get_kafka_worker_context


logger = logging.getLogger(__name__)


class AdditionalLoggingRoute(APIRoute):
    """Additional logging and information in case of errors

    Makes sure that requests are logged in every situation.
    """

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                json_data = await request.json()
            except json.decoder.JSONDecodeError:
                body = await request.body()
                logger.info(
                    "RECEIVED BODY (could not parse as json):\n%s", body.decode()
                )
            else:
                logger.info(
                    "RECEIVED JSON BODY: \n%s",
                    json.dumps(json_data, indent=2, sort_keys=True),
                )
            try:
                return await original_route_handler(request)  # type: ignore
            except RequestValidationError as exc:
                body = await request.body()
                detail = {"errors": exc.errors(), "body": body.decode()}
                logger.info("Request Validation Error: %s", str(exc))
                raise HTTPException(  # pylint: disable=raise-missing-from
                    status_code=422, detail=detail
                )

        return custom_route_handler


middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=runtime_config.allowed_origins.split(","),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
]


def app_desc_part() -> str:
    if runtime_config.is_backend_service and runtime_config.is_runtime_service:
        return "Runtime + Backend"
    if runtime_config.is_backend_service and not runtime_config.is_runtime_service:
        return "Backend"
    return "Runtime"


app = FastAPI(
    title="Hetida Designer " + app_desc_part() + " API",
    description="Hetida Designer " + app_desc_part() + " Web Services API",
    version=VERSION,
    root_path=runtime_config.swagger_prefix,
    middleware=middleware,
)

app.router.route_class = AdditionalLoggingRoute


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.info("Request validation failed:\n%s", str(exc))
    return await request_validation_exception_handler(request, exc)


if runtime_config.is_runtime_service:
    app.include_router(local_file_adapter_router)
    app.include_router(runtime_router, prefix="/engine")

if runtime_config.is_backend_service:
    app.include_router(adapter_router, prefix="/api")
    app.include_router(base_item_router, prefix="/api")
    app.include_router(documentation_router, prefix="/api")
    app.include_router(info_router, prefix="/api")
    app.include_router(component_router, prefix="/api")
    app.include_router(workflow_router, prefix="/api")
    app.include_router(wiring_router, prefix="/api")
    app.include_router(transformation_router, prefix="/api")


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Initializing application ...")
    if runtime_config.hd_kafka_consumer_enabled and runtime_config.is_backend_service:
        logger.info("Initializing Kafka consumer...")
        kakfa_worker_context = get_kafka_worker_context()
        await kakfa_worker_context.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Shutting down application...")
    if runtime_config.hd_kafka_consumer_enabled and runtime_config.is_backend_service:
        logger.info("Shutting down Kafka consumer...")
        kakfa_worker_context = get_kafka_worker_context()
        await kakfa_worker_context.stop()
