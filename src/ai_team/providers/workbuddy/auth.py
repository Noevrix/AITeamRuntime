"""Confidential OAuth component: use only in an officially approved trusted deployment."""
import asyncio
import secrets
import time
from dataclasses import dataclass, field
from urllib.parse import urlencode, urlsplit, parse_qs
from .client import BASE, SCOPES, HttpTransport, WorkBuddyError, request_json


@dataclass(repr=False)
class Token:
    access: str = field(repr=False)
    expires_at: float
    scopes: frozenset
    refresh: str = field(default="", repr=False)

    @classmethod
    def parse(cls, data, clock=time.time, previous_refresh=""):
        if (not isinstance(data, dict) or data.get("token_type") != "Bearer" or
            not isinstance(data.get("access_token"), str) or not data["access_token"] or
            type(data.get("expires_in")) not in {int, float} or
            not 0 < data["expires_in"] <= 365 * 86400 or
            not isinstance(data.get("scope"), str) or
            not isinstance(data.get("refresh_token", previous_refresh), str)):
            raise WorkBuddyError("INVALID_RESPONSE")
        scopes = frozenset(data["scope"].split())
        if not SCOPES <= scopes:
            raise WorkBuddyError("FORBIDDEN")
        return cls(data["access_token"], clock() + data["expires_in"], scopes,
                   data.get("refresh_token", previous_refresh))


class OAuth:
    def __init__(self, client_id, redirect_uri, secret, *, approved_server=False,
                 transport=None, clock=time.time):
        self.client_id, self.redirect_uri, self._secret = client_id, redirect_uri, secret
        self.approved_server = approved_server
        self.transport, self.clock = transport or HttpTransport(), clock

    def validate(self):
        if not self.client_id or not self.redirect_uri or not self._secret:
            raise WorkBuddyError("NOT_CONFIGURED")
        if not self.approved_server:
            raise WorkBuddyError("DEPLOYMENT_UNCONFIRMED")
        uri = urlsplit(self.redirect_uri)
        # Conservative supported subset; no invented localhost/PKCE contract.
        if uri.scheme != "https" or not uri.hostname or uri.username or uri.password or uri.fragment:
            raise WorkBuddyError("INVALID_CONFIG")

    def begin(self):
        self.validate()
        pending = {"state": secrets.token_urlsafe(32), "created_at": self.clock(),
                   "redirect_uri": self.redirect_uri, "client_id": self.client_id}
        url = BASE + "/authorize?" + urlencode({
            "response_type": "code", "client_id": self.client_id,
            "redirect_uri": self.redirect_uri, "scope": " ".join(sorted(SCOPES)),
            "state": pending["state"]})
        return url, pending

    async def exchange(self, callback, pending):
        self.validate()
        try:
            uri, expected = urlsplit(callback), urlsplit(self.redirect_uri)
            query = parse_qs(uri.query, keep_blank_values=True, max_num_fields=32)
            expected_query = parse_qs(expected.query, keep_blank_values=True, max_num_fields=32)
        except (ValueError, TypeError):
            raise WorkBuddyError("STATE_MISMATCH") from None
        if (not isinstance(pending, dict) or
            not isinstance(pending.get("state"), str) or not pending["state"] or
            type(pending.get("created_at")) not in {int, float}):
            raise WorkBuddyError("STATE_MISMATCH")
        valid = (
            pending.get("client_id") == self.client_id and
            pending.get("redirect_uri") == self.redirect_uri and
            0 <= self.clock() - pending.get("created_at", 0) <= 600 and
            (uri.scheme, uri.netloc, uri.path) == (expected.scheme, expected.netloc, expected.path) and
            not uri.fragment and len(query.get("state", [])) == 1 and
            secrets.compare_digest(query["state"][0].encode(), pending["state"].encode()) and
            all(query.get(k) == v for k, v in expected_query.items()))
        if not valid:
            raise WorkBuddyError("STATE_MISMATCH")
        if "error" in query:
            raise WorkBuddyError("AUTH_FAILED")
        if len(query.get("code", [])) != 1 or not query["code"][0]:
            raise WorkBuddyError("AUTH_FAILED")
        return await self._grant({"grant_type": "authorization_code",
                                  "code": query["code"][0], "redirect_uri": self.redirect_uri})

    async def _grant(self, fields, previous_refresh=""):
        self.validate()
        try:
            data = await request_json(self.transport, "POST", "/token", form=True, timeout=20,
                                      data={**fields, "client_id": self.client_id,
                                            "client_secret": self._secret})
        except WorkBuddyError as exc:
            if exc.status_code in {400, 401}:
                raise WorkBuddyError("AUTH_FAILED", exc.status_code) from None
            raise
        # OAuth failures sometimes return HTTP 400. Raw bodies are never exposed.
        if "error" in data:
            raise WorkBuddyError("AUTH_FAILED")
        return Token.parse(data, self.clock, previous_refresh)

    async def refresh(self, token):
        if not token.refresh:
            raise WorkBuddyError("AUTH_REQUIRED")
        return await self._grant({"grant_type": "refresh_token", "refresh_token": token.refresh},
                                 token.refresh)


class TokenProvider:
    def __init__(self, token=None, oauth=None, save=None, clock=time.time):
        self._token, self.oauth, self.save, self.clock = token, oauth, save, clock
        self._invalid = False
        self._lock = asyncio.Lock()

    def invalidate(self):
        self._invalid = True

    async def access_token(self):
        async with self._lock:
            if self._invalid:
                raise WorkBuddyError("AUTH_REQUIRED")
            if self._token is None:
                raise WorkBuddyError("AUTH_REQUIRED")
            if not SCOPES <= self._token.scopes:
                raise WorkBuddyError("FORBIDDEN")
            if self._token.expires_at <= self.clock() + 30:
                if self.oauth is None:
                    raise WorkBuddyError("AUTH_REQUIRED")
                # Failure latches: no repeated refresh attempts or POST replay.
                self._invalid = True
                updated = await self.oauth.refresh(self._token)
                if self.save:
                    self.save(updated)
                self._token = updated
                self._invalid = False
            return self._token.access
