import asyncio
import json
from contextlib import suppress
from ai_team.providers.base import ProviderError


class AppServer:
    """Official stdio JSON-RPC transport. Never reads client auth files."""
    def __init__(self, executable="codex", timeout=30):
        self.executable, self.timeout = executable, timeout
        self.process = None
        self.pending = {}
        self.notifications = asyncio.Queue(maxsize=2048)
        self.serial = 0
        self.reader = None

    async def start(self):
        try:
            self.process = await asyncio.create_subprocess_exec(self.executable, "app-server", "--listen", "stdio://", stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, limit=4*1024*1024)
            self.reader = asyncio.create_task(self._read())
            await self.request("initialize", {"clientInfo": {"name": "ai_team_runtime", "title": "AI Team Runtime", "version": "0.1.0"}})
            await self.write({"method": "initialized", "params": {}})
        except Exception:
            await self.close()
            raise

    async def write(self, message):
        if not self.process or self.process.returncode is not None:
            raise ProviderError("Codex app-server unavailable")
        self.process.stdin.write((json.dumps(message) + "\n").encode())
        await self.process.stdin.drain()

    async def request(self, method, params):
        self.serial += 1
        key = self.serial
        future = asyncio.get_running_loop().create_future()
        self.pending[key] = future
        try:
            await self.write({"id": key, "method": method, "params": params})
            return await asyncio.wait_for(future, self.timeout)
        finally:
            self.pending.pop(key, None)

    async def _read(self):
        try:
            while line := await self.process.stdout.readline():
                msg = json.loads(line)
                if "id" in msg and "method" not in msg:
                    future = self.pending.get(msg["id"])
                    if future and not future.done():
                        if "error" in msg:
                            future.set_exception(ProviderError("Codex RPC rejected request"))
                        else:
                            future.set_result(msg.get("result", {}))
                elif "id" in msg:
                    # No implicit tool approvals, credentials or user-input fabrication.
                    await self.write({"id": msg["id"], "error": {"code": -32601, "message": "Interactive approval is unsupported by this headless client"}})
                elif msg.get("method") in {"turn/completed", "item/completed"}:
                    self.notifications.put_nowait(msg)
        except Exception:
            pass
        finally:
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(ProviderError("Codex app-server disconnected"))
            with suppress(asyncio.QueueFull):
                self.notifications.put_nowait({"method": "disconnected"})

    async def close(self):
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), 5)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()
        if self.reader:
            self.reader.cancel()
            with suppress(asyncio.CancelledError):
                await self.reader
