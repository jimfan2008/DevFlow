# GBM AI Agent HR - 开发环境配置文档 V1

## 基本信息

| 字段 | 值 |
|------|-----|
| 项目名称 | GBM AI Agent HR 智能人力管理系统 |
| 项目ID | 04308c14-31c7-4cfe-aed0-58f7019e907c |
| 文档版本 | V1.0 |
| 基于 SRS | V15.0 |
| 基于架构设计 | ARCHITECTURE_V24 |
| 基于后端设计 | BACKEND_V35 |
| 基于数据库设计 | DATABASE_V19 |
| 基于前端设计 | FRONTEND_V26 |
| 创建日期 | 2026-06-22 |
| 创建者 | 后富 (HouFu) |

---

## 1. 技术栈总览

### 1.1 后端技术栈

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| 语言 | Java | 17 LTS | 企业级稳定性 |
| 框架 | Spring Boot | 3.2.x | 4 个独立域服务 |
| ORM | MyBatis-Plus | 3.5.x | 灵活 SQL 控制 |
| 认证 | Keycloak SSO | 22.x | OAuth 2.0 + JWT |
| 消息队列 | Kafka | 3.x (3 节点集群) | 跨域事件总线 |
| 流程引擎 | Camunda 8 (Zeebe) | 8.x | BPMN 2.0 编排 |
| 缓存 | Redis | 7.2.x | Redisson 客户端 |
| 配置管理 | application.yml + Spring Profile | - | 按环境差异化配置 |
| 链路追踪 | OpenTelemetry | 1.x | 分布式追踪 |
| 对象存储 | MinIO SDK | 8.x | 文件上传/下载 |
| 弹性容错 | Resilience4j | 2.x | 熔断/限流/重试 |
| 密钥管理 | .env 文件 | - | 敏感配置统一管理 |
| 定时任务 | Spring @Scheduled + Quartz | - | 各域独立调度 |

### 1.2 Python 子服务

| 服务 | 端口 | 技术栈 | 用途 |
|------|------|--------|------|
| RPA 服务 | 8090 | FastAPI + Playwright | 社保/公积金网站自动化 |
| OCR 服务 | 8091 | FastAPI + PaddleOCR | 证件识别 |
| 人脸服务 | 8092 | FastAPI + InsightFace 0.3.x | 人脸比对与活体检测 |

### 1.3 前端技术栈

| 用途 | 选型 | 版本 |
|------|------|------|
| Web 前端 | Vue 3.4 + Element Plus 2 | Vue 3.4.x |
| 移动端 | UniApp | 3.0.x |
| 状态管理 | Pinia + Vue Query | Pinia 2.1.x / Vue Query 5.x |
| HTTP 客户端 | Axios | 1.x |
| 路由 | Vue Router | 4.x |
| 构建工具 | Vite | 5.x |
| 国际化 | vue-i18n | 9.x |
| 图表 | ECharts | 5.x |

### 1.4 基础设施

| 组件 | 选型 | 版本 | 部署模式 |
|------|------|------|---------|
| 数据库 | MySQL | 8.0 | 主从复制 (1 主 2 从) |
| 缓存 | Redis | 7.2 | Cluster (3 主 3 从) |
| 消息队列 | Kafka | 3.x | 3 节点集群 |
| 对象存储 | MinIO | RELEASE.2024-07.x | 单节点 |
| 向量数据库 | Milvus | 2.4.x | Docker Compose 单节点 |
| 搜索引擎 | Elasticsearch | 8.12.x | 单节点 |
| 认证中心 | Keycloak | 22.x | 单节点 |
| 流程引擎 | Camunda 8 (Zeebe) | 8.x | Zeebe + Operate + Tasklist |
| 链路追踪 | Jaeger | 1.58.x | All-in-one 单节点 |
| 监控 | Prometheus + Grafana | 2.51.x | 单节点 |
| 网关 | Nginx | 1.25 | 反向代理 |
| 容器 | Docker Compose | 24.x | 开发环境 |

---

## 2. 系统架构

### 2.1 域服务划分

| 域服务 | 端口 | 数据库 Schema | 职责 |
|--------|------|--------------|------|
| user-domain | 8081 | hr_user | 用户管理、认证授权、组织架构、权限管理、员工档案、入职/离职/证明 |
| recruit-domain | 8082 | hr_recruit | 简历筛选、面试管理、培训管理、招聘流程 |
| payroll-domain | 8083 | hr_payroll | 考勤管理、薪资核算、绩效管理、外务管理 |
| auto-domain | 8084 | hr_auto | 报表分析、体系审核、RPA/OCR/人脸调用、流程优化 |

### 2.2 架构拓扑

```
Internet
    │
    ▼
┌─────────────┐
│   Nginx      │  :80 / :443
│  (L7 Gateway)│
└──────┬──────┘
       │
       ├── /          → Frontend (Vue SPA)
       ├── /api/user/  → user-domain   :8081
       ├── /api/recruitment/ → recruit-domain :8082
       ├── /api/payroll/ → payroll-domain :8083
       └── /api/auto/  → auto-domain   :8084
       │
┌──────┴──────┐
│             │
│  user-domain  :8081  →  hr_user     (MySQL)
│  recruit-domain :8082 →  hr_recruit  (MySQL)
│  payroll-domain :8083 →  hr_payroll  (MySQL)
│  auto-domain   :8084 →  hr_auto     (MySQL)
│
│  ─── Kafka 事件总线 (at-least-once) ───
│
│  rpa-service   :8090  (Python/Playwright)
│  ocr-service   :8091  (Python/PaddleOCR)
│  face-service  :8092  (Python/InsightFace)
│
│  ─── 共享基础设施 ───
│
│  MySQL 8.0    :3306  (4 schemas)
│  Redis 7.2    :6379
│  Kafka 1-3    :9092-9094
│  MinIO        :9000
│  Milvus       :19530
│  ES           :9200
│  Keycloak     :8080
│  Zeebe        :26500
│  Operate      :8085
│  Tasklist     :8086
│  Prometheus   :9090
│  Grafana      :3000
│  Jaeger       :16686
└──────────────────┘
```

---

## 3. 项目目录结构

```
gbm-ai-agent-hr/
├── backend/                              # Java 后端 (Maven 多模块)
│   ├── pom.xml                           # 父 POM (Spring Boot 3.2.x)
│   ├── common/                           # 公共模块
│   │   ├── pom.xml
│   │   └── src/                          # 公共工具类、DTO、异常定义
│   ├── user-domain/                      # 用户中心域服务 (:8081)
│   │   ├── pom.xml
│   │   └── src/main/java/com/gbm/hr/user/
│   ├── recruit-domain/                   # 招聘培训域服务 (:8082)
│   │   ├── pom.xml
│   │   └── src/main/java/com/gbm/hr/recruit/
│   ├── payroll-domain/                   # 薪酬考勤域服务 (:8083)
│   │   ├── pom.xml
│   │   └── src/main/java/com/gbm/hr/payroll/
│   ├── auto-domain/                      # 分析自动化域服务 (:8084)
│   │   ├── pom.xml
│   │   └── src/main/java/com/gbm/hr/auto/
│   └── Dockerfile                        # Java 通用 Dockerfile
│
├── python-services/                      # Python 子服务
│   ├── rpa-service/                      # RPA 自动化服务 (:8090)
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── rpa_service/
│   ├── ocr-service/                      # OCR 识别服务 (:8091)
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── ocr_service/
│   └── face-service/                     # 人脸比对服务 (:8092)
│       ├── main.py
│       ├── requirements.txt
│       ├── Dockerfile
│       └── face_service/
│
├── frontend/                             # 前端应用
│   ├── web/                              # Web 端 (Vue 3.4)
│   │   ├── package.json
│   │   ├── vite.config.js
│   │   ├── src/
│   │   └── public/
│   ├── mobile/                           # 移动端 (UniApp 3.0)
│   │   └── ...
│   └── tests/                            # 前端测试
│
├── database/                             # 数据库初始化脚本
│   ├── init/                             # 初始化 SQL (按执行顺序)
│   │   ├── 01_create_schemas.sql         # 创建 4 个 schema
│   │   ├── 02_hr_user.sql               # hr_user 表结构
│   │   ├── 03_hr_recruit.sql            # hr_recruit 表结构
│   │   ├── 04_hr_payroll.sql            # hr_payroll 表结构
│   │   ├── 05_hr_auto.sql               # hr_auto 表结构
│   │   └── 06_init_data.sql             # 初始种子数据
│   ├── migration/                        # Flyway/Liquibase 迁移
│   └── seed/                             # 种子数据
│
├── infra/                                # 基础设施即代码
│   ├── docker/                           # Docker Compose 编排
│   │   ├── mysql/conf.d/                 # MySQL 配置
│   │   ├── nginx/nginx.conf              # Nginx 反向代理
│   │   └── ...
│   └── k8s/                              # Kubernetes 部署配置
│       ├── deployment.yaml
│       └── service.yaml
│
├── monitoring/                           # 监控配置
│   ├── prometheus.yml                    # Prometheus 采集配置
│   └── grafana/                          # Grafana 仪表盘
│
├── .github/workflows/                    # CI/CD 流水线
│   ├── backend-ci.yml                    # 后端 CI (Lint/Test/Build)
│   ├── frontend-ci.yml                   # 前端 CI
│   ├── cd.yml                            # CD 部署流水线
│   ├── security.yml                      # 安全扫描
│   └── docker-build.yml                  # Docker 镜像构建
│
├── docs/                                 # 项目文档
│   ├── gbm-ai-agent-hr_SRS_V15.md
│   ├── gbm-ai-agent-hr_ARCHITECTURE_V24.md
│   ├── gbm-ai-agent-hr_BACKEND_V35.md
│   ├── gbm-ai-agent-hr_DATABASE_V19.md
│   ├── gbm-ai-agent-hr_FRONTEND_V26.md
│   └── gbm-ai-agent-hr_env_V1.md        # 本文档
│
├── scripts/                              # 运维脚本
│   ├── start-dev.sh                      # 启动开发环境
│   └── db-migrate.sh                     # 数据库迁移
│
├── docker-compose.yml                    # 开发环境 Docker Compose
├── docker-compose.dev.yml                # 开发环境覆盖配置
├── .env.example                          # 环境变量模板
├── .env                                  # 本地环境变量 (gitignore)
├── .gitignore                            # Git 忽略规则
├── Makefile                              # 快捷命令
├── .pre-commit-config.yaml               # Pre-commit 钩子
├── ci/pipeline.yml                       # CI 管道定义
└── README.md                             # 项目说明
```

---

## 4. 开发环境要求

### 4.1 硬件要求

| 配置 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 8 核心 | 16 核心 |
| 内存 | 32 GB | 64 GB |
| 存储 | 500 GB SSD | 1 TB SSD |
| GPU | 无 (开发) | NVIDIA GPU 8GB+ (本地 LLM) |

### 4.2 软件要求

| 软件 | 版本 | 用途 |
|------|------|------|
| Java | JDK 17 | 后端编译和运行 |
| Maven | 3.8+ | Java 构建工具 |
| Node.js | 18.x LTS | 前端构建 |
| Python | 3.11+ | Python 子服务 |
| Docker | 24.x | 容器运行 |
| Docker Compose | 2.23+ | 服务编排 |
| Git | 2.30+ | 版本控制 |
| MySQL Client | 8.0+ | 数据库管理 |
| IDE | IntelliJ IDEA / VS Code | 代码编辑 |

### 4.3 系统要求

- **操作系统**：Ubuntu 22.04 LTS / macOS 12+ / WSL2
- **网络**：需要访问外网下载 Docker 镜像和 Maven/Node.js 依赖
- **端口占用**：确保以下端口未被占用 (3306, 6379, 9092-9094, 8080-8092, 9000, 9200, 19530, 26500, 80, 443, 9090, 3000)

---

## 5. 数据库设计

### 5.1 四域 Schema 架构

| Schema | 业务域 | 对应服务 | 端口 | 核心表 |
|--------|--------|---------|------|--------|
| `hr_user` | 用户域 | user-domain | 8081 | sys_user, sys_role, employee_base, employee_job, employee_pay_profile, department, job_position |
| `hr_recruit` | 招聘域 | recruit-domain | 8082 | resume, recruitment_process, exam_paper, exam_question, interview_record, training_record, certificate |
| `hr_payroll` | 薪资域 | payroll-domain | 8083 | payroll, attendance_record, shift_config, salary_rule, social_security_rule, performance_review |
| `hr_auto` | 自动化域 | auto-domain | 8084 | agent_run_log, rpa_task, audit_log, report_template, certificate_type, external_affairs_type |

### 5.2 数据库初始化

```bash
# 方式一: Docker Compose 自动初始化 (推荐)
# docker-compose.yml 已配置 volumes 挂载 database/init/ 到 /docker-entrypoint-initdb.d
# MySQL 启动时自动执行初始化脚本
docker-compose up -d mysql

# 方式二: 手动初始化
mysql -u root -p < database/init/01_create_schemas.sql
mysql -u root -p < database/init/02_hr_user.sql
mysql -u root -p < database/init/03_hr_recruit.sql
mysql -u root -p < database/init/04_hr_payroll.sql
mysql -u root -p < database/init/05_hr_auto.sql
mysql -u root -p < database/init/06_init_data.sql
```

### 5.3 数据库连接信息

| 属性 | 开发环境值 |
|------|----------|
| 主机 | localhost |
| 端口 | 3306 |
| 用户名 | hr_admin |
| 密码 | gbm_hr_admin_2026 |
| 字符集 | utf8mb4 |
| 排序规则 | utf8mb4_unicode_ci |
| 连接数 | 500 |
| InnoDB Buffer Pool | 2GB |

### 5.4 各域服务数据源 URL

| 域服务 | JDBC URL |
|--------|---------|
| user-domain | `jdbc:mysql://mysql:3306/hr_user?useUnicode=true&characterEncoding=utf8mb4&useSSL=false&serverTimezone=Asia/Shanghai` |
| recruit-domain | `jdbc:mysql://mysql:3306/hr_recruit?useUnicode=true&characterEncoding=utf8mb4&useSSL=false&serverTimezone=Asia/Shanghai` |
| payroll-domain | `jdbc:mysql://mysql:3306/hr_payroll?useUnicode=true&characterEncoding=utf8mb4&useSSL=false&serverTimezone=Asia/Shanghai` |
| auto-domain | `jdbc:mysql://mysql:3306/hr_auto?useUnicode=true&characterEncoding=utf8mb4&useSSL=false&serverTimezone=Asia/Shanghai` |

---

## 6. 开发环境启动

### 6.1 一键启动 (Docker Compose)

```bash
cd /home/jim/DevFlow/projects/gbm-ai-agent-hr

# 1. 复制环境变量
cp .env.example .env
# 修改 .env 中的密码为实际值

# 2. 启动基础设施 (MySQL, Redis, Kafka, MinIO, ES, Milvus, Keycloak, Camunda)
docker-compose up -d mysql redis zookeeper kafka1 kafka2 kafka3 \
  minio elasticsearch milvus keycloak zeebe operate tasklist \
  prometheus grafana jaeger

# 3. 等待服务就绪
docker-compose ps

# 4. 构建并启动域服务
docker-compose up -d user-domain recruit-domain payroll-domain auto-domain

# 5. 启动 Python 子服务
docker-compose up -d rpa-service ocr-service face-service

# 6. 构建并启动前端
cd frontend/web && npm install && npm run build
cd ../..
docker-compose up -d nginx
```

### 6.2 本地开发 (不通过 Docker)

#### 后端

```bash
# 1. 启动基础设施 (Docker)
docker-compose up -d mysql redis zookeeper kafka1 kafka2 kafka3 \
  minio elasticsearch milvus keycloak zeebe

# 2. 初始化数据库
mysql -u hr_admin -p < database/init/01_create_schemas.sql
mysql -u hr_admin -p < database/init/02_hr_user.sql
# ... 依次执行 03-06

# 3. 编译后端
cd backend
mvn clean install -DskipTests

# 4. 启动各域服务 (独立终端窗口)
# user-domain (:8081)
cd backend/user-domain
mvn spring-boot:run -Dspring-boot.run.profiles=dev

# recruit-domain (:8082)
cd backend/recruit-domain
mvn spring-boot:run -Dspring-boot.run.profiles=dev

# payroll-domain (:8083)
cd backend/payroll-domain
mvn spring-boot:run -Dspring-boot.run.profiles=dev

# auto-domain (:8084)
cd backend/auto-domain
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

#### Python 子服务

```bash
# RPA 服务
cd python-services/rpa-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8090 --reload

# OCR 服务
cd python-services/ocr-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8091 --reload

# 人脸服务
cd python-services/face-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8092 --reload --workers 4
```

#### 前端

```bash
# Web 前端
cd frontend/web
npm install
npm run dev  # 开发服务器 :5173

# 移动端 (UniApp)
cd frontend/mobile
npm install
npx cross-env NODE_ENV=development uni
```

### 6.3 Makefile 快捷命令

```bash
make dev          # 启动完整开发环境
make dev-infra    # 仅启动基础设施
make dev-backend  # 启动后端域服务
make dev-frontend # 启动前端开发服务器
make dev-python   # 启动 Python 子服务
make test         # 运行全量测试
make test-backend # 运行后端测试
make test-frontend# 运行前端测试
make lint         # 代码质量检查
make build        # 构建 Docker 镜像
make db-init      # 初始化数据库
make db-migrate   # 执行数据库迁移
make clean        # 清理构建产物
make down         # 停止所有服务
```

---

## 7. 服务地址与端口

### 7.1 后端服务

| 服务 | 本地地址 | 端口 | 说明 |
|------|---------|------|------|
| user-domain | http://localhost:8081 | 8081 | 用户中心域服务 |
| recruit-domain | http://localhost:8082 | 8082 | 招聘培训域服务 |
| payroll-domain | http://localhost:8083 | 8083 | 薪酬考勤域服务 |
| auto-domain | http://localhost:8084 | 8084 | 分析自动化域服务 |
| 用户域 API 文档 | http://localhost:8081/swagger-ui.html | - | SpringDoc OpenAPI |
| 招聘域 API 文档 | http://localhost:8082/swagger-ui.html | - | SpringDoc OpenAPI |
| 薪资域 API 文档 | http://localhost:8083/swagger-ui.html | - | SpringDoc OpenAPI |
| 自动化域 API 文档 | http://localhost:8084/swagger-ui.html | - | SpringDoc OpenAPI |

### 7.2 Python 子服务

| 服务 | 本地地址 | 端口 | 健康检查 |
|------|---------|------|---------|
| RPA 服务 | http://localhost:8090 | 8090 | GET /health |
| OCR 服务 | http://localhost:8091 | 8091 | GET /health |
| 人脸服务 | http://localhost:8092 | 8092 | GET /health |

### 7.3 基础设施服务

| 服务 | 本地地址 | 端口 | 默认凭据 |
|------|---------|------|---------|
| Nginx 网关 | http://localhost | 80 | - |
| MySQL | localhost:3306 | 3306 | hr_admin / gbm_hr_admin_2026 |
| Redis | localhost:6379 | 6379 | 密码: gbm_redis_2026 |
| Kafka Broker 1 | localhost:9092 | 9092 | - |
| Kafka Broker 2 | localhost:9093 | 9093 | - |
| Kafka Broker 3 | localhost:9094 | 9094 | - |
| Zookeeper | localhost:2181 | 2181 | - |
| MinIO API | http://localhost:9000 | 9000 | minioadmin / minioadmin |
| MinIO Console | http://localhost:9001 | 9001 | minioadmin / minioadmin |
| Elasticsearch | http://localhost:9200 | 9200 | - |
| Milvus | localhost:19530 | 19530 | - |
| Keycloak 控制台 | http://localhost:8080 | 8080 | admin / admin |
| Camunda Zeebe | localhost:26500 | 26500 | - |
| Camunda Operate | http://localhost:8085 | 8085 | demo / demo |
| Camunda Tasklist | http://localhost:8086 | 8086 | demo / demo |

### 7.4 监控与观测

| 服务 | 本地地址 | 端口 | 默认凭据 |
|------|---------|------|---------|
| Prometheus | http://localhost:9090 | 9090 | - |
| Grafana | http://localhost:3000 | 3000 | admin / admin |
| Jaeger UI | http://localhost:16686 | 16686 | - |

### 7.5 前端

| 服务 | 本地地址 | 端口 | 说明 |
|------|---------|------|------|
| Web 开发服务器 | http://localhost:5173 | 5173 | Vite 开发服务器 |
| 生产前端 (Nginx) | http://localhost:80 | 80 | Nginx 托管静态文件 |

---

## 8. CI/CD 流水线

### 8.1 流水线架构

```
代码提交 → CI 检查 → 构建 → 测试 → 镜像构建 → 安全扫描 → 部署
           │          │       │        │           │          │
        Lint/Format  Compile  Unit    Docker    Trivy    K8s/Compose
        Type Check   Package  Integ   Image     Scan     Rollout
        Security               Test  Multi-arch           Health
```

### 8.2 GitHub Actions 流水线

#### 后端 CI (.github/workflows/backend-ci.yml)

| 阶段 | 工具 | 说明 |
|------|------|------|
| 代码检查 | Checkstyle + SpotBugs | Maven 插件，代码规范和安全缺陷检查 |
| 单元测试 | JUnit 5 + Mockito | 各域服务独立测试，覆盖率要求 ≥ 80% |
| 集成测试 | Testcontainers | 使用 Docker 容器运行集成测试 |
| 构建 | Maven | 编译打包，跳过测试 |
| 镜像构建 | Docker Buildx | 多平台镜像构建 |

触发条件：
- push 到 main/develop 分支
- pull request 到 main 分支
- backend/ 目录文件变更

#### 前端 CI (.github/workflows/frontend-ci.yml)

| 阶段 | 工具 | 说明 |
|------|------|------|
| 代码检查 | ESLint + Prettier | 代码风格和语法检查 |
| 类型检查 | TypeScript | tsconfig 严格模式 |
| 单元测试 | Vitest + Testing Library | 组件和逻辑测试 |
| 构建 | Vite | 生产环境构建 |

触发条件：
- push 到 main/develop 分支
- frontend/ 目录文件变更

#### CD 流水线 (.github/workflows/cd.yml)

| 阶段 | 工具 | 说明 |
|------|------|------|
| 镜像构建 | Docker Buildx | 多平台镜像，推送至 GHCR |
| 安全扫描 | Trivy | CRITICAL/HIGH 漏洞阻断 |
| 部署 | kubectl | K8s 滚动更新，健康检查 |
| 回滚 | kubectl | 自动回滚策略 |

触发条件：
- push 到 main 分支

### 8.3 代码质量门禁

#### 后端 (Java/Maven)

```bash
# 代码风格检查
mvn checkstyle:check

# 静态代码分析
mvn spotbugs:check

# 单元测试 + 覆盖率
mvn test jacoco:report

# 集成测试
mvn verify -Pintegration-test

# 全量构建 (含所有检查)
mvn clean verify
```

#### 前端 (Node.js)

```bash
# 代码风格
npm run lint

# 类型检查
npm run type-check

# 单元测试
npm run test

# 构建
npm run build
```

### 8.4 分支策略

| 分支 | 说明 | 保护规则 |
|------|------|---------|
| main | 生产代码 | 受保护，仅允许 Merge Request |
| develop | 开发集成分支 | 受保护，CI 通过后方可合并 |
| feature/* | 功能开发 | 从 develop 分支创建 |
| bugfix/* | 缺陷修复 | 从 develop 分支创建 |
| hotfix/* | 紧急修复 | 从 main 分支创建 |

### 8.5 提交规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型：`feat` `fix` `docs` `style` `refactor` `test` `chore` `perf` `ci`

示例：
```
feat(user-domain): 新增员工入职 OCR 证件识别接口

实现 OCR Agent 调用接口，支持身份证、学历证书识别
支持批量识别和异步回调机制

Closes #123
```

---

## 9. 环境变量配置

### 9.1 环境变量文件

| 文件 | 说明 | Git 跟踪 |
|------|------|---------|
| .env.example | 环境变量模板 | ✓ 跟踪 |
| .env | 本地环境变量 | ✗ 已 .gitignore |

```bash
# 初始化
cp .env.example .env
# 修改 .env 中的占位符为实际值
```

### 9.2 必填变量

```bash
# 数据库
MYSQL_ROOT_PASSWORD=ChangeMe...
# Redis
REDIS_PASSWORD=ChangeMe...
# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=ChangeMe...
# Keycloak
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=ChangeMe...
# JWT
JWT_SECRET=ChangeMe...
# Elasticsearch
ELASTICSEARCH_PASSWORD=ChangeMe...
# 邮件
SMTP_PASSWORD=ChangeMe...
```

### 9.3 可选变量

```bash
# 监控
GRAFANA_PASSWORD=gbm_grafana_2026
# AI 模型服务 (本地部署)
LLM_ENDPOINT=http://vllm:8000
EMBEDDING_ENDPOINT=http://embedding:8001

# OpenAI API (可选，用于外部 LLM)
OPENAI_API_KEY=xxx

# 短信
SMS_API_KEY=xxx
```

---

## 10. Kafka Topic 配置

### 10.1 业务 Topic

| Topic | 发布者 | 订阅者 | 用途 | 可靠性 |
|-------|--------|--------|------|--------|
| rpa.result | RPA 子服务 | auto-domain | RPA 长任务完成通知 | at-least-once |
| ocr.result | OCR 子服务 | auto-domain | OCR 批量处理结果回传 | at-least-once |
| face.result | 人脸子服务 | auto-domain | 人脸批量比对结果通知 | at-least-once |
| notification.email | auto-domain | 邮件服务 | 邮件通知 | at-least-once |
| notification.sms | auto-domain | 短信服务 | 短信通知 | at-least-once |
| notification.push | auto-domain | 推送服务 | APP 推送 | best-effort |
| agent.event | 各域服务 | 前端 Dashboard | Agent 状态更新 | best-effort |
| agent.error | 各域服务 | 告警服务 | Agent 错误告警 | at-least-once |

### 10.2 开发环境 Topic 初始化

Kafka 启动后，Topic 由 Spring Kafka 的 `auto-create-topics=true` 配置自动创建。

如需手动创建：
```bash
docker exec gbm-hr-kafka1 kafka-topics.sh \
  --create --topic rpa.result \
  --bootstrap-server kafka1:9092 \
  --partitions 3 --replication-factor 1
```

---

## 11. 安全要求

### 11.1 数据加密

- 敏感字段 (身份证号、人脸特征、薪资数据) 使用 **AES-256-GCM** 加密存储
- 加密密钥通过 `.env` 配置，生产环境使用 K8s Secret
- 传输层强制 **TLS 1.2+**
- 数据库加密字段：`employee_base.id_number_encrypted`、`employee_bank.bank_account_encrypted`、`resume.id_number_encrypted`

### 11.2 认证与授权

- 所有 API 端点强制身份认证 (Keycloak SSO)
- OAuth 2.0 + JWT 令牌认证
- RBAC 基于角色的访问控制
- 行级数据隔离 (部门主管只能查看本部门数据)
- 高风险操作强制 MFA：管理员首次登录、访问薪资数据、公积金/社保操作、大批量导出、密码重置

### 11.3 审计日志

- 审计日志保留期 **≥ 10 年**
- 不可篡改、不可删除
- 包含字段：操作时间、操作人、IP、操作类型、模块、对象、变更前后快照、结果、耗时

### 11.4 Agent 安全护栏

| 护栏类型 | 说明 |
|---------|------|
| 金额操作护栏 | Agent 不得在未获人事专员审核批准的情况下修改任何金额的变动记录 |
| 对外通讯护栏 | Agent 发送邮件给外部联系人前需预审确认 |
| 数据删除护栏 | Agent 不得无条件删除已归档数据；删除动作需二次审批 |
| 模型推理护栏 | Agent 输出结果需经过合理性阈值检查 |
| Prompt 注入防护 | 对用户输入和 Agent 内部 Prompt 统一注入安全过滤 |

---

## 12. 备份与灾备

### 12.1 备份策略

| 类型 | 频率 | 保留期 | 执行方式 |
|------|------|--------|---------|
| 全量备份 | 每周一次 | ≥ 15 年 | 系统自动调度 |
| 增量备份 | 每天一次 | ≥ 15 年 | 系统自动调度 |
| 恢复演练 | 每季度一次 | - | 系统管理员手动执行 |

### 12.2 灾备指标

| 指标 | 目标 | 说明 |
|------|------|------|
| RTO (恢复时间) | ≤ 4 小时 | 数据中心级灾难恢复 |
| RPO (数据丢失上限) | ≤ 1 小时 | 基于 binlog 增量恢复 |

### 12.3 数据归档策略

| 数据类型 | 在线保留 | 离线归档 | 法律依据 |
|---------|---------|---------|---------|
| 薪资数据 | ≥ 15 年 | ≥ 15 年 | 工资支付暂行规定 |
| 工伤档案 | 永久 | ≥ 15 年 | 工伤保险条例 |
| 审计日志 | ≥ 10 年 | ≥ 10 年 | 个人信息保护法 |
| 简历数据 | 3 年 | ≥ 2 年 | 招聘惯例 |
| 考勤数据 | 2 年 | ≥ 2 年 | 劳动争议诉讼时效 |

---

## 13. Git 工作流

### 13.1 Pre-commit 钩子

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files

  # Java 代码检查
  - repo: https://github.com/macisamuele/language-formatters-pre-commit-hooks
    rev: v2.11.0
    hooks:
      - id: pretty-format-java
        args: ['--autofix']

  # Python 代码检查 (子服务)
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        files: python-services/

  # 前端代码检查
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
        files: frontend/
```

### 13.2 .gitignore 关键条目

```gitignore
# 敏感文件
.env
*.pem
*.key
*.keystore

# Java
backend/*/target/
*.class
*.jar

# Node.js
node_modules/
frontend/*/dist/

# Python
__pycache__/
*.py[cod]
venv/

# IDE
.idea/
.vscode/

# 本地数据
data/
uploads/
logs/
reports/

# Docker Compose 覆盖
docker-compose.override.yml
```

---

## 14. 监控告警

### 14.1 监控指标

| 监控项 | 告警阈值 | 采集方式 |
|--------|---------|---------|
| CPU 利用率 | 持续 5min > 85% | Prometheus JMX Exporter |
| 内存利用率 | 持续 5min > 90% | Prometheus JMX Exporter |
| 磁盘空间 | > 80% | Prometheus Node Exporter |
| DB 连接池 | > 80% | Micrometer |
| API P95 延迟 | > 5s | Micrometer |
| Agent 操作成功率 | < 95% | 自定义指标 |
| 简历筛选积压量 | > 500 份 | 自定义指标 |
| 薪资核算任务 | 超时或失败 | Camunda Operate |
| Kafka 积压 | > 10 万条 | Prometheus Kafka Exporter |

### 14.2 告警等级

| 等级 | 响应时间 | 通知方式 | 升级策略 |
|------|---------|---------|---------|
| 紧急 | 5 分钟 | 电话/SMS | 15 分钟无人确认自动升级 |
| 重要 | 30 分钟 | 邮件/SMS | - |
| 一般 | 下一工作日 | 邮件 | - |

---

## 15. 常见问题排查

### 15.1 Docker Compose 启动失败

```bash
# 检查端口冲突
sudo lsof -i :3306  # MySQL
sudo lsof -i :6379  # Redis
sudo lsof -i :9092  # Kafka

# 检查 Docker 资源
docker system df
docker stats

# 清理并重新启动
docker-compose down -v
docker-compose up -d
```

### 15.2 Kafka 连接失败

```bash
# 检查 Kafka 集群状态
docker exec gbm-hr-kafka1 kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# 检查 Topic 列表
docker exec gbm-hr-kafka1 kafka-topics.sh --list --bootstrap-server localhost:9092

# 检查消费者组
docker exec gbm-hr-kafka1 kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list
```

### 15.3 域服务启动失败

```bash
# 查看日志
docker logs gbm-hr-user-domain --tail 100

# 检查数据库连接
docker exec -it gbm-hr-mysql mysql -u hr_admin -p -e "SHOW DATABASES;"

# 检查健康检查
curl http://localhost:8081/actuator/health
curl http://localhost:8082/actuator/health
curl http://localhost:8083/actuator/health
curl http://localhost:8084/actuator/health
```

### 15.4 Python 子服务启动失败

```bash
# RPA 服务 (需要浏览器依赖)
docker exec gbm-hr-rpa-service python -m playwright install --with-deps chromium

# OCR 服务 (模型加载需要时间)
# 启动后等待 90 秒再检查健康状态
curl http://localhost:8091/health

# 人脸服务 (需要下载 ONNX 模型)
docker logs gbm-hr-face-service --tail 50
```

---

## 16. 参考文档

| 文档 | 版本 | 路径 |
|------|------|------|
| 需求规格说明书 | SRS V15 | `docs/gbm-ai-agent-hr_SRS_V15.md` |
| 架构设计文档 | V24 | `docs/gbm-ai-agent-hr_ARCHITECTURE_V24.md` |
| 后端设计文档 | V35 | `docs/gbm-ai-agent-hr_BACKEND_V35.md` |
| 数据库设计脚本 | V19 | `docs/gbm-ai-agent-hr_DATABASE_V19.md` |
| 前端设计文档 | V26 | `docs/gbm-ai-agent-hr_FRONTEND_V26.md` |
| 环境配置文档 | V1 | `docs/gbm-ai-agent-hr_env_V1.md` (本文档) |

---

*文档结束*
