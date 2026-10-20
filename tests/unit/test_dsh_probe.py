"""Probe orchestration tests with a fake SDK behind the REAL adapter class."""
import asyncio
import json
from types import SimpleNamespace
import pytest
from ai_team.providers.dsh import adapter as adapter_module
from ai_team.providers.dsh.probe import run_probe
from ai_team.memory.database import Database


@pytest.fixture
def sdk(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-probe-secret")
    state = SimpleNamespace(calls=0, closed=False, finish="completed", text='{"type":"PROPOSE","content":"Plan add(a,b), test positive and negative inputs."}')

    class Runtime:
        def __init__(self, **options):
            state.options = options
        def start(self): pass
        def close(self): state.closed = True
        def start_session(self, session_id):
            def run(prompt):
                state.calls += 1
                state.prompt = prompt
                return SimpleNamespace(session_id=session_id, finish_reason=state.finish, final_response=state.text)
            return SimpleNamespace(id=session_id, run=run, get_working_directory=lambda: state.options["cwd"])

    monkeypatch.setattr(adapter_module, "create_runtime", Runtime)
    return state


def test_probe_uses_adapter_once_and_persists_blackboard(tmp_path, sdk):
    root = tmp_path / "probe"
    summary = asyncio.run(run_probe(root))
    assert summary["status"] == "PASS"
    assert summary["adapter"] == "DSHAdapter"
    assert summary["model_result_verified"] and summary["blackboard_verified"]
    assert summary["turns"] == sdk.calls == 1 and sdk.closed
    assert "Analyze the requirement" in sdk.prompt  # Prompt from existing adapter.
    db = Database(root / "blackboard.sqlite")
    try:
        assert len(db.list("tasks")) == 1
        assert len(db.list("decisions")) == 1
        assert db.list("providers")[0]["id"] == "DSH"
        assert not db.list("providers")[0]["mock"]
    finally:
        db.close()
    text = (root / "summary.json").read_text()
    assert "synthetic-probe-secret" not in text
    assert "Plan add" not in text  # Shareable summary excludes model content.


@pytest.mark.parametrize("finish,text,category", [
    ("error", "", "MODEL_TURN_FAILED"),
    ("completed", "not JSON", "INVALID_MODEL_JSON"),
    ("completed", '{"type":"PROPOSE","content":"x","mock":true}', "INVALID_MODEL_CONTENT"),
])
def test_failed_probe_never_retries_or_creates_decision(tmp_path, sdk, finish, text, category):
    sdk.finish, sdk.text = finish, text
    root = tmp_path / "probe"
    summary = asyncio.run(run_probe(root))
    assert summary["status"] == "FAILED"
    assert summary["error_category"] == category
    assert sdk.calls == 1 and sdk.closed
    db = Database(root / "blackboard.sqlite")
    try:
        assert db.list("decisions") == []
        assert db.list("tasks")[0]["status"] == "FAILED"
    finally:
        db.close()


def test_missing_key_never_starts_adapter(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    summary = asyncio.run(run_probe(tmp_path / "probe"))
    assert summary == {"status": "NOT_CONFIGURED", "phase": "preflight", "turns": 0}
    assert not (tmp_path / "probe").exists()


def test_explicit_account_probe_routes_without_key(tmp_path, sdk, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    home = tmp_path / "existing-home"
    home.mkdir()
    summary = asyncio.run(run_probe(tmp_path / "probe", account_home=home))
    assert summary["status"] == "PASS"  # Fake SDK only, not live authorization.
    assert sdk.options["provider"] == "deepseek-account"
    assert sdk.options["model"] == "deepseek-flash"
    assert sdk.options["profile"] == "sdk"
    assert sdk.options["dsh_home"] == str(home.resolve())
    assert sdk.calls == 1
    assert not (tmp_path / "probe" / "dsh-home").exists()


def test_account_probe_missing_home_stops_before_state(tmp_path, sdk):
    summary = asyncio.run(run_probe(tmp_path / "probe", account_home=tmp_path / "absent"))
    assert summary["status"] == "NOT_CONFIGURED"
    assert sdk.calls == 0
    assert not (tmp_path / "probe").exists()
