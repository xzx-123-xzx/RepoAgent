from pydantic import BaseModel, Field

from app.schemas.code_audit import CodeAuditReport
from app.schemas.product_value import ProductValueReport


class ScoreWeights(BaseModel):
    code: float = 0.5
    product: float = 0.5


class Scores(BaseModel):
    total_score: int = Field(ge=0, le=100)
    code_score: int = Field(ge=0, le=100)
    product_score: int = Field(ge=0, le=100)
    weights: ScoreWeights = Field(default_factory=ScoreWeights)


class Recommendation(BaseModel):
    priority: str = "medium"
    category: str = "code"
    action: str


class FinalReport(BaseModel):
    agent_id: str = "judge"
    repo_name: str
    repo_url: str
    analyzed_at: str
    scores: Scores
    grade: str
    summary: str
    repo_metrics: dict
    code_audit: CodeAuditReport
    product_analysis: ProductValueReport
    top_recommendations: list[Recommendation] = Field(default_factory=list)
    verdict: str = ""
