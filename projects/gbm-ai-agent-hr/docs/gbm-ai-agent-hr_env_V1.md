# GBM AI Agent HR - Development Environment Configuration V1

## 版本信息

| 字段 | 值 |
|------|-----|
| 文档名称 | GBM AI Agent HR 开发环境配置文档 |
| 版本号 | V1.0 |
| 基于 SRS | V15.0 |
| 基于后端设计 | V35.0 |
| 基于数据库设计 | V19.0 |
| 日期 | 2026-06-22 |
| 作者 | 后富 (HouFu) |
| 角色 | CI/CD 工程师 |

---

## 1. 项目概述

| 属性 | 值 |
|------|-----|
| 项目名称 | GBM AI Agent HR 智能人力管理系统 |
| 项目ID | 04308c14-31c7-4cfe-aed0-58f7019e907c |
| 核心目标 | AI 原生的 HR 系统，AI Agent 驱动，全自动化 |
| 设计原则 | 零操作性原则 —— 所有可操作性事务由 AI Agent 自主执行 |
| 仓库路径 | /home/jim/DevFlow/projects/gbm-ai-agent-hr/ |
| Git 远程 | 本地 Git 仓库 |

---

## 2. 技术栈

### 2.1 后端服务

| 组件 | 技术选型 | 版本 |
|------|---------|------|
| 框架 | FastAPI | >= 0.110.0 |
| 服务器 | Uvicorn + Gunicorn | >= 0.27.0 / >= 21.2.0 |
| 语言 | Python | >= 3.11 |
| ORM | SQLAlchemy | >= 2.0.25 |
| 数据库迁移 | Alembic | >= 1.13.0 |
| 任务队列 | Celery + RabbitMQ | >= 5.3.6 |
| 配置管理 | Pydantic Settings | >= 2.5.0 |

### 2.2 AI / ML 服务

| 组件 | 技术选型 | 版本 |
|------|---------|------|
| LLM 集成 | OpenAI SDK | >= 1.6.0 |
| LLM 集成 | Anthropic SDK | >= 0.18.0 |
| Agent 框架 | LangChain + LangGraph | >= 0.1.0 / >= 0.0.20 |
| 向量检索 | Sentence Transformers + FAISS | >= 2.3.1 / >= 1.7.4 |
| OCR 引擎 | PaddleOCR | >= 2.7.0 |
| 人脸识别 | Face-API.py | >= 0.7.0 |
| RPA 引擎 | Playwright + Selenium | >= 1.40.0 / >= 4.16.0 |

### 2.3 数据基础设施

| 组件 | 技术选型 | 版本 | 用途 |
|------|---------|------|------|
| 主数据库 | MySQL 8.0 | 8.x | 4 个独立 schema (hr_user/hr_recruit/hr_payroll/hr_auto) |
| 缓存 | Redis | 7.x | 会话、热点数据、Agent 锁 |
| 消息队列 | RabbitMQ | 3.12+ | Agent 间通信、Celery Broker |
| 事件总线 | Kafka | 3.x | Agent 结果回传 (rpa.result/ocr.result/face.result) |
| 对象存储 | MinIO | latest | 简历、证件、视频、回执等文件存储 |
| 搜索引擎 | Elasticsearch | 8.12+ | 简历搜索、日志检索 |
| 认证服务 | Keycloak | 23.0 | SSO 统一认证 (可选) |

### 2.4 基础设施

| 组件 | 技术选型 | 版本 |
|------|---------|------|
| 容器化 | Docker | 24.x |
| 编排 | Docker Compose | 3.8 |
| 反向代理 | Nginx | latest |
| CI/CD | GitHub Actions | - |
| 监控 | Prometheus + Grafana | latest |
| 代码质量 | pre-commit + black + isort + flake8 + mypy | - |

---

## 3. 开发环境要求

### 3.1 硬件要求

| 资源 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 8 核 | 16 核 |
| 内存 | 32 GB | 64 GB |
| 存储 | 500 GB SSD | 1 TB SSD |
| GPU | 无 (云服务 OCR/人脸) | NVIDIA 8GB+ VRAM (本地推理) |

### 3.2 软件要求

| 软件 | 版本 | 用途 |
|------|------|------|
| OS | Ubuntu 22.04 LTS / WSL2 | 开发/运行环境 |
| Python | >= 3.11 | 后端应用 |
| Docker | >= 24.x | 容器化部署 |
| Docker Compose | >= 2.x | 服务编排 |
| Git | >= 2.30 | 版本控制 |
| pip | >= 23.x | Python 包管理 |

---

## 4. 项目结构

```
gbm-ai-agent-hr/
├── app/                          # 应用主目录
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用入口
│   ├── config/                   # 配置模块
│   │   ├── settings.py
│   │   ├── database.py
│   │   ├── redis_config.py
│   │   └── ai_models.py
│   ├── core/                     # 核心模块
│   │   ├── app.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── lifespan.py
│   │   └── security.py
│   ├── models/                   # 数据模型 (SQLAlchemy ORM)
│   │   ├── base.py
│   │   ├── employee.py
│   │   ├── resume.py
│   │   ├── attendance.py
│   │   ├── payroll.py
│   │   ├── performance.py
│   │   ├── injury.py
│   │   └── agent_log.py
│   ├── schemas/                  # Pydantic 数据模式
│   │   ├── employee.py
│   │   ├── resume.py
│   │   ├── attendance.py
│   │   ├── payroll.py
│   │   └── auth.py
│   ├── routers/                  # API 路由
│   │   ├── employees.py
│   │   ├── resumes.py
│   │   ├── attendance.py
│   │   ├── payroll.py
│   │   ├── performance.py
│   │   └── auth.py
│   ├── agent/                    # AI Agent 实现 (18 个 Agent)
│   │   ├── orchestrator.py       # Agent 编排器
│   │   ├── recruitment.py        # 招聘 Agent
│   │   ├── onboarding.py         # 入职 Agent
│   │   ├── training.py           # 培训 Agent
│   │   ├── attendance.py         # 考勤 Agent
│   │   ├── payroll.py            # 薪资 Agent
│   │   ├── performance.py        # 绩效 Agent
│   │   ├── external_affairs.py   # 外务 Agent
│   │   ├── rpa.py                # RPA Agent
│   │   ├── ocr.py                # OCR Agent
│   │   ├── video.py              # 视频 Agent
│   │   └── certificate.py        # 证书 Agent
│   ├── services/                 # 业务服务层
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── audit_service.py
│   │   └── notification_service.py
│   ├── middleware/               # 中间件
│   │   ├── auth_middleware.py
│   │   ├── rbac_middleware.py
│   │   └── audit_middleware.py
│   ├── utils/                    # 工具函数
│   │   ├── encryption.py
│   │   ├── security.py
│   │   └── helpers.py
│   └── tests/                    # 测试
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_payroll.py
│       └── test_resumes.py
├── database/                     # 数据库脚本
│   └── init.sql                  # 初始化 SQL (4 schema)
├── alembic/                      # 数据库迁移
│   ├── env.py
│   ├── script.py.mako
│   ├── versions/                 # 迁移脚本
│   └── 001_initial_schema.py
├── alembic.ini                   # Alembic 配置
├── Dockerfile                    # 容器化构建
├── docker-compose.yml            # 服务编排 (12 个服务)
├── pyproject.toml                # Python 项目配置
├── .env.example                  # 环境变量模板
├── .gitignore                    # Git 忽略规则
├── .pre-commit-config.yaml       # Pre-commit 钩子
├── nginx/                        # Nginx 配置
│   └── nginx.conf
├── monitoring/                   # 监控配置
│   ├── prometheus.yml
│   └── grafana/
│       └── dashboards/
│           ├── dashboards.yml
│           └── gbm-hr-overview.json
├── .github/workflows/            # CI/CD 流水线
│   ├── ci.yml                    # 持续集成
│   ├── cd.yml                    # 持续部署
│   └── scheduled.yml             # 定时检查
├── docs/                         # 文档
│   ├── gbm-ai-agent-hr_SRS_V15.md
│   ├── gbm-ai-agent-hr_BACKEND_V35.md
│   ├── gbm-ai-agent-hr_DATABASE_V19.md
│   └── gbm-ai-agent-hr_env_V1.md  # 本文档
├── data/                         # 数据目录
├── uploads/                      # 上传文件
├── logs/                         # 日志目录
└── README.md
```

---

## 5. 环境变量配置

### 5.1 完整环境变量列表

基于 `.env.example` 文件，完整环境变量如下：

```bash
# === 应用配置 ===
APP_NAME="GBM AI Agent HR"
APP_VERSION="1.0.0"
DEBUG=false
SECRET_KEY=CHANGE_ME_TO_RANDOM_STRING
ALLOWED_HOSTS=http://localhost,http://localhost:8000,http://localhost:3000

# === 数据库配置 (MySQL 8.x, 4 schema) ===
DB_HOST=localhost
DB_PORT=3306
DB_USER=hr_admin
DB_PASSWORD=CHANGE_ME_DB_PASSWORD
DB_NAME=gbm_hr_db
DB_CHARSET=utf8mb4
SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_MAX_OVERFLOW=10
SQLALCHEMY_ECHO=false

# === Redis 配置 ===
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=CHANGE_ME_REDIS_PASSWORD
REDIS_DB=0
REDIS_DEFAULT_TTL=3600

# === RabbitMQ 配置 ===
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# === Kafka 配置 (Agent 结果回传) ===
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# === JWT 认证 ===
JWT_SECRET_KEY=CHANGE_ME_JWT_SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# === AI/LLM 服务配置 ===
OPENAI_API_KEY=CHANGE_ME_OPENAI_KEY
OPENAI_MODEL=gpt-4o
ANTHROPIC_API_KEY=CHANGE_ME_ANTHROPIC_KEY
ANTHROPIC_MODEL=claude-3-opus-20240229

# === OCR 服务 ===
OCR_ENGINE=paddleocr
OCR_MODEL_DIR=./models/ocr

# === 人脸识别 ===
FACE_API_KEY=CHANGE_ME_FACE_API_KEY
FACE_API_SECRET=CHANGE_ME_FACE_API_SECRET
FACE_THRESHOLD=0.85

# === 对象存储 (MinIO) ===
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=CHANGE_ME_MINIO_PASSWORD
MINIO_BUCKET_NAME=hr-documents
MINIO_SECURE=false

# === Celery 任务队列 ===
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=redis://:CHANGE_ME_REDIS_PASSWORD@localhost:6379/1

# === Elasticsearch ===
ELASTICSEARCH_URL=http://localhost:9200

# === 邮件服务 ===
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=hr-noreply@example.com
SMTP_PASSWORD=CHANGE_ME_SMTP_PASSWORD
SMTP_USE_TLS=true

# === 短信服务 ===
SMS_PROVIDER=aliyun
SMS_ACCESS_KEY=CHANGE_ME_SMS_KEY
SMS_ACCESS_SECRET=CHANGE_ME_SMS_SECRET
SMS_SIGN_NAME=GBM-HR

# === 外务 RPA 凭证 ===
SOCIAL_SECURITY_USERNAME=CHANGE_ME_SS_USERNAME
SOCIAL_SECURITY_PASSWORD=CHANGE_ME_SS_PASSWORD
HOUSING_FUND_USERNAME=CHANGE_ME_HF_USERNAME
HOUSING_FUND_PASSWORD=CHANGE_ME_HF_PASSWORD

# === 审计日志 ===
AUDIT_LOG_RETENTION_YEARS=10
AUDIT_LOG_PATH=/var/log/gbm-hr/audit

# === 监控 ===
SENTRY_DSN=
METRICS_ENABLED=true
METRICS_PORT=9090

# === 文件存储 ===
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=50
ALLOWED_EXTENSIONS=.pdf,.doc,.docx,.xlsx,.xls,.jpg,.jpeg,.png,.bmp

# === 备份 ===
BACKUP_DIR=/var/backups/gbm-hr
BACKUP_RETENTION_DAYS=15
BACKUP_SCHEDULE=0 2 * * 0

# === Keycloak SSO (可选) ===
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin
KEYCLOAK_URL=http://localhost:8080

# === 监控 (Grafana/Prometheus) ===
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_PASSWORD=admin
```

---

## 6. 数据库架构

### 6.1 Schema 分配 (基于 DATABASE_V19)

| Schema | 用途 | 核心表 |
|--------|------|--------|
| hr_user | 用户、员工、组织架构 | sys_user, sys_role, sys_permission, employee, department, audit_log |
| hr_recruit | 招聘、简历、面试 | resume, job_position, recruitment_process, exam_paper, exam_question, exam_answer |
| hr_payroll | 薪资、考勤、绩效 | attendance_record, payroll, payroll_rule, performance_review, salary_change_history |
| hr_auto | 培训、外务、工伤、证书 | training_plan, training_attendance, injury_case, certificate, rpa_task, face_feature |

### 6.2 初始化命令

```bash
# 使用 Docker Compose 启动数据库
docker-compose up -d mysql

# 等待数据库就绪
docker-compose exec mysql mysqladmin ping -h localhost --wait=30

# 验证 schema 创建
docker-compose exec mysql mysql -u hr_admin -p -e "SHOW DATABASES;"
```

### 6.3 Alembic 迁移

```bash
# 初始化迁移环境
alembic init alembic

# 创建新迁移
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看迁移状态
alembic current
```

---

## 7. Docker 服务

### 7.1 服务列表 (12 个服务)

| 服务 | 镜像 | 端口 | 用途 |
|------|------|------|------|
| mysql | mysql:8.0 | 3306 | 主数据库 (4 schema) |
| redis | redis:7-alpine | 6379 | 缓存/会话/Agent 锁 |
| rabbitmq | rabbitmq:3.12-management | 5672/15672 | 消息队列 |
| minio | minio/minio | 9000/9001 | 对象存储 |
| minio-init | minio/mc | - | 初始化 bucket |
| elasticsearch | elasticsearch:8.12 | 9200 | 搜索/日志 |
| backend | 自构建 (FastAPI) | 8000 | 主应用 |
| celery-worker | 自构建 | - | 异步任务 |
| celery-beat | 自构建 | - | 定时任务 |
| nginx | nginx | 80 | 反向代理 |
| prometheus | prom/prometheus | 9090 | 监控指标 |
| grafana | grafana/grafana | 3000 | 监控仪表盘 |

### 7.2 启动命令

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend

# 停止所有服务
docker-compose down

# 停止并清除数据卷
docker-compose down -v

# 仅启动数据库和缓存
docker-compose up -d mysql redis rabbitmq
```

---

## 8. CI/CD 流水线

### 8.1 持续集成 (ci.yml)

触发: push 到 main/develop 分支 或 PR 到 main

| Job | 工具 | 用途 |
|-----|------|------|
| lint | flake8 + black + isort | 代码风格检查 |
| type-check | mypy | 类型检查 |
| unit-test | pytest + coverage | 单元测试 (覆盖率 >= 80%) |
| security-scan | bandit + safety | 安全扫描 |
| build-docker | docker build | Docker 镜像构建 |

### 8.2 持续部署 (cd.yml)

触发: push 到 main 分支

| Job | 用途 |
|-----|------|
| build-and-push | 构建并推送 Docker 镜像到 Registry |
| deploy-staging | 部署到预发环境 |

### 8.3 定时检查 (scheduled.yml)

| Job | 频率 | 用途 |
|-----|------|------|
| dependency-update | 每周 | 检查过期依赖 |
| security-scan | 每天 | 安全漏洞扫描 |

---

## 9. 本地开发流程

### 9.1 环境搭建

```bash
# 1. 克隆项目
cd /home/jim/DevFlow/projects/gbm-ai-agent-hr

# 2. 创建虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -e ".[dev]"

# 4. 安装 Playwright 浏览器
playwright install chromium

# 5. 复制环境变量
cp .env.example .env
# 编辑 .env 填入真实值

# 6. 启动基础设施服务
docker-compose up -d mysql redis rabbitmq minio elasticsearch

# 7. 等待服务就绪
sleep 30

# 8. 执行数据库迁移
alembic upgrade head

# 9. 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

### 9.2 代码质量检查

```bash
# 安装 pre-commit hooks
pre-commit install

# 运行所有检查
pre-commit run --all-files

# 单独运行
black app/
isort app/
flake8 app/
mypy app/
pytest --cov=app --cov-report=term-missing
bandit -r app/ -ll
safety check
```

### 9.3 测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest app/tests/test_auth.py

# 带覆盖率报告
pytest --cov=app --cov-report=html

# 并行运行
pytest -n auto
```

---

## 10. 安全配置

### 10.1 敏感信息管理

- 所有敏感信息存储在 `.env` 文件中
- `.env` 文件已添加到 `.gitignore`
- 生产环境使用 Vault 或类似密钥管理服务
- AES-256 加密存储员工敏感数据 (身份证号、人脸特征等)

### 10.2 认证与授权

- JWT Token 认证 (HS256 算法)
- RBAC 基于角色的访问控制
- 行级数据隔离 (部门主管仅查看本部门数据)
- MFA 二因子认证 (管理员、薪资访问等高风险操作)
- 审计日志保留 >= 10 年

### 10.3 网络安全

- TLS 1.2+ 强制加密传输
- CORS 跨域策略配置
- 速率限制 (API: 10r/s, 登录: 1r/s)
- XSS/CSRF/SQL 注入防护

---

## 11. 监控与告警

### 11.1 Prometheus 指标

| 指标 | 用途 |
|------|------|
| CPU 使用率 | 应用资源监控 |
| 内存使用 | 内存泄漏检测 |
| HTTP 请求速率 | API 流量监控 |
| 响应时间 P95 | 性能监控 |
| Agent 成功率 | Agent 运行质量 |
| Agent 平均耗时 | Agent 效率 |

### 11.2 Grafana 仪表盘

- 系统概览 (CPU/内存/磁盘)
- API 性能 (请求速率/响应时间)
- Agent 运行状态 (成功率/耗时)
- 数据库连接池
- 消息队列积压

### 11.3 告警阈值 (SRS V15 4.7.1)

| 监控项 | 告警阈值 |
|--------|---------|
| CPU 利用率 | 持续 5min > 85% |
| 内存利用率 | 持续 5min > 90% |
| 磁盘空间 | 使用率 > 80% |
| DB 连接池 | > 80% |
| API 响应延时 P95 | > 5s |
| Agent 操作成功率 | < 95% |

---

## 12. 部署拓扑

### 12.1 开发环境

```
[Developer Machine]
    ├── VS Code / PyCharm
    ├── Docker Desktop
    │   ├── MySQL:3306
    │   ├── Redis:6379
    │   ├── RabbitMQ:5672
    │   ├── MinIO:9000
    │   ├── Elasticsearch:9200
    │   ├── Backend:8000
    │   ├── Celery Worker
    │   ├── Celery Beat
    │   ├── Nginx:80
    │   ├── Prometheus:9090
    │   └── Grafana:3000
    └── Browser: http://localhost
```

### 12.2 生产环境 (推荐)

```
[Load Balancer]
    └── Nginx Ingress
        ├── backend:8000 (x3 replicas)
        ├── celery-worker (x2 replicas)
        ├── celery-beat (x1)
        └── MinIO:9000

[Data Layer]
    ├── MySQL 8.x (Primary/Replica)
    ├── Redis Cluster
    ├── RabbitMQ Cluster
    ├── Kafka Cluster
    └── Elasticsearch

[Monitoring]
    ├── Prometheus
    └── Grafana
```

---

## 13. 备份与恢复

### 13.1 备份策略 (SRS V15 6.4)

| 类型 | 频率 | 保留 |
|------|------|------|
| 全量备份 | 每周一次 | >= 15 年 |
| 增量备份 | 每天一次 | >= 15 年 |
| 恢复演练 | 每季度一次 | - |

### 13.2 备份命令

```bash
# 数据库备份
docker-compose exec mysql mysqldump -u hr_admin -p --all-databases > backup_$(date +%Y%m%d).sql

# MinIO 备份
mc mirror myminio/hr-documents backup/hr-documents

# 恢复数据库
docker-compose exec -T mysql mysql -u hr_admin -p < backup_YYYYMMDD.sql
```

---

## 14. 故障排查

### 14.1 常见问题

| 问题 | 解决方案 |
|------|---------|
| 数据库连接失败 | 检查 MySQL 容器是否运行，验证 .env 中的数据库凭据 |
| Redis 连接被拒 | 检查 Redis 密码是否与 .env 一致 |
| Celery 任务不执行 | 检查 RabbitMQ 连接，确认 worker 进程运行 |
| OCR 识别失败 | 检查 PaddleOCR 模型是否下载，验证 GPU 可用性 |
| Agent 超时 | 检查 LLM API 配额，增加超时配置 |

### 14.2 日志查看

```bash
# 查看后端日志
docker-compose logs -f backend

# 查看 Celery 日志
docker-compose logs -f celery-worker

# 查看数据库日志
docker-compose logs -f mysql

# 查看 Nginx 访问日志
docker-compose logs -f nginx
```

---

*文档结束*
