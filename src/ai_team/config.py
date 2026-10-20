from pydantic import BaseModel, Field
import os
from collections.abc import Mapping


def dsh_auth_configured(environ: Mapping[str, str] | None = None) -> bool:
    """Presence only: no SDK, network, file reads, key output or validity claim."""
    source = os.environ if environ is None else environ
    value = source.get("DEEPSEEK_API_KEY", "").strip()
    # Reject our documented placeholder; do not guess the vendor's key format.
    return bool(value) and value != "<your-deepseek-api-key>"


class Limits(BaseModel):
    max_agent_turns: int = Field(default=12, ge=1, le=12)
    max_revisions_per_task: int = Field(default=2, ge=0, le=2)
    max_delegation_depth: int = Field(default=3, ge=0, le=3)
    turn_timeout: float = Field(default=180, gt=0, le=600)
