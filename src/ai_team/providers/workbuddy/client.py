"""Documented HTTPS endpoints only. No redirects, automatic retries or body logging."""
import asyncio
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from ai_team.providers.base import ProviderError

BASE = "https://www.workbuddy.cn/openapi/v2"
SCOPES = frozenset({"user.localassistant.readable", "user.localassistant.invokable"})
CODES = frozenset({
    "NOT_CONFIGURED", "AUTH_REQUIRED", "AUTH_FAILED", "FORBIDDEN", "RATE_LIMITED",
    "SERVER_ERROR", "HTTP_ERROR", "TIMEOUT", "CONNECTION_ERROR", "INVALID_RESPONSE",
    "OFFLINE", "BUSY", "CLOSED", "CANCELLED", "CANCEL_UNSUPPORTED",
    "COMPLETION_UNSUPPORTED", "COMPLETION_UNCONFIRMED", "STORAGE_ERROR",
    "DEPLOYMENT_UNCONFIRMED", "STATE_MISMATCH", "INVALID_CONFIG",
})


class WorkBuddyError(ProviderError):
    def __init__(self, code, http_status=None):
        self.code = code if code in CODES else "INVALID_RESPONSE"
        self.status_code = http_status if type(http_status) is int else None
        super().__init__(self.code)

    def summary(self):
        value = {"status": self.code}
        if self.status_code is not None:
            value["http_status"] = self.status_code
        return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class HttpTransport:
    """One HTTP request per invocation; bounded body, standard TLS verification."""
    async def request(self, method, path, *, headers=None, data=None, form=False, timeout=20):
        def perform():
            if not path.startswith("/") or path.startswith("//"):
                raise WorkBuddyError("INVALID_CONFIG")
            body = None
            request_headers = {"Accept": "application/json", **(headers or {})}
            if data is not None:
                body = (urllib.parse.urlencode(data) if form else json.dumps(data)).encode()
                request_headers["Content-Type"] = (
                    "application/x-www-form-urlencoded" if form else "application/json")
            request = urllib.request.Request(BASE + path, body, request_headers, method=method)
            try:
                # Explicitly avoid environment proxy credentials and redirect forwarding.
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
                with opener.open(request, timeout=timeout) as response:
                    raw = response.read(1_048_577)
                    if len(raw) > 1_048_576:
                        raise WorkBuddyError("INVALID_RESPONSE")
                    return response.status, raw
            except urllib.error.HTTPError as exc:
                # Do not read an error body: it may contain credentials or private data.
                status = exc.code
                exc.close()
                return status, b""
            except (TimeoutError, socket.timeout):
                raise WorkBuddyError("TIMEOUT") from None
            except urllib.error.URLError as exc:
                code = "TIMEOUT" if isinstance(exc.reason, TimeoutError) else "CONNECTION_ERROR"
                raise WorkBuddyError(code) from None
            except OSError:
                raise WorkBuddyError("CONNECTION_ERROR") from None
        return await asyncio.to_thread(perform)


async def request_json(transport, method, path, **kwargs):
    try:
        status, raw = await transport.request(method, path, **kwargs)
    except WorkBuddyError:
        raise
    except TimeoutError:
        raise WorkBuddyError("TIMEOUT") from None
    except Exception:
        raise WorkBuddyError("CONNECTION_ERROR") from None
    if status != 200:
        code = {401: "AUTH_FAILED", 403: "FORBIDDEN", 429: "RATE_LIMITED"}.get(
            status, "SERVER_ERROR" if 500 <= status < 600 else "HTTP_ERROR")
        raise WorkBuddyError(code, status)
    try:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, TypeError, UnicodeError):
        raise WorkBuddyError("INVALID_RESPONSE") from None


class WorkBuddyClient:
    def __init__(self, tokens, transport=None, timeout=20):
        self.tokens = tokens
        self.transport = transport or HttpTransport()
        self.timeout = timeout

    async def _request(self, method, path, data=None):
        token = await self.tokens.access_token()
        try:
            result = await request_json(
                self.transport, method, path, data=data, timeout=self.timeout,
                headers={"Authorization": "Bearer " + token})
        except WorkBuddyError as exc:
            if exc.code == "AUTH_FAILED":
                self.tokens.invalidate()
            raise
        if type(result.get("code")) is not int or result["code"] != 0 or not isinstance(result.get("data"), dict):
            raise WorkBuddyError("INVALID_RESPONSE")
        return result["data"]

    async def online(self):
        value = (await self._request("GET", "/localassistant")).get("online")
        if type(value) is not bool:
            raise WorkBuddyError("INVALID_RESPONSE")
        return value

    async def send(self, text):
        if not isinstance(text, str) or not text or len(text) > 128_000:
            raise WorkBuddyError("INVALID_CONFIG")
        value = (await self._request("POST", "/localassistant/message",
                                    {"content": text, "msg_type": "text"})).get("message_id")
        if not isinstance(value, str) or not value or len(value) > 512:
            raise WorkBuddyError("INVALID_RESPONSE")
        return value

    async def messages_after(self, cursor):
        data = await self._request("GET", "/localassistant/message?" +
                                   urllib.parse.urlencode({"message_id": cursor}))
        messages = data.get("messages")
        if not isinstance(messages, list) or len(messages) > 1000:
            raise WorkBuddyError("INVALID_RESPONSE")
        for message in messages:
            if (not isinstance(message, dict) or
                not isinstance(message.get("message_id"), str) or not message["message_id"] or
                message.get("role") not in {"user", "assistant"} or
                not isinstance(message.get("content"), list) or
                not isinstance(message.get("msg_type"), str)):
                raise WorkBuddyError("INVALID_RESPONSE")
        return messages
