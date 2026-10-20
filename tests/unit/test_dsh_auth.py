"""Offline checks with synthetic values only; no vendor calls or actual keys."""
import asyncio
from types import SimpleNamespace
import sys
import pytest
from ai_team.config import dsh_auth_configured
from ai_team.providers.base import ProviderError
from ai_team.providers.dsh.adapter import DSHAdapter
from ai_team.providers.dsh.auth import main
from ai_team.providers.dsh.runtime import create_runtime


@pytest.mark.parametrize("environment,expected", [
    ({}, False),
    ({"DEEPSEEK_API_KEY": ""}, False),
    ({"DEEPSEEK_API_KEY": " \t "}, False),
    ({"DEEPSEEK_API_KEY": "<your-deepseek-api-key>"}, False),
    ({"DEEPSEEK_API_KEY": "synthetic-test-value"}, True),
    ({"OTHER_API_KEY": "synthetic-test-value", "DSH_HOME": "home"}, False),
])
def test_boolean_presence_only(environment, expected):
    assert dsh_auth_configured(environment) is expected


@pytest.mark.parametrize("configured", [True, False])
def test_command_prints_status_only(monkeypatch, capsys, configured):
    if configured:
        monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-test-value")
    else:
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert main() == (0 if configured else 1)
    captured = capsys.readouterr()
    assert captured.out == ("CONFIGURED\n" if configured else "NOT_CONFIGURED\n")
    assert captured.err == ""


def test_missing_auth_never_constructs_sdk(monkeypatch, tmp_path):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    calls = []
    monkeypatch.setitem(sys.modules, "deepseek_harness",
                        SimpleNamespace(DeepSeekHarness=lambda **kwargs: calls.append(kwargs)))
    async def run():
        provider = DSHAdapter(tmp_path, dsh_home=tmp_path / "home")
        with pytest.raises(ProviderError, match="NOT_CONFIGURED"):
            await provider.connect()
        assert not provider.connected
        assert provider.runtime is None
        assert not await provider.health_check()
    asyncio.run(run())
    assert calls == []


def test_present_auth_not_forwarded_as_python_option(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-test-value")
    calls = []
    marker = object()
    def factory(**options):
        calls.append(options)
        return marker
    monkeypatch.setitem(sys.modules, "deepseek_harness", SimpleNamespace(DeepSeekHarness=factory))
    assert create_runtime(provider="deepseek-official") is marker
    assert calls == [{"provider": "deepseek-official"}]


def test_no_dotenv_or_desktop_auth_discovery(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=synthetic-test-value", encoding="utf-8")
    assert dsh_auth_configured() is False


def test_presence_is_checked_again_after_environment_change(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert not dsh_auth_configured()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-test-value")
    assert dsh_auth_configured()
    monkeypatch.delenv("DEEPSEEK_API_KEY")
    assert not dsh_auth_configured()


def test_account_route_uses_sdk_without_reading_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    calls = []
    monkeypatch.setitem(sys.modules, "deepseek_harness",
                        SimpleNamespace(DeepSeekHarness=lambda **kw: calls.append(kw)))
    create_runtime(provider="deepseek-account", dsh_home=str(tmp_path), profile="sdk")
    assert calls == [{"provider": "deepseek-account", "dsh_home": str(tmp_path), "profile": "sdk"}]


@pytest.mark.parametrize("options", [
    {"provider": "deepseek-account"},
    {"provider": "deepseek-account", "profile": "desktop"},
    {"provider": "unknown"},
])
def test_unsafe_runtime_options_fail_before_sdk(monkeypatch, options):
    calls = []
    monkeypatch.setitem(sys.modules, "deepseek_harness",
                        SimpleNamespace(DeepSeekHarness=lambda **kw: calls.append(kw)))
    with pytest.raises(ProviderError):
        create_runtime(**options)
    assert calls == []


def test_account_adapter_does_not_discover_home(monkeypatch, tmp_path):
    monkeypatch.setenv("DSH_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="explicitly"):
        DSHAdapter(tmp_path, provider="deepseek-account")
