from ai_team.providers.mock import MockProvider
from ai_team.providers.base import Capabilities, Result
from ai_team.protocol.message import MessageType as M
from ai_team.orchestration.demo_files import TODO_SOURCE, TODO_TESTS, USAGE


class DemoEngineer(MockProvider):
    """Writes our deterministic fixture, never pretends to be an AI."""
    def capabilities(self):
        return Capabilities(file_access=True)

    async def send_task(self, session_id, task):
        await self.get_status(session_id)
        workspace = self.sessions[session_id]
        (workspace / "todo.py").write_text(TODO_SOURCE, encoding="utf-8")
        (workspace / "test_todo.py").write_text(TODO_TESTS, encoding="utf-8")
        if task.task_type == "REVISE":
            (workspace / "USAGE.md").write_text(USAGE, encoding="utf-8")
        return Result(type=M.COMPLETE, content="Deterministic fixture written; kernel must verify tests.", mock=True)
