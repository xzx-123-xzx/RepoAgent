"""Aggregate GitHub data into RepoSnapshot."""

from __future__ import annotations

from app.schemas.repo_snapshot import (
    CommitActivity,
    DependencyFile,
    RepoSnapshot,
    SourceSample,
)
from app.services.github_service import GitHubService
from app.services.url_validator import normalize_repo_url
from common.logger import my_logger

logger = my_logger

PRIORITY_FILES = {
    "readme.md",
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "go.mod",
    "cargo.toml",
    "dockerfile",
    "makefile",
    "main.py",
    "app.py",
    "index.js",
    "index.ts",
}
DEPENDENCY_PATTERNS = (
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "go.mod",
    "cargo.toml",
    "pom.xml",
    "build.gradle",
)
MAX_SAMPLE_BYTES = 50 * 1024


class RepoFetcher:
    def __init__(self, github: GitHubService | None = None) -> None:
        self.github = github or GitHubService()

    async def fetch(self, owner: str, repo: str) -> RepoSnapshot:
        repo_data = await self.github.get_repo(owner, repo)
        languages_raw = await self.github.get_languages(owner, repo)
        total_bytes = sum(languages_raw.values()) or 1
        languages = {k: round(v / total_bytes * 100, 1) for k, v in languages_raw.items()}
        primary_language = repo_data.get("language") or (max(languages, key=languages.get) if languages else "")

        readme = await self.github.get_readme(owner, repo)
        file_tree = await self.github.get_tree(owner, repo)
        commit_activity_raw = await self.github.get_commit_activity(owner, repo)
        contributors_count = await self.github.get_contributors_count(owner, repo)

        source_samples, dependency_files = await self._sample_sources(owner, repo, file_tree)

        return RepoSnapshot(
            owner=owner,
            repo=repo,
            repo_name=f"{owner}/{repo}",
            repo_url=normalize_repo_url(owner, repo),
            description=repo_data.get("description") or "",
            stars=repo_data.get("stargazers_count", 0),
            forks=repo_data.get("forks_count", 0),
            open_issues=repo_data.get("open_issues_count", 0),
            primary_language=primary_language or "",
            languages=languages,
            created_at=repo_data.get("created_at", ""),
            updated_at=repo_data.get("updated_at", ""),
            readme_content=readme[:8000],
            file_tree=file_tree,
            source_samples=source_samples,
            dependency_files=dependency_files,
            commit_activity=CommitActivity(**commit_activity_raw),
            contributors_count=contributors_count,
            topics=repo_data.get("topics") or [],
            is_private=repo_data.get("private", False),
        )

    async def _sample_sources(
        self, owner: str, repo: str, file_tree: list[str]
    ) -> tuple[list[SourceSample], list[DependencyFile]]:
        samples: list[SourceSample] = []
        deps: list[DependencyFile] = []
        total_bytes = 0

        candidates = []
        for path in file_tree:
            if path.endswith("/"):
                continue
            lower = path.lower()
            if any(lower.endswith(p) or lower.split("/")[-1] == p for p in DEPENDENCY_PATTERNS):
                candidates.insert(0, path)
            elif any(name in lower for name in PRIORITY_FILES) or lower.endswith((".py", ".js", ".ts", ".go", ".rs")):
                candidates.append(path)

        seen = set()
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            content = await self.github.get_file_content(owner, repo, path)
            if not content:
                continue
            size = len(content.encode("utf-8"))
            lower = path.lower()
            if any(lower.endswith(p) or lower.split("/")[-1] == p for p in DEPENDENCY_PATTERNS):
                deps.append(DependencyFile(path=path, content=content[:5000]))
                continue
            if total_bytes + size > MAX_SAMPLE_BYTES:
                continue
            total_bytes += size
            samples.append(SourceSample(path=path, content=content, lines=content.count("\n") + 1))
            if len(samples) >= 8:
                break

        return samples, deps
