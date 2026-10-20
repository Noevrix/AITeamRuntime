"""Presence-only by default. --online explicitly uses the authorized API."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_team.providers.workbuddy.config import configuration_status, configured_client
from ai_team.providers.workbuddy.client import WorkBuddyError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()
    try:
        result = configuration_status()
        if args.online:
            online = asyncio.run(configured_client().online())
            result.update(status="ONLINE" if online else "OFFLINE", online=online)
    except WorkBuddyError as exc:
        result = exc.summary()
    except Exception:
        result = {"status": "CONFIG_ERROR"}
    print(json.dumps(result))
    return 0 if result["status"] in {"CONFIGURED", "ONLINE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
