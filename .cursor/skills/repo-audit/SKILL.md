---
name: repo-audit
description: >-
  Analyze public GitHub repositories using the RepoAgent backend API and
  return structured health reports with scores and recommendations. Use when
  the user asks to audit, evaluate, score, or review a GitHub repo, compare
  open-source projects, or run RepoAgent analysis from the terminal or chat.
---

# RepoAgent Usage (GitHub Repo Audit)

Call the running RepoAgent backend to produce a **FinalReport**: total score, code/product dimensions, recommendations.

## Prerequisites

Backend must be running (default `http://localhost:8000`).

```bash
# Quick start — see run.md for full setup
cp .env.example .env          # fill MODEL_API_KEY
docker run -d -p 6379:6379 redis:7-alpine
python scripts/run_backend.py
```

Verify:

```bash
curl http://localhost:8000/api/v1/health/ready
# redis: ok, llm: ok
```

If backend is down, tell the user to start it per [run.md](../../../run.md). Do not guess scores without API data.

## Primary Workflow

Run the bundled script from **project root**:

```bash
python .cursor/skills/repo-audit/scripts/analyze_repo.py https://github.com/owner/repo
```

With progress on stderr:

```bash
python .cursor/skills/repo-audit/scripts/analyze_repo.py -v https://github.com/tiangolo/fastapi
```

### Script options

| Flag | Purpose |
|------|---------|
| `--base-url URL` | API base (default `http://localhost:8000`) |
| `--cache` | Return cached report only; skip new analysis |
| `--json` | Raw FinalReport JSON |
| `--poll-only` | Use GET `/report/{task_id}` instead of SSE |
| `-v` | Progress logs to stderr |
| `--skip-ready` | Skip health check |

**Cache lookup:**

```bash
python .cursor/skills/repo-audit/scripts/analyze_repo.py --cache tiangolo fastapi
```

**Owner/repo shorthand:**

```bash
python .cursor/skills/repo-audit/scripts/analyze_repo.py vuejs core
```

## URL Rules

Valid: `https://github.com/{owner}/{repo}`

Invalid:

- `https://github.com/owner` — user profile, not a repo
- Private repos — not supported
- Gitee/GitLab — not supported yet

## Present Results to User

After script succeeds, summarize in chat using this structure:

```markdown
# {repo_name} 体检报告

| 指标 | 分数 |
|------|------|
| 综合 | {total}/100 ({grade}) |
| 代码 | {code}/100 |
| 产品 | {product}/100 |

## 总结
{summary}

## 核心建议
1. ...
2. ...

## 综合结论
{verdict}
```

Expand on request:

- **Code details** → `code_audit.dimensions`, `critical_issues`, `highlights`
- **Product details** → `product_analysis.dimensions`
- **Full JSON** → re-run with `--json`

## Compare Multiple Repos

Run analysis for each repo, then produce a comparison table:

```markdown
| 仓库 | 总分 | 代码 | 产品 | 等级 |
|------|------|------|------|------|
| owner/a | 82 | 78 | 85 | B+ |
| owner/b | 71 | 68 | 74 | C |
```

Highlight trade-offs (e.g. high code score but low documentation).

## API Flow (manual / curl)

```
POST /api/v1/analyze          {"repo_url": "..."}  → task_id
GET  /api/v1/stream/{task_id}                       → SSE until report_complete + done
GET  /api/v1/report/{task_id}                       → poll fallback
GET  /api/v1/report/cache/{owner}/{repo}            → cache only
```

Prefer the script over hand-written curl.

## SSE Events (reference)

| Event | Meaning |
|-------|---------|
| `progress` | Stage update (fetch_data → agent_a/b/c → finalize) |
| `agent_log` | LLM streaming (verbose) |
| `stage_result` | One Agent finished |
| `report_complete` | FinalReport ready |
| `cache_hit` | Served from Redis |
| `error` | Failed (see code) |
| `done` | Stream closed |

Typical run: 1–3 minutes for a new analysis; cache hit is instant.

## Error Handling

| Symptom | Action |
|---------|--------|
| Connection refused | Start backend (`python scripts/run_backend.py`) |
| `redis: fail` | Start Redis on 6379 |
| `llm: missing_key` | Set `MODEL_API_KEY` in `.env` |
| URL 400 | Fix to `https://github.com/owner/repo` |
| Timeout | Retry; check `logs/app.log` |
| 503 task limit | Wait; `MAX_CONCURRENT_TASKS=3` |

Dev troubleshooting: [../repoagent-dev/troubleshooting.md](../repoagent-dev/troubleshooting.md)

## Limitations

- Requires running RepoAgent backend (not standalone LLM)
- No Vue UI — report shown in terminal/chat
- Public GitHub repos only
- First analysis consumes LLM quota; cache reuse is free

## Examples

See [examples.md](examples.md).
