"""Synthetic SDK/results only. No actual runtime or credentials."""
import asyncio
import json
from types import SimpleNamespace
import pytest
from ai_team.providers.base import ProviderError
from ai_team.providers.diagnostics import ClassifiedProviderError, error_diagnostic, sanitize
from ai_team.providers.dsh.adapter import DSHAdapter

SECRET = "synthetic-api-key-token-cookie-password"


@pytest.mark.parametrize("error,code", [
    (TimeoutError(SECRET), "TIMEOUT"),
    (ConnectionError(SECRET), "CONNECTION_ERROR"),
    (ProviderError(SECRET), "PROVIDER_ERROR"),
    (ValueError(SECRET), "UNKNOWN_ERROR"),
])
def test_safe_categories(error, code):
    value = error_diagnostic(error)
    assert value["code"] == code
    assert SECRET not in json.dumps(value)


def test_sdk_error_retains_only_numeric_codes_and_safe_chain():
    cls = type("JsonRpcError", (Exception,), {"__module__": "deepseek_harness.errors"})
    error = cls(SECRET)
    error.code, error.status_code = -32603, 429
    error.data = {"Authorization": SECRET, "Cookie": SECRET}
    error.__cause__ = ConnectionError(SECRET)
    diagnostic = error_diagnostic(error)
    assert diagnostic == {"code": "SDK_RPC_ERROR", "source_type": "JsonRpcError",
                          "rpc_code": -32603, "http_status": 429, "cause_types": ["ConnectionError"]}
    error.status_code = SECRET
    assert "http_status" not in error_diagnostic(error)


def test_untrusted_diagnostic_fields_are_dropped():
    value = sanitize({"code": [SECRET], "finish_reason": {"token": SECRET},
                      "source_type": SECRET, "cause_types": [SECRET, {"Cookie": SECRET}],
                      "headers": {"Authorization": SECRET}, "http_status": SECRET})
    assert value == {"code": "UNKNOWN_ERROR", "cause_types": ["OTHER", "OTHER"]}


@pytest.mark.parametrize("finish,text,code", [
    ("max-tokens", "", "MODEL_MAX_TOKENS"),
    ("max-tokens", '{"type":"APPROVE","content":"partial"}', "MODEL_MAX_TOKENS"),
    ("error", "", "MODEL_TURN_FAILED"),
    ("completed", SECRET, "INVALID_MODEL_JSON"),
    ("completed", '{"type":"APPROVE","content":"","mock":false}', "INVALID_MODEL_CONTENT"),
    ("completed", '{"type":"APPROVE","content":"x","mock":true}', "INVALID_MODEL_CONTENT"),
    ("completed", '{"type":"PROPOSE","content":"wrong stage"}', "INVALID_MODEL_DECISION"),
])
def test_review_failure_is_persisted_without_approval_or_retry(kernel, finish, text, code):
    calls = []
    class Runtime:
        def __init__(self, **options): self.options = options
        def start(self): pass
        def close(self): pass
        def start_session(self, sid):
            def run(prompt):
                calls.append(prompt)
                return SimpleNamespace(session_id=sid, finish_reason=finish, final_response=text,
                    events=[{"type": "assistant/message", "data": {"usage": {"outputTokens": 4096}, "secret": SECRET}}])
            return SimpleNamespace(id=sid, run=run, get_working_directory=lambda: str(kernel.workspace))
    async def run():
        provider = DSHAdapter(kernel.workspace, dsh_home=kernel.workspace, runtime_factory=Runtime)
        kernel.providers["shared"] = provider
        await provider.connect()
        task = kernel.create_task("review", "a", "FINAL_REVIEW", "actual evidence")
        with pytest.raises(ClassifiedProviderError) as error:
            await kernel.execute(task)
        assert error_diagnostic(error.value)["code"] == code
        assert kernel.tasks.get(task.id).status == "FAILED"
        events = kernel.db.list("events")
        failure = next(e for e in events if e["type"] == "PROVIDER_FAILURE")
        assert failure["metadata"]["diagnostic"]["code"] == code
        assert SECRET not in json.dumps(events)
        assert not any(m["type"] == "APPROVE" for m in kernel.db.list("messages"))
        assert len(calls) == 1
        await provider.close()
    asyncio.run(run())


@pytest.mark.parametrize("error,code", [(TimeoutError(SECRET), "TIMEOUT"), (ConnectionError(SECRET), "CONNECTION_ERROR")])
def test_sdk_failure_closes_and_does_not_retry(tmp_path, error, code):
    calls, closed = [], []
    def fail():
        calls.append(1)
        raise error
    async def run():
        provider = DSHAdapter(tmp_path, dsh_home=tmp_path)
        provider.runtime = SimpleNamespace(close=lambda: closed.append(1))
        with pytest.raises((ProviderError, TimeoutError)) as raised:
            await provider._call(fail)
        assert error_diagnostic(raised.value)["code"] == code
        assert SECRET not in str(raised.value)
        assert SECRET not in json.dumps(error_diagnostic(raised.value))
        assert calls == [1] and closed == [1] and not provider.connected
    asyncio.run(run())
