"""One bounded DSH/Codex run; no mock fallback or application retries."""
import hashlib
import json
from ai_team.memory.database import Database
from ai_team.protocol.message import MessageType as M
from ai_team.protocol.task import TaskStatus as S
from ai_team.providers.base import ProviderError
from .workflow import ThreeAgentWorkflow
from ai_team.providers.diagnostics import error_diagnostic


class DualRealWorkflow(ThreeAgentWorkflow):
    def __init__(self, kernel, db_path, progress=None):
        super().__init__(kernel, progress)
        self.db_path = db_path
        self.records = []
        self.plan_reference = None
        self.calls = {"DSH": 0, "Codex": 0}

    async def call(self, kind, agent, description, parent=None, revision=None):
        k = self.kernel
        provider_id = k.registry.get(agent).provider_id
        if k.providers[provider_id].is_mock:
            raise ProviderError("Mock forbidden in real validation")
        if self.calls[provider_id] >= (3 if provider_id == "DSH" else 2):
            raise ProviderError("Application call budget exhausted")
        task = revision or k.create_task(kind, agent, kind, description, parent)
        record = {"stage": kind, "task_id": task.id, "provider": provider_id, "status": "STARTED"}
        self.records.append(record)
        self.calls[provider_id] += 1  # Attempt reserved, even when transport fails.
        self.progress(f"{kind}: {task.id}")
        try:
            result = await k.execute(task)
        except BaseException as exc:
            record.update(status="FAILED", diagnostic=error_diagnostic(exc))
            raise
        if result.mock:
            raise ProviderError("Mock result forbidden")
        record.update(status="RETURNED", decision=result.type, content=result.content)
        return task, result

    def persist_decision(self, task, result):
        k = self.kernel
        value = k.blackboard.decide(k.project.id, result.content)
        reader = Database(self.db_path)
        try:
            assert reader.get("decisions", value["id"]) == value
            assert any(m["task_id"] == task.id and m["content"] == result.content
                       and m["metadata"].get("mock") is False
                       for m in reader.list("messages", k.project.id))
        finally:
            reader.close()
        k.events.emit(k.project.id, "BLACKBOARD_VERIFIED", task.id, decision_id=value["id"])
        return value

    async def run(self):
        k = self.kernel
        plan_task, plan = await self.call("PLAN", "architect", k.project.goal)
        if plan.type != M.PROPOSE:
            raise ProviderError("Plan must be PROPOSE")
        decision = self.persist_decision(plan_task, plan)
        self.plan_reference = {"decision_id": decision["id"], "task_id": plan_task.id,
                               "sha256": hashlib.sha256(plan.content.encode()).hexdigest()}
        # Export only the verified Blackboard decision into the engineer sandbox.
        reader = Database(self.db_path)
        try:
            stored = reader.get("decisions", decision["id"])
        finally:
            reader.close()
        export = {"reference": self.plan_reference, "blackboard_decision": stored}
        (k.workspace / "blackboard-plan.json").write_text(json.dumps(export, ensure_ascii=False), encoding="utf-8")
        instruction = ("Read blackboard-plan.json, the persisted Blackboard plan export. Follow that plan and "
                       "create USAGE.md as well as implementation and tests. Include this decision ID in your "
                       "final JSON content to acknowledge the plan you read: " + decision["id"] +
                       ". Run the actual tests. Do not change blackboard-plan.json. Requirement: " + k.project.goal)
        original, implementation = await self.call("IMPLEMENT", "engineer", instruction)
        if implementation.type != M.COMPLETE or decision["id"] not in implementation.content:
            raise ProviderError("Engineer did not acknowledge persisted plan reference")
        if json.loads((k.workspace / "blackboard-plan.json").read_text(encoding="utf-8")) != export:
            raise ProviderError("Plan export changed")
        k.events.emit(k.project.id, "ENGINEER_PLAN_REFERENCE", original.id,
                      decision_id=decision["id"], plan_task_id=plan_task.id,
                      sha256=self.plan_reference["sha256"])
        await self.verify(original)
        for attempt in range(2):
            evidence = self.review_evidence(original)
            # Preserve the exact source/test snapshot supplied for each review.
            (k.workspace / f"review-evidence-{attempt + 1}.json").write_text(evidence, encoding="utf-8")
            review_task, review = await self.call("FINAL_REVIEW", "architect",
                "Review independently using the actual files, test outputs and original requirement below. "
                "Return APPROVE or REQUEST_CHANGES, explaining concrete findings.\n" + evidence, original)
            self.persist_decision(review_task, review)
            k.message(original, "architect", "engineer", review.type, review.content,
                      mock=False, review_task_id=review_task.id)
            if review.type == M.APPROVE:
                k.tasks.transition(original.id, S.COMPLETED)
                return {"status": "PASS", "reworked": bool(attempt)}
            if review.type != M.REQUEST_CHANGES or attempt:
                raise ProviderError("Review not approved within one revision")
            k.tasks.transition(original.id, S.CHANGES_REQUESTED)
            revision = k.revise(original, "Review task " + review_task.id + ": " + review.content)
            revised_task, revised = await self.call("REVISE", "engineer", revision.description, revision=revision)
            if revised.type != M.COMPLETE:
                raise ProviderError("Revision incomplete")
            await self.verify(revised_task)
            k.tasks.transition(revised_task.id, S.COMPLETED)
