"""Offline placeholder and Mock checks; no account or vendor runtime required."""
import asyncio
import socket
from types import SimpleNamespace
import pytest
from ai_team.providers.base import ProviderError
from ai_team.providers.workbuddy.adapter import WorkBuddyAdapter
from ai_team.providers.workbuddy.mock_adapter import WorkBuddyMockAdapter


@pytest.fixture
def run_offline(monkeypatch):
    # Windows asyncio creates an internal socketpair before the network guard.
    loop = asyncio.new_event_loop()
    def forbidden(*args, **kwargs):
        raise AssertionError("Offline tests must not connect")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    try:
        yield loop.run_until_complete
    finally:
        loop.close()


def test_placeholder_never_claims_readiness(run_offline):
    async def run():
        provider = WorkBuddyAdapter()
        assert not any(provider.capabilities().model_dump().values())
        assert not await provider.health_check()
        assert await provider.get_status("unbound") == "NOT_CONFIGURED"
        await provider.close()
        await provider.close()
        assert not await provider.health_check()
    run_offline(run())


@pytest.mark.parametrize("operation", ["connect", "create_session", "send_message", "send_task", "interrupt", "resume_session"])
def test_placeholder_operations_fail_without_external_effects(tmp_path, operation, run_offline):
    async def run():
        provider = WorkBuddyAdapter()
        args = {
            "connect": (), "create_session": ("reviewer", tmp_path),
            "send_message": ("unbound", "synthetic request"),
            "send_task": ("unbound", SimpleNamespace(description="synthetic task")),
            "interrupt": ("unbound",), "resume_session": ("unbound", tmp_path),
        }
        with pytest.raises(ProviderError):
            await getattr(provider, operation)(*args[operation])
        assert not await provider.health_check()
        assert await provider.get_status("unbound") == "NOT_CONFIGURED"
        assert list(tmp_path.iterdir()) == []
    run_offline(run())


def test_mock_review_states_remain_explicitly_mock(tmp_path, run_offline):
    async def run():
        provider = WorkBuddyMockAdapter()
        assert provider.is_mock and not await provider.health_check()
        await provider.connect()
        session = await provider.create_session("reviewer", tmp_path)
        assert await provider.get_status(session) == "READY"
        result = await provider.send_task(session, SimpleNamespace())
        assert result.type == "REQUEST_CHANGES" and result.mock
        (tmp_path / "USAGE.md").write_text("Synthetic offline fixture", encoding="utf-8")
        result = await provider.send_task(session, SimpleNamespace())
        assert result.type == "APPROVE" and result.mock
        await provider.close()
        assert await provider.get_status(session) == "CLOSED"
        assert not await provider.health_check()
    run_offline(run())
