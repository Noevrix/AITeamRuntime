from datetime import datetime
from pydantic import Field
from .task import Model, uid, now


class Event(Model):
    id: str = Field(default_factory=uid)
    project_id: str
    task_id: str | None = None
    type: str
    timestamp: datetime = Field(default_factory=now)
    metadata: dict = Field(default_factory=dict)
