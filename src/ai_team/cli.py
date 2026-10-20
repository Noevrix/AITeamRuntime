import asyncio
import json
import os
from pathlib import Path
import typer
from rich.console import Console
from ai_team.agents.agent import Agent, Team, Project
from ai_team.agents.role import Role
from ai_team.memory.database import Database
from ai_team.kernel.team_kernel import TeamKernel
from ai_team.providers.codex.adapter import CodexAdapter
from ai_team.providers.demo_engineer import DemoEngineer
from ai_team.providers.dsh.mock_adapter import DSHMockAdapter
from ai_team.providers.dsh.adapter import DSHAdapter
from ai_team.providers.workbuddy.mock_adapter import WorkBuddyMockAdapter
from ai_team.providers.workbuddy.adapter import WorkBuddyAdapter
from ai_team.providers.workbuddy.config import configured_client
from ai_team.orchestration.workflow import ThreeAgentWorkflow
from ai_team.protocol.task import uid

app = typer.Typer()
console = Console()


async def run_demo(root: Path, mode="mock", dsh_mode="mock", workbuddy_mode="mock"):
    if mode not in {"mock", "auto", "real"}:
        raise ValueError("mode must be mock, auto, or real")
    if dsh_mode not in {"mock", "real"}:
        raise ValueError("dsh_mode must be mock or real")
    if workbuddy_mode not in {"mock", "real"}:
        raise ValueError("workbuddy_mode must be mock or real")
    if workbuddy_mode == "real":
        # Must gate before starting any Codex/DSH process or spending a turn.
        WorkBuddyAdapter.require_review_support()
        reviewer = WorkBuddyAdapter(configured_client())
    else:
        reviewer = WorkBuddyMockAdapter()
    root.mkdir(parents=True, exist_ok=False)
    workspace = root / "workspace"
    workspace.mkdir()
    engineer = DemoEngineer() if mode == "mock" else CodexAdapter(os.environ.get("AI_TEAM_CODEX", "codex"))
    fallback = None
    try:
        await engineer.connect()
    except Exception as exc:
        await engineer.close()
        if mode == "real":
            raise
        fallback = type(exc).__name__
        console.print(f"Codex UNAVAILABLE ({fallback}); explicit fallback: MOCK")
        engineer = DemoEngineer()
        await engineer.connect()
    db = Database(root / "blackboard.sqlite")
    team = Team(name="Three Agent Team", agent_ids=["architect", "engineer", "reviewer"])
    project = Project(team_id=team.id, goal="Create a small Python TODO CLI with add/list/delete and tests.", risks=["Mock reviews are deterministic fixture checks, not independent AI reviews."])
    k = TeamKernel(db, project, team, workspace)
    architect = (DSHMockAdapter() if dsh_mode == "mock" else
                 DSHAdapter(workspace, model=os.environ.get("AI_TEAM_DSH_MODEL", "deepseek-v4-flash")))
    try:
        for key, name, provider, role in [("engineer", "Codex", engineer, Role.ENGINEER), ("architect", "DSH", architect, Role.ARCHITECT), ("reviewer", "WorkBuddy", reviewer, Role.REVIEWER)]:
            k.register(Agent(id=key, name=f"{name} {role.value}", provider_id=name, role=role), provider)
            if provider is not engineer:
                await provider.connect()
        if fallback:
            k.events.emit(project.id, "PROVIDER_FALLBACK", provider="Codex", reason=fallback, replacement="MOCK")
        result = await ThreeAgentWorkflow(k, progress=lambda text: console.print(text, markup=False)).run()
        result["project_id"] = project.id
        (root / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    finally:
        await k.close()
        db.close()


@app.command()
def demo(mode: str = "mock", output: Path = Path("runs"), dsh_mode: str = "mock", workbuddy_mode: str = "mock"):
    """Run an isolated demo; auto can consume Codex quota, mock never does."""
    if mode not in {"mock", "auto", "real"}:
        raise typer.BadParameter("mode must be mock, auto, or real")
    if dsh_mode not in {"mock", "real"}:
        raise typer.BadParameter("dsh-mode must be mock or real")
    if workbuddy_mode not in {"mock", "real"}:
        raise typer.BadParameter("workbuddy-mode must be mock or real")
    root = output / uid()
    console.print("[bold]AI TEAM RUN[/bold]\nGoal: Create Python TODO CLI")
    try:
        result = asyncio.run(run_demo(root, mode, dsh_mode, workbuddy_mode))
    except Exception as exc:
        console.print(f"STATUS: FAILED ({type(exc).__name__}) — {exc}")
        raise typer.Exit(1)
    console.print(result)
    console.print(f"Artifacts: {root}")


@app.command()
def doctor():
    """Probe official Codex handshake without making an inference request."""
    async def probe():
        provider = CodexAdapter(os.environ.get("AI_TEAM_CODEX", "codex"))
        try:
            await provider.connect()
            console.print("Codex: REAL transport/auth READY; inference not tested")
        except Exception as exc:
            console.print(f"Codex: UNAVAILABLE ({type(exc).__name__}: {exc})")
        finally:
            await provider.close()
    asyncio.run(probe())
    console.print("DSH: MOCK (official SDK requires separate configuration)\nWorkBuddy: MOCK (external API not configured)")


if __name__ == "__main__":
    app()
