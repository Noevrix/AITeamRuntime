"""Offline review execution with fake SDK; no live provider is started."""
import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from ai_team.memory.database import Database
from ai_team.providers.dsh import adapter as adapter_module
from ai_team.providers.dsh.adapter import DSHAdapter
from ai_team.providers.dsh.review_probe import FILES, load_evidence, run_review
from ai_team.providers.base import ProviderError


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "history"
    workspace = root / "workspace"
    workspace.mkdir(parents=True)
    db = Database(root / "blackboard.sqlite")
    db.put("projects", {"id": "p", "goal": "add list delete"})
    db.put("tasks", {"id": "plan", "task_type": "PLAN", "status": "COMPLETED"})
    plan = "2. CLI contract\nadd list delete\n11. Acceptance checklist\ntests pass"
    db.put("messages", {"id": "m", "task_id": "plan", "type": "PROPOSE", "content": plan, "metadata": {"mock": False}})
    db.put("decisions", {"id": "d", "content": plan})
    db.put("events", {"id": "e", "type": "TEST_RESULT", "metadata": {"passed": True, "exit_code": 0, "log": "tests-1.txt"}})
    for name in FILES:
        data = b"Ran 14 tests in 1.0s\nOK\n" if name == "tests-1.txt" else b"# synthetic artifact\n"
        (workspace / name).write_bytes(data)
        db.put("artifacts", {"id": name, "path": name, "task_id": "impl", "sha256": hashlib.sha256(data).hexdigest()})
    db.close()
    return root


@pytest.fixture
def sdk(monkeypatch):
    state = SimpleNamespace(calls=0, starts=0, finish="completed", error=None,
                            text='{"type":"APPROVE","content":"Meets requirements","findings":[]}')
    class Runtime:
        def __init__(self, **options): state.options = options
        def start(self): state.starts += 1
        def close(self): pass
        def start_session(self, sid):
            def run(prompt):
                state.calls += 1
                state.prompt = prompt
                if state.error: raise state.error
                return SimpleNamespace(session_id=sid, finish_reason=state.finish, final_response=state.text)
            return SimpleNamespace(id=sid, run=run, get_working_directory=lambda: state.options["cwd"])
    monkeypatch.setattr(adapter_module, "create_runtime", Runtime)
    return state


@pytest.mark.parametrize("finish,text,error,status", [
    ("completed", '{"type":"APPROVE","content":"OK","findings":[]}', None, "APPROVE"),
    ("completed", '{"type":"REQUEST_CHANGES","content":"Fix","findings":["Missing validation"]}', None, "REQUEST_CHANGES"),
    ("max-tokens", "", None, "MAX_TOKENS"),
    ("completed", "", None, "INVALID_RESPONSE"),
    ("completed", "not JSON", None, "INVALID_RESPONSE"),
    ("completed", '{"type":"APPROVE","content":"OK","findings":[],"mock":true}', None, "INVALID_RESPONSE"),
    ("completed", '{"type":"APPROVE","content":"OK","findings":["a","b","c","d"]}', None, "INVALID_RESPONSE"),
    ("completed", "", ProviderError("synthetic-token-cookie-key"), "PROVIDER_ERROR"),
    ("completed", "", TimeoutError("synthetic-token-cookie-key"), "PROVIDER_ERROR"),
    ("completed", "", ConnectionError("synthetic-token-cookie-key"), "PROVIDER_ERROR"),
])
def test_single_review(source, tmp_path, sdk, finish, text, error, status):
    sdk.finish, sdk.text, sdk.error = finish, text, error
    output = tmp_path / "review"
    result = asyncio.run(run_review(source, output, dsh_home=tmp_path, dsh_bin="fake"))
    assert result["status"] == status
    assert sdk.calls == result["application_attempts"] == 1
    assert sdk.options["max_tokens"] == 4096 and sdk.options["reasoning_effort"] == "off"
    assert sdk.options["provider"] == "deepseek-account" and sdk.options["profile"] == "sdk"
    assert "synthetic-token-cookie-key" not in json.dumps(result)
    db = Database(output / "blackboard.sqlite")
    try:
        messages = db.list("messages")
        assert "synthetic-token-cookie-key" not in json.dumps(db.list("events"))
        assert any(m["type"] == "APPROVE" for m in messages) == (status == "APPROVE")
        if status in {"APPROVE", "REQUEST_CHANGES"}:
            assert result["blackboard_verified"]
            assert result["diagnostic"]["finish_reason"] == "completed"
            assert db.get("decisions", result["decision_id"])
    finally:
        db.close()
    with pytest.raises(FileExistsError):
        asyncio.run(run_review(source, output, dsh_home=tmp_path, dsh_bin="fake"))
    assert sdk.calls == 1


def test_changed_artifact_stops_before_sdk(source, tmp_path, sdk):
    (source / "workspace/todo.py").write_text("changed")
    with pytest.raises(StopIteration):
        load_evidence(source)
    assert sdk.calls == sdk.starts == 0


def test_configurable_budget_preserves_source(source, tmp_path, sdk):
    before = (source / "blackboard.sqlite").read_bytes()
    result = asyncio.run(run_review(source, tmp_path / "review", dsh_home=tmp_path,
                                   dsh_bin="fake", max_tokens=8192, reasoning_effort="low"))
    assert result["status"] == "APPROVE"
    assert sdk.options["max_tokens"] == 8192 and sdk.options["reasoning_effort"] == "low"
    assert before == (source / "blackboard.sqlite").read_bytes()


@pytest.mark.parametrize("budget", [0, True, 8193])
def test_invalid_budget_rejected(tmp_path, budget):
    with pytest.raises(ValueError):
        DSHAdapter(tmp_path, max_tokens=budget)


def test_actual_sdk_parameter_contract(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "runs/dsh-sdk"))
    api = pytest.importorskip("deepseek_harness.api")
    client = pytest.importorskip("deepseek_harness.client")
    config = api.DeepSeekHarnessConfig(max_tokens=8192, reasoning_effort="off")
    transport = client.HarnessClient(client.HarnessConfig())
    captured = {}
    def request(method, payload, **kwargs):
        captured.update(payload)
        return {}
    monkeypatch.setattr(transport, "request", request)
    transport.initialize(cwd=".", provider="deepseek-account", model="deepseek-flash",
                         max_tokens=config.max_tokens, reasoning_effort=config.reasoning_effort)
    assert captured["maxTokens"] == 8192 and captured["reasoningEffort"] == "off"
