"""Default is offline preflight; --execute explicitly submits one real review."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "runs" / "dsh-sdk")]
from ai_team.providers.dsh.review_probe import load_evidence, run_review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-tokens", type=int, choices=[2048, 4096, 8192], default=4096)
    parser.add_argument("--reasoning-effort", choices=["off", "low"], default="off")
    parser.add_argument("--dsh-home", type=Path, default=Path.home() / ".dsh")
    args = parser.parse_args()
    source, output = ROOT / "runs/v013-dual-real", ROOT / "runs/v0132-dsh-review"
    try:
        if not args.execute:
            prompt, refs = load_evidence(source)
            result = {"status": "READY_OFFLINE", "input_bytes": len(prompt.encode()),
                      "artifact_count": len(refs["artifacts"]), "max_tokens": args.max_tokens,
                      "reasoning_effort": args.reasoning_effort, "model_called": False}
        else:
            result = asyncio.run(run_review(source, output, dsh_home=args.dsh_home,
                dsh_bin=None,
                max_tokens=args.max_tokens, reasoning_effort=args.reasoning_effort))
    except FileExistsError:
        result = {"status": "ALREADY_ATTEMPTED", "model_called": False}
    except (Exception, KeyboardInterrupt):
        result = {"status": "LOCAL_SETUP_ERROR"}
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["status"] in {"READY_OFFLINE", "APPROVE"} else 2 if result["status"] == "REQUEST_CHANGES" else 1


if __name__ == "__main__":
    raise SystemExit(main())
