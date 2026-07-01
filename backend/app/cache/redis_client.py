import json
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings
from common.logger import my_logger

logger = my_logger


class RedisClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        if self._client is None:
            self._client = aioredis.Redis(
                host=self.settings.REDIS_HOST,
                port=self.settings.REDIS_PORT,
                password=self.settings.REDIS_PASSWORD or None,
                db=self.settings.REDIS_DB,
                decode_responses=True,
            )

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def ping(self) -> bool:
        try:
            await self.connect()
            return bool(await self._client.ping())
        except Exception as exc:
            logger.warning("Redis ping failed: %s", exc)
            return False

    def _report_key(self, owner: str, repo: str) -> str:
        return f"repoagent:report:{owner}/{repo}"

    def _task_key(self, task_id: str) -> str:
        return f"repoagent:task:{task_id}"

    async def get_cached_report(self, owner: str, repo: str) -> dict[str, Any] | None:
        await self.connect()
        data = await self._client.get(self._report_key(owner, repo))
        return json.loads(data) if data else None

    async def set_cached_report(self, owner: str, repo: str, report: dict[str, Any]) -> None:
        await self.connect()
        await self._client.setex(
            self._report_key(owner, repo),
            self.settings.REDIS_EXPIRE,
            json.dumps(report, ensure_ascii=False),
        )

    async def set_task_state(self, task_id: str, state: dict[str, Any]) -> None:
        await self.connect()
        await self._client.setex(self._task_key(task_id), 3600, json.dumps(state, ensure_ascii=False))

    async def get_task_state(self, task_id: str) -> dict[str, Any] | None:
        await self.connect()
        data = await self._client.get(self._task_key(task_id))
        return json.loads(data) if data else None


redis_client = RedisClient()
