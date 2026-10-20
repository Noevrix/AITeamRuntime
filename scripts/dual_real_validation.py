"""Explicit live validation. An exclusive directory prevents accidental reruns."""
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "runs" / "dsh-sdk"))

from ai_team.agents.agent import Agent, Project, Team
from ai_team.agents.role import Role
from ai_team.config import Limits
from ai_team.kernel.team_kernel import TeamKernel
from ai_team.memory.database import Database
from ai_team.orchestration.dual_real import DualRealWorkflow
from ai_team.providers.codex.adapter import CodexAdapter
from ai_team.providers.dsh.adapter import DSHAdapter
from ai_team.providers.diagnostics import error_diagnostic


async def main():
    output = ROOT / "runs" / "v013-dual-real"
    output.mkdir(exist_ok=False)  # Never remove this guard to retry automatically.
    workspace = output / "workspace"
    workspace.mkdir()
    db_path = output / "blackboard.sqlite"
    db = Database(db_path)
    team = Team(name="V0.1.3 real collaboration", agent_ids=["architect", "engineer"])
    project = Project(team_id=team.id, goal=(
        "Implement a Python TODO CLI with add, list and delete: python todo.py --file PATH "
        "add TEXT | list | delete ID. Persist JSON; use stable positive IDs, list as ID: text; "
        "reject empty task text and unknown delete IDs with nonzero exit. Include unittest "
        "tests and USAGE.md. Use only the Python standard library."))
    kernel = TeamKernel(db, project, team, workspace,
                        Limits(max_agent_turns=5, max_revisions_per_task=1, turn_timeout=180))
    dsh = DSHAdapter(workspace, dsh_home=Path.home() / ".dsh", provider="deepseek-account",
                     dsh_bin=None)
    codex = CodexAdapter()
    kernel.register(Agent(id="architect", name="DSH Architect", provider_id="DSH", role=Role.ARCHITECT), dsh)
    kernel.register(Agent(id="engineer", name="Codex Engineer", provider_id="Codex", role=Role.ENGINEER), codex)
    flow = DualRealWorkflow(kernel, db_path, lambda value: print(value, flush=True))
    summary = {"status": "FAILED", "project_id": project.id, "phase": "connect"}
    try:
        await dsh.connect()
        await codex.connect()
        summary["phase"] = "workflow"
        summary.update(await flow.run())
    except BaseException as exc:
        summary["diagnostic"] = error_diagnostic(exc)
        summary["error_type"] = summary["diagnostic"].get("source_type", "ProviderError")
        # No raw provider diagnostics or credentials in output.
        kernel.events.emit(project.id, "DUAL_VALIDATION_FAILED", error_type=summary["error_type"],
                           diagnostic=summary["diagnostic"])
    finally:
        for provider in (dsh, codex):
            try:
                await provider.close()
            except Exception:
                summary.update(status="FAILED", cleanup_failed=True)
        summary.update(stages=flow.records, application_attempts=flow.calls,
                       plan_reference=flow.plan_reference, test_runs=flow.test_runs)
        reader = Database(db_path)
        try:
            summary["persisted_counts"] = {t: len(reader.list(t, project.id))
                for t in ("tasks", "messages", "decisions", "artifacts", "events")}
        finally:
            reader.close()
        db.close()
        (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in summary.items() if k != "stages"}, ensure_ascii=True), flush=True)
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
