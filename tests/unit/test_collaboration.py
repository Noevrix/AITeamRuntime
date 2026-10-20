import asyncio
import json
import threading
import time

import pytest

from ai_team.console.collaboration import Collaboration, validate_plan, evidence
from ai_team.console.service import ConsoleError
from ai_team.providers.base import Capabilities, Result, ProviderError
from ai_team.protocol.message import MessageType as M


PLAN = {"steps": [{"id": "build", "agent": "Codex", "instruction": "Implement and test",
                   "depends_on": []}, {"id": "check", "agent": "Codex",
                   "instruction": "Check edge cases", "depends_on": ["build"]}]}


class Fake:
    is_mock = True
    def __init__(self, name, workspace, calls, failure=None):
        self.name, self.workspace, self.calls, self.failure = name, workspace, calls, failure
        self.last_commands = []
    def capabilities(self):
        return Capabilities(task_cancel=True)
    async def connect(self):
        if self.failure == "connect":
            raise ConnectionError("synthetic confidential text")
    async def create_session(self, agent, workspace):
        return agent + "-session"
    async def close(self):
        pass
    async def interrupt(self, session):
        pass
    async def send_message(self, session, content):
        self.calls.append((self.name, content))
        if self.failure == "timeout":
            raise TimeoutError("synthetic confidential text")
        if self.failure == "provider":
            raise ProviderError("synthetic confidential text")
        if self.failure == "wait":
            await asyncio.sleep(60)
        if self.failure == "ask":
            return Result(type=M.ASK, content="Which acceptance criteria?", mock=True)
        if "TYPE=CHALLENGE" in content:
            return Result(type=M.CHALLENGE, content="Add missing edge cases", mock=True)
        if "content must be a JSON-encoded object" in content:
            return Result(type=M.PROPOSE, content=json.dumps(PLAN), mock=True)
        if "TYPE=COMPLETE" in content:
            (self.workspace / "main.py").write_text("print('actual source')", encoding="utf-8")
            (self.workspace / "test-results.txt").write_text("python -m unittest\nOK", encoding="utf-8")
            self.last_commands = [{"command": "python -m unittest", "status": "completed",
                                   "exit_code": 1 if self.failure == "test" else 0, "output": "actual test output"}]
            return Result(type=M.COMPLETE, content="implementation", mock=True)
        if "TYPE=APPROVE" in content:
            if self.failure == "invalid_review":
                return Result(type=M.APPROVE, content="not JSON", mock=True)
            return Result(type=M.REQUEST_CHANGES if self.failure == "changes" else M.APPROVE,
                          content=json.dumps({"summary": "reviewed", "findings": ["fix"] if self.failure == "changes" else []}),
                          mock=True)
        return Result(type=M.PROPOSE, content="DSH original proposal", mock=True)


def setup(tmp_path, failure=None):
    calls = []
    def factory(workspace):
        return {n: Fake(n, workspace, calls, failure) for n in ("DSH", "Codex")}
    service = Collaboration(tmp_path, enabled=True, factory=factory)
    service.create({"goal": "Build a small program", "request_id": "sample"})
    return service, calls


def wait(service):
    limit = time.monotonic() + 5
    while service.jobs and time.monotonic() < limit:
        time.sleep(.01)
    assert not service.jobs
    return service.read("sample")


def discuss(service):
    service.start("sample", "discuss", {"confirm_model_calls": True})
    return wait(service)


def execute(service):
    state = service.read("sample")["conversation"]
    service.start("sample", "execute", {"confirm_model_calls": True,
                                      "confirm_code_execution": True, "plan_id": state["plan_id"]})
    return wait(service)


def test_offline_full_cycle_relay_persistence_evidence(tmp_path):
    service, calls = setup(tmp_path)
    service.comment("sample", {"content": "Include edge cases"})
    data = discuss(service)
    assert data["conversation"]["status"] == "AWAITING_CONFIRMATION"
    assert len(calls) == 3
    assert "DSH original proposal" in calls[1][1]
    assert "Add missing edge cases" in calls[2][1]
    assert all("Include edge cases" in prompt for _, prompt in calls)
    restored = Collaboration(tmp_path)
    assert restored.read("sample")["conversation"]["plan_id"] == data["conversation"]["plan_id"]
    data = execute(service)
    assert data["conversation"]["status"] == "COMPLETED"
    assert len(calls) == 6
    assert "print('actual source')" in calls[-1][1]
    assert "actual test output" in calls[-1][1]
    assert len(data["artifacts"]) == 3
    assert any(e["type"] == "CROSS_REVIEW" for e in data["events"])
    assert all(m["metadata"]["conversation_id"] == "sample" for m in data["messages"])
    assert all(m["metadata"].get("mock") is True for m in data["messages"] if m["from_agent"] in {"DSH", "Codex"})
    assert all(t["status"] == "COMPLETED" for t in data["tasks"])
    with pytest.raises(ConsoleError):
        execute(service)
    assert len(calls) == 6


@pytest.mark.parametrize("failure,code", [("provider", "PROVIDER_ERROR"), ("timeout", "TIMEOUT"), ("connect", "CONNECTION_ERROR")])
def test_failure_stops_no_retry_no_secret(tmp_path, failure, code):
    service, calls = setup(tmp_path, failure)
    data = discuss(service)
    assert data["conversation"]["status"] == "FAILED"
    assert data["conversation"]["error"] == code
    assert len(calls) <= 1
    assert "confidential" not in json.dumps(data)
    assert not data["conversation"]["review_id"]


@pytest.mark.parametrize("failure,status", [("invalid_review", "FAILED"), ("changes", "CHANGES_REQUESTED"), ("test", "FAILED")])
def test_review_and_test_failures_never_approve(tmp_path, failure, status):
    service, calls = setup(tmp_path)
    discuss(service)
    service.factory = lambda w: {n: Fake(n, w, calls, failure) for n in ("DSH", "Codex")}
    data = execute(service)
    assert data["conversation"]["status"] == status
    assert data["conversation"].get("review") != "APPROVE"
    assert len(calls) <= 6
    assert all(t["status"] != "COMPLETED" for t in data["tasks"] if t["task_type"] == "IMPLEMENT")
    if failure == "invalid_review":
        assert not any(m["type"] == "APPROVE" for m in data["messages"])
        assert all(t["status"] == "FAILED" for t in data["tasks"] if t["task_type"] == "FINAL_REVIEW")


def test_consent_idempotency_and_plan_edit(tmp_path):
    service, calls = setup(tmp_path)
    same = service.create({"goal": "Build a small program", "request_id": "sample"})
    assert same["project_id"] == "sample"
    with pytest.raises(ConsoleError, match="MODEL_CONSENT_REQUIRED"):
        service.start("sample", "discuss", {})
    with pytest.raises(ConsoleError, match="AUTH_REQUIRED"):
        service.start("sample", "discuss", {"confirm_model_calls": True, "agent": "WorkBuddy"})
    assert not calls
    data = discuss(service)
    old = data["conversation"]["plan_id"]
    service.edit_plan("sample", {"plan_id": old, "plan": PLAN})
    assert service.read("sample")["conversation"]["plan_id"] != old
    with pytest.raises(ConsoleError, match="PLAN_CONFIRMATION_REQUIRED"):
        service.start("sample", "execute", {"plan_id": old, "confirm_model_calls": True, "confirm_code_execution": True})
    assert len(calls) == 3


def test_disabled_and_reads_do_not_create_runtime(tmp_path):
    service = Collaboration(tmp_path, factory=lambda _: pytest.fail("provider instantiated"))
    assert service.list() == {"items": [], "execution_enabled": False}
    assert not service.root.exists()
    service.create({"goal": "hello", "request_id": "sample"})
    service.read("sample")
    with pytest.raises(ConsoleError, match="MODEL_EXECUTION_DISABLED"):
        service.start("sample", "discuss", {"confirm_model_calls": True})


def test_cancel_and_serial_scheduler(tmp_path):
    service, calls = setup(tmp_path, "wait")
    service.start("sample", "discuss", {"confirm_model_calls": True})
    service.create({"goal": "other", "request_id": "other"})
    with pytest.raises(ConsoleError, match="RUNTIME_BUSY"):
        service.start("other", "discuss", {"confirm_model_calls": True})
    service.cancel("sample")
    data = wait(service)
    assert data["conversation"]["status"] == "CANCELLED"
    assert all(t["status"] == "CANCELLED" for t in data["tasks"])
    assert len(calls) <= 1


def test_crash_record_is_not_replayed(tmp_path):
    service, _ = setup(tmp_path)
    db = service.db()
    state = service.state(db, "sample")
    service.save(db, state, status="EXECUTING")
    db.close()
    restored = Collaboration(tmp_path)
    assert restored.read("sample")["interrupted"]
    restored.cancel("sample")
    assert restored.read("sample")["conversation"]["status"] == "CANCELLED"


def test_clarification_continues_same_conversation_with_round_limit(tmp_path):
    service, calls = setup(tmp_path, "ask")
    data = discuss(service)
    assert data["conversation"]["status"] == "WAITING_FOR_USER"
    assert len(calls) == 1
    service.comment("sample", {"content": "Use the existing CLI requirements"})
    service.factory = lambda w: {n: Fake(n, w, calls) for n in ("DSH", "Codex")}
    data = discuss(service)
    assert data["conversation"]["status"] == "AWAITING_CONFIRMATION"
    assert "Which acceptance criteria?" in calls[1][1]
    assert data["conversation"]["discussion_rounds"] == 2
    service.comment("sample", {"content": "another requirement"})
    with pytest.raises(ConsoleError, match="DISCUSSION_LIMIT"):
        discuss(service)
    assert len(calls) == 4


@pytest.mark.parametrize("plan", [
    {"steps": []},
    {"steps": [{"id": "s", "agent": "WorkBuddy", "instruction": "x", "depends_on": []}]},
    {"steps": [{"id": "s", "agent": "Codex", "instruction": "x", "depends_on": ["later"]}]},
    {"steps": PLAN["steps"] * 3},
])
def test_invalid_dependency_or_assignment(plan):
    with pytest.raises(ConsoleError, match="INVALID_PLAN"):
        validate_plan(json.dumps(plan))


def test_sensitive_goal_and_evidence(tmp_path):
    service = Collaboration(tmp_path)
    with pytest.raises(ConsoleError, match="SENSITIVE_INPUT_BLOCKED"):
        service.create({"goal": "password=synthetic-sensitive", "request_id": "sample"})
    w = tmp_path / "workspace"
    w.mkdir()
    (w / "main.py").write_text('password="synthetic-sensitive"')
    (w / "test-results.txt").write_text("OK")
    with pytest.raises(ConsoleError, match="SENSITIVE_EVIDENCE_BLOCKED"):
        evidence(w)


def test_codex_readonly_policy_and_transport_test_evidence(tmp_path):
    from ai_team.providers.codex.adapter import CodexAdapter
    class RPC:
        process = type("Process", (), {"returncode": None})()
        def __init__(self):
            self.requests = []
            self.notifications = asyncio.Queue()
        async def request(self, method, args):
            self.requests.append((method, args))
            if method == "thread/start":
                return {"thread": {"id": "thread"}}
            return {"turn": {"id": "turn"}}
    async def check():
        adapter = CodexAdapter(read_only=True)
        adapter.rpc = RPC()
        adapter.connected = True
        session = await adapter.create_session("Codex", tmp_path)
        for item in [{"type": "commandExecution", "command": "python -m unittest",
                      "status": "completed", "exitCode": 0, "aggregatedOutput": "OK"},
                     {"type": "agentMessage", "text": '{"type":"CHALLENGE","content":"valid"}'}]:
            await adapter.rpc.notifications.put({"method": "item/completed",
                "params": {"threadId": "thread", "turnId": "turn", "item": item}})
        await adapter.rpc.notifications.put({"method": "turn/completed",
            "params": {"threadId": "thread", "turn": {"id": "turn", "status": "completed"}}})
        await adapter.send_message(session, "review")
        assert adapter.rpc.requests[0][1]["sandbox"] == "read-only"
        assert adapter.rpc.requests[1][1]["sandboxPolicy"] == {"type": "readOnly"}
        assert adapter.last_commands[0]["output"] == "OK"
        assert adapter.last_commands[0]["exit_code"] == 0
    asyncio.run(check())
