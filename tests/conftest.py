import pytest
from ai_team.memory.database import Database
from ai_team.agents.agent import Agent, Project, Team
from ai_team.agents.role import Role
from ai_team.kernel.team_kernel import TeamKernel
from ai_team.providers.mock import MockProvider


@pytest.fixture
def kernel(tmp_path):
    db = Database(tmp_path / "state.sqlite")
    team = Team(name="test", agent_ids=["a", "b"])
    project = Project(team_id=team.id, goal="test")
    k = TeamKernel(db, project, team, tmp_path)
    provider = MockProvider()
    for key in team.agent_ids:
        k.register(Agent(id=key, name=key, provider_id="shared", role=Role.ENGINEER), provider)
    yield k
    db.close()
