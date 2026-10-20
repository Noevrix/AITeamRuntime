from .agent import Agent


class AgentRegistry:
    def __init__(self):
        self.agents: dict[str, Agent] = {}

    def register(self, agent: Agent):
        if agent.id in self.agents:
            raise ValueError("duplicate agent")
        self.agents[agent.id] = agent

    def get(self, agent_id: str) -> Agent:
        return self.agents[agent_id]
