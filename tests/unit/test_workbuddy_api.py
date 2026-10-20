"""Synthetic official-protocol fixtures only; no installed client or real credentials."""
import asyncio
import json
import socket
import time
from urllib.parse import parse_qs, urlsplit
import pytest
from ai_team.providers.workbuddy.client import WorkBuddyClient, WorkBuddyError, SCOPES
from ai_team.providers.workbuddy.auth import OAuth, Token, TokenProvider
from ai_team.providers.workbuddy.adapter import WorkBuddyAdapter
from ai_team.providers.workbuddy.config import configuration_status
from ai_team.providers.workbuddy.probe import run_probe
from ai_team.memory.database import Database


@pytest.fixture
def run(monkeypatch):
    loop = asyncio.new_event_loop()
    def forbidden(*args, **kwargs):
        raise AssertionError("Network forbidden")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    try:
        yield loop.run_until_complete
    finally:
        loop.close()


def envelope(data):
    return 200, json.dumps({"code": 0, "data": data}).encode()


class Transport:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    async def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        value = self.responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        if callable(value):
            return value(self.calls)
        return value


def token_reply(**changes):
    return {"access_token": "synthetic-access", "refresh_token": "synthetic-refresh",
            "expires_in": 3600, "token_type": "Bearer", "scope": " ".join(SCOPES), **changes}


def client(transport):
    return WorkBuddyClient(TokenProvider(Token("synthetic-access", time.time() + 3600, SCOPES)),
                           transport)


def test_missing_configuration_does_not_read_store():
    class Store:
        def exists(self, name):
            return False
        def load(self, name):
            pytest.fail("presence check must never decrypt")
    result = configuration_status({}, Store())
    assert result["status"] == "NOT_CONFIGURED"
    env = {"AI_TEAM_WORKBUDDY_CLIENT_ID": "synthetic-app",
           "AI_TEAM_WORKBUDDY_REDIRECT_URI": "https://example.invalid/callback",
           "AI_TEAM_WORKBUDDY_DEPLOYMENT_APPROVED": "1"}
    assert configuration_status(env, Store())["status"] == "AUTH_REQUIRED"


def test_oauth_state_exchange_and_secret_not_represented(run):
    transport = Transport([(200, json.dumps(token_reply()).encode())])
    oauth = OAuth("test-app", "https://example.invalid/callback", "synthetic-secret",
                  approved_server=True, transport=transport, clock=lambda: 100)
    url, pending = oauth.begin()
    assert "synthetic-secret" not in url
    assert set(parse_qs(urlsplit(url).query)["scope"][0].split()) == SCOPES
    callback = oauth.redirect_uri + "?code=test-code&state=" + pending["state"]
    result = run(oauth.exchange(callback, pending))
    assert result.access == "synthetic-access" and result.expires_at == 3700
    assert "synthetic-access" not in repr(result)
    call = transport.calls[0]
    assert call[:2] == ("POST", "/token") and call[2]["form"]
    assert call[2]["data"]["redirect_uri"] == oauth.redirect_uri


@pytest.mark.parametrize("case", ["state", "origin", "expired", "duplicate", "denied"])
def test_oauth_callback_rejected_without_request(run, case):
    transport = Transport([])
    oauth = OAuth("test", "https://example.invalid/cb", "synthetic",
                  approved_server=True, transport=transport, clock=lambda: 700)
    _, pending = oauth.begin()
    callback = oauth.redirect_uri + "?code=c&state=" + pending["state"]
    if case == "state":
        callback += "wrong"
    elif case == "origin":
        callback = callback.replace("example.invalid", "other.invalid")
    elif case == "expired":
        pending["created_at"] = 0
    elif case == "duplicate":
        callback += "&code=other"
    else:
        callback += "&error=access_denied"
    with pytest.raises(WorkBuddyError):
        run(oauth.exchange(callback, pending))
    assert not transport.calls


def test_unapproved_deployment_blocked():
    with pytest.raises(WorkBuddyError, match="DEPLOYMENT_UNCONFIRMED"):
        OAuth("id", "https://example.invalid/cb", "synthetic").begin()


def test_expiry_refresh_once_and_save_rotation(run):
    transport = Transport([(200, json.dumps(token_reply(refresh_token="rotated")).encode())])
    oauth = OAuth("id", "https://example.invalid/cb", "synthetic",
                  approved_server=True, transport=transport, clock=lambda: 100)
    saved = []
    provider = TokenProvider(Token("old", 99, SCOPES, "old-refresh"), oauth, saved.append,
                             clock=lambda: 100)
    assert run(provider.access_token()) == "synthetic-access"
    assert run(provider.access_token()) == "synthetic-access"
    assert saved[0].refresh == "rotated" and len(transport.calls) == 1


def test_failed_refresh_latches_and_no_secret_leak(run):
    transport = Transport([(401, b"secret-body")])
    oauth = OAuth("id", "https://example.invalid/cb", "synthetic-secret",
                  approved_server=True, transport=transport)
    provider = TokenProvider(Token("old", 0, SCOPES, "refresh"), oauth)
    with pytest.raises(WorkBuddyError, match="AUTH_FAILED") as error:
        run(provider.access_token())
    assert "secret" not in str(error.value) and "secret" not in repr(error.value)
    with pytest.raises(WorkBuddyError, match="AUTH_REQUIRED"):
        run(provider.access_token())
    assert len(transport.calls) == 1


@pytest.mark.parametrize("value", [None, Token("old", 0, SCOPES)])
def test_missing_or_expired_token_requires_auth(run, value):
    with pytest.raises(WorkBuddyError, match="AUTH_REQUIRED"):
        run(TokenProvider(value).access_token())


@pytest.mark.parametrize("response,code", [
    ((401, b"private"), "AUTH_FAILED"), ((403, b"private"), "FORBIDDEN"),
    ((429, b"private"), "RATE_LIMITED"), ((503, b"private"), "SERVER_ERROR"),
    ((302, b"private"), "HTTP_ERROR"), ((200, b"not-json-secret"), "INVALID_RESPONSE"),
    (TimeoutError("secret"), "TIMEOUT"), (ConnectionError("secret"), "CONNECTION_ERROR"),
    ((200, b'{"code":0,"data":{"online":"true"}}'), "INVALID_RESPONSE"),
])
def test_errors_are_classified_not_retried(run, response, code):
    transport = Transport([response])
    with pytest.raises(WorkBuddyError, match=code) as error:
        run(client(transport).online())
    assert len(transport.calls) == 1
    assert "private" not in str(error.value) and "secret" not in str(error.value)
    assert error.value.summary()["status"] == code


def test_revoked_auth_does_not_retry_http(run):
    transport = Transport([(401, b"")])
    api = client(transport)
    for expected in ("AUTH_FAILED", "AUTH_REQUIRED"):
        with pytest.raises(WorkBuddyError, match=expected):
            run(api.online())
    assert len(transport.calls) == 1


def echo_response(calls):
    post = next(call for call in calls if call[0] == "POST")
    content = post[2]["data"]["content"]
    expected = content.split("请只回复 ", 1)[1].split("，", 1)[0]
    message = {"message_id": "reply", "role": "assistant",
               "msg_type": "text", "content": [expected]}
    return envelope({"messages": [message, message]})


def test_echo_is_not_final_and_unrelated_increment_is_discarded(run, tmp_path):
    transport = Transport([
        envelope({"online": True}), envelope({"message_id": "sent"}),
        envelope({"messages": [{"message_id": "unrelated", "role": "assistant",
                               "content": ["private unrelated APPROVE"], "msg_type": "text"}]}),
        echo_response,
    ])
    adapter = WorkBuddyAdapter(client(transport), poll_interval=0)
    result = run(run_probe(tmp_path / "probe", adapter))
    assert result["status"] == "COMPLETION_UNCONFIRMED"
    assert result["observed_echo"] and not result["completion_verified"]
    assert not result["official_correlation_verified"]
    assert result["blackboard_verified"] and result["task_status"] == "ESCALATED"
    assert result["application_attempts"] == 1 and not result["mock"]
    db = Database(tmp_path / "probe" / "blackboard.sqlite")
    messages = db.list("messages")
    assert sum(m["type"] == "REVIEW" for m in messages) == 1
    assert not any(m["type"] in {"APPROVE", "COMPLETE"} for m in messages)
    assert "private unrelated" not in json.dumps(messages + db.list("decisions") + db.list("events"))
    db.close()
    assert sum(c[0] == "POST" for c in transport.calls) == 1
    assert not any(adapter.capabilities().model_dump().values())


def test_empty_poll_timeout_persists_failure_no_resubmit(run, tmp_path):
    transport = Transport([envelope({"online": True}), envelope({"message_id": "sent"}),
                           envelope({"messages": []}), envelope({"messages": []})])
    adapter = WorkBuddyAdapter(client(transport), poll_interval=0, max_polls=2)
    result = run(run_probe(tmp_path / "timeout", adapter))
    assert result["status"] == "TIMEOUT" and result["task_status"] == "FAILED"
    assert result["blackboard_verified"] and result["application_attempts"] == 1
    assert sum(c[0] == "POST" for c in transport.calls) == 1


def test_ambiguous_submit_failure_never_resends(run, tmp_path):
    transport = Transport([envelope({"online": True}), TimeoutError("sensitive")])
    adapter = WorkBuddyAdapter(client(transport), poll_interval=0)
    result = run(run_probe(tmp_path / "ambiguous", adapter))
    assert result["status"] == "TIMEOUT" and result["application_attempts"] == 1
    assert len(transport.calls) == 2 and result["blackboard_verified"]


def test_formal_send_task_fails_before_network_and_kernel_never_approves(run, kernel):
    transport = Transport([envelope({"online": True})])
    adapter = WorkBuddyAdapter(client(transport))
    kernel.providers["shared"] = adapter
    task = kernel.create_task("real review blocked", "a", "REVIEW", "actual input")
    with pytest.raises(WorkBuddyError, match="COMPLETION_UNSUPPORTED"):
        run(kernel.execute(task))
    assert kernel.tasks.get(task.id).status == "FAILED"
    assert not any(m["type"] == "APPROVE" for m in kernel.db.list("messages"))
    assert all(c[0] == "GET" for c in transport.calls)
    assert not kernel.db.list("decisions")


def test_cancel_wait_does_not_claim_remote_cancel(run, tmp_path):
    async def scenario():
        transport = Transport([envelope({"online": True}), envelope({"message_id": "sent"}),
                               envelope({"messages": []})])
        adapter = WorkBuddyAdapter(client(transport), poll_interval=20)
        await adapter.connect()
        handle = await adapter.create_session("reviewer", tmp_path)
        work = asyncio.create_task(adapter.observe_once(handle))
        for _ in range(10):
            if adapter.handles[handle] == "WAITING":
                break
            await asyncio.sleep(0)
        await adapter.cancel_wait(handle)
        with pytest.raises(asyncio.CancelledError):
            await work
        assert await adapter.get_status(handle) == "CANCELLED"
        with pytest.raises(WorkBuddyError, match="BUSY"):
            await adapter.observe_once(handle)
        with pytest.raises(WorkBuddyError, match="CANCEL_UNSUPPORTED"):
            await adapter.interrupt(handle)
        assert sum(c[0] == "POST" for c in transport.calls) == 1
    run(scenario())


def test_real_workflow_gate_precedes_other_providers(run, tmp_path):
    from ai_team.cli import run_demo
    with pytest.raises(WorkBuddyError, match="COMPLETION_UNSUPPORTED"):
        run(run_demo(tmp_path / "must-not-exist", mode="real", dsh_mode="real", workbuddy_mode="real"))
    assert not (tmp_path / "must-not-exist").exists()


def test_secure_store_uses_ciphertext_and_detects_corruption(tmp_path, monkeypatch):
    import ai_team.providers.workbuddy.store as module
    # Mock crypto for deterministic offline tests; DPAPI itself is not claimed tested here.
    def crypto(data, decrypt=False):
        if decrypt:
            if not data.startswith(b"encrypted:"):
                raise WorkBuddyError("STORAGE_ERROR")
            return bytes(value ^ 0x55 for value in data[10:])
        return b"encrypted:" + bytes(value ^ 0x55 for value in data)
    monkeypatch.setattr(module, "dpapi", crypto)
    store = module.SecureStore(tmp_path)
    store.save("token", {"access": "synthetic-secret"})
    assert b"synthetic-secret" not in (tmp_path / "token.dpapi").read_bytes()
    assert store.load("token") == {"access": "synthetic-secret"}
    (tmp_path / "token.dpapi").write_bytes(b"bad")
    with pytest.raises(WorkBuddyError):
        store.load("token")


def test_increment_final_looking_and_invalid_review_never_complete(run, tmp_path):
    transport = Transport([
        envelope({"online": True}), envelope({"message_id": "sent"}),
        envelope({"messages": [
            {"message_id": "part", "role": "assistant", "content": ["partial"], "msg_type": "text"},
            {"message_id": "final", "role": "assistant", "content": ['{"type":"APPROVE"}'],
             "msg_type": "text", "metadata": {"status": "completed"}},
        ]}),
    ])
    adapter = WorkBuddyAdapter(client(transport), poll_interval=0, max_polls=1)
    result = run(run_probe(tmp_path / "untrusted-final", adapter))
    assert result["status"] == "TIMEOUT" and not result["completion_verified"]
    assert result["task_status"] == "FAILED"
    # metadata.status is undocumented for Local Assistant: must not accept it.
    db = Database(tmp_path / "untrusted-final" / "blackboard.sqlite")
    assert not any(m["from_agent"] == "reviewer" for m in db.list("messages"))
    db.close()


def test_invalid_message_envelope_and_missing_scope(run):
    transport = Transport([envelope({"messages": [{"content": "not an array"}]})])
    with pytest.raises(WorkBuddyError, match="INVALID_RESPONSE"):
        run(client(transport).messages_after("sent"))
    with pytest.raises(WorkBuddyError, match="FORBIDDEN"):
        Token.parse(token_reply(scope="user.profile.readable"))


def test_total_timeout_is_bounded_and_no_second_post(run, tmp_path):
    async def scenario():
        transport = Transport([envelope({"online": True}), envelope({"message_id": "sent"}),
                               envelope({"messages": []})])
        adapter = WorkBuddyAdapter(client(transport), timeout=0.01, poll_interval=10)
        await adapter.connect()
        handle = await adapter.create_session("reviewer", tmp_path)
        with pytest.raises(WorkBuddyError, match="TIMEOUT"):
            await adapter.observe_once(handle)
        assert await adapter.get_status(handle) == "TIMEOUT"
        with pytest.raises(WorkBuddyError, match="BUSY"):
            await adapter.observe_once(handle)
        assert sum(c[0] == "POST" for c in transport.calls) == 1
    run(scenario())


def test_offline_assistant_fails_without_send(run, tmp_path):
    transport = Transport([envelope({"online": False})])
    result = run(run_probe(tmp_path / "offline", WorkBuddyAdapter(client(transport))))
    assert result["status"] == "OFFLINE" and result["application_attempts"] == 0
    assert result["blackboard_verified"] and len(transport.calls) == 1


def test_dpapi_synthetic_memory_roundtrip():
    import os
    from ai_team.providers.workbuddy.store import dpapi
    if os.name != "nt":
        pytest.skip("Windows-only protection")
    plaintext = b"synthetic-test-only-no-real-credentials"
    protected = dpapi(plaintext)
    assert plaintext not in protected
    assert dpapi(protected, decrypt=True) == plaintext


@pytest.mark.parametrize("suffix", ["&state=", "&code=", "&error=", "&state=%E4%B8%AD"])
def test_callback_ambiguity_rejected_without_token_exchange(run, suffix):
    transport = Transport([])
    oauth = OAuth("test", "https://example.invalid/cb", "synthetic",
                  approved_server=True, transport=transport)
    _, pending = oauth.begin()
    callback = oauth.redirect_uri + "?code=c&state=" + pending["state"] + suffix
    with pytest.raises(WorkBuddyError):
        run(oauth.exchange(callback, pending))
    assert transport.calls == []


def test_unicode_state_is_safe_classified_error(run):
    transport = Transport([])
    oauth = OAuth("test", "https://example.invalid/cb", "synthetic",
                  approved_server=True, transport=transport)
    _, pending = oauth.begin()
    with pytest.raises(WorkBuddyError, match="STATE_MISMATCH"):
        run(oauth.exchange(oauth.redirect_uri + "?code=c&state=%E4%B8%AD", pending))
    assert not transport.calls


def test_wrong_handle_cannot_cancel_active_wait(run, tmp_path):
    async def scenario():
        transport = Transport([envelope({"online": True}), envelope({"message_id": "sent"}),
                               envelope({"messages": []})])
        adapter = WorkBuddyAdapter(client(transport), poll_interval=20)
        await adapter.connect()
        first = await adapter.create_session("first", tmp_path)
        second = await adapter.create_session("second", tmp_path)
        work = asyncio.create_task(adapter.observe_once(first))
        for _ in range(10):
            if adapter.handles[first] == "WAITING":
                break
            await asyncio.sleep(0)
        with pytest.raises(WorkBuddyError, match="INVALID_CONFIG"):
            await adapter.cancel_wait(second)
        assert not work.done() and not work.cancelling()
        await adapter.cancel_wait(first)
        with pytest.raises(asyncio.CancelledError):
            await work
        assert adapter.active_handle is None
        assert adapter.handles[second] == "READY"
    run(scenario())


def test_hidden_input_refuses_visible_fallback(monkeypatch):
    import importlib.util
    import warnings
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "audit_workbuddy_auth", Path(__file__).resolve().parents[2] / "scripts/workbuddy_auth.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fallback = []
    def unavailable(prompt):
        warnings.warn("cannot hide input", module.getpass.GetPassWarning)
        fallback.append(True)
        return "synthetic-secret"
    monkeypatch.setattr(module.getpass, "getpass", unavailable)
    with pytest.raises(WorkBuddyError, match="AUTH_REQUIRED") as error:
        module.hidden_input("hidden")
    assert not fallback and "synthetic-secret" not in str(error.value)
