import asyncio
import json
from ai_team.providers.base import AgentProvider, Capabilities, ProviderError, Result
from ai_team.protocol.message import MessageType as M
from .app_server import AppServer


class CodexAdapter(AgentProvider):
    def __init__(self, executable="codex", *, read_only=False):
        self.read_only = read_only
        self.rpc = AppServer(executable)
        self.connected = False
        self.sessions = {}
        self.active = {}
        self.last_commands = []
        self.lock = asyncio.Lock()

    def capabilities(self):
        return Capabilities(persistent_session=True, file_access=True, code_execution=True, task_cancel=True, review=True, tool_use=True)

    async def connect(self):
        try:
            await self.rpc.start()
            account = await self.rpc.request("account/read", {"refreshToken": False})
            if account.get("account") is None:
                raise ProviderError("Codex not signed in: use official codex login")
            self.connected = True
        except Exception:
            await self.close()
            raise

    async def health_check(self):
        return self.connected and self.rpc.process.returncode is None

    async def create_session(self, agent_id, workspace):
        if not await self.health_check():
            raise ProviderError("Codex unavailable")
        result = await self.rpc.request("thread/start", {"cwd": str(workspace.resolve()), "approvalPolicy": "never", "sandbox": "read-only" if self.read_only else "workspace-write"})
        session = result["thread"]["id"]
        self.sessions[session] = str(workspace.resolve())
        return session

    async def resume_session(self, session_id, workspace):
        result = await self.rpc.request("thread/resume", {"threadId": session_id, "cwd": str(workspace.resolve()), "approvalPolicy": "never", "sandbox": "workspace-write"})
        self.sessions[result["thread"]["id"]] = str(workspace.resolve())
        return result["thread"]["id"]

    async def send_message(self, session_id, content):
        workspace = self.sessions[session_id]
        async with self.lock:
            self.last_commands = []
            policy = {"type": "readOnly"} if self.read_only else {"type": "workspaceWrite", "writableRoots": [workspace], "networkAccess": False}
            turn = await self.rpc.request("turn/start", {"threadId": session_id, "input": [{"type": "text", "text": content}], "approvalPolicy": "never", "sandboxPolicy": policy})
            turn_id = turn["turn"]["id"]
            self.active[session_id] = turn_id
            final_text = ""
            try:
                async with asyncio.timeout(180):
                    while True:
                        event = await self.rpc.notifications.get()
                        if event["method"] == "disconnected":
                            raise ProviderError("Codex disconnected during turn")
                        params = event.get("params", {})
                        if params.get("threadId") != session_id or params.get("turnId", params.get("turn", {}).get("id")) != turn_id:
                            continue
                        if event["method"] == "item/completed":
                            item = params.get("item", {})
                            if item.get("type") == "agentMessage":
                                final_text = item.get("text", "")
                            elif item.get("type") == "commandExecution":
                                # Bounded transport evidence; callers must redact before persistence.
                                if len(self.last_commands) < 40:
                                    self.last_commands.append({
                                        "command": str(item.get("command", ""))[:2000],
                                        "status": item.get("status"),
                                        "exit_code": item.get("exitCode"),
                                        "output": str(item.get("aggregatedOutput", ""))[:16000],
                                    })
                        elif event["method"] == "turn/completed":
                            if params["turn"]["status"] != "completed":
                                raise ProviderError("Codex turn failed or interrupted")
                            break
                try:
                    data = json.loads(final_text)
                    result = Result.model_validate(data)
                except (ValueError, TypeError) as exc:
                    raise ProviderError("Codex must return structured JSON result") from exc
                if result.mock:
                    raise ProviderError("real provider returned mock result")
                return result
            except (TimeoutError, asyncio.CancelledError):
                await self.interrupt(session_id)
                raise
            finally:
                self.active.pop(session_id, None)

    async def send_task(self, session_id, task):
        prompt = ("Work only inside the current demo workspace. Do not delegate or access credentials. "
                  "Implement todo.py with: python todo.py --file PATH add TEXT, list, delete ID. "
                  "Use persistent JSON, stable positive IDs, reject empty text and missing delete IDs. "
                  "Include test_todo.py using unittest and run python -m unittest discover -v. "
                  "Return ONLY JSON {\"type\":\"COMPLETE\",\"content\":\"brief result\"}.\n" + task.description)
        return await self.send_message(session_id, prompt)

    async def get_status(self, session_id):
        if session_id not in self.sessions:
            raise KeyError(session_id)
        return "RUNNING" if session_id in self.active else ("READY" if await self.health_check() else "UNAVAILABLE")

    async def interrupt(self, session_id):
        if session_id in self.active:
            await self.rpc.request("turn/interrupt", {"threadId": session_id, "turnId": self.active[session_id]})

    async def close(self):
        self.connected = False
        await self.rpc.close()
