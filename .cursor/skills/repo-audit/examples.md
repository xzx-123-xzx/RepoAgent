# RepoAgent Usage Examples

## Example 1: Basic audit

**User:** 帮我分析一下 fastapi 这个仓库

**Agent:**

```bash
python .cursor/skills/repo-audit/scripts/analyze_repo.py -v https://github.com/tiangolo/fastapi
```

Then summarize stdout markdown for the user.

---

## Example 2: Cached report

**User:** 之前分析过的 vue 仓库还有结果吗？

```bash
python .cursor/skills/repo-audit/scripts/analyze_repo.py --cache vuejs core
```

If 404, run full analysis without `--cache`.

---

## Example 3: Compare two projects

**User:** 对比 react 和 vue 哪个开源健康度更好

```bash
python .cursor/skills/repo-audit/scripts/analyze_repo.py --json https://github.com/facebook/react > /tmp/react.json
python .cursor/skills/repo-audit/scripts/analyze_repo.py --json https://github.com/vuejs/core > /tmp/vue.json
```

Parse `scores` from both JSON files and present comparison table + narrative.

---

## Example 4: Remote backend

**User:** 用部署在 192.168.1.10 的服务分析

```bash
python .cursor/skills/repo-audit/scripts/analyze_repo.py \
  --base-url http://192.168.1.10:8000 \
  https://github.com/langchain-ai/langgraph
```

---

## Example 5: Backend not running

**User:** 分析某个仓库

Agent checks:

```bash
curl -s http://localhost:8000/api/v1/health
```

If fails → instruct user:

1. `cp .env.example .env` and set `MODEL_API_KEY`
2. Start Redis
3. `python scripts/run_backend.py`

Do not fabricate a report.

---

## Example 6: Deep dive after summary

After showing summary, user asks: 「代码方面有什么问题？」

From cached `--json` output or prior run, cite:

- `code_audit.dimensions.*.issues`
- `code_audit.critical_issues`
- `code_audit.recommendations`

Same pattern for product: `product_analysis.*`.
