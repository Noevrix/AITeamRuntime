import asyncio
import pytest
from pydantic import ValidationError
from ai_team.protocol.task import TaskStatus as S
from ai_team.protocol.message import Message, MessageType as M
from ai_team.kernel.team_kernel import LimitExceeded, TeamKernel
from ai_team.agents.agent import Agent
from ai_team.agents.role import Role
from ai_team.providers.base import ProviderError
from ai_team.providers.codex.adapter import CodexAdapter
from ai_team.providers.workbuddy.adapter import WorkBuddyAdapter
from ai_team.config import Limits


def test_transition_rejects_jump_and_terminal_change(kernel):
    task = kernel.create_task("work", "a", "IMPLEMENT")
    with pytest.raises(ValueError):
        kernel.tasks.transition(task.id, S.COMPLETED)
    kernel.tasks.transition(task.id, S.RUNNING)
    kernel.tasks.transition(task.id, S.REVIEW)
    kernel.tasks.transition(task.id, S.COMPLETED)
    with pytest.raises(ValueError):
        kernel.tasks.transition(task.id, S.RUNNING)


def test_message_roundtrip_and_routing(kernel):
    task = kernel.create_task("work", "a", "PLAN")
    message = kernel.message(task, "a", "b", M.ASK, "clarify", purpose="question")
    assert Message.model_validate_json(message.model_dump_json()) == message
    with pytest.raises(KeyError):
        kernel.message(task, "a", "unknown", M.ASK, "invalid")
    with pytest.raises(ValidationError):
        Message.model_validate({**message.model_dump(), "type": "invented"})
    with pytest.raises(ValueError):
        kernel.messages.send(message.model_copy(update={"project_id": "other"}))


def test_registry_shared_provider(kernel):
    assert len(kernel.registry.agents) == 2
    assert len(kernel.providers) == 1
    with pytest.raises(ValueError):
        kernel.register(Agent(id="a", name="duplicate", provider_id="shared", role=Role.ENGINEER), kernel.providers["shared"])


def test_capabilities_and_unconfigured():
    assert CodexAdapter().capabilities().persistent_session
    unavailable = WorkBuddyAdapter()
    assert not unavailable.capabilities().file_access
    assert not asyncio.run(unavailable.health_check())
    with pytest.raises(ProviderError, match="NOT_CONFIGURED"):
        asyncio.run(unavailable.connect())


def test_blackboard_crud_and_isolation(kernel):
    db = kernel.db
    decision = kernel.blackboard.decide(kernel.project.id, "use JSON")
    assert db.get("decisions", decision["id"])["content"] == "use JSON"
    decision["content"] = "use SQLite"
    db.put("decisions", decision)
    assert kernel.blackboard.snapshot(kernel.project.id)["decisions"][0]["content"] == "use SQLite"
    assert db.list("decisions", "other") == []
    db.delete("decisions", decision["id"])
    assert db.get("decisions", decision["id"]) is None
    with pytest.raises(ValueError):
        db.list("tasks; DROP TABLE tasks")


def test_delegation_limit(kernel):
    task = kernel.create_task("root", "a", "PLAN")
    for _ in range(3):
        task = kernel.create_task("child", "b", "PLAN", parent=task)
    with pytest.raises(LimitExceeded, match="depth"):
        kernel.create_task("too deep", "a", "PLAN", parent=task)
    assert kernel.tasks.get(task.id).status == S.ESCALATED


def test_revision_limit(kernel):
    task = kernel.create_task("root", "a", "IMPLEMENT")
    for status in [S.RUNNING, S.REVIEW, S.CHANGES_REQUESTED]:
        kernel.tasks.transition(task.id, status)
    first = kernel.revise(task, "fix")
    second = kernel.revise(task, "fix again")
    assert first.parent_task == second.parent_task == task.id
    assert kernel.tasks.get(task.id).revision_count == 2
    with pytest.raises(LimitExceeded, match="revision"):
        kernel.revise(task, "third")


def test_turn_limit_is_persistent(kernel):
    async def run():
        await kernel.providers["shared"].connect()
        for _ in range(12):
            task = kernel.create_task("step", "a", "PLAN")
            await kernel.execute(task)
        task = kernel.create_task("excess", "b", "PLAN")
        with pytest.raises(LimitExceeded, match="turn"):
            await kernel.execute(task)
        rebuilt = TeamKernel(kernel.db, kernel.project, kernel.team, kernel.workspace)
        assert rebuilt.turns == 12
        assert kernel.tasks.get(task.id).status == S.ESCALATED
    asyncio.run(run())


def test_mock_sessions_are_distinct(kernel):
    async def run():
        provider = kernel.providers["shared"]
        await provider.connect()
        one = await provider.create_session("a", kernel.workspace)
        two = await provider.create_session("b", kernel.workspace)
        assert one != two
        assert (await provider.send_message(one, "hello")).mock
        await provider.close()
        assert await provider.get_status(one) == "CLOSED"
    asyncio.run(run())


def test_timeout_marks_failed_and_reserves_turn(kernel):
    async def slow(*args):
        await asyncio.sleep(10)
    async def run():
        provider = kernel.providers["shared"]
        await provider.connect()
        provider.send_task = slow
        kernel.limits = Limits(turn_timeout=0.01)
        task = kernel.create_task("slow", "a", "IMPLEMENT")
        with pytest.raises(TimeoutError):
            await kernel.execute(task)
        assert kernel.tasks.get(task.id).status == S.FAILED
        assert kernel.turns == 1
    asyncio.run(run())


def test_limits_cannot_be_raised():
    with pytest.raises(ValidationError):
        Limits(max_agent_turns=13)
