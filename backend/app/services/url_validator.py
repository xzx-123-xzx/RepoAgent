import re

from app.utils.exceptions import InvalidUrlError

GITHUB_URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)/?$"
)


def parse_github_url(repo_url: str) -> tuple[str, str]:
    url = repo_url.strip().rstrip("/")
    match = GITHUB_URL_PATTERN.match(url)
    if not match:
        raise InvalidUrlError()
    owner = match.group("owner")
    repo = match.group("repo").removesuffix(".git")
    return owner, repo


def normalize_repo_url(owner: str, repo: str) -> str:
    return f"https://github.com/{owner}/{repo}"
