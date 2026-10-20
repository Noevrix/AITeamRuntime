"""Read verified historic artifacts; submit at most one review in a fresh session."""
import asyncio
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from ai_team.agents.agent import Agent, Project, Team
from ai_team.agents.role import Role
from ai_team.config import Limits
from ai_team.kernel.team_kernel import TeamKernel
from ai_team.memory.database import Database
from ai_team.protocol.artifact import Artifact
from ai_team.protocol.task import TaskStatus
from ai_team.providers.diagnostics import error_diagnostic
from .adapter import DSHAdapter

FILES = ("todo.py", "test_todo.py", "test_runtime_contract.py", "USAGE.md", "tests-1.txt")


def load_evidence(source):
    source = Path(source).resolve()
    database = source / "blackboard.sqlite"
    if database.is_symlink() or Path(str(database) + "-wal").exists():
        raise ValueError("Historic database must be a closed snapshot")
    connection = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        def rows(table):
            return [json.loads(r[0]) for r in connection.execute("SELECT data FROM " + table)]
        projects, decisions, tasks = rows("projects"), rows("decisions"), rows("tasks")
        if len(projects) != 1:
            raise ValueError("Expected one historical project")
        project = projects[0]
        plan_task = next(t for t in tasks if t["task_type"] == "PLAN" and t["status"] == "COMPLETED")
        plan_message = next(m for m in rows("messages") if m["task_id"] == plan_task["id"]
                            and m["type"] == "PROPOSE" and m["metadata"].get("mock") is False)
        plan = next(d for d in decisions if d["content"] == plan_message["content"])
        tests = next(e for e in rows("events") if e["type"] == "TEST_RESULT"
                     and e["metadata"].get("passed") is True and e["metadata"].get("exit_code") == 0)
        artifacts = rows("artifacts")
    finally:
        connection.close()
    files, references = {}, []
    workspace = source / "workspace"
    for name in FILES:
        path = workspace / name
        if path.is_symlink() or path.resolve().parent != workspace.resolve() or path.stat().st_size > 64_000:
            raise ValueError("Unsafe or oversized evidence")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        artifact = next(a for a in artifacts if a["path"] == name and a["sha256"] == digest)
        files[name] = data.decode("utf-8")
        references.append({"path": name, "sha256": digest, "artifact_id": artifact["id"], "task_id": artifact["task_id"]})
    if tests["metadata"].get("log") != "tests-1.txt" or not re.search(r"Ran 14 tests.*\bOK\b", files["tests-1.txt"], re.S):
        raise ValueError("Expected original passing 14-test evidence")
    # Exact excerpts, not a generated summary. Full plan remains referenced by hash.
    sections = re.split(r"(?m)(?=^\d+\. )", plan["content"])
    excerpt = "\n".join(s for s in sections if re.match(r"(?:2|11)\. ", s))
    if not excerpt:
        raise ValueError("Missing expected plan sections")
    evidence = {"requirement": project["goal"], "plan_excerpt": excerpt,
                "files": files, "test_summary": {"passed": 14, "exit_code": 0}}
    refs = {"project_id": project["id"], "plan_task_id": plan_task["id"], "decision_id": plan["id"],
            "plan_sha256": hashlib.sha256(plan["content"].encode()).hexdigest(), "artifacts": references}
    prompt = json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
    if len(prompt.encode()) > 24_000:
        raise ValueError("Review input exceeds bounded evidence budget")
    return prompt, refs


async def run_review(source, output, *, dsh_home, dsh_bin, max_tokens=4096, reasoning_effort="off"):
    if max_tokens not in (2048, 4096, 8192) or reasoning_effort not in ("off", "low"):
        raise ValueError("Unsupported review budget")
    prompt, references = load_evidence(source)  # Before state creation or SDK startup.
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)  # One-shot guard, never overwrite.
    workspace = output / "workspace"
    workspace.mkdir()
    (workspace / "review-input.json").write_text(prompt, encoding="utf-8")
    db = Database(output / "blackboard.sqlite")
    team = Team(name="Single DSH review", agent_ids=["architect"])
    project = Project(team_id=team.id, goal="Independently review the referenced historical TODO CLI")
    kernel = TeamKernel(db, project, team, workspace, Limits(max_agent_turns=1, max_revisions_per_task=0, turn_timeout=180))
    provider = DSHAdapter(workspace, dsh_home=dsh_home, dsh_bin=dsh_bin, provider="deepseek-account",
                          model="deepseek-flash", max_tokens=max_tokens, reasoning_effort=reasoning_effort, compact_review=True)
    kernel.register(Agent(id="architect", name="DSH Reviewer", provider_id="DSH", role=Role.ARCHITECT), provider)
    task = kernel.create_task("Review existing TODO CLI", "architect", "FINAL_REVIEW", prompt)
    kernel.blackboard.decide(project.id, json.dumps({"source_references": references}))
    db.put("artifacts", Artifact(project_id=project.id, task_id=task.id, path="review-input.json",
                                 sha256=hashlib.sha256(prompt.encode()).hexdigest()))
    kernel.events.emit(project.id, "REVIEW_REFERENCES", task.id, source_references=references)
    summary = {"status": "PROVIDER_ERROR", "task_id": task.id, "project_id": project.id,
               "application_attempts": 0, "max_tokens": max_tokens, "reasoning_effort": reasoning_effort,
               "blackboard_verified": False}
    try:
        await provider.connect()
        summary["application_attempts"] = 1
        result = await kernel.execute(task)
        decision = kernel.blackboard.decide(project.id, result.content)
        kernel.events.emit(project.id, "REVIEW_RESULT", task.id, decision=result.type,
                           diagnostic=provider.last_response_metadata, decision_id=decision["id"])
        reader = Database(output / "blackboard.sqlite")
        try:
            verified = (reader.get("decisions", decision["id"])["content"] == result.content
                        and reader.get("tasks", task.id)["status"] == "COMPLETED"
                        and any(m["task_id"] == task.id and m["type"] == result.type
                                and m["metadata"].get("mock") is False for m in reader.list("messages", project.id)))
        finally:
            reader.close()
        if not verified:
            raise ValueError("Persistence verification failed")
        summary.update(status=result.type, blackboard_verified=True, decision_id=decision["id"],
                       diagnostic=provider.last_response_metadata)
    except (Exception, asyncio.CancelledError) as exc:
        if kernel.tasks.get(task.id).status == TaskStatus.ASSIGNED:
            kernel.tasks.transition(task.id, TaskStatus.FAILED)
        diagnostic = error_diagnostic(exc)
        code = diagnostic["code"]
        status = ("MAX_TOKENS" if code == "MODEL_MAX_TOKENS" else "INVALID_RESPONSE" if code in
                  {"INVALID_MODEL_JSON", "INVALID_MODEL_CONTENT", "INVALID_MODEL_DECISION", "MISSING_FINAL_TEXT", "SESSION_MISMATCH"}
                  else "PROVIDER_ERROR")
        summary.update(status=status, diagnostic=diagnostic)
        kernel.events.emit(project.id, "REVIEW_FAILED", task.id, diagnostic=diagnostic)
    finally:
        try:
            await provider.close()
        except Exception:
            summary.update(status="PROVIDER_ERROR", cleanup_failed=True)
        db.close()
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
