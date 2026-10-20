"""Offline guard tests; these do not establish real model access."""
import asyncio
from types import SimpleNamespace
import pytest
from ai_team.orchestration.dual_real import DualRealWorkflow
from ai_team.providers.base import ProviderError


@pytest.mark.parametrize("mock,calls", [(True, 0), (False, 3)])
def test_guards_stop_before_task_creation(mock, calls):
    kernel = SimpleNamespace(registry=SimpleNamespace(get=lambda _: SimpleNamespace(provider_id="DSH")),
                             providers={"DSH": SimpleNamespace(is_mock=mock)})
    workflow = DualRealWorkflow(kernel, "unused")
    workflow.calls["DSH"] = calls
    with pytest.raises(ProviderError):
        asyncio.run(workflow.call("PLAN", "architect", "requirement"))
    assert workflow.records == []


def test_failed_call_is_counted_and_never_retried():
    calls = []
    async def execute(task):
        calls.append(task.id)
        raise ProviderError("offline failure")
    kernel = SimpleNamespace(registry=SimpleNamespace(get=lambda _: SimpleNamespace(provider_id="DSH")),
        providers={"DSH": SimpleNamespace(is_mock=False)},
        create_task=lambda *args: SimpleNamespace(id="test-task"), execute=execute)
    workflow = DualRealWorkflow(kernel, "unused")
    with pytest.raises(ProviderError):
        asyncio.run(workflow.call("PLAN", "architect", "requirement"))
    assert calls == ["test-task"]
    assert workflow.calls == {"DSH": 1, "Codex": 0}
