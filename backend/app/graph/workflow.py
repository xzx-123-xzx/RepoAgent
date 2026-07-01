from __future__ import annotations

import asyncio
from typing import Any

from app.agents.code_auditor import CodeAuditorAgent
from app.agents.judge import JudgeAgent
from app.agents.product_analyst import ProductAnalystAgent
from app.cache.redis_client import redis_client
from app.config import get_settings
from app.graph.event_emitter import EventEmitter, event_bus
from app.graph.task_registry import task_registry
from app.services.repo_fetcher import RepoFetcher
from app.services.url_validator import parse_github_url
from app.utils.exceptions import RepoAgentError
from common.logger import my_logger

logger = my_logger


class AnalysisWorkflow:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.fetcher = RepoFetcher()
        self.agent_a = CodeAuditorAgent()
        self.agent_b = ProductAnalystAgent()
        self.agent_c = JudgeAgent()

    async def run(self, task_id: str, repo_url: str, emitter: EventEmitter) -> None:
        owner, repo = parse_github_url(repo_url)
        task_registry.update_status(task_id, "running")

        try:
            cached = await redis_client.get_cached_report(owner, repo)
            if cached:
                await emitter.emit_cache_hit(cached.get("analyzed_at", ""))
                await emitter.emit_report_complete(cached)
                task_registry.set_report(task_id, cached)
                await emitter.emit_done()
                return

            await emitter.emit_progress("fetch_data", "started", "正在拉取 GitHub 仓库数据...", 5)
            snapshot = await self.fetcher.fetch(owner, repo)
            await emitter.emit_progress("fetch_data", "completed", "仓库数据采集完成", 20)

            await emitter.emit_progress("agent_a", "started", "代码审计智能体分析中...", 25)
            code_report = await self.agent_a.run(snapshot, emitter)
            await emitter.emit_progress("agent_a", "completed", "代码审计完成", 50)

            await emitter.emit_progress("agent_b", "started", "产品价值智能体分析中...", 55)
            product_report = await self.agent_b.run(snapshot, emitter)
            await emitter.emit_progress("agent_b", "completed", "产品价值分析完成", 75)

            await emitter.emit_progress("agent_c", "started", "总分裁判汇总中...", 80)
            final_report = await self.agent_c.run_with_reports(snapshot, code_report, product_report, emitter)
            await emitter.emit_progress("agent_c", "completed", "汇总评分完成", 90)

            await emitter.emit_progress("finalize", "started", "生成最终报告...", 95)
            report_dict = final_report.model_dump()
            await redis_client.set_cached_report(owner, repo, report_dict)
            await redis_client.set_task_state(task_id, {"status": "completed", "report": report_dict})
            task_registry.set_report(task_id, report_dict)
            await emitter.emit_report_complete(report_dict)
            await emitter.emit_progress("finalize", "completed", "分析完成", 100)
            await emitter.emit_done()
        except RepoAgentError as exc:
            logger.error("Task %s failed: %s", task_id, exc.message)
            await emitter.emit_error(exc.code, exc.message, exc.stage, exc.recoverable)
            task_registry.set_error(task_id, exc.message)
            await emitter.emit_done()
        except Exception as exc:
            logger.exception("Task %s unexpected error", task_id)
            await emitter.emit_error(5000, str(exc), recoverable=False)
            task_registry.set_error(task_id, str(exc))
            await emitter.emit_done()
        finally:
            event_bus.remove(task_id)


async def start_analysis_task(task_id: str, repo_url: str) -> None:
    queue = event_bus.get_queue(task_id)
    if queue is None:
        emitter = event_bus.create_emitter(task_id)
    else:
        emitter = EventEmitter(task_id, queue)
    await emitter.emit_connected()
    workflow = AnalysisWorkflow()
    timeout = get_settings().TASK_TIMEOUT
    task_registry.mark_running()
    try:
        await asyncio.wait_for(workflow.run(task_id, repo_url, emitter), timeout=timeout)
    except asyncio.TimeoutError:
        from app.utils.exceptions import TaskTimeoutError

        err = TaskTimeoutError()
        await emitter.emit_error(err.code, err.message, recoverable=False)
        task_registry.set_error(task_id, err.message)
        await emitter.emit_done()
    finally:
        task_registry.mark_done()
