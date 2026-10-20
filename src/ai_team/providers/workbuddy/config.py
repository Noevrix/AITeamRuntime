"""Project configuration names, not vendor-defined environment variables."""
import os
import math
from .auth import Token, TokenProvider
from .client import SCOPES, WorkBuddyClient, WorkBuddyError
from .store import SecureStore


def configuration_status(environ=None, store=None):
    env = os.environ if environ is None else environ
    present = lambda key: bool(env.get(key)) and not env[key].startswith("<")
    configured = present("AI_TEAM_WORKBUDDY_CLIENT_ID") and present("AI_TEAM_WORKBUDDY_REDIRECT_URI")
    approved = env.get("AI_TEAM_WORKBUDDY_DEPLOYMENT_APPROVED") == "1"
    exists = (store or SecureStore()).exists("token")
    return {
        "status": ("NOT_CONFIGURED" if not configured else
                   "DEPLOYMENT_UNCONFIRMED" if not approved else
                   "AUTH_REQUIRED" if not exists else "CONFIGURED"),
        "client_id_present": present("AI_TEAM_WORKBUDDY_CLIENT_ID"),
        "redirect_uri_present": present("AI_TEAM_WORKBUDDY_REDIRECT_URI"),
        "deployment_approved_by_operator": approved,
        "encrypted_token_present": exists,
        "token_validity_verified": False,
        "completion_supported": False,
    }


def save_token(store, token, client_id):
    store.save("token", {"client_id": client_id, "access": token.access,
                        "refresh": token.refresh, "expires_at": token.expires_at,
                        "scopes": sorted(token.scopes)})


def load_token(store, client_id):
    value = store.load("token")
    if (value.get("client_id") != client_id or
        not isinstance(value.get("access"), str) or not value["access"] or
        type(value.get("expires_at")) not in {int, float} or
        not math.isfinite(value["expires_at"]) or
        not isinstance(value.get("refresh"), str) or
        not isinstance(value.get("scopes"), list) or
        not all(isinstance(s, str) for s in value["scopes"])):
        raise WorkBuddyError("AUTH_REQUIRED")
    if not SCOPES <= set(value["scopes"]):
        raise WorkBuddyError("FORBIDDEN")
    return Token(value["access"], value["expires_at"], frozenset(value["scopes"]), value["refresh"])


def configured_client(environ=None, store=None):
    env = os.environ if environ is None else environ
    store = store or SecureStore()
    status = configuration_status(env, store)
    if status["status"] != "CONFIGURED":
        raise WorkBuddyError(status["status"])
    token = load_token(store, env["AI_TEAM_WORKBUDDY_CLIENT_ID"])
    # Desktop does not hold an application secret; expired tokens require trusted
    # OAuth component refresh. The API never silently replays a request after 401.
    return WorkBuddyClient(TokenProvider(token))
