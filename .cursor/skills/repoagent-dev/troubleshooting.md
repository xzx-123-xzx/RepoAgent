# RepoAgent Troubleshooting

## SSL: CERTIFICATE_VERIFY_FAILED

**Symptom:** GitHub API fails; log shows `certificate verify failed`.

**Fix (dev only):**

```env
HTTP_SSL_VERIFY=false
```

Restart backend. Uses `backend/app/utils/http_client.py` → `get_ssl_verify()`.

Production: configure `SSL_CERT_FILE` or enterprise root CA; do not disable verify.

---

## ModuleNotFoundError: No module named 'common'

**Cause:** Backend started without project root on `PYTHONPATH`.

**Fix:**

```bash
python scripts/run_backend.py
```

Or set `PYTHONPATH` to repo root before `uvicorn`.

---

## Redis ping failed / connection refused

**Symptom:** `/health/ready` shows `redis: fail`; analysis errors on cache/task write.

**Fix:**

```bash
docker run -d --name repoagent-redis -p 6379:6379 redis:7-alpine
```

Confirm `.env`: `REDIS_HOST=localhost`, `REDIS_PORT=6379`.

Docker Compose: backend uses `REDIS_HOST=redis`.

---

## llm: missing_key

**Symptom:** `/health/ready` → `"llm": "missing_key"`.

**Fix:** Set in project root `.env`:

```env
MODEL_API_KEY=sk-...
MODEL_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
```

Restart backend. Config loaded from `common/config.py`.

---

## ValidationError on CodeAuditReport / ProductValueReport

**Symptom:** `overall_code_score Field required`, `dimensions Field required`.

**Cause:** LLM returned prose or wrong JSON shape.

**Already handled by:**

1. `JSON_ONLY_SUFFIX` on prompts
2. `parse_json_content()` extraction
3. `normalize_*_report()` in `json_parser.py`
4. `repair_json()` retry in `BaseAgent._parse_and_validate`

**If still failing:**

- Verify prompt template includes full schema example
- Add/update normalizer aliases for new field names LLM uses
- Check `SCHEMA_EXAMPLES[agent_id]` matches Pydantic model
- Inspect raw LLM output in `logs/app.log` under `[code_auditor]` tags

---

## GitHub URL 格式不正确 (4001)

**Cause:** User entered profile URL or invalid format.

**Valid:** `https://github.com/owner/repo`

**Invalid:** `https://github.com/owner` (no repo segment)

Validator: `backend/app/services/url_validator.py`.

---

## GitHub API rate limit (5001 / 403)

**Cause:** Unauthenticated limit ~60 req/hour.

**Fix:**

```env
GITHUB_TOKEN=ghp_...
```

Also benefits from Redis cache — repeated same repo skips GitHub fetch.

---

## GitHub 404 / PrivateRepoError (4002)

Only **public** repos supported. Private repos rejected at fetch.

---

## SSE connects but no report

**Checklist:**

1. Backend running on 8000
2. Frontend dev: Vite proxy `/api` → 8000
3. Browser Network: `POST /analyze` returns 202
4. EventSource on `/stream/{task_id}` receives events
5. Wait for `report_complete` then `done` (1–3 min typical)

Poll fallback: `GET /api/v1/report/{task_id}`.

---

## Frontend analyze fails silently

- F12 → Network → check `/api/v1/analyze` response
- CORS: `CORS_ORIGINS` must include frontend origin
- Both services must run in local dev mode

---

## logs/app.log empty or missing

Logger path: `common/config.py` → `LOG_FILE = logs/app.log` (project root).

Ensure `logs/` directory exists. `EventEmitter._log_event` writes progress, agent_log (buffered), stage_result, errors.

---

## Agent timeout / task timeout

Defaults:

```env
TASK_TIMEOUT=300
AGENT_TIMEOUT=120
```

Large repos: reduce sample size in `repo_fetcher.py`, not by disabling timeouts globally.

---

## Docker backend cannot reach Redis

Use `REDIS_HOST=redis` (service name), not `localhost`, inside Compose network.

---

## Git clone SSH port 22 refused

Not application code — network blocks SSH.

```bash
git clone https://github.com/xzx-123-xzx/RepoAgent.git
```

Or configure `~/.ssh/config` to use `ssh.github.com:443`.

---

## Git HTTPS SSL error

Same root cause as GitHub API SSL. For git only (dev):

```bash
git config --global http.sslVerify false
```

Prefer fixing certificates over disabling verify.
