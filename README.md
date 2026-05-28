# DevFlow - AI Agent 全自动软件开发项目管理平台

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](backend/requirements.txt)
[![Vue](https://img.shields.io/badge/vue-3.4%2B-green)](frontend/package.json)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104%2B-teal)](backend/requirements.txt)
[![SRS](https://img.shields.io/badge/SRS-v4.0-orange)](SRS_软件需求规格说明书.md)

## 项目简介

DevFlow v4.0 是一个面向人类用户与 AI Agent 协同的**全自动化软件开发项目管理平台**。平台以 **16 步 AI Agent 全自动开发流程**为主线，通过 **10 个命名 Hermes Agent** 角色紧密协作（海梅/后兴/后旺/后发/后达/后富/后贵/后荣/后华），围绕项目讨论群实时沟通，每步产出经 **QA 门控**（后荣检验）合格方可进入下一步，检验合格产出全部提交 Gitea 代码库。支持 **Agent 蜂群**并行执行代码编写与测试，以 **TDD** 驱动开发，实现从需求分析到部署交付的全流程自动化。

### 核心价值

- **16 步标准流程**：从项目创建 → 需求分析 → 架构设计 → TDD 测试用例 → 代码编写 → 全面测试 → 安全审计 → 生产部署 → 文档交付 → 用户确认，全流程自动化
- **QA 门控机制**：每步产出必须经后荣(QA)检验合格方可进入下一步，不合格退回重做，确保交付质量
- **Agent 蜂群并行执行**：后发/后达可建立编程 Agent 蜂群（9 种编程 Agent），并行完成代码编写和测试任务
- **项目讨论群协作**：所有 Agent 加入项目讨论群，支持讨论模式和会议模式，@mention 定向沟通
- **TDD 驱动开发**：先制订测试用例计划 → 蜂群编写 TDD 测试用例 → 蜂群编写功能代码
- **原子化任务管理**：每个任务最小原子化，有向无环依赖图，测试用例一一对应
- **迭代修改闭环**：用户在第 16 步不满意则自动回到第 3 步重新迭代，已合格产出保留

---

## 16 步 AI Agent 全自动开发流程

| 步骤 | 执行 Agent | 任务内容 | QA 门控 |
|------|-----------|---------|---------|
| 1 | 人类用户 | 提出项目核心需求 | — |
| 2 | 海梅 (项目经理) | 确认核心目标，搭建组织架构，建立项目讨论群（拉入全部 9 个 Agent） | ✅ |
| 3 | 后兴 (需求分析师) | 需求分析，产出软件需求规格说明书 | ✅ |
| 4 | 后旺 (架构设计师) | 架构设计、后端设计、前端设计、数据库设计（4 份文档，逐一检验） | ✅ |
| 5 | 后富 (CI/CD 工程师) | 建立开发环境 | ✅ |
| 6 | 海梅 | 制订 TDD 测试用例编写计划 | ✅ |
| 7 | 后发 (程序员) | 建立代码编写 Agent 蜂群，同步编写 TDD 测试用例 | ✅ |
| 8 | 海梅 | 制订代码编写计划（原子化任务 + 有向无环依赖图） | ✅ |
| 9 | 后发 (程序员) | 建立代码编写 Agent 蜂群，编写功能代码 | ✅ |
| 10 | 后富 (CI/CD 工程师) | 部署代码到测试环境 | — |
| 11 | 后达 (测试员) | 建立代码测试 Agent 蜂群，执行单元/模块/集成测试 + 前端实操验证 | ✅ |
| 12 | 后华 (安全员) | 代码审计、合规审查、渗透测试、漏洞修复 | ✅ |
| 13 | 后富 (CI/CD 工程师) | 部署代码到生产环境 | — |
| 14 | 后贵 (文档管理员) | 完善项目文档，确保所有文档版本一致性 | ✅ |
| 15 | 海梅 (项目经理) | 向用户报告交付成果 | — |
| 16 | 人类用户 | 确认满意度（不满意 → 回到第 3 步迭代） | — |

---

## 10 个命名 Agent 角色

| 角色名 | 角色 | 职责 |
|--------|------|------|
| **海梅 (HaiMei)** | 默认 Hermes Agent / 项目经理 | 任务分派，流程管控，对交付成果负责，主动与用户对话 |
| **后兴 (HouXing)** | 需求分析师 | 需求分析，与用户沟通，产出完整准确的软件需求说明书 |
| **后旺 (HouWang)** | 架构设计师 | 架构设计、后端设计、前端设计、数据库设计 |
| **后发 (HouFa)** | 程序员 / 蜂群调度 | 建立代码编写 Agent 蜂群，监督蜂群完成 TDD 测试用例和代码 |
| **后达 (HouDa)** | 测试员 / 蜂群调度 | 建立代码测试 Agent 蜂群，执行全类型测试 |
| **后富 (HouFu)** | CI/CD 工程师 | 开发环境搭建，代码部署到测试/生产环境 |
| **后贵 (HouGui)** | 文档管理员 | 全项目文档一致性管理，任一文档修改则全部同步 |
| **后荣 (HouRong)** | QA 门控 | 检验每个 Agent 产出，未达标退回重做，达标放行并提交代码库 |
| **后华 (HouHua)** | 安全员 | 代码审计、合规审查、渗透测试、漏洞修复 |

Agent 蜂群支持的 9 种编程 Agent：Claude Code / Codex / Opencode / Cursor / CodeArts / Trae / Lingma / hermes 子 agent / pi-coding-agent 子 agent

---

## 核心特性

### 1. 16 步工作流引擎 (Workflow Engine)

- 完整 16 步状态机，自动流转
- 每步产出记录与 QA 状态跟踪
- 步骤间依赖检验（前一步 QA 通过方可进入下一步）
- 迭代闭环：用户不满意 → 自动回到第 3 步，已合格产出保留

### 2. QA 门控 (QA Gating)

- 后荣(QA) 对每步产出进行多维度检验
- 11 种产出类型、60+ 检验维度
- 不合格产出退回重做，附带详细修改建议
- 合格产出全部提交 Gitea 代码库，确保检验记录完整可追溯

### 3. Agent 蜂群 (Agent Swarm)

- 后发/后达 按需建立蜂群，管理成员调度
- 支持 9 种编程 Agent 混合编组
- 依赖感知任务分发：有依赖关系的任务自动分配给不同 Agent
- 实时进度监控，蜂群完成后自动解散

### 4. 项目讨论群 (Discussion Group)

- 项目创建后自动建立讨论群，全部 9 个 Agent 加入
- **讨论模式**：自由发言、@mention 定向沟通、消息持久化
- **会议模式**：主持人控场、结构化议程、产出决议/待办/风险
- WebSocket 实时通信

### 5. 代码仓库管理 (Gitea Integration)

- Gitea 本地部署，私有代码托管
- Git Flow 分支策略：main / develop / feature / release / hotfix / bugfix
- Pull Request 流程：代码审查 → 自动化检查 → 审批合并
- Conventional Commits 提交规范

### 6. Hermes Agent 管理

- Profile 自动扫描：自动发现 `~/.hermes` 目录下的 Agent 配置
- Gateway 模式：通过 Gateway API 与 Hermes Agent 通信（支持流式响应）
- 健康检查：实时监控 Agent 在线状态
- v4.0 新增 9 个命名角色（haimei/houxing/houwang/houfa/houda/houfu/hougui/hourong/houhua）

### 7. TDD 驱动开发

- 先制订测试用例计划 → 蜂群编写 TDD 测试用例 → 蜂群编写功能代码
- 原子化任务与测试用例一一对应
- 有向无环依赖图确保任务正确执行顺序

### 8. 安全审计

- 代码审计：静态分析 + 人工审查
- 合规审查：OWASP / ISO 27001 标准
- 渗透测试：模拟攻击场景
- 漏洞修复：发现即修复，修复后复检

---

## 技术架构

### 技术栈

| 层级 | 技术选型 |
|------|---------|
| **前端** | Vue 3 + Element Plus + Vite + Pinia + Vue Router |
| **后端** | Python 3.10+ / FastAPI / Celery / asyncio |
| **数据库** | PostgreSQL 14+ + Redis 6+ |
| **代码托管** | Gitea（本地自托管 Git 服务） |
| **AI 交互** | Hermes Gateway API + WebSocket |
| **部署** | Docker + Docker Compose |

### 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     人类用户 (Client)                            │
│         浏览器 (项目创建 / 进度查看 / 群聊 / 会议 / 验收)         │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP / WebSocket
┌──────────────────────────────┴──────────────────────────────────┐
│                        Nginx (反向代理)                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│                  FastAPI 后端 (DevFlow v4.0)                     │
│  ┌───────────┬────────────┬────────────┬──────────────────┐     │
│  │ 16步流程  │ QA 门控    │ 蜂群调度   │ 安全审计          │     │
│  └───────────┴────────────┴────────────┴──────────────────┘     │
│  ┌───────────┬────────────┬────────────┬──────────────────┐     │
│  │ 讨论群    │ Agent 管理 │ 任务管理   │ Gitea 集成        │     │
│  └───────────┴────────────┴────────────┴──────────────────┘     │
│  ┌───────────┬────────────┬────────────┬──────────────────┐     │
│  │ 文档管理  │ 验收交付   │ 通知管理   │ Gateway Client   │     │
│  └───────────┴────────────┴────────────┴──────────────────┘     │
└──────────────────────────────┬──────────────────────────────────┘
         Gitea REST API        │            Gateway API / WebSocket
┌──────────────────────────────┴──────────────────────────────────┐
│             Gitea 代码托管层 (QA 合格产物全部提交)                │
│   Git Flow 分支 | Pull Request | 提交规范校验 | Webhook          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│             Hermes Agent Profiles (9 个命名角色)                  │
│  haimei / houxing / houwang / houfa / houda / houfu /            │
│  hougui / hourong / houhua                                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│    编程 Agent 蜂群 (Claude Code / Codex / Opencode / Cursor /    │
│    CodeArts / Trae / Lingma / hermes子agent / pi-coding-agent)   │
│  代码生成 | TDD 测试 | 代码审查 | Bug 修复 | 部署 | 文档         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- Git 2.25+
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

### 方式一：Docker 部署（推荐）

#### 1. 克隆项目

```bash
git clone https://github.com/jimfan2008/DevFlow.git
cd DevFlow
```

#### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置必要的环境变量（参见「环境配置」章节）。

#### 3. 启动开发环境

```bash
# 启动所有服务（后端 + 前端 + 数据库 + Redis + Gitea）
docker-compose -f docker-compose.dev.yml up -d

# 查看服务状态
docker-compose -f docker-compose.dev.yml ps

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f
```

#### 4. 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | <http://localhost> | 主应用界面 |
| 后端 API | <http://localhost:8000> | FastAPI 后端 |
| API 文档 | <http://localhost:8000/docs> | Swagger UI |
| Gitea | <http://localhost:3000> | 代码托管平台 |

### 方式二：本地开发

#### 后端开发

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env

# 使用 SQLite 快速启动（无需 PostgreSQL）
# 编辑 .env，设置: DATABASE_URL=sqlite+aiosqlite:///./devflow.db

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 <http://localhost:5173>

#### 运行测试

```bash
# 后端单元测试（104 个 v4.0 测试）
cd backend
pytest tests/test_workflow_engine.py tests/test_agent_roles.py \
       tests/test_swarm.py tests/test_qa_gate.py \
       tests/test_full_v4_workflow.py -v

# API 集成测试（58 个用例）
python tests/test_api_e2e.py

# 前端 E2E 测试（Mock 环境，无需后端）
cd frontend
npm run build                          # 构建静态文件
node e2e/mock-server.mjs               # 启动 Mock Server
node e2e/cli/v4-e2e-workflow.mjs       # 运行 E2E 测试
```

---

## 环境配置

### 核心环境变量

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `APP_NAME` | DevFlow | 应用名称 |
| `APP_DEBUG` | true | 调试模式 |
| `APP_HOST` | 0.0.0.0 | 监听地址 |
| `APP_PORT` | 8000 | 监听端口 |

### 数据库配置

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `DATABASE_URL` | postgresql://... | PostgreSQL 连接字符串（开发可用 SQLite） |
| `REDIS_URL` | redis://... | Redis 连接字符串 |
| `DB_POOL_SIZE` | 5 | 数据库连接池大小 |

### JWT 认证

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `JWT_SECRET` | dev-jwt-secret | JWT 密钥（生产环境必须修改） |
| `JWT_ALGORITHM` | HS256 | 加密算法 |
| `JWT_EXPIRE_MINUTES` | 30 | Token 过期时间（分钟） |

### Gitea 配置

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `GITEA_HOST` | localhost | Gitea 服务器地址 |
| `GITEA_PORT` | 3000 | Gitea HTTP 端口 |
| `GITEA_PROTOCOL` | http | 协议（http/https） |
| `GITEA_API_TOKEN` | - | Gitea API 访问令牌 |
| `GITEA_DEFAULT_ORG` | devflow | 默认组织名称 |

### Hermes Agent 配置

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `HERMES_PROFILES_PATH` | ~/.hermes | Hermes Profile 目录 |
| `HERMES_GATEWAY_TIMEOUT` | 360 | Gateway API 超时（秒） |
| `HERMES_MAX_CONCURRENT` | 5 | 最大并发请求数 |

---

## 使用指南

### 1. 初始化 Hermes Agent

#### 安装 Hermes Agent

```bash
# Linux/macOS/WSL2
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes doctor
```

#### v4.0 命名角色 Profile 配置

在 `~/.hermes/profiles/` 下创建 9 个角色配置：

```yaml
# ~/.hermes/profiles/haimei/config.yaml
name: haimei
role_name: 海梅 (项目经理)
model_default: gpt-4o
gateway_port: 8765
personality: "资深项目经理，主动与人类用户沟通，协调全流程"
```

### 2. 创建项目并启动 16 步流程

1. 登录 DevFlow 前端
2. 点击「创建项目」，填写项目名称和核心目标
3. 海梅(项目经理) 自动搭建组织架构，建立项目讨论群
4. 流程按 16 步自动推进，每步产出经后荣(QA) 检验
5. 用户可随时查看进度和 QA 检验记录
6. 第 16 步确认满意度（不满意 → 回到第 3 步迭代）

### 3. 查看工作流进度

- **流程视图**：查看 16 步状态（pending / in_progress / qa_review / completed / rejected）
- **QA 面板**：查看每步检验记录、驳回原因、修改建议
- **蜂群监控**：查看代码编写和测试蜂群的实时进度
- **讨论群**：所有 Agent 的沟通记录

### 4. 项目讨论群协作

- **讨论模式**：Agent 自由发言，@mention 定向提及
- **会议模式**：海梅担任主持人，按议程讨论，产出决议/待办
- 所有消息持久化，支持历史回溯

### 5. 代码仓库操作

系统自动在 Gitea 中创建项目仓库：

- 每步 QA 通过的产出自动提交
- Git Flow 分支策略自动管理
- Pull Request：功能合并必经代码审查
- Conventional Commits 提交规范自动校验

---

## API 参考

### 认证

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/register` | 用户注册 |

### v4.0 工作流 API（核心新增）

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/workflow/{project_id}/step2` | 海梅确认核心目标 |
| POST | `/api/v1/workflow/{project_id}/step3` | 后兴需求分析 |
| POST | `/api/v1/workflow/{project_id}/step4` | 后旺架构设计 |
| POST | `/api/v1/workflow/{project_id}/step5` | 后富开发环境 |
| POST | `/api/v1/workflow/{project_id}/step6` | 海梅 TDD 计划 |
| POST | `/api/v1/workflow/{project_id}/step7` | 后发蜂群 TDD 用例 |
| POST | `/api/v1/workflow/{project_id}/step8` | 海梅编码计划 |
| POST | `/api/v1/workflow/{project_id}/step9` | 后发蜂群功能代码 |
| POST | `/api/v1/workflow/{project_id}/step10` | 后富部署测试环境 |
| POST | `/api/v1/workflow/{project_id}/step11` | 后达蜂群全面测试 |
| POST | `/api/v1/workflow/{project_id}/step12` | 后华安全审计 |
| POST | `/api/v1/workflow/{project_id}/step13` | 后富部署生产环境 |
| POST | `/api/v1/workflow/{project_id}/step14` | 后贵文档完善 |
| POST | `/api/v1/workflow/{project_id}/step15` | 海梅交付报告 |
| POST | `/api/v1/workflow/{project_id}/step16` | 用户确认满意度 |
| POST | `/api/v1/workflow/{project_id}/step{n}/qa` | 第 n 步 QA 检验 |
| GET  | `/api/v1/workflow/{project_id}/status` | 查询项目进度 |

### v4.0 QA 门控 API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/qa/inspect` | QA 检验（通过/驳回） |
| GET  | `/api/v1/qa/{project_id}/records` | QA 检验记录查询 |
| POST | `/api/v1/qa/rollback` | QA 退回重做 |
| GET  | `/api/v1/qa/status` | QA 状态查询 |

### v4.0 蜂群管理 API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/swarms` | 创建蜂群 |
| GET  | `/api/v1/swarms/{id}` | 查询蜂群详情 |
| POST | `/api/v1/swarms/{id}/members` | 添加蜂群成员 |
| DELETE | `/api/v1/swarms/{id}/members/{agent_id}` | 移除蜂群成员 |
| POST | `/api/v1/swarms/{id}/dispatch` | 分发任务 |
| GET  | `/api/v1/swarms/{id}/progress` | 查询蜂群进度 |
| DELETE | `/api/v1/swarms/{id}` | 解散蜂群 |

### v4.0 安全审计 API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/security/{project_id}/audit` | 启动安全审计 |
| GET  | `/api/v1/security/{project_id}/audit/status` | 查询审计状态 |
| GET  | `/api/v1/security/{project_id}/audit/report` | 获取审计报告 |

### 项目管理 API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/projects` | 创建项目 |
| GET  | `/api/projects` | 获取项目列表 |
| GET  | `/api/projects/:id` | 获取项目详情 |
| POST | `/api/projects/:id/tasks/decompose` | 触发任务拆解 |
| GET  | `/api/projects/:id/tasks` | 获取项目任务清单 |

### WebSocket

| 端点 | 描述 |
|------|------|
| `ws://{host}/ws/group-chat` | 群聊实时通信（讨论/会议模式） |

完整 API 文档请访问：<http://localhost:8000/docs>

---

## 项目结构

```
devflow/
├── backend/                       # 后端代码
│   ├── app/
│   │   ├── api/                   # API 路由
│   │   │   ├── auth.py            # 认证
│   │   │   ├── projects.py        # 项目管理
│   │   │   ├── workflow.py        # 16步流程调度 (v4.0)
│   │   │   ├── qa.py              # QA 门控 (v4.0)
│   │   │   ├── swarms.py          # 蜂群管理 (v4.0)
│   │   │   ├── security.py        # 安全审计 (v4.0)
│   │   │   ├── hermes.py          # Hermes Agent
│   │   │   ├── groups.py          # 讨论群
│   │   │   └── repos.py           # 代码仓库
│   │   ├── models/                # 数据模型
│   │   │   ├── workflow_step.py   # 工作流步骤 (v4.0)
│   │   │   ├── qa_record.py       # QA 检验记录 (v4.0)
│   │   │   ├── swarm.py           # 蜂群/蜂群任务 (v4.0)
│   │   │   ├── security_audit.py  # 安全审计 (v4.0)
│   │   │   ├── doc_version.py     # 文档版本管理 (v4.0)
│   │   │   └── ...
│   │   ├── services/              # 业务逻辑
│   │   │   ├── workflow_engine.py # 流程引擎 (v4.0)
│   │   │   ├── qa_gate_service.py # QA 门控服务 (v4.0)
│   │   │   ├── swarm_service.py   # 蜂群服务 (v4.0)
│   │   │   ├── agent_role_service.py # 角色服务 (v4.0)
│   │   │   └── ...
│   │   └── main.py
│   ├── tests/                     # 测试
│   │   ├── test_workflow_engine.py   # 流程引擎测试 (23)
│   │   ├── test_agent_roles.py       # 角色服务测试 (18)
│   │   ├── test_swarm.py             # 蜂群服务测试 (13)
│   │   ├── test_qa_gate.py           # QA 门控测试 (14)
│   │   ├── test_full_v4_workflow.py  # 全流程集成测试 (36)
│   │   └── test_api_e2e.py           # API E2E 测试 (58)
│   ├── alembic/                   # 数据库迁移
│   │   └── versions/
│   │       ├── 004_v4_agent_roles.py
│   │       ├── 005_v4_workflow_qa.py
│   │       └── 006_v4_swarm_security_docs.py
│   └── requirements.txt
├── frontend/                      # 前端代码
│   ├── src/
│   │   ├── api/                   # API 模块
│   │   ├── components/            # Vue 组件
│   │   ├── views/                 # 页面视图
│   │   │   ├── LoginView.vue      # 登录
│   │   │   ├── RegisterView.vue   # 注册
│   │   │   ├── ProjectListView.vue # 项目列表
│   │   │   ├── ChatView.vue       # 讨论群
│   │   │   ├── RequirementsView.vue # 需求管理
│   │   │   └── ...
│   │   ├── stores/                # Pinia 状态
│   │   └── main.js
│   ├── e2e/
│   │   ├── cli/
│   │   │   └── v4-e2e-workflow.mjs # 前端 E2E 测试
│   │   └── mock-server.mjs         # Mock Server
│   ├── package.json
│   └── vite.config.js
├── docker/                        # Docker 配置
├── docker-compose.dev.yml
├── .gitignore
├── SRS_软件需求规格说明书.md      # v4.0 完整需求规格
└── README.md
```

---

## 运行测试

```bash
# 后端 v4.0 单元测试 (104 个)
cd backend
pytest tests/test_workflow_engine.py tests/test_agent_roles.py \
       tests/test_swarm.py tests/test_qa_gate.py \
       tests/test_full_v4_workflow.py -v

# API 集成测试 (58 个)
python tests/test_api_e2e.py

# 前端 E2E 测试 (Mock 环境)
cd frontend
npm run build
node e2e/mock-server.mjs &          # 启动 Mock Server
node e2e/cli/v4-e2e-workflow.mjs    # 运行 E2E
```

---

## 代码规范

**Python 后端**：遵循 PEP 8，类型注解，测试覆盖率 > 80%

**Vue 前端**：组合式 API，ESLint + Prettier

**Git 提交**：Conventional Commits

```
feat(workflow): 添加第5步QA门控
fix(swarm): 修复蜂群任务分配死锁
docs(srs): 更新v4.0术语定义
test(e2e): 添加全流程集成测试
```

---

## 常见问题

### Q1: 如何快速体验 16 步流程？

```bash
cd backend
python tests/test_api_e2e.py   # 自动执行完整 16 步 API 调用
```

### Q2: 前端 E2E 测试如何运行？

```bash
cd frontend
npm run build                            # 构建前端
node e2e/mock-server.mjs                 # 启动 Mock Server (端口 8080)
node e2e/cli/v4-e2e-workflow.mjs         # 运行测试
```

### Q3: 如何注册新的编程 Agent 到蜂群？

通过 API 主动注册或在 Swarm 管理接口中添加：
```bash
curl -X POST http://localhost:8000/api/v1/swarms/{swarm_id}/members \
  -H "Content-Type: application/json" \
  -d '{"agent_type": "claude_code", "agent_id": "claude-001"}'
```

### Q4: QA 检验不合格怎么办？

后荣(QA) 会退回产出并附带修改建议。相关 Agent 根据建议修改后重新提交，后荣重新检验直至通过。

### Q5: 用户不满意如何触发迭代？

在第 16 步时，用户选择"不满意"并提供反馈，系统自动回到第 3 步（需求分析），已合格的步骤产出保留。迭代次数无限制。

---

## 相关文档

- [SRS 软件需求规格说明书 v4.0](SRS_软件需求规格说明书.md) - 完整的功能需求和 16 步流程规格
- [API 文档](http://localhost:8000/docs) - Swagger 在线文档
- [Gitea 文档](https://docs.gitea.io/) - Gitea 官方文档
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) - Hermes 开源项目

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 致谢

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) - 核心 AI 调度代理
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Python Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Gitea](https://gitea.io/) - 轻量级自托管 Git 服务

---

<div align="center">
  <p>Made with ❤️ by DevFlow Team</p>
</div>