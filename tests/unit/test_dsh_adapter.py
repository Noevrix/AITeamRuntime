"""Fake SDK contract tests; none of these calls a model or proves live access."""
import asyncio
import json
import threading
from types import SimpleNamespace
import pytest
from ai_team.providers.dsh.adapter import DSHAdapter
from ai_team.providers.base import ProviderError
from ai_team.protocol.task import Task
from ai_team.protocol.message import MessageType as M


class FakeSession:
    def __init__(self, runtime, session_id):
        self.runtime, self.id = runtime, session_id

    def get_working_directory(self):
        if self.runtime.closed:
            raise RuntimeError("closed")
        return self.runtime.options["cwd"]

    def run(self, content):
        self.runtime.prompts.append(content)
        if self.runtime.block:
            self.runtime.stopped.wait(2)
        return SimpleNamespace(session_id=self.id, finish_reason=self.runtime.finish,
                               final_response=self.runtime.text)


class FakeRuntime:
    def __init__(self, **options):
        self.options = options
        self.closed = False
        self.block = False
        self.stopped = threading.Event()
        self.prompts = []
        self.finish = "completed"
        self.text = '{"type":"PROPOSE","content":"Plan from fake SDK"}'

    def start(self):
        pass

    def close(self):
        self.closed = True
        self.stopped.set()

    def start_session(self, session_id):
        return FakeSession(self, session_id)

    def resume_session(self, session_id):
        return self.start_session(session_id)


def adapter(tmp_path, **kwargs):
    return DSHAdapter(tmp_path, dsh_home=tmp_path / "home", runtime_factory=FakeRuntime, **kwargs)


def test_explicit_home_required(tmp_path, monkeypatch):
    monkeypatch.delenv("DSH_HOME", raising=False)
    with pytest.raises(ProviderError, match="NOT_CONFIGURED"):
        asyncio.run(DSHAdapter(tmp_path).connect())


def test_connection_sessions_resume_capabilities(tmp_path):
    async def run():
        p = adapter(tmp_path)
        assert not await p.health_check()
        await p.connect()
        assert await p.health_check()
        first = await p.create_session("a", tmp_path)
        second = await p.create_session("b", tmp_path)
        assert first != second
        assert await p.resume_session(first, tmp_path) == first
        assert await p.get_status(first) == "READY"
        assert p.capabilities().persistent_session
        assert not p.capabilities().task_cancel
        with pytest.raises(ProviderError, match="unsupported"):
            await p.interrupt(first)
        with pytest.raises(ValueError, match="workspace"):
            await p.create_session("c", tmp_path / "other")
        runtime = p.runtime
        assert runtime.options["request_timeout_seconds"] == 120
        assert runtime.options["max_tokens"] == 4096
        await p.close()
        assert runtime.closed
        assert await p.get_status(first) == "UNAVAILABLE"
    asyncio.run(run())


@pytest.mark.parametrize("finish,text", [
    ("error", ""), ("max-tokens", '{"type":"PROPOSE","content":"partial"}'),
    (None, ""), ("completed", "plain text"),
    ("completed", '{"type":"PROPOSE","content":"x","mock":true}'),
    ("completed", '{"type":"PROPOSE","content":"  "}'),
])
def test_failed_or_malformed_result_is_never_success(tmp_path, finish, text):
    async def run():
        p = adapter(tmp_path)
        await p.connect()
        p.runtime.finish, p.runtime.text = finish, text
        session = await p.create_session("a", tmp_path)
        with pytest.raises(ProviderError):
            await p.send_message(session, "plan")
        assert not p.active
        await p.close()
    asyncio.run(run())


def test_planning_and_final_decisions(tmp_path):
    async def run():
        p = adapter(tmp_path)
        await p.connect()
        session = await p.create_session("architect", tmp_path)
        task = Task(project_id="p", title="plan", description="TODO requirement", created_by="user", task_type="PLAN")
        result = await p.send_task(session, task)
        assert result.type == M.PROPOSE and not result.mock
        assert "TODO requirement" in p.runtime.prompts[-1]
        task.task_type = "FINAL_REVIEW"
        for decision in [M.APPROVE, M.REJECT, M.REQUEST_CHANGES]:
            p.runtime.text = json.dumps({"type": decision, "content": "evidence reviewed"})
            assert (await p.send_task(session, task)).type == decision
        task.task_type = "PLAN"
        with pytest.raises(ProviderError, match="invalid decision"):
            await p.send_task(session, task)
        task.task_type = "IMPLEMENT"
        with pytest.raises(ProviderError, match="only"):
            await p.send_task(session, task)
        await p.close()
    asyncio.run(run())


def test_timeout_stops_sdk_worker(tmp_path):
    async def run():
        p = adapter(tmp_path, timeout=0.05)
        await p.connect()
        runtime = p.runtime
        runtime.block = True
        session = await p.create_session("a", tmp_path)
        with pytest.raises(TimeoutError):
            await p.send_message(session, "plan")
        assert runtime.closed and runtime.stopped.is_set()
        assert not p.connected and not p.active
    asyncio.run(run())


def test_cancellation_stops_sdk_worker(tmp_path):
    async def run():
        p = adapter(tmp_path)
        await p.connect()
        runtime = p.runtime
        runtime.block = True
        session = await p.create_session("a", tmp_path)
        pending = asyncio.create_task(p.send_message(session, "plan"))
        while not p.active:
            await asyncio.sleep(0)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert runtime.closed and not p.connected
    asyncio.run(run())


def test_connection_failure_sanitized_and_closed(tmp_path):
    class Broken(FakeRuntime):
        def start(self):
            raise RuntimeError("sensitive vendor diagnostics")

    async def run():
        p = DSHAdapter(tmp_path, dsh_home=tmp_path / "home", runtime_factory=Broken)
        with pytest.raises(ProviderError) as error:
            await p.connect()
        assert "sensitive" not in str(error.value)
        assert not p.connected and p.runtime is None
    asyncio.run(run())


def test_plan_persisted_and_passed_as_task_data(kernel):
    async def run():
        p = adapter(kernel.workspace)
        await p.connect()
        kernel.providers["shared"] = p
        task = kernel.create_task("plan", "a", "PLAN", "TODO")
        result = await kernel.execute(task)
        kernel.blackboard.decide(kernel.project.id, result.content)
        downstream = kernel.create_task("implement", "b", "IMPLEMENT", result.content)
        assert kernel.tasks.get(downstream.id).description == result.content
        assert any(m["type"] == "PROPOSE" and m["content"] == result.content
                   for m in kernel.db.list("messages"))
        assert kernel.blackboard.snapshot(kernel.project.id)["decisions"][0]["content"] == result.content
        await p.close()
    asyncio.run(run())
