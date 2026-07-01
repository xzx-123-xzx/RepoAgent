from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    score: int = Field(ge=0, le=100)
    summary: str = ""
    issues: list[str] = Field(default_factory=list)


class CodeAuditReport(BaseModel):
    agent_id: str = "code_auditor"
    overall_code_score: int = Field(ge=0, le=100)
    dimensions: dict[str, DimensionScore]
    highlights: list[str] = Field(default_factory=list)
    critical_issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
