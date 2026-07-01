from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from app.schemas.sse_events import SSEEvent
from common.logger import my_logger

logger = my_logger


class EventEmitter:
    def __init__(self, task_id: str, queue: asyncio.Queue[SSEEvent | None]) -> None:
        self.task_id = task_id
        self.queue = queue
        self._seq = 0
        self._agent_log_buffers: dict[str, str] = {}
        self._agent_log_flush_size = 300

    def _task_tag(self) -> str:
        return f"[task:{self.task_id[:8]}]"

    def _flush_agent_buffer(self, agent: str, force: bool = False) -> None:
        buffer = self._agent_log_buffers.get(agent, "")
        if not buffer:
            return
        if not force and len(buffer) < self._agent_log_flush_size and "\n" not in buffer:
            return
        if "\n" in buffer:
            lines = buffer.split("\n")
            for line in lines[:-1]:
                if line.strip():
                    logger.info("%s [%s] %s", self._task_tag(), agent, line.strip())
            self._agent_log_buffers[agent] = lines[-1]
            return
        if force or len(buffer) >= self._agent_log_flush_size:
            logger.info("%s [%s] %s", self._task_tag(), agent, buffer.strip())
            self._agent_log_buffers[agent] = ""

    def _log_event(self, event_type: str, **data: Any) -> None:
        tag = self._task_tag()
        if event_type == "connected":
            logger.info("%s [connected] %s", tag, data.get("message", ""))
        elif event_type == "progress":
            logger.info(
                "%s [progress] [%s] %s (%s%%)",
                tag,
                data.get("stage", ""),
                data.get("message", ""),
                data.get("progress_percent", 0),
            )
        elif event_type == "agent_log":
            agent = str(data.get("agent", "agent"))
            content = str(data.get("content", ""))
            self._agent_log_buffers[agent] = self._agent_log_buffers.get(agent, "") + content
            self._flush_agent_buffer(agent)
        elif event_type == "stage_result":
            agent = str(data.get("agent", "agent"))
            self._flush_agent_buffer(agent, force=True)
            result = data.get("result") or {}
            score = result.get("overall_code_score") or result.get("overall_product_score")
            if score is not None:
                logger.info("%s [stage_result] %s 完成，评分: %s", tag, agent, score)
            else:
                logger.info("%s [stage_result] %s 阶段分析完成", tag, agent)
        elif event_type == "report_complete":
            report = data.get("report") or {}
            scores = report.get("scores") or {}
            logger.info(
                "%s [report_complete] %s 总分: %s (代码:%s 产品:%s)",
                tag,
                report.get("repo_name", ""),
                scores.get("total_score", "-"),
                scores.get("code_score", "-"),
                scores.get("product_score", "-"),
            )
        elif event_type == "cache_hit":
            logger.info("%s [cache_hit] %s", tag, data.get("message", ""))
        elif event_type == "error":
            logger.error(
                "%s [error] code=%s stage=%s %s",
                tag,
                data.get("code", ""),
                data.get("stage", ""),
                data.get("message", ""),
            )
        elif event_type == "done":
            for agent in list(self._agent_log_buffers):
                self._flush_agent_buffer(agent, force=True)
            self._agent_log_buffers.clear()
            logger.info("%s [done] %s", tag, data.get("message", ""))

    async def _emit(self, event_type: str, **data: Any) -> None:
        self._seq += 1
        self._log_event(event_type, **data)
        event = SSEEvent(event=event_type, task_id=self.task_id, data=data)
        await self.queue.put(event)

    async def emit_connected(self) -> None:
        await self._emit("connected", message="SSE 连接已建立")

    async def emit_progress(
        self, stage: str, status: str, message: str, progress_percent: int
    ) -> None:
        await self._emit(
            "progress",
            stage=stage,
            status=status,
            message=message,
            progress_percent=progress_percent,
        )

    async def emit_agent_log(
        self, agent: str, content: str, chunk_index: int, log_type: str = "thinking"
    ) -> None:
        await self._emit(
            "agent_log",
            agent=agent,
            log_type=log_type,
            content=content,
            chunk_index=chunk_index,
        )

    async def emit_stage_result(self, agent: str, result: dict[str, Any]) -> None:
        await self._emit("stage_result", agent=agent, result=result)

    async def emit_report_complete(self, report: dict[str, Any]) -> None:
        await self._emit("report_complete", report=report)

    async def emit_cache_hit(self, cached_at: str) -> None:
        await self._emit("cache_hit", cached_at=cached_at, message="该仓库已有分析结果，直接返回")

    async def emit_error(
        self, code: int, message: str, stage: str = "", recoverable: bool = False
    ) -> None:
        await self._emit("error", code=code, stage=stage, message=message, recoverable=recoverable)

    async def emit_done(self) -> None:
        await self._emit("done", message="分析流程结束")
        await self.queue.put(None)


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[SSEEvent | None]] = {}

    def create_emitter(self, task_id: str) -> EventEmitter:
        queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()
        self._queues[task_id] = queue
        return EventEmitter(task_id, queue)

    def get_queue(self, task_id: str) -> asyncio.Queue[SSEEvent | None] | None:
        return self._queues.get(task_id)

    async def stream_events(self, task_id: str) -> AsyncIterator[str]:
        queue = self.get_queue(task_id)
        if queue is None:
            return
        seq = 0
        while True:
            event = await queue.get()
            if event is None:
                break
            seq += 1
            yield event.to_sse(seq)

    def remove(self, task_id: str) -> None:
        self._queues.pop(task_id, None)


event_bus = EventBus()
