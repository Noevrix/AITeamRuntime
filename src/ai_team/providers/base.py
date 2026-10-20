from abc import ABC, abstractmethod
from pathlib import Path
from pydantic import BaseModel
from ai_team.protocol.message import MessageType


class ProviderError(RuntimeError):
    pass


class Capabilities(BaseModel):
    persistent_session: bool = False
    file_access: bool = False
    code_execution: bool = False
    task_cancel: bool = False
    streaming: bool = False
    review: bool = False
    tool_use: bool = False


class Result(BaseModel):
    type: MessageType
    content: str
    mock: bool = False


class AgentProvider(ABC):
    is_mock = False

    @abstractmethod
    def capabilities(self) -> Capabilities: ...
    @abstractmethod
    async def connect(self): ...
    @abstractmethod
    async def health_check(self) -> bool: ...
    @abstractmethod
    async def create_session(self, agent_id: str, workspace: Path) -> str: ...
    @abstractmethod
    async def send_message(self, session_id: str, content: str) -> Result: ...
    @abstractmethod
    async def send_task(self, session_id: str, task) -> Result: ...
    @abstractmethod
    async def get_status(self, session_id: str) -> str: ...
    @abstractmethod
    async def interrupt(self, session_id: str): ...
    @abstractmethod
    async def close(self): ...

    async def resume_session(self, session_id: str, workspace: Path):
        raise ProviderError("persistent sessions unsupported")


class UnconfiguredProvider(AgentProvider):
    def capabilities(self):
        return Capabilities()

    async def connect(self):
        raise ProviderError("NOT_CONFIGURED: official external integration required")

    async def health_check(self):
        return False

    async def create_session(self, agent_id, workspace):
        await self.connect()

    async def send_message(self, session_id, content):
        await self.connect()

    async def send_task(self, session_id, task):
        await self.connect()

    async def get_status(self, session_id):
        return "NOT_CONFIGURED"

    async def interrupt(self, session_id):
        raise ProviderError("cancellation unsupported")

    async def close(self):
        pass
