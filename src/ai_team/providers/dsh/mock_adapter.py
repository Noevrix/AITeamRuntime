from ai_team.providers.mock import MockProvider
from ai_team.providers.base import Result
from ai_team.protocol.message import MessageType as M


class DSHMockAdapter(MockProvider):
    async def send_task(self, session_id, task):
        await self.get_status(session_id)
        if task.task_type == "PLAN":
            return Result(type=M.PROPOSE, content="Use argparse and JSON storage; stable positive IDs; add/list/delete; unittest coverage. Engineer writes code; reviewer checks empty-text rejection and user instructions.", mock=True)
        return Result(type=M.APPROVE, content="Mock final approval; actual acceptance additionally requires executable contract tests.", mock=True)
