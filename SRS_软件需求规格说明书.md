# DevFlow 项目管理平台 - 软件需求规格说明书 (SRS)



版本:

&#x20;3.3\


日期:

&#x20;2026-05-18\


作者:

&#x20;@houxing (Hermes Agent)\


状态:

&#x20;Gitea 本地部署与代码仓库管理



变更日志:



- v3.3 (2026-05-18): Gitea 本地部署与代码仓库管理模块
  - 术语定义新增：Gitea、Gitea 本地部署、代码仓库、分支、Git Flow 分支策略、Pull Request、代码提交规范、代码成果
  - 2.3节更新：运行环境新增 Gitea 技术栈要求
  - 2.5节新增：Gitea 本地安装部署模块
    - 支持 Docker/二进制/源码三种安装方式
    - Docker Compose 配置示例
    - 安装向导配置项说明
    - DevFlow 连接 Gitea 配置
    - Systemd 自动启动配置
  - 3.3节新增：代码库管理模块
    - 3.3.1 项目仓库自动创建
    - 3.3.2 分支策略（Git Flow）
    - 3.3.3 代码提交规范（Conventional Commits）
    - 3.3.4 Pull Request 流程
    - 3.3.5 代码成果提交要求
  - 5.1节更新：技术栈新增代码托管层（Gitea）
  - 5.2节更新：架构图新增 Gitea 代码托管层
  - 5.3节更新：数据库设计新增 5 个代码仓库相关表（repos, repo_branches, pull_requests, commits, task_commits）
  - 6.1.6节新增：Gitea 代码仓库管理 API 接口（19 个端点）
  - 7.8节新增：Gitea 代码仓库管理验收（7 个子模块，60+ 验收项）
- v3.2 (2026-05-18): 编程 Agent 技能注册与调用模块
  - 3.5节新增：编程 Agent 技能注册与调用模块
  - 支持 7 种编程 Agent：Trae、CodeArts、Opencode、Cursor、Claude Code、CodeBuddy、Lingma
  - 定义9 种技能类型：TDD测试用例、code\_generation、test\_creation、code\_review、debugging、refactoring、deployment、integration\_testing、documentation
  - 技能匹配规则：需求分析→TDD测试用例→code\_generation+documentation、测试用例→test\_creation+code\_review、代码编写→code\_generation+code\_review
  - Agent 类型匹配规则：测试用例→claude\_code/trae、代码编写opencode/cursor/claude\_code/codearts/trae/lingma、部署→codearts/codebuddy
  - 任务执行接口：GET /api/tasks/pending、GET /api/tasks/:id、POST /api/tasks/:id/start/progress/deliver/fail
  - 新增 7.7 节：编程 Agent 技能注册与调用验收（32 项验收标准）
- v3.1 (2026-05-18): 需求协同模块改用群聊会议模式
  - 3.1节重构：需求协同从单Agent对话改为多Agent群聊会议模式
  - 项目创建后自动创建需求评审群组（产品经理+架构师+开发者+测试工程师）
  - 需求讨论通过"需求评审会"（requirement\_review）会议类型完成
  - 会议议程模板：PRD整体介绍→业务流程→边界规则→特殊场景→开发提问→疑问答疑→当场确认→记录变更
  - 需求文档基于会议纪要生成，确保多方共识
- v3.0 (2026-05-18): 合并 GroupChat 项目，重构 Agent 发现和通信机制
  - Agent 发现：从 ACP 主动注册改为 Profile 自动扫描
  - 通信协议：从 ACP 改为 Gateway API
  - 新增功能：多 Agent 群聊（讨论模式 + 会议模式）
  - 新增表：groups, group\_messages, meeting\_outcomes, group\_tasks

***

## 1. 引言

### 1.1 目的

本文档定义 DevFlow 项目管理平台的功能需求、非功能需求及系统架构，核心聚焦于“AI 自动化完成软件开发项目”的核心目标，作为开发团队实施和测试验收的依据。

### 1.2 范围

DevFlow 是一个面向人类用户与 AI Agent 协同的自动化软件开发项目管理平台，核心功能包括：项目需求协同确认、AI 任务自动拆解、多专业编程 Agent 任务分配与调度、任务分配与成果验收、项目完成通知。

### 1.3 术语定义

| 术语                    | 定义                                                                                                    |
| --------------------- | ----------------------------------------------------------------------------------------------------- |
| Hermes Agent          | 由 Nous Research 开发的开源 AI 代理（github.com/NousResearch/hermes-agent），负责与人类沟通需求、拆解任务、调度编程 Agent、分配任务及验收成果 |
| Hermes Profile        | Hermes Agent 的配置文件（profile），定义了 Agent 的名称、模型、Gateway 端口等配置信息，存储在用户的 profiles 目录下                      |
| 编程 Agent              | 专业 AI 编程代理，如 trae、codearts、opencode、cursor、claude code、codebuddy、lingma 等，负责执行具体开发任务                  |
| Hermes Gateway        | Hermes Agent 的消息网关模式，通过 `hermes gateway` 启动，提供 REST API + WebSocket 接口供外部系统调用                         |
| Gateway API           | Hermes Gateway 暴露的标准 API 接口，支持流式和非流式响应                                                                |
| MCP                   | Model Context Protocol，模型上下文协议，Hermes Agent 通过 MCP 扩展能力，连接外部工具和服务                                     |
| Profile 扫描            | DevFlow 通过扫描用户 profiles 目录自动发现可用 Hermes Agent 的过程，替代传统的主动注册模式                                         |
| 编程 Agent 技能           | 编程 Agent 能够执行的具体能力，包括 9 种技能类型：TDD 测试用例、代码编写、测试用例编写、代码审查、Bug 修复、代码重构、环境部署、集成测试、文档编写 |
| 技能注册                  | 编程 Agent 向 DevFlow 平台注册自身信息和可用技能的过程                                                                   |
| 技能调用                  | Hermes Agent 向编程 Agent 下发任务，调用其技能执行具体工作的过程                                                            |
| 任务执行接口                | DevFlow 提供给编程 Agent 的标准化接口，用于接收任务、上报进度、交付成果                                                           |
| 群组（Group）             | 由多个 Agent 成员组成的协作单元，支持多 Agent 自主讨论和结构化会议两种工作模式                                                        |
| 讨论模式（Discussion Mode） | 群组的自由工作模式，成员可自主发言、回复消息，支持 @mention 定向沟通                                                               |
| 会议模式（Meeting Mode）    | 群组的结构化工作模式，由主持人（Host Agent）控制议程、分配发言权，产出决议、待办、风险等结构化会议成果                                              |
| 主持人（Host Agent）       | 会议模式下的主导 Agent，负责制定议程、控场、总结会议成果                                                                       |
| **Gitea**               | 轻量级自托管 Git 服务，用于本地代码仓库管理，替代 GitHub/GitLab 等公共代码托管平台                                               |
| **Gitea 本地部署**         | 在本地服务器或开发环境中安装和配置 Gitea 服务，实现私有代码托管                                                             |
| **代码仓库（Repository）**   | Gitea 中存储代码的容器，每个项目对应一个独立的代码仓库                                                                   |
| **分支（Branch）**         | 代码仓库中的并行开发线，支持主分支、开发分支、功能分支等多种分支策略                                                         |
| **Git Flow 分支策略**       | 一种标准化的分支管理策略，包括 master、develop、feature、release、hotfix 五种分支类型                                      |
| **Pull Request（PR）**    | 代码合并请求机制，用于将功能分支的代码合并到主分支或开发分支前进行代码审查                                                |
| **代码提交规范**            | 标准化的 Git 提交消息格式，如 Conventional Commits 规范，便于版本管理和 CHANGELOG 生成                                        |
| **代码成果**               | 编程 Agent 交付的所有可交付代码和文档，包括功能代码、测试用例、配置文件、部署脚本、API 文档等                                        |
| 需求协同                  | Hermes Agent 与人类用户围绕软件开发项目需求进行沟通、确认、迭代的过程                                                             |
| 任务拆解                  | Hermes Agent 按软件开发流程与规范，将整体项目需求拆分为可执行的原子任务                                                            |
| 任务分配                  | Hermes Agent 对拆解后的任务进行分类、存储、分配及进度管控的过程                                                                |
| 成果验收                  | Hermes Agent 对编程 Agent 交付的任务成果进行合规性、完整性、可用性验证的过程                                                      |

***

## 2. 整体描述

### 2.1 产品愿景

为人类用户提供全自动化的软件开发项目管理能力，通过 Hermes Agent 协同确认需求、拆解任务、调度专业编程 Agent 完成从代码编写到部署的全流程工作，降低软件开发门槛，提升项目交付效率。

### 2.2 用户角色

| 角色                                                | 描述               | 权限                                  |
| ------------------------------------------------- | ---------------- | ----------------------------------- |
| 人类用户                                              | 软件开发项目发起者，提出项目需求 | 项目创建、需求沟通、成果验收、查看项目进度、创建群组、参与会议讨论   |
| 项目经理（Hermes Agent）                                | 核心 AI 调度与管理代理    | 需求沟通、任务拆解、Agent 调度、任务分配、成果验收、发送完成通知 |
| 编程 Agent（trae/codearts/opencode/cursor/claude code/codebuddy/lingma） | 专业开发任务执行代理       | 接收任务、执行开发/测试/部署操作、交付任务成果、参与群组讨论     |
| 主持人（Host Agent）                                   | 会议模式下的主导 Agent   | 制定会议议程、控场、分配发言权、总结会议成果、生成待办任务       |
| 系统管理员                                             | 平台运维人员（人类）       | 配置 Agent 能力、监控系统运行状态、管理权限           |

### 2.3 运行环境

-   前端:   现代浏览器 (Chrome 90+, Firefox 88+, Safari 14+)
-   后端:   Linux/Windows/macOS (Docker 部署)
-   数据库:   PostgreSQL 14+, Redis 6+
-   **代码托管:**   本地部署 Gitea（轻量级自托管 Git 服务）
-   AI Agent 交互层:   通过 Hermes Gateway API 与 Hermes Agent 通信
-   Hermes Profiles 路径配置:  
  - Windows: `\\wsl$\{distro}\home\{user}\.hermes`（通过 WSL 路径访问）
  - Linux/macOS: `~/.hermes`
-   Hermes Agent:  
  - Python 3.10+（推荐 3.11）
  - 操作系统：Linux（生产推荐）、macOS、Windows（仅限 WSL2 或 PowerShell Beta）
  - Node.js（部分 gateway 功能需要）
  - 磁盘空间：最低 500MB（不含模型权重），推荐 2GB+
-   **Gitea:**  
  - Go 1.21+（源码安装需要）
  - 数据库：SQLite（默认）或 PostgreSQL 12+ / MySQL 8+
  - Git 2.25+
  - 磁盘空间：最低 1GB，根据代码仓库数量和大小扩展
  - 默认端口：3000（HTTP）、22（SSH，可选）

### 2.4 Hermes Agent 安装

#### 2.4.1 快速安装（推荐）

DevFlow 平台依赖外部 Hermes Agent 实例作为核心调度代理。Hermes Agent 是独立开源软件，需单独安装部署。



Linux / macOS / WSL2（生产推荐）：



```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

### 2.5 Gitea 本地安装部署

DevFlow 平台依赖本地部署的 Gitea 作为代码托管服务，所有项目代码及成果必须提交到 Gitea 代码库。

#### 2.5.1 支持的安装方式

| 安装方式                | 描述                         | 推荐场景                   |
| ------------------- | -------------------------- | ---------------------- |
| **Docker 安装（推荐）**   | 使用官方 Gitea Docker 镜像快速部署 | 生产环境、快速部署、易于维护        |
| **二进制安装**            | 下载官方二进制包直接运行            | 开发环境、小型部署            |
| **源码安装**             | 从源码编译安装                 | 定制化需求、特殊架构           |

#### 2.5.2 Docker 安装（推荐生产配置）

```bash
# 创建数据目录
mkdir -p /data/gitea
mkdir -p /data/git

# Docker Compose 配置示例
cat > docker-compose.yml << 'EOF'
version: "3"

services:
  server:
    image: gitea/gitea:latest
    container_name: gitea
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - GITEA__database__DB_TYPE=postgres
      - GITEA__database__HOST=gitea-db:5432
      - GITEA__database__NAME=gitea
      - GITEA__database__USER=gitea
      - GITEA__database__PASSWD=gitea_db_password
      - GITEA__server__DOMAIN=localhost
      - GITEA__server__HTTP_PORT=3000
      - GITEA__server__ROOT_URL=http://localhost:3000/
    restart: always
    volumes:
      - /data/gitea:/data
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    ports:
      - "3000:3000"
      - "222:22"    # 映射容器内SSH 22到主机222，避免与主机SSH冲突
    depends_on:
      - db
  db:
    image: postgres:14
    container_name: gitea-db
    environment:
      - POSTGRES_USER=gitea
      - POSTGRES_PASSWORD=gitea_db_password
      - POSTGRES_DB=gitea
    volumes:
      - /data/postgres:/var/lib/postgresql/data
    restart: always
EOF

# 启动 Gitea
docker-compose up -d
```

#### 2.5.3 二进制安装（开发环境）

```bash
# 下载 Gitea 二进制文件（以 Linux 为例）
wget -O gitea https://dl.gitea.com/gitea/1.21.0/gitea-1.21.0-linux-amd64
chmod +x gitea

# 创建数据目录
mkdir -p /var/lib/gitea/{custom,data,log}

# 启动 Gitea
./gitea web
```

#### 2.5.4 首次配置（安装向导）

启动 Gitea 后，首次访问 `http://localhost:3000` 进入安装向导，配置以下参数：

| 配置项                | 配置值                                      | 说明                       |
| ------------------- | ---------------------------------------- | ------------------------ |
| **数据库类型**          | SQLite3（默认）或 PostgreSQL/MySQL             | SQLite 适用于小型部署，PostgreSQL 适用于生产 |
| **数据库路径**          | `/data/gitea/gitea.db`（Docker）              | 存储 Gitea 元数据              |
| **站点名称**            | DevFlow Code Repository                  | 代码仓库站点名称                |
| **仓库根目录**          | `/data/git/gitea-repositories`             | 存放 Git 仓库数据               |
| **LFS 根目录**           | `/data/git/lfs`                           | 存储大文件（可选）               |
| **运行用户**            | git（默认）                                | Gitea 运行用户                |
| **SSH 服务端口**         | 22（默认）或 222（Docker）                  | SSH 克隆端口                  |
| **HTTP 端口**           | 3000（默认）                               | Web 访问端口                  |
| **应用 URL**            | `http://localhost:3000`                    | 外部访问地址                  |
| **管理员账号**           | admin（自行设置）                           | 第一个注册用户自动成为管理员           |
| **管理员邮箱**           | admin@devflow.local                       | 管理员邮箱                   |
| **管理员密码**           | 自行设置                                    | 管理员密码                   |

#### 2.5.5 配置 DevFlow 连接 Gitea

Gitea 安装完成后，需要在 DevFlow 中配置 Gitea 连接信息：

```yaml
# DevFlow 配置文件中的 Gitea 配置
gitea:
  host: "localhost"
  port: 3000
  protocol: "http"
  api_token: "gitea_api_token"
  username: "devflow_bot"
  default_org: "devflow"
  default_branch: "main"
```

**配置项说明：**
- `host`: Gitea 服务器地址
- `port`: Gitea HTTP 端口
- `protocol`: HTTP 或 HTTPS
- `api_token`: DevFlow 用于访问 Gitea API 的访问令牌
- `username`: DevFlow 在 Gitea 中的服务账号
- `default_org`: 默认组织名称（所有项目仓库创建在此组织下）
- `default_branch`: 默认分支名称

#### 2.5.6 自动启动配置

**Systemd 服务配置（Linux）：**

```ini
# /etc/systemd/system/gitea.service
[Unit]
Description=Gitea (Git with a cup of tea)
After=syslog.target
After=network.target

[Service]
Type=simple
User=git
Group=git
WorkingDirectory=/var/lib/gitea/
ExecStart=/usr/local/bin/gitea web --config /etc/gitea/app.ini
Restart=always
Environment=USER=git HOME=/home/git

[Install]
WantedBy=multi-user.target
```

**启动命令：**
```bash
sudo systemctl enable gitea
sudo systemctl start gitea
sudo systemctl status gitea
```

### 2.6 Hermes Agent 启动与运行模式

Hermes Agent 支持多种运行模式，DevFlow 平台可对接任意模式下的 Hermes 实例：

#### 2.6.1 CLI/TUI 模式（交互开发用）

```bash
hermes                          # 启动交互式终端 UI
```

启动后进入全功能 TUI 界面，支持多行编辑、斜杠命令自动补全、对话历史、流式工具输出。

#### 2.6.2 Gateway 模式（生产对接用）

Gateway 是 Hermes Agent 的消息网关进程，DevFlow 通过 Gateway 与 Hermes 进行双向通信。

```bash
hermes gateway setup            # 首次配置网关（设置 API Key、平台绑定等）
hermes gateway start            # 启动网关进程
```

Gateway 模式下 Hermes 可以同时对接多个消息平台（飞书、Telegram、Discord、Slack、WhatsApp、Signal），DevFlow 通过 REST API + WebSocket 与 Gateway 通信。

#### 2.6.3 自动启动（推荐生产配置）

建议将 Hermes Gateway 配置为系统服务，确保与 DevFlow 平台的持久连接：

### 2.7 Hermes Agent Profile 自动发现与对接

#### 2.7.1 Profile 自动扫描机制

DevFlow 通过   Profile Scanner   自动发现用户系统中的所有 Hermes Agent，替代传统的主动注册模式。扫描器会遍历用户的 profiles 目录，自动识别所有可用的 Hermes Agent 配置。

| 发现方式             | 机制                                         | 适用场景         |
| ---------------- | ------------------------------------------ | ------------ |
|   Profile 目录扫描   | 定期扫描用户 profiles 目录，自动发现和识别 Hermes Agent 配置 | 主要发现方式，零配置使用 |
|   手动刷新           | 用户可通过 API 触发立即扫描，获取最新 profiles 列表          | 实时同步场景       |
|   状态轮询           | 定期检查各 profile 的 Gateway 运行状态（端口监听检测）       | 在线状态监控       |



Profile 存储路径：



-   Linux/macOS:   遍历`~/.hermes 查找config.yaml`
-   Windows (WSL):   `\\wsl$\{distro}\home\{user}\.hermes`

#### 2.7.2 Profile 信息结构

每个 Profile 目录包含一个配置文件，Profile Scanner 会自动提取以下关键信息：

```json
{
  "name": "architect",
  "model_default": "gpt-4o",
  "model_provider": "openai",
  "gateway_port": 8765,
  "api_key": "sk-xxxxxx",
  "personality": "专业技术架构师，擅长系统设计和性能优化",
  "is_running": true,
  "config_path": "/home/user/.hermes/profiles/architect/config.yaml"
}
```



关键字段说明：



- `name`: Profile 名称（唯一标识）
- `model_default`: 默认使用的 LLM 模型
- `model_provider`: LLM 提供商
- `gateway_port`: Gateway 监听端口（用于 API 通信）
- `is_running`: Gateway 是否正在运行（通过端口检测）

#### 2.7.3 Gateway 健康检查

-   状态检测：   通过检查 Gateway 端口是否监听来判断 Agent 是否在线
-   主动健康检查：   调用 Gateway 的健康检查端点验证服务可用性
-   状态同步：   将扫描到的 profiles 自动同步到 DevFlow 数据库，更新在线/离线状态

#### 2.7.4 Gateway API 通信规范

DevFlow 与 Hermes Agent 之间通过   Gateway API   进行通信：

```
┌─────────────┐    HTTP + WebSocket     ┌──────────────┐
│  DevFlow    │◄───────────────────────►│ Hermes Agent │
│  (调度平台)  │    Gateway API 规范      │ (Gateway模式) │
└─────────────┘                         └──────────────┘
                                                 │
                                                 │
            (支持流式响应 SSE)                     │
                                                 │
                                                 ▼
                               对话消息、任务拆解、多Agent 群组讨论、
                               需求协同、会议主持、结构化会议、自动总结
```



通信特点：



-   流式响应：   支持 Server-Sent Events (SSE) 流式输出
-   并发控制：   通过信号量限制最大并发请求数（默认 5）

#### 2.7.5 多 Profile 支持

DevFlow 支持同时管理多个 Hermes Agent Profiles：

-   自动发现：   扫描所有 profiles，无需手动注册
-   状态隔离：   每个 Profile 维护独立的对话上下文
-   自由组合：   用户可将多个 Profile 组合成群组，实现多 Agent 协作
-   负载均衡：   群组讨论和会议模式下，根据需要分配发言角色

***

## 3. 功能需求

### 3.1 项目需求协同模块 (Requirement Collaboration)



设计变更:

&#x20;需求协同不再是单Agent对话模式，而是通过创建"需求评审群组"，使用群聊的会议模式（需求评审会）来完成结构化的需求讨论。

#### 3.1.1 项目创建与需求评审群初始化

-   功能描述:   人类用户创建软件开发项目，提交初始需求，系统自动创建需求评审群组
-   输入:   项目名称、项目描述、需求文档/原型、技术栈偏好、交付时间要求
-   处理:  
  1. 验证项目信息完整性（必填字段：项目名称、核心需求）
  2. 生成唯一项目 ID，存储项目基础信息
  3. 自动创建需求评审群组（Group），成员包含：
     - 产品经理 Agent（product-manager）- 主持人
     - 技术架构师 Agent（architect）
     - 开发者 Agent（developer）
     - 测试工程师 Agent（qa-engineer）
  4. 将用户初始需求作为会前物料，准备启动需求评审会议
-   输出:   项目创建成功提示，需求评审群组已就绪
-   业务规则:  
  - 项目名称需唯一
  - 支持富文本/Markdown 需求描述，支持附件上传（原型图、需求文档等）
  - 需求评审群组成员基于系统配置的 profiles 自动组合
  - 每个项目对应一个需求评审群组

#### 3.1.2 需求评审会议

-   功能描述:   通过群聊的会议模式（需求评审会类型），多 Agent 协同与人类用户进行结构化需求讨论
-   会议类型:   `requirement_review`（需求评审会）
-   主持人:   产品经理 Agent（product-manager）
-   参会成员:   技术架构师、开发者、测试工程师、人类用户
-   会议议程模板:  
  1.   PRD整体介绍   - 产品经理介绍项目背景和目标
  2.   业务流程   - 梳理核心业务流程和用户路径
  3.   边界规则   - 明确功能边界和非功能需求
  4.   特殊场景   - 讨论异常情况和边缘用例
  5.   开发提问   - 技术团队提出技术可行性问题
  6.   疑问答疑   - 产品经理解答疑问
  7.   当场确认   - 确认是否可排期、是否有变更
  8.   记录变更   - 记录会议中的需求变更点
-   处理:  
  1. 用户启动需求评审会议，选择主持人（默认产品经理）
  2. 主持人开场定调，说明会议目标和产出要求
  3. 主持人根据会议类型生成可执行议程
  4. 按议程逐项讨论，成员按顺序发言，每人限时
  5. 用户可在会议中发送消息干预，主持人可调整议程
  6. 如有争议，主持人当场拍板并标记"拍板后不翻案"
  7. 主持人总结会议，输出结构化会议纪要
-   输出:   结构化会议纪要，包含：
  - 决议结论（拍板了什么/不做什么）
  - 待办任务（责任人+截止时间）
  - 风险点与规避措施
  - 遗留问题（会后小会/下次再议）
-   业务规则:  
  - 会议支持用户实时干预和议程调整
  - 所有讨论内容实时广播到群聊
  - 会议纪要自动持久化到数据库
  - 待办事项自动创建为可跟踪的任务

#### 3.1.3 需求确认与锁定

-   功能描述:   需求评审会议结束后，根据会议纪要生成最终需求文档，人类用户确认后锁定
-   输入:   人类用户的确认指令（点击确认/自然语言确认）
-   处理:  
  1. 系统根据会议纪要整理生成标准化需求文档（PRD）
  2. 需求文档包含：功能清单、技术方案、验收标准、非功能约束
  3. 提交给人类用户确认
  4. 确认后标记需求文档为"已锁定"状态，禁止未授权修改
  5. 记录需求确认时间与版本
  6. 触发任务拆解流程
-   输出:   需求锁定成功提示，任务拆解流程启动
-   业务规则:  
  - 需求文档需基于会议纪要生成，确保多方共识
  - 支持需求文档的多轮迭代修改（可重新召开需求评审会）
  - 锁定后的需求变更需走正式变更流程

### 3.2 任务自动拆解模块 (Task Decomposition)

#### 3.2.1 按开发流程拆解任务

-   功能描述:   Hermes Agent 基于锁定的需求文档，按软件开发规范拆解为原子任务
-   拆解维度（按开发流程）:  
  - 需求分析细化任务
  - 测试用例编写任务
  - 功能模块编码任务
  - 单元/集成测试任务
  - 生产部署环境搭建任务
  - 整体联调任务
-   处理:  
  1. 解析需求文档，识别核心功能模块与技术环节
  2. 按“最小可执行”原则拆解原子任务，定义任务依赖关系
  3. 为每个任务标注执行要求、验收标准
-   输出:   结构化任务清单（含任务 ID、名称、描述、依赖、验收标准、适配 Agent 类型）
-   业务规则:  
  - 任务拆解需遵循软件开发行业规范（如敏捷/瀑布流程适配）
  - 任务间依赖关系需清晰，避免循环依赖
  - 不同类型任务需匹配对应专业能力的编程 Agent

#### 3.2.2 任务优先级与资源匹配

-   功能描述:   Hermes Agent 为拆解后的任务设置优先级，并匹配适配的编程 Agent 类型
-   优先级维度:   核心功能（高）、辅助功能（中）、优化项（低）
-   Agent 匹配规则:  
  - 测试用例编写：优先分配 claude code/codebuddy
  - 功能代码编写：支持 opencode/cursor/claude code/codearts/trae/lingma 按需分配
  - 环境部署：优先分配 cursor/codebuddy
  - 集成测试：优先分配 claude code/trae
-   处理:  
  1. 基于任务类型与优先级生成分配策略
  2. 存储任务优先级与 Agent 匹配信息
-   输出:   带优先级和 Agent 匹配标签的任务清单

### 3.3 代码库管理模块 (Code Repository Management)

DevFlow 平台必须将所有代码及成果提交到本地部署的 Gitea 代码库，实现代码的版本管理、协作开发和成果交付。

#### 3.3.1 项目仓库自动创建

-   功能描述:   项目创建时，系统自动在 Gitea 中创建项目代码仓库
-   触发条件:   需求确认锁定后（见 3.1.3，由人类用户确认锁定即视为审核通过），系统自动触发仓库创建
-   处理:  
  1.  根据项目名称生成仓库名称（规则：项目名小写，空格替换为连字符）
  2.  在配置的默认组织（`devflow`）下创建仓库
  3.  设置仓库为私有（默认），仅项目成员可见
  4.  初始化仓库，创建基础文件：
      -   `README.md` - 项目说明文档
      -   `.gitignore` - Git 忽略规则
      -   `LICENSE` - 许可证（可选，默认 MIT）
      -   项目配置文件（如 `package.json`、`requirements.txt` 等，根据技术栈自动生成）
  5.  设置默认分支为 `main`
  6.  配置分支保护规则（详见 3.3.2）
-   输出:   Gitea 仓库创建成功，返回仓库 URL、SSH/HTTPS 克隆地址
-   业务规则:  
  -   仓库名称在同一组织下唯一
  -   支持自定义仓库名称（需管理员审核）
  -   仓库创建成功后，自动关联项目信息

#### 3.3.2 分支管理（推荐使用 git worktree）

DevFlow 在仓库层面仍采用 Git Flow 的分支模型（如 `main`, `develop`, `feature/*`, `release/*`, `hotfix/*`），但推荐开发者在本地并行工作时使用 `git worktree`，以便在不频繁切换分支的情况下同时在多个分支上并行开发、运行测试或构建。

核心要点：
- 保持远端仓库的分支命名规范（见上文 Git Flow 类型），用于 CI/PR 策略和分支保护。
- 在本地同时工作于多个分支时，用 `git worktree` 创建独立工作目录，每个工作目录对应一个分支，避免频繁 `checkout` 导致的脏工作树和构建缓存冲突。

常用命令示例：

- 从远端检出并为已有分支创建 worktree：

```bash
git fetch origin
git worktree add ../worktrees/feature-123 feature/feature-123
```

- 基于某个分支创建并同时新建本地分支（例如从 `develop` 衍生）：

```bash
git fetch origin
git worktree add -b feature/awesome ../worktrees/feature-awesome origin/develop
```

- 列出当前仓库的所有 worktree：

```bash
git worktree list
```

- 删除并清理某个 worktree（在确保不再使用后）：

```bash
git worktree remove ../worktrees/feature-awesome
git branch -d feature/awesome      # 如需同时删除本地分支
```

- 将本地分支推送到远端并设置上游：

```bash
git push -u origin feature/awesome
```

推荐实践与注意事项：

- 命名规范：Worktree 的目录名建议包含分支类型和编号，例如 `worktrees/feature-123`，便于识别和清理。
- 工作目录位置：不要在原仓库（工作树）内部创建新的 worktree，建议放在仓库外部的 `../worktrees/...` 或专用目录。
- 并发提交：避免在多个 worktree 同时针对同一分支并发提交，可能导致冲突或复杂的历史。每个 worktree 最好对应唯一分支。
- 清理：完成分支合并并确认不再需要本地工作目录时，使用 `git worktree remove` 清理；随后可删除本地分支并推送删除到远端（如需要）。
- CI/PR：Pull Request 流程不受 worktree 影响，仍通过远端分支创建 PR 并在 CI 中运行。
- 链接文件：`git worktree` 会在 `.git/worktrees/` 中登记信息，不要手工删除该目录下文件以免造成仓库损坏。

采用 `git worktree` 能显著提升本地多分支开发效率，尤其适合需要同时运行多个版本的本地构建/测试场景。DevFlow 将在服务端继续使用分支保护、PR 审核与 CI 校验策略以保障代码质量。

#### 3.3.3 代码提交规范

所有代码提交必须遵循约定式提交（Conventional Commits）规范，确保提交历史清晰可读：

**提交消息格式：**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型（type）说明：**

| 类型       | 描述                                   | 示例                                   |
| -------- | ------------------------------------ | ------------------------------------ |
| **feat** | 新功能                                 | `feat(api): 添加用户登录接口`                 |
| **fix**  | Bug 修复                               | `fix(auth): 修复密码重置功能`                 |
| **docs** | 文档更新                                 | `docs: 更新 README`                       |
| **style** | 代码格式调整（不影响功能）                       | `style: 格式化代码`                        |
| **refactor** | 代码重构（非功能变更、非 Bug 修复）                 | `refactor(core): 重构配置加载逻辑`            |
| **test** | 添加或修改测试                             | `test: 添加用户服务单元测试`                   |
| **build** | 构建系统或依赖更新                          | `build: 更新 package.json`                  |
| **ci**   | CI 配置更新                              | `ci: 配置 GitHub Actions`                  |
| **chore** | 其他杂项任务                               | `chore: 更新 .gitignore`                   |

-   功能描述:   系统自动验证代码提交是否符合规范
-   提交验证规则:  
  1.  提交消息必须以类型开头（feat, fix, docs 等）
  2.  类型后可跟作用域（scope），用括号包裹
  3.  类型和作用域后必须跟冒号和空格
  4.  主题（subject）必须简洁明了，不超过 50 字符
  5.  可选的正文（body）用于详细描述变更
  6.  可选的页脚（footer）用于关联 Issue 或标记破坏性变更
-   输出:   提交验证通过或拒绝，拒绝时给出具体错误信息
-   业务规则:  
  -   所有提交必须通过规范验证才能推送
  -   系统自动记录提交信息，用于生成变更日志
  -   支持通过 Git Hooks 在客户端强制执行

#### 3.3.4 Pull Request (PR) 流程

所有代码合并必须通过 Pull Request 流程，确保代码质量和团队协作：

**PR 流程：**

```
1. 创建分支 (feature/*/bugfix/*/hotfix/*)
        ↓
2. 开发编码 + 本地测试
        ↓
3. 推送到远程分支
        ↓
4. 创建 Pull Request
        ↓
5. 代码审查 (Code Review)
        ↓
6. 自动化测试 + 代码质量检查
        ↓
7. 审批通过 (至少 1 个审批人)
        ↓
8. 合并到目标分支
        ↓
9. 删除源分支 (自动)
```

**PR 创建要求：**
-   标题：简洁描述变更内容
-   描述：
  -   变更原因和背景
  -   具体实现方案
  -   测试方法和结果
  -   相关 Issue（如有）
-   标签：添加适当标签（bug, enhancement, documentation 等）
-   审核人：指定至少 1 个审核人

**PR 检查清单：**
-   [ ] 代码编译/构建通过
-   [ ] 所有测试用例通过
-   [ ] 代码符合提交规范
-   [ ] 已添加/更新相关文档
-   [ ] 无敏感信息泄露（密钥、密码等）
-   [ ] 代码审查通过

-   功能描述:   系统自动管理 PR 生命周期，确保代码合并质量
-   处理:  
  1.  自动检测源分支和目标分支的兼容性
  2.  自动触发 CI/CD 流水线（如已配置）
  3.  自动检查代码冲突
  4.  自动分配审核人（基于项目配置）
  5.  自动检查 PR 描述完整性
  6.  合并后自动删除源分支
-   输出:   PR 状态变更通知，合并成功提示
-   业务规则:  
  -   PR 必须通过所有检查才能合并
  -   至少需要 1 个审核人审批通过
  -   代码冲突必须手动解决

#### 3.3.5 代码成果提交要求

DevFlow 平台要求所有代码及成果必须提交到 Gitea 代码库：

**必须提交的内容：**
-   全部源代码（包括前端、后端、配置文件等）
-   测试代码（单元测试、集成测试、E2E 测试）
-   项目文档（README、API 文档、部署文档等）
-   构建配置文件（package.json、requirements.txt、Dockerfile 等）
-   CI/CD 配置文件
-   数据库迁移脚本
-   设计文档（如适用）

**提交时机：**
| 阶段               | 提交内容                            | 目标分支   |
| ---------------- | ------------------------------- | ------ |
| 功能开发完成         | 功能代码 + 单元测试                    | feature/* |
| 功能开发联调通过       | 完整功能代码 + 集成测试                   | develop（通过 PR） |
| 发布准备完成         | 生产就绪代码 + 发布文档                    | release/* |
| 生产发布            | 稳定版本代码                          | main（通过 PR） |
| 紧急修复完成         | 修复代码 + 验证测试                      | main（通过 hotfix PR） |

**提交验证：**
-   系统自动检查提交内容完整性
-   系统自动关联提交与任务（通过提交消息中的任务 ID）
-   系统自动记录提交历史，用于项目进度追踪

-   功能描述:   确保所有项目成果完整提交到代码库
-   处理:  
  1.  任务完成时，提示开发者提交代码
  2.  自动检查是否所有关联文件已提交
  3.  自动生成提交消息（如开发者未提供）
  4.  推送代码到 Gitea
  5.  记录提交信息到项目数据库
-   输出:   代码提交成功通知，提交信息已记录
-   业务规则:  
  -   未提交代码的任务不能标记为完成
  -   提交信息必须与任务关联（通过任务 ID 或其他标识）
  -   所有提交必须符合提交规范

### 3.4 Hermes Agent 管理模块 (Hermes Agent Management)

#### 3.4.1 Hermes Agent 安装部署

-   功能描述:   支持通过标准安装流程将 Hermes Agent 部署到目标环境
-   支持的部署方式:  
  -   一键脚本安装 (推荐):   Linux/macOS 使用 `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash`
-   安装验证:  
  - `hermes doctor` 命令诊断安装完整性，检查 Python、Node.js、系统依赖是否完备
-   输出:   Hermes Agent 成功安装并可正常启动

#### 3.4.2 Hermes Agent 启动与运行

-   功能描述:   支持以多种模式启动 Hermes Agent，满足不同使用场景
-   启动模式:  
  -   Gateway 模式:   执行 `hermes gateway start` 启动消息网关进程，适用于生产环境与 DevFlow 对接
-   持久化运行:  
  - 支持注册为系统服务（systemd）实现开机自启和崩溃自动恢复
  - Gateway 模式下支持多消息平台同时在线（飞书、Telegram、Discord、Slack、WhatsApp、Signal）
-   输入:   Hermes Agent 安装路径及配置参数
-   输出:   Hermes Agent 进程正常运行，可接收指令

#### 3.4.3 Hermes Agent Profile 自动发现

-   功能描述:   DevFlow 通过 Profile Scanner 自动发现用户系统中的所有 Hermes Agent，无需手动注册
-   发现机制:  
  -   目录扫描:   自动遍历用户 profiles 目录（`~/.hermes` 或 WSL 路径）
  -   配置解析:   读取每个 profile 的 `config.yaml `，提取名称、模型、Gateway 端口等信息
  -   状态检测:   通过检查 Gateway 端口监听状态判断 Agent 是否在线
-   Profile 信息提取:  
  - 基本信息：profile 名称、模型配置、Gateway 端口
  - 运行状态：Gateway 是否运行、配置文件是否加载
  - 扩展信息：personality（角色设定）、API Key 等
-   处理:  
  1. Profile Scanner 扫描 profiles 目录
  2. 解析每个 profile 的配置文件
  3. 检测 Gateway 运行状态
  4. 返回结构化 ProfileInfo 列表
-   输出:   自动发现的 Hermes Agent 列表，含在线状态和配置详情

#### 3.4.4 Profile 同步到数据库

-   功能描述:   将扫描到的 profiles 自动同步到 DevFlow 数据库，便于管理和使用
-   同步规则:  
  -   新增 profile:   数据库中不存在的 profile，自动创建 Agent 记录
  -   更新 profile:   已存在的 profile，更新在线状态和配置信息
  -   状态同步:   Gateway 在线的标记为 `online`，离线的标记为 `offline`
-   同步内容:  
  - Agent 名称（来自 profile 名称）
  - Agent 类型：固定为 `hermes`
  - API 端点：`http://localhost:{gateway_port}`
  - 配置：模型信息、Gateway 端口、personality 等
-   处理:  
  1. 获取所有扫描到的 profiles
  2. 遍历每个 profile，检查数据库中是否存在
  3. 新增或更新 Agent 记录
  4. 提交数据库事务
-   输出:   同步统计（发现数量、新增数量、更新数量）

#### 3.4.5 Gateway API 通信

-   功能描述:   通过 Gateway API 与 Hermes Agent 进行对话通信，支持流式和非流式响应
-   支持的消息类型:  
  -   单轮对话:   一次性发送消息并获取完整响应
  -   流式对话:   逐字返回响应内容（SSE 格式）
  -   多轮对话:   携带历史消息上下文
-   并发控制:  
  - 信号量限制最大并发数（默认 5）
  - 请求超时控制（默认 360 秒）
-   输出:   Agent 的文本响应（流式输出时为逐块返回）

### 3.5 多 Agent 群聊与协作模块 (Multi-Agent Group Chat & Collaboration)

#### 3.5.1 群组管理

-   功能描述:   创建和管理由多个 Hermes Agent 组成的协作群组
-   群组属性:  
  -   基本信息:   群组名称、描述、创建时间
  -   成员列表:   包含的 Hermes Agent profile 名称列表
  -   工作模式:   `discussion`（讨论模式）或 `meeting`（会议模式）
  -   主持人:   会议模式下的 Host Agent
-   支持的操作:  
  -   创建群组:   指定名称、描述、初始成员
  -   查看群组:   获取群组详情和成员列表
  -   修改群组:   更新名称、描述、成员、主持人
  -   删除群组:   删除群组及其相关数据（级联删除消息、任务等）
  -   成员管理:   添加/移除成员，设置主持人
-   业务规则:  
  - 群组名称可重复，通过群组 ID（系统自动生成）唯一标识
  - 成员必须是已发现的 Hermes Agent profiles
  - 会议模式必须设置主持人
-   输出:   群组信息（含 ID、成员、模式、主持人）

#### 3.5.2 讨论模式 (Discussion Mode)

-   功能描述:   群组的自由工作模式，成员可自主发言、回复消息
-   消息发送:  
  - 用户发送消息到群组
  - 支持 `@profile_name` 定向提及特定 Agent
  - 未提及 Agent 时，所有成员都会收到消息并回复
-   自动回复机制:  
  - 检测消息中的 @mention
  - 确定目标回复 Agent（被提及的或所有成员）
  - 获取最近 10 条消息作为上下文
  - 调用 Gateway API 获取各 Agent 的响应
  - 流式输出响应内容到前端
-   消息存储:  
  - 所有消息持久化到数据库
  - 记录发送者、角色、内容、时间戳
  - 支持元数据（如消息类型、状态）
-   输出:   实时消息推送（WebSocket）、历史消息查询

#### 3.5.3 会议模式 (Meeting Mode)

-   功能描述:   群组的结构化工作模式，由主持人控制议程，产出结构化会议成果
-   会议类型（支持多种模板）:  
  -   需求评审会 (requirement\_review):   PRD整体介绍→业务流程→边界规则→特殊场景→开发提问→当场确认
  -   技术方案讨论会 (tech\_solution):   背景目标→现有问题→备选方案对比→架构接口→敲定方案→拆分任务
  -   每日站会 (daily\_standup):   每人3句话（昨天/今天/阻塞），15分钟，阻塞当场协调
  -   故障复盘会 (incident\_postmortem):   时间线→影响面→根因→修复措施→预防改进
-   会议流程:  
  1.   开场定调:   主持人介绍会议目标、产出要求、会议规则
  2.   制订议程:   主持人根据会议类型生成可执行的会议议程（3-6项）
  3.   按议程讨论:  
     - 每项议程主持人先介绍目标
     - 按顺序邀请各成员发言（每人限时）
     - 主持人控场，防止偏离主题
     - 如有争议，主持人拍板并标记"拍板后不翻案"
  4.   会议总结:   主持人输出结构化会议纪要
-   会议规则（默认）:  
  - 聚焦议题，不跑偏；不聊无关内容
  - 不临时加议题；细节争论标记为会后小会再对齐
  - 发言简明，每人限时；争议无共识由负责人当场拍板
  - 结论当场记录：决议 / 待办+责任人+截止时间 / 风险及规避 / 遗留问题
-   用户干预:  
  - 会议进行中用户可发送消息干预
  - 主持人处理用户请求，可调整议程
-   输出:   会议纪要、决议、待办任务、风险点、遗留问题

#### 3.5.4 会议结果与任务管理

-   功能描述:   自动保存会议成果，创建待办任务并分配责任人
-   会议结果存储:  
  -   MeetingOutcome:   存储会议主题、主持人、时间、纪要、决议、待办、风险、遗留问题
  -   GroupTask:   将待办事项转换为可跟踪的任务，插入到dashboard进行追踪
-   任务创建规则:  
  - 从会议纪要的 JSON 结构化数据自动提取待办
  - 每个任务包含：描述、责任人、截止时间、关联会议ID
  - 任务状态：`pending`（待执行）、`in_progress`（进行中）、`completed`（已完成）
-   任务管理操作:  
  - 查看待办任务（按责任人筛选）
  - 更新任务状态和执行结果
  - 标记任务完成
-   会后通知:  
  - 会议结束后，自动创建任务并通知责任人
  - 在群组中发送任务分配公告
  - 触发相关 Agent 确认和执行
-   输出:   结构化会议结果、可跟踪的待办任务清单

### 3.6 编程 Agent 技能注册与调用模块 (Coding Agent Skills Registration & Invocation)



设计说明:

&#x20;Hermes Agent 通过 DevFlow 平台调度和调用各类编程 Agent 的技能，完成从代码编写到部署的全流程开发工作。

#### 3.6.1 支持的编程 Agent 类型

DevFlow 支持对接多种主流 AI 编程代理，每种 Agent 具备不同的技能专长：

| 编程 Agent        | 主要特点                      | 推荐应用场景             |
| --------------- | ------------------------- | ------------------ |
|   Trae          | 字节出品的AI 代码助手，LLM免费        | 企业级项目开发、云原生应用部署    |
|   CodeArts      | 华为云 CodeArts IDE 内置 AI 代理 | 代码生成、重构、测试用例编写     |
|   Opencode      | 开源 AI 代码代理，支持本地运行         | 小型项目、原型开发、快速迭代     |
|   Cursor        | 基于 VS Code 的 AI 编程编辑器     | 前端开发、代码重构、实时代码补全   |
|   Claude Code   | Anthropic 官方 AI 编程代理      | 复杂逻辑实现、测试驱动开发、代码审查 |
|   CodeBuddy     | 腾讯出品的轻量级 AI 代码助手          | 代码片段生成、快速问题解决、学习辅助 |
|   Lingma        | 阿里云灵码 AI 编程代理             | 阿里云生态项目、中文项目开发     |

#### 3.6.2 编程 Agent 技能注册

-   功能描述:   编程 Agent 向 DevFlow 平台注册自身信息和可用技能，Hermes Agent 负责检查各编程 Agent 的状态并灵活安排任务。注意：Hermes Agent 的发现采用 Profile 自动扫描机制（见 2.7 节），无需主动注册；此处仅针对编程 Agent 的技能注册
-   注册方式:  
  -   API 主动注册:   编程 Agent 启动时调用 `POST /api/agents/register` 上报自身信息
  -   配置文件注册:   在 DevFlow 配置文件中静态声明编程 Agent 的 API 端点和技能
  -   手动注册:   用户通过管理界面手动添加编程 Agent
-   注册信息结构:  
  ```json
  {
    "name": "opencode-dev-01",
    "agent_type": "opencode",
    "api_endpoint": "http://192.168.1.100:3000",
    "status": "online",
    "config": {
      "version": "1.0.0",
      "skills": [
        "code_generation",
        "code_review",
        "test_creation",
        "debugging"
      ],
      "capabilities": {
        "languages": ["python", "javascript", "typescript", "go"],
        "frameworks": ["fastapi", "react", "vue"],
        "max_concurrent_tasks": 3
      },
      "workspace_path": "/workspace/project"
    },
    "capabilities": {
      "code_generation": true,
      "test_creation": true,
      "debugging": true,
      "deployment": false
    }
  }
  ```
-   技能类型定义:  
  - `tdd_test`: TDD 测试用例编写（测试驱动开发）
  - `code_generation`: 功能代码生成
  - `test_creation`: 测试用例编写
  - `code_review`: 代码审查
  - `debugging`: Bug 修复
  - `refactoring`: 代码重构
  - `deployment`: 环境部署
  - `integration_testing`: 集成测试
  - `documentation`: 文档编写
-   处理:  
  1. 编程 Agent 发送注册请求到 DevFlow
  2. DevFlow 验证 Agent 信息完整性，分配唯一 ID
  3. 注册中心返回确认，Agent 开始定期发送心跳
  4. 其他客户端可通过注册中心查询可用 Agent 和技能
-   输出:   Agent 注册成功，注册中心维护其在线状态和技能清单
-   业务规则:  
  - 编程 Agent 必须注册至少一种技能
  - 支持动态更新技能列表（Agent 运行时变更）
  - 离线 Agent 自动从可用列表中移除

#### 3.6.3 编程 Agent 技能调用机制

-   功能描述:   Hermes Agent 从 DevFlow 平台接收任务，根据技能匹配规则选择编程 Agent，并调用其技能执行具体任务
-   技能匹配规则:  
  - 需求分析细化：`tdd_test` + `code_generation` + `documentation`
  - 测试用例编写：`test_creation` + `code_review`
  - 功能代码编写：`code_generation` + `code_review`
  - 单元/集成测试：`test_creation` + `debugging`
  - 环境部署：`deployment` + `code_generation`
  - 整体联调：`debugging` + `integration_testing`
-   Agent 类型匹配规则:  
  - 测试用例编写：优先分配 `claude_code`、`codebuddy`
  - 功能代码编写：支持 `opencode`、`cursor`、`claude_code`、`codearts`、`trae`、`lingma`
  - 环境部署：优先分配 `cursor`、`codebuddy`
  - 集成测试：优先分配 `claude_code`、`trae`
-   调用流程:  
  1. Hermes Agent 确定需要执行的任务类型
  2. 根据 Agent 负载和优先级选择最优 Agent
  3. 通过任务执行接口向编程 Agent 下发任务
  4. 实时监控任务执行进度
  5. 接收任务执行结果，触发验收流程
-   任务下发格式:  
  ```json
  {
    "task_id": "task-001",
    "task_type": "code_generation",
    "title": "实现用户认证模块",
    "description": "实现用户登录、注册、权限验证功能",
    "requirements": "支持 JWT Token 认证、邮箱验证、密码重置",
    "acceptance_criteria": "代码覆盖率 > 80%，通过所有单元测试",
    "deadline": "2026-05-20T18:00:00Z",
    "context": {
      "project_id": "proj-001",
      "language": "python",
      "framework": "fastapi",
      "workspace_path": "/workspace/project"
    }
  }
  ```
-   输出:   任务分配成功提示，编程 Agent 接收任务并开始执行
-   业务规则:  
  - 任务必须拆解到足够细，任务的验收标准必须明确且可验证
  - 若目标 Agent 负载过高，自动调整分配策略
  - 有依赖的前后两个任务必须分配给不同的 Agent
  - 前后两个任务必须达到验收标准，并进行验证后才能进行交接，否则退回重做

#### 3.6.4 任务执行接口（编程 Agent 视角）

-   功能描述:   DevFlow 提供标准化接口，供编程 Agent 查询任务、上报进度、交付成果
-   接口列表:  
  - `GET /api/tasks/pending`: 查询待执行的任务列表
  - `GET /api/tasks/:id`: 获取任务详情
  - `POST /api/tasks/:id/start`: 标记任务开始执行
  - `POST /api/tasks/:id/progress`: 上报任务执行进度
  - `POST /api/tasks/:id/deliver`: 交付任务执行成果
  - `POST /api/tasks/:id/fail`: 上报任务执行失败
-   进度上报格式:  
  ```json
  {
    "task_id": "task-001",
    "progress": 65,
    "status": "running",
    "message": "正在实现数据库模型层",
    "logs": [
      "2026-05-18 10:00:00 - 开始分析需求",
      "2026-05-18 10:05:00 - 创建项目结构",
      "2026-05-18 10:15:00 - 实现数据模型"
    ]
  }
  ```
-   成果交付格式:  
  ```json
  {
    "task_id": "task-001",
    "status": "delivered",
    "result_summary": "用户认证模块实现完成",
    "artifacts": {
      "code_files": [
        "app/models/user.py",
        "app/routes/auth.py",
        "app/services/auth_service.py"
      ],
      "test_files": [
        "tests/test_auth.py"
      ],
      "documentation": "docs/auth-module.md"
    },
    "test_results": {
      "total": 15,
      "passed": 15,
      "failed": 0,
      "coverage": "85%"
    },
    "execution_log": "完整的执行日志..."
  }
  ```
-   处理:  
  1. Hermes Agent 通过接口拉取待执行任务，并转发给合适的编程 Agent
  2. 编程 Agent开始执行任务，定期上报进度
  3. 完成后交付成果（代码、测试、文档等）
  4. Hermes Agent接收成果并触发验收流程
  5. 验收通过，将本任务标记为已完成
-   输出:   任务状态更新，验收流程启动

#### 3.6.5 任务分配与进度监控

-   功能描述:   DevFlow 对所有任务进行统一仓储管理，实时监控执行进度
-   分配管理内容:  
  - 任务状态跟踪（待分配/已分配/执行中/已交付/验收通过/验收驳回）
  - 任务成果暂存（代码片段、测试报告、部署配置等）
  - 编程 Agent 执行日志收集
-   进度监控处理:  
  1. 实时接收编程 Agent 任务执行进度上报
  2. 对超时未交付的任务触发提醒（向对应编程 Agent 发送催办指令）
  3. 向人类用户展示可视化的任务进度看板
-   任务状态流转:  
  ```
  pending → assigned → running → delivered → accepted
                        ↓               ↓
                     failed → reassigned → running
                                        ↓
                                 rejected → reassigned
  ```
-   输出:   实时更新的任务进度看板，超时任务提醒

#### 3.6.6 任务依赖联动

-   功能描述:   基于任务依赖关系，控制编程 Agent 任务执行顺序
-   触发条件:   前置任务完成并验收通过
-   处理:  
  1. 检测前置任务状态变更
  2. 自动向下游编程 Agent 下发任务执行指令
  3. 记录依赖联动日志
-   依赖关系示例:  
  - 需求分析细化 → 测试用例编写 → 功能模块编码 → 单元/集成测试
  - 生产部署环境搭建（可并行）
  - 整体联调（依赖编码、测试、环境部署）
-   输出:   下游任务状态更新为"可执行"，并触发分配/执行流程

### 3.7 成果验收模块 (Result Acceptance)

#### 3.7.1 任务成果自动验收

-   功能描述:   Hermes Agent 对编程 Agent 交付的任务成果进行自动化验收
-   验收维度:  
  - 测试用例：覆盖度、有效性、规范性
  - 功能代码：语法正确性、需求匹配度、无明显漏洞
  - 测试报告：完整性、问题记录清晰性
  - 部署环境：可用性、合规性、可访问性
-   处理:  
  1. 拉取编程 Agent 交付的成果文件，与验收标准一一比对
  2. 按验收标准自动校验（调用代码检测工具、环境验证脚本等），验收通过才允许交接，否则，退回去重做
  3. 前后两个任务，必须是两个不同的Agent
  4. 生成验收报告（通过/驳回+问题明细）
-   输出:   验收结果通知（发送给对应编程 Agent），验收报告存储
-   业务规则:  
  - 验收驳回的任务需附带明确的修改建议
  - 编程 Agent 需在指定时限内完成修改并重新提交

#### 3.7.2 全项目成果汇总与最终验收

-   功能描述:   所有任务验收通过后，Hermes Agent 汇总全项目成果，发起最终验收
-   汇总内容:   代码仓库、测试报告、部署文档、运行演示链接等
-   处理:  
  1. 验证所有任务均验收通过，无未完成/驳回任务
  2. 打包汇总项目成果，生成项目交付报告
  3. 向人类用户发起最终验收请求
-   输出:   项目交付报告，人类用户验收入口

### 3.8 通知与交付模块 (Notification & Delivery)

#### 3.8.1 项目进度通知

-   功能描述:   向人类用户推送关键节点进度通知
-   通知节点:   需求确认完成、任务拆解完成、核心任务交付、验收驳回、整体进度过半
-   通知方式:   平台内消息、邮件、短信（可选）
-   处理:  
  1. 监控关键节点状态变更
  2. 生成标准化通知内容，推送至人类用户指定渠道
-   输出:   结构化进度通知，支持查看详情

#### 3.8.2 项目完成通知

-   功能描述:   项目最终验收通过后，Hermes Agent 向人类用户发送完成通知
-   通知内容:   项目完成状态、成果下载/访问链接、交付报告链接、售后支持说明
-   处理:  
  1. 检测人类用户最终验收确认指令
  2. 生成完成通知，触发多渠道推送
  3. 标记项目状态为"已完成"
-   输出:   项目完成通知，项目状态更新

***

## 4. 非功能需求

### 4.1 性能要求

| 指标                  | 目标值           |
| ------------------- | ------------- |
| 页面加载时间              | < 2 秒         |
| Hermes Agent 需求响应时间 | < 3 秒         |
| 编程 Agent 任务分配响应时间   | < 500 毫秒      |
| 任务验收自动化处理时间         | 单任务 < 1 分钟    |
| 并发项目数               | 支持 20 个项目同时执行 |
| 数据库查询响应             | < 100 毫秒      |

### 4.2 安全要求

- 用户认证: JWT Token 认证
- 授权控制: 基于角色的访问控制 (RBAC)，人类用户仅可查看/操作自身发起的项目
- 数据加密: HTTPS 传输加密，Agent 交互数据脱敏存储
- 成果安全: 项目代码/成果仅对人类用户和授权 Agent 可见
- 日志审计: 记录所有 Agent 交互、任务分配、验收操作日志

### 4.3 可用性要求

- 系统可用性: 99.5%
- 数据备份: 项目需求、任务信息、成果文件每日自动备份
- 容错机制: 编程 Agent 执行失败时，Hermes Agent 自动重试或切换备用 Agent
- 错误处理: 关键流程失败时提供明确的错误提示和人工介入入口

### 4.4 可扩展性要求

- API接口 设计遵循 RESTful 规范，支持新增编程 Agent 类型的快速接入
- 任务拆解规则支持配置化扩展（适配不同开发流程）
- 验收标准支持自定义扩展（适配不同技术栈/行业规范）
- 前端组件化设计，支持功能模块快速迭代

***

## 5. 系统架构

### 5.1 技术栈

| 层            | 技术                                                                                            |
| ------------ | --------------------------------------------------------------------------------------------- |
| 前端           | Vue 3 + Element Plus + 实时通信组件                                                                 |
| 后端           | Python FastAPI接口 + Celery（任务调度）+ asyncio（异步并发控制）                                              |
| 数据库          | PostgreSQL + Redis（缓存/状态存储）                                                                   |
| **代码托管层**      | **Gitea（本地部署的自托管 Git 服务）**                                                                |
| AI Agent 交互层 | Gateway Client（ 兼容）、Profile Scanner、Conversation Coordinator（多Agent协调） |
| 群聊协作层        | WebSocket 实时通信、Connection Manager（连接管理）、Meeting State（会议状态管理）                                 |
| Hermes Agent | 独立部署的开源 AI 代理（NousResearch/hermes-agent），通过 Gateway 模式提供 REST API                             |
| 部署           | Docker + Docker Compose                                                                       |

### 5.2 架构图

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                           人类用户 (Client)                                    │
│              浏览器 / 移动端 (需求提交/进度查看/群组聊天/会议参与)                │
└───────────────────────────────────┬───────────────────────────────────────────┘
                                    │ HTTP / WebSocket
┌───────────────────────────────────▼───────────────────────────────────────────┐
│                            Nginx (反向代理)                                     │
└───────────────────────────────────┬───────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼───────────────────────────────────────────┐
│                      FastAPI 后端 (DevFlow Server)                             │
│  ┌──────────┬─────────────┬────────────┬───────────────────┬───────────────┐ │
│  │ Auth     │ 需求协同    │ 任务拆解   │ Profile 扫描      │ 群组管理      │ │
│  └──────────┴─────────────┴────────────┴───────────────────┴───────────────┘ │
│  ┌──────────┬─────────────┬────────────┬───────────────────┬───────────────┐ │
│  │ 任务分配 │ 成果验收    │ 通知管理   │ Gateway Client    │ 会议协调      │ │
│  │          │             │            │ (OpenAI兼容)      │ (主持人/议程)  │ │
│  └──────────┴─────────────┴────────────┴───────────────────┴───────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  Gitea 集成: 代码仓库创建、分支管理、PR 流程、提交规范校验                   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  WebSocket 层: Connection Manager (连接管理) + 实时消息广播               │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                          │
└────────────────────────────────────┼──────────────────────────────────────────┘
               Gitea REST API         │                      │ Gateway API 
┌──────────────────────────────────▼───┐                  │ POST /v1/chat/completions (支持流式SSE)
│       Gitea 代码托管层 (本地部署)     │                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  代码仓库管理: 项目仓库自动创建、分支保护、PR 审核、提交规范校验         │ │
│  │  Git Flow 分支策略: main/develop/feature/release/hotfix              │ │
│  │  集成: 自动触发构建/测试、代码质量检查                                 │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐            │
│  │ project-1        │  │ project-2        │  │ project-3      │            │
│  │ (项目1仓库)   │  │ (项目2仓库)   │  │ (项目3仓库)   │            │
│  │ 分支: main/develop │  │ 分支: main/develop │  │ 分支: main/develop │            │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘            │
└───────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                    Hermes Profiles (用户本地 Agent 配置)                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐            │
│  │ architect        │  │ developer        │  │ qa-engineer      │            │
│  │ (架构师 Agent)   │  │ (开发 Agent)     │  │ (测试 Agent)     │            │
│  │ Gateway:8765     │  │ Gateway:8766     │  │ Gateway:8767     │            │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘            │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  Profiles 目录: ~/.hermes (自动扫描发现)                        │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────┐
│                              多 Agent 协作层                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  Conversation Coordinator: 管理讨论模式和会议模式                          │ │
│  │  - Discussion Mode: 自由讨论、@mention、自动回复                          │ │
│  │  - Meeting Mode: 议程驱动、主持人控场、决议/待办/风险产出                 │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  Meeting State: 会议状态管理                                              │ │
│  │  - 活动会议列表、当前发言人、议程进度、历史记录                            │ │
│  │  - 会议结果解析 (决议/待办/风险/遗留问题)                                  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────┐
│                              数据库层 (PostgreSQL)                               │
│  ┌───────────┬───────────┬──────────────┬───────────────────┬───────────────┐ │
│  │ users     │ projects  │ requirements │ agents (Profiles  │ tasks         │ │
│  │           │           │              │  自动同步)        │               │ │
│  └───────────┴───────────┴──────────────┴───────────────────┴───────────────┘ │
│  ┌───────────┬───────────────────┬───────────────────┬───────────────────────┐ │
│  │ groups    │ group_messages    │ meeting_outcomes  │ group_tasks           │ │
│  │ (群组)    │ (群聊消息)        │ (会议结果)        │ (群组任务)            │ │
│  └───────────┴───────────────────┴───────────────────┴───────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  repos: 代码仓库元数据、分支状态、PR 状态、提交记录                          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 数据库设计概要

#### 核心表

1.   users   - 人类用户表
   - id, username, email, password\_hash, role, created\_at
2.   projects   - 项目表
   - id, name, description, creator\_id, requirement\_doc, status, created\_at, completed\_at
3.   requirements   - 需求表
   - id, project\_id, content, version, is\_locked, confirmed\_at
4.   tasks   - 任务表
   - id, project\_id, name, description, type, priority, agent\_type, assignee\_agent, status, acceptance\_criteria, created\_at, completed\_at
5.   task\_dependencies   - 任务依赖表
   - id, source\_task\_id, target\_task\_id, created\_at
6.   agents   - Agent 注册表（Profile 自动同步）
   - id, name (唯一), agent\_type (hermes/trae/codearts/opencode/cursor/claude\_code/codebuddy/lingma), status (online/offline/busy), api\_endpoint, config (JSON, 含 gateway\_port, model, personality 等), created\_at
7.   agent\_execution\_logs   - Agent 执行日志表
   - id, task\_id, agent\_type, agent\_id, execution\_content, result, created\_at
8.   acceptance\_records   - 验收记录表
   - id, task\_id, acceptance\_result, problem\_details, reviewer (Hermes Agent), created\_at
9.   notifications   - 通知表
   - id, user\_id, project\_id, content, type, is\_read, created\_at
10.   agent\_heartbeats   - Agent 心跳记录表
    - id, agent\_id, heartbeat\_at, load\_level (当前负载), status\_detail (JSON)

#### 代码仓库相关表（新增）

1.   repos   - 代码仓库表
    - id, project\_id, gitea\_repo\_id, name, url, ssh\_url, http\_url, default\_branch, is\_private, created\_at, updated\_at
2.   repo\_branches   - 代码仓库分支表
    - id, repo\_id, name, commit\_sha, is\_protected, created\_at, updated\_at
3.   pull\_requests   - Pull Request 表
    - id, repo\_id, number, title, description, source\_branch, target\_branch, author, status (open/closed/merged), created\_at, updated\_at, merged\_at
4.   commits   - 代码提交记录表
    - id, repo\_id, sha, message, author, author\_email, committer, committer\_email, created\_at
5.   task\_commits   - 任务与提交关联表
    - id, task\_id, commit\_id, created\_at

#### 群聊与会议相关表（新增）

1.   groups   - 群组表
   - id, name, description, members (JSON 数组), host\_agent, mode (discussion/meeting), created\_at
2.   group\_messages   - 群聊消息表
   - id, group\_id, sender, role (user/assistant/system), content, timestamp, is\_streaming, metadata (JSON)
3.   meeting\_outcomes   - 会议结果表
   - id, group\_id, meeting\_topic, host\_agent, started\_at, ended\_at, minutes, decisions (JSON), todos (JSON), risks (JSON), open\_issues (JSON)
4.   group\_tasks   - 群组待办任务表（来自会议决议）
   - id, group\_id, meeting\_id (外键), assignee, description, deadline, status (pending/in\_progress/completed), created\_at, completed\_at, result

***

## 6. 接口需求

### 6.1 API接口 端点 (RESTful)

#### 6.1.1 用户与项目管理

| 方法   | 路径                                     | 描述          |
| ---- | -------------------------------------- | ----------- |
| POST | /api/auth/login                        | 人类用户登录      |
| POST | /api/projects                          | 人类用户创建项目    |
| PUT  | /api/projects/:id/requirements         | 提交/更新项目需求   |
| POST | /api/projects/:id/requirements/confirm | 人类用户确认需求    |
| GET  | /api/projects/:id/tasks                | 获取项目任务清单    |
| GET  | /api/projects/:id/notification         | 获取项目通知列表    |
| POST | /api/projects/:id/complete             | 确认项目完成并发送通知 |

#### 6.1.2 Hermes Agent Profile 扫描与同步

| 方法     | 路径                                  | 描述                                    |
| ------ | ----------------------------------- | ------------------------------------- |
| GET    | /api/profiles                       | 获取所有扫描到的 Hermes Agent Profiles 列表     |
| GET    | /api/profiles/:profile\_name        | 获取单个 Profile 的详细信息                    |
| GET    | /api/profiles/:profile\_name/status | 检查指定 Profile 的 Gateway 运行状态           |
| GET    | /api/agents/discover                | 自动发现所有 Hermes Agent profiles（替代手动注册）  |
| POST   | /api/agents/sync-hermes             | 同步发现的 profiles 到数据库（自动创建/更新 Agent 记录） |
| GET    | /api/agents                         | 获取所有注册 Agent 列表（含自动同步的）               |
| GET    | /api/agents/:id                     | 获取指定 Agent 的详情                        |
| DELETE | /api/agents/:id                     | 移除已注册的 Agent                          |

#### 6.1.3 Gateway 通信与对话

| 方法   | 路径                      | 描述                                   |
| ---- | ----------------------- | ------------------------------------ |
| GET  | /api/hermes/health      | 检查 Hermes Gateway 健康状态（支持指定 profile） |
| GET  | /api/hermes/profiles    | 获取所有可用的 Hermes profiles              |
| GET  | /api/hermes/chat/intro  | 开始新对话，获取 Agent 自我介绍                  |
| POST | /api/hermes/chat        | 与指定 Hermes Agent 对话（非流式响应）           |
| POST | /api/hermes/chat/stream | 与 Hermes Agent 对话（流式响应）              |
| POST | /api/hermes/decompose   | 使用 Hermes Agent 拆解任务                 |

#### 6.1.4 群组管理

| 方法     | 路径                                   | 描述                   |
| ------ | ------------------------------------ | -------------------- |
| GET    | /api/groups                          | 获取所有群组列表             |
| POST   | /api/groups                          | 创建新群组（指定名称、描述、成员）    |
| GET    | /api/groups/:group\_id               | 获取群组详情               |
| PUT    | /api/groups/:group\_id               | 更新群组信息（名称、描述、成员、主持人） |
| DELETE | /api/groups/:group\_id               | 删除群组（级联删除消息、任务等）     |
| POST   | /api/groups/:group\_id/members       | 添加成员到群组              |
| DELETE | /api/groups/:group\_id/members/:name | 从群组移除成员              |
| POST   | /api/groups/:group\_id/host          | 设置群组主持人（Host Agent）  |
| GET    | /api/groups/:group\_id/messages      | 获取群组历史消息（支持分页）       |
| GET    | /api/groups/:group\_id/outcomes      | 获取群组的会议结果列表          |
| GET    | /api/groups/:group\_id/tasks         | 获取群组的待办任务            |

#### 6.1.5 任务调度与交付

| 方法   | 路径                                | 描述                     |
| ---- | --------------------------------- | ---------------------- |
| POST | /api/agents/assign                | 分配任务给指定编程 Agent        |
| POST | /api/agents/auto-assign/:task\_id | 自动匹配可用 Agent 并分配任务     |
| POST | /api/tasks/:id/deliver            | 编程 Agent 交付任务成果        |
| POST | /api/tasks/:id/accept             | Hermes Agent 验收任务成果    |
| GET  | /api/tasks/:id/executions         | 获取任务的所有执行记录            |
| POST | /api/projects/:id/tasks/decompose | 触发 Hermes Agent 自动拆解任务 |

#### 6.1.6 Gitea 代码仓库管理（新增）

| 方法     | 路径                                                           | 描述                                                   |
| ------ | ------------------------------------------------------------ | ---------------------------------------------------- |
| POST   | /api/repos                                                    | 为项目创建 Gitea 代码仓库                                  |
| GET    | /api/repos                                                    | 获取所有代码仓库列表（支持按项目筛选）                            |
| GET    | /api/repos/:repo\_id                                          | 获取代码仓库详情                                          |
| GET    | /api/repos/project/:project\_id                               | 获取指定项目的代码仓库                                        |
| DELETE | /api/repos/:repo\_id                                          | 删除代码仓库（需管理员权限）                                    |
| GET    | /api/repos/:repo\_id/branches                                  | 获取仓库所有分支列表                                         |
| GET    | /api/repos/:repo\_id/branches/:branch\_name                    | 获取指定分支详情                                           |
| POST   | /api/repos/:repo\_id/branches                                  | 创建新分支（从指定分支创建）                                     |
| DELETE | /api/repos/:repo\_id/branches/:branch\_name                    | 删除分支（非保护分支）                                         |
| GET    | /api/repos/:repo\_id/pulls                                     | 获取仓库所有 PR 列表（支持状态筛选）                                |
| GET    | /api/repos/:repo\_id/pulls/:number                             | 获取指定 PR 详情                                            |
| POST   | /api/repos/:repo\_id/pulls                                     | 创建 Pull Request                                           |
| POST   | /api/repos/:repo\_id/pulls/:number/merge                       | 合并 PR（需满足合并条件）                                       |
| POST   | /api/repos/:repo\_id/pulls/:number/close                       | 关闭 PR                                                     |
| GET    | /api/repos/:repo\_id/commits                                   | 获取仓库提交记录（支持分页）                                      |
| GET    | /api/repos/:repo\_id/commits/:sha                              | 获取指定提交详情                                              |
| GET    | /api/repos/:repo\_id/compare/:base...:head                      | 比较两个分支/提交的差异                                        |
| POST   | /api/repos/:repo\_id/hooks                                     | 创建 Webhook（用于 CI/CD 集成）                                  |
| GET    | /api/repos/:repo\_id/hooks                                     | 获取仓库 Webhook 列表                                         |
| DELETE | /api/repos/:repo\_id/hooks/:hook\_id                           | 删除 Webhook                                                |
| POST   | /api/repos/validate-commit                                     | 验证提交消息是否符合规范                                         |
| POST   | /api/repos/:repo\_id/protect-branch                            | 配置分支保护规则                                              |

#### 6.1.7 群组任务管理

| 方法  | 路径                          | 描述                                     |
| --- | --------------------------- | -------------------------------------- |
| GET | /api/tasks/pending          | 获取待办任务列表（可按 assignee 筛选）               |
| PUT | /api/tasks/:task\_id/status | 更新任务状态（pending/in\_progress/completed） |

#### 6.1.8 Webhook 与通知

| 方法   | 路径                                  | 描述                          |
| ---- | ----------------------------------- | --------------------------- |
| POST | /api/webhooks/hermes/status         | Hermes Agent 状态变更回调 webhook |
| POST | /api/webhooks/hermes/task-completed | Hermes Agent 任务完成通知 webhook |

### 6.2 WebSocket 事件

#### 6.2.1 核心事件

| 事件                          | 描述            |
| --------------------------- | ------------- |
| project.requirement.updated | 项目需求更新        |
| task.assigned               | 任务分配给编程 Agent |
| task.status.changed         | 任务状态变更        |
| acceptance.result           | 任务验收结果推送      |
| project.completed           | 项目完成通知        |

#### 6.2.2 群聊 WebSocket 端点与事件



WebSocket 端点:

&#x20;`ws://{host}/ws/group-chat`



客户端发送的消息类型:



| 类型                    | 描述                    |
| --------------------- | --------------------- |
| subscribe             | 订阅指定群组的消息             |
| unsubscribe           | 取消订阅指定群组的消息           |
| send\_message         | 发送消息到群组（支持 @mention）  |
| start\_meeting        | 启动会议（指定主题、主持人、类型、时长等） |
| stop\_meeting         | 停止当前会议                |
| meeting\_intervention | 会议进行中用户干预（可调整议程）      |



服务端推送的事件类型:



| 事件类型                    | 描述                               |
| ----------------------- | -------------------------------- |
| subscribed              | 成功订阅群组                           |
| message\_new            | 新消息到达（用户或 Agent 发送）              |
| message\_start          | Agent 开始回复（流式输出）                 |
| message\_chunk          | Agent 回复的流式内容块                   |
| message\_complete       | Agent 回复完成                       |
| agent\_status           | Agent 状态更新（typing/speaking/idle） |
| agent\_error            | Agent 执行出错                       |
| meeting\_started        | 会议开始                             |
| meeting\_stopped        | 会议结束                             |
| meeting\_phase          | 会议阶段变更（开场定调/制订议程/按议程讨论/总结）       |
| meeting\_agenda         | 会议议程就绪                           |
| meeting\_agenda\_item   | 议程项开始                            |
| meeting\_grant\_speak   | 主持人授予发言权                         |
| meeting\_minutes        | 会议纪要推送                           |
| meeting\_outcome\_saved | 会议结果已保存                          |
| task\_created           | 新任务创建（来自会议待办）                    |

***

## 7. 验收标准

### 7.1 Hermes Agent 安装与启动验收

- [ ] Hermes Agent 可通过一键安装脚本正常安装（Linux/macOS `curl | bash`）
- [ ] Hermes Agent 可通过 Docker 镜像正常部署运行
- [ ] `hermes doctor` 命令可正常诊断安装完整性
- [ ] `hermes` 命令可正常启动交互式 CLI/TUI 界面
- [ ] `hermes gateway start` 可正常启动消息网关进程
- [ ] Hermes Gateway 支持作为 systemd 服务持久运行，意外退出后自动重启

### 7.2 Hermes Agent Profile 发现与同步验收

- [ ] Profile Scanner 可自动扫描用户 profiles 目录（`~/.hermes`）
- [ ] 可正确识别每个 profile 的名称、模型配置、Gateway 端口
- [ ] 可检测 Gateway 运行状态（端口监听检查）
- [ ] `GET /api/profiles` 可返回所有扫描到的 profiles 列表
- [ ] `POST /api/agents/sync-hermes` 可将 profiles 同步到数据库
- [ ] 同步时，新增 profile 自动创建 Agent 记录
- [ ] 同步时，已存在 profile 自动更新在线状态和配置
- [ ] Gateway 在线的 Agent 标记为 `online`，离线的标记为 `offline`

### 7.3 Gateway API 通信验收

- [ ] Gateway Client 兼容  API 规范
- [ ] 支持非流式响应（`POST /api/hermes/chat`）
- [ ] 支持流式响应（`POST /api/hermes/chat/stream`，SSE 格式）
- [ ] 支持多轮对话（携带历史消息上下文）
- [ ] 正确处理请求超时（默认 360 秒）
- [ ] 并发控制正常（默认最大 5 并发）
- [ ] 支持可选的 Bearer Token 认证（从 profile 配置读取）

### 7.4 群聊功能验收

- [ ] 可创建群组（`POST /api/groups`），指定名称、描述、成员
- [ ] 可获取群组列表和详情（`GET /api/groups`、`GET /api/groups/:id`）
- [ ] 可添加/移除群组成员
- [ ] WebSocket 连接正常（`ws://{host}/ws/group-chat`）
- [ ] 可订阅/取消订阅群组消息
- [ ] 用户发送消息后，群组所有成员收到实时推送
- [ ] 支持 `@profile_name` 定向提及特定 Agent
- [ ] 未提及 Agent 时，所有成员自动回复
- [ ] Agent 回复支持流式输出（message\_start → message\_chunk → message\_complete）
- [ ] 所有消息持久化到数据库，可查询历史记录

### 7.5 会议模式验收

- [ ] 可启动会议（`start_meeting` WebSocket 消息）
- [ ] 支持 4 种会议类型：需求评审会、技术方案讨论会、每日站会、故障复盘会
- [ ] 主持人可正常开场定调（说明目标、产出、规则）
- [ ] 主持人可根据会议类型生成可执行议程（3-6项）
- [ ] 议程项按顺序执行，主持人控场
- [ ] 成员按顺序发言，每人限时
- [ ] 如有争议，主持人拍板并标记"拍板后不翻案"
- [ ] 会议进行中用户可干预（`meeting_intervention`）
- [ ] 主持人可根据用户干预调整议程
- [ ] 会议结束后输出结构化纪要
- [ ] 纪要包含：决议结论、待办任务（责任人+截止时间）、风险点、遗留问题
- [ ] 可手动停止会议（`stop_meeting`）

### 7.6 会议结果与任务管理验收

- [ ] 会议结果自动保存到 `meeting_outcomes` 表
- [ ] 待办事项自动提取并创建 `group_tasks` 记录
- [ ] 每个任务包含：描述、责任人、截止时间、关联会议ID
- [ ] 任务状态支持：pending、in\_progress、completed
- [ ] 可查询待办任务列表（支持按责任人筛选）
- [ ] 可更新任务状态和执行结果
- [ ] 会议结束后，群组发送任务分配公告
- [ ] 相关 Agent 收到任务通知并可确认执行

### 7.7 编程 Agent 技能注册与调用验收

- [ ] 所有支持的编程 Agent 类型均可注册：Trae、CodeArts、Opencode、Cursor、Claude Code、CodeBuddy、Lingma
- [ ] 编程 Agent 可通过 `POST /api/agents/register` 主动注册自身信息
- [ ] 注册信息包含：Agent 类型、版本、技能列表、能力声明、工作空间路径
- [ ] 支持注册 9 种技能类型：tdd\_test、code\_generation、test\_creation、code\_review、debugging、refactoring、deployment、integration\_testing、documentation
- [ ] 编程 Agent 必须注册至少一种技能才能注册成功
- [ ] 离线 Agent 自动从可用列表中移除
- [ ] 支持动态更新技能列表（Agent 运行时变更）
- [ ] 技能匹配规则正确：需求分析→tdd\_test+code\_generation+documentation、测试用例→test\_creation+code\_review、代码编写→code\_generation+code\_review、测试→test\_creation+debugging、部署→deployment+code\_generation、联调→debugging+integration\_testing
- [ ] Agent 类型匹配规则正确：测试用例→claude\_code/codebuddy、代码编写→opencode/cursor/claude\_code/codearts/trae/lingma、部署→cursor/codebuddy、集成测试→claude\_code/trae
- [ ] 任务下发格式正确：包含 task\_id、task\_type、title、description、requirements、acceptance\_criteria、deadline、context
- [ ] 同一任务支持多 Agent 协作（如代码编写+交叉测试）
- [ ] 目标 Agent 负载过高时自动调整分配策略
- [ ] 关键任务支持冗余分配（多 Agent 交叉验证）
- [ ] 前后两个任务必须分配给不同的 Agent
- [ ] 编程 Agent 可通过 `GET /api/tasks/pending` 查询待执行任务列表
- [ ] 编程 Agent 可通过 `GET /api/tasks/:id` 获取任务详情
- [ ] 编程 Agent 可通过 `POST /api/tasks/:id/start` 标记任务开始执行
- [ ] 编程 Agent 可通过 `POST /api/tasks/:id/progress` 上报任务执行进度
- [ ] 编程 Agent 可通过 `POST /api/tasks/:id/deliver` 交付任务执行成果
- [ ] 编程 Agent 可通过 `POST /api/tasks/:id/fail` 上报任务执行失败
- [ ] 进度上报格式正确：包含 progress、status、message、logs
- [ ] 成果交付格式正确：包含 status、result\_summary、artifacts、test\_results、execution\_log
- [ ] 任务状态流转正确：pending → assigned → running → delivered → accepted（或失败/驳回重分配）
- [ ] 实时接收编程 Agent 任务执行进度上报
- [ ] 对超时未交付的任务触发提醒（向对应编程 Agent 发送催办指令）
- [ ] 向人类用户展示可视化的任务进度看板
- [ ] 前置任务完成并验收通过后，自动触发下游任务分配
- [ ] 任务依赖联动正常：需求分析细化 → 测试用例编写 → 功能模块编码 → 单元/集成测试
- [ ] 记录依赖联动日志

### 7.8 Gitea 代码仓库管理验收（新增）

#### 7.8.1 Gitea 本地部署验收

- [ ] 可通过 Docker Compose 快速部署 Gitea 服务
- [ ] 可通过二进制包快速安装 Gitea
- [ ] 首次访问时安装向导正常工作
- [ ] 可配置数据库（SQLite/PostgreSQL/MySQL）
- [ ] 可配置应用 URL、SSH 端口、HTTP 端口
- [ ] 可创建管理员账号
- [ ] Gitea 服务可正常启动并访问 `http://localhost:3000`
- [ ] 可配置为 Systemd 服务自动启动
- [ ] 服务意外退出后可自动重启

#### 7.8.2 代码仓库创建验收

- [ ] 需求锁定并通过审核后，系统自动在 Gitea 中创建项目代码仓库
- [ ] 仓库名称生成规则正确（项目名小写，空格替换为连字符）
- [ ] 仓库创建在默认组织（`devflow`）下
- [ ] 仓库默认设置为私有
- [ ] 自动初始化仓库，创建 `README.md`、`.gitignore`、`LICENSE` 等基础文件
- [ ] 根据技术栈自动生成项目配置文件（如 `package.json`、`requirements.txt`）
- [ ] 默认分支设置为 `main`
- [ ] 自动配置分支保护规则
- [ ] 仓库创建成功后，自动关联项目信息
- [ ] 返回仓库 URL、SSH/HTTPS 克隆地址

#### 7.8.3 Git Flow 分支策略验收

- [ ] 正确识别 6 种分支类型：main、develop、feature/*、release/*、hotfix/*、bugfix/*
- [ ] 功能开发时自动从 `develop` 创建 `feature/<功能名称>` 分支
- [ ] 发布准备时自动从 `develop` 创建 `release/<版本号>` 分支
- [ ] 紧急修复时自动从 `main` 创建 `hotfix/<问题描述>` 分支
- [ ] 分支命名规范验证正确（前缀必须符合要求）
- [ ] `main` 分支禁止直接推送，必须通过 PR 合并
- [ ] `develop` 分支禁止直接推送，必须通过 PR 合并
- [ ] `feature/*`、`release/*`、`hotfix/*` 分支允许直接推送（开发阶段）
- [ ] 每个功能/修复有独立分支

#### 7.8.4 代码提交规范验收

- [ ] 提交消息必须以类型开头（feat, fix, docs 等 9 种类型）
- [ ] 支持可选的作用域（scope），用括号包裹
- [ ] 类型和作用域后必须跟冒号和空格
- [ ] 主题（subject）简洁明了，不超过 50 字符
- [ ] 支持可选的正文（body）详细描述变更
- [ ] 支持可选的页脚（footer）关联 Issue 或标记破坏性变更
- [ ] 不符合规范的提交被拒绝并给出具体错误信息
- [ ] 所有提交通过规范验证后才能推送
- [ ] 系统自动记录提交信息用于生成变更日志

#### 7.8.5 Pull Request 流程验收

- [ ] 可创建 PR，指定源分支和目标分支
- [ ] PR 标题和描述填写要求明确
- [ ] 支持添加标签（bug, enhancement, documentation 等）
- [ ] 可指定审核人（至少 1 个）
- [ ] 自动检测源分支和目标分支的兼容性
- [ ] 自动触发 CI/CD 流水线（如已配置）
- [ ] 自动检查代码冲突
- [ ] 自动检查 PR 描述完整性
- [ ] 至少需要 1 个审核人审批通过才能合并
- [ ] PR 必须通过所有检查才能合并
- [ ] 代码冲突必须手动解决
- [ ] 合并后自动删除源分支
- [ ] PR 状态变更有通知

#### 7.8.6 代码成果提交要求验收

- [ ] 任务完成时提示开发者提交代码
- [ ] 自动检查是否所有关联文件已提交
- [ ] 未提交代码的任务不能标记为完成
- [ ] 提交信息必须与任务关联（通过任务 ID 或其他标识）
- [ ] 所有提交符合提交规范
- [ ] 自动生成提交消息（如开发者未提供）
- [ ] 推送代码到 Gitea 成功
- [ ] 记录提交信息到项目数据库
- [ ] 系统自动检查提交内容完整性（源代码、测试代码、文档、配置文件等）
- [ ] 不同阶段提交到正确的分支（feature/*、develop、main 等）

#### 7.8.7 Gitea API 接口验收

- [ ] `POST /api/repos` 可创建代码仓库
- [ ] `GET /api/repos` 可获取所有代码仓库列表（支持按项目筛选）
- [ ] `GET /api/repos/:repo_id` 可获取代码仓库详情
- [ ] `GET /api/repos/project/:project_id` 可获取指定项目的代码仓库
- [ ] `GET /api/repos/:repo_id/branches` 可获取仓库所有分支列表
- [ ] `POST /api/repos/:repo_id/branches` 可创建新分支
- [ ] `GET /api/repos/:repo_id/pulls` 可获取仓库所有 PR 列表
- [ ] `POST /api/repos/:repo_id/pulls` 可创建 PR
- [ ] `POST /api/repos/:repo_id/pulls/:number/merge` 可合并 PR
- [ ] `GET /api/repos/:repo_id/commits` 可获取仓库提交记录
- [ ] `POST /api/repos/validate-commit` 可验证提交消息规范
- [ ] `POST /api/repos/:repo_id/protect-branch` 可配置分支保护规则
- [ ] `POST /api/repos/:repo_id/hooks` 可创建 Webhook
- [ ] `GET /api/repos/:repo_id/hooks` 可获取仓库 Webhook 列表

### 7.9 核心功能验收

- [ ] 人类用户可创建项目并提交初始需求
- [ ] 项目创建后自动创建需求评审群组（含产品经理、架构师、开发者、测试工程师）
- [ ] 可在需求评审群组中启动需求评审会议（会议类型：requirement\_review）
- [ ] 主持人（产品经理）可正常开场定调，说明会议目标和产出要求
- [ ] 主持人可根据需求评审会模板生成可执行议程（8项议程）
- [ ] 多 Agent 协同讨论需求，各成员按议程顺序发言
- [ ] 会议进行中用户可发送消息干预，主持人可调整议程
- [ ] 如有争议，主持人当场拍板并标记"拍板后不翻案"
- [ ] 会议结束后输出结构化纪要（决议、待办、风险、遗留问题）
- [ ] 需求确认后，系统根据会议纪要生成标准化需求文档（PRD）
- [ ] 需求文档包含：功能清单、技术方案、验收标准、非功能约束
- [ ] 需求确认后，Hermes Agent 可按开发流程自动拆解任务并匹配编程 Agent
- [ ] 编程 Agent 可接收任务并执行（编写用例/代码/部署等），交付成果
- [ ] Hermes Agent 可自动验收任务成果，驳回时提供修改建议
- [ ] 任务依赖联动正常，按顺序执行
- [ ] 人类用户可实时查看项目进度，接收关键节点通知
- [ ] 项目完成后，Hermes Agent 可汇总成果并向人类用户发送完成通知

### 7.10 非功能验收

- [ ] 页面加载时间 < 2 秒，Hermes Agent 需求响应时间 < 3 秒
- [ ] 支持 20 个项目并发执行，无明显卡顿
- [ ] 系统无严重安全漏洞，项目成果仅对授权用户可见
- [ ] 编程 Agent 执行失败时，Hermes Agent 可自动重试/切换 Agent
- [ ] 接口文档完整，支持新增编程 Agent 快速接入
- [ ] Hermes Agent 支持多种 LLM 提供商切换（OpenAI、OpenRouter、HuggingFace 等），无代码锁定
- [ ] 群聊消息延迟 < 100ms（局域网内）
- [ ] 单个群组支持至少 10 个 Agent 同时在线
- [ ] WebSocket 断线后可自动重连并恢复群组订阅

***



文档结束

