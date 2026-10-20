"""A one-POST diagnostic only; final task completion cannot currently be certified."""
import argparse
import asyncio
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ai_team.protocol.task import uid
from ai_team.providers.workbuddy.adapter import WorkBuddyAdapter
from ai_team.providers.workbuddy.config import configured_client, configuration_status
from ai_team.providers.workbuddy.client import WorkBuddyError
from ai_team.providers.workbuddy.probe import run_probe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send-once", action="store_true",
                        help="Explicitly permit one safe task; not a finality acceptance test")
    parser.add_argument("--output", type=Path, default=Path("runs/workbuddy"))
    args = parser.parse_args()
    try:
        if not args.send_once:
            result = configuration_status()
            result["application_attempts"] = 0
        else:
            adapter = WorkBuddyAdapter(configured_client())
            result = asyncio.run(run_probe(args.output / uid(), adapter))
    except WorkBuddyError as exc:
        result = {**exc.summary(), "application_attempts": 0}
    except (Exception, KeyboardInterrupt):
        result = {"status": "PROBE_ERROR", "application_attempts": "see persisted evidence"}
    print(json.dumps(result))
    # No documented finality contract => never return smoke PASS / exit 0.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
