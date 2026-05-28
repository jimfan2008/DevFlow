# DevFlow 项目管理平台 - 软件需求规格说明书 (SRS)

版本: 4.0

日期: 2026-05-28

作者: HaiMei (海梅) / HouXing (后兴)

状态: AI Agent 全自动开发流程重构

变更日志:

- v4.0 (2026-05-28): AI Agent 全自动开发流程重构
  - 核心变更：以16步AI Agent全自动开发流程为主线，重新定义整个SRS
  - 新增10个命名Agent角色：海梅(项目经理)、后兴(需求分析师)、后旺(架构设计师)、后发(程序员/蜂群调度)、后达(测试员/蜂群调度)、后富(CI/CD工程师)、后贵(文档管理员)、后荣(QA)、后华(安全员)
  - 新增QA门控机制：每步产出必须经后荣(QA)检验合格方可进入下一步，检验合格产出全部提交代码库
  - 新增Agent蜂群机制：后发/后达可建立编程Agent蜂群(Claude Code/Codex/Opencode/Cursor/CodeArts/Trae/Lingma/hermes/pi-codeing-agent子agent)
  - 新增TDD驱动流程：先制订测试用例计划→编写TDD测试用例→编写功能代码
  - 新增原子化任务拆解要求：每个任务最小原子化，测试用例一一对应
  - 新增迭代修改闭环：用户不满意则回到第三步重新迭代
  - 重构术语定义、用户角色、功能需求、验收标准等全部章节

***

## 1. 引言

### 1.1 目的

本文档定义 DevFlow 项目管理平台的功能需求、非功能需求及系统架构，核心聚焦于"AI Agent 全自动开发软件"的16步标准流程，确保每个Agent严格按流程执行，确保各Agent能相互沟通和协作，作为开发团队实施和测试验收的依据。

### 1.2 范围

DevFlow 是一个面向人类用户与 AI Agent 协同的全自动化软件开发项目管理平台，核心功能包括：项目创建、需求分析、架构设计、开发环境搭建、TDD测试用例编写、代码编写、测试验证、安全审计、部署交付、文档管理、QA门控的全流程自动化，通过10个命名Agent角色协作完成。

### 1.3 术语定义

| 术语 | 定义 |
|------|------|
| **HaiMei（海梅）** | 默认 Hermes Agent，项目经理角色，负责任务分派，对项目交付成果负责 |
| **HouXing（后兴）** | Hermes Agent，需求分析师角色，负责需求分析，产出完整、准确的软件需求说明书 |
| **HouWang（后旺）** | Hermes Agent，架构设计师角色，负责架构设计、后端设计、前端设计、数据库设计 |
| **HouFa（后发）** | Hermes Agent，程序员角色，负责建立代码编写Agent蜂群，监督蜂群完成TDD测试用例和代码编写 |
| **HouDa（后达）** | Hermes Agent，测试员角色，负责建立代码测试Agent蜂群，执行单元测试、模块测试、集成测试、前端实操验证 |
| **HouFu（后富）** | Hermes Agent，CI/CD工程师角色，负责开发环境搭建和代码部署到测试/生产环境 |
| **HouGui（后贵）** | Hermes Agent，文档管理员角色，负责整个项目文档的一致性管理 |
| **HouRong（后荣）** | Hermes Agent，QA角色，负责检验每个Agent的产出是否达到验收标准，未达标退回重做，达标放行并提交代码库 |
| **HouHua（后华）** | Hermes Agent，安全员角色，负责代码审计、合规审查、渗透测试、漏洞修复 |
| **Agent蜂群** | 由后发或后达建立的编程Agent集群，成员可以是Claude Code/Codex/Opencode/Cursor/CodeArts/Trae/Lingma/hermes/pi-codeing-agent的子agent |
| **QA门控** | 每步产出必须经后荣(QA)检验合格方可进入下一步的机制，检验合格产出全部提交代码库 |
| **原子化任务** | 最小不可再分的任务单元，每个任务有明确的、可量化的验收标准，与测试用例一一对应 |
| **TDD** | 测试驱动开发(Test-Driven Development)，先编写测试用例，再编写功能代码 |
| **项目讨论群** | 项目创建后自动建立的群组，所有10个Agent加入，用于项目沟通和协作 |
| Hermes Agent | 由 Nous Research 开发的开源 AI 代理(github.com/NousResearch/hermes-agent) |
| Hermes Profile | Hermes Agent 的配置文件，定义名称、模型、Gateway端口等 |
| Hermes Gateway | Hermes Agent 的消息网关模式，提供 REST API + WebSocket 接口 |
| Gateway API | Hermes Gateway 暴露的标准 API 接口，支持流式和非流式响应 |
| MCP | Model Context Protocol，Hermes Agent 通过 MCP 扩展能力 |
| Profile 扫描 | DevFlow 通过扫描用户 profiles 目录自动发现可用 Hermes Agent |
| 编程 Agent | 专业 AI 编程代理，如 Claude Code/Codex/Opencode/Cursor/CodeArts/Trae/Lingma 等 |
| Gitea | 轻量级自托管 Git 服务，用于本地代码仓库管理 |
| Git Flow | 标准化分支管理策略，包括 master/develop/feature/release/hotfix 五种分支类型 |
| Pull Request | 代码合并请求机制，合并前需代码审查 |
| Conventional Commits | 标准化 Git 提交消息格式规范 |
| 群组(Group) | 由多个 Agent 成员组成的协作单元，支持讨论模式和会议模式 |
| 讨论模式 | 群组自由工作模式，成员可自主发言、回复，支持 @mention |
| 会议模式 | 群组结构化工作模式，由主持人控制议程，产出决议/待办/风险等 |

***

## 2. 整体描述

### 2.1 产品愿景

为人类用户提供全自动化的软件开发项目管理能力，通过10个命名AI Agent角色严格按16步标准流程协作，完成从需求分析到部署交付的全流程工作，每步产出经QA门控检验，确保交付质量，降低软件开发门槛，提升项目交付效率。

### 2.2 用户角色

| 角色 | 描述 | 权限 |
|------|------|------|
| 人类用户 | 软件开发项目发起者，提出项目需求 | 项目创建、需求沟通、成果验收、查看项目进度、参与群组讨论 |
| HaiMei（海梅） | 项目经理（Hermes Agent） | 任务分派、流程管控、交付成果负责、对项目讨论群管理 |
| HouXing（后兴） | 需求分析师（Hermes Agent） | 需求分析、需求评审、产出软件需求说明书 |
| HouWang（后旺） | 架构设计师（Hermes Agent） | 架构设计、后端设计、前端设计、数据库设计 |
| HouFa（后发） | 程序员（Hermes Agent） | 建立代码编写Agent蜂群、监督蜂群完成TDD测试用例和代码编写 |
| HouDa（后达） | 测试员（Hermes Agent） | 建立代码测试Agent蜂群、执行全类型测试 |
| HouFu（后富） | CI/CD工程师（Hermes Agent） | 开发环境搭建、代码部署到测试/生产环境 |
| HouGui（后贵） | 文档管理员（Hermes Agent） | 全项目文档一致性管理 |
| HouRong（后荣） | QA（Hermes Agent） | 检验每个Agent产出、验收标准判定、不合格退回重做、合格提交代码库 |
| HouHua（后华） | 安全员（Hermes Agent） | 代码审计、合规审查、渗透测试、漏洞修复 |
| 系统管理员 | 平台运维人员（Hermes Agent） | 配置Agent能力、监控系统运行状态、管理权限 |

### 2.3 Agent组织架构

```
┌──────────────────────────────────────────────────────────────┐
│                    项目讨论群（所有Agent）                      │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ HaiMei   │  │ HouXing  │  │ HouWang  │  │ HouFa    │    │
│  │ 海梅     │  │ 后兴     │  │ 后旺     │  │ 后发     │    │
│  │ 项目经理 │  │ 需求分析 │  │ 架构设计 │  │ 程序员   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ HouDa    │  │ HouFu    │  │ HouGui   │  │ HouRong  │    │
│  │ 后达     │  │ 后富     │  │ 后贵     │  │ 后荣     │    │
│  │ 测试员   │  │ CI/CD    │  │ 文档管理 │  │ QA       │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│  ┌──────────┐                                               │
│  │ HouHua   │                                               │
│  │ 后华     │                                               │
│  │ 安全员   │                                               │
│  └──────────┘                                               │
└──────────────────────────────────────────────────────────────┘
```

### 2.4 运行环境

- 前端: 现代浏览器 (Chrome 90+, Firefox 88+, Safari 14+)
- 后端: Linux/Windows/macOS (Docker 部署)
- 数据库: PostgreSQL 14+, Redis 6+
- 代码托管: 本地部署 Gitea（轻量级自托管 Git 服务）
- AI Agent 交互层: 通过 Hermes Gateway API 与 Hermes Agent 通信
- Hermes Profiles 路径配置:
  - Windows: `\\wsl$\{distro}\home\{user}\.hermes`（通过 WSL 路径访问）
  - Linux/macOS: `~/.hermes`
- Hermes Agent:
  - Python 3.10+（推荐 3.14）
  - 操作系统：Linux（生产推荐）、macOS、Windows（仅限 WSL2 或 PowerShell Beta）
  - Node.js（部分 gateway 功能需要）
  - 磁盘空间：最低 500MB，推荐 2GB+
- Gitea:
  - Go 1.21+（源码安装需要）
  - 数据库：SQLite（默认）或 PostgreSQL 12+ / MySQL 8+
  - Git 2.25+
  - 默认端口：3000（HTTP）、22（SSH，可选）

### 2.5 Hermes Agent 安装

#### 2.5.1 快速安装（推荐）

DevFlow 平台依赖外部 Hermes Agent 实例作为核心调度代理。Hermes Agent 是独立开源软件，需单独安装部署。

Linux / macOS / WSL2（生产推荐）：

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

### 2.6 Gitea 本地安装部署

DevFlow 平台依赖本地部署的 Gitea 作为代码托管服务，所有项目代码及成果必须提交到 Gitea 代码库。

#### 2.6.1 支持的安装方式

| 安装方式 | 描述 | 推荐场景 |
|---------|------|---------|
| Docker 安装（推荐） | 使用官方 Gitea Docker 镜像快速部署 | 生产环境、快速部署、易于维护 |
| 二进制安装 | 下载官方二进制包直接运行 | 开发环境、小型部署 |
| 源码安装 | 从源码编译安装 | 定制化需求、特殊架构 |

#### 2.6.2 Docker 安装（推荐生产配置）

```bash
mkdir -p /data/gitea
mkdir -p /data/git

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
      - "222:22"
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

docker-compose up -d
```

#### 2.6.3 配置 DevFlow 连接 Gitea

```yaml
gitea:
  host: "localhost"
  port: 3000
  protocol: "http"
  api_token: "gitea_api_token"
  username: "devflow_bot"
  default_org: "devflow"
  default_branch: "main"
```

### 2.7 Hermes Agent Profile 自动发现与对接

#### 2.7.1 Profile 自动扫描机制

DevFlow 通过 Profile Scanner 自动发现用户系统中的所有 Hermes Agent，替代传统的主动注册模式。

| 发现方式 | 机制 | 适用场景 |
|---------|------|---------|
| Profile 目录扫描 | 定期扫描用户 profiles 目录，自动发现和识别 Hermes Agent 配置 | 主要发现方式，零配置使用 |
| 手动刷新 | 用户可通过 API 触发立即扫描 | 实时同步场景 |
| 状态轮询 | 定期检查各 profile 的 Gateway 运行状态（端口监听检测） | 在线状态监控 |

Profile 存储路径：
- Linux/macOS: `~/.hermes`
- Windows (WSL): `\\wsl$\{distro}\home\{user}\.hermes`

#### 2.7.2 Profile 信息结构

```json
{
  "name": "haimei",
  "model_default": "gpt-4o",
  "model_provider": "openai",
  "gateway_port": 8765,
  "personality": "项目经理，负责任务分派，对项目交付成果负责",
  "is_running": true,
  "config_path": "/home/user/.hermes/profiles/haimei/config.yaml"
}
```

#### 2.7.3 Gateway API 通信规范

```
┌─────────────┐    HTTP + WebSocket     ┌──────────────┐
│  DevFlow    │◄───────────────────────►│ Hermes Agent │
│  (调度平台)  │    Gateway API 规范      │ (Gateway模式) │
└─────────────┘                         └──────────────┘
                                                │
                                                ▼
                               对话消息、任务拆解、多Agent群组讨论、
                               需求协同、会议主持、结构化会议、自动总结
```

通信特点：
- 流式响应：支持 Server-Sent Events (SSE) 流式输出
- 并发控制：通过信号量限制最大并发请求数（默认 5）

***

## 3. AI Agent 全自动开发流程（16步标准流程）

> **核心原则**：
> 1. 每步产出必须经 HouRong（后荣/QA）检验合格方可进入下一步
> 2. 检验合格的产出品全部提交到代码库
> 3. 检验不合格的产出品退回重做，直到合格
> 4. 所有Agent通过项目讨论群进行沟通和协作

### 第一步：人类用户创建新的软件项目

- **执行者**: 人类用户
- **输入**: 项目名称、项目描述、初始需求
- **处理**:
  1. 人类用户在 DevFlow 平台创建新的软件项目
  2. 系统生成唯一项目 ID，存储项目基础信息
  3. 系统在 Gitea 中自动创建项目代码仓库
- **输出**: 项目创建成功，代码仓库就绪
- **业务规则**:
  - 项目名称需唯一
  - 支持富文本/Markdown 需求描述，支持附件上传

### 第二步：海梅主动与人类用户对话，确认项目核心目标并搭建组织架构

- **执行者**: HaiMei（海梅）— 项目经理
- **输入**: 人类用户的项目描述和初始需求
- **处理**:
  1. 海梅主动与人类用户对话，沟通并确认项目的核心目标
  2. 搭建项目组织架构，激活以下9个Agent角色：

  | Agent名称 | 中文名 | 角色 | 职责 |
  |-----------|--------|------|------|
  | HaiMei | 海梅 | 项目经理 | 负责任务分派，对项目的交付成果负责 |
  | HouXing | 后兴 | 需求分析师 | 负责需求分析，产出完整、准确的软件需求说明书 |
  | HouWang | 后旺 | 架构设计师 | 负责架构设计、后端设计、前端设计、数据库设计等 |
  | HouFa | 后发 | 程序员 | 负责建立代码编写Agent蜂群，监督蜂群完成TDD测试用例和代码编写 |
  | HouDa | 后达 | 测试员 | 负责建立代码测试Agent蜂群，执行单元测试、模块测试、集成测试、前端实操验证 |
  | HouFu | 后富 | CI/CD工程师 | 专门负责开发环境搭建和代码部署到测试环境或生产环境 |
  | HouGui | 后贵 | 文档管理员 | 负责整个项目的文档一致性管理 |
  | HouRong | 后荣 | QA | 负责检验每个Agent的产出是否达到验收标准，未达标退回重做，达标放行并提交代码库 |
  | HouHua | 后华 | 安全员 | 负责代码审计、合规审查、渗透测试、漏洞修复等 |

  3. 建立项目讨论群，将人类用户及所有Agent（海梅、后兴、后旺、后发、后达、后富、后贵、后荣、后华）加入群组
- **产出成果**:
  1. 软件项目的核心目标（经用户确认）
  2. 项目组织架构（9个Agent角色定义）
  3. 项目讨论群（所有Agent已加入）
- **QA门控**: 后荣检验核心目标是否明确、组织架构是否完整、讨论群是否正常
- **业务规则**:
  - 海梅必须主动发起对话，不能等待用户追问
  - 所有Agent必须加入项目讨论群
  - 讨论群支持讨论模式和会议模式

### 第三步：海梅安排后兴与用户对话，产出软件需求说明书

- **执行者**: HaiMei（海梅）安排 HouXing（后兴）
- **输入**: 项目核心目标、用户初始需求
- **处理**:
  1. 海梅安排后兴（Hermes Agent — 需求分析师角色）一起与人类用户对话，沟通具体需求
  2. 如果项目较复杂，在项目讨论群中召开需求评审会议（会议类型：`requirement_review`）
  3. 后兴根据沟通结果和会议纪要，生成完整、准确的软件需求说明书（SRS）
- **产出成果**: 完整、准确的软件需求说明书（SRS）
- **QA门控**: 软件需求说明书必须经 HouRong（后荣/QA）检验合格才可以进行下一步
- **代码库提交**: 检验合格的软件需求说明书提交到代码库
- **业务规则**:
  - 需求说明书必须包含：功能需求、非功能需求、验收标准、约束条件
  - 复杂项目必须召开需求评审会议
  - 需求说明书需人类用户确认
  - 后荣检验维度：需求完整性、一致性、可验证性、无歧义性

### 第四步：海梅安排后旺进行架构设计

- **执行者**: HaiMei（海梅）安排 HouWang（后旺）
- **输入**: 项目核心目标、软件需求说明书
- **处理**:
  1. 海梅安排后旺，依据项目的核心目标、软件需求说明书，依次生成：
     - 架构设计文档
     - 后端设计文档
     - 前端设计文档
     - 数据库设计文档
  2. 每一份设计文档必须经 HouRong（后荣/QA）检验
  3. 全部合格才可以进行下一步
- **产出成果**: 架构设计文档、后端设计文档、前端设计文档、数据库设计文档
- **QA门控**: 每份设计文档必须经 HouRong（后荣/QA）检验合格，且全部合格方可放行
- **代码库提交**: 检验合格的全部设计文档提交到代码库
- **业务规则**:
  - 设计文档必须与需求说明书一致
  - 后荣检验维度：设计完整性、需求覆盖度、技术可行性、架构合理性

### 第五步：海梅安排后富建立软件开发环境

- **执行者**: HaiMei（海梅）安排 HouFu（后富）
- **输入**: 软件需求说明书、架构设计文档、后端设计文档、前端设计文档、数据库设计文档
- **处理**:
  1. 海梅安排后富，依据上述文档建立软件开发环境
  2. 包括：代码仓库初始化、开发框架搭建、依赖配置、数据库初始化等
- **产出成果**: 可用的软件开发环境
- **QA门控**: 开发环境必须经 HouRong（后荣/QA）检验合格才可以进行下一步
- **代码库提交**: 环境配置文件提交到代码库
- **业务规则**:
  - 开发环境必须可正常运行
  - 后荣检验维度：环境可用性、配置正确性、依赖完整性

### 第六步：海梅制订《TDD测试用例编写计划》

- **执行者**: HaiMei（海梅）
- **输入**: 软件需求说明书、架构设计文档、后端设计文档、前端设计文档、数据库设计文档
- **处理**:
  1. 海梅依据上述文档，制订《TDD测试用例编写计划》
  2. 每个测试用例必须是最小原子化的
  3. 每个测试用例必须有明确的、最好是可量化的验收标准
- **产出成果**: 《TDD测试用例编写计划》
- **QA门控**: 必须经 HouRong（后荣/QA）检验合格才可以进行下一步
- **代码库提交**: 检验合格的计划文档提交到代码库
- **业务规则**:
  - 测试用例必须覆盖所有功能需求
  - 每个测试用例原子化，不可再分
  - 验收标准可量化、可验证
  - 后荣检验维度：覆盖率、原子化程度、验收标准可量化性

### 第七步：海梅安排后发建立Agent蜂群编写TDD测试用例

- **执行者**: HaiMei（海梅）安排 HouFa（后发）
- **输入**: 《TDD测试用例编写计划》
- **处理**:
  1. 海梅安排后发，依据《TDD测试用例编写计划》，建立Agent蜂群
  2. 蜂群中的Agent可以是：Claude Code / Codex / Opencode / Cursor / CodeArts / Trae / Lingma / hermes子agent / pi-codeing-agent子agent
  3. 由后发负责对接和监督蜂群中的Agent完成具体的TDD测试用例编写
- **产出成果**: 所有TDD测试用例代码
- **QA门控**: 必须经 HouRong（后荣/QA）检验合格才可以进行下一步
- **代码库提交**: 检验合格的TDD测试用例全部提交到代码库
- **业务规则**:
  - 后发负责任务分发、进度监控、成果收集
  - 每个蜂群Agent完成的测试用例需单独检验
  - 后荣检验维度：用例正确性、覆盖率、原子化、验收标准匹配

### 第八步：海梅制订《代码编写计划》

- **执行者**: HaiMei（海梅）
- **输入**: 软件需求说明书、架构设计文档、后端设计文档、前端设计文档、数据库设计文档、《TDD测试用例编写计划》
- **处理**:
  1. 海梅依据上述文档，制订《代码编写计划》
  2. 每个代码编写任务必须是最小原子化的任务
  3. 每个任务都有测试用例一一对应
  4. 若任务有依赖关系，必须按照依赖关系画出任务依赖图
- **产出成果**: 《代码编写计划》（含任务依赖图）
- **QA门控**: 必须经 HouRong（后荣/QA）检验合格才可以进行下一步
- **代码库提交**: 检验合格的计划文档提交到代码库
- **业务规则**:
  - 每个任务与测试用例一一对应
  - 任务原子化，不可再分
  - 依赖关系无循环
  - 后荣检验维度：任务原子化、测试用例对应、依赖关系正确性

### 第九步：海梅安排后发建立Agent蜂群编写功能代码

- **执行者**: HaiMei（海梅）安排 HouFa（后发）
- **输入**: 《TDD测试用例编写计划》、《代码编写计划》
- **处理**:
  1. 海梅安排后发，依据《TDD测试用例编写计划》和《代码编写计划》，建立Agent蜂群
  2. 蜂群中的Agent可以是：Claude Code / Codex / Opencode / Cursor / CodeArts / Trae / Lingma / hermes子agent / pi-codeing-agent子agent
  3. 由后发负责对接和监督蜂群中的Agent完成具体的代码编写
  4. 每个子任务必须经 HouRong（后荣/QA）检验合格才可以进行下一步
- **产出成果**: 全部功能代码
- **QA门控**: 每个子任务必须经 HouRong（后荣/QA）检验，合格才可以进行下一步
- **代码库提交**: 检验合格的代码全部提交到代码库
- **业务规则**:
  - 严格按照任务依赖图顺序执行
  - 有依赖关系的任务，前置任务验收通过后才执行后继任务
  - 每个子任务完成后立即检验，不合格立即退回重做
  - 后荣检验维度：代码正确性、测试用例通过、需求匹配度、代码规范

### 第十步：海梅安排后富将代码部署到测试环境

- **执行者**: HaiMei（海梅）安排 HouFu（后富）
- **输入**: 代码库中的全部代码
- **处理**:
  1. 海梅安排后富将代码部署到测试环境
  2. 后富负责配置测试环境、执行部署、验证部署成功
- **产出成果**: 测试环境部署成功，应用可访问
- **业务规则**:
  - 部署前代码必须全部通过QA检验
  - 部署失败需后富排查并修复

### 第十一步：海梅安排后达执行全面测试

- **执行者**: HaiMei（海梅）安排 HouDa（后达）
- **输入**: 测试环境中的应用、《TDD测试用例编写计划》
- **处理**:
  1. 海梅安排后达，建立代码测试的Agent蜂群
  2. 执行以下测试：
     - 单元测试
     - 模块测试
     - 集成测试
     - 前端实操验证
  3. 生成所有测试报告
- **产出成果**: 全部测试报告（单元测试报告、模块测试报告、集成测试报告、前端实操验证报告）
- **QA门控**: 所有测试报告必须经 HouRong（后荣/QA）检验合格才可以进行下一步
- **代码库提交**: 检验合格的测试报告全部提交到代码库
- **业务规则**:
  - 测试蜂群Agent可并行执行不同类型测试
  - 前端实操验证必须实际操作验证，不能仅靠后端测试
  - 后荣检验维度：测试覆盖率、通过率、缺陷严重程度、实操验证结果

### 第十二步：海梅安排后华进行安全审计

- **执行者**: HaiMei（海梅）安排 HouHua（后华）
- **输入**: 代码库中的全部代码、测试报告
- **处理**:
  1. 海梅安排后华执行安全审计
  2. 审计内容包括：
     - 代码审计
     - 合规审查
     - 渗透测试
     - 漏洞修复
  3. 产出安全审计报告
- **产出成果**: 安全审计报告
- **QA门控**: 安全审计报告必须经 HouRong（后荣/QA）检验合格才可以进行下一步
- **代码库提交**: 检验合格的安全审计报告提交到代码库
- **业务规则**:
  - 发现的高危漏洞必须修复后重新审计
  - 后荣检验维度：漏洞修复率、合规达标、渗透测试通过

### 第十三步：海梅安排后富将代码部署到生产环境

- **执行者**: HaiMei（海梅）安排 HouFu（后富）
- **输入**: 通过全部测试和安全审计的代码
- **处理**:
  1. 海梅安排后富将代码部署到生产环境
  2. 后富负责配置生产环境、执行部署、验证部署成功
- **产出成果**: 生产环境部署成功，应用可正常使用
- **业务规则**:
  - 部署前必须通过全部测试和安全审计
  - 部署失败需后富排查并修复

### 第十四步：海梅安排后贵完善项目文档

- **执行者**: HaiMei（海梅）安排 HouGui（后贵）
- **输入**: 全部项目产出（需求说明书、设计文档、代码、测试报告、安全审计报告等）
- **处理**:
  1. 海梅安排后贵修改完善整个项目的文档
  2. 包括：
     - 部署手册
     - 操作手册
     - API文档
     - 用户手册
  3. 保证文档一致性：任何一处修改，其它文档必须同步修改
- **产出成果**: 完整、一致的项目文档集
- **业务规则**:
  - 后贵必须保证所有文档之间的一致性
  - 代码有修改，文档必须同步更新
  - 后荣检验维度：文档完整性、一致性、准确性

### 第十五步：海梅向人类用户报告项目进展及交付成果

- **执行者**: HaiMei（海梅）
- **输入**: 全部项目产出
- **处理**:
  1. 海梅向人类用户报告项目的进展及交付成果
  2. 报告内容包括：
     - 项目完成状态
     - 功能交付清单
     - 测试结果摘要
     - 安全审计结果
     - 部署访问地址
     - 文档下载链接
- **产出成果**: 项目交付报告
- **业务规则**:
  - 报告必须清晰、完整
  - 提供成果验证入口

### 第十六步：用户满意度确认与迭代修改

- **执行者**: HaiMei（海梅）
- **处理**:
  1. 若人类用户对交付成果不满意，海梅收集用户的修改意见
  2. 回到第三步，依流程进行修改
  3. 直到用户满意交付成果为止
  4. 用户满意后，项目结束
- **产出成果**: 用户确认满意，项目结束
- **业务规则**:
  - 每次迭代修改仍需严格遵循16步流程
  - 迭代修改时，已合格的产出可保留，仅修改不合格部分
  - 项目结束需在代码库中打版本标签

### 16步流程全景图

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI Agent 全自动开发流程（16步）                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ① 人类用户创建项目                                                   │
│     │                                                               │
│  ② 海梅↔用户：确认核心目标 + 搭建组织架构 + 建立讨论群                   │
│     │ ──QA后荣检验──                                                 │
│  ③ 海梅→后兴：需求分析 → 软件需求说明书                                │
│     │ ──QA后荣检验──✓→提交代码库                                     │
│  ④ 海梅→后旺：架构设计/后端设计/前端设计/数据库设计                      │
│     │ ──QA后荣逐项检验──✓→提交代码库                                  │
│  ⑤ 海梅→后富：建立开发环境                                            │
│     │ ──QA后荣检验──                                                 │
│  ⑥ 海梅：制订《TDD测试用例编写计划》                                    │
│     │ ──QA后荣检验──✓→提交代码库                                     │
│  ⑦ 海梅→后发(蜂群)：编写TDD测试用例                                   │
│     │ ──QA后荣检验──✓→提交代码库                                     │
│  ⑧ 海梅：制订《代码编写计划》+ 任务依赖图                              │
│     │ ──QA后荣检验──✓→提交代码库                                     │
│  ⑨ 海梅→后发(蜂群)：编写功能代码（按依赖图顺序）                       │
│     │ ──QA后荣逐任务检验──✓→提交代码库                                │
│  ⑩ 海梅→后富：部署到测试环境                                          │
│     │                                                               │
│  ⑪ 海梅→后达(蜂群)：全面测试(单元/模块/集成/前端实操)                   │
│     │ ──QA后荣检验──✓→提交代码库                                     │
│  ⑫ 海梅→后华：安全审计(代码审计/合规/渗透/漏洞修复)                     │
│     │ ──QA后荣检验──✓→提交代码库                                     │
│  ⑬ 海梅→后富：部署到生产环境                                          │
│     │                                                               │
│  ⑭ 海梅→后贵：完善项目文档(部署手册/操作手册等)                        │
│     │                                                               │
│  ⑮ 海梅→用户：报告项目进展及交付成果                                   │
│     │                                                               │
│  ⑯ 用户不满意？──是──→ 回到③重新迭代                                  │
│     │              └──否──→ 项目结束                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

***

## 4. 功能需求（支撑模块）

### 4.1 项目讨论群与多Agent协作模块

#### 4.1.1 群组管理

- **功能描述**: 创建和管理由10个Agent组成的项目讨论群
- **群组属性**:
  - 基本信息：群组名称、描述、创建时间
  - 成员列表：HaiMei, HouXing, HouWang, HouFa, HouDa, HouFu, HouGui, HouRong, HouHua
  - 工作模式：`discussion`（讨论模式）或 `meeting`（会议模式）
  - 主持人：会议模式下的 Host Agent（默认海梅）
- **支持的操作**:
  - 创建群组：项目创建时自动创建，指定名称、描述、初始成员
  - 查看群组：获取群组详情和成员列表
  - 修改群组：更新名称、描述、成员、主持人
  - 成员管理：添加/移除成员，设置主持人
- **业务规则**:
  - 每个项目必须有一个项目讨论群
  - 所有10个Agent必须加入讨论群
  - 会议模式必须设置主持人

#### 4.1.2 讨论模式 (Discussion Mode)

- **功能描述**: 群组的自由工作模式，成员可自主发言、回复消息
- **消息发送**:
  - 用户或Agent发送消息到群组
  - 支持 `@Agent名称` 定向提及特定Agent
  - 未提及Agent时，所有成员都会收到消息并回复
- **自动回复机制**:
  - 检测消息中的 @mention
  - 确定目标回复Agent
  - 获取最近消息作为上下文
  - 调用 Gateway API 获取各Agent的响应
  - 流式输出响应内容到前端

#### 4.1.3 会议模式 (Meeting Mode)

- **功能描述**: 群组的结构化工作模式，由主持人控制议程，产出结构化会议成果
- **会议类型**:
  - 需求评审会 (requirement_review): PRD整体介绍→业务流程→边界规则→特殊场景→开发提问→当场确认
  - 技术方案讨论会 (tech_solution): 背景目标→现有问题→备选方案对比→架构接口→敲定方案→拆分任务
  - 每日站会 (daily_standup): 每人3句话（昨天/今天/阻塞）
  - 故障复盘会 (incident_postmortem): 时间线→影响面→根因→修复措施→预防改进
- **会议流程**:
  1. 开场定调：主持人介绍会议目标、产出要求
  2. 制订议程：主持人根据会议类型生成可执行议程
  3. 按议程讨论：按顺序邀请各成员发言，主持人控场
  4. 会议总结：主持人输出结构化会议纪要
- **会议规则**:
  - 聚焦议题，不跑偏
  - 发言简明，每人限时
  - 争议无共识由负责人当场拍板
  - 结论当场记录
- **用户干预**: 会议进行中用户可发送消息干预，主持人可调整议程
- **输出**: 会议纪要、决议、待办任务、风险点、遗留问题

### 4.2 Agent蜂群管理模块

#### 4.2.1 蜂群建立

- **功能描述**: 后发或后达建立编程Agent蜂群，调度多个编程Agent并行执行任务
- **蜂群成员**: 可以是以下任意编程Agent：
  - Claude Code
  - Codex
  - Opencode
  - Cursor
  - CodeArts
  - Trae
  - Lingma
  - hermes子agent
  - pi-codeing-agent子agent
- **蜂群调度者**:
  - 后发（HouFa）：代码编写蜂群调度
  - 后达（HouDa）：代码测试蜂群调度
- **蜂群管理**:
  - 任务分发：将原子化任务分配给蜂群中合适的Agent
  - 进度监控：实时监控每个Agent的执行进度
  - 成果收集：收集每个Agent的交付成果
  - 负载均衡：根据Agent负载和技能匹配分配任务

#### 4.2.2 编程Agent技能注册

- **功能描述**: 编程Agent向DevFlow平台注册自身信息和可用技能
- **注册方式**:
  - API主动注册：编程Agent启动时调用 `POST /api/agents/register`
  - 配置文件注册：在DevFlow配置文件中静态声明
  - 手动注册：用户通过管理界面手动添加
- **技能类型定义**:
  - `tdd_test`: TDD测试用例编写
  - `code_generation`: 功能代码生成
  - `test_creation`: 测试用例编写
  - `code_review`: 代码审查
  - `debugging`: Bug修复
  - `refactoring`: 代码重构
  - `deployment`: 环境部署
  - `integration_testing`: 集成测试
  - `documentation`: 文档编写

#### 4.2.3 技能匹配规则

| 任务类型 | 技能组合 | 优先Agent类型 |
|---------|---------|-------------|
| TDD测试用例编写 | tdd_test + code_review | claude_code, codebuddy |
| 功能代码编写 | code_generation + code_review | opencode, cursor, claude_code, codearts, trae, lingma |
| 测试用例编写 | test_creation + code_review | claude_code, codebuddy |
| 环境部署 | deployment + code_generation | cursor, codebuddy, codearts |
| 集成测试 | test_creation + debugging | claude_code, trae |

### 4.3 QA门控模块

#### 4.3.1 QA检验流程

- **功能描述**: HouRong（后荣/QA）对每个Agent的产出进行检验
- **检验流程**:
  1. 接收Agent交付的产出品
  2. 按验收标准逐项比对
  3. 检验合格：放行，产出品提交到代码库，允许进入下一步
  4. 检验不合格：退回重做，附带修改建议，Agent必须在时限内修改重新提交
- **检验维度**（按产出类型）:

| 产出类型 | 检验维度 |
|---------|---------|
| 软件需求说明书 | 完整性、一致性、可验证性、无歧义性 |
| 设计文档 | 完整性、需求覆盖度、技术可行性、架构合理性 |
| 开发环境 | 可用性、配置正确性、依赖完整性 |
| TDD测试用例 | 正确性、覆盖率、原子化、验收标准可量化 |
| 计划文档 | 任务原子化、测试用例对应、依赖关系正确性 |
| 功能代码 | 正确性、测试通过、需求匹配度、代码规范 |
| 测试报告 | 覆盖率、通过率、缺陷严重度、实操验证结果 |
| 安全审计报告 | 漏洞修复率、合规达标、渗透测试通过 |
| 项目文档 | 完整性、一致性、准确性 |

#### 4.3.2 代码库提交规则

- **功能描述**: 检验合格的产出品全部提交到代码库
- **提交规则**:
  - 所有检验合格的产出必须提交到Gitea代码库
  - 提交必须遵循Conventional Commits规范
  - 提交必须关联任务ID
  - 未检验或检验不合格的产出禁止提交
- **提交时机**:

| 阶段 | 提交内容 | 目标分支 |
|------|---------|---------|
| 需求分析完成 | 软件需求说明书 | develop |
| 设计完成 | 设计文档 | develop |
| TDD测试用例完成 | 测试用例代码 | feature/* |
| 功能代码完成 | 功能代码 + 单元测试 | feature/* |
| 测试通过 | 测试报告 | develop（通过PR） |
| 安全审计通过 | 安全审计报告 | develop |
| 发布就绪 | 全部产出 | release/* |
| 生产发布 | 稳定版本 | main（通过PR） |

### 4.4 代码库管理模块

#### 4.4.1 项目仓库自动创建

- **功能描述**: 项目创建时，系统自动在Gitea中创建项目代码仓库
- **触发条件**: 第二步组织架构搭建完成
- **处理**:
  1. 根据项目名称生成仓库名称
  2. 在配置的默认组织下创建仓库
  3. 设置仓库为私有
  4. 初始化仓库，创建基础文件
  5. 设置默认分支为 `main`
  6. 配置分支保护规则

#### 4.4.2 分支管理（Git Flow）

采用 Git Flow 分支策略：
- `main`: 生产分支，仅通过PR合并
- `develop`: 开发分支，仅通过PR合并
- `feature/*`: 功能分支
- `release/*`: 发布分支
- `hotfix/*`: 紧急修复分支

#### 4.4.3 代码提交规范

所有代码提交必须遵循 Conventional Commits 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

| 类型 | 描述 |
|------|------|
| feat | 新功能 |
| fix | Bug修复 |
| docs | 文档更新 |
| style | 代码格式调整 |
| refactor | 代码重构 |
| test | 添加或修改测试 |
| build | 构建系统或依赖更新 |
| ci | CI配置更新 |
| chore | 其他杂项任务 |

#### 4.4.4 Pull Request流程

所有代码合并必须通过Pull Request流程，确保代码质量：
1. 创建分支 → 2. 开发编码 → 3. 推送远程 → 4. 创建PR → 5. 代码审查 → 6. 自动化测试 → 7. 审批通过 → 8. 合并 → 9. 删除源分支

### 4.5 Hermes Agent管理模块

#### 4.5.1 Agent安装部署

- 支持一键脚本安装（Linux/macOS）
- 安装验证：`hermes doctor` 命令诊断安装完整性
- 支持Gateway模式和CLI/TUI模式

#### 4.5.2 Profile自动发现

- Profile Scanner自动扫描用户profiles目录
- 自动识别Agent配置（名称、模型、Gateway端口等）
- 自动检测Gateway运行状态
- 自动同步到DevFlow数据库

#### 4.5.3 Gateway API通信

- 支持流式响应（SSE格式）
- 支持多轮对话（携带历史消息上下文）
- 并发控制（信号量限制，默认5）
- 请求超时控制（默认360秒）

### 4.6 通知与交付模块

#### 4.6.1 项目进度通知

- **通知节点**: 需求确认完成、设计完成、测试用例完成、代码编写完成、测试完成、安全审计完成、部署完成
- **通知方式**: 平台内消息、邮件（可选）

#### 4.6.2 项目完成通知

- **通知内容**: 项目完成状态、成果访问链接、交付报告链接

***

## 5. 非功能需求

### 5.1 性能要求

| 指标 | 目标值 |
|------|-------|
| 页面加载时间 | < 2 秒 |
| Agent响应时间 | < 3 秒 |
| 蜂群Agent任务分配响应时间 | < 500 毫秒 |
| QA检验自动化处理时间 | 单产出 < 1 分钟 |
| 并发项目数 | 支持 20 个项目同时执行 |
| 数据库查询响应 | < 100 毫秒 |

### 5.2 安全要求

- 用户认证: JWT Token 认证
- 授权控制: 基于角色的访问控制 (RBAC)
- 数据加密: HTTPS传输加密，Agent交互数据脱敏存储
- 成果安全: 项目代码/成果仅对人类用户和授权Agent可见
- 日志审计: 记录所有Agent交互、任务分配、QA检验操作日志

### 5.3 可用性要求

- 系统可用性: 99.5%
- 数据备份: 每日自动备份
- 容错机制: Agent执行失败时，海梅自动重试或切换备用Agent
- 错误处理: 关键流程失败时提供明确错误提示和人工介入入口

### 5.4 可扩展性要求

- API接口设计遵循RESTful规范
- 支持新增编程Agent类型的快速接入
- 任务拆解规则支持配置化扩展
- 验收标准支持自定义扩展

***

## 6. 系统架构

### 6.1 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Element Plus + 实时通信组件 |
| 后端 | Python FastAPI + Celery（任务调度）+ asyncio（异步并发控制） |
| 数据库 | PostgreSQL + Redis（缓存/状态存储） |
| 代码托管层 | Gitea（本地部署的自托管Git服务） |
| AI Agent交互层 | Gateway Client（OpenAI兼容）、Profile Scanner、Conversation Coordinator |
| 群聊协作层 | WebSocket实时通信、Connection Manager、Meeting State |
| Hermes Agent | 独立部署的开源AI代理，10个命名Agent角色 |
| 部署 | Docker + Docker Compose |

### 6.2 架构图

```
┌───────────────────────────────────────────────────────────────────────┐
│                           人类用户 (Client)                            │
│              浏览器 / 移动端 (需求提交/进度查看/群组聊天/会议参与)          │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │ HTTP / WebSocket
┌───────────────────────────────────▼───────────────────────────────────┐
│                            Nginx (反向代理)                             │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
┌───────────────────────────────────▼───────────────────────────────────┐
│                      FastAPI 后端 (DevFlow Server)                     │
│  ┌──────────┬─────────────┬────────────┬───────────────────┐         │
│  │ 16步流程  │ Agent蜂群   │ QA门控     │ 项目讨论群        │         │
│  │ 调度引擎  │ 调度管理    │ 检验引擎   │ 管理/会议         │         │
│  └──────────┴─────────────┴────────────┴───────────────────┘         │
│  ┌──────────┬─────────────┬────────────┬───────────────────┐         │
│  │ Profile  │ Gateway     │ 代码库     │ 通知管理          │         │
│  │ 扫描     │ Client      │ 集成       │                   │         │
│  └──────────┴─────────────┴────────────┴───────────────────┘         │
│                                    │                                  │
└────────────────────────────────────┼──────────────────────────────────┘
               Gitea REST API         │                      │ Gateway API
┌──────────────────────────────────▼───┐                  │
│       Gitea 代码托管层 (本地部署)     │                  │
│  代码仓库管理 / Git Flow / PR审核     │                  │
└──────────────────────────────────────┘                  │
                                                          │
┌─────────────────────────────────────────────────────────▼───────────┐
│                    10个命名Agent角色 (Hermes Profiles)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ HaiMei   │  │ HouXing  │  │ HouWang  │  │ HouFa    │           │
│  │ 海梅     │  │ 后兴     │  │ 后旺     │  │ 后发     │           │
│  │ 项目经理 │  │ 需求分析 │  │ 架构设计 │  │ 程序员   │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ HouDa    │  │ HouFu    │  │ HouGui   │  │ HouRong  │           │
│  │ 后达     │  │ 后富     │  │ 后贵     │  │ 后荣     │           │
│  │ 测试员   │  │ CI/CD    │  │ 文档管理 │  │ QA       │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│  ┌──────────┐                                                       │
│  │ HouHua   │                                                       │
│  │ 后华     │                                                       │
│  │ 安全员   │                                                       │
│  └──────────┘                                                       │
└──────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│                          Agent蜂群层                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │Claude   │ │ Codex   │ │Opencode │ │ Cursor  │ │CodeArts │      │
│  │Code     │ │         │ │         │ │         │ │         │      │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘      │
│  ┌─────────┐ ┌─────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │ Trae    │ │ Lingma  │ │hermes子agent    │ │pi-codeing-agent │  │
│  │         │ │         │ │                 │ │子agent          │  │
│  └─────────┘ └─────────┘ └─────────────────┘ └─────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│                          数据库层 (PostgreSQL)                         │
│  ┌───────────┬───────────┬──────────────┬───────────┬───────────┐   │
│  │ users     │ projects  │ requirements │ agents    │ tasks     │   │
│  └───────────┴───────────┴──────────────┴───────────┴───────────┘   │
│  ┌───────────┬───────────┬──────────────┬───────────┬───────────┐   │
│  │ groups    │ messages  │ meetings     │ qa_records│ repos      │   │
│  └───────────┴───────────┴──────────────┴───────────┴───────────┘   │
└───────────────────────────────────────────────────────────────────────┘
```

### 6.3 数据库设计概要

#### 核心表

1. **users** - 人类用户表
   - id, username, email, password_hash, role, created_at

2. **projects** - 项目表
   - id, name, description, creator_id, core_goal, status, current_step(1-16), created_at, completed_at

3. **requirements** - 需求表
   - id, project_id, content, version, is_locked, confirmed_at

4. **agents** - Agent角色表（10个命名Agent + 编程Agent蜂群）
   - id, name(唯一), agent_type, role_name, chinese_name, status(online/offline/busy), api_endpoint, config(JSON), created_at

5. **tasks** - 任务表
   - id, project_id, name, description, type, priority, assignee_agent, status, acceptance_criteria, step_number(1-16), is_atomic, parent_task_id, created_at, completed_at

6. **task_dependencies** - 任务依赖表
   - id, source_task_id, target_task_id, created_at

7. **agent_execution_logs** - Agent执行日志表
   - id, task_id, agent_id, execution_content, result, created_at

8. **qa_records** - QA检验记录表
   - id, task_id, qa_agent_id, acceptance_result(pass/fail), problem_details, review_dimensions(JSON), created_at

9. **groups** - 群组表（项目讨论群）
   - id, project_id, name, description, members(JSON数组), host_agent, mode, created_at

10. **group_messages** - 群聊消息表
    - id, group_id, sender, role, content, timestamp, is_streaming, metadata(JSON)

11. **meeting_outcomes** - 会议结果表
    - id, group_id, meeting_topic, host_agent, started_at, ended_at, minutes, decisions(JSON), todos(JSON), risks(JSON), open_issues(JSON)

12. **swarms** - Agent蜂群表
    - id, project_id, manager_agent_id(后发/后达), members(JSON), purpose, status, created_at

13. **notifications** - 通知表
    - id, user_id, project_id, content, type, is_read, created_at

#### 代码仓库相关表

1. **repos** - 代码仓库表
   - id, project_id, gitea_repo_id, name, url, ssh_url, http_url, default_branch, is_private, created_at

2. **repo_branches** - 分支表
   - id, repo_id, name, commit_sha, is_protected, created_at

3. **pull_requests** - PR表
   - id, repo_id, number, title, description, source_branch, target_branch, author, status, created_at, merged_at

4. **commits** - 提交记录表
   - id, repo_id, sha, message, author, created_at

5. **task_commits** - 任务与提交关联表
   - id, task_id, commit_id, created_at

***

## 7. 接口需求

### 7.1 API端点 (RESTful)

#### 7.1.1 用户与项目管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/auth/login | 人类用户登录 |
| POST | /api/projects | 人类用户创建项目（第一步） |
| GET | /api/projects/:id | 获取项目详情 |
| GET | /api/projects/:id/progress | 获取项目16步流程进度 |
| POST | /api/projects/:id/complete | 确认项目完成 |

#### 7.1.2 Agent角色管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/agents | 获取所有Agent列表（含10个命名Agent+蜂群Agent） |
| GET | /api/agents/:id | 获取指定Agent详情 |
| POST | /api/agents/register | 编程Agent注册（蜂群成员） |
| DELETE | /api/agents/:id | 移除Agent |
| GET | /api/profiles | 获取所有扫描到的Hermes Agent Profiles |
| POST | /api/agents/sync-hermes | 同步发现的profiles到数据库 |

#### 7.1.3 16步流程调度

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/projects/:id/step2 | 执行第二步：海梅确认核心目标+搭建组织架构 |
| POST | /api/projects/:id/step3 | 执行第三步：后兴需求分析 |
| POST | /api/projects/:id/step4 | 执行第四步：后旺架构设计 |
| POST | /api/projects/:id/step5 | 执行第五步：后富建立开发环境 |
| POST | /api/projects/:id/step6 | 执行第六步：海梅制订TDD测试用例计划 |
| POST | /api/projects/:id/step7 | 执行第七步：后发蜂群编写TDD测试用例 |
| POST | /api/projects/:id/step8 | 执行第八步：海梅制订代码编写计划 |
| POST | /api/projects/:id/step9 | 执行第九步：后发蜂群编写功能代码 |
| POST | /api/projects/:id/step10 | 执行第十步：后富部署到测试环境 |
| POST | /api/projects/:id/step11 | 执行第十一步：后达蜂群全面测试 |
| POST | /api/projects/:id/step12 | 执行第十二步：后华安全审计 |
| POST | /api/projects/:id/step13 | 执行第十三步：后富部署到生产环境 |
| POST | /api/projects/:id/step14 | 执行第十四步：后贵完善文档 |
| POST | /api/projects/:id/step15 | 执行第十五步：海梅报告交付成果 |
| POST | /api/projects/:id/step16 | 执行第十六步：用户满意度确认 |

#### 7.1.4 QA门控

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/qa/:task_id/inspect | 后荣检验产出 |
| GET | /api/qa/:project_id/records | 获取项目QA检验记录 |
| POST | /api/qa/:task_id/rollback | 退回重做 |

#### 7.1.5 Agent蜂群

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/swarms | 建立Agent蜂群 |
| GET | /api/swarms/:id | 获取蜂群详情 |
| POST | /api/swarms/:id/dispatch | 蜂群调度：分发任务 |
| GET | /api/swarms/:id/progress | 获取蜂群执行进度 |

#### 7.1.6 项目讨论群

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/groups | 获取所有群组列表 |
| POST | /api/groups | 创建群组 |
| GET | /api/groups/:group_id | 获取群组详情 |
| POST | /api/groups/:group_id/members | 添加成员 |
| GET | /api/groups/:group_id/messages | 获取群组历史消息 |

#### 7.1.7 Gateway通信

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/hermes/health | 检查Gateway健康状态 |
| POST | /api/hermes/chat | 与指定Agent对话（非流式） |
| POST | /api/hermes/chat/stream | 与Agent对话（流式SSE） |

#### 7.1.8 代码库管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/repos | 创建代码仓库 |
| GET | /api/repos/:repo_id | 获取仓库详情 |
| GET | /api/repos/:repo_id/branches | 获取分支列表 |
| POST | /api/repos/:repo_id/branches | 创建分支 |
| GET | /api/repos/:repo_id/pulls | 获取PR列表 |
| POST | /api/repos/:repo_id/pulls | 创建PR |
| POST | /api/repos/:repo_id/pulls/:number/merge | 合并PR |
| GET | /api/repos/:repo_id/commits | 获取提交记录 |
| POST | /api/repos/validate-commit | 验证提交规范 |

### 7.2 WebSocket事件

#### 7.2.1 核心事件

| 事件 | 描述 |
|------|------|
| project.step.started | 某步骤开始执行 |
| project.step.completed | 某步骤执行完成 |
| project.step.failed | 某步骤执行失败 |
| qa.inspection.passed | QA检验通过 |
| qa.inspection.failed | QA检验未通过 |
| task.assigned | 任务分配给Agent |
| task.status.changed | 任务状态变更 |
| project.completed | 项目完成通知 |

#### 7.2.2 群聊WebSocket端点

WebSocket端点: `ws://{host}/ws/group-chat`

| 客户端消息类型 | 描述 |
|-------------|------|
| subscribe | 订阅群组消息 |
| unsubscribe | 取消订阅 |
| send_message | 发送消息（支持@mention） |
| start_meeting | 启动会议 |
| stop_meeting | 停止会议 |
| meeting_intervention | 会议中用户干预 |

| 服务端事件类型 | 描述 |
|-------------|------|
| message_new | 新消息 |
| message_chunk | 流式内容块 |
| message_complete | 回复完成 |
| meeting_started | 会议开始 |
| meeting_minutes | 会议纪要 |
| task_created | 新任务创建 |

***

## 8. 验收标准

### 8.1 16步流程验收

#### 8.1.1 第一步验收：项目创建

- [ ] 人类用户可创建项目并提交初始需求
- [ ] 项目创建后自动在Gitea中创建代码仓库
- [ ] 生成唯一项目ID

#### 8.1.2 第二步验收：核心目标确认与组织架构搭建

- [ ] 海梅主动与人类用户对话
- [ ] 确认项目核心目标
- [ ] 搭建项目组织架构（9个Agent角色全部激活）
- [ ] 建立项目讨论群，所有Agent已加入
- [ ] 后荣检验核心目标和组织架构合格

#### 8.1.3 第三步验收：需求分析

- [ ] 海梅安排后兴与用户对话沟通需求
- [ ] 复杂项目召开需求评审会议
- [ ] 生成完整、准确的软件需求说明书
- [ ] 后荣检验需求说明书合格
- [ ] 检验合格的需求说明书已提交到代码库

#### 8.1.4 第四步验收：架构设计

- [ ] 海梅安排后旺进行架构设计
- [ ] 架构设计文档生成并经后荣检验合格
- [ ] 后端设计文档生成并经后荣检验合格
- [ ] 前端设计文档生成并经后荣检验合格
- [ ] 数据库设计文档生成并经后荣检验合格
- [ ] 全部合格的设计文档已提交到代码库

#### 8.1.5 第五步验收：开发环境搭建

- [ ] 海梅安排后富建立开发环境
- [ ] 开发环境可正常运行
- [ ] 后荣检验开发环境合格

#### 8.1.6 第六步验收：TDD测试用例计划

- [ ] 海梅制订《TDD测试用例编写计划》
- [ ] 每个测试用例是最小原子化的
- [ ] 每个测试用例有明确的、可量化的验收标准
- [ ] 后荣检验计划合格
- [ ] 检验合格的计划已提交到代码库

#### 8.1.7 第七步验收：TDD测试用例编写

- [ ] 海梅安排后发建立Agent蜂群
- [ ] 蜂群Agent成功完成TDD测试用例编写
- [ ] 后荣检验测试用例合格
- [ ] 检验合格的测试用例已提交到代码库

#### 8.1.8 第八步验收：代码编写计划

- [ ] 海梅制订《代码编写计划》
- [ ] 每个代码编写任务是最小原子化的
- [ ] 每个任务有测试用例一一对应
- [ ] 任务依赖关系正确，已画出依赖图
- [ ] 后荣检验计划合格
- [ ] 检验合格的计划已提交到代码库

#### 8.1.9 第九步验收：功能代码编写

- [ ] 海梅安排后发建立Agent蜂群
- [ ] 蜂群Agent按依赖图顺序完成代码编写
- [ ] 每个子任务经后荣检验合格
- [ ] 检验合格的代码已提交到代码库

#### 8.1.10 第十步验收：测试环境部署

- [ ] 海梅安排后富部署到测试环境
- [ ] 测试环境部署成功，应用可访问

#### 8.1.11 第十一步验收：全面测试

- [ ] 海梅安排后达建立测试Agent蜂群
- [ ] 单元测试执行完成
- [ ] 模块测试执行完成
- [ ] 集成测试执行完成
- [ ] 前端实操验证执行完成
- [ ] 后荣检验测试报告合格
- [ ] 检验合格的测试报告已提交到代码库

#### 8.1.12 第十二步验收：安全审计

- [ ] 海梅安排后华执行安全审计
- [ ] 代码审计完成
- [ ] 合规审查完成
- [ ] 渗透测试完成
- [ ] 漏洞修复完成
- [ ] 后荣检验安全审计报告合格
- [ ] 检验合格的安全审计报告已提交到代码库

#### 8.1.13 第十三步验收：生产环境部署

- [ ] 海梅安排后富部署到生产环境
- [ ] 生产环境部署成功，应用可正常使用

#### 8.1.14 第十四步验收：文档完善

- [ ] 海梅安排后贵完善项目文档
- [ ] 部署手册完整
- [ ] 操作手册完整
- [ ] 文档一致性保证（任一修改，其它同步更新）

#### 8.1.15 第十五步验收：交付报告

- [ ] 海梅向人类用户报告项目进展及交付成果
- [ ] 报告内容完整清晰

#### 8.1.16 第十六步验收：满意度确认与迭代

- [ ] 用户满意则项目结束
- [ ] 用户不满意则收集意见回到第三步重新迭代
- [ ] 迭代修改仍严格遵循16步流程
- [ ] 项目结束时在代码库中打版本标签

### 8.2 QA门控验收

- [ ] 每步产出必须经后荣(QA)检验
- [ ] 检验合格方可进入下一步
- [ ] 检验不合格退回重做，附带修改建议
- [ ] 检验合格的产出全部提交到代码库
- [ ] QA检验记录完整保存在qa_records表
- [ ] QA检验维度按产出类型正确匹配

### 8.3 Agent蜂群验收

- [ ] 后发可建立代码编写Agent蜂群
- [ ] 后达可建立代码测试Agent蜂群
- [ ] 蜂群成员支持：Claude Code/Codex/Opencode/Cursor/CodeArts/Trae/Lingma/hermes子agent/pi-codeing-agent子agent
- [ ] 蜂群调度者负责任务分发、进度监控、成果收集
- [ ] 蜂群Agent可通过任务执行接口接收任务、上报进度、交付成果

### 8.4 项目讨论群验收

- [ ] 项目创建后自动建立项目讨论群
- [ ] 所有10个Agent已加入讨论群
- [ ] 讨论模式：成员可自主发言、@mention定向沟通
- [ ] 会议模式：主持人控场、议程驱动、产出结构化纪要
- [ ] 支持4种会议类型：需求评审会、技术方案讨论会、每日站会、故障复盘会

### 8.5 Hermes Agent安装与Profile发现验收

- [ ] Hermes Agent可通过一键脚本正常安装
- [ ] Profile Scanner可自动扫描用户profiles目录
- [ ] 可正确识别每个profile的名称、模型配置、Gateway端口
- [ ] Gateway API通信正常（流式/非流式）

### 8.6 Gitea代码仓库管理验收

- [ ] 可通过Docker Compose部署Gitea服务
- [ ] 项目创建时自动在Gitea中创建代码仓库
- [ ] Git Flow分支策略正确（main/develop/feature/release/hotfix）
- [ ] 代码提交规范验证正确
- [ ] PR流程正确（创建/审查/合并）
- [ ] 检验合格的产出全部提交到代码库

### 8.7 非功能验收

- [ ] 页面加载时间 < 2秒，Agent响应时间 < 3秒
- [ ] 支持20个项目并发执行
- [ ] 系统无严重安全漏洞
- [ ] Agent执行失败时可自动重试/切换Agent
- [ ] 群聊消息延迟 < 100ms（局域网内）
- [ ] WebSocket断线后可自动重连
- [ ] 接口文档完整，支持新增编程Agent快速接入

***

文档结束
