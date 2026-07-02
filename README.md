# RepoAgent

> GitHub 仓库智能体检平台 — 三 Agent 串行流水线 + SSE 实时流式推送

**快速上手：** 克隆后本地运行见 [run.md](run.md) · Cursor AI 集成见 [第 12 节](#12-cursor-skill-集成)

---

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 整体分层架构](#2-整体分层架构)
- [3. 端到端数据流](#3-端到端数据流)
- [4. 多 Agent 协作设计](#4-多-agent-协作设计)
- [5. SSE 流式推送事件设计](#5-sse-流式推送事件设计)
- [6. 后端 API 接口清单](#6-后端-api-接口清单)
- [7. 项目目录结构](#7-项目目录结构)
- [8. 技术选型说明](#8-技术选型说明)
- [9. 约束规则与扩展规范](#9-约束规则与扩展规范)
- [10. 风险点与优化方案](#10-风险点与优化方案)
- [11. 48 小时开发排期](#11-48-小时开发排期)
- [12. Cursor Skill 集成](#12-cursor-skill-集成)

---

## 1. 项目概述

### 1.1 目标

用户输入公开 GitHub 仓库 URL，系统通过 **3 个专属 Agent 串行流水线**协同分析，**实时 SSE 流式推送**分析进度与阶段性结论，最终输出：

- 结构化仓库体检报告
- 0~100 综合评分（代码维度 + 产品维度）
- 针对性优化建议清单

### 1.2 核心能力矩阵

| 能力域 | 说明 |
|--------|------|
| 数据采集 | GitHub REST API（octokit.py）拉取元数据、README、目录树、源码快照 |
| 智能分析 | LangGraph 编排 Agent A → B → C 串行流转 |
| 实时通信 | FastAPI SSE 推送思考日志、阶段结论、最终报告 |
| 结果缓存 | Redis 缓存已分析仓库，降低 GitHub API 调用 |
| 可扩展 | 模块化 Agent 注册机制，支持后续新增 Agent D/E |

---

## 2. 整体分层架构

### 2.1 架构总图（文字版）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         【表现层 Presentation Layer】                        │
│  Vue3 + TypeScript + Vite + TailwindCSS                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ URL 输入组件  │  │ SSE 日志面板  │  │ 报告可视化   │  │ 评分/建议展示    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ HTTP / SSE
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                         【接口层 API Gateway Layer】                         │
│  FastAPI (Async) + Pydantic 数据校验 + 路由 + 中间件                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ POST /analyze│  │ GET /stream  │  │ GET /report  │  │ GET /health      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  中间件：CORS / 限流 / 超时 / 异常统一处理 / Request-ID 追踪                   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                       【编排层 Orchestration Layer】                         │
│  LangGraph 状态机 + 任务生命周期管理                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  GraphState (Pydantic)                                                │   │
│  │  fetch_data → agent_a → agent_b → agent_c → finalize                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                        │
│  │ EventEmitter │  │ TimeoutGuard │  │ TaskRegistry │                        │
│  │ (SSE 桥接)    │  │ (超时控制)    │  │ (任务状态)    │                        │
│  └──────────────┘  └──────────────┘  └──────────────┘                        │
└───────────────┬─────────────────────────────┬─────────────────────────────────┘
                │                             │
┌───────────────▼──────────────┐  ┌───────────▼─────────────────────────────────┐
│   【Agent 层 Agent Layer】    │  │        【数据采集层 Data Collection】         │
│  ┌────────┐ ┌────────┐ ┌────┐│  │  GitHubService (octokit.py)                   │
│  │Agent A │→│Agent B │→│ C  ││  │  ┌─────────┐ ┌─────────┐ ┌─────────────────┐ │
│  │代码审计 │ │产品价值 │ │裁判││  │  │Metadata │ │FileTree │ │SourceSnapshot   │ │
│  └────────┘ └────────┘ └────┘│  │  └─────────┘ └─────────┘ └─────────────────┘ │
│  统一 Agent 基类 + Prompt 模板 │  │  URL校验 / 私有仓库拦截 / 限流 / 异常捕获      │
└───────────────┬──────────────┘  └───────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────────────────────┐
│                      【基础设施层 Infrastructure Layer】                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ LLM Adapter  │  │ Redis Cache  │  │ Config/Env   │  │ Logging/Metrics  │  │
│  │ DeepSeek/豆包 │  │ 结果+元数据   │  │ GITHUB_TOKEN │  │ 结构化日志        │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 各层职责

| 层级 | 职责 | 关键模块 |
|------|------|----------|
| **表现层** | 用户交互、SSE 订阅、报告渲染 | `UrlInput`, `StreamLogPanel`, `ReportDashboard` |
| **接口层** | REST/SSE 端点、请求校验、错误码 | `routers/analyze.py`, `schemas/` |
| **编排层** | Agent 串行调度、状态持久化、事件广播 | `graph/workflow.py`, `graph/state.py` |
| **Agent 层** | 领域分析、结构化 JSON 输出 | `agents/code_auditor.py`, `agents/product_analyst.py`, `agents/judge.py` |
| **数据采集层** | GitHub API 封装、数据预处理 | `services/github_service.py` |
| **基础设施层** | LLM 抽象、缓存、配置、日志 | `llm/adapter.py`, `cache/redis_client.py` |

### 2.3 模块依赖方向（约束）

```
Presentation → API → Orchestration → Agent → DataCollection
                              ↓           ↓
                         Infrastructure ←─┘
```

**禁止反向依赖**：Agent 层不得直接调用 API 路由；数据采集层不得感知 LangGraph 状态。

---

## 3. 端到端数据流

### 3.1 主流程（逐步骤）

```
Step 0  用户在前端输入 GitHub URL，点击「开始分析」
          ↓
Step 1  前端 POST /api/v1/analyze { "repo_url": "https://github.com/owner/repo" }
          ↓ 返回 { "task_id": "uuid", "stream_url": "/api/v1/stream/{task_id}" }
Step 2  前端立即建立 EventSource 连接 GET /api/v1/stream/{task_id}
          ↓
Step 3  后端校验 URL 格式 → 解析 owner/repo → 检查 Redis 缓存
          ├─ 命中缓存 → SSE 推送 cache_hit 事件 → 直接推送完整报告 → 结束
          └─ 未命中 → 创建 LangGraph 任务，进入流水线
          ↓
Step 4  【数据采集节点 fetch_data】
          - octokit.py 拉取：repo 元数据、languages、contributors、commits 活跃度
          - 拉取 README.md 全文
          - 递归获取文件目录树（深度限制 3~5 层）
          - 采样关键源码文件（入口文件、配置文件、核心模块，总量 ≤ 50KB）
          - SSE 推送：event=progress, stage=fetch_data
          ↓
Step 5  【Agent A - 代码审计】
          - 输入：GraphState.repo_snapshot（目录树 + 源码样本 + 依赖文件内容）
          - LLM 流式推理 → SSE 推送：event=agent_log, agent=code_auditor
          - 输出：CodeAuditReport (JSON) 写入 GraphState
          - SSE 推送：event=stage_result, agent=code_auditor
          ↓
Step 6  【Agent B - 产品价值】
          - 输入：README + 活跃度指标 + Star/Fork 数据（不含源码）
          - LLM 流式推理 → SSE 推送：event=agent_log, agent=product_analyst
          - 输出：ProductValueReport (JSON) 写入 GraphState
          - SSE 推送：event=stage_result, agent=product_analyst
          ↓
Step 7  【Agent C - 总分裁判】
          - 输入：CodeAuditReport + ProductValueReport
          - 加权计算评分 → 生成 FinalReport
          - SSE 推送：event=agent_log, agent=judge
          - SSE 推送：event=stage_result, agent=judge
          ↓
Step 8  【finalize 节点】
          - 组装 FinalReport（含基础指标 + 双维度报告 + 总分 + 建议）
          - 写入 Redis 缓存（TTL 可配置，默认 24h）
          - SSE 推送：event=report_complete, data=FinalReport
          - SSE 推送：event=done
          ↓
Step 9  前端收到 report_complete → 渲染报告可视化面板
          收到 done → 关闭 EventSource 连接
```

### 3.2 数据对象流转图

```
GitHub API Raw Data
       │
       ▼
┌─────────────────┐
│  RepoSnapshot   │  owner, repo, stars, forks, languages, readme,
│  (Pydantic)     │  file_tree, source_samples, commit_activity, contributors
└────────┬────────┘
         │
    ┌────▼────┐
    │ Agent A │──► CodeAuditReport
    └────┬────┘         │
         │              │
    ┌────▼────┐         │
    │ Agent B │──► ProductValueReport
    └────┬────┘         │
         │              │
    ┌────▼──────────────▼────┐
    │       Agent C          │──► FinalReport
    └────────────────────────┘
```

### 3.3 异常分支数据流

| 触发条件 | SSE 事件 | 后续动作 |
|----------|----------|----------|
| URL 格式非法 | `error` code=4001 | 终止任务 |
| 私有仓库 / 404 | `error` code=4002 | 终止任务 |
| GitHub API 限流 | `error` code=5001 | 重试 1 次后终止 |
| 单 Agent 超时 | `error` code=5002 | 终止任务，释放资源 |
| LLM 调用失败 | `error` code=5003 | 重试 1 次后终止 |
| 全局任务超时 | `error` code=5004 | 强制 cancel LangGraph run |

---

## 4. 多 Agent 协作设计

### 4.1 LangGraph 状态机定义

```python
# 概念定义（实现参考）
class GraphState(TypedDict):
    task_id: str
    repo_url: str
    repo_snapshot: RepoSnapshot | None
    code_audit_report: CodeAuditReport | None
    product_value_report: ProductValueReport | None
    final_report: FinalReport | None
    current_stage: str          # fetch_data | agent_a | agent_b | agent_c | done
    error: str | None
```

**节点与边：**

```
START → fetch_data → agent_a → agent_b → agent_c → finalize → END
                         ↑         ↑         ↑
                    (条件边：error 时 → error_handler → END)
```

### 4.2 Agent A — 代码审计智能体

#### 角色定义

| 属性 | 值 |
|------|-----|
| ID | `code_auditor` |
| 名称 | 代码审计智能体 |
| 执行顺序 | 第 1 位（流水线起点） |

#### 输入 Schema

```json
{
  "repo_name": "owner/repo",
  "primary_language": "Python",
  "languages": { "Python": 85.2, "Dockerfile": 14.8 },
  "file_tree": ["src/", "src/main.py", "tests/", "requirements.txt", "..."],
  "source_samples": [
    { "path": "src/main.py", "content": "...", "lines": 120 },
    { "path": "requirements.txt", "content": "...", "lines": 15 }
  ],
  "dependency_files": [
    { "path": "requirements.txt", "content": "..." },
    { "path": "package.json", "content": "..." }
  ]
}
```

#### 输出 Schema — `CodeAuditReport`

```json
{
  "agent_id": "code_auditor",
  "overall_code_score": 78,
  "dimensions": {
    "directory_structure": { "score": 82, "summary": "...", "issues": ["..."] },
    "architecture_quality": { "score": 75, "summary": "...", "issues": ["..."] },
    "tech_debt": { "score": 70, "summary": "...", "issues": ["..."] },
    "dependency_risk": { "score": 85, "summary": "...", "issues": ["..."] },
    "code_standards": { "score": 80, "summary": "...", "issues": ["..."] }
  },
  "highlights": ["亮点1", "亮点2"],
  "critical_issues": ["严重问题1"],
  "recommendations": ["建议1", "建议2"]
}
```

#### 工作逻辑

1. 解析文件树，识别项目类型（Web/CLI/Library/Monorepo）
2. 评估目录规范性（src/tests/docs 分离、命名一致性）
3. 分析源码样本的架构模式（分层、模块化、耦合度）
4. 扫描依赖文件，识别过时/高危依赖
5. 检测代码规范信号（lint 配置、类型注解、测试覆盖迹象）
6. 汇总各维度分数，输出结构化 JSON

#### Prompt 模板

```
你是资深代码审计专家 Agent A（代码审计智能体）。你的任务是评估 GitHub 仓库的代码质量。

## 输入数据
- 仓库：{repo_name}
- 主语言：{primary_language}
- 语言占比：{languages}
- 文件目录树：
{file_tree}

- 源码样本：
{source_samples}

- 依赖文件：
{dependency_files}

## 评估维度（每项 0-100 分）
1. **目录规范性**：目录结构是否清晰、是否符合语言生态惯例
2. **架构合理性**：模块划分、分层设计、职责单一性
3. **技术债务**：代码复杂度、重复代码、过时模式
4. **依赖风险**：依赖版本、已知漏洞、依赖数量
5. **代码规范**：命名规范、注释、配置文件（lint/test/ci）

## 输出要求
严格输出 JSON，符合以下 Schema，不要输出任何 JSON 以外的内容：

{
  "agent_id": "code_auditor",
  "overall_code_score": <0-100整数>,
  "dimensions": {
    "directory_structure": { "score": <int>, "summary": "<string>", "issues": ["<string>"] },
    "architecture_quality": { "score": <int>, "summary": "<string>", "issues": ["<string>"] },
    "tech_debt": { "score": <int>, "summary": "<string>", "issues": ["<string>"] },
    "dependency_risk": { "score": <int>, "summary": "<string>", "issues": ["<string>"] },
    "code_standards": { "score": <int>, "summary": "<string>", "issues": ["<string>"] }
  },
  "highlights": ["<string>"],
  "critical_issues": ["<string>"],
  "recommendations": ["<string>"]
}

## 评分标准
- 90-100：优秀，可作为开源标杆
- 70-89：良好，有少量改进空间
- 50-69：一般，存在明显问题
- 0-49：较差，需要重构

请开始分析。
```

---

### 4.3 Agent B — 产品价值智能体

#### 角色定义

| 属性 | 值 |
|------|-----|
| ID | `product_analyst` |
| 名称 | 产品价值智能体 |
| 执行顺序 | 第 2 位（接收 Agent A 完成信号后启动，输入不含 A 的报告） |

> **设计说明**：Agent B 与 Agent A **并行输入源独立**——B 的输入来自 `RepoSnapshot` 的产品相关字段，不依赖 A 的输出。串行执行的原因是需要 A 先完成以控制 LLM 并发与 SSE 推送顺序；后续可改为 A/B 并行再 C 汇总。

#### 输入 Schema

```json
{
  "repo_name": "owner/repo",
  "description": "A awesome project",
  "stars": 1234,
  "forks": 567,
  "open_issues": 23,
  "created_at": "2020-01-01T00:00:00Z",
  "updated_at": "2025-06-15T00:00:00Z",
  "readme_content": "# Project Title\n\n...",
  "commit_activity": {
    "last_30_days": 45,
    "last_90_days": 120,
    "last_commit_date": "2025-06-14"
  },
  "contributors_count": 15,
  "topics": ["machine-learning", "python"]
}
```

#### 输出 Schema — `ProductValueReport`

```json
{
  "agent_id": "product_analyst",
  "overall_product_score": 85,
  "dimensions": {
    "documentation": { "score": 90, "summary": "...", "issues": ["..."] },
    "practicality": { "score": 82, "summary": "...", "issues": ["..."] },
    "open_source_activity": { "score": 88, "summary": "...", "issues": ["..."] },
    "maintainability": { "score": 80, "summary": "...", "issues": ["..."] },
    "popularity": { "score": 85, "summary": "...", "issues": ["..."] }
  },
  "highlights": ["..."],
  "critical_issues": ["..."],
  "recommendations": ["..."]
}
```

#### 工作逻辑

1. 解析 README：是否包含安装、用法、示例、贡献指南、License
2. 评估 Stars/Forks 绝对值与相对值（结合仓库年龄）
3. 分析提交频率与最近更新时间，判断维护活跃度
4. 评估贡献者多样性与社区健康度
5. 判断项目定位清晰度与目标用户匹配度
6. 输出结构化 JSON

#### Prompt 模板

```
你是资深开源产品分析师 Agent B（产品价值智能体）。你的任务是评估 GitHub 仓库的产品价值与开源健康度。

## 输入数据
- 仓库：{repo_name}
- 描述：{description}
- Stars：{stars} | Forks：{forks} | Open Issues：{open_issues}
- 创建时间：{created_at} | 最近更新：{updated_at}
- Topics：{topics}
- 贡献者数量：{contributors_count}
- 提交活跃度：最近30天 {last_30_days} 次，最近90天 {last_90_days} 次，最近提交 {last_commit_date}

## README 全文
{readme_content}

## 评估维度（每项 0-100 分）
1. **文档完整性**：README 是否包含项目介绍、安装、用法、示例、License、Contributing
2. **项目实用性**：解决的问题是否明确、是否有实际应用场景
3. **开源活跃度**：Stars/Forks 增长、Issue/PR 活跃度、社区互动
4. **维护可持续性**：更新频率、贡献者分布、维护者响应
5. **传播度**：Star 数量、Topics 标签、项目定位清晰度

## 输出要求
严格输出 JSON，符合以下 Schema，不要输出任何 JSON 以外的内容：

{
  "agent_id": "product_analyst",
  "overall_product_score": <0-100整数>,
  "dimensions": {
    "documentation": { "score": <int>, "summary": "<string>", "issues": ["<string>"] },
    "practicality": { "score": <int>, "summary": "<string>", "issues": ["<string>"] },
    "open_source_activity": { "score": <int>, "summary": "<string>", "issues": ["<string>"] },
    "maintainability": { "score": <int>, "summary": "<string>", "issues": ["<string>"] },
    "popularity": { "score": <int>, "summary": "<string>", "issues": ["<string>"] }
  },
  "highlights": ["<string>"],
  "critical_issues": ["<string>"],
  "recommendations": ["<string>"]
}

请开始分析。
```

---

### 4.4 Agent C — 总分裁判汇总智能体

#### 角色定义

| 属性 | 值 |
|------|-----|
| ID | `judge` |
| 名称 | 总分裁判汇总智能体 |
| 执行顺序 | 第 3 位（必须等待 A + B 报告） |

#### 输入 Schema

```json
{
  "repo_name": "owner/repo",
  "repo_metrics": {
    "stars": 1234,
    "forks": 567,
    "primary_language": "Python",
    "languages": { "Python": 85.2 },
    "contributors_count": 15,
    "last_updated": "2025-06-15"
  },
  "code_audit_report": { "...": "Agent A 完整输出" },
  "product_value_report": { "...": "Agent B 完整输出" }
}
```

#### 输出 Schema — `FinalReport`

```json
{
  "agent_id": "judge",
  "repo_name": "owner/repo",
  "repo_url": "https://github.com/owner/repo",
  "analyzed_at": "2025-07-01T12:00:00Z",
  "scores": {
    "total_score": 82,
    "code_score": 78,
    "product_score": 85,
    "weights": { "code": 0.5, "product": 0.5 }
  },
  "grade": "B+",
  "summary": "一句话总结",
  "repo_metrics": { "...": "基础指标快照" },
  "code_audit": { "...": "Agent A 报告嵌入" },
  "product_analysis": { "...": "Agent B 报告嵌入" },
  "top_recommendations": [
    { "priority": "high", "category": "code", "action": "..." },
    { "priority": "medium", "category": "product", "action": "..." }
  ],
  "verdict": "综合结论段落"
}
```

#### 评分权重规则

| 维度 | 默认权重 | 说明 |
|------|----------|------|
| 代码质量（Agent A） | 50% | `overall_code_score` |
| 产品价值（Agent B） | 50% | `overall_product_score` |
| **总分** | — | `total_score = code_score * 0.5 + product_score * 0.5` |

等级映射：`A(90-100)` / `B(80-89)` / `C(70-79)` / `D(60-69)` / `F(0-59)`

#### Prompt 模板

```
你是首席评审官 Agent C（总分裁判汇总智能体）。你的任务是基于 Agent A 和 Agent B 的分析报告，给出最终综合评分与体检结论。

## 仓库信息
- 仓库：{repo_name}
- 基础指标：{repo_metrics}

## Agent A 代码审计报告
{code_audit_report}

## Agent B 产品价值报告
{product_value_report}

## 评分规则
- 代码维度分 = Agent A 的 overall_code_score
- 产品维度分 = Agent B 的 overall_product_score
- 总分 = 代码维度分 × 0.5 + 产品维度分 × 0.5（四舍五入取整）
- 等级：A(90-100) / B(80-89) / C(70-79) / D(60-69) / F(0-59)

## 输出要求
严格输出 JSON，符合 FinalReport Schema，不要输出任何 JSON 以外的内容：

{
  "agent_id": "judge",
  "repo_name": "<string>",
  "repo_url": "<string>",
  "analyzed_at": "<ISO8601>",
  "scores": {
    "total_score": <0-100>,
    "code_score": <0-100>,
    "product_score": <0-100>,
    "weights": { "code": 0.5, "product": 0.5 }
  },
  "grade": "<A|B+|B|C+|C|D|F>",
  "summary": "<一句话总结>",
  "repo_metrics": { ... },
  "code_audit": { ... Agent A 报告原样嵌入 ... },
  "product_analysis": { ... Agent B 报告原样嵌入 ... },
  "top_recommendations": [
    { "priority": "high|medium|low", "category": "code|product", "action": "<string>" }
  ],
  "verdict": "<综合结论文段，200字以内>"
}

## 要求
1. top_recommendations 按优先级排序，最多 8 条
2. 合并 A/B 的建议，去重并重新按影响力排序
3. verdict 需客观、具体、可执行

请开始汇总。
```

---

## 5. SSE 流式推送事件设计

### 5.1 连接规范

```
GET /api/v1/stream/{task_id}
Accept: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

### 5.2 事件通用格式

每条 SSE 消息遵循：

```
event: {event_type}
id: {monotonic_sequence_id}
data: {JSON_string}

```

### 5.3 事件类型定义

#### `connected` — 连接建立

```json
{
  "event": "connected",
  "task_id": "uuid",
  "timestamp": "2025-07-01T12:00:00Z",
  "message": "SSE 连接已建立"
}
```

#### `progress` — 阶段进度

```json
{
  "event": "progress",
  "task_id": "uuid",
  "timestamp": "2025-07-01T12:00:01Z",
  "stage": "fetch_data | agent_a | agent_b | agent_c | finalize",
  "status": "started | in_progress | completed",
  "message": "正在拉取 GitHub 仓库元数据...",
  "progress_percent": 10
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| stage | string | ✓ | 当前流水线阶段 |
| status | string | ✓ | 阶段状态 |
| message | string | ✓ | 人类可读描述 |
| progress_percent | int | ✓ | 整体进度 0-100 |

#### `agent_log` — Agent 思考日志（流式）

```json
{
  "event": "agent_log",
  "task_id": "uuid",
  "timestamp": "2025-07-01T12:00:05Z",
  "agent": "code_auditor | product_analyst | judge",
  "log_type": "thinking | action | observation",
  "content": "正在分析目录结构，发现 src/ 与 tests/ 分离良好...",
  "chunk_index": 3
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agent | string | ✓ | Agent 标识 |
| log_type | string | ✓ | 日志类型 |
| content | string | ✓ | 日志片段（LLM 流式 token 或摘要） |
| chunk_index | int | ✓ | 递增序号，用于前端排序 |

#### `stage_result` — 阶段结论

```json
{
  "event": "stage_result",
  "task_id": "uuid",
  "timestamp": "2025-07-01T12:01:00Z",
  "agent": "code_auditor | product_analyst | judge",
  "result": { "...": "该 Agent 的完整 JSON 输出" }
}
```

#### `report_complete` — 最终报告

```json
{
  "event": "report_complete",
  "task_id": "uuid",
  "timestamp": "2025-07-01T12:03:00Z",
  "report": { "...": "FinalReport 完整 JSON" }
}
```

#### `cache_hit` — 缓存命中

```json
{
  "event": "cache_hit",
  "task_id": "uuid",
  "timestamp": "2025-07-01T12:00:00Z",
  "cached_at": "2025-06-30T10:00:00Z",
  "message": "该仓库已有分析结果，直接返回"
}
```

#### `error` — 错误

```json
{
  "event": "error",
  "task_id": "uuid",
  "timestamp": "2025-07-01T12:00:02Z",
  "code": 4001,
  "stage": "fetch_data",
  "message": "GitHub URL 格式不正确",
  "recoverable": false
}
```

| 错误码 | 含义 |
|--------|------|
| 4001 | URL 格式非法 |
| 4002 | 仓库不存在或为私有 |
| 4003 | 重复任务 / task_id 无效 |
| 4290 | 请求频率超限 |
| 5001 | GitHub API 错误 |
| 5002 | Agent 执行超时 |
| 5003 | LLM 调用失败 |
| 5004 | 全局任务超时 |

#### `done` — 流结束

```json
{
  "event": "done",
  "task_id": "uuid",
  "timestamp": "2025-07-01T12:03:01Z",
  "message": "分析流程结束"
}
```

### 5.4 事件推送时序

```
connected → progress(fetch_data) → progress(agent_a) → agent_log* → stage_result(A)
         → progress(agent_b) → agent_log* → stage_result(B)
         → progress(agent_c) → agent_log* → stage_result(C)
         → progress(finalize) → report_complete → done
```

---

## 6. 后端 API 接口清单

### 6.1 接口总览

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | `/api/v1/analyze` | 提交分析任务 |
| GET | `/api/v1/stream/{task_id}` | SSE 流式推送 |
| GET | `/api/v1/report/{task_id}` | 获取已完成报告（轮询备选） |
| GET | `/api/v1/report/cache/{owner}/{repo}` | 按仓库名查缓存报告 |
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/health/ready` | 就绪检查（Redis/LLM） |

### 6.2 POST `/api/v1/analyze`

**用途**：创建分析任务，返回 task_id 与 SSE 地址。

**请求体：**

```json
{
  "repo_url": "https://github.com/owner/repo"
}
```

| 字段 | 类型 | 必填 | 校验规则 |
|------|------|------|----------|
| repo_url | string | ✓ | 匹配 `https://github.com/{owner}/{repo}` |

**响应 202：**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "stream_url": "/api/v1/stream/550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2025-07-01T12:00:00Z"
}
```

**错误响应：**

| 状态码 | 场景 |
|--------|------|
| 400 | URL 格式错误 |
| 429 | 触发限流 |
| 503 | 服务不可用 |

### 6.3 GET `/api/v1/stream/{task_id}`

**用途**：建立 SSE 连接，实时接收分析事件。

**路径参数：** `task_id` (UUID)

**响应：** `text/event-stream` 事件流（见第 5 节）

**错误：** task_id 不存在返回 404 JSON（非 SSE）

### 6.4 GET `/api/v1/report/{task_id}`

**用途**：轮询备选方案，获取已完成任务的 FinalReport。

**响应 200：**

```json
{
  "task_id": "uuid",
  "status": "completed | running | failed",
  "report": { "...FinalReport..." }
}
```

### 6.5 GET `/api/v1/report/cache/{owner}/{repo}`

**用途**：直接查询 Redis 缓存，不触发新分析。

**响应 200：** FinalReport JSON  
**响应 404：** 无缓存

### 6.6 GET `/api/v1/health`

```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2025-07-01T12:00:00Z"
}
```

### 6.7 GET `/api/v1/health/ready`

```json
{
  "status": "ready",
  "checks": {
    "redis": "ok",
    "llm": "ok",
    "github": "ok"
  }
}
```

---

## 7. 项目目录结构

```
RepoAgent/
├── README.md                          # 本文档
├── run.md                             # 本地运行指南（含 Skill 用法）
├── LICENSE
├── .gitignore
├── docker-compose.yml                 # 一键部署：backend + frontend + redis
├── .env.example                       # 环境变量模板
│
├── .cursor/skills/                    # Cursor Agent Skill
│   ├── repoagent-dev/                 # 开发向：架构规范、扩展 Agent、排错
│   │   ├── SKILL.md
│   │   ├── reference.md
│   │   └── troubleshooting.md
│   └── repo-audit/                    # 使用向：CLI 调用 API 分析 GitHub 仓库
│       ├── SKILL.md
│       ├── examples.md
│       └── scripts/analyze_repo.py
│
├── frontend/                          # Vue3 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   ├── Dockerfile
│   ├── public/
│   │   └── favicon.ico
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── vite-env.d.ts
│       ├── assets/
│       │   └── styles/
│       │       └── main.css             # Tailwind 入口
│       ├── components/
│       │   ├── UrlInput.vue             # GitHub URL 输入框 + 开始按钮
│       │   ├── StreamLogPanel.vue       # SSE 实时日志面板
│       │   ├── ReportDashboard.vue      # 最终报告可视化
│       │   ├── ScoreGauge.vue           # 0-100 评分仪表盘
│       │   ├── DimensionCard.vue          # 维度分数卡片
│       │   └── RecommendationList.vue   # 优化建议清单
│       ├── composables/
│       │   ├── useSSE.ts                # EventSource 封装
│       │   └── useAnalyze.ts            # 分析任务状态管理
│       ├── services/
│       │   └── api.ts                   # API 请求封装
│       ├── types/
│       │   ├── sse.ts                   # SSE 事件类型
│       │   └── report.ts                # 报告 Schema 类型
│       └── views/
│           └── HomeView.vue             # 主页面
│
├── backend/                           # FastAPI 后端
│   ├── pyproject.toml                 # 依赖管理（Poetry/pip）
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI 入口
│   │   ├── config.py                  # 配置（Pydantic Settings）
│   │   ├── dependencies.py            # 依赖注入
│   │   │
│   │   ├── routers/                   # 【接口层】
│   │   │   ├── __init__.py
│   │   │   ├── analyze.py             # POST /analyze
│   │   │   ├── stream.py              # GET /stream SSE
│   │   │   ├── report.py              # GET /report
│   │   │   └── health.py              # 健康检查
│   │   │
│   │   ├── schemas/                   # 【Pydantic 模型】
│   │   │   ├── __init__.py
│   │   │   ├── request.py             # 请求体
│   │   │   ├── response.py            # 响应体
│   │   │   ├── repo_snapshot.py       # 仓库快照
│   │   │   ├── code_audit.py          # Agent A 输出
│   │   │   ├── product_value.py       # Agent B 输出
│   │   │   ├── final_report.py        # Agent C 输出
│   │   │   └── sse_events.py          # SSE 事件 Schema
│   │   │
│   │   ├── services/                  # 【数据采集层】
│   │   │   ├── __init__.py
│   │   │   ├── github_service.py      # octokit.py 封装
│   │   │   ├── repo_fetcher.py        # 仓库数据聚合
│   │   │   └── url_validator.py       # URL 校验
│   │   │
│   │   ├── graph/                     # 【编排层 LangGraph】
│   │   │   ├── __init__.py
│   │   │   ├── state.py               # GraphState 定义
│   │   │   ├── workflow.py            # 状态机图构建
│   │   │   ├── nodes/
│   │   │   │   ├── fetch_data.py      # 数据采集节点
│   │   │   │   ├── finalize.py        # 收尾节点
│   │   │   │   └── error_handler.py   # 异常处理节点
│   │   │   └── event_emitter.py       # SSE 事件广播
│   │   │
│   │   ├── agents/                    # 【Agent 层】
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # Agent 基类（输入输出校验）
│   │   │   ├── registry.py            # Agent 注册表（扩展点）
│   │   │   ├── code_auditor.py        # Agent A
│   │   │   ├── product_analyst.py     # Agent B
│   │   │   ├── judge.py               # Agent C
│   │   │   └── prompts/
│   │   │       ├── code_auditor.txt
│   │   │       ├── product_analyst.txt
│   │   │       └── judge.txt
│   │   │
│   │   ├── llm/                       # 【LLM 抽象层】
│   │   │   ├── __init__.py
│   │   │   ├── adapter.py             # 通用 LLM 接口
│   │   │   ├── providers/
│   │   │   │   ├── deepseek.py
│   │   │   │   └── doubao.py
│   │   │   └── json_parser.py         # LLM 输出 JSON 解析/修复
│   │   │
│   │   ├── cache/                     # 【缓存层】
│   │   │   ├── __init__.py
│   │   │   └── redis_client.py
│   │   │
│   │   ├── middleware/                # 中间件
│   │   │   ├── rate_limit.py
│   │   │   └── timeout.py
│   │   │
│   │   └── utils/
│   │       ├── logger.py
│   │       └── exceptions.py          # 自定义异常 + 错误码
│   │
│   └── tests/
│       ├── test_url_validator.py
│       ├── test_github_service.py
│       ├── test_agents.py
│       └── test_workflow.py
│
└── docs/                              # 补充文档（可选）
    ├── api.md
    └── agent-design.md
```

---

## 8. 技术选型说明

### 8.1 前端

| 技术 | 版本建议 | 选型理由 |
|------|----------|----------|
| **Vue 3** | ^3.4 | Composition API 适合 SSE 状态管理 |
| **TypeScript** | ^5.4 | 与后端 Pydantic Schema 对齐类型安全 |
| **Vite** | ^5.x | 快速 HMR，开发体验好 |
| **TailwindCSS** | ^3.4 | 快速构建报告可视化 UI |
| **EventSource** | 原生 API | SSE 客户端，无需额外库 |

### 8.2 后端

| 技术 | 版本建议 | 选型理由 |
|------|----------|----------|
| **FastAPI** | ^0.111 | 原生 async + SSE StreamingResponse |
| **Pydantic v2** | ^2.7 | 请求/响应/Agent I/O 统一校验 |
| **LangGraph** | ^0.2 | 状态机编排 Agent 串行流转，易扩展 |
| **octokit.py** | latest | GitHub REST API 官方 Python SDK |
| **redis-py** | ^5.x | 异步 Redis 客户端（aioredis 已合并） |
| **httpx** | ^0.27 | 异步 HTTP（LLM API 调用） |

### 8.3 LLM 抽象层设计

```
LLMAdapter (抽象基类)
├── chat(messages, stream=True) → AsyncIterator[str]
├── chat_json(messages, schema) → dict
└── providers/
    ├── DeepSeekProvider  (API_KEY, BASE_URL 环境变量)
    └── DoubaoProvider    (API_KEY, BASE_URL 环境变量)
```

**环境变量：**

```env
LLM_PROVIDER=deepseek          # deepseek | doubao
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_TIMEOUT=120
```

### 8.4 缓存策略

| Key 模式 | 内容 | TTL |
|----------|------|-----|
| `repoagent:report:{owner}/{repo}` | FinalReport JSON | 24h（可配置） |
| `repoagent:task:{task_id}` | 任务状态 + 中间结果 | 1h |
| `repoagent:ratelimit:{ip}` | 限流计数 | 1min |

### 8.5 部署

```yaml
# docker-compose.yml 服务组成
services:
  frontend:   # Nginx 托管 Vue 静态资源
  backend:    # Uvicorn + FastAPI
  redis:      # 缓存
```

---

## 9. 约束规则与扩展规范

### 9.1 强制约束

1. **超时控制**
   - 全局任务超时：默认 5 分钟（`TASK_TIMEOUT=300`）
   - 单 Agent 超时：默认 2 分钟（`AGENT_TIMEOUT=120`）
   - GitHub API 单次请求：30 秒

2. **GitHub Token 隔离**
   ```env
   GITHUB_TOKEN=ghp_xxx        # 可选，提高 API 限额
   GITHUB_API_BASE=https://api.github.com
   ```

3. **结构化 I/O**
   - 所有 Agent 输出必须经 Pydantic Model 校验
   - LLM 返回非 JSON 时，`json_parser.py` 尝试提取修复，失败则重试 1 次

4. **低耦合扩展**
   - 新增 Agent D：在 `agents/` 添加实现 → `registry.py` 注册 → `workflow.py` 添加节点和边
   - 不得修改已有 Agent 的输入输出 Schema（只增不改）

5. **限流**
   - 单 IP：5 次/分钟
   - 单仓库：缓存命中时不消耗 LLM 配额

### 9.2 Agent 扩展接口规范

```python
# agents/base.py 概念
class BaseAgent(ABC):
    agent_id: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]

    async def run(self, input_data: BaseModel, emitter: EventEmitter) -> BaseModel:
        # 1. 校验输入
        # 2. 渲染 Prompt
        # 3. 流式调用 LLM，emit agent_log
        # 4. 解析 JSON，校验输出
        # 5. 返回结构化结果
```

---

## 10. 风险点与优化方案

| 风险 | 影响 | 概率 | 优化方案 |
|------|------|------|----------|
| GitHub API 限流（未认证 60次/h） | 数据采集失败 | 高 | 配置 GITHUB_TOKEN；Redis 缓存；请求合并 |
| LLM 输出非标准 JSON | Agent 链路中断 | 中 | json_parser 容错提取；Prompt 强调 JSON-only；失败重试 |
| 大型仓库文件过多 | 超时/OOM | 中 | 目录深度限制 5 层；源码采样 ≤50KB；跳过大文件/二进制 |
| SSE 连接断开 | 用户看不到后续日志 | 中 | 前端自动重连 + Last-Event-ID；report 轮询兜底 |
| LLM 响应慢 | 用户体验差 | 高 | 流式推送 agent_log；progress heartbeat 每 5s |
| 私有仓库 | 分析失败 | 低 | 前置检测 `repo.private`，友好错误提示 |
| 并发分析过多 | 资源耗尽 | 中 | 任务队列 + 最大并发数限制（默认 3） |
| Prompt 注入（恶意 README） | LLM 误导 | 低 | README 截断 8000 字符；system prompt 隔离 |

### 10.1 后续优化路线

- **Phase 2**：Agent A/B 并行执行，C 汇总（LangGraph 并行分支）
- **Phase 3**：支持 GitLab / Gitee
- **Phase 4**：历史分析对比、趋势报告
- **Phase 5**：Agent D（安全审计）、Agent E（License 合规）

---

## 11. 48 小时开发排期

### 总览

| 阶段 | 时间 | 目标 |
|------|------|------|
| Phase 1 | 0-8h | 项目脚手架 + 数据采集层 |
| Phase 2 | 8-20h | LLM 层 + 三 Agent + LangGraph |
| Phase 3 | 20-32h | SSE 推送 + API 完整链路 |
| Phase 4 | 32-42h | 前端 UI + 联调 |
| Phase 5 | 42-48h | Docker 部署 + 测试 + 文档 |

---

### Phase 1：基础脚手架与数据采集（0-8h）

| 小时 | 任务 | 交付物 |
|------|------|--------|
| 0-2h | 初始化前后端项目结构、依赖安装、配置管理 | 目录结构、`.env.example`、`config.py` |
| 2-4h | `url_validator.py` + `github_service.py`（octokit.py） | 可拉取 repo 元数据、README、languages |
| 4-6h | `repo_fetcher.py` 文件树 + 源码采样 | `RepoSnapshot` Pydantic Model |
| 6-8h | Redis 客户端 + 基础缓存逻辑 | 缓存读写可用 |

**里程碑 M1**：给定 GitHub URL，后端能输出完整 `RepoSnapshot` JSON。

---

### Phase 2：Agent 与 LangGraph 编排（8-20h）

| 小时 | 任务 | 交付物 |
|------|------|--------|
| 8-10h | `llm/adapter.py` 抽象层 + DeepSeek Provider | LLM 流式/JSON 调用可用 |
| 10-12h | Agent 基类 + Agent A 实现 + Prompt | `CodeAuditReport` 输出 |
| 12-14h | Agent B 实现 + Prompt | `ProductValueReport` 输出 |
| 14-16h | Agent C 实现 + Prompt | `FinalReport` 输出 |
| 16-18h | LangGraph `GraphState` + `workflow.py` 串行图 | 三 Agent 端到端跑通 |
| 18-20h | 超时控制 + 异常处理 + json_parser | 流水线健壮性 |

**里程碑 M2**：命令行触发 LangGraph，输入 URL 输出 FinalReport JSON。

---

### Phase 3：SSE 与 API 层（20-32h）

| 小时 | 任务 | 交付物 |
|------|------|--------|
| 20-22h | `event_emitter.py` SSE 广播机制 | 事件可推送至订阅者 |
| 22-24h | `POST /analyze` + 任务生命周期管理 | 任务创建与状态追踪 |
| 24-26h | `GET /stream/{task_id}` SSE 端点 | 完整事件流推送 |
| 26-28h | LangGraph 节点集成 EventEmitter | agent_log / stage_result 实时推送 |
| 28-30h | 限流中间件 + 统一异常处理 | 错误码规范 |
| 30-32h | `GET /report` + 缓存命中流程 | API 全链路完成 |

**里程碑 M3**：Postman/curl 可完成分析并收到 SSE 事件流。

---

### Phase 4：前端开发与联调（32-42h）

| 小时 | 任务 | 交付物 |
|------|------|--------|
| 32-34h | Vue3 项目初始化 + TailwindCSS + 类型定义 | 前端脚手架 |
| 34-36h | `useSSE.ts` + `UrlInput.vue` + `StreamLogPanel.vue` | 输入 + 实时日志 |
| 36-38h | `ReportDashboard.vue` + 评分/维度/建议组件 | 报告可视化 |
| 38-40h | 前后端联调 | 完整用户流程跑通 |
| 40-42h | UI 打磨 + 错误态 + 加载态 | 用户体验完善 |

**里程碑 M4**：浏览器输入 URL → 实时日志 → 最终报告可视化。

---

### Phase 5：部署与收尾（42-48h）

| 小时 | 任务 | 交付物 |
|------|------|--------|
| 42-44h | Dockerfile + docker-compose.yml | 一键启动 |
| 44-46h | 核心单元测试 + 集成测试 | tests/ 基础覆盖 |
| 46-48h | README 完善 + 演示准备 + Bug 修复 | 可交付版本 |

**里程碑 M5**：`docker-compose up` 一键启动，完整 Demo 可演示。

---

## 12. Cursor Skill 集成

项目在 `.cursor/skills/` 内置两个 Cursor Agent Skill，clone 后在 Cursor 中打开仓库即可使用，便于 **AI 辅助开发** 与 **对话式仓库体检**。

> 本地启动与环境配置见 [run.md](run.md)；Skill 详细用法见 [run.md §10](run.md#10-cursor-skillai-助手集成)。

### 12.1 Skill 一览

| Skill | 目录 | 触发场景 |
|-------|------|----------|
| **repoagent-dev** | `.cursor/skills/repoagent-dev/` | 修改 RepoAgent 代码、新增 Agent/API/SSE、排查 SSL/Redis/JSON 等问题 |
| **repo-audit** | `.cursor/skills/repo-audit/` | 分析/评估/对比 GitHub 公开仓库，获取评分报告与建议 |

### 12.2 repo-audit — 对话式仓库体检

**前提：** 后端已运行（`python scripts/run_backend.py` 或 Docker Compose）。

在 Cursor 中直接说：

```
分析一下 https://github.com/tiangolo/fastapi
对比 react 和 vue 的开源健康度
```

或终端调用：

```bash
python .cursor/skills/repo-audit/scripts/analyze_repo.py -v https://github.com/owner/repo
python .cursor/skills/repo-audit/scripts/analyze_repo.py --cache owner repo
python .cursor/skills/repo-audit/scripts/analyze_repo.py --json owner repo
```

输出包含：综合评分（0–100）、代码/产品双维度分数、等级、摘要、Top 建议。完整 JSON 结构同 `FinalReport` Schema（见第 4.4 节）。

### 12.3 repoagent-dev — 开发规范助手

面向贡献者与维护者，Skill 内固化：

- 六层架构与单向依赖约束
- 新增 Agent 的完整 checklist（Schema → Prompt → json_parser → workflow）
- SSE 事件类型与 API 端点索引
- 错误码对照与 `logs/app.log` 排查路径

示例提问：「如何添加 Agent D 安全审计？」「CodeAuditReport ValidationError 怎么修？」

### 12.4 Web UI vs Skill

| 入口 | 优势 |
|------|------|
| 前端 http://localhost:5173 | 可视化报告、评分仪表盘、实时 SSE 日志 |
| repo-audit Skill | 无需打开浏览器，在 IDE 对话中快速分析、多仓库对比 |

---

## 附录 A：环境变量清单

```env
# GitHub
GITHUB_TOKEN=
GITHUB_API_BASE=https://api.github.com

# LLM
LLM_PROVIDER=deepseek
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_TIMEOUT=120

# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=86400

# Task
TASK_TIMEOUT=300
AGENT_TIMEOUT=120
MAX_CONCURRENT_TASKS=3

# Rate Limit
RATE_LIMIT_PER_MINUTE=5

# App
APP_ENV=development
CORS_ORIGINS=http://localhost:5173
```

## 附录 B：关键 Pydantic Model 关系

```
AnalyzeRequest
RepoSnapshot ──► CodeAuditReport ──┐
                 ProductValueReport ──┼──► FinalReport
                                       │
AnalyzeResponse ◄── task_id          │
SSEEvent (union) ◄── 各阶段事件        │
```

---

> **RepoAgent** — 让每一次开源探索，都有一份专业的体检报告。
