from typing import Annotated, TypedDict

from app.schemas.code_audit import CodeAuditReport
from app.schemas.final_report import FinalReport
from app.schemas.product_value import ProductValueReport
from app.schemas.repo_snapshot import RepoSnapshot


class GraphState(TypedDict, total=False):
    task_id: str
    repo_url: str
    owner: str
    repo: str
    repo_snapshot: RepoSnapshot
    code_audit_report: CodeAuditReport
    product_value_report: ProductValueReport
    final_report: FinalReport
    current_stage: str
    error: str | None
