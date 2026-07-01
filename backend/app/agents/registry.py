from app.agents.base import BaseAgent
from app.agents.code_auditor import CodeAuditorAgent
from app.agents.judge import JudgeAgent
from app.agents.product_analyst import ProductAnalystAgent

AGENT_REGISTRY: dict[str, BaseAgent] = {
    "code_auditor": CodeAuditorAgent(),
    "product_analyst": ProductAnalystAgent(),
    "judge": JudgeAgent(),
}


def get_agent(agent_id: str) -> BaseAgent:
    return AGENT_REGISTRY[agent_id]
