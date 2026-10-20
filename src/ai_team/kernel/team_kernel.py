import asyncio
from pathlib import Path
from ai_team.agents.registry import AgentRegistry
from ai_team.config import Limits
from ai_team.memory.blackboard import Blackboard
from ai_team.protocol.task import Task, TaskStatus as S, now
from ai_team.protocol.message import Message, MessageType as M
from ai_team.providers.base import AgentProvider, ProviderError
from ai_team.providers.diagnostics import error_diagnostic
from .event_bus import EventBus
from .message_bus import MessageBus
from .task_manager import TaskManager


class LimitExceeded(RuntimeError):
    pass


class TeamKernel:
    def __init__(self, db, project, team, workspace: Path, limits=None):
        self.db, self.project, self.workspace = db, project, workspace
        self.limits = limits or Limits()
        self.registry = AgentRegistry()
        self.providers: dict[str, AgentProvider] = {}
        self.sessions = {}
        self.events = EventBus(db)
        self.messages = MessageBus(db, self.registry, self.events)
        self.tasks = TaskManager(db, self.events)
        self.blackboard = Blackboard(db)
        self.team = team
        db.put("teams", team)
        db.put("projects", project)
        self.turns = sum(e["type"] == "TURN_RESERVED" for e in db.list("events", project.id))
        self.lock = asyncio.Lock()

    def register(self, agent, provider):
        if agent.id not in self.team.agent_ids:
            raise ValueError("agent is not a team member")
        if agent.provider_id in self.providers and self.providers[agent.provider_id] is not provider:
            raise ValueError("provider id already bound")
        self.registry.register(agent)
        self.providers[agent.provider_id] = provider
        self.db.put("agents", agent)
        self.db.put("providers", {"id": agent.provider_id, "mock": provider.is_mock, "capabilities": provider.capabilities().model_dump()})

    def message(self, task, sender, recipient, kind, content, **metadata):
        value = Message(project_id=self.project.id, task_id=task.id, parent_task_id=task.parent_task, from_agent=sender, to_agent=recipient, type=kind, content=content, metadata=metadata)
        self.messages.send(value)
        return value

    def escalate(self, task, reason):
        self.tasks.transition(task.id, S.ESCALATED)
        self.message(task, "kernel", "user", M.ESCALATE, reason)
        raise LimitExceeded(reason)

    def create_task(self, title, agent_id, task_type, description="", parent=None):
        self.registry.get(agent_id)
        if parent:
            parent = self.tasks.get(parent.id)
            if parent.project_id != self.project.id:
                raise ValueError("cross-project delegation")
            if parent.depth >= self.limits.max_delegation_depth:
                self.escalate(parent, "delegation depth limit")
        task = Task(project_id=self.project.id, title=title, description=description, created_by=parent.assigned_to if parent else "user", assigned_to=agent_id, task_type=task_type, parent_task=parent.id if parent else None, depth=parent.depth + 1 if parent else 0)
        self.tasks.create(task)
        task = self.tasks.transition(task.id, S.ASSIGNED)
        self.message(task, task.created_by, agent_id, M.ASSIGN, description or title)
        return task

    def revise(self, original, description):
        original = self.tasks.get(original.id)
        if original.status != S.CHANGES_REQUESTED:
            raise ValueError("revision requires CHANGES_REQUESTED")
        if original.revision_count >= self.limits.max_revisions_per_task:
            self.escalate(original, "revision limit")
        revision = self.create_task("Revise: " + original.title, original.assigned_to, "REVISE", description, original)
        original.revision_count += 1
        original.updated_at = now()
        self.db.put("tasks", original)
        self.message(revision, "kernel", original.assigned_to, M.REVISE, description)
        return revision

    async def execute(self, task):
        task = self.tasks.get(task.id)
        if task.status != S.ASSIGNED:
            raise ValueError("task must be assigned")
        async with self.lock:
            if self.turns >= self.limits.max_agent_turns:
                self.escalate(task, "agent turn limit")
            self.turns += 1
            self.events.emit(self.project.id, "TURN_RESERVED", task.id, turn=self.turns)
        self.tasks.transition(task.id, S.RUNNING)
        agent = self.registry.get(task.assigned_to)
        provider = self.providers[agent.provider_id]
        session = self.sessions.get(agent.id)
        try:
            async with asyncio.timeout(self.limits.turn_timeout):
                if session is None:
                    session = await provider.create_session(agent.id, self.workspace)
                    self.sessions[agent.id] = session
                    self.db.put("sessions", {"id": session, "project_id": self.project.id, "agent_id": agent.id, "provider_id": agent.provider_id})
                result = await provider.send_task(session, task)
            self.message(task, agent.id, "kernel", result.type, result.content, mock=result.mock)
            self.tasks.transition(task.id, S.REVIEW if task.task_type in {"IMPLEMENT", "REVISE"} else S.COMPLETED)
            return result
        except BaseException as exc:
            if isinstance(exc, (TimeoutError, asyncio.CancelledError)) and session and provider.capabilities().task_cancel:
                try:
                    await asyncio.wait_for(provider.interrupt(session), 5)
                except Exception:
                    pass
            self.tasks.transition(task.id, S.CANCELLED if isinstance(exc, asyncio.CancelledError) else S.FAILED)
            self.events.emit(self.project.id, "PROVIDER_FAILURE", task.id,
                             error_type="ProviderError" if isinstance(exc, ProviderError) else error_diagnostic(exc).get("source_type", "OTHER"),
                             diagnostic=error_diagnostic(exc))
            raise

    async def close(self):
        for provider in self.providers.values():
            await provider.close()
