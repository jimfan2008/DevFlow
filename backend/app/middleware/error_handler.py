from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exceptions import DevFlowException
import logging
import traceback

logger = logging.getLogger("devflow.error_handler")


async def devflow_exception_handler(request: Request, exc: DevFlowException) -> JSONResponse:
    logger.error(f"DevFlowException: {exc.error_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.error_code,
            "message": exc.detail,
            "details": {},
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
            "details": {},
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    serializable_errors = []
    for e in errors:
        se = {"type": e.get("type"), "loc": list(e.get("loc", [])), "msg": e.get("msg"), "input": e.get("input")}
        if "ctx" in e and e["ctx"]:
            se["ctx"] = {k: str(v) for k, v in e["ctx"].items()}
        serializable_errors.append(se)
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {"errors": serializable_errors},
        },
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    logger.warning(f"ValueError: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "code": "BAD_REQUEST",
            "message": str(exc),
            "details": {},
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled exception: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "Internal server error",
            "details": {},
        },
    )


def register_error_handlers(app):
    app.add_exception_handler(DevFlowException, devflow_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
