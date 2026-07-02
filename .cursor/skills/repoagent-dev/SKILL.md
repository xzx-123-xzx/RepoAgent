---
name: repoagent-dev
description: >-
  Develop, extend, and troubleshoot the RepoAgent GitHub audit platform
  (FastAPI + LangGraph + Vue3). Use when modifying RepoAgent code, adding
  Agents or API endpoints, wiring SSE events, fixing local startup issues,
  or questions about architecture, schemas, prompts, Redis cache, or LLM
  JSON parsing in this repository.
---

# RepoAgent Development

RepoAgent is a GitHub repository health-check platform: fetch public repo data → three serial Agents (code audit, product value, judge) → SSE streaming → FinalReport with scores and recommendations.

## Before Coding

1. Read [run.md](../../../run.md) for local startup (`.env`, Redis, `PYTHONPATH`).
2. Architecture details: [reference.md](reference.md).
3. Known failures: [troubleshooting.md](troubleshooting.md).

## Layer Rules (Do Not Violate)

```
Presentation → API → Orchestration → Agent → DataCollection
                              ↓           ↓
                         Infrastructure ←─┘
```

| Layer | Path | Must NOT |
|-------|------|----------|
| API | `backend/app/routers/` | contain business logic |
| Orchestration | `backend/app/graph/` | call GitHub directly |
| Agent | `backend/app/agents/` | import routers or know HTTP |
| Data | `backend/app/services/` | import LangGraph state |
| Shared config/LLM | `common/` | depend on `backend/app` |

**Dependency direction is one-way.** Agent layer must not call API routes.

## Key Entry Points

| File | Role |
|------|------|
| `backend/app/main.py` | FastAPI app, CORS, rate limit, exception handler |
| `backend/app/graph/workflow.py` | Main pipeline: cache → fetch → A → B → C → finalize |
| `backend/app/agents/base.py` | Agent base: prompt, LLM stream, JSON parse/validate/repair |
| `backend/app/graph/event_emitter.py` | SSE events + mirrored `logs/app.log` |
| `common/config.py` | All env vars (LLM, GitHub, Redis, timeouts) |
| `common/llm.py` | LangChain `ChatOpenAI` instance |
| `scripts/run_backend.py` | Start backend with correct `PYTHONPATH` |

## Local Dev Checklist

```bash
# 1. .env at project root (not backend/)
cp .env.example .env   # fill MODEL_API_KEY, MODEL_BASE_URL, MODEL_NAME

# 2. Redis
docker run -d --name repoagent-redis -p 6379:6379 redis:7-alpine

# 3. Backend (from project root)
pip install -r backend/requirements.txt
python scripts/run_backend.py

# 4. Frontend
cd frontend && npm install && npm run dev
```

Verify: `GET /api/v1/health/ready` — redis + llm must be ok.

**Critical:** `.env` lives at repo root; `common/` is imported via `PYTHONPATH=项目根目录`.

## Pipeline Flow

```
POST /api/v1/analyze → task_id
GET  /api/v1/stream/{task_id}  (SSE)

workflow.run():
  cache hit? → cache_hit + report_complete + done
  else:
    fetch_data (RepoFetcher → RepoSnapshot)
    agent_a    (CodeAuditorAgent → CodeAuditReport)
    agent_b    (ProductAnalystAgent → ProductValueReport)
    agent_c    (JudgeAgent → FinalReport)
    finalize   (Redis cache + report_complete + done)
```

Progress mapping in `workflow.py`: fetch 5→20%, A 25→50%, B 55→75%, C 80→90%, finalize 95→100%.

## Agent Development

Every Agent extends `BaseAgent` in `backend/app/agents/base.py`.

### Required class attributes

```python
class MyAgent(BaseAgent):
    agent_id = "my_agent"           # unique, used in SSE + json_parser
    prompt_file = "my_agent.txt"    # under agents/prompts/
    output_schema = MyReport        # Pydantic model in schemas/
```

### Required methods

- `build_user_prompt(input_data: BaseModel) -> str` — serialize input as JSON/text for LLM.

Optional overrides:

- `normalize_output(data)` — use when LLM field names drift; register normalizer in `json_parser.py`.

### Agent run lifecycle (BaseAgent.run)

1. Load system prompt from `agents/prompts/{prompt_file}`
2. Append `JSON_ONLY_SUFFIX` to user prompt
3. Stream LLM → emit `agent_log` chunks via `EventEmitter`
4. `_parse_and_validate`: parse JSON → Pydantic validate → on failure call `llm_adapter.repair_json`
5. Emit `stage_result` with validated output

### Add Agent D — checklist

```
- [ ] backend/app/schemas/my_report.py       # Pydantic output schema
- [ ] backend/app/agents/my_agent.py         # extends BaseAgent
- [ ] backend/app/agents/prompts/my_agent.txt
- [ ] backend/app/llm/json_parser.py         # NORMALIZERS + SCHEMA_EXAMPLES entry
- [ ] backend/app/agents/registry.py         # AGENT_REGISTRY
- [ ] backend/app/graph/workflow.py          # new stage + emit_progress
- [ ] frontend types/components (if exposed in UI)
```

Do **not** change existing Agent output schemas — only add new ones.

### Existing Agents

| ID | Class | Input | Output |
|----|-------|-------|--------|
| `code_auditor` | `CodeAuditorAgent` | `RepoSnapshot` (tree, samples, deps) | `CodeAuditReport` |
| `product_analyst` | `ProductAnalystAgent` | `RepoSnapshot` (readme, stars, activity) | `ProductValueReport` |
| `judge` | `JudgeAgent` | A + B reports + metrics | `FinalReport` |

A and B both read `RepoSnapshot` independently; serial order is for SSE clarity and LLM concurrency control.

## Schema & JSON Rules

- All Agent I/O: Pydantic v2 models in `backend/app/schemas/`.
- LLM must return JSON only; `JSON_ONLY_SUFFIX` is appended automatically.
- `json_parser.py` handles: markdown fences, partial JSON extraction, dimension aliases, score clamping 0–100.
- New Agent: add `NORMALIZERS[agent_id]` and `SCHEMA_EXAMPLES[agent_id]` in `json_parser.py`.

Score fields:

- Agent A: `overall_code_score` + `dimensions.{directory_structure, architecture_quality, tech_debt, dependency_risk, code_standards}`
- Agent B: `overall_product_score` + 5 product dimensions
- Agent C: `scores.total_score = code * 0.5 + product * 0.5`

## SSE Events

Defined in `backend/app/schemas/sse_events.py`, emitted via `EventEmitter`:

| Event | When |
|-------|------|
| `connected` | SSE client attached |
| `progress` | Stage start/complete |
| `agent_log` | LLM streaming token (buffered to log file) |
| `stage_result` | Agent finished, full JSON |
| `report_complete` | FinalReport ready |
| `cache_hit` | Redis returned cached report |
| `error` | Failure with code |
| `done` | Stream closed |

Add new event: extend `SSEEvent` schema → add `EventEmitter.emit_*` → mirror in `_log_event` → frontend `api.ts` handler list.

## API Endpoints

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/analyze` | Body `{repo_url}` → 202 + task_id |
| GET | `/api/v1/stream/{task_id}` | SSE stream |
| GET | `/api/v1/report/{task_id}` | Poll fallback |
| GET | `/api/v1/report/cache/{owner}/{repo}` | Cache lookup only |
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/health/ready` | Redis + LLM key check |

URL validation: `backend/app/services/url_validator.py` — must match `https://github.com/{owner}/{repo}` (not user profile).

## Error Codes

Use subclasses in `backend/app/utils/exceptions.py`:

| Code | Class | Stage |
|------|-------|-------|
| 4001 | `InvalidUrlError` | validate |
| 4002 | `PrivateRepoError` | fetch_data |
| 4003 | `TaskNotFoundError` | — |
| 4290 | `RateLimitError` | — |
| 5001 | `GitHubApiError` | fetch_data |
| 5002 | `AgentTimeoutError` | agent |
| 5003 | `LLMError` | agent |
| 5004 | `TaskTimeoutError` | workflow |

Raise `RepoAgentError` subclasses; `main.py` handler converts to JSON `{code, message, stage}`.

## Config (common/config.py)

Required for analysis:

```env
MODEL_API_KEY=
MODEL_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
```

Recommended:

```env
GITHUB_TOKEN=          # raises API rate limit
HTTP_SSL_VERIFY=true     # set false only in dev if SSL fails
REDIS_HOST=localhost
REDIS_PORT=6379
CORS_ORIGINS=http://localhost:5173
```

Redis keys: `repoagent:report:{owner}/{repo}` (TTL `REDIS_EXPIRE`), `repoagent:task:{task_id}` (1h).

## Code Conventions

- Match existing style: async FastAPI, type hints, minimal comments.
- Reuse `llm_adapter` (`backend/app/llm/adapter.py`); do not instantiate LLM in Agents.
- GitHub calls only through `GitHubService` / `RepoFetcher`; use `get_ssl_verify()` from `http_client.py`.
- Logging: `from common.logger import my_logger`.
- Frontend API base: Vite proxy `/api` → `localhost:8000`; production nginx same pattern.
- Keep diffs focused; do not refactor unrelated code.

## Testing

```bash
cd backend
PYTHONPATH=.. pytest tests/ -v
```

Existing: `test_json_parser.py`. Add tests when changing parsers, validators, or Agent normalization.

## When User Reports Bugs

1. Check `logs/app.log` (SSE events mirrored here).
2. Hit `/api/v1/health/ready`.
3. Match error code → [troubleshooting.md](troubleshooting.md).
4. Do not suggest user-profile URLs; require `https://github.com/owner/repo`.

## Additional Resources

- Architecture & extension patterns: [reference.md](reference.md)
- SSL / Redis / LLM JSON / GitHub rate limit fixes: [troubleshooting.md](troubleshooting.md)
- User-facing run guide: [run.md](../../../run.md)
- Full design doc: [README.md](../../../README.md)
