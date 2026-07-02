# RepoAgent 本地运行指南

本文档说明从 GitHub 克隆 RepoAgent 后，如何在本地启动并使用。

---

## 目录

- [1. 项目简介](#1-项目简介)
- [2. 环境要求](#2-环境要求)
- [3. 快速开始（Docker，推荐）](#3-快速开始docker推荐)
- [4. 本地开发模式（前后端分离）](#4-本地开发模式前后端分离)
- [5. 环境变量说明](#5-环境变量说明)
- [6. 验证是否启动成功](#6-验证是否启动成功)
- [7. 如何使用](#7-如何使用)
- [8. 常见问题](#8-常见问题)
- [9. 端口与服务一览](#9-端口与服务一览)
- [10. Cursor Skill（AI 助手集成）](#10-cursor-skillai-助手集成)

---

## 1. 项目简介

RepoAgent 是一个 **GitHub 仓库智能体检平台**：

- 输入公开仓库 URL（如 `https://github.com/tiangolo/fastapi`）
- 后端通过 GitHub API 采集数据，三个 AI Agent 串行分析
- 前端通过 SSE 实时展示分析进度，最终输出评分报告与优化建议

本地运行需要三个组件：**后端（FastAPI）**、**前端（Vue3）**、**Redis（缓存）**，以及一个可用的 **大模型 API Key**。

---

## 2. 环境要求

| 组件 | 版本要求 | 用途 |
|------|----------|------|
| **Python** | 3.11+ | 后端服务 |
| **Node.js** | 18+ | 前端开发服务器 |
| **Redis** | 7.x | 报告缓存、任务状态 |
| **Git** | 任意较新版本 | 克隆代码 |

可选：

| 组件 | 说明 |
|------|------|
| **Docker + Docker Compose** | 一键启动全部服务，无需手动装 Redis |
| **GitHub Token** | 提高 GitHub API 限额（未配置时 60 次/小时） |
| **大模型 API Key** | 必填，支持 DeepSeek、豆包等 OpenAI 兼容接口 |

---

## 3. 快速开始（Docker，推荐）

适合想最快跑起来、不想手动配置 Python/Node 环境的用户。

### 3.1 克隆项目

```bash
git clone https://github.com/xzx-123-xzx/RepoAgent.git
cd RepoAgent
```

### 3.2 配置环境变量

```bash
# Linux / macOS
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

编辑项目根目录的 `.env`，**至少填写 LLM 相关三项**：

```env
MODEL_API_KEY=sk-你的密钥
MODEL_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
```

建议同时配置 GitHub Token（可选但推荐）：

```env
GITHUB_TOKEN=ghp_你的token
```

### 3.3 一键启动

```bash
docker compose up -d --build
```

### 3.4 访问

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 前端页面 |
| http://localhost:8000/api/v1/health | 后端健康检查 |
| http://localhost:8000/docs | FastAPI 自动文档 |

### 3.5 停止服务

```bash
docker compose down
```

---

## 4. 本地开发模式（前后端分离）

适合需要改代码、调试的开发场景。需要 **3 个终端窗口**（Redis、后端、前端）。

### 4.1 克隆并进入项目

```bash
git clone https://github.com/xzx-123-xzx/RepoAgent.git
cd RepoAgent
```

### 4.2 配置 `.env`

```bash
cp .env.example .env   # Windows: Copy-Item .env.example .env
```

编辑 `.env`，参考 [第 5 节](#5-环境变量说明) 填写必填项。

> **注意**：`.env` 必须放在**项目根目录**（与 `common/`、`backend/` 同级），后端启动时会自动加载。

### 4.3 启动 Redis

**方式 A：Docker 只跑 Redis（推荐）**

```bash
docker run -d --name repoagent-redis -p 6379:6379 redis:7-alpine
```

**方式 B：本机已安装 Redis**

确保 Redis 运行在 `localhost:6379`（与 `.env` 中 `REDIS_HOST` / `REDIS_PORT` 一致）。

### 4.4 启动后端

**终端 1 — 创建虚拟环境并安装依赖：**

```bash
# 进入项目根目录 RepoAgent/
python -m venv .venv

# 激活虚拟环境
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.\.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

pip install -r backend/requirements.txt
```

**启动后端（任选一种）：**

```bash
# 方式 1：使用项目脚本（推荐，已自动设置 PYTHONPATH）
python scripts/run_backend.py

# 方式 2：手动启动
# Windows PowerShell:
$env:PYTHONPATH = (Get-Location).Path
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Linux / macOS:
export PYTHONPATH=$(pwd)
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

看到以下日志表示后端启动成功：

```
RepoAgent backend started
Uvicorn running on http://127.0.0.1:8000
```

> **重要**：后端依赖项目根目录下的 `common/` 模块，必须通过 `PYTHONPATH` 指向项目根目录，或使用 `scripts/run_backend.py` 启动。

### 4.5 启动前端

**终端 2：**

```bash
cd frontend
npm install
npm run dev
```

看到类似输出：

```
  VITE v5.x  ready in xxx ms
  ➜  Local:   http://localhost:5173/
```

前端开发服务器已将 `/api` 代理到 `http://localhost:8000`，无需额外配置。

### 4.6 打开浏览器

访问 **http://localhost:5173** 即可使用。

---

## 5. 环境变量说明

所有变量均在项目根目录 `.env` 中配置。可从 `.env.example` 复制。

### 5.1 必填

| 变量 | 示例 | 说明 |
|------|------|------|
| `MODEL_API_KEY` | `sk-xxx` | 大模型 API 密钥 |
| `MODEL_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI 兼容接口地址 |
| `MODEL_NAME` | `deepseek-chat` | 模型名称 |

**DeepSeek 示例：**

```env
MODEL_API_KEY=sk-xxxxxxxx
MODEL_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
```

**豆包（火山引擎）示例：**

```env
MODEL_API_KEY=你的方舟APIKey
MODEL_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
MODEL_NAME=ep-xxxxxxxx-xxxxx
```

### 5.2 推荐配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GITHUB_TOKEN` | （空） | GitHub Personal Access Token，提高 API 限额 |
| `HTTP_SSL_VERIFY` | `true` | Windows/企业网络 SSL 报错时可设为 `false`（仅开发环境） |

### 5.3 Redis

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `REDIS_HOST` | `localhost` | Redis 地址 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `REDIS_PASSWORD` | （空） | Redis 密码 |
| `REDIS_DB` | `0` | 数据库编号 |
| `REDIS_EXPIRE` | `86400` | 报告缓存 TTL（秒，默认 24 小时） |

### 5.4 其他（一般保持默认即可）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GITHUB_API_BASE` | `https://api.github.com` | GitHub API 地址 |
| `TASK_TIMEOUT` | `300` | 全局任务超时（秒） |
| `AGENT_TIMEOUT` | `120` | 单 Agent 超时（秒） |
| `MAX_CONCURRENT_TASKS` | `3` | 最大并发分析任务数 |
| `RATE_LIMIT_PER_MINUTE` | `5` | 单 IP 每分钟请求上限 |
| `CORS_ORIGINS` | `http://localhost:5173` | 允许跨域的前端地址 |
| `APP_ENV` | `development` | 运行环境 |

---

## 6. 验证是否启动成功

### 6.1 后端存活检查

浏览器或 curl 访问：

```bash
curl http://localhost:8000/api/v1/health
```

期望返回：

```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "..."
}
```

### 6.2 依赖就绪检查

```bash
curl http://localhost:8000/api/v1/health/ready
```

期望返回（各项均为 ok 时最理想）：

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

| checks 字段 | 含义 | 处理 |
|-------------|------|------|
| `redis: fail` | Redis 未启动或连接失败 | 检查 Redis 是否运行、端口是否正确 |
| `llm: missing_key` | 未配置 `MODEL_API_KEY` | 编辑 `.env` 填入密钥后重启后端 |
| `github: no_token` | 未配置 GitHub Token | 不影响基本功能，但 API 限额较低 |

### 6.3 前端检查

打开 http://localhost:5173 ，页面正常显示输入框即表示前端 OK。

### 6.4 日志文件

分析过程中的 SSE 事件会同步写入：

```
logs/app.log
```

可用于排查分析过程中的问题。

---

## 7. 如何使用

### 7.1 输入仓库 URL

在首页输入框填入 **GitHub 公开仓库地址**，格式：

```
https://github.com/{owner}/{repo}
```

**正确示例：**

- `https://github.com/tiangolo/fastapi`
- `https://github.com/vuejs/core`

**错误示例（不支持）：**

- `https://github.com/tiangolo` — 这是用户主页，不是仓库
- `https://gitee.com/owner/repo` — 暂不支持 Gitee
- 私有仓库 — 暂不支持

### 7.2 开始分析

1. 点击「开始分析」
2. 左侧/上方实时日志面板会显示 SSE 推送的进度
3. 分析完成后展示综合评分、维度详情和优化建议

一次完整分析通常需要 **1~3 分钟**（取决于仓库大小和 LLM 响应速度）。

### 7.3 分析流程概览

```
输入 URL → 采集 GitHub 数据 → Agent A 代码审计
         → Agent B 产品价值 → Agent C 综合评分 → 输出报告
```

---

## 8. 常见问题

### Q1：`SSL: CERTIFICATE_VERIFY_FAILED`（GitHub API 调用失败）

常见于 Windows、Conda 或企业代理环境。

**解决：** 在 `.env` 中设置：

```env
HTTP_SSL_VERIFY=false
```

重启后端。此选项**仅建议在本地开发使用**。

---

### Q2：`Redis ping failed` / 后端启动后分析报错

**原因：** Redis 未运行或地址/端口配置错误。

**解决：**

```bash
# 快速启动 Redis
docker run -d --name repoagent-redis -p 6379:6379 redis:7-alpine

# 确认 .env 中
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

### Q3：`GitHub URL 格式不正确`

**原因：** 输入的不是仓库 URL。

**解决：** 使用 `https://github.com/owner/repo` 格式，必须包含 **owner 和 repo 两段**。

---

### Q4：`LLM 返回内容无法解析为 JSON` / Agent 校验失败

**原因：** 大模型输出格式不符合预期。

**解决：**

1. 确认 `MODEL_API_KEY`、`MODEL_BASE_URL`、`MODEL_NAME` 配置正确
2. 换用支持 JSON 输出的模型（如 `deepseek-chat`）
3. 查看 `logs/app.log` 中的 Agent 原始输出

---

### Q5：`ModuleNotFoundError: No module named 'common'`

**原因：** 未设置 `PYTHONPATH` 指向项目根目录。

**解决：** 使用 `python scripts/run_backend.py` 启动，或手动设置：

```powershell
# Windows PowerShell（在项目根目录执行）
$env:PYTHONPATH = (Get-Location).Path
```

```bash
# Linux / macOS（在项目根目录执行）
export PYTHONPATH=$(pwd)
```

---

### Q6：GitHub API 限流（403 / rate limit）

**原因：** 未配置 Token 时，GitHub 限制 60 次/小时。

**解决：** 在 GitHub → Settings → Developer settings → Personal access tokens 创建 Token，写入 `.env`：

```env
GITHUB_TOKEN=ghp_xxxxxxxx
```

---

### Q7：前端能打开，但点击分析无响应

**排查步骤：**

1. 确认后端在 `8000` 端口运行
2. 浏览器 F12 → Network，看 `/api/v1/analyze` 是否返回 202
3. 本地开发模式下，前端通过 Vite 代理访问后端，确保两个服务都在运行

---

### Q8：`git clone` 时 SSH 连接失败（port 22 refused）

**解决：** 改用 HTTPS 克隆：

```bash
git clone https://github.com/xzx-123-xzx/RepoAgent.git
```

或在 `~/.ssh/config` 中配置 GitHub 走 443 端口（详见 GitHub 官方文档）。

---

## 9. 端口与服务一览

| 服务 | 端口 | 本地开发 | Docker Compose |
|------|------|----------|----------------|
| 前端 | 5173 | Vite dev server | Nginx → 5173 |
| 后端 | 8000 | Uvicorn | 8000 |
| Redis | 6379 | 需自行启动 | 内置 |

---

## 10. Cursor Skill（AI 助手集成）

项目在 `.cursor/skills/` 下内置两个 Cursor Agent Skill，clone 后在 Cursor 中打开本项目即可使用（无需额外安装）。

### 10.1 两个 Skill 的分工

| Skill | 路径 | 适用场景 |
|-------|------|----------|
| **repoagent-dev** | `.cursor/skills/repoagent-dev/` | 改代码、加 Agent、修 bug、架构/SSE/JSON 解析问题 |
| **repo-audit** | `.cursor/skills/repo-audit/` | 在对话里分析/评估/对比 GitHub 仓库 |

### 10.2 如何使用

**自动触发：** 在 Cursor 对话中直接提问，Agent 会根据 Skill 描述自动匹配。

**手动引用：** 输入 `@repoagent-dev` 或 `@repo-audit`，或说「按 repo-audit skill 分析…」。

### 10.3 repo-audit — 仓库体检（需后端运行）

后端启动后，可在 Cursor 中说：

> 分析一下 https://github.com/tiangolo/fastapi 这个仓库

Agent 会调用脚本并返回结构化报告。也可在终端手动运行：

```bash
# 完整分析（进度输出到 stderr）
python .cursor/skills/repo-audit/scripts/analyze_repo.py -v https://github.com/tiangolo/fastapi

# 只查 Redis 缓存（秒出，不消耗 LLM）
python .cursor/skills/repo-audit/scripts/analyze_repo.py --cache tiangolo fastapi

# 输出原始 FinalReport JSON
python .cursor/skills/repo-audit/scripts/analyze_repo.py --json vuejs core

# 指定远程 API 地址
python .cursor/skills/repo-audit/scripts/analyze_repo.py --base-url http://localhost:8000 owner/repo
```

| 参数 | 说明 |
|------|------|
| `--cache` | 仅读取缓存，不发起新分析 |
| `--json` | 输出原始 JSON |
| `--poll-only` | 用轮询代替 SSE 流 |
| `-v` | 显示分析进度 |
| `--base-url` | API 地址，默认 `http://localhost:8000` |

**前提：** 后端已在 `8000` 端口运行，且 `/api/v1/health/ready` 中 `redis` 与 `llm` 均为 ok。

### 10.4 repoagent-dev — 开发辅助

适合维护 RepoAgent 本身，例如：

- 「怎么加 Agent D？」
- 「LLM 返回 JSON 校验失败怎么修？」
- 「SSE 事件怎么接到前端？」

Skill 内含架构分层规则、扩展 Agent 清单、错误码对照和排错手册（见 `troubleshooting.md`）。

### 10.5 与 Web 界面的区别

| 方式 | 体验 |
|------|------|
| 浏览器 http://localhost:5173 | 可视化仪表盘 + 实时 SSE 日志面板 |
| repo-audit Skill | 在 Cursor 对话中获取报告摘要，适合快速评估与多仓库对比 |

---

## 附录：目录结构（运行相关）

```
RepoAgent/
├── .env                 # 环境变量（需自行创建，不提交 Git）
├── .env.example         # 环境变量模板
├── docker-compose.yml   # Docker 一键部署
├── run.md               # 本文档
├── .cursor/skills/      # Cursor Agent Skill
│   ├── repoagent-dev/   # 开发向：架构、扩展、排错
│   └── repo-audit/      # 使用向：CLI 调用 API 分析仓库
├── common/              # 公共配置与 LLM（后端依赖）
├── backend/             # FastAPI 后端
│   ├── requirements.txt
│   └── app/
├── frontend/            # Vue3 前端
│   ├── package.json
│   └── src/
├── scripts/
│   └── run_backend.py   # 后端启动脚本
└── logs/
    └── app.log          # 运行日志（自动生成）
```

---

> 如有问题，可先查看 `logs/app.log` 和后端终端输出，或访问 http://localhost:8000/docs 调试 API。
