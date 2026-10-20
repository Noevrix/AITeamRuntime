"""One explicit planning turn through DSHAdapter and TeamKernel; no retries."""
import asyncio
import json
import os
from pathlib import Path
from ai_team.agents.agent import Agent, Project, Team
from ai_team.agents.role import Role
from ai_team.config import Limits, dsh_auth_configured
from ai_team.kernel.team_kernel import TeamKernel
from ai_team.memory.database import Database
from ai_team.protocol.message import MessageType
from ai_team.protocol.task import uid
from .adapter import DSHAdapter


async def run_probe(root: Path, *, account_home=None):
    # Check before creating state or starting any provider.
    if account_home is not None and not Path(account_home).is_dir():
        return {"status": "NOT_CONFIGURED", "phase": "preflight", "turns": 0}
    if account_home is None and not dsh_auth_configured():
        return {"status": "NOT_CONFIGURED", "phase": "preflight", "turns": 0}
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    workspace = root / "workspace"
    workspace.mkdir()
    db = Database(root / "blackboard.sqlite")
    team = Team(name="DSH planning probe", agent_ids=["architect"])
    project = Project(team_id=team.id, goal="Plan a pure Python add(a, b) function and two unittest cases. No implementation.")
    kernel = TeamKernel(db, project, team, workspace,
                        Limits(max_agent_turns=1, max_revisions_per_task=0, turn_timeout=130))
    # Account reuse is explicit; never discover a home or resume private sessions.
    provider = DSHAdapter(workspace, dsh_home=account_home if account_home is not None else root / "dsh-home",
                          provider="deepseek-account" if account_home is not None else "deepseek-official",
                          model="deepseek-flash" if account_home is not None else os.environ.get("AI_TEAM_DSH_MODEL", "deepseek-v4-flash"))
    kernel.register(Agent(id="architect", name="DSH Architect", provider_id="DSH", role=Role.ARCHITECT), provider)
    summary = {"status": "FAILED", "phase": "connect", "adapter": "DSHAdapter",
               "model_result_verified": False, "blackboard_verified": False,
               "turns": 0, "project_id": project.id, "evidence_directory": root.name}
    try:
        await provider.connect()
        summary["phase"] = "planning"
        task = kernel.create_task("Minimal real planning probe", "architect", "PLAN", project.goal)
        result = await kernel.execute(task)
        if result.mock or result.type != MessageType.PROPOSE or not result.content.strip():
            raise ValueError("invalid planning result")
        summary["model_result_verified"] = True
        summary["phase"] = "blackboard"
        decision = kernel.blackboard.decide(project.id, result.content)
        # Reopen SQLite independently: verify persisted evidence, not in-memory state.
        reader = Database(root / "blackboard.sqlite")
        try:
            messages = reader.list("messages", project.id)
            verified = (reader.get("decisions", decision["id"])["content"] == result.content
                        and reader.get("tasks", task.id)["status"] == "COMPLETED"
                        and any(m["type"] == "PROPOSE" and m["content"] == result.content
                                and m["metadata"].get("mock") is False for m in messages))
        finally:
            reader.close()
        if not verified:
            raise ValueError("persisted evidence mismatch")
        summary.update(status="PASS", phase="complete", blackboard_verified=True)
    except (Exception, asyncio.CancelledError) as exc:
        # Never serialize exception messages, SDK diagnostics or environment values.
        summary["error_category"] = ("TIMEOUT" if isinstance(exc, TimeoutError) else
                                     "CANCELLED" if isinstance(exc, asyncio.CancelledError) else
                                     "PROVIDER_OR_VALIDATION_FAILURE")
        known_errors = {
            "DSH returned an incomplete or failed model turn": "MODEL_TURN_FAILED",
            "DSH response must be a structured JSON Result": "INVALID_MODEL_JSON",
            "DSH response is empty or incorrectly marked mock": "INVALID_MODEL_CONTENT",
            "DSH returned an invalid decision for this stage": "INVALID_MODEL_DECISION",
        }
        if str(exc) in known_errors:
            summary["error_category"] = known_errors[str(exc)]
        kernel.events.emit(project.id, "PROBE_FAILED", phase=summary["phase"],
                           category=summary["error_category"])
    finally:
        summary["turns"] = kernel.turns
        try:
            await kernel.close()
        except Exception:
            summary.update(status="FAILED", error_category="CLEANUP_FAILURE")
        finally:
            db.close()
        (root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(output: Path, *, account_home=None):
    try:
        summary = asyncio.run(run_probe(output / ("dsh-plan-" + uid()), account_home=account_home))
    except KeyboardInterrupt:
        summary = {"status": "FAILED", "error_category": "CANCELLED"}
    except Exception:
        summary = {"status": "FAILED", "error_category": "LOCAL_SETUP_FAILURE"}
    print(json.dumps(summary, ensure_ascii=True))
    return 0 if summary["status"] == "PASS" else 1
