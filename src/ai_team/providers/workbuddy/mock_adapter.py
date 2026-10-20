from ai_team.providers.mock import MockProvider
from ai_team.providers.base import Result
from ai_team.protocol.message import MessageType as M


class WorkBuddyMockAdapter(MockProvider):
    async def send_task(self, session_id, task):
        await self.get_status(session_id)
        workspace = self.sessions[session_id]
        if not (workspace / "USAGE.md").is_file():
            return Result(type=M.REQUEST_CHANGES, content="Add USAGE.md documenting add/list/delete examples and empty-text / missing-ID behavior. Rerun tests.", mock=True)
        return Result(type=M.APPROVE, content="Mock check: usage guide exists. Executable tests are checked separately by the workflow.", mock=True)
