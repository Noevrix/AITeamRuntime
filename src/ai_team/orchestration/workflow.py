import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path
from ai_team.protocol.task import TaskStatus as S
from ai_team.protocol.message import MessageType as M
from ai_team.protocol.artifact import Artifact
from ai_team.providers.base import ProviderError
from .demo_files import TODO_TESTS


class ThreeAgentWorkflow:
    def __init__(self, kernel, progress=None):
        self.kernel = kernel
        self.progress = progress or (lambda text: None)
        self.test_runs = 0
        self.stages = []

    def review_evidence(self, task):
        """Persist bounded, actual artifacts before asking the architect to review."""
        k = self.kernel
        files = {}
        total = 0
        names = ["todo.py", "test_todo.py", "test_runtime_contract.py", "USAGE.md"]
        names += [f"tests-{n}.txt" for n in range(1, self.test_runs + 1)]
        for name in names:
            path = k.workspace / name
            if not path.is_file() or path.is_symlink():
                raise ProviderError("missing or unsafe final review evidence: " + name)
            total += path.stat().st_size
            if total > 128_000:
                raise ProviderError("final review evidence exceeds 128 KB budget")
            data = path.read_bytes()
            files[name] = data.decode("utf-8", errors="replace")
            k.db.put("artifacts", Artifact(project_id=k.project.id, task_id=task.id,
                     path=name, sha256=hashlib.sha256(data).hexdigest()))
        return json.dumps({"blackboard": k.blackboard.snapshot(k.project.id),
                           "test_results": [e for e in k.db.list("events", k.project.id)
                                            if e["type"] == "TEST_RESULT"],
                           "files": files})

    async def verify(self, task):
        k = self.kernel
        # Independent contract suite is supplied by the runtime, not the engineer.
        contract = k.workspace / "test_runtime_contract.py"
        contract.write_text(TODO_TESTS, encoding="utf-8")
        process = await asyncio.create_subprocess_exec(sys.executable, "-I", "-m", "unittest", "discover", "-v", cwd=k.workspace, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        try:
            output, _ = await asyncio.wait_for(process.communicate(), 30)
        except BaseException:
            if process.returncode is None:
                process.kill()
                await process.wait()
            raise
        self.test_runs += 1
        self.progress(f"TEST: {'PASS' if process.returncode == 0 else 'FAIL'}")
        text = output.decode(errors="replace")
        log = k.workspace / f"tests-{self.test_runs}.txt"
        log.write_text(text, encoding="utf-8")
        k.message(task, "kernel", task.assigned_to, M.TEST, f"unittest exit={process.returncode}", log=log.name)
        k.events.emit(k.project.id, "TEST_RESULT", task.id, passed=process.returncode == 0, exit_code=process.returncode, log=log.name)
        if process.returncode:
            raise ProviderError("demo tests failed; see local test log")

    async def stage(self, kind, agent, description, parent=None):
        k = self.kernel
        identity = k.registry.get(agent)
        label = "MOCK" if k.providers[identity.provider_id].is_mock else "REAL"
        self.progress(f"{identity.name} [{label}]: {kind}")
        task = k.create_task(kind, agent, kind, description, parent)
        result = await k.execute(task)
        self.stages.append(kind)
        return task, result

    async def run(self):
        k = self.kernel
        started = time.monotonic()
        original = None
        try:
            _, plan = await self.stage("PLAN", "architect", k.project.goal)
            if plan.type != M.PROPOSE:
                raise ProviderError("architect must return PROPOSE")
            k.blackboard.decide(k.project.id, plan.content)
            original, result = await self.stage("IMPLEMENT", "engineer", plan.content)
            if result.type != M.COMPLETE:
                raise ProviderError("engineer did not complete implementation")
            await self.verify(original)
            while True:
                reviewer = k.providers[k.registry.get("reviewer").provider_id]
                review_input = ("Independently review implementation and usage guide."
                                if reviewer.is_mock else self.review_evidence(original))
                _, review = await self.stage("REVIEW", "reviewer", review_input, original)
                k.blackboard.decide(k.project.id, review.content)
                k.message(original, "reviewer", "engineer", review.type, review.content, mock=review.mock)
                if review.type == M.APPROVE:
                    break
                if review.type != M.REQUEST_CHANGES:
                    raise ProviderError("review rejected or malformed")
                if k.tasks.get(original.id).status == S.REVIEW:
                    k.tasks.transition(original.id, S.CHANGES_REQUESTED)
                revision = k.revise(original, review.content)
                self.progress("Codex Engineer: REVISE")
                result = await k.execute(revision)
                self.stages.append("REVISE")
                if result.type != M.COMPLETE:
                    raise ProviderError("revision did not complete")
                await self.verify(revision)
                k.tasks.transition(revision.id, S.COMPLETED)
            _, final = await self.stage("FINAL_REVIEW", "architect", self.review_evidence(original), original)
            if final.type != M.APPROVE:
                raise ProviderError("final review not approved")
            k.tasks.transition(original.id, S.COMPLETED)
            k.message(original, "kernel", "user", M.COMPLETE, "Workflow accepted; mock labels remain attached to provider outputs.")
            status = "ACCEPTED"
        except Exception as exc:
            if original and k.tasks.get(original.id).status in {S.REVIEW, S.CHANGES_REQUESTED}:
                k.tasks.transition(original.id, S.FAILED)
            k.events.emit(k.project.id, "WORKFLOW_FAILED", error_type=type(exc).__name__)
            raise
        finally:
            k.events.emit(k.project.id, "WORKFLOW_STOPPED", duration=round(time.monotonic()-started, 3))
        return {"status": status, "stages": self.stages, "tasks": len(k.db.list("tasks", k.project.id)), "messages": len(k.db.list("messages", k.project.id)), "revisions": k.tasks.get(original.id).revision_count, "test_runs": self.test_runs, "turns": k.turns, "duration": round(time.monotonic()-started, 3), "providers": {key: "MOCK" if value.is_mock else "REAL" for key, value in k.providers.items()}}
