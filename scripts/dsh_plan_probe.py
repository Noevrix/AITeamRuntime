"""Local launcher: uses the existing adapter, never a mock or full workflow."""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if importlib.util.find_spec("deepseek_harness") is None:
    sys.path.insert(1, str(ROOT / "runs" / "dsh-sdk"))


if __name__ == "__main__":
    try:
        from ai_team.providers.dsh.probe import main
        from ai_team.providers.dsh.runtime import sdk_available
        if sys.argv[1:] == ["--preflight"]:
            if not sdk_available():
                print("SDK_NOT_INSTALLED: install the project dsh optional dependency.")
                raise SystemExit(2)
            print("LOCAL_PREFLIGHT_PASS: no provider started; no model called.")
            raise SystemExit(0)
        if len(sys.argv) == 3 and sys.argv[1] == "--account-home":
            # Explicit user-run opt-in; never accepts a key or token argument.
            raise SystemExit(main(ROOT / "runs", account_home=Path(sys.argv[2])))
        if len(sys.argv) != 1:
            print("UNSUPPORTED_ARGUMENTS")
            raise SystemExit(2)
        raise SystemExit(main(ROOT / "runs"))
    except ImportError:
        print("DEPENDENCY_MISSING: install project dependencies; no model called.")
        raise SystemExit(2)
