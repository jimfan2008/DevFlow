#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - 请求日志中间件
"""

import time
import logging
import traceback

logger = logging.getLogger("devflow")


class LoggingMiddleware:
    """请求日志中间件"""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        try:
            await self.app(scope, receive, send)
        except Exception:
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {method} {path}",
                extra={"duration": duration, "error": traceback.format_exc()},
            )
            raise

        duration = time.time() - start_time
        status = getattr(scope, "get", lambda k, d=None: d)("status", 0)
        logger.info(
            f"Request completed: {method} {path} {status} ({duration:.3f}s)",
        )
