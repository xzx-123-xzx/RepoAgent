# RepoAgent Reference

## Directory Map

```
RepoAgent/
├── .env                    # runtime config (project root)
├── common/
│   ├── config.py           # Config class, loads .env
│   ├── llm.py              # ChatOpenAI (MODEL_* env vars)
│   ├── logger.py           # RepoAgent logger → logs/app.log
│   └── path_utils.py       # get_file_path() from project root
├── backend/app/
│   ├── main.py
│   ├── config.py           # get_settings() → common.Config
│   ├── routers/            # analyze, stream, report, health
│   ├── schemas/            # Pydantic I/O models
│   ├── services/           # github_service, repo_fetcher, url_validator
│   ├── graph/              # workflow, event_emitter, task_registry, state
│   ├── agents/             # code_auditor, product_analyst, judge, base, registry
│   ├── llm/                # adapter, json_parser
│   ├── cache/              # redis_client
│   ├── middleware/         # rate_limit
│   └── utils/              # exceptions, http_client
├── frontend/src/
│   ├── services/api.ts     # analyze + EventSource
│   ├── composables/useAnalyze.ts
│   └── components/         # UrlInput, StreamLogPanel, ReportDashboard, ...
└── scripts/run_backend.py
```

## Data Models Chain

```
AnalyzeRequest { repo_url }
       ↓
RepoSnapshot
  ├── repo_name, stars, forks, languages, readme
  ├── file_tree[], source_samples[], dependency_files[]
  └── commit_activity, contributors_count, topics
       ↓
CodeAuditReport (Agent A)     ProductValueReport (Agent B)
       ↓                              ↓
              FinalReport (Agent C)
                ├── scores { total, code, product, weights }
                ├── grade, summary, verdict
                ├── code_audit, product_analysis (embedded)
                └── top_recommendations[]
```

## RepoFetcher Sampling Limits

Implemented in `backend/app/services/repo_fetcher.py`:

- File tree depth: up to 5 levels
- Source samples: key entry/config files, total content budget ~50KB
- README: truncated for prompt safety (~8000 chars in product agent path)
- Skips binary/large files

When extending fetch logic, preserve these limits to avoid timeout/OOM.

## LLM Adapter

`backend/app/llm/adapter.py`:

- `chat_stream(system, user)` → async token iterator (used by BaseAgent.run)
- `chat_json(system, user)` → dict via `parse_json_content`
- `repair_json(...)` → second LLM call with schema example + validation error

Provider config comes from `common/llm.py` (OpenAI-compatible API).

## Task Lifecycle

`backend/app/graph/task_registry.py` — in-memory task state for active runs.

`backend/app/routers/analyze.py`:

1. Validate URL + rate limit
2. Create task_id, register task
3. `asyncio.create_task(start_analysis_task(...))`
4. Return 202 with stream_url

`backend/app/routers/stream.py`:

1. Subscribe to `event_bus` queue for task_id
2. Stream SSE until `done` or disconnect

## Extend Workflow (Example: Agent D Security)

### 1. Schema — `schemas/security_report.py`

```python
class SecurityReport(BaseModel):
    agent_id: str = "security_auditor"
    overall_security_score: int
    dimensions: dict[str, DimensionScore]
    highlights: list[str]
    critical_issues: list[str]
    recommendations: list[str]
```

### 2. Agent — `agents/security_auditor.py`

```python
class SecurityAuditorAgent(BaseAgent):
    agent_id = "security_auditor"
    prompt_file = "security_auditor.txt"
    output_schema = SecurityReport

    def build_user_prompt(self, input_data: RepoSnapshot) -> str:
        ...
```

### 3. json_parser.py

Add dimension list, aliases, `normalize_security_report()`, entries in `NORMALIZERS` and `SCHEMA_EXAMPLES`.

### 4. workflow.py

Insert after agent_a or parallel branch (Phase 2):

```python
await emitter.emit_progress("agent_d", "started", "...", 52)
security_report = await self.agent_d.run(snapshot, emitter)
await emitter.emit_progress("agent_d", "completed", "...", 58)
```

Pass into judge input if C should merge security scores.

### 5. Judge / FinalReport

Extend `FinalReport` schema and `JudgeAgent.run_with_reports` — **additive fields only**.

## Frontend SSE Integration

`frontend/src/services/api.ts` — `createSSEConnection` registers listeners:

```
connected, progress, agent_log, stage_result, report_complete, cache_hit, error, done
```

New backend event → add to this array + handle in `useAnalyze.ts` / UI components.

## Docker Compose

Services: `redis`, `backend` (port 8000), `frontend` (nginx port 5173→80).

Backend env overrides: `REDIS_HOST=redis`, `PYTHONPATH=/app`.

## Phase 2 Roadmap (from README)

- Parallel Agent A + B, then C merge
- GitLab / Gitee support
- Agent D security, Agent E license compliance

When implementing Phase 2 parallel branch, use LangGraph conditional edges; keep EventEmitter ordering documented for frontend.
