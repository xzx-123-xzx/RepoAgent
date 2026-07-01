import json

from app.agents.base import BaseAgent
from app.schemas.code_audit import CodeAuditReport
from app.schemas.repo_snapshot import RepoSnapshot


class CodeAuditorAgent(BaseAgent):
    agent_id = "code_auditor"
    prompt_file = "code_auditor.txt"
    output_schema = CodeAuditReport

    def build_user_prompt(self, input_data: RepoSnapshot) -> str:
        payload = {
            "repo_name": input_data.repo_name,
            "primary_language": input_data.primary_language,
            "languages": input_data.languages,
            "file_tree": input_data.file_tree[:200],
            "source_samples": [s.model_dump() for s in input_data.source_samples],
            "dependency_files": [d.model_dump() for d in input_data.dependency_files],
        }
        return f"## 输入数据\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n请开始分析。"
