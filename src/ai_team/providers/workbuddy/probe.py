"""One explicit observation task, recorded in the existing Kernel/Blackboard."""
import asyncio
import json
from pathlib import Path
from ai_team.agents.agent import Agent, Project, Team
from ai_team.agents.role import Role
from ai_team.kernel.team_kernel import TeamKernel
from ai_team.memory.database import Database
from ai_team.protocol.message import MessageType as M
from ai_team.protocol.task import TaskStatus as S
from .client import WorkBuddyError


async def run_probe(root: Path, adapter):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    workspace = root / "workspace"
    workspace.mkdir()
    path = root / "blackboard.sqlite"
    db = Database(path)
    team = Team(name="WorkBuddy observation", agent_ids=["reviewer"])
    project = Project(team_id=team.id, goal="One no-tools connectivity observation",
                      risks=["Local Assistant task completion and reply-to contract unconfirmed."])
    kernel = TeamKernel(db, project, team, workspace)
    kernel.register(Agent(id="reviewer", name="WorkBuddy", provider_id="WorkBuddy",
                          role=Role.REVIEWER), adapter)
    task = kernel.create_task("Observe WorkBuddy", "reviewer", "CONNECTIVITY",
                              "One synthetic echo only; never an APPROVE decision.")
    summary = {"status": "NOT_RUN", "project_id": project.id, "task_id": task.id,
               "application_attempts": 0, "blackboard_verified": False,
               "completion_verified": False, "mock": adapter.is_mock}
    decision = None
    try:
        kernel.tasks.transition(task.id, S.RUNNING)
        await adapter.connect()
        handle = await adapter.create_session("reviewer", workspace)
        db.put("sessions", {"id": handle, "project_id": project.id, "agent_id": "reviewer",
                           "provider_id": "WorkBuddy", "remote_session": False})

        def record(kind, metadata):
            kernel.events.emit(project.id, kind, task.id, **metadata)
            if kind == "SUBMIT_RESERVED":
                kernel.message(task, "kernel", "reviewer", M.ASK, metadata["prompt"],
                               remote_submission_pending=True)
            elif kind == "ECHO_OBSERVED":
                kernel.message(task, "reviewer", "kernel", M.REVIEW, metadata["content"],
                               mock=adapter.is_mock, completion_verified=False,
                               official_correlation_verified=False)

        kernel.events.emit(project.id, "TURN_RESERVED", task.id, turn=1)
        result = await adapter.observe_once(handle, on_event=record)
        summary.update(result)
        # Receipt is evidence, not a review decision or successful task terminal.
        kernel.tasks.transition(task.id, S.ESCALATED)
    except WorkBuddyError as exc:
        summary.update(exc.summary())
        kernel.tasks.transition(task.id, S.FAILED)
    except asyncio.CancelledError:
        summary["status"] = "CANCELLED"
        kernel.tasks.transition(task.id, S.CANCELLED)
    except Exception:
        summary["status"] = "INTERNAL_ERROR"
        kernel.tasks.transition(task.id, S.FAILED)
    finally:
        summary["application_attempts"] = adapter.attempts
        summary["task_status"] = kernel.tasks.get(task.id).status.value
        decision = kernel.blackboard.decide(project.id, json.dumps({
            "kind": "CONNECTIVITY_OBSERVATION", **summary}))
        summary["decision_id"] = decision["id"]
        kernel.events.emit(project.id, "WORKBUDDY_PROBE_STOPPED", task.id,
                           status=summary["status"], application_attempts=adapter.attempts)
        await adapter.close()
        db.close()
    # Independent reopen verifies actual persistence, including failure evidence.
    check = Database(path)
    try:
        summary["blackboard_verified"] = (
            check.get("decisions", decision["id"]) == decision and
            check.get("tasks", task.id)["status"] == summary["task_status"])
    finally:
        check.close()
    (root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
