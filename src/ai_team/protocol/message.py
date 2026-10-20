from datetime import datetime
from enum import StrEnum
from pydantic import Field
from .task import Model, uid, now


class MessageType(StrEnum):
    PROPOSE = "PROPOSE"
    ASSIGN = "ASSIGN"
    ASK = "ASK"
    REVIEW = "REVIEW"
    CHALLENGE = "CHALLENGE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REVISE = "REVISE"
    TEST = "TEST"
    ESCALATE = "ESCALATE"
    COMPLETE = "COMPLETE"


class Message(Model):
    id: str = Field(default_factory=uid)
    project_id: str
    task_id: str
    parent_task_id: str | None = None
    from_agent: str
    to_agent: str
    type: MessageType
    content: str
    timestamp: datetime = Field(default_factory=now)
    metadata: dict = Field(default_factory=dict)
