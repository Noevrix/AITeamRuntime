from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict


def now():
    return datetime.now(timezone.utc)


def uid():
    return uuid4().hex


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    REVIEW = "REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


class Task(Model):
    id: str = Field(default_factory=uid)
    project_id: str
    title: str
    description: str = ""
    created_by: str
    assigned_to: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    task_type: str = "IMPLEMENT"
    parent_task: str | None = None
    depth: int = Field(default=0, ge=0)
    revision_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
