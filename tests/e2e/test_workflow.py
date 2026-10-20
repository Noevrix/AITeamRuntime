import asyncio
from ai_team.cli import run_demo
from ai_team.memory.database import Database


def test_three_agent_workflow(tmp_path):
    root = tmp_path / "demo"
    result = asyncio.run(run_demo(root))
    assert result["status"] == "ACCEPTED"
    assert result["stages"] == ["PLAN", "IMPLEMENT", "REVIEW", "REVISE", "REVIEW", "FINAL_REVIEW"]
    assert result["revisions"] == 1
    assert result["turns"] == 6
    assert result["test_runs"] == 2
    assert set(result["providers"].values()) == {"MOCK"}
    db = Database(root / "blackboard.sqlite")
    try:
        project_id = result["project_id"]
        assert all(t["status"] == "COMPLETED" for t in db.list("tasks", project_id))
        assert len(db.list("sessions", project_id)) == 3
        assert len(db.list("artifacts", project_id)) >= 4
        assert any(m["type"] == "REQUEST_CHANGES" for m in db.list("messages", project_id))
        assert sum(e["type"] == "TEST_RESULT" and e["metadata"]["passed"] for e in db.list("events", project_id)) == 2
        import json
        tasks = db.list("tasks", project_id)
        final = next(t for t in tasks if t["task_type"] == "FINAL_REVIEW")
        evidence = json.loads(final["description"])
        assert "argparse" in evidence["files"]["todo.py"]
        assert "OK" in evidence["files"]["tests-2.txt"]
        assert evidence["blackboard"]["artifacts"]
        plan = db.list("decisions", project_id)[0]["content"]
        assert next(t for t in tasks if t["task_type"] == "IMPLEMENT")["description"] == plan
    finally:
        db.close()


def test_endless_review_escalates_without_extra_call(tmp_path, monkeypatch):
    import pytest
    from ai_team.providers.workbuddy.mock_adapter import WorkBuddyMockAdapter
    from ai_team.providers.base import Result
    from ai_team.protocol.message import MessageType
    from ai_team.kernel.team_kernel import LimitExceeded
    from ai_team.orchestration.workflow import ThreeAgentWorkflow

    async def reject(self, session, task):
        return Result(type=MessageType.REQUEST_CHANGES, content="another change", mock=True)

    async def skip_execution(self, task):
        pass  # Unit-style workflow policy test; full executable E2E is above.

    monkeypatch.setattr(WorkBuddyMockAdapter, "send_task", reject)
    monkeypatch.setattr(ThreeAgentWorkflow, "verify", skip_execution)
    root = tmp_path / "loop"
    with pytest.raises(LimitExceeded, match="revision"):
        asyncio.run(run_demo(root))
    db = Database(root / "blackboard.sqlite")
    try:
        original = next(t for t in db.list("tasks") if t["task_type"] == "IMPLEMENT")
        assert original["revision_count"] == 2
        assert original["status"] == "ESCALATED"
        assert sum(e["type"] == "TURN_RESERVED" for e in db.list("events")) == 7
        assert any(m["type"] == "ESCALATE" for m in db.list("messages"))
    finally:
        db.close()


def test_auto_does_not_hide_real_turn_failure(tmp_path, monkeypatch):
    import pytest
    import ai_team.cli as cli
    from ai_team.providers.mock import MockProvider
    from ai_team.providers.base import ProviderError

    class ConnectedButFailing(MockProvider):
        is_mock = False
        def __init__(self, *args):
            super().__init__()
        async def send_task(self, session, task):
            raise ProviderError("inference unavailable")

    monkeypatch.setattr(cli, "CodexAdapter", ConnectedButFailing)
    root = tmp_path / "failure"
    with pytest.raises(ProviderError, match="inference unavailable"):
        asyncio.run(run_demo(root, "auto"))
    db = Database(root / "blackboard.sqlite")
    try:
        assert not any(e["type"] == "PROVIDER_FALLBACK" for e in db.list("events"))
        assert any(t["status"] == "FAILED" for t in db.list("tasks"))
        assert not (root / "summary.json").exists()
    finally:
        db.close()
