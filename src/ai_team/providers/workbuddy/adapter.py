import asyncio
import hashlib
import time
from uuid import uuid4
from ai_team.providers.base import AgentProvider, Capabilities
from .client import WorkBuddyError


class WorkBuddyAdapter(AgentProvider):
    """Official transport with observation-only probes until finality is documented.

    Local handles are correlation containers, not remote sessions or cwd bindings.
    No Result is returned without an officially defined task completion contract.
    """
    @staticmethod
    def require_review_support():
        raise WorkBuddyError("COMPLETION_UNSUPPORTED")

    def __init__(self, client=None, *, timeout=60, poll_interval=2, max_polls=20):
        if not 0 < timeout <= 180 or not 0 <= poll_interval <= 30 or not 1 <= max_polls <= 60:
            raise WorkBuddyError("INVALID_CONFIG")
        self.client = client
        self.timeout, self.poll_interval, self.max_polls = timeout, poll_interval, max_polls
        self.state = "NOT_CONFIGURED" if client is None else "AUTH_REQUIRED"
        self.handles = {}
        self.active = None
        self.active_handle = None
        self.attempts = 0
        self.observation = {}

    def capabilities(self):
        # Polling observations do not constitute streaming Results or verified reviews.
        return Capabilities()

    async def connect(self):
        if self.client is None:
            raise WorkBuddyError("NOT_CONFIGURED")
        if self.state == "CLOSED":
            raise WorkBuddyError("CLOSED")
        try:
            if not await self.client.online():
                raise WorkBuddyError("OFFLINE")
            self.state = "READY"
        except WorkBuddyError as exc:
            self.state = exc.code
            raise

    async def health_check(self):
        if self.client is None or self.state == "CLOSED" or self.active is not None:
            return False
        try:
            await self.connect()
            return True
        except WorkBuddyError:
            return False

    async def create_session(self, agent_id, workspace):
        if self.client is None:
            raise WorkBuddyError("NOT_CONFIGURED")
        if self.state != "READY":
            await self.connect()
        handle = "local-" + uuid4().hex
        self.handles[handle] = "READY"
        return handle

    async def send_message(self, session_id, content):
        if self.client is None:
            raise WorkBuddyError("NOT_CONFIGURED")
        # Kernel treats any Result as completion. Refuse BEFORE sending a remote task.
        raise WorkBuddyError("COMPLETION_UNSUPPORTED")

    async def send_task(self, session_id, task):
        return await self.send_message(session_id, task.description)

    async def get_status(self, session_id):
        return self.handles.get(session_id, self.state)

    async def interrupt(self, session_id):
        # No official remote cancel endpoint. Never claim remote cancellation.
        raise WorkBuddyError("CANCEL_UNSUPPORTED")

    async def cancel_wait(self, session_id):
        if session_id not in self.handles:
            raise WorkBuddyError("INVALID_CONFIG")
        if self.active is not None:
            if session_id != self.active_handle:
                raise WorkBuddyError("INVALID_CONFIG")
            self.active.cancel()

    async def observe_once(self, session_id, *, on_event=None):
        """Explicit diagnostic task, never a completed Kernel review.

        Only stores an exact synthetic echo; unrelated content is discarded.
        A nonce echo is application evidence, not official reply-to correlation.
        """
        if session_id not in self.handles:
            raise WorkBuddyError("INVALID_CONFIG")
        if self.active is not None or self.attempts:
            raise WorkBuddyError("BUSY")
        if self.state != "READY":
            raise WorkBuddyError("CLOSED" if self.state == "CLOSED" else "OFFLINE")
        self.active = asyncio.current_task()
        self.active_handle = session_id
        nonce = uuid4().hex
        expected = "WORKBUDDY_CONNECTIVITY_OK " + nonce
        prompt = f"请只回复 {expected}，不要执行任何工具操作或修改文件。"
        self.observation = {"application_attempts": 0, "observed_echo": False,
                            "official_correlation_verified": False, "completion_verified": False}

        def emit(kind, **data):
            if on_event:
                on_event(kind, data)

        try:
            async with asyncio.timeout(self.timeout):
                self.attempts += 1  # reserve before POST, including ambiguous failures
                self.observation["application_attempts"] = self.attempts
                self.handles[session_id] = "SUBMITTING"
                emit("SUBMIT_RESERVED", nonce=nonce, prompt=prompt)
                cursor = await self.client.send(prompt)
                # Persist hashes of opaque external IDs, never arbitrary server strings.
                self.observation["request_id_sha256"] = hashlib.sha256(cursor.encode()).hexdigest()
                emit("MESSAGE_SUBMITTED", **self.observation)
                self.handles[session_id] = "WAITING"
                seen = set()
                for _ in range(self.max_polls):
                    messages = await self.client.messages_after(cursor)
                    for message in messages:
                        fingerprint = hashlib.sha256(
                            (message["message_id"] + repr(message["content"])).encode()).hexdigest()
                        if fingerprint in seen:
                            continue
                        seen.add(fingerprint)
                        if len(seen) > 1000:
                            raise WorkBuddyError("INVALID_RESPONSE")
                        # No private history, metadata, tools or uncorrelated replies are persisted.
                        if (message["role"] == "assistant" and message["msg_type"] == "text" and
                            message["content"] == [expected]):
                            self.observation["observed_echo"] = True
                            self.observation["response_id_sha256"] = hashlib.sha256(
                                message["message_id"].encode()).hexdigest()
                            emit("ECHO_OBSERVED", content=expected, **self.observation)
                            self.handles[session_id] = "COMPLETION_UNCONFIRMED"
                            return {"status": "COMPLETION_UNCONFIRMED", **self.observation}
                    # Keep original cursor: avoid assuming undocumented ordering/completeness.
                    await asyncio.sleep(self.poll_interval)
                raise WorkBuddyError("TIMEOUT")
        except asyncio.CancelledError:
            self.handles[session_id] = "CANCELLED"
            emit("WAIT_CANCELLED", remote_cancelled=False)
            raise
        except TimeoutError:
            self.handles[session_id] = "TIMEOUT"
            raise WorkBuddyError("TIMEOUT") from None
        except WorkBuddyError as exc:
            self.handles[session_id] = exc.code
            raise
        finally:
            self.active = None
            self.active_handle = None

    async def close(self):
        active = self.active
        if active is not None and active is not asyncio.current_task():
            active.cancel()
            try:
                await active
            except (asyncio.CancelledError, WorkBuddyError):
                pass
        if self.client is not None:
            self.state = "CLOSED"
        for key in self.handles:
            self.handles[key] = "CLOSED"
