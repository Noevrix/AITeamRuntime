from pydantic import Field
from ai_team.protocol.task import Model, uid
from .role import Role


class Agent(Model):
    id: str
    name: str
    provider_id: str
    role: Role


class Team(Model):
    id: str = Field(default_factory=uid)
    name: str
    agent_ids: list[str]


class Project(Model):
    id: str = Field(default_factory=uid)
    team_id: str
    goal: str
    known_facts: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
