from importlib.util import find_spec
from pathlib import Path
from ai_team.providers.base import ProviderError
from ai_team.config import dsh_auth_configured


def sdk_available():
    return find_spec("deepseek_harness") is not None


def create_runtime(**options):
    """Only the public SDK API; no desktop credential or private RPC access."""
    provider = options.get("provider", "deepseek-official")
    if provider not in {"deepseek-official", "deepseek-account"}:
        raise ProviderError("Unsupported DSH provider")
    if options.get("profile", "sdk") != "sdk":
        raise ProviderError("Only the separate SDK profile is supported")
    if provider == "deepseek-account":
        # DSH owns account authorization. Never read/copy its credential store,
        # and never equate route selection with a verified signed-in account.
        home = options.get("dsh_home")
        if not home or not Path(home).is_dir():
            raise ProviderError("NOT_CONFIGURED: account reuse requires an existing explicit DSH home")
    elif not dsh_auth_configured():
        raise ProviderError("NOT_CONFIGURED: DEEPSEEK_API_KEY is not configured in the launching environment")
    try:
        from deepseek_harness import DeepSeekHarness
    except ImportError:
        raise ProviderError("DSH SDK unavailable: install the optional dsh dependency") from None
    return DeepSeekHarness(**options)
