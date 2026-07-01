import json

from app.agents.base import BaseAgent
from app.schemas.product_value import ProductValueReport
from app.schemas.repo_snapshot import RepoSnapshot


class ProductAnalystAgent(BaseAgent):
    agent_id = "product_analyst"
    prompt_file = "product_analyst.txt"
    output_schema = ProductValueReport

    def build_user_prompt(self, input_data: RepoSnapshot) -> str:
        payload = {
            "repo_name": input_data.repo_name,
            "description": input_data.description,
            "stars": input_data.stars,
            "forks": input_data.forks,
            "open_issues": input_data.open_issues,
            "created_at": input_data.created_at,
            "updated_at": input_data.updated_at,
            "topics": input_data.topics,
            "contributors_count": input_data.contributors_count,
            "commit_activity": input_data.commit_activity.model_dump(),
            "readme_content": input_data.readme_content,
        }
        return f"## 输入数据\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n请开始分析。"
