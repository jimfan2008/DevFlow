# DevFlow - AI Agent 驱动的全自动开发平台

## 项目概述

DevFlow 是一个面向人类用户与 AI Agent 协同的全自动化软件开发项目管理平台。
核心功能包括：项目创建、需求分析、架构设计、开发环境搭建、TDD测试用例编写、
代码编写、测试验证、安全审计、部署交付、文档管理、QA门控的全流程自动化。

## 技术栈

### 后端
- Python 3.11 + FastAPI 0.109+
- SQLAlchemy 2.0 + Alembic 1.13+
- Celery 5.3 + Redis 7.x
- PostgreSQL 15
- Pydantic Settings 2.0+
- Uvicorn 0.27+

### 前端
- Vue.js 3.4+ + Vite 5.0+ + TypeScript 5.x
- Element Plus 2.5+
- Pinia 2.1+ + Vue Router 4.2+
- Axios 1.6+
- Vue I18n 9.x

### 基础设施
- Docker + Docker Compose
- Nginx 1.24 (反向代理)
- Gitea 1.21 (代码托管)
- Ollama (本地 LLM 推理)
- Prometheus + Grafana + Loki + Alertmanager (监控)

## 16步标准流程

1. 人类用户创建新的软件项目
2. 海梅主动与人类用户对话，确认项目核心目标并搭建组织架构
3. 海梅安排后兴与用户对话，产出软件需求说明书
4. 海梅安排后旺进行架构设计
5. 海梅安排后旺进行后端设计
6. 海梅安排后旺进行前端设计
7. 海梅安排后旺进行数据库设计
8. 海梅安排后富建立开发环境
9. 海梅安排后发建立编程Agent蜂群，完成TDD测试用例编写
10. 海梅安排后发建立编程Agent蜂群，完成代码编写
11. 海梅安排后达建立测试Agent蜂群，执行单元测试
12. 海梅安排后达建立测试Agent蜂群，执行集成测试
13. 海梅安排后华进行安全审计
14. 海梅安排后富进行部署交付
15. 海梅安排后贵进行文档整理
16. 海梅安排后达进行前端实操验证，项目验收

## 9个命名Agent角色

| Agent | 中文名 | 角色 | 职责 |
|-------|--------|------|------|
| HaiMei | 海梅 | 项目经理 | 任务分派、协调所有Agent工作、对项目交付成果负责 |
| HouXing | 后兴 | 需求分析师 | 需求分析、与用户沟通、产出SRS |
| HouWang | 后旺 | 架构设计师 | 架构/前后端/数据库设计 |
| HouFa | 后发 | 程序员 | 建立编程Agent蜂群、监督TDD和代码编写 |
| HouDa | 后达 | 测试员 | 建立测试Agent蜂群、执行各类测试 |
| HouFu | 后富 | CI/CD工程师 | 开发环境搭建、代码部署 |
| HouGui | 后贵 | 文档管理员 | 项目文档一致性管理 |
| HouRong | 后荣 | QA | 检验每个Agent产出物、门控放行 |
| HouHua | 后华 | 安全员 | 代码审计、合规审查、渗透测试、漏洞修复 |

## 快速开始

### 环境要求
- Docker 24.0+
- Docker Compose
- Python 3.11
- Node.js 18+
- Git 2.25+

### 启动服务

```bash
# 1. 克隆仓库
git clone <repository-url>
cd devflow

# 2. 配置环境变量
cp docker/.env.example docker/.env
# 编辑 .env 文件，设置必要的配置

# 3. 启动基础设施服务
docker compose -f docker/docker-compose.infra.yml up -d

# 4. 初始化数据库
cd backend
pip install -e .
alembic upgrade head

# 5. 启动后端服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 6. 启动前端开发服务器
cd ../frontend
npm install
npm run dev
```

## 项目结构

```
devflow/
├── README.md
├── .gitignore
├── .env.example
├── .github/
│   └── workflows/
│       ├── backend-ci.yml
│       ├── frontend-ci.yml
│       └── deploy.yml
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.infra.yml
│   ├── .env.example
│   └── nginx/
├── backend/
│   ├── README.md
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── tasks/
│   │   └── monitoring/
│   ├── alembic/
│   ├── tests/
│   └── docker/
├── frontend/
│   ├── README.md
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── api/
│   │   ├── components/
│   │   ├── composables/
│   │   ├── layouts/
│   │   ├── router/
│   │   ├── stores/
│   │   ├── views/
│   │   ├── i18n/
│   │   ├── utils/
│   │   └── types/
│   └── tests/
├── docs/
│   ├── devflow_SRS_V6.md
│   ├── devflow_ARCHITECTURE_V26.md
│   ├── devflow_FRONTEND_V24.md
│   ├── devflow_BACKEND_V44.md
│   ├── devflow_DATABASE_V37.md
│   └── devflow_env_V1.md
└── scripts/
    └── init-db.sh
```

## 开发规范

### Git 分支策略 (Git Flow)
- `main` - 生产环境分支
- `develop` - 开发环境分支
- `feature/*` - 功能分支
- `release/*` - 发布分支
- `hotfix/*` - 热修复分支

### 提交消息规范 (Conventional Commits)
- `feat:` - 新功能
- `fix:` - 修复bug
- `docs:` - 文档更新
- `style:` - 代码格式
- `refactor:` - 重构
- `test:` - 测试
- `chore:` - 构建/工具链

## 许可证

Proprietary - DevFlow Team
