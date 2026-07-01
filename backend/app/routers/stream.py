from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.graph.event_emitter import event_bus
from app.graph.task_registry import task_registry

router = APIRouter(prefix="/api/v1", tags=["stream"])


@router.get("/stream/{task_id}")
async def stream_analysis(task_id: str):
    if not task_registry.get(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")

    queue = event_bus.get_queue(task_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="SSE 通道不存在")

    async def event_generator():
        seq = 0
        while True:
            event = await queue.get()
            if event is None:
                break
            seq += 1
            yield event.to_sse(seq)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
