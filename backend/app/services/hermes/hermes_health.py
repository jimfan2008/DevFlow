from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, List, Optional

from app.services.hermes.types import HealthStatus
from app.services.hermes.hermes_api_client import HermesAPIClient

logger = logging.getLogger("devflow.hermes.health")


class HermesHealthChecker:
    def __init__(
        self,
        api_client: HermesAPIClient,
        interval: int = 30,
        debounce_count: int = 3,
        max_reconnect_attempts: int = 12,
    ):
        self._api = api_client
        self._interval = interval
        self._debounce_count = debounce_count
        self._max_reconnect = max_reconnect_attempts
        self._status: HealthStatus = "unknown"
        self._pending_status: Optional[HealthStatus] = None
        self._pending_count: int = 0
        self._task: Optional[asyncio.Task] = None
        self._reconnect_attempts: int = 0
        self._callbacks: List[Callable] = []
        self._last_check: Optional[datetime] = None

    @property
    def status(self) -> HealthStatus:
        return self._status

    def on_status_change(self, callback: Callable[[HealthStatus, HealthStatus], None]):
        self._callbacks.append(callback)

    async def start(self):
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._health_loop())
        logger.info("HermesHealthChecker started")

    async def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("HermesHealthChecker stopped")

    async def check_once(self) -> HealthStatus:
        try:
            ok = await self._api.health_check()
            return "online" if ok else "offline"
        except Exception:
            return "offline"

    def get_diagnostic_info(self) -> dict:
        return {
            "status": self._status,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "reconnect_attempts": self._reconnect_attempts,
        }

    async def _health_loop(self):
        while True:
            try:
                new_status = await self.check_once()
                self._last_check = datetime.now(timezone.utc)
                self._apply_debounced_status(new_status)

                if self._status == "online":
                    self._reconnect_attempts = 0
                elif self._status == "offline":
                    await self._try_reconnect()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

            await asyncio.sleep(self._interval)

    def _apply_debounced_status(self, new_status: HealthStatus):
        if new_status == self._status:
            self._pending_status = None
            self._pending_count = 0
            return

        if new_status == self._pending_status:
            self._pending_count += 1
        else:
            self._pending_status = new_status
            self._pending_count = 1

        if self._pending_count >= self._debounce_count:
            old = self._status
            self._status = new_status
            self._pending_status = None
            self._pending_count = 0
            logger.info(f"Hermes status changed: {old} → {new_status}")
            for cb in self._callbacks:
                try:
                    cb(old, new_status)
                except Exception as e:
                    logger.error(f"Status callback error: {e}")

    async def _try_reconnect(self):
        if self._reconnect_attempts >= self._max_reconnect:
            logger.warning(f"Max reconnect attempts ({self._max_reconnect}) reached")
            return
        self._reconnect_attempts += 1
        logger.info(f"Reconnect attempt {self._reconnect_attempts}/{self._max_reconnect}")
        await asyncio.sleep(10)
