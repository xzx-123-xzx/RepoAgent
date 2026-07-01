import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.config import get_settings
from app.graph.task_registry import task_registry
from app.graph.workflow import start_analysis_task
from app.schemas.request import AnalyzeRequest
from app.schemas.response import AnalyzeResponse
from app.services.url_validator import parse_github_url
from app.utils.exceptions import InvalidUrlError

router = APIRouter(prefix="/api/v1", tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse, status_code=202)
async def create_analysis(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    settings = get_settings()
    if not task_registry.can_start(settings.MAX_CONCURRENT_TASKS):
        raise HTTPException(status_code=503, detail="当前分析任务过多，请稍后重试")

    try:
        owner, repo = parse_github_url(request.repo_url)
    except InvalidUrlError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    task_id = str(uuid.uuid4())
    task_registry.create(task_id, request.repo_url, owner, repo)

    # Create emitter queue before background task starts
    from app.graph.event_emitter import event_bus

    event_bus.create_emitter(task_id)

    background_tasks.add_task(start_analysis_task, task_id, request.repo_url)

    return AnalyzeResponse(
        task_id=task_id,
        stream_url=f"/api/v1/stream/{task_id}",
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
