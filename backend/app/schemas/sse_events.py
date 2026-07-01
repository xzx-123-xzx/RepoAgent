from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SSEEvent(BaseModel):
    event: str
    task_id: str
    timestamp: str = Field(default_factory=utc_now_iso)
    data: dict[str, Any] = Field(default_factory=dict)

    def to_sse(self, event_id: int) -> str:
        payload = {"event": self.event, "task_id": self.task_id, "timestamp": self.timestamp, **self.data}
        import json

        return f"event: {self.event}\nid: {event_id}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
