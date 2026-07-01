from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class TaskRecord:
    task_id: str
    repo_url: str
    owner: str
    repo: str
    status: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    report: dict[str, Any] | None = None
    error: str | None = None


class TaskRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._running_count = 0

    def create(self, task_id: str, repo_url: str, owner: str, repo: str) -> TaskRecord:
        record = TaskRecord(task_id=task_id, repo_url=repo_url, owner=owner, repo=repo)
        self._tasks[task_id] = record
        return record

    def get(self, task_id: str) -> TaskRecord | None:
        return self._tasks.get(task_id)

    def update_status(self, task_id: str, status: str) -> None:
        if task := self._tasks.get(task_id):
            task.status = status

    def set_report(self, task_id: str, report: dict[str, Any]) -> None:
        if task := self._tasks.get(task_id):
            task.report = report
            task.status = "completed"

    def set_error(self, task_id: str, error: str) -> None:
        if task := self._tasks.get(task_id):
            task.error = error
            task.status = "failed"

    def can_start(self, max_concurrent: int) -> bool:
        return self._running_count < max_concurrent

    def mark_running(self) -> None:
        self._running_count += 1

    def mark_done(self) -> None:
        self._running_count = max(0, self._running_count - 1)


task_registry = TaskRegistry()
