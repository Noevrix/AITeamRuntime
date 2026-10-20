"""Operator tool for an approved trusted Windows OAuth deployment, not desktop scraping."""
import argparse
import asyncio
import getpass
import json
import os
import sys
import warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_team.providers.workbuddy.auth import OAuth
from ai_team.providers.workbuddy.client import WorkBuddyError
from ai_team.providers.workbuddy.config import save_token, load_token
from ai_team.providers.workbuddy.store import SecureStore


def hidden_input(prompt):
    # getpass otherwise falls back to visible stdin on unsupported terminals.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            return getpass.getpass(prompt)
        except (getpass.GetPassWarning, EOFError):
            raise WorkBuddyError("AUTH_REQUIRED") from None


async def authorize(args):
    if not args.approved_trusted_server or os.environ.get("AI_TEAM_WORKBUDDY_DEPLOYMENT_APPROVED") != "1":
        raise WorkBuddyError("DEPLOYMENT_UNCONFIRMED")
    client_id = os.environ.get("AI_TEAM_WORKBUDDY_CLIENT_ID", "")
    redirect = os.environ.get("AI_TEAM_WORKBUDDY_REDIRECT_URI", "")
    if not client_id or not redirect:
        raise WorkBuddyError("NOT_CONFIGURED")
    store = SecureStore()
    # Secret never appears in argv, environment template, output or saved token data.
    secret = hidden_input("Approved server application secret (hidden): ")
    oauth = OAuth(client_id, redirect, secret, approved_server=True)
    if args.action == "begin":
        url, pending = oauth.begin()
        if store.exists("pending"):
            raise WorkBuddyError("BUSY")
        store.save("pending", pending)
        # URL has only public client configuration and random CSRF state.
        return {"status": "USER_CONSENT_REQUIRED", "authorization_url": url}
    if args.action == "exchange":
        if not store.exists("pending"):
            raise WorkBuddyError("AUTH_REQUIRED")
        pending = store.load("pending")
        callback = hidden_input("Callback URL received by your registered server (hidden): ")
        # Consume state before exchange: errors never automatically retry a code.
        store.delete("pending")
        token = await oauth.exchange(callback, pending)
    else:
        token = await oauth.refresh(load_token(store, client_id))
    save_token(store, token, client_id)
    return {"status": "CONFIGURED", "token_saved_encrypted": True,
            "real_model_validated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["begin", "exchange", "refresh"])
    parser.add_argument("--approved-trusted-server", action="store_true")
    args = parser.parse_args()
    try:
        result = asyncio.run(authorize(args))
        code = 0
    except WorkBuddyError as exc:
        result, code = exc.summary(), 2
    except (Exception, KeyboardInterrupt):
        result, code = {"status": "AUTH_FAILED"}, 2
    print(json.dumps(result))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
