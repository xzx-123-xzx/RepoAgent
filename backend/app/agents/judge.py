import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.llm.json_parser import normalize_final_report
from app.schemas.code_audit import CodeAuditReport
from app.schemas.final_report import FinalReport, Recommendation
from app.schemas.product_value import ProductValueReport
from app.schemas.repo_snapshot import RepoSnapshot


class JudgeInput(BaseModel):
    snapshot: RepoSnapshot
    code_audit: CodeAuditReport
    product_value: ProductValueReport


class JudgeAgent(BaseAgent):
    agent_id = "judge"
    prompt_file = "judge.txt"
    output_schema = FinalReport

    def __init__(self) -> None:
        self._fallback: dict[str, Any] = {}

    def normalize_output(self, data: dict[str, Any]) -> dict[str, Any]:
        return normalize_final_report(data, self._fallback)

    def build_user_prompt(self, input_data: JudgeInput) -> str:
        payload = {
            "repo_name": input_data.snapshot.repo_name,
            "repo_metrics": {
                "stars": input_data.snapshot.stars,
                "forks": input_data.snapshot.forks,
                "primary_language": input_data.snapshot.primary_language,
                "languages": input_data.snapshot.languages,
                "contributors_count": input_data.snapshot.contributors_count,
                "last_updated": input_data.snapshot.updated_at,
            },
            "code_audit_report": input_data.code_audit.model_dump(),
            "product_value_report": input_data.product_value.model_dump(),
        }
        return f"## 输入数据\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n请开始汇总。"

    async def run_with_reports(
        self,
        snapshot: RepoSnapshot,
        code_audit: CodeAuditReport,
        product_value: ProductValueReport,
        emitter,
    ) -> FinalReport:
        self._fallback = {
            "repo_name": snapshot.repo_name,
            "repo_url": snapshot.repo_url,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "repo_metrics": {
                "stars": snapshot.stars,
                "forks": snapshot.forks,
                "primary_language": snapshot.primary_language,
                "languages": snapshot.languages,
                "contributors_count": snapshot.contributors_count,
                "last_updated": snapshot.updated_at,
            },
            "code_score": code_audit.overall_code_score,
            "product_score": product_value.overall_product_score,
            "code_audit": code_audit.model_dump(),
            "product_analysis": product_value.model_dump(),
            "summary": f"{snapshot.repo_name} 仓库体检完成",
        }
        judge_input = JudgeInput(snapshot=snapshot, code_audit=code_audit, product_value=product_value)
        report = await self.run(judge_input, emitter)
        report.repo_name = snapshot.repo_name
        report.repo_url = snapshot.repo_url
        report.analyzed_at = self._fallback["analyzed_at"]
        report.repo_metrics = self._fallback["repo_metrics"]
        report.code_audit = code_audit
        report.product_analysis = product_value
        code_score = code_audit.overall_code_score
        product_score = product_value.overall_product_score
        report.scores.code_score = code_score
        report.scores.product_score = product_score
        report.scores.total_score = round(code_score * 0.5 + product_score * 0.5)
        if not report.top_recommendations:
            merged = code_audit.recommendations[:4] + product_value.recommendations[:4]
            report.top_recommendations = [
                Recommendation(priority="medium", category="code", action=r) for r in merged[:8]
            ]
        return report
