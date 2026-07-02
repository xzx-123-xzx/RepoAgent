#!/usr/bin/env python3
"""Call RepoAgent API to analyze a GitHub repository.

Usage:
  python scripts/analyze_repo.py https://github.com/tiangolo/fastapi
  python scripts/analyze_repo.py --cache tiangolo fastapi
  python scripts/analyze_repo.py --base-url http://localhost:8000 owner/repo
  python scripts/analyze_repo.py --json --poll-only https://github.com/vuejs/core
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE = "http://localhost:8000"
GITHUB_URL_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)/?$"
)
POLL_INTERVAL = 2.0
POLL_TIMEOUT = 360


def _request(
    method: str,
    url: str,
    body: dict | None = None,
    timeout: float = 30,
) -> tuple[int, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"detail": raw or exc.reason}
        return exc.code, payload


def parse_repo_input(url_or_owner: str, repo: str | None) -> tuple[str, str, str]:
    if repo:
        owner = url_or_owner.strip().strip("/")
        repo_name = repo.strip().strip("/").removesuffix(".git")
        repo_url = f"https://github.com/{owner}/{repo_name}"
        return owner, repo_name, repo_url

    text = url_or_owner.strip().rstrip("/")
    match = GITHUB_URL_RE.match(text)
    if not match:
        raise ValueError(
            "Invalid GitHub repo URL. Use https://github.com/owner/repo (not a user profile)."
        )
    owner = match.group("owner")
    repo_name = match.group("repo").removesuffix(".git")
    return owner, repo_name, text


def check_ready(base: str) -> dict[str, str]:
    _, payload = _request("GET", f"{base}/api/v1/health/ready")
    if not isinstance(payload, dict):
        return {"status": "unknown"}
    return payload.get("checks", {})


def get_cached_report(base: str, owner: str, repo: str) -> dict | None:
    status, payload = _request("GET", f"{base}/api/v1/report/cache/{owner}/{repo}")
    if status == 200 and isinstance(payload, dict):
        return payload
    return None


def start_analysis(base: str, repo_url: str) -> str:
    status, payload = _request("POST", f"{base}/api/v1/analyze", {"repo_url": repo_url})
    if status != 202:
        detail = payload.get("detail") or payload.get("message") or payload
        raise RuntimeError(f"Analyze failed ({status}): {detail}")
    task_id = payload.get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in response: {payload}")
    return task_id


def poll_report(base: str, task_id: str, verbose: bool = False) -> dict:
    deadline = time.time() + POLL_TIMEOUT
    last_status = ""
    while time.time() < deadline:
        status, payload = _request("GET", f"{base}/api/v1/report/{task_id}")
        if status == 404:
            raise RuntimeError("Task not found. Backend may have restarted.")
        task_status = payload.get("status", "")
        if task_status != last_status and verbose:
            print(f"[status] {task_status}", file=sys.stderr)
            last_status = task_status
        if task_status == "completed" and payload.get("report"):
            return payload["report"]
        if task_status == "failed":
            raise RuntimeError(f"Analysis failed: {payload}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Timed out after {POLL_TIMEOUT}s waiting for report.")


def stream_sse(base: str, task_id: str, verbose: bool = False) -> dict | None:
    url = f"{base}/api/v1/stream/{task_id}"
    req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
    report: dict | None = None
    try:
        with urllib.request.urlopen(req, timeout=POLL_TIMEOUT) as resp:
            event_type = ""
            data_lines: list[str] = []
            for raw_line in resp:
                line = raw_line.decode("utf-8").rstrip("\r\n")
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].strip())
                elif line == "" and event_type:
                    if data_lines:
                        payload = json.loads("\n".join(data_lines))
                        if verbose:
                            _print_sse_event(event_type, payload)
                        if event_type == "report_complete":
                            report = payload.get("report") or payload
                        elif event_type == "error":
                            msg = payload.get("message", payload)
                            raise RuntimeError(f"SSE error ({payload.get('code')}): {msg}")
                        elif event_type == "done":
                            break
                    event_type = ""
                    data_lines = []
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"SSE connect failed ({exc.code}): {body}") from exc
    return report


def _print_sse_event(event_type: str, payload: dict) -> None:
    if event_type == "progress":
        print(
            f"[{payload.get('progress_percent', 0)}%] {payload.get('stage')}: {payload.get('message')}",
            file=sys.stderr,
        )
    elif event_type == "cache_hit":
        print("[cache] Using cached report", file=sys.stderr)
    elif event_type == "stage_result":
        print(f"[done] {payload.get('agent')} stage complete", file=sys.stderr)
    elif event_type == "error":
        print(f"[error] {payload.get('message')}", file=sys.stderr)


def format_report_markdown(report: dict) -> str:
    scores = report.get("scores", {})
    total = scores.get("total_score", "N/A")
    code = scores.get("code_score", "N/A")
    product = scores.get("product_score", "N/A")
    grade = report.get("grade", "N/A")
    lines = [
        f"# RepoAgent Report: {report.get('repo_name', 'unknown')}",
        "",
        f"- **URL**: {report.get('repo_url', '')}",
        f"- **Analyzed at**: {report.get('analyzed_at', '')}",
        f"- **Total score**: {total}/100 (Grade: {grade})",
        f"- **Code score**: {code}/100",
        f"- **Product score**: {product}/100",
        "",
        "## Summary",
        report.get("summary", ""),
        "",
        "## Verdict",
        report.get("verdict", ""),
        "",
        "## Top Recommendations",
    ]
    for i, rec in enumerate(report.get("top_recommendations") or [], 1):
        if isinstance(rec, dict):
            lines.append(
                f"{i}. [{rec.get('priority', 'medium')}/{rec.get('category', '')}] {rec.get('action', '')}"
            )
        else:
            lines.append(f"{i}. {rec}")
    code_audit = report.get("code_audit", {})
    if isinstance(code_audit, dict) and code_audit.get("critical_issues"):
        lines.extend(["", "## Code Critical Issues"])
        for issue in code_audit["critical_issues"]:
            lines.append(f"- {issue}")
    product = report.get("product_analysis", {})
    if isinstance(product, dict) and product.get("critical_issues"):
        lines.extend(["", "## Product Critical Issues"])
        for issue in product["critical_issues"]:
            lines.append(f"- {issue}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a GitHub repo via RepoAgent API")
    parser.add_argument(
        "target",
        help="GitHub repo URL or owner (when used with repo name)",
    )
    parser.add_argument("repo", nargs="?", help="Repo name (optional if target is full URL)")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help=f"RepoAgent API base (default: {DEFAULT_BASE})")
    parser.add_argument("--cache", action="store_true", help="Only fetch cached report (no new analysis)")
    parser.add_argument("--json", action="store_true", help="Output raw FinalReport JSON")
    parser.add_argument("--poll-only", action="store_true", help="Poll /report instead of SSE stream")
    parser.add_argument("--skip-ready", action="store_true", help="Skip /health/ready check")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")

    try:
        owner, repo_name, repo_url = parse_repo_input(args.target, args.repo)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not args.skip_ready:
        checks = check_ready(base)
        if args.verbose:
            print(f"[ready] {checks}", file=sys.stderr)
        if checks.get("redis") == "fail":
            print("Error: Redis not ready. Start Redis and backend (see run.md).", file=sys.stderr)
            return 1
        if checks.get("llm") == "missing_key":
            print("Error: MODEL_API_KEY not configured in .env", file=sys.stderr)
            return 1

    if args.cache:
        report = get_cached_report(base, owner, repo_name)
        if not report:
            print(f"No cached report for {owner}/{repo_name}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(format_report_markdown(report))
        return 0

    if args.verbose:
        print(f"[analyze] {repo_url}", file=sys.stderr)

    try:
        task_id = start_analysis(base, repo_url)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.verbose:
        print(f"[task] {task_id}", file=sys.stderr)

    try:
        if args.poll_only:
            report = poll_report(base, task_id, verbose=args.verbose)
        else:
            report = stream_sse(base, task_id, verbose=args.verbose)
            if not report:
                if args.verbose:
                    print("[fallback] SSE ended without report, polling...", file=sys.stderr)
                report = poll_report(base, task_id, verbose=args.verbose)
    except (RuntimeError, TimeoutError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
