from pydantic import Field
from .task import Model, uid


class Artifact(Model):
    id: str = Field(default_factory=uid)
    project_id: str
    task_id: str
    path: str
    sha256: str
