# GBM AI Agent HR 智能人力管理系统

AI 原生的 HR 管理平台，基于零操作性原则设计 —— 所有可操作性事务由 AI Agent 自主执行，人类用户仅负责战略性审核、争议仲裁和政策制定。

## 系统架构

- **后端**: Python 3.11+ / FastAPI
- **数据库**: MySQL 8.0 (4 schema: hr_user/hr_recruit/hr_payroll/hr_auto)
- **缓存**: Redis 7.x
- **消息队列**: Kafka 3.x + RabbitMQ 3.12
- **对象存储**: MinIO
- **搜索引擎**: Elasticsearch 8.x
- **AI**: LangChain + LangGraph + OpenAI/Claude/Qwen
- **RPA**: Playwright + Selenium
- **OCR**: PaddleOCR
- **人脸识别**: InsightFace (ONNX)

## 快速开始

### 环境要求

- Python 3.11+
- Docker 24.x+
- Git 2.30+

### 安装

```bash
# 安装依赖
pip install -e ".[dev]"
playwright install chromium

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入真实配置
```

### 启动

```bash
# 启动基础设施
docker-compose up -d mysql redis minio kafka rabbitmq elasticsearch

# 初始化数据库
bash scripts/setup_db.sh

# 启动应用
make dev

# 启动 Worker
make dev-worker
```

### 访问

| 服务 | 地址 |
|------|------|
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| MinIO Console | http://localhost:9001 |
| RabbitMQ Management | http://localhost:15672 |
| Flower (Celery) | http://localhost:5555 |

## 项目结构

```
gbm-ai-agent-hr/
├── app/                    # 应用代码
│   ├── main.py             # FastAPI 入口
│   ├── core/               # 核心配置
│   ├── agent/              # AI Agent 实现
│   ├── routers/            # API 路由
│   ├── schemas/            # Pydantic 模型
│   ├── services/           # 业务逻辑
│   ├── middleware/         # 中间件
│   └── tests/              # 测试
├── database/               # 数据库脚本
├── alembic/                # 数据库迁移
├── nginx/                  # Nginx 配置
├── scripts/                # 运维脚本
├── docs/                   # 文档
├── .github/workflows/      # CI/CD
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── Makefile
└── .env.example
```

## AI Agent 清单

| Agent | 模块 | 职责 |
|-------|------|------|
| 招聘 Agent | 招聘管理 | 简历抓取、匹配评分、分拣 |
| 组卷 Agent | 招聘管理 | 智能抽题生成试卷 |
| 阅卷 Agent | 招聘管理 | 自动批阅客/主观题 |
| 入职 Agent | 入职管理 | 引导新人完成材料提交 |
| OCR Agent | 入职管理 | 证件信息识别提取 |
| 人脸 Agent | 入职管理 | 人脸采集与比对建档 |
| 培训 Agent | 培训管理 | 培训全流程管理 |
| 考勤 Agent | 考勤管理 | 数据汇集与异常识别 |
| 薪资 Agent | 薪资管理 | 全自动月度薪资核算 |
| 绩效 Agent | 绩效管理 | 考核流程收集汇总 |
| 外务 Agent | 外务管理 | 工伤+公积金 RPA 自动化 |
| RPA Agent | 外务管理 | 政府网站自动填报 |

## 数据库 Schema

| Schema | 说明 | 核心表 |
|--------|------|--------|
| hr_user | 用户/员工/RBAC | employee_*, sys_user, sys_role, department |
| hr_recruit | 招聘/考试 | resume, recruitment_process, exam_*, interview_record |
| hr_payroll | 考勤/薪资/绩效 | attendance_record, payroll, performance_review |
| hr_auto | 外务/审计/Agent | audit_log, agent_run_log, rpa_task, injury_case |

## Makefile 命令

| 命令 | 说明 |
|------|------|
| `make setup` | 安装依赖 |
| `make dev` | 启动开发服务器 |
| `make test` | 运行测试 |
| `make lint` | 代码检查 |
| `make format` | 代码格式化 |
| `make docker-up` | 启动 Docker 服务 |
| `make db-init` | 初始化数据库 |
| `make migrate` | 运行数据库迁移 |

## 文档

- [需求规格说明书 (SRS V15)](docs/gbm-ai-agent-hr_SRS_V15.md)
- [后端设计文档 (V35)](docs/gbm-ai-agent-hr_BACKEND_V35.md)
- [数据库设计文档 (V19)](docs/gbm-ai-agent-hr_DATABASE_V19.md)
- [架构设计文档 (V24)](docs/gbm-ai-agent-hr_ARCHITECTURE_V24.md)
- [前端设计文档 (V26)](docs/gbm-ai-agent-hr_FRONTEND_V26.md)
- [环境配置文档 (V1)](docs/gbm-ai-agent-hr_env_V1.md)

## 安全

- AES-256 加密敏感字段
- TLS 1.2+ 传输加密
- RBAC 基于角色的访问控制
- 审计日志 (不可篡改，≥ 10 年)
- MFA 二次认证

## 许可证

Proprietary - GBM AI Agent HR
