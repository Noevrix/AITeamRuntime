import asyncio
from types import SimpleNamespace
import pytest
from ai_team.providers.codex.adapter import CodexAdapter
from ai_team.providers.base import ProviderError
from ai_team.protocol.message import MessageType


class FakeRPC:
    def __init__(self, status="completed", text=None, account=True):
        self.notifications = asyncio.Queue()
        self.process = SimpleNamespace(returncode=None)
        self.calls = []
        self.status = status
        self.text = text or '{"type":"COMPLETE","content":"tested"}'
        self.account = account
        self.closed = False

    async def start(self): pass
    async def close(self): self.closed = True

    async def request(self, method, params):
        self.calls.append((method, params))
        if method == "account/read":
            return {"account": {"type": "chatgpt"} if self.account else None}
        if method in {"thread/start", "thread/resume"}:
            return {"thread": {"id": "thread-1"}}
        if method == "turn/start":
            await self.notifications.put({"method": "item/completed", "params": {"threadId": "thread-1", "turnId": "turn-1", "item": {"type": "agentMessage", "text": self.text}}})
            await self.notifications.put({"method": "turn/completed", "params": {"threadId": "thread-1", "turn": {"id": "turn-1", "status": self.status}}})
            return {"turn": {"id": "turn-1"}}
        return {}


def test_codex_session_resume_turn_and_interrupt(tmp_path):
    async def run():
        adapter = CodexAdapter()
        adapter.rpc = FakeRPC()
        await adapter.connect()
        session = await adapter.create_session("engineer", tmp_path)
        assert await adapter.resume_session(session, tmp_path) == session
        result = await adapter.send_message(session, "work")
        assert result.type == MessageType.COMPLETE and not result.mock
        adapter.active[session] = "turn-2"
        await adapter.interrupt(session)
        assert adapter.rpc.calls[-1] == ("turn/interrupt", {"threadId": session, "turnId": "turn-2"})
        start = next(p for m, p in adapter.rpc.calls if m == "turn/start")
        assert start["sandboxPolicy"]["networkAccess"] is False
        assert start["approvalPolicy"] == "never"
        await adapter.close()
        assert adapter.rpc.closed
    asyncio.run(run())


@pytest.mark.parametrize("status,text", [("failed", None), ("interrupted", None), ("completed", "not JSON"), ("completed", '{"type":"COMPLETE","content":"x","mock":true}')])
def test_codex_rejects_bad_results(tmp_path, status, text):
    async def run():
        adapter = CodexAdapter()
        adapter.rpc = FakeRPC(status, text)
        await adapter.connect()
        session = await adapter.create_session("engineer", tmp_path)
        with pytest.raises(ProviderError):
            await adapter.send_message(session, "work")
        assert not adapter.active
        await adapter.close()
    asyncio.run(run())


def test_codex_no_auth_fails_closed():
    async def run():
        adapter = CodexAdapter()
        adapter.rpc = FakeRPC(account=False)
        with pytest.raises(ProviderError, match="not signed in"):
            await adapter.connect()
        assert adapter.rpc.closed
    asyncio.run(run())
