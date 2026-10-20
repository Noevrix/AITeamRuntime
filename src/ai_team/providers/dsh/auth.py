"""Offline environment-presence check. This module never starts a provider."""
from ai_team.config import dsh_auth_configured


def main():
    configured = dsh_auth_configured()
    print("CONFIGURED" if configured else "NOT_CONFIGURED")
    return 0 if configured else 1


if __name__ == "__main__":
    raise SystemExit(main())
