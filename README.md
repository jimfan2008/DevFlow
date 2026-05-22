# DevFlow - AI 驱动的自动化软件开发项目管理平台

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](backend/requirements.txt)
[![Vue](https://img.shields.io/badge/vue-3.4%2B-green)](frontend/package.json)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104%2B-teal)](backend/requirements.txt)

## 项目简介

DevFlow 是一个面向人类用户与 AI Agent 协同的自动化软件开发项目管理平台。通过集成 Hermes Agent 和多种专业编程 Agent，实现从需求确认到代码交付的全流程自动化管理。

### 核心价值

- **需求协同**：通过多 Agent 群聊会议模式，结构化确认项目需求
- **任务自动拆解**：AI 按开发流程自动拆解任务并分配给专业编程 Agent
- **多 Agent 协作**：支持 7 种主流编程 Agent（Trae、CodeArts、Opencode、Cursor、Claude Code、CodeBuddy、Lingma）
- **代码仓库管理**：本地部署 Gitea，支持 Git Flow 分支策略和 Pull Request 流程
- **自动化验收**：任务成果自动验收，确保交付质量

***

## 核心特性

### 1. 项目需求协同 (Requirement Collaboration)

- 项目创建后自动创建需求评审群组（产品经理 + 架构师 + 开发者 + 测试工程师）
- 支持**会议模式**：结构化需求评审会议（8项议程）
- 支持**讨论模式**：自由群聊，@mention 定向沟通
- 会议纪要自动生成：决议、待办、风险、遗留问题

### 2. 任务自动拆解 (Task Decomposition)

- 基于锁定的需求文档自动拆解为原子任务
- 按开发流程拆解：需求分析 → 测试用例 → 功能编码 → 测试 → 部署 → 联调
- 自动识别任务依赖关系，避免循环依赖
- 每个任务标注执行要求和验收标准

### 3. 代码仓库管理 (Code Repository Management)

- **Gitea 本地部署**：私有代码托管，替代 GitHub/GitLab
- **Git Flow 分支策略**：main / develop / feature / release / hotfix / bugfix
- **Pull Request 流程**：代码审查、自动化检查、审批合并
- **代码提交规范**：Conventional Commits 标准（feat/fix/docs/style/refactor/test/build/ci/chore）

### 4. Hermes Agent 管理 (Hermes Agent Management)

- **Profile 自动扫描**：自动发现 `~/.hermes` 目录下的所有 Agent 配置
- **Gateway 模式**：通过 Gateway API 与 Hermes Agent 通信（支持流式响应）
- **健康检查**：实时监控 Agent 在线状态
- **多 Profile 支持**：同时管理多个 Hermes Agent，自由组合群组

### 5. 多 Agent 群聊与协作 (Multi-Agent Group Chat)

- **群组管理**：创建、编辑、删除协作群组
- **讨论模式**：自由发言、回复消息、@mention 定向提及
- **会议模式**：主持人控场、议程驱动、限时发言、当场拍板
- **4种会议类型模板**：需求评审会、技术方案讨论会、每日站会、故障复盘会

### 6. 编程 Agent 技能注册与调用 (Coding Agent Skills)

- **7种编程 Agent**：Trae、CodeArts、Opencode、Cursor、Claude Code、CodeBuddy、Lingma
- **9种技能类型**：TDD 测试用例、代码生成、测试用例、代码审查、Bug 修复、代码重构、环境部署、集成测试、文档编写
- **技能匹配规则**：自动匹配任务类型与 Agent 技能
- **负载均衡**：Agent 负载过高时自动调整分配策略

### 7. 成果验收 (Result Acceptance)

- **任务级验收**：测试用例覆盖度、功能代码正确性、部署环境可用性
- **项目级验收**：所有任务通过后汇总成果，发起最终验收
- **验收驳回**：附带明确的修改建议，指定时限内重新提交
- **前后任务隔离**：相邻任务必须分配给不同 Agent 执行交叉验证

### 8. 通知与交付 (Notification & Delivery)

- **进度通知**：需求确认、任务拆解、核心任务交付、验收驳回等关键节点
- **多渠道推送**：平台内消息、邮件、短信（可选）
- **项目完成通知**：成果下载链接、交付报告、售后支持说明

***

## 技术架构

### 技术栈

| 层级        | 技术选型                                             |
| --------- | ------------------------------------------------ |
| **前端**    | Vue 3 + Element Plus + Vite + Pinia + Vue Router |
| **后端**    | Python FastAPI + Celery + asyncio                |
| **数据库**   | PostgreSQL 14+ + Redis 6+                        |
| **代码托管**  | Gitea（本地自托管 Git 服务）                              |
| **AI 交互** | Hermes Gateway API + WebSocket                   |
| **部署**    | Docker + Docker Compose                          |

### 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        人类用户 (Client)                             │
│           浏览器 (需求提交/进度查看/群组聊天/会议参与)                │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP / WebSocket
┌───────────────────────────────▼─────────────────────────────────────┐
│                           Nginx (反向代理)                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                    FastAPI 后端 (DevFlow Server)                    │
│  ┌──────────┬─────────────┬────────────┬───────────────────┐       │
│  │ Auth     │ 需求协同    │ 任务拆解   │ Profile 扫描      │       │
│  └──────────┴─────────────┴────────────┴───────────────────┘       │
│  ┌──────────┬─────────────┬────────────┬───────────────────┐       │
│  │ 任务分配 │ 成果验收    │ 通知管理   │ Gateway Client    │       │
│  └──────────┴─────────────┴────────────┴───────────────────┘       │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │  Gitea 集成: 仓库创建、分支管理、PR 流程、提交规范校验     │     │
│  └───────────────────────────────────────────────────────────┘     │
└───────────────────────────────┬─────────────────────────────────────┘
         Gitea REST API         │                      Gateway API
┌───────────────────────────────▼─────────────────────────────────────┐
│                   Gitea 代码托管层 (本地部署)                         │
│  项目仓库 | Git Flow 分支 | Pull Request | 提交规范校验               │
└─────────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                    Hermes Profiles (用户本地 Agent 配置)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ architect    │  │ developer    │  │ qa-engineer  │              │
│  │ 架构师 Agent │  │ 开发 Agent   │  │ 测试 Agent   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                     编程 Agent (Trae/Cursor/Claude...)              │
│  代码生成 | 测试编写 | 代码审查 | Bug 修复 | 部署 | 文档              │
└─────────────────────────────────────────────────────────────────────┘
```

***

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
git clone https://github.com/your-username/devflow.git
cd devflow
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

| 服务     | 地址                           | 说明         |
| ------ | ---------------------------- | ---------- |
| 前端     | <http://localhost>           | 主应用界面      |
| 后端 API | <http://localhost:8000>      | FastAPI 后端 |
| API 文档 | <http://localhost:8000/docs> | Swagger UI |
| Gitea  | <http://localhost:3000>      | 代码托管平台     |

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
# 编辑 .env，配置数据库连接等

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 配置 API 地址
cp .env.example .env

# 启动开发服务器
npm run dev
```

访问 <http://localhost:5173>

***

## 环境配置

### 核心环境变量

| 变量名         | 默认值     | 说明   |
| ----------- | ------- | ---- |
| `APP_NAME`  | DevFlow | 应用名称 |
| `APP_DEBUG` | true    | 调试模式 |
| `APP_HOST`  | 0.0.0.0 | 监听地址 |
| `APP_PORT`  | 8000    | 监听端口 |

### 数据库配置

| 变量名            | 默认值              | 说明               |
| -------------- | ---------------- | ---------------- |
| `DATABASE_URL` | postgresql://... | PostgreSQL 连接字符串 |
| `REDIS_URL`    | redis\://...     | Redis 连接字符串      |
| `DB_POOL_SIZE` | 5                | 数据库连接池大小         |

### JWT 认证

| 变量名                  | 默认值            | 说明               |
| -------------------- | -------------- | ---------------- |
| `JWT_SECRET`         | dev-jwt-secret | JWT 密钥（生产环境必须修改） |
| `JWT_ALGORITHM`      | HS256          | 加密算法             |
| `JWT_EXPIRE_MINUTES` | 30             | Token 过期时间（分钟）   |

### Gitea 配置

| 变量名                 | 默认值       | 说明             |
| ------------------- | --------- | -------------- |
| `GITEA_HOST`        | localhost | Gitea 服务器地址    |
| `GITEA_PORT`        | 3000      | Gitea HTTP 端口  |
| `GITEA_PROTOCOL`    | http      | 协议（http/https） |
| `GITEA_API_TOKEN`   | -         | Gitea API 访问令牌 |
| `GITEA_DEFAULT_ORG` | devflow   | 默认组织名称         |

### Hermes Agent 配置

| 变量名                      | 默认值        | 说明                |
| ------------------------ | ---------- | ----------------- |
| `HERMES_PROFILES_PATH`   | \~/.hermes | Hermes Profile 目录 |
| `HERMES_GATEWAY_TIMEOUT` | 360        | Gateway API 超时（秒） |
| `HERMES_MAX_CONCURRENT`  | 5          | 最大并发请求数           |

***

## 使用指南

### 1. 初始化 Hermes Agent

#### 安装 Hermes Agent

```bash
# Linux/macOS/WSL2
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# 验证安装
hermes doctor
```

#### 创建 Profile

在 `~/.hermes/profiles/` 目录下创建 Agent 配置，例如：

```yaml
# ~/.hermes/profiles/architect/config.yaml
name: architect
model_default: gpt-4o
model_provider: openai
gateway_port: 8765
personality: "专业技术架构师，擅长系统设计和性能优化"
```

#### 启动 Gateway

```bash
# 配置网关
hermes gateway setup

# 启动网关
hermes gateway start
```

### 2. 配置 Gitea

首次访问 <http://localhost:3000> 进入安装向导：

1. **数据库配置**：选择 PostgreSQL，填写连接信息
2. **基本设置**：
   - 站点名称：DevFlow Code Repository
   - 仓库根目录：`/data/git/gitea-repositories`
3. **管理员账号**：创建第一个用户（自动成为管理员）
4. 点击「立即安装」

### 3. 创建项目

1. 登录 DevFlow 前端
2. 点击「创建项目」
3. 填写项目信息：
   - 项目名称
   - 项目描述
   - 核心需求
   - 技术栈偏好
   - 交付时间
4. 提交后自动创建需求评审群组

### 4. 需求评审会议

1. 进入项目详情页
2. 点击「启动需求评审会」
3. 等待多 Agent 加入会议
4. 主持人按议程引导讨论：
   - PRD 整体介绍
   - 业务流程梳理
   - 边界规则确认
   - 特殊场景讨论
   - 开发提问
   - 当场确认
5. 会议结束后查看结构化纪要
6. 确认需求，锁定并触发任务拆解

### 5. 查看任务进度

- **看板视图**：拖拽任务卡片，查看状态流转
- **任务详情**：查看任务描述、验收标准、执行进度
- **依赖关系**：可视化任务依赖图
- **负载分析**：查看各 Agent 负载情况

### 6. 代码仓库操作

系统自动在 Gitea 中创建项目仓库：

- **分支管理**：Git Flow 策略自动管理
- **Pull Request**：功能合并必经代码审查
- **提交规范**：自动验证 Conventional Commits
- **Webhook**：支持 CI/CD 集成

***

## API 参考

### 认证 API

| 方法   | 路径                   | 描述   |
| ---- | -------------------- | ---- |
| POST | `/api/auth/login`    | 用户登录 |
| POST | `/api/auth/register` | 用户注册 |

### 项目管理 API

| 方法   | 路径                                       | 描述       |
| ---- | ---------------------------------------- | -------- |
| POST | `/api/projects`                          | 创建项目     |
| GET  | `/api/projects`                          | 获取项目列表   |
| GET  | `/api/projects/:id`                      | 获取项目详情   |
| POST | `/api/projects/:id/requirements/confirm` | 确认需求     |
| POST | `/api/projects/:id/tasks/decompose`      | 触发任务拆解   |
| GET  | `/api/projects/:id/tasks`                | 获取项目任务清单 |

### Hermes Agent API

| 方法   | 路径                        | 描述                  |
| ---- | ------------------------- | ------------------- |
| GET  | `/api/profiles`           | 获取所有 Hermes Profile |
| GET  | `/api/agents/discover`    | 重新扫描发现 Agent        |
| POST | `/api/agents/sync-hermes` | 同步 Profile 到数据库     |
| GET  | `/api/hermes/health`      | 检查 Gateway 健康状态     |
| POST | `/api/hermes/chat`        | 与 Hermes 对话（非流式）    |
| POST | `/api/hermes/chat/stream` | 与 Hermes 对话（流式 SSE） |

### 群组与会议 API

| 方法   | 路径                         | 描述       |
| ---- | -------------------------- | -------- |
| GET  | `/api/groups`              | 获取群组列表   |
| POST | `/api/groups`              | 创建群组     |
| GET  | `/api/groups/:id`          | 获取群组详情   |
| GET  | `/api/groups/:id/messages` | 获取群组消息   |
| GET  | `/api/groups/:id/outcomes` | 获取会议结果   |
| GET  | `/api/groups/:id/tasks`    | 获取群组待办任务 |

### 任务管理 API

| 方法   | 路径                        | 描述       |
| ---- | ------------------------- | -------- |
| GET  | `/api/tasks/pending`      | 获取待办任务列表 |
| GET  | `/api/tasks/:id`          | 获取任务详情   |
| POST | `/api/tasks/:id/start`    | 标记任务开始   |
| POST | `/api/tasks/:id/progress` | 上报任务进度   |
| POST | `/api/tasks/:id/deliver`  | 交付任务成果   |
| POST | `/api/tasks/:id/accept`   | 验收任务成果   |

### 代码仓库 API

| 方法   | 路径                                   | 描述       |
| ---- | ------------------------------------ | -------- |
| POST | `/api/repos`                         | 创建代码仓库   |
| GET  | `/api/repos`                         | 获取仓库列表   |
| GET  | `/api/repos/:id`                     | 获取仓库详情   |
| GET  | `/api/repos/:id/branches`            | 获取分支列表   |
| POST | `/api/repos/:id/branches`            | 创建新分支    |
| GET  | `/api/repos/:id/pulls`               | 获取 PR 列表 |
| POST | `/api/repos/:id/pulls`               | 创建 PR    |
| POST | `/api/repos/:id/pulls/:number/merge` | 合并 PR    |
| GET  | `/api/repos/:id/commits`             | 获取提交记录   |
| POST | `/api/repos/validate-commit`         | 验证提交规范   |

### WebSocket 端点

| 端点                          | 描述     |
| --------------------------- | ------ |
| `ws://{host}/ws/group-chat` | 群聊实时通信 |

**消息类型：**

- `subscribe` - 订阅群组消息
- `send_message` - 发送消息（支持 @mention）
- `start_meeting` - 启动会议
- `stop_meeting` - 停止会议
- `meeting_intervention` - 会议干预

完整 API 文档请访问：<http://localhost:8000/docs>

***

## 开发指南

### 项目结构

```
devflow/
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── requirements.py
│   │   │   ├── tasks.py
│   │   │   ├── hermes.py
│   │   │   ├── groups.py
│   │   │   └── repos.py
│   │   ├── models/            # 数据模型
│   │   ├── schemas/           # Pydantic 模式
│   │   ├── services/          # 业务逻辑
│   │   │   ├── hermes_service.py
│   │   │   ├── task_service.py
│   │   │   └── gitea_client.py
│   │   ├── middleware/        # 中间件
│   │   ├── ws/                # WebSocket
│   │   └── main.py            # 应用入口
│   ├── tests/                 # 测试
│   ├── alembic/               # 数据库迁移
│   └── requirements.txt
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── api/               # API 模块
│   │   ├── components/        # Vue 组件
│   │   ├── views/             # 页面视图
│   │   ├── stores/            # Pinia 状态管理
│   │   ├── router/            # 路由
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
├── docker/                     # Docker 配置
│   ├── nginx/
│   ├── postgres/
│   └── redis/
├── docker-compose.dev.yml     # 开发环境编排
├── docker-compose.prod.yml    # 生产环境编排
├── .env.example               # 环境变量示例
└── SRS_软件需求规格说明书.md   # 详细需求文档
```

### 运行测试

```bash
# 后端测试
cd backend
pytest -v

# 查看测试覆盖率
pytest --cov=app --cov-report=html

# 前端测试
cd frontend
npm run test
```

### 代码规范

**Python 后端：**

- 遵循 PEP 8 规范
- 使用类型注解
- 单元测试覆盖率 > 80%

**Vue 前端：**

- 遵循 Vue 3 组合式 API
- 使用 TypeScript
- ESLint + Prettier 格式化

**Git 提交：**
遵循 Conventional Commits 规范：

```
<type>(<scope>): <subject>

类型：
- feat: 新功能
- fix: Bug 修复
- docs: 文档更新
- style: 代码格式
- refactor: 重构
- test: 测试
- build: 构建
- ci: CI/CD
- chore: 杂项
```

### 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: 添加AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

***

## 常见问题

### Q1: Hermes Agent 无法连接？

**A:** 检查以下几点：

- 确认 Hermes Gateway 已启动：`hermes gateway start`
- 确认 Gateway 端口监听：`netstat -an | grep 8765`
- 检查 DevFlow 配置中的 Profile 路径
- 查看 DevFlow 日志中的错误信息

### Q2: Gitea 无法创建仓库？

**A:** 检查以下几点：

- 确认 Gitea 服务正常运行
- 验证 Gitea API Token 权限
- 确认默认组织（devflow）已创建
- 检查 Gitea 磁盘空间是否充足

### Q3: 任务一直处于"待分配"状态？

**A:** 可能原因：

- 没有可用的编程 Agent 注册
- 任务类型与 Agent 技能不匹配
- 所有 Agent 都处于高负载状态
- 前置任务未完成

### Q4: 如何添加新的编程 Agent？

**A:** 有三种方式：

1. **API 主动注册**：Agent 启动时调用 `POST /api/agents/register`
2. **配置文件注册**：在 DevFlow 配置文件中静态声明
3. **手动注册**：通过管理界面手动添加

### Q5: Docker 启动后服务无法访问？

**A:** 排查步骤：

```bash
# 查看容器状态
docker-compose -f docker-compose.dev.yml ps

# 查看容器日志
docker-compose -f docker-compose.dev.yml logs fastapi

# 检查端口占用
netstat -an | grep -E "8000|5173|3000"
```

### Q6: 如何重置开发环境？

**A:** 清除所有数据（注意：这会删除所有数据库和 Gitea 数据）：

```bash
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```

***

## 相关文档

- [SRS 软件需求规格说明书](SRS_软件需求规格说明书.md) - 详细的功能需求和技术规格
- [前端 README](frontend/README.md) - 前端开发指南
- [API 文档](http://localhost:8000/docs) - 在线 Swagger 文档
- [Gitea 文档](https://docs.gitea.io/) - Gitea 官方文档
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) - Hermes 开源项目

***

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

***

## 致谢

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) - 核心 AI 调度代理
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Python Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Gitea](https://gitea.io/) - 轻量级自托管 Git 服务

***

<div align="center">
  <p>Made with ❤️ by DevFlow Team</p>
</div>
