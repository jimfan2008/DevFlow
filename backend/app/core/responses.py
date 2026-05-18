#!/usr/bin/env python3
"""统一响应格式"""
from fastapi.responses import JSONResponse
from typing import Optional, Any


class APIResponse(JSONResponse):
    """统一 API 响应"""
    def __init__(self, code: int = 0, message: str = "success", data: Optional[Any] = None, meta: Optional[dict] = None):
        super().__init__(content={
            "code": code,
            "message": message,
            "data": data,
            "meta": meta,
        })


def success_response(data: Any = None, message: str = "success", **meta):
    """成功响应"""
    return {"success": True, "message": message, **(data if isinstance(data, dict) else {"data": data}), **meta}


def error_response(message: str, error: str = None, code: int = None):
    """错误响应"""
    result = {"success": False, "message": message}
    if error:
        result["error"] = error
    if code:
        result["code"] = code
    return result
