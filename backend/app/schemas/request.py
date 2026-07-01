from pydantic import BaseModel, Field, HttpUrl


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub 仓库 URL", examples=["https://github.com/torvalds/linux"])
