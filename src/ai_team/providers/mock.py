from ai_team.protocol.task import uid
from ai_team.protocol.message import MessageType as M
from .base import AgentProvider, Capabilities, ProviderError, Result


class MockProvider(AgentProvider):
    is_mock = True

    def __init__(self):
        self.connected = False
        self.sessions = {}

    def capabilities(self):
        return Capabilities(review=True)

    async def connect(self):
        self.connected = True

    async def health_check(self):
        return self.connected

    async def create_session(self, agent_id, workspace):
        if not self.connected:
            raise ProviderError("mock not connected")
        session = uid()
        self.sessions[session] = workspace
        return session

    async def send_message(self, session_id, content):
        await self.get_status(session_id)
        return Result(type=M.COMPLETE, content=content, mock=True)

    async def send_task(self, session_id, task):
        return await self.send_message(session_id, task.description)

    async def get_status(self, session_id):
        if session_id not in self.sessions:
            raise KeyError(session_id)
        return "READY" if self.connected else "CLOSED"

    async def interrupt(self, session_id):
        await self.get_status(session_id)

    async def close(self):
        self.connected = False
