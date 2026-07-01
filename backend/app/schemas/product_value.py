from pydantic import BaseModel, Field

from app.schemas.code_audit import DimensionScore


class ProductValueReport(BaseModel):
    agent_id: str = "product_analyst"
    overall_product_score: int = Field(ge=0, le=100)
    dimensions: dict[str, DimensionScore]
    highlights: list[str] = Field(default_factory=list)
    critical_issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
