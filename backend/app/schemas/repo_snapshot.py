from pydantic import BaseModel, Field


class SourceSample(BaseModel):
    path: str
    content: str
    lines: int = 0


class DependencyFile(BaseModel):
    path: str
    content: str


class CommitActivity(BaseModel):
    last_30_days: int = 0
    last_90_days: int = 0
    last_commit_date: str = ""


class RepoSnapshot(BaseModel):
    owner: str
    repo: str
    repo_name: str
    repo_url: str
    description: str = ""
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    primary_language: str = ""
    languages: dict[str, float] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    readme_content: str = ""
    file_tree: list[str] = Field(default_factory=list)
    source_samples: list[SourceSample] = Field(default_factory=list)
    dependency_files: list[DependencyFile] = Field(default_factory=list)
    commit_activity: CommitActivity = Field(default_factory=CommitActivity)
    contributors_count: int = 0
    topics: list[str] = Field(default_factory=list)
    is_private: bool = False
