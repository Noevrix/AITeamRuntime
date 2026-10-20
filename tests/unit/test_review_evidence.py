import json
import pytest
from ai_team.orchestration.workflow import ThreeAgentWorkflow
from ai_team.providers.base import ProviderError


def test_actual_evidence_is_persisted_before_final_review(kernel):
    task = kernel.create_task("implement", "a", "IMPLEMENT")
    workflow = ThreeAgentWorkflow(kernel)
    workflow.test_runs = 1
    names = ["todo.py", "test_todo.py", "test_runtime_contract.py", "USAGE.md", "tests-1.txt"]
    for name in names:
        (kernel.workspace / name).write_text("actual evidence: " + name, encoding="utf-8")
    kernel.events.emit(kernel.project.id, "TEST_RESULT", task.id, passed=True)
    evidence = json.loads(workflow.review_evidence(task))
    assert evidence["files"]["todo.py"] == "actual evidence: todo.py"
    assert len(evidence["blackboard"]["artifacts"]) == len(names)
    assert evidence["test_results"][0]["metadata"]["passed"]


def test_missing_evidence_fails_closed(kernel):
    task = kernel.create_task("implement", "a", "IMPLEMENT")
    with pytest.raises(ProviderError, match="missing"):
        ThreeAgentWorkflow(kernel).review_evidence(task)
