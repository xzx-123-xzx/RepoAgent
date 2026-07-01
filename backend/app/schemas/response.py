from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnalyzeResponse(BaseModel):
    task_id: str
    stream_url: str
    status: str = "pending"
    created_at: datetime


class ReportResponse(BaseModel):
    task_id: str
    status: str
    report: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]
