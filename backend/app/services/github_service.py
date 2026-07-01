"""GitHub REST API client (Octokit-style wrapper using httpx)."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.utils.exceptions import GitHubApiError, PrivateRepoError
from app.utils.http_client import get_ssl_verify
from common.logger import my_logger

logger = my_logger


class GitHubService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.GITHUB_API_BASE.rstrip("/")
        self.verify = get_ssl_verify()
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.settings.GITHUB_TOKEN:
            self.headers["Authorization"] = f"Bearer {self.settings.GITHUB_TOKEN}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0, verify=self.verify) as client:
                response = await client.request(method, url, headers=self.headers, **kwargs)
        except httpx.HTTPError as exc:
            err_msg = str(exc)
            if "CERTIFICATE_VERIFY_FAILED" in err_msg or "certificate verify failed" in err_msg.lower():
                logger.error(
                    "GitHub API SSL 校验失败。请在 .env 中设置 HTTP_SSL_VERIFY=false（开发环境），"
                    "或配置企业根证书到 SSL_CERT_FILE。"
                )
            else:
                logger.error("GitHub API request failed: %s", exc)
            raise GitHubApiError(err_msg) from exc

        if response.status_code == 404:
            raise PrivateRepoError()
        if response.status_code == 403:
            raise GitHubApiError("GitHub API 限流或权限不足")
        if response.status_code >= 400:
            raise GitHubApiError(f"GitHub API 错误: {response.status_code}")

        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        data = await self._request("GET", f"/repos/{owner}/{repo}")
        if data.get("private"):
            raise PrivateRepoError()
        return data

    async def get_languages(self, owner: str, repo: str) -> dict[str, float]:
        return await self._request("GET", f"/repos/{owner}/{repo}/languages") or {}

    async def get_readme(self, owner: str, repo: str) -> str:
        try:
            data = await self._request("GET", f"/repos/{owner}/{repo}/readme")
            if not data:
                return ""
            import base64

            content = data.get("content", "")
            encoding = data.get("encoding", "base64")
            if encoding == "base64" and content:
                return base64.b64decode(content).decode("utf-8", errors="replace")
            return content or ""
        except PrivateRepoError:
            raise
        except GitHubApiError:
            return ""

    async def get_contributors_count(self, owner: str, repo: str) -> int:
        data = await self._request("GET", f"/repos/{owner}/{repo}/contributors", params={"per_page": 1, "anon": "true"})
        if isinstance(data, list):
            return len(data) if len(data) < 30 else 30
        return 0

    async def get_commit_activity(self, owner: str, repo: str) -> dict[str, Any]:
        commits = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/commits",
            params={"per_page": 100},
        )
        if not isinstance(commits, list):
            return {"last_30_days": 0, "last_90_days": 0, "last_commit_date": ""}

        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        last_30 = 0
        last_90 = 0
        last_commit_date = ""
        for item in commits:
            date_str = item.get("commit", {}).get("author", {}).get("date", "")
            if not date_str:
                continue
            if not last_commit_date:
                last_commit_date = date_str
            try:
                commit_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                continue
            delta = now - commit_date
            if delta <= timedelta(days=30):
                last_30 += 1
            if delta <= timedelta(days=90):
                last_90 += 1

        return {
            "last_30_days": last_30,
            "last_90_days": last_90,
            "last_commit_date": last_commit_date,
        }

    async def get_tree(self, owner: str, repo: str, max_depth: int = 5) -> list[str]:
        repo_data = await self.get_repo(owner, repo)
        default_branch = repo_data.get("default_branch", "main")
        ref_data = await self._request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{default_branch}")
        sha = ref_data["object"]["sha"]
        tree_data = await self._request("GET", f"/repos/{owner}/{repo}/git/trees/{sha}", params={"recursive": "1"})
        paths: list[str] = []
        for item in tree_data.get("tree", []):
            path = item.get("path", "")
            depth = path.count("/") + 1
            if depth <= max_depth:
                paths.append(path + ("/" if item.get("type") == "tree" else ""))
        return sorted(paths)

    async def get_file_content(self, owner: str, repo: str, path: str) -> str | None:
        try:
            data = await self._request("GET", f"/repos/{owner}/{repo}/contents/{path}")
            if isinstance(data, list):
                return None
            import base64

            content = data.get("content", "")
            if data.get("encoding") == "base64" and content:
                raw = base64.b64decode(content)
                if len(raw) > 20000:
                    return raw[:20000].decode("utf-8", errors="replace")
                return raw.decode("utf-8", errors="replace")
            return content
        except GitHubApiError:
            return None
