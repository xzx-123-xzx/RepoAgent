from fastapi import APIRouter, HTTPException

from app.cache.redis_client import redis_client
from app.graph.task_registry import task_registry
from app.schemas.response import ReportResponse

router = APIRouter(prefix="/api/v1", tags=["report"])


@router.get("/report/{task_id}", response_model=ReportResponse)
async def get_report(task_id: str):
    task = task_registry.get(task_id)
    if not task:
        state = await redis_client.get_task_state(task_id)
        if state:
            return ReportResponse(task_id=task_id, status=state.get("status", "unknown"), report=state.get("report"))
        raise HTTPException(status_code=404, detail="任务不存在")

    return ReportResponse(task_id=task_id, status=task.status, report=task.report)


@router.get("/report/cache/{owner}/{repo}")
async def get_cached_report(owner: str, repo: str):
    report = await redis_client.get_cached_report(owner, repo)
    if not report:
        raise HTTPException(status_code=404, detail="无缓存报告")
    return report
