# GBM AI Agent HR 智能人力管理系统 — 后端设计文档 (V19)

## 版本信息

| 字段 | 值 |
|------|-----|
| 文档名称 | GBM AI Agent HR 后端设计文档 |
| 版本号 | V19.0 |
| 基于 SRS | V15.0 |
| 日期 | 2026-06-12 |
| 修订日期 | 2026-06-12 |
| 作者 | 后旺 (HouWang) |
| 角色 | 后端架构师 |

**修订说明**
V9.0→V19.0：根据后荣检验意见修正以下问题：
1. 【致命】确认文档完整性，V19 保持完整 10 章节内容，无截断风险
2. 【严重】修复 Nacos 技术栈矛盾：明确仅使用配置热更能力，舍弃服务发现功能
3. 【中等】补充 Python 子服务（RPA/OCR）部署方案：Docker 容器化部署、健康检查、故障恢复、通信契约
4. 【中等】Face++ 选型收敛：明确选用 Face++ SDK（云端 API），放弃自研方案
5. 【轻微】补充模块化单体跨模块数据访问机制：共享实体 + 内部 API 接口

---

## 目录

1. 后端技术栈
2. 项目结构
3. API 接口设计
4. 数据流设计
5. 中间件设计
6. 安全策略
7. Agent 运行时设计
8. RPA 引擎设计
9. 错误处理与异常管理
10. 性能优化策略

---

## 1. 后端技术栈

### 1.1 核心技术

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| 语言 | Java | 17 LTS | 企业级稳定性 |
| 框架 | Spring Boot | 3.2.x | 微服务基础框架 |
| Spring Cloud | - | 已移除（模块化单体不需要服务治理） |
| ORM | MyBatis-Plus | 3.5.x | 灵活 SQL 控制 |
| API 文档 | SpringDoc OpenAPI | 2.x | 自动生成 API 文档 |
| 认证 | Spring Security | 6.x | 安全框架 |
| JWT | jjwt | 0.12.x | Token 生成与验证 |
| 消息队列 | Spring Event (进程内) + Redis Stream (进程间) | - | 模块化单体内优先使用 Spring Event，跨进程可靠事件传递使用 Redis Stream（at-least-once 投递） |
| 流程引擎 | Flowable | 6.8.x | BPMN 2.0 流程编排（对 MySQL 兼容性优于 Camunda） |
| 缓存 | Redis | 7.x | Redisson 客户端 |
| 配置中心 | Nacos | 2.x | **仅使用配置热更能力，不使用服务发现功能**（模块化单体无服务发现需求） |
| 链路追踪 | OpenTelemetry | 1.x | 分布式追踪 |
| 日志 | SLF4J + Logback | - | 结构化日志 |
| 对象存储 | MinIO SDK | 8.x | 文件上传/下载 |
| RPA | Playwright Python (通过 HTTP API 调用) | - | 浏览器自动化（Python 生态更成熟） |
| OCR | PaddleOCR Python (通过 HTTP API 调用) | - | 证件识别（Python 生态更成熟） |
| 人脸 | Face++ SDK (云端 API) | - | 人脸比对（详见 1.3 选型说明） |
| 定时任务 | XXL-JOB | 2.x | 分布式任务调度 |
| WebSocket | Spring WebSocket + STOMP | - | 实时推送（Dashboard 待办提醒、Agent 状态更新） |
| 测试 | JUnit 5 + Mockito | - | 单元测试 |
| 测试容器 | Testcontainers | - | 集成测试 |
| 密钥管理 | HashiCorp Vault | 1.x | 加密密钥、API 凭证安全管理 |
| 监控 | Prometheus + Grafana | - | 指标采集与可视化 |
| 弹性容错 | Resilience4j | 2.x | 熔断器、限流、超时控制（替代 Hystrix，与 Spring Boot 3.x 兼容） |

### 1.2 架构模式

采用**模块化单体 (Modular Monolith)** 架构，各模块通过包边界隔离，后期可按需拆分为微服务。

**模块划分依据**：
- 业务域独立性
- 数据隔离性
- 部署独立性（未来）
- 团队职责划分

### 1.3 Nacos 配置中心使用说明

> **修正说明**：V9 版本标注 Nacos 为"配置热更 + 服务发现"，与"已移除 Spring Cloud"声明矛盾。V19 明确修正如下：

**仅使用 Nacos 的配置管理功能**：
- 应用启动时从 Nacos 拉取配置（YAML 格式）
- 支持配置热更新（`@NacosValue` + `@RefreshScope`）
- 支持多环境配置隔离（dev/test/prod）
- 配置变更历史保留，支持回滚

**明确不使用 Nacos 的服务发现功能**：
- 模块化单体架构下不存在多个服务实例，服务发现无意义
- RPA/OCR Python 子服务通过固定 URL 调用，不走服务发现注册
- Nacos 客户端仅启用配置模块（`nacos-config`），不引入服务发现依赖（`nacos-discovery`）

**简化方案对比**：
- 若配置变更频率极低（如仅环境差异），可退化为 `application.yml` + Spring Profile 方案
- 当前保留 Nacos 配置热更能力，理由：薪资规则、Agent 参数等需运行时动态调整，无需重启应用

### 1.4 Face++ 人脸比对选型说明

> **修正说明**：V9 版本标注为"Face++ SDK / 自研"，选型未收敛。V19 明确最终选型如下：

**最终选型：Face++ SDK（云端 API）**

| 评估维度 | Face++ SDK | 自研方案 | 结论 |
|---------|-----------|---------|------|
| 开发周期 | 接入 1-2 周 | 3-6 个月（含训练数据收集、模型训练、调优） | Face++ 胜出 |
| 准确率 | 行业领先（>99% 活体检测） | 依赖数据量和训练水平，初期准确率难以保证 | Face++ 胜出 |
| 维护成本 | 按调用量付费，无需维护模型 | 需要持续训练、GPU 资源投入 | Face++ 胜出 |
| 合规性 | Face++ 具备人脸识别相关资质 | 需自行申请等保和人脸识别许可 | Face++ 胜出 |
| 数据隐私 | 照片上传至 Face++ 云端 | 数据完全本地化 | 自研胜出 |
| 成本控制 | 初期成本低，大规模调用时费用增长 | 初期投入高，长期边际成本低 | 项目初期 Face++ 更优 |

**选型理由**：
1. 人脸比对本系统仅用于入职时"采集照片与身份证照片比对"，调用量有限（每人 1 次），Face++ 按量付费成本可控
2. 项目首期目标为"零操作性"，自研方案开发周期过长，严重影响交付进度
3. Face++ 提供的活体检测能力（眨眼、摇头等动作验证）可有效防止照片冒用，自研方案实现难度大
4. 身份证照片比对场景对数据隐私敏感，Face++ 支持"比对后不存储"模式，原始照片在比对完成后立即删除

**隐私保护措施**：
- 调用 Face++ API 时启用 `return_image=false`，不返回原始图像数据
- 人脸特征向量（features）使用 AES-256-GCM 加密后存储于本地数据库
- 日志中不记录人脸相关原始数据

**Python 子服务部署方案**（详见 1.5 节）：
> RPA（Playwright）和 OCR（PaddleOCR）均为独立的 Python 子服务，通过 HTTP API 与 Java 主服务通信。V19 补充完整的部署方案如下。

### 1.5 Python 子服务部署方案

> **新增内容**：V9 版本缺失 RPA/OCR Python 子服务的部署细节。V19 补充如下。

#### 1.5.1 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Compose 集群                   │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │  Java 主服务  │   │  RPA 子服务  │   │  OCR 子服务  │    │
│  │  (Spring Boot)│   │ (Playwright) │   │(PaddleOCR)   │    │
│  │  :8080       │   │  :8090       │   │  :8091       │    │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘    │
│         │                  │                  │             │
│         │ HTTP API         │                  │             │
│         │                  │ HTTP API         │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                │
│  ┌──────────────┐   ┌─────┴──────────┐                      │
│  │    MySQL     │   │    Redis       │                      │
│  │    :3306     │   │    :6379       │                      │
│  └──────────────┘   └────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

#### 1.5.2 RPA 子服务（Playwright）

**技术栈**：Python 3.11 + FastAPI + Playwright + Uvicorn

**Docker 镜像构建**：
```dockerfile
# Dockerfile.rpa
FROM python:3.11-slim

# 安装系统依赖（Playwright 浏览器需要）
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libatspi2.0-0 \
    libx11-6 libxcomposite1 libxdamage1 \
    libxext6 libxfixes3 libxi6 libxrandr2 \
    libxrender1 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-rpa.txt .
RUN pip install --no-cache-dir -r requirements-rpa.txt

RUN python -m playwright install chromium

COPY rpa_service/ ./rpa_service/
COPY main.py .

EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8090/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]
```

**健康检查**：
- 端点：`GET /health`，返回 `{"status": "healthy", "browser": "ready"}`
- Java 主服务每 30 秒调用健康检查端点
- 连续 3 次健康检查失败 → 触发告警，暂停 RPA 任务分发
- Docker Compose 内置 `HEALTHCHECK`，容器管理器可自动重启不健康容器

**故障恢复策略**：
- 容器崩溃：Docker `restart: on-failure` 策略，最多重启 5 次
- 浏览器进程异常：Playwright 支持浏览器崩溃后自动重启，单次 RPA 任务自动重试 2 次
- 子服务不可用：Java 端 Resilience4j 熔断器触发降级（返回"RPA 服务不可用，请人工处理"）

#### 1.5.3 OCR 子服务（PaddleOCR）

**技术栈**：Python 3.11 + FastAPI + PaddlePaddle + PaddleOCR + Uvicorn

**Docker 镜像构建**：
```dockerfile
# Dockerfile.ocr
FROM python:3.11-slim

WORKDIR /app
COPY requirements-ocr.txt .
RUN pip install --no-cache-dir -r requirements-ocr.txt

# 预下载 OCR 模型（约 200MB）
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='ch')"

COPY ocr_service/ ./ocr_service/
COPY main.py .

EXPOSE 8091
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8091/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8091"]
```

**健康检查**：
- 端点：`GET /health`，返回 `{"status": "healthy", "model_loaded": true}`
- Java 主服务每 30 秒调用健康检查端点
- 连续 3 次健康检查失败 → 触发告警，暂停 OCR 任务分发
- PaddleOCR 模型加载耗时较长（约 60 秒），`start-period` 设置为 90 秒

**故障恢复策略**：
- 容器崩溃：Docker `restart: on-failure` 策略，最多重启 5 次
- OCR 识别失败：返回部分识别结果 + 置信度标记，Java 端可根据置信度决定是否重试或转人工
- 子服务不可用：Java 端 Resilience4j 熔断器触发降级

#### 1.5.4 Docker Compose 编排

```yaml
# docker-compose.yml
version: '3.8'

services:
  hr-backend:
    build:
      context: .
      dockerfile: Dockerfile.java
    ports:
      - "8080:8080"
    environment:
      - RPA_SERVICE_URL=http://rpa-service:8090
      - OCR_SERVICE_URL=http://ocr-service:8091
      - FACE_PLUS_API_KEY=${FACE_PLUS_API_KEY}
      - FACE_PLUS_API_SECRET=${FACE_PLUS_API_SECRET}
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: on-failure

  rpa-service:
    build:
      context: .
      dockerfile: Dockerfile.rpa
    ports:
      - "8090:8090"
    environment:
      - MAX_CONCURRENT_BROWSERS=3
    deploy:
      resources:
        limits:
          memory: 2G
    restart: on-failure

  ocr-service:
    build:
      context: .
      dockerfile: Dockerfile.ocr
    ports:
      - "8091:8091"
    environment:
      - MAX_WORKERS=4
    deploy:
      resources:
        limits:
          memory: 4G
    restart: on-failure

  mysql:
    image: mysql:8.0
    ports:
      - "3306:3306"
    environment:
      - MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=gbm_hr
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: on-failure

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --requirepass ${REDIS_PASSWORD}
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: on-failure

volumes:
  mysql_data:
  redis_data:
```

#### 1.5.5 Java 与 Python 子服务通信契约

**RPA 子服务 HTTP API**：
```
# 提交 RPA 任务
POST http://rpa-service:8090/api/v1/rpa/execute
Content-Type: application/json

Request:
{
    "task_id": "uuid-v4",
    "target_system": "social_security",
    "target_url": "https://xxx.gov.cn/portal",
    "credentials": {"username": "...", "password": "..."},
    "actions": [
        {"type": "CLICK", "selector": "#login-btn"},
        {"type": "TYPE", "selector": "#username", "value": "..."},
        {"type": "TYPE", "selector": "#password", "value": "..."},
        {"type": "CLICK", "selector": "#submit"},
        {"type": "WAIT", "timeout": 30},
        {"type": "CLICK", "selector": "#declare-btn"},
        {"type": "UPLOAD", "selector": "#file-input", "file": "s3://bucket/path"},
        {"type": "CLICK", "selector": "#confirm"},
        {"type": "SCROLLSHOT", "save_as": "receipt"}
    ],
    "timeout_seconds": 300
}

Response (202 - 异步任务已接受):
{
    "task_id": "uuid-v4",
    "status": "ACCEPTED",
    "estimated_time_seconds": 120
}

# 查询 RPA 任务状态
GET http://rpa-service:8090/api/v1/rpa/status/{task_id}

Response (200):
{
    "task_id": "uuid-v4",
    "status": "RUNNING|COMPLETED|FAILED",
    "progress": 0.75,
    "current_step": 5,
    "total_steps": 8,
    "result": null,
    "error": null
}

Response (COMPLETED):
{
    "task_id": "uuid-v4",
    "status": "COMPLETED",
    "progress": 1.0,
    "result": {
        "receipt_url": "s3://bucket/receipt.png",
        "declare_id": "SS20260612001"
    },
    "screenshots": ["s3://bucket/step1.png", "s3://bucket/step2.png"]
}

Response (FAILED):
{
    "task_id": "uuid-v4",
    "status": "FAILED",
    "error": {
        "code": "SELECTION_FAILED",
        "message": "未找到元素 #declare-btn",
        "step": 5,
        "screenshot": "s3://bucket/error_step5.png"
    }
}

# 健康检查
GET http://rpa-service:8090/health

Response:
{
    "status": "healthy",
    "browser": "ready",
    "active_tasks": 2,
    "max_concurrent": 3
}
```

**OCR 子服务 HTTP API**：
```
# OCR 识别
POST http://ocr-service:8091/api/v1/ocr/recognize
Content-Type: multipart/form-data

File: image (jpg/png, max 10MB)
Form: type=id_card|diploma|passport|medical_report

Response (200):
{
    "task_id": "uuid-v4",
    "status": "SUCCESS",
    "type": "id_card",
    "result": {
        "name": "张三",
        "id_number": "110101199001011234",
        "gender": "男",
        "birth_date": "1990-01-01",
        "address": "北京市朝阳区xxx路xxx号"
    },
    "confidence": {
        "name": 0.99,
        "id_number": 0.98,
        "gender": 0.99,
        "birth_date": 0.97,
        "address": 0.85
    },
    "raw_text": "..."
}

Response (低置信度):
{
    "task_id": "uuid-v4",
    "status": "LOW_CONFIDENCE",
    "type": "id_card",
    "result": { ... },
    "confidence": {
        "name": 0.95,
        "id_number": 0.60    <-- 低于阈值 0.8
    },
    "message": "身份证号识别置信度低，建议人工复核"
}

# 健康检查
GET http://ocr-service:8091/health

Response:
{
    "status": "healthy",
    "model_loaded": true,
    "pending_tasks": 0
}
```

**通信契约约定**：
| 维度 | 约定 |
|------|------|
| 传输协议 | HTTP/1.1，非加密内网通信（Docker 内部网络） |
| 数据格式 | JSON（文本）+ multipart/form-data（文件） |
| 超时设置 | RPA: 300s（浏览器操作耗时），OCR: 30s |
| 重试策略 | Java 端指数退避重试（1s, 2s, 4s），最多 3 次 |
| 熔断策略 | Resilience4j，失败率 >50% 熔断 30s |
| 文件大小 | OCR 图片最大 10MB，RPA 上传文件最大 50MB |
| 认证方式 | 内网通信不启用 mTLS，生产环境建议启用 |

---

## 2. 项目结构

```
gbm-ai-agent-hr-backend/
├── gbm-hr-core/                     # 核心公共模块
│   ├── src/main/java/com/gbm/hr/core/
│   │   ├── config/                  # 全局配置
│   │   │   ├── SwaggerConfig.java
│   │   │   ├── RedisConfig.java
│   │   │   ├── SpringEventConfig.java
│   │   │   ├── RedisPubSubConfig.java
│   │   │   ├── MyBatisConfig.java
│   │   │   ├── WebMvcConfig.java
│   │   │   ├── SecurityConfig.java
│   │   │   └── NacosConfig.java     # Nacos 配置中心（仅配置管理）
│   │   ├── constant/                # 常量定义
│   │   │   ├── ErrorCode.java
│   │   │   ├── CacheKey.java
│   │   │   └── EventType.java
│   │   ├── dto/                     # 通用 DTO
│   │   │   ├── Result.java          # 统一响应
│   │   │   ├── PageRequest.java
│   │   │   ├── PageResult.java
│   │   │   └── BaseEntity.java
│   │   ├── exception/               # 异常定义
│   │   │   ├── BusinessException.java
│   │   │   ├── GlobalExceptionHandler.java
│   │   │   └── ValidationException.java
│   │   ├── util/                    # 工具类
│   │   │   ├── EncryptUtil.java
│   │   │   ├── DateUtil.java
│   │   │   ├── IdGenerator.java
│   │   │   ├── FileUtil.java
│   │   │   └── ExcelUtil.java
│   │   ├── client/                  # 外部子服务客户端
│   │   │   ├── RPAService.java      # RPA 子服务 HTTP 客户端
│   │   │   ├── OCRService.java      # OCR 子服务 HTTP 客户端
│   │   │   └── FacePlusService.java # Face++ 云端 API 客户端
│   │   └── validator/               # 校验器
│   │       ├── IdCardValidator.java
│   │       ├── PhoneValidator.java
│   │       └── AmountValidator.java
│   └── build.gradle
│
├── gbm-hr-auth/                     # 认证授权模块
│   ├── src/main/java/com/gbm/hr/auth/
│   │   ├── controller/
│   │   │   ├── AuthController.java
│   │   │   ├── MFAController.java
│   │   │   └── PermissionController.java
│   │   ├── service/
│   │   │   ├── AuthService.java
│   │   │   ├── MFAService.java
│   │   │   ├── TokenService.java
│   │   │   └── PermissionService.java
│   │   ├── entity/
│   │   │   ├── User.java
│   │   │   ├── Role.java
│   │   │   └── UserRole.java
│   │   ├── mapper/
│   │   │   ├── UserMapper.java
│   │   │   └── RoleMapper.java
│   │   └── filter/
│   │       ├── JwtAuthenticationFilter.java
│   │       └── MFAFilter.java
│   └── build.gradle
│
├── gbm-hr-recruitment/              # 招聘管理模块
│   ├── src/main/java/com/gbm/hr/recruitment/
│   │   ├── controller/
│   │   │   ├── JobPostController.java
│   │   │   ├── ResumeController.java
│   │   │   ├── ExamController.java
│   │   │   ├── QuestionBankController.java
│   │   │   └── TalentPoolController.java
│   │   ├── service/
│   │   │   ├── JobPostService.java
│   │   │   ├── ResumeService.java
│   │   │   ├── ResumeMatchingService.java
│   │   │   ├── ExamService.java
│   │   │   ├── GradingService.java
│   │   │   └── TalentPoolService.java
│   │   ├── agent/
│   │   │   ├── RecruitmentChannelAgent.java
│   │   │   ├── ResumeMatchingAgent.java
│   │   │   ├── ExamPaperAgent.java
│   │   │   └── GradingAgent.java
│   │   ├── entity/
│   │   │   ├── JobPost.java
│   │   │   ├── Resume.java
│   │   │   ├── ResumeScore.java
│   │   │   ├── ExamPaper.java
│   │   │   └── Question.java
│   │   ├── mapper/
│   │   │   ├── JobPostMapper.java
│   │   │   ├── ResumeMapper.java
│   │   │   └── ExamPaperMapper.java
│   │   └── job/
│   │       ├── ResumeCrawlJob.java     # 定时抓取简历
│   │       └── TalentHealthCheckJob.java
│   └── build.gradle
│
├── gbm-hr-onboarding/               # 入职管理模块
│   ├── src/main/java/com/gbm/hr/onboarding/
│   │   ├── controller/
│   │   │   ├── OnboardingController.java
│   │   │   ├── DocumentController.java
│   │   │   └── FaceController.java
│   │   ├── service/
│   │   │   ├── OnboardingService.java
│   │   │   ├── DocumentRecognitionService.java
│   │   │   └── FaceRecognitionService.java
│   │   ├── agent/
│   │   │   ├── OnboardingGuideAgent.java
│   │   │   ├── OCRAgent.java
│   │   │   └── FaceAgent.java
│   │   ├── entity/
│   │   │   ├── Employee.java
│   │   │   ├── OnboardingRecord.java
│   │   │   └── EmployeeDocument.java
│   │   └── mapper/
│   │       ├── EmployeeMapper.java
│   │       └── OnboardingRecordMapper.java
│   └── build.gradle
│
├── gbm-hr-training/                 # 培训管理模块
│   ├── src/main/java/com/gbm/hr/training/
│   │   ├── controller/
│   │   │   ├── TrainingPlanController.java
│   │   │   ├── TrainingSessionController.java
│   │   │   ├── CheckInController.java
│   │   │   ├── CertificateController.java
│   │   │   └── AuditMaterialsController.java
│   │   ├── service/
│   │   │   ├── TrainingPlanService.java
│   │   │   ├── CheckInService.java
│   │   │   ├── CertificateService.java
│   │   │   └── AuditMaterialsService.java
│   │   ├── agent/
│   │   │   ├── TrainingAgent.java
│   │   │   ├── VideoAgent.java
│   │   │   └── AuditMaterialsAgent.java
│   │   ├── entity/
│   │   │   ├── TrainingPlan.java
│   │   │   ├── TrainingSession.java
│   │   │   ├── CheckInRecord.java
│   │   │   └── Certificate.java
│   │   └── mapper/
│   │       ├── TrainingPlanMapper.java
│   │       └── CheckInRecordMapper.java
│   └── build.gradle
│
├── gbm-hr-attendance/               # 考勤管理模块
│   ├── src/main/java/com/gbm/hr/attendance/
│   │   ├── controller/
│   │   │   ├── AttendanceController.java
│   │   │   ├── LeaveController.java
│   │   │   └── ShiftController.java
│   │   ├── service/
│   │   │   ├── AttendanceService.java
│   │   │   ├── AnomalyDetectionService.java
│   │   │   └── ShiftService.java
│   │   ├── api/                     # 跨模块 API 接口
│   │   │   ├── AttendanceInternalApi.java   # 考勤内部接口
│   │   │   └── LeaveInternalApi.java        # 假期内部接口
│   │   ├── agent/
│   │   │   └── AttendanceAgent.java
│   │   ├── entity/
│   │   │   ├── AttendanceRecord.java
│   │   │   ├── LeaveRecord.java
│   │   │   └── ShiftSchedule.java
│   │   ├── mapper/
│   │   │   ├── AttendanceRecordMapper.java
│   │   │   └── LeaveRecordMapper.java
│   │   └── job/
│   │       └── AttendanceSyncJob.java  # 定时同步打卡数据
│   └── build.gradle
│
├── gbm-hr-payroll/                  # 薪资管理模块
│   ├── src/main/java/com/gbm/hr/payroll/
│   │   ├── controller/
│   │   │   ├── PayrollController.java
│   │   │   ├── PayslipController.java
│   │   │   └── PayrollRuleController.java
│   │   ├── service/
│   │   │   ├── PayrollCalculationService.java
│   │   │   ├── PayslipService.java
│   │   │   ├── TaxCalculationService.java
│   │   │   └── PayrollRuleService.java
│   │   ├── api/                     # 跨模块 API 消费者
│   │   │   └── AttendanceApiClient.java   # 调用考勤内部接口
│   │   ├── agent/
│   │   │   ├── PayrollAgent.java
│   │   │   └── PayslipAgent.java
│   │   ├── entity/
│   │   │   ├── Payroll.java
│   │   │   ├── Payslip.java
│   │   │   └── PayrollRule.java
│   │   ├── mapper/
│   │   │   ├── PayrollMapper.java
│   │   │   └── PayslipMapper.java
│   │   └── job/
│   │       └── MonthlyPayrollJob.java  # 月末薪资核算
│   └── build.gradle
│
├── gbm-hr-performance/              # 绩效管理模块
│   ├── src/main/java/com/gbm/hr/performance/
│   │   ├── controller/
│   │   │   ├── PerformanceController.java
│   │   │   └── ReportController.java
│   │   ├── service/
│   │   │   ├── PerformanceService.java
│   │   │   └── ReportService.java
│   │   ├── agent/
│   │   │   └── PerformanceAgent.java
│   │   ├── entity/
│   │   │   └── PerformanceReview.java
│   │   └── mapper/
│   │       └── PerformanceReviewMapper.java
│   └── build.gradle
│
├── gbm-hr-external/                 # 外务管理模块
│   ├── src/main/java/com/gbm/hr/external/
│   │   ├── controller/
│   │   │   ├── InjuryCaseController.java
│   │   │   └── HousingFundController.java
│   │   ├── service/
│   │   │   ├── InjuryCaseService.java
│   │   │   ├── HousingFundService.java
│   │   │   └── GovernmentDeclarationService.java
│   │   ├── agent/
│   │   │   ├── ExternalAgent.java
│   │   │   └── RPAAgent.java
│   │   ├── entity/
│   │   │   ├── InjuryCase.java
│   │   │   └── HousingFundRecord.java
│   │   ├── mapper/
│   │   │   ├── InjuryCaseMapper.java
│   │   │   └── HousingFundMapper.java
│   │   └── rpa/
│   │       ├── SocialSecurityRPA.java  # 社保系统 RPA
│   │       ├── HousingFundRPA.java     # 公积金系统 RPA
│   │       └── RPAExecutor.java        # RPA 执行器
│   └── build.gradle
│
├── gbm-hr-employee/                 # 员工服务模块
│   ├── src/main/java/com/gbm/hr/employee/
│   │   ├── controller/
│   │   │   ├── EmployeeController.java
│   │   │   ├── ResignationController.java
│   │   │   ├── CertificateController.java
│   │   │   └── ExpenseController.java
│   │   ├── service/
│   │   │   ├── EmployeeService.java
│   │   │   ├── ResignationService.java
│   │   │   ├── CertificateService.java
│   │   │   └── ExpenseService.java
│   │   ├── agent/
│   │   │   ├── ResignationAgent.java
│   │   │   ├── CertificateAgent.java
│   │   │   └── BudgetAgent.java
│   │   ├── entity/
│   │   │   ├── ResignationRecord.java
│   │   │   └── CertificateRequest.java
│   │   └── mapper/
│   │       ├── ResignationMapper.java
│   │       └── CertificateMapper.java
│   └── build.gradle
│
├── gbm-hr-agent/                    # Agent 运行时模块
│   ├── src/main/java/com/gbm/hr/agent/
│   │   ├── runtime/
│   │   │   ├── AgentRuntime.java       # Agent 运行时
│   │   │   ├── AgentContext.java       # Agent 上下文
│   │   │   └── AgentResult.java        # Agent 执行结果
│   │   ├── orchestration/
│   │   │   ├── Orchestrator.java       # 编排器
│   │   │   ├── Pipeline.java           # 流水线编排
│   │   │   ├── FanOutFanIn.java        # 扇出扇入编排
│   │   │   ├── DecisionTree.java       # 决策树编排
│   │   │   └── FeedbackLoop.java       # 反馈环编排
│   │   ├── guardrail/
│   │   │   ├── Guardrail.java          # 护栏接口
│   │   │   ├── AmountGuardrail.java    # 金额护栏
│   │   │   ├── CommunicationGuardrail.java
│   │   │   ├── DataDeleteGuardrail.java
│   │   │   └── ReasoningGuardrail.java
│   │   ├── logging/
│   │   │   ├── AgentLogger.java        # Agent 日志
│   │   │   └── ReasoningTrace.java     # 推理链
│   │   ├── retry/
│   │   │   ├── RetryPolicy.java        # 重试策略
│   │   │   └── ExponentialBackoff.java # 指数退避
│   │   ├── event/
│   │   │   ├── AgentEventPublisher.java  # Spring Event 发布
│   │   │   └── AgentEventListener.java   # Spring Event 监听
│   │   └── redis/
│   │       ├── RedisStreamProducer.java   # Redis Stream 发布
│   │       └── RedisStreamConsumer.java   # Redis Stream 订阅
│   └── build.gradle
│
├── gbm-hr-notification/             # 通知模块
│   ├── src/main/java/com/gbm/hr/notification/
│   │   ├── controller/
│   │   │   └── NotificationController.java
│   │   ├── service/
│   │   │   ├── EmailService.java
│   │   │   ├── SMSService.java
│   │   │   ├── PushNotificationService.java
│   │   │   └── NotificationService.java
│   │   ├── template/
│   │   │   ├── EmailTemplateEngine.java
│   │   │   └── SMSTemplateEngine.java
│   │   └── redis/
│   │       └── NotificationConsumer.java   # Redis Stream 订阅通知
│   └── build.gradle
│
├── gbm-hr-audit/                    # 审计模块
│   ├── src/main/java/com/gbm/hr/audit/
│   │   ├── service/
│   │   │   └── AuditLogService.java
│   │   ├── aspect/
│   │   │   └── AuditLogAspect.java     # AOP 审计切面
│   │   ├── entity/
│   │   │   └── AuditLog.java
│   │   └── mapper/
│   │       └── AuditLogMapper.java
│   └── build.gradle
│
├── gbm-hr-application/              # 启动模块
│   ├── src/main/java/com/gbm/hr/
│   │   └── GbmHrApplication.java     # Spring Boot 启动类
│   ├── src/main/resources/
│   │   ├── application.yml           # 主配置
│   │   ├── application-dev.yml       # 开发环境
│   │   ├── application-test.yml      # 测试环境
│   │   ├── application-prod.yml      # 生产环境
│   │   └── logback-spring.xml        # 日志配置
│   └── build.gradle
│
├── build.gradle                     # 根构建脚本
├── settings.gradle                  # 模块设置
└── gradle/                          # Gradle 包装器
```

### 2.1 跨模块数据访问机制

> **新增内容**：V9 版本未说明模块化单体中模块间数据访问的方式。V19 补充如下。

**核心原则**：模块间**不直接引用彼此的实体类或 Mapper**，而是通过**内部 API 接口**进行数据访问，保持模块边界清晰。

#### 2.1.1 内部 API 接口模式

提供跨模块数据的模块定义 `api/` 包，暴露 `*InternalApi` 接口。消费方通过 Spring 依赖注入调用：

```java
// 考勤模块暴露的内部接口
package com.gbm.hr.attendance.api;

public interface AttendanceInternalApi {
    /**
     * 获取指定员工在指定月份的考勤汇总
     * @param employeeId 员工 ID
     * @param month 月份 (yyyy-MM)
     * @return 考勤汇总 DTO
     */
    AttendanceSummaryDTO getMonthlySummary(Long employeeId, String month);
    
    /**
     * 批量获取员工考勤汇总（薪资核算用）
     */
    List<AttendanceSummaryDTO> getMonthlySummaryBatch(List<Long> employeeIds, String month);
    
    /**
     * 获取员工请假记录
     */
    List<LeaveRecordDTO> getLeaveRecords(Long employeeId, String month);
}

// 考勤模块内部实现
package com.gbm.hr.attendance.api;

@Service
public class AttendanceInternalApiImpl implements AttendanceInternalApi {
    
    @Autowired
    private AttendanceRecordMapper attendanceMapper;
    
    @Autowired
    private LeaveRecordMapper leaveMapper;
    
    @Override
    public AttendanceSummaryDTO getMonthlySummary(Long employeeId, String month) {
        // 查询考勤记录并汇总
        List<AttendanceRecord> records = attendanceMapper.selectByEmployeeAndMonth(
            employeeId, month);
        // 组装 DTO 返回
        return convertToDTO(records);
    }
    
    @Override
    public List<AttendanceSummaryDTO> getMonthlySummaryBatch(
            List<Long> employeeIds, String month) {
        // 批量查询，避免 N+1
        List<AttendanceRecord> records = attendanceMapper.selectByEmployeesAndMonth(
            employeeIds, month);
        return records.stream()
            .collect(Collectors.groupingBy(AttendanceRecord::getEmployeeId))
            .entrySet().stream()
            .map(e -> convertToDTO(e.getValue()))
            .toList();
    }
    
    @Override
    public List<LeaveRecordDTO> getLeaveRecords(Long employeeId, String month) {
        return leaveMapper.selectByEmployeeAndMonth(employeeId, month)
            .stream().map(this::convertToDTO).toList();
    }
}
```

```java
// 薪资模块消费考勤数据
package com.gbm.hr.payroll.api;

@Service
public class AttendanceApiClient {
    
    @Autowired
    private AttendanceInternalApi attendanceInternalApi;
    
    public List<AttendanceSummaryDTO> getAllAttendance(String month) {
        // 获取全员考勤汇总
        List<Long> allEmployeeIds = employeeService.getAllActiveIds();
        return attendanceInternalApi.getMonthlySummaryBatch(allEmployeeIds, month);
    }
}
```

#### 2.1.2 跨模块数据访问规则

| 规则 | 说明 |
|------|------|
| 禁止直接引用 | A 模块的 `build.gradle` 不应依赖 B 模块的完整 JAR，仅依赖 B 模块的 `api` 子模块（或共享接口） |
| DTO 传递 | 跨模块数据以 DTO 形式传递，不使用实体类，避免实体变更影响消费方 |
| 内部接口命名 | 命名规范为 `{模块}InternalApi`，标识为模块间调用接口 |
| 实现隔离 | `*InternalApiImpl` 在提供方模块的 `api/` 包中实现，消费方仅引用接口 |
| 共享基础类 | `gbm-hr-core` 中的基础 DTO（`Result`、`PageResult`、`BaseEntity`）可被所有模块引用 |

#### 2.1.3 Gradle 依赖配置

```groovy
// gbm-hr-payroll/build.gradle
dependencies {
    implementation project(':gbm-hr-core')         // 公共模块
    implementation project(':gbm-hr-attendance:api') // 考勤内部 API（仅提供接口）
    // 不依赖 gbm-hr-attendance 完整模块，避免直接访问其 Mapper/Entity
}
```

```groovy
// gbm-hr-attendance/build.gradle
dependencies {
    implementation project(':gbm-hr-core')
    // 考勤模块自身完整实现，api 子模块由薪资模块引用
}
```

> **模块化单体跨模块访问设计说明**：
> - 通过 `api/` 包暴露内部接口，消费方仅依赖接口定义
> - DTO 替代实体类传递，实现数据结构的版本化和隔离
> - 批量查询接口（如 `getMonthlySummaryBatch`）避免 N+1 查询问题
> - 未来拆分为微服务时，`*InternalApi` 可直接替换为 Feign Client 或 gRPC Stub

---

## 3. API 接口设计

### 3.1 统一响应格式

```java
public class Result<T> {
    private Integer code;       // 状态码: 200 成功, 400 参数错误, 401 未认证, 403 无权限, 500 系统错误
    private String message;     // 消息
    private T data;             // 数据
    private Long timestamp;     // 时间戳
    private String traceId;     // 链路追踪 ID
}
```

### 3.2 认证授权 API

#### 3.2.1 登录

```
POST /api/v1/auth/login
Content-Type: application/json

Request:
{
    "username": "string",       // 账号/邮箱/手机号
    "password": "string"        // 密码 (前端已加密)
}

Response (200):
{
    "code": 200,
    "message": "登录成功",
    "data": {
        "token": "jwt_token_string",
        "refreshToken": "refresh_token_string",
        "expiresIn": 7200,
        "roles": ["HR"],
        "mfaRequired": false
    }
}

Response (200 - MFA needed):
{
    "code": 200,
    "message": "需要二因子验证",
    "data": {
        "mfaRequired": true,
        "mfaMethod": "sms",
        "mfaTarget": "138****8888"
    }
}
```

#### 3.2.2 MFA 验证

```
POST /api/v1/auth/mfa/verify
Content-Type: application/json
Authorization: Bearer ***

Request:
{
    "code": "123456"            // 验证码
}

Response (200):
{
    "code": 200,
    "data": {
        "token": "jwt_token_string",
        "refreshToken": "refresh_token_string",
        "expiresIn": 7200
    }
}
```

#### 3.2.3 Token 刷新

```
POST /api/v1/auth/refresh
Content-Type: application/json

Request:
{
    "accessToken": "expiring_access_token",    // 即将过期的 Access Token
    "refreshToken": "refresh_token_string"      // Refresh Token
}

Response (200):
{
    "code": 200,
    "data": {
        "token": "new_jwt_token",               // 新 Access Token
        "refreshToken": "new_refresh_token",    // 新 Refresh Token（旧 Token 立即失效）
        "expiresIn": 7200
    }
}

Response (401 - Refresh Token 已失效):
{
    "code": 401,
    "message": "Token 已失效，请重新登录"
}
```

> **Token 旋转（Rotation）机制**：
> - 请求需同时提交 accessToken 和 refreshToken，服务端验证两者均有效后才发放新 Token
> - 新 refreshToken 生成后，旧 refreshToken 立即加入 Redis 黑名单
> - 黑名单条目 TTL = 原 refreshToken 剩余有效期，到期自动删除，无需额外清理任务
> - 同一 refreshToken 被使用 2 次以上触发告警（可能的 Refresh Token 重用攻击）
> - 旋转机制防止 Refresh Token 被盗用后持续使用

### 3.3 招聘管理 API

#### 3.3.1 岗位管理

```
GET    /api/v1/recruitment/jobs                # 岗位列表 (分页)
GET    /api/v1/recruitment/jobs/{id}           # 岗位详情
POST   /api/v1/recruitment/jobs                # 创建岗位
PUT    /api/v1/recruitment/jobs/{id}           # 更新岗位
DELETE /api/v1/recruitment/jobs/{id}           # 删除岗位
POST   /api/v1/recruitment/jobs/{id}/publish   # 发布到招聘平台
GET    /api/v1/recruitment/jobs/{id}/channels  # 查看发布渠道
```

#### 3.3.2 简历管理

```
GET    /api/v1/recruitment/resumes                    # 简历列表 (分页+筛选)
GET    /api/v1/recruitment/resumes/{id}               # 简历详情
GET    /api/v1/recruitment/resumes/{id}/score-detail  # 评分明细
POST   /api/v1/recruitment/resumes/import             # 批量导入 (Excel/CSV)
POST   /api/v1/recruitment/resumes/{id}/classify      # 手动分类
GET    /api/v1/recruitment/resumes/export             # 导出简历
POST   /api/v1/recruitment/resumes/search/nl          # 自然语言搜索

# 导入请求示例
POST /api/v1/recruitment/resumes/import
Content-Type: multipart/form-data

File: file (xlsx/xls/csv, max 50MB)

Response:
{
    "code": 200,
    "data": {
        "total": 150,
        "success": 142,
        "failed": 8,
        "failures": [
            {"row": 5, "reason": "身份证号格式无效"},
            {"row": 12, "reason": "手机号格式无效"}
        ]
    }
}

# 自然语言搜索示例
POST /api/v1/recruitment/resumes/search/nl
{
    "query": "找出所有有5年以上Java经验且做过微服务架构设计的候选人"
}
```

#### 3.3.3 考试管理

```
GET    /api/v1/recruitment/exams                    # 考试列表
POST   /api/v1/recruitment/exams                    # 创建考试 (Agent 组卷)
GET    /api/v1/recruitment/exams/{id}               # 考试详情
GET    /api/v1/recruitment/exams/{id}/qr-code       # 生成考试二维码
POST   /api/v1/recruitment/exams/{id}/publish        # 发布考试
GET    /api/v1/recruitment/exams/{id}/results        # 查看成绩
GET    /api/v1/recruitment/exams/{token}/paper        # 考生获取试卷 (Token 访问)
POST   /api/v1/recruitment/exams/{token}/submit       # 考生提交答案
```

#### 3.3.3.1 考试 Token 安全设计

- **Token 生成**：UUIDv4 + HMAC-SHA256 签名（密钥从 Vault 获取），格式：`{uuid}.{timestamp}.{signature}`
- **有效期**：考试开始时间前 10 分钟生效，考试结束后 5 分钟失效
- **防重放**：每次提交答案携带 nonce（32 位随机数），服务端 5 分钟内去重
- **绑定约束**：Token 与考试 ID + 考生信息绑定，不可跨考试使用
- **频率限制**：同 IP 每分钟最多 5 次请求，同 Token 提交频率限制为 1 次/分钟
- **存储安全**：Token 存储于 Redis，带过期时间，使用完毕后立即删除
- **访问日志**：所有考试 API 访问记录写入审计日志，包含 IP、User-Agent、时间戳

#### 3.3.4 题库管理

```
GET    /api/v1/recruitment/questions                # 题目列表
POST   /api/v1/recruitment/questions                # 添加题目
PUT    /api/v1/recruitment/questions/{id}           # 编辑题目
DELETE /api/v1/recruitment/questions/{id}           # 删除题目
POST   /api/v1/recruitment/questions/import         # 批量导入
```

### 3.4 入职管理 API

```
POST   /api/v1/onboarding/start                     # 开始入职流程
GET    /api/v1/onboarding/{employeeId}/progress     # 入职进度
POST   /api/v1/onboarding/{employeeId}/documents    # 上传证件
GET    /api/v1/onboarding/{employeeId}/documents    # 查看已传证件
POST   /api/v1/onboarding/{employeeId}/ocr          # OCR 识别
POST   /api/v1/onboarding/{employeeId}/face-capture # 人脸采集
POST   /api/v1/onboarding/{employeeId}/sign         # 电子签名
GET    /api/v1/onboarding/{employeeId}/agreements   # 待签协议
POST   /api/v1/onboarding/{employeeId}/complete     # 完成入职
GET    /api/v1/onboarding/list                      # 入职名单 (HR)
```

### 3.5 培训管理 API

```
GET    /api/v1/training/plans                       # 培训计划列表
POST   /api/v1/training/plans                       # 创建培训计划
GET    /api/v1/training/sessions                    # 培训场次列表
POST   /api/v1/training/sessions/{id}/check-in      # 签到
GET    /api/v1/training/sessions/{id}/attendance    # 签到统计
POST   /api/v1/training/sessions/{id}/exam          # 结业考试
GET    /api/v1/training/sessions/{id}/results       # 考试成绩
GET    /api/v1/training/certificates                # 证书列表
POST   /api/v1/training/video/generate              # 教材转视频
POST   /api/v1/training/audit/generate              # 生成审核资料包
```

### 3.6 考勤管理 API

```
GET    /api/v1/attendance/records                   # 考勤记录 (分页)
GET    /api/v1/attendance/summary                   # 考勤汇总
GET    /api/v1/attendance/anomalies                 # 异常列表
POST   /api/v1/attendance/leave                     # 请假申请
GET    /api/v1/attendance/shift/schedule            # 排班表
PUT    /api/v1/attendance/shift/schedule            # 调整排班
POST   /api/v1/attendance/sync                      # 手动同步打卡数据
GET    /api/v1/attendance/export                    # 导出考勤数据
```

### 3.7 薪资管理 API

```
POST   /api/v1/payroll/calculate                    # 启动薪资核算
GET    /api/v1/payroll/{month}                      # 查看核算结果
POST   /api/v1/payroll/{month}/review               # 审核确认
GET    /api/v1/payroll/{month}/anomalies            # 异常数据
GET    /api/v1/payroll/{month}/export               # 导出薪资明细
GET    /api/v1/payroll/payslip/current              # 当前月工资条
GET    /api/v1/payroll/payslip/history              # 历史工资条
GET    /api/v1/payroll/rules                        # 薪资规则
PUT    /api/v1/payroll/rules                        # 更新薪资规则
```

### 3.8 绩效管理 API

```
GET    /api/v1/performance/cycles                   # 考核周期列表
POST   /api/v1/performance/evaluate                  # 提交自评
GET    /api/v1/performance/review/pending            # 待审核列表
POST   /api/v1/performance/review/{id}/approve       # 审批确认
GET    /api/v1/performance/report                    # 绩效报告
GET    /api/v1/performance/distribution              # 等级分布
```

### 3.9 外务管理 API

```
POST   /api/v1/external/injury                      # 申报工伤
GET    /api/v1/external/injury/list                 # 工伤列表
GET    /api/v1/external/injury/{id}                 # 工伤详情
GET    /api/v1/external/injury/{id}/progress        # 理赔进度
POST   /api/v1/external/housing-fund/enroll         # 公积金参保
POST   /api/v1/external/housing-fund/seal           # 公积金封存
POST   /api/v1/external/housing-fund/supplement     # 公积金补缴
GET    /api/v1/external/housing-fund/list           # 公积金记录
```

### 3.10 员工服务 API

```
GET    /api/v1/employee/list                        # 员工列表
GET    /api/v1/employee/{id}                        # 员工档案
POST   /api/v1/employee/resignation                 # 离职申请
GET    /api/v1/employee/resignation/progress        # 离职进度
POST   /api/v1/employee/certificate                 # 申请证明
GET    /api/v1/employee/certificate/{id}            # 查看证明
POST   /api/v1/employee/expense                     # 费用报销
GET    /api/v1/employee/expense/list                # 报销记录
```

### 3.11 Agent 管理 API

```
GET    /api/v1/agent/dashboard                      # Agent 监控面板
GET    /api/v1/agent/{name}/status                  # Agent 状态
GET    /api/v1/agent/{name}/logs                    # Agent 执行日志
PUT    /api/v1/agent/{name}/config                  # 更新 Agent 参数
POST   /api/v1/agent/{name}/restart                 # 重启 Agent
POST   /api/v1/agent/{name}/trigger                 # 手动触发 Agent
GET    /api/v1/agent/alerts                         # 告警列表
POST   /api/v1/agent/alerts/{id}/acknowledge        # 确认告警
```

### 3.12 系统管理 API

```
GET    /api/v1/system/users                         # 用户列表
POST   /api/v1/system/users                         # 创建用户
PUT    /api/v1/system/users/{id}                    # 更新用户
DELETE /api/v1/system/users/{id}                    # 删除用户
GET    /api/v1/system/roles                         # 角色列表
PUT    /api/v1/system/roles/{id}/permissions        # 更新角色权限
GET    /api/v1/system/audit-logs                    # 审计日志
GET    /api/v1/system/config                        # 系统配置
PUT    /api/v1/system/config                        # 更新系统配置
POST   /api/v1/system/backup                        # 手动备份
POST   /api/v1/system/restore                       # 恢复备份
```

### 3.13 Flowable 流程管理 API

> **说明**：Flowable 用于入职办理、薪资核算、工伤申报等长流程的 BPMN 2.0 编排。以下 API 供 HR 操作人员在流程界面进行审核、审批操作。

#### 3.13.1 流程实例管理

```
GET    /api/v1/process/instances                     # 流程实例列表
       ?status=RUNNING&assignee=123&keyword=入职
GET    /api/v1/process/instances/{instanceId}        # 流程实例详情
POST   /api/v1/process/instances/{instanceId}/cancel  # 终止流程实例
```

**流程实例列表响应**：
```json
{
    "code": 200,
    "data": {
        "total": 50,
        "items": [
            {
                "instanceId": "proc_20260612_001",
                "processDefinitionKey": "onboarding_process",
                "processName": "新员工入职办理",
                "status": "RUNNING",  // RUNNING / COMPLETED / CANCELLED
                "assignee": "123",
                "assigneeName": "张三",
                "startTime": "2026-06-10T09:00:00",
                "currentActivity": "hr_review",
                "currentActivityName": "HR审核"
            }
        ]
    }
}
```

#### 3.13.2 任务管理

```
GET    /api/v1/process/tasks                         # 我的待办任务
       ?status=PENDING
GET    /api/v1/process/tasks/{taskId}                # 任务详情
POST   /api/v1/process/tasks/{taskId}/approve         # 审批通过
POST   /api/v1/process/tasks/{taskId}/reject          # 审批驳回
POST   /api/v1/process/tasks/{taskId}/comment         # 添加审批意见
GET    /api/v1/process/tasks/history                  # 我的已办任务
```

**审批通过请求**：
```
POST /api/v1/process/tasks/{taskId}/approve
Content-Type: application/json

{
    "comment": "薪资核算无误，同意发放",
    "variables": {
        "approved": true,
        "approvalAmount": 15000.00
    }
}
```

**审批驳回请求**：
```
POST /api/v1/process/tasks/{taskId}/reject
Content-Type: application/json

{
    "comment": "考勤数据异常，请核实后重新提交",
    "variables": {
        "approved": false,
        "rejectionReason": "考勤数据异常"
    }
}
```

#### 3.13.3 流程定义管理

```
GET    /api/v1/process/definitions                   # 流程定义列表
GET    /api/v1/process/definitions/{key}/model       # 获取 BPMN 模型
POST   /api/v1/process/definitions/{key}/deploy      # 部署新流程定义
POST   /api/v1/process/definitions/{key}/suspended   # 挂起流程定义
POST   /api/v1/process/definitions/{key}/activate    # 激活流程定义
```

> **流程管理说明**：
> - 流程实例由 Agent 自动启动（如入职 Agent 调用 `RuntimeService.startProcessInstanceByKey()`）
> - 人类用户通过任务 API 进行审核/审批操作
> - 流程变量通过 `variables` 对象传递，用于条件分支和后续节点判断
> - 流程终止需有管理员权限，终止后产生死信记录供审计

---

## 4. 数据流设计

### 4.1 简历筛选数据流

```
招聘平台 (前程无忧/中国人才热线)
    ↓ (每15分钟定时拉取)
简历抓取 Agent (RecruitmentChannelAgent)
    ↓ (Spring Event: ResumeNewEvent)
简历去重与格式校验
    ↓
简历匹配 Agent (ResumeMatchingAgent)
    ├── 学历匹配 (15%)
    ├── 工作经验匹配 (25%)
    ├── 技能匹配 (20%)
    ├── 年龄匹配 (5%)
    ├── 证书匹配 (15%)
    └── 语义综合匹配 (20%) ← LLM API
    ↓
综合评分计算 (0-100分)
    ↓
自动分拣:
    ├── > 合格线+10分 → 高潜简历 → 自动入库
    ├── 合格线-10 ~ 合格线+10 → 候选简历 → 提交HR审核
    └── < 合格线-10分 → 淘汰简历 → 自动标记
    ↓ (Spring Event: ResumeClassifiedEvent)
简历入库 (MySQL: resume 表)
    ↓
通知 HR (Redis Stream: notification channel)
    ↓
前端 Dashboard 待办提醒
```

### 4.2 薪资核算数据流

```
月末定时触发 (XXL-JOB: MonthlyPayrollJob)
    ↓
薪资 Agent (PayrollAgent)
    ├── Fan-Out: 并行拉取数据
    │   ├── 考勤 Agent → 当月考勤数据 (通过 AttendanceInternalApi 内部接口)
    │   ├── 社保/公积金系统 → 缴纳数据 (API)
    │   └── 薪资规则库 → 现行规则 (Redis 缓存)
    ├── Fan-In: 汇聚数据
    │
    ├── 计算流程
    │   ├── 应发工资 = 基本工资 + 加班费 - 考勤扣款 + 补贴
    │   ├── 加班费 = PayrollRuleService.getOvertimeRates().calculate(加班时长)
    │   ├── 个人社保 = 社保个人缴纳额
    │   ├── 个人公积金 = 公积金个人缴纳额
    │   ├── 应税收入 = 应发 - 社保 - 公积金 - PayrollRuleService.getTaxFreeThreshold() - 专项扣除
    │   ├── 个税 = 七级累进税率计算
    │   └── 实发 = 应发 - 社保 - 公积金 - 个税
    │
    ├── 异常检测
    │   ├── 波动 ±20% 标记
    │   ├── 个税负数标记
    │   ├── 社保/公积金为 0 标记
    │   ├── 低于最低工资标记
    │   └── 加班费异常标记
    │
    └── 输出: 全员薪资明细表
    ↓ (Spring Event: PayrollCalculatedEvent)
推送 HR 审核 (Redis Stream: notification channel)
    ↓
HR 审核确认 / 退回重算
    ↓
工资条 Agent (PayslipAgent)
    ├── 批量生成工资条
    ├── 发送 (短信/邮件/APP 推送)
    └── 追踪阅读状态
    ↓
归档 (MySQL: payroll 表)
```

> **薪资计算规则可配置化**：
> - 所有薪资计算参数（加班费倍数、个税起征点、社保比例等）由 `payroll_rule` 表管理
> - 支持按生效日期版本化，同一规则可设置有效期
> - Agent 通过 `PayrollRuleService` 读取当前有效规则进行计算
> - 规则变更需经 HR 管理员审批，变更历史保留至少 15 年

### 4.3 工伤处理数据流

```
工伤事件触发 (员工报告 / 系统检测)
    ↓
工伤 Agent (ExternalAgent)
    ├── 生成事故说明模板
    ├── 指导员工填写 (≥50字)
    ├── 发出材料清单
    │   ├── 病案
    │   ├── 诊断书
    │   ├── 旁证
    │   ├── 身份证件
    │   └── 出勤记录
    ├── Feedback Loop: 校验材料完整性
    │   ├── 缺失 → 提醒补传
    │   └── 完整 → 进入下一步
    │
    ├── 打包标准化备案文档
    │
    └── 调用 RPA Agent
        ↓
RPA Agent (RPAAgent)
    ├── 登录社保系统 (Playwright via HTTP API → RPA Python 子服务)
    ├── 自动填写表单
    ├── 上传备案材料
    ├── 提交申报
    ├── 截图保存回执
    └── 返回申报回执
    ↓
跟踪理赔进度 (定时查询)
    ↓
状态更新 → 通知相关人员 (Redis Stream: notification channel)
    ↓
理赔到账 → 记录理赔金额
```

### 4.4 新员工入职数据流

```
新员工扫码进入入职门户
    ↓
入职引导 Agent (OnboardingGuideAgent)
    ├── Step 1: 基本信息确认
    ├── Step 2: 上传证件材料
    │   ├── 身份证正反面
    │   ├── 学历证书
    │   └── 证件照
    │   ↓
    │   OCR Agent (OCRAgent)
    │   ├── 调用 OCR Python 子服务 (HTTP API)
    │   ├── 识别证件并提取结构化信息
    │   └── 返回识别结果
    │
    ├── Step 3: 实名认证比对
    │   ├── OCR 信息 vs 身份证原件
    │   └── 不一致 → 提醒重新上传
    │
    ├── Step 4: 签署电子协议
    │   ├── 推送协议列表
    │   ├── 手写签名
    │   └── 加盖时间戳和水印
    │
    ├── Step 5: 人脸采集
    │   ↓
    │   人脸 Agent (FaceAgent)
    │   ├── 检测照片质量
    │   ├── 调用 Face++ API 与身份证照片比对
    │   ├── 写入人脸门禁系统
    │   └── 返回比对结果
    │
    └── Step 6: 生成人事档案
        ├── 组装结构化信息
        ├── 建立档案索引
        └── 归档至 MinIO
    ↓
入职完成通知 HR (Redis Stream: notification channel)
    ↓
触发公积金参保 (ExternalAgent)
    ↓
触发培训计划 (TrainingAgent)
```

---

## 5. 中间件设计

### 5.1 事件机制

> **设计原则**：模块化单体架构内模块间优先直接方法调用或 Spring Event，避免引入重量级消息队列。

#### 5.1.1 Spring Event (进程内事件)

**适用场景**：同一进程内模块间的解耦通信（如简历分拣后通知 HR 审核）。

```java
// 事件定义
public class ResumeClassifiedEvent extends ApplicationEvent {
    private final String resumeId;
    private final String classifyResult;
    private final String flowId;
    
    public ResumeClassifiedEvent(Object source, String resumeId, String classifyResult, String flowId) {
        super(source);
        this.resumeId = resumeId;
        this.classifyResult = classifyResult;
        this.flowId = flowId;
    }
}

// 事件发布
@Service
public class ResumeMatchingService {
    @Autowired
    private ApplicationEventPublisher eventPublisher;
    
    public void classifyResume(Resume resume) {
        // ... 分拣逻辑
        eventPublisher.publishEvent(new ResumeClassifiedEvent(
            this, resume.getId(), result, flowId));
    }
}

// 事件监听（@Async 异步执行，避免阻塞主流程）
@Component
public class HRNotificationListener {
    @Async
    @EventListener
    public void onResumeClassified(ResumeClassifiedEvent event) {
        // 通知 HR 审核
        notificationService.sendHRNotification(event);
    }
}
```

> **异步事件监听配置**：
> - `@EventListener` 默认同步执行，涉及 LLM 调用等耗时操作的监听器必须添加 `@Async` 注解
> - 配置独立线程池：在 `SpringEventConfig` 中定义 `AsyncEventExecutor` Bean
> - 线程池参数：核心线程数 5，最大线程数 20，队列容量 100
> - 替代方案：如事件处理逻辑复杂度增加，可改用 `ApplicationEventMulticaster` 异步模式

#### 5.1.2 Redis Stream（可靠事件传递）

**适用场景**：跨服务可靠事件传递（如薪资核算完成通知 HR 审核、入职完成触发后续流程等不可丢失事件）。

| Channel | 用途 | 消费者 | 可靠性 |
|---------|------|--------|--------|
| `notification:email` | 邮件通知 | 邮件发送服务 | at-least-once |
| `notification:sms` | 短信通知 | 短信发送服务 | at-least-once |
| `notification:push` | APP 推送 | 推送服务 | best-effort |
| `agent:event` | Agent 状态更新 | 前端 Dashboard (WebSocket) | best-effort |
| `agent:error` | Agent 错误告警 | 告警服务 | at-least-once |
| `rpa:task` | RPA 任务分发 | RPA Python 子服务 | at-least-once |
| `rpa:result` | RPA 结果回传 | 主服务 RPA 模块 | at-least-once |

```java
// Redis Stream 发布
@Service
public class RedisStreamService {
    
    @Autowired
    private StringRedisTemplate redisTemplate;
    
    public void publish(String stream, String message) {
        Map<String, String> entry = new HashMap<>();
        entry.put("payload", message);
        redisTemplate.opsForStream().add(stream, entry);
    }
}

// Redis Stream 订阅（使用 StreamListener 避免死循环阻塞）
@Component
public class NotificationConsumer {
    
    @Autowired
    private StringRedisTemplate redisTemplate;
    
    @Autowired
    private TaskExecutor streamListenerExecutor;
    
    private final static String GROUP = "notification-group";
    private final static String CONSUMER = "notification-consumer";
    
    private StreamListener<String, MapRecord<String, String, String>> listener;
    
    @PostConstruct
    public void startListening() {
        // StreamListener 正确用法：无需 while 循环，由框架内部管理消费循环
        listener = StreamListener
            .<String, MapRecord<String, String, String>>consumer(
                Consumer.from(GROUP, CONSUMER))
            .stream(Streams.stream("notification:email"))
            .read(
                StreamReadOptions.empty().block(Duration.ofSeconds(5)))
            .listen(record -> {
                try {
                    processNotification(record.getValue());
                    // 处理完成后 ACK
                    redisTemplate.opsForStream().acknowledge(
                        "notification:email", record.getId());
                } catch (Exception e) {
                    log.error("处理通知消息失败: recordId={}", record.getId(), e);
                    // 不 ACK，消息将重新入队重试
                }
            });
        
        // 在独立线程中运行，不阻塞主线程
        streamListenerExecutor.execute(() -> {
            listener.start();
        });
    }
    
    @PreDestroy
    public void stopListening() {
        if (listener != null) {
            listener.stop();
            listener.flush();
        }
    }
    
    private void processNotification(Map<String, String> values) {
        // 通知处理逻辑
    }
}
```

#### 5.1.3 消息格式

```json
{
    "message_id": "uuid-v4",
    "trace_id": "uuid-v4",
    "flow_id": "uuid-v4",
    "source": "module_name",
    "target": "module_name|channel_name",
    "event_type": "string",
    "priority": "HIGH|MEDIUM|LOW",
    "ttl_seconds": 3600,
    "payload": {},
    "metadata": {
        "created_at": "2026-06-12T10:00:00Z",
        "retry_count": 0,
        "max_retries": 3
    }
}
```

### 5.2 Redis 缓存

#### 缓存策略

| 缓存 Key 模式 | 过期时间 | 用途 |
|--------------|---------|------|
| `user:session:{userId}` | 2h | 用户会话 |
| `user:token:{tokenId}` | 2h | Token 黑名单 |
| `payroll:rule:current` | 永久 | 现行薪资规则 |
| `attendance:today:{date}` | 24h | 当日考勤 |
| `recruitment:job:{jobId}` | 24h | 岗位信息 |
| `training:qr:{qrCode}` | 2h | 签到二维码 |
| `exam:paper:{examId}` | 考试期间 | 试卷缓存 |
| `rate:limit:{ip}:{action}` | 1min | 速率限制 |
| `agent:lock:{agentName}` | 30s | Agent 分布式锁 |
| `distributed:lock:{resource}` | 10s | 通用分布式锁 |

#### 分布式锁实现

```java
@Service
public class DistributedLockService {
    
    @Autowired
    private RedissonClient redisson;
    
    public boolean tryLock(String lockKey, long waitTime, long leaseTime, TimeUnit unit) {
        RLock lock = redisson.getLock(lockKey);
        try {
            return lock.tryLock(waitTime, leaseTime, unit);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }
    }
    
    public void unlock(String lockKey) {
        RLock lock = redisson.getLock(lockKey);
        if (lock.isHeldByCurrentThread()) {
            lock.unlock();
        }
    }
}
```

### 5.3 Flowable 流程引擎

> **选型理由**：Flowable 对 MySQL 兼容性优于 Camunda 7.x（Camunda 内置引擎要求 PostgreSQL），更适合当前技术栈。

#### 流程定义 (BPMN)

```
入职流程 (onboarding_process.bpmn):
    
    [开始] → 扫码登录
        → [入职引导 Agent] 引导材料上传
        → [OCR Agent] 识别证件
        → 校验完整性?
            → 否 → [Feedback Loop] 提醒补传 → 回到材料上传
            → 是 → [人脸 Agent] 采集人脸
        → 签署电子协议
        → 生成人事档案
        → [公积金 Agent] 自动参保
        → [培训 Agent] 推送培训计划
        → [结束]

薪资核算流程 (payroll_process.bpmn):
    
    [定时触发: 月末] → [Fan-Out]
        → [考勤 Agent] 拉取考勤数据
        → [社保系统] 拉取缴费数据
        → [规则库] 读取薪资规则
    → [Fan-In] 汇聚数据
    → [薪资 Agent] 执行计算
    → 异常检测
        → 有异常 → 标记异常
    → [HR 审核] 等待人工确认
        → 确认 → [工资条 Agent] 批量发放
        → 退回 → [薪资 Agent] 重新计算
    → [结束]
```

**Flowable 与 Agent 编排器职责划分**：

| 维度 | Flowable BPMN | Agent 编排器 |
|------|--------------|-------------|
| 生命周期 | 长生命周期（跨天/跨周） | 短生命周期（分钟级） |
| 典型流程 | 入职流程、薪资核算、工伤申报、离职流程 | 简历匹配流水线、薪资 Fan-Out/Fan-In、组卷/阅卷 |
| 人工介入 | 需要（审核节点、等待节点） | 无需（纯自动执行） |
| 状态持久化 | BPMN 引擎自动管理 | 自定义 process_instance 表 |
| 断点恢复 | 引擎内置 | 根据 flow_id 从断点恢复 |
| 重试机制 | BPMN Service Task 重试 | SDK 内置 RetryPolicy |

**协同方式**：
- Flowable BPMN 中的 Service Task 节点触发 Agent 编排器（通过 HTTP/RPC 调用）
- Agent 编排器执行完成后，通过 `AgentCompletionCallback` 接口回调推进 BPMN 流程
- 两者共享 `flow_id`（Flowable 的 processInstanceId）作为全局流程追踪 ID
- Agent 编排器产生的中间状态写入 `process_instance` 表，Flowable 通过外部任务模式（External Task Pattern）读取

#### 5.3.1 AgentCompletionCallback 接口定义

```java
/**
 * Agent 完成回调接口 — Agent 执行完成后调用此接口通知 Flowable 推进流程
 */
public interface AgentCompletionCallback {
    
    /**
     * Agent 执行成功，推进流程到下一节点
     * @param taskId Flowable 任务 ID
     * @param variables 流程变量（用于条件分支判断）
     */
    void complete(String taskId, Map<String, Object> variables);
    
    /**
     * Agent 执行失败，触发异常处理或补偿流程
     * @param taskId Flowable 任务 ID
     * @param error 错误信息
     * @param variables 可选的流程变量
     */
    void onError(String taskId, String error, Map<String, Object> variables);
}

/**
 * AgentCompletionCallback 实现 — 调用 Flowable RuntimeService 推进流程
 */
@Service
public class FlowableAgentCallback implements AgentCompletionCallback {
    
    @Autowired
    private RuntimeService runtimeService;
    
    @Autowired
    private TaskService taskService;
    
    @Override
    @Transactional
    public void complete(String taskId, Map<String, Object> variables) {
        // 查询任务所属的流程实例
        Task task = taskService.createTaskQuery().taskId(taskId).singleResult();
        if (task == null) {
            // 外部任务模式：直接 complete
            runtimeService.complete(taskId, variables);
        } else {
            // 人工任务模式：complete 任务
            taskService.complete(taskId, variables);
        }
    }
    
    @Override
    @Transactional
    public void onError(String taskId, String error, Map<String, Object> variables) {
        // 设置错误变量，触发 BPMN 异常事件边界
        variables.put("agent_error", error);
        variables.put("agent_status", "FAILED");
        
        // 设置业务关键错误，触发 BPMN 的 BPMNError 事件
        runtimeService.setVariable(taskId, "bpmnError", error);
        
        // 如果流程需要人工干预，创建补偿任务
        taskService.createTask(taskId + "_compensation");
        taskService.setAssignee(taskId + "_compensation", "hr_admin");
    }
}
```

**回调调用示例**：
```java
@Service
public class ResumeMatchingAgent extends BaseAgent {
    
    @Autowired
    private AgentCompletionCallback agentCallback;
    
    @Override
    public AgentResult act(Decision decision, AgentContext context) {
        // ... Agent 执行逻辑
        
        // Agent 完成后回调 Flowable 推进流程
        Map<String, Object> variables = new HashMap<>();
        variables.put("matchScore", decision.getScore());
        variables.put("matchResult", decision.getResult());
        
        try {
            agentCallback.complete(context.getTaskId(), variables);
        } catch (Exception e) {
            agentCallback.onError(context.getTaskId(), e.getMessage(), variables);
            throw e;
        }
        
        return AgentResult.success();
    }
}
```

### 5.4 XXL-JOB 定时任务

| Job Handler | Cron 表达式 | 描述 |
|-------------|------------|------|
| ResumeCrawlJob | `0 */15 * * * ?` | 每 15 分钟抓取简历 |
| AttendanceSyncJob | `0 */30 * * * ?` | 每 30 分钟同步打卡数据 |
| MonthlyPayrollJob | `0 0 2 27 * ?` | 每月 27 日凌晨 2 点核算薪资（为 2 月留有余量） |
| CertificateExpiryJob | `0 9 * * ?` | 每天 9 点检查证书效期 |
| TalentHealthCheckJob | `0 0 3 ? * 0` | 每周日凌晨 3 点简历健康检查 |
| RPAValidationJob | `0 10 ? * 1` | 每周一 10 点验证 RPA 流程 |
| DataArchiveJob | `0 0 2 ? * 0` | 每周日凌晨 2 点数据归档 |
| BackupJob | `0 0 1 ? * 6` | 每周日凌晨 1 点全量备份 |
| ModelAccuracyJob | `0 0 9 1 * ?` | 每月 1 日 9 点模型精度复查 |
| BiasTestJob | `0 0 10 1 */3 ?` | 每季度首日 10 点偏见测试 |

---

## 6. 安全策略

### 6.1 认证流程

```
客户端 → 输入账号密码
    ↓
AuthController → 验证凭证
    ↓
AuthService → 查询用户信息
    ↓
检查是否需要 MFA?
    ├── 是 → 生成临时 Token → 发送验证码
    │       → 客户端输入验证码
    │       → MFAController → 验证验证码
    │       → 生成正式 JWT Token
    │
    └── 否 → 直接生成 JWT Token
    ↓
返回 Token 给客户端
    ↓
后续请求携带 Token (Authorization: Bearer ***
    ↓
JwtAuthenticationFilter → 验证 Token
    ↓
加载用户权限到 SecurityContext
    ↓
业务逻辑执行
```

### 6.2 JWT Token 设计

```java
public class JwtToken {
    // Header
    private String alg = "RS256";
    private String typ = "JWT";
    
    // Payload
    private String sub;          // 用户 ID
    private String username;     // 用户名
    private List<String> roles;  // 角色列表
    private List<String> perms;  // 权限列表
    private Long iat;            // 签发时间
    private Long exp;            // 过期时间
    private Long nbf;            // 生效时间
    private String jti;          // Token 唯一 ID
    private String traceId;      // 链路追踪 ID
}

// Token 配置
// Access Token: 有效期 2 小时
// Refresh Token: 有效期 7 天
// RSA 密钥对: 2048 位，定期轮换
```

### 6.3 RBAC 权限模型

```
用户 (User)
    ↓ (多对多)
角色 (Role)
    ↓ (多对多)
权限 (Permission)

权限命名规则: {模块}:{资源}:{操作}

示例:
recruitment:job:create        创建岗位
recruitment:job:read          查看岗位
recruitment:job:update        编辑岗位
recruitment:job:delete        删除岗位
recruitment:resume:read       查看简历
recruitment:resume:export     导出简历
payroll:data:read             查看薪资数据 (需 MFA)
payroll:data:update           修改薪资数据 (需 MFA)
system:user:create            创建用户 (管理员)
system:audit:read             查看审计日志 (管理员)
```

### 6.4 数据加密

```java
@Component
public class DataEncryptionService {
    
    @Autowired
    private VaultService vaultService;  // 从 Vault 获取 AES 密钥
    
    private static final String ALGORITHM = "AES/GCM/NoPadding";
    private static final int KEY_SIZE = 256;
    private static final int IV_LENGTH = 12;
    private static final int TAG_LENGTH = 128;
    
    /**
     * AES-256-GCM 加密
     * @param plaintext 明文
     * @return Base64 编码的 IV + 密文
     */
    public String encrypt(String plaintext) throws GeneralSecurityException {
        SecretKey key = vaultService.getAESKey("hr-data-encryption");
        
        Cipher cipher = Cipher.getInstance(ALGORITHM);
        GCMParameterSpec parameterSpec = new GCMParameterSpec(TAG_LENGTH, generateIV());
        cipher.init(Cipher.ENCRYPT_MODE, key, parameterSpec);
        
        byte[] ciphertext = cipher.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
        
        // IV + ciphertext 组合后 Base64 编码
        byte[] combined = new byte[IV_LENGTH + ciphertext.length];
        System.arraycopy(parameterSpec.getIV(), 0, combined, 0, IV_LENGTH);
        System.arraycopy(ciphertext, 0, combined, IV_LENGTH, ciphertext.length);
        
        return Base64.getEncoder().encodeToString(combined);
    }
    
    /**
     * AES-256-GCM 解密
     * @param ciphertextWithIV Base64 编码的 IV + 密文
     * @return 明文
     */
    public String decrypt(String ciphertextWithIV) throws GeneralSecurityException {
        SecretKey key = vaultService.getAESKey("hr-data-encryption");
        
        byte[] combined = Base64.getDecoder().decode(ciphertextWithIV);
        byte[] iv = Arrays.copyOfRange(combined, 0, IV_LENGTH);
        byte[] ciphertext = Arrays.copyOfRange(combined, IV_LENGTH, combined.length);
        
        Cipher cipher = Cipher.getInstance(ALGORITHM);
        GCMParameterSpec parameterSpec = new GCMParameterSpec(TAG_LENGTH, iv);
        cipher.init(Cipher.DECRYPT_MODE, key, parameterSpec);
        
        byte[] plaintext = cipher.doFinal(ciphertext);
        return new String(plaintext, StandardCharsets.UTF_8);
    }
    
    private byte[] generateIV() {
        byte[] iv = new byte[IV_LENGTH];
        SecureRandom random = new SecureRandom();
        random.nextBytes(iv);
        return iv;
    }
    
    // 加密字段:
    // - 身份证号 (employee.id_number)
    // - 人脸特征 (face.features)
    // - 薪资数据 (payroll.net_pay) - 数据库级加密
    // - 银行账号 (employee_pay_profile.bank_account)
    
    // 密钥管理方案:
    // - AES 密钥存储于 HashiCorp Vault
    // - 密钥定期轮换 (90 天)
    // - 应用启动时从 Vault 加载，内存中缓存
    // - 不同环境使用不同密钥 (dev/test/prod 隔离)
}
```

### 6.5 审计日志 (AOP 切面)

```java
@Aspect
@Component
public class AuditLogAspect {
    
    @Around("@annotation(AuditLog)")
    public Object audit(ProceedingJoinPoint point, AuditLog annotation) 
            throws Throwable {
        AuditLogEntry entry = new AuditLogEntry();
        entry.setOperationTime(LocalDateTime.now());
        entry.setOperator(getCurrentUserId());
        entry.setOperatorIp(getClientIp());
        entry.setOperationType(annotation.type());
        entry.setModule(annotation.module());
        entry.setTarget(annotation.target());
        
        // 记录操作前快照（beforeSnapshot）
        entry.setBeforeSnapshot(serialize(getTargetObject(point)));
        
        long start = System.currentTimeMillis();
        try {
            Object result = point.proceed();
            entry.setResult("SUCCESS");
            entry.setAfterSnapshot(serialize(result));
            return result;
        } catch (Exception e) {
            entry.setResult("FAILED");
            entry.setErrorDetail(e.getMessage());
            throw e;
        } finally {
            entry.setDuration(System.currentTimeMillis() - start);
            auditLogService.save(entry);
        }
    }
    
    /**
     * 从方法参数中提取目标对象 ID，查询数据库获取操作前状态
     */
    private Object getTargetObject(ProceedingJoinPoint point) {
        return auditorRegistry.getAuditor(point.getTarget().getClass())
            .getBeforeSnapshot(point);
    }
}
```

#### 6.5.1 Auditor 接口定义

```java
/**
 * 模块审计器接口 — 定义如何提取目标对象的操作前快照
 * 各业务模块实现此接口，注册到 AuditorRegistry 中
 */
public interface ModuleAuditor<T> {
    /**
     * 返回此 Auditor 适用的 Service 类
     */
    Class<T> getServiceClass();

    /**
     * 从方法参数中提取目标对象 ID，查询数据库返回操作前快照
     * @param point AOP 切点
     * @return 操作前数据快照（Map 或实体对象）
     */
    Object getBeforeSnapshot(ProceedingJoinPoint point);
}
```

#### 6.5.2 AuditorRegistry 注册机制

```java
/**
 * Auditor 注册中心 — 自动扫描并注册所有 ModuleAuditor 实现
 */
@Component
public class AuditorRegistry {

    private final Map<Class<?>, ModuleAuditor<?>> auditorMap = new ConcurrentHashMap<>();

    // Spring 自动注入所有 ModuleAuditor 实现
    public AuditorRegistry(List<ModuleAuditor<?>> auditors) {
        for (ModuleAuditor<?> auditor : auditors) {
            auditorMap.put(auditor.getServiceClass(), auditor);
        }
    }

    @SuppressWarnings("unchecked")
    public <T> ModuleAuditor<T> getAuditor(Class<T> serviceClass) {
        ModuleAuditor<T> auditor = (ModuleAuditor<T>) auditorMap.get(serviceClass);
        if (auditor == null) {
            throw new IllegalStateException(
                "未注册 Auditor: " + serviceClass.getName() +
                "，请在对应模块中实现 ModuleAuditor 接口");
        }
        return auditor;
    }
}
```

#### 6.5.3 各模块 Auditor 实现示例

```java
// 薪资模块 Auditor
@Service
public class PayrollAuditor implements ModuleAuditor<PayrollService> {
    private final PayrollMapper payrollMapper;

    public PayrollAuditor(PayrollMapper payrollMapper) {
        this.payrollMapper = payrollMapper;
    }

    @Override
    public Class<PayrollService> getServiceClass() {
        return PayrollService.class;
    }

    @Override
    public Object getBeforeSnapshot(ProceedingJoinPoint point) {
        String[] args = point.getArgs();
        // 从参数提取月份，查询操作前薪资记录
        String month = (String) args[0];
        return payrollMapper.selectByMonth(month);
    }
}

// 员工模块 Auditor
@Service
public class EmployeeAuditor implements ModuleAuditor<EmployeeService> {
    private final EmployeeMapper employeeMapper;

    public EmployeeAuditor(EmployeeMapper employeeMapper) {
        this.employeeMapper = employeeMapper;
    }

    @Override
    public Class<EmployeeService> getServiceClass() {
        return EmployeeService.class;
    }

    @Override
    public Object getBeforeSnapshot(ProceedingJoinPoint point) {
        // 安全提取参数：避免强制类型转换导致 ClassCastException
        Object[] args = point.getArgs();
        if (args == null || args.length == 0) {
            return null;
        }
        
        // 按参数类型安全提取 employeeId
        Long employeeId = null;
        for (Object arg : args) {
            if (arg instanceof Long) {
                employeeId = (Long) arg;
                break;
            } else if (arg instanceof String) {
                // 支持 String 类型的 ID
                try {
                    employeeId = Long.parseLong((String) arg);
                    break;
                } catch (NumberFormatException e) {
                    // 跳过非数字字符串
                }
            } else if (arg != null) {
                // 尝试从对象中提取 getId()
                try {
                    Method getId = arg.getClass().getMethod("getId");
                    Object id = getId.invoke(arg);
                    if (id instanceof Long) {
                        employeeId = (Long) id;
                        break;
                    } else if (id instanceof String) {
                        try {
                            employeeId = Long.parseLong((String) id);
                            break;
                        } catch (NumberFormatException ignored) {}
                    }
                } catch (NoSuchMethodException | IllegalAccessException | 
                         InvocationTargetException e) {
                    // 该参数没有 getId 方法，继续查找
                }
            }
        }
        
        if (employeeId == null) {
            log.warn("未能从方法参数中提取 employeeId: method={}", 
                point.getSignature().toShortString());
            return null;
        }
        
        return employeeMapper.selectById(employeeId);
    }
}
```

> **Auditor 设计说明**：
> - `ModuleAuditor<T>` 泛型接口绑定到具体 Service 类，避免运行时类型转换错误
> - `AuditorRegistry` 通过构造函数注入自动注册所有 Auditor 实现，无需手动配置
> - 每个业务模块独立实现自己的 Auditor，遵循开闭原则
> - 未注册 Auditor 的 Service 调用审计注解时将抛出明确异常，避免静默失败
> - 参数提取采用安全反射方式：优先 `instanceof` 类型检查，再尝试 `getId()` 反射调用，最后回退到日志警告，避免 `ClassCastException`

// 使用示例
@AuditLog(type = "UPDATE", module = "PAYROLL", target = "payroll:{month}")
public PayrollResult calculatePayroll(String month) {
    // 薪资核算逻辑
}
```

> **审计日志前后快照说明**：
> - `beforeSnapshot`：操作前的数据状态快照，用于追溯变更差异
> - `afterSnapshot`：操作后的数据状态快照
> - 前后快照对比可生成变更报告（Diff Report），用于薪资修改、员工信息变更等敏感操作的审计合规
> - 快照数据采用 JSON 格式存储，敏感字段（如身份证号、薪资）加密存储

---

## 7. Agent 运行时设计

### 7.0 Service 与 Agent 边界定义

> **职责划分原则**：
> - **Service 层**：负责 CRUD 操作、数据库事务、数据校验、业务规则执行。所有数据持久化操作均由 Service 完成。
> - **Agent 层**：负责推理决策、LLM 调用、外部 API 调用、复杂任务编排。Agent 不直接操作数据库，通过调用 Service 完成数据读写。
>
> **交互契约**：
>
> | 场景 | Service 职责 | Agent 职责 |
> |------|-------------|-----------|
> | 简历匹配 | 读取简历/岗位数据、保存评分结果 | 执行匹配算法、LLM 语义分析、生成分数 |
> | 薪资核算 | 读取考勤/社保数据、保存核算结果 | 执行计算逻辑、异常检测、生成审核报告 |
> | 工伤申报 | 保存案件信息、上传附件 | 生成事故说明、调用 RPA 子服务、跟踪进度 |
> | 入职引导 | 保存员工档案、存储证件文件 | 引导流程、OCR 识别、人脸采集、材料校验 |
>
> **调用方向**：Agent → Service（Agent 调用 Service 方法），Service 不调用 Agent。
> Service 通过 Spring Event 发布业务事件，Agent 监听事件后执行推理任务。

### 7.1 Agent 基类

```java
public abstract class BaseAgent {
    
    protected String agentName;
    protected AgentLogger logger;
    protected AgentMessageProducer messageProducer;
    protected GuardrailExecutor guardrailExecutor;
    protected RetryPolicy retryPolicy;
    
    /**
     * Agent 执行入口
     */
    public AgentResult execute(AgentContext context) {
        // 1. 记录开始
        logger.logStart(agentName, context.getFlowId());
        
        // 2. 感知阶段: 获取所需数据
        var inputs = perceive(context);
        
        // 3. 推理阶段: 分析并决策
        var decision = reason(inputs, context);
        
        // 4. 护栏检查（在执行 act() 之前，避免产生未提交事务）
        guardrailExecutor.check(decision);

        // 5. 行动阶段: 执行操作
        // 注意：act() 内部调用 Service 方法涉及数据库事务时，
        // 每个 Service 方法应在独立的 @Transactional 事务中执行，
        // guardrail 检查已通过后才进入 act()，不会产生未提交事务或脏数据。
        // 如 act() 需跨多个 Service 操作，建议使用 TransactionTemplate 手动管理事务边界。
        AgentResult result;
        try {
            result = retryPolicy.execute(() -> act(decision, context));
        } catch (GuardrailException e) {
            result = AgentResult.blocked(e.getMessage());
        } catch (Exception e) {
            result = AgentResult.failed(e.getMessage());
            logger.logError(agentName, context.getFlowId(), e);
        }
        
        // 6. 记录结果
        logger.logEnd(agentName, context.getFlowId(), result);
        
        // 7. 发布事件
        messageProducer.send(context.getFlowId(), agentName, result);
        
        return result;
    }
    
    // 子类实现
    protected abstract Map<String, Object> perceive(AgentContext context);
    protected abstract Decision reason(Map<String, Object> inputs, AgentContext context);
    protected abstract AgentResult act(Decision decision, AgentContext context);
}
```

#### 7.1.1 Agent 注册与 Bean 生命周期管理

**Spring Bean 注册方式**：
所有业务 Agent 通过 `@Service` 注解注册为 Spring Bean，继承 `BaseAgent` 基类。Spring 容器在启动时自动扫描并实例化：

```java
@Service
public class ResumeMatchingAgent extends BaseAgent {
    
    @Autowired
    private ResumeMapper resumeMapper;
    
    @Autowired
    private EmbeddingService embeddingService;
    
    @Autowired
    private AgentCompletionCallback agentCallback;
    
    @PostConstruct
    @Override
    public void init() {
        this.agentName = "ResumeMatchingAgent";
        // 初始化时从 Vault 加载 API 凭证
        // 订阅 RabbitMQ 简历入库队列
    }
}
```

**Bean 生命周期阶段**：

| 阶段 | 时机 | 操作 |
|------|------|------|
| 实例化 | Spring 容器启动 | 通过 `@Service` 注解自动创建 Agent Bean 实例 |
| 依赖注入 | 实例化后 | `@Autowired` 注入 Service、Mapper、外部客户端等依赖 |
| 初始化 | `@PostConstruct` | 从 Vault 加载凭证、订阅消息队列、初始化工具集 |
| 运行中 | 接收任务 | 通过 RabbitMQ/Spring Event 触发 `execute()` 方法 |
| 销毁 | 应用关闭 | `@PreDestroy` 取消订阅、释放资源、刷新日志 |

**依赖注入管理**：
- Agent 继承 `BaseAgent` 获得通用组件（Logger、MessageProducer、GuardrailExecutor、RetryPolicy）
- 业务 Agent 通过 `@Autowired` 注入模块特定的 Service/Mapper
- 外部服务客户端（LLM、OCR、RPA）通过构造函数注入或 `@Autowired` 注入
- 配置属性通过 `@Value` 或 `@ConfigurationProperties` 注入

**Agent 初始化时序**：
```
Spring Boot 启动
    ↓
扫描 @Service 注解 → 创建 Agent Bean 实例
    ↓
@Autowired 注入依赖（Service、Mapper、外部客户端）
    ↓
@PostConstruct 执行初始化
    ├── 从 Vault 加载 API 凭证
    ├── 订阅 RabbitMQ 队列
    ├── 注册工具集（@Tool 注解扫描）
    └── 设置 agentName
    ↓
应用就绪，等待任务触发
```

> **设计说明**：
> - Agent 作为 Spring Bean 管理，享受容器化的生命周期管理、依赖注入、AOP 切面等能力
> - 每个 Agent 是单例 Bean（Spring 默认），通过线程安全的上下文对象（`AgentContext`）隔离并发执行
> - Agent 不直接操作数据库，通过注入的 Service 完成数据读写，保持职责分离
> - 外部服务调用（LLM、OCR、RPA）通过专用客户端封装，支持熔断、超时、降级等弹性容错

### 7.2 Agent 执行日志

```java
@Entity
@Table(name = "agent_run_log")
public class AgentRunLog {
    @Id
    private String runId;              // UUID
    private String agentName;          // Agent 名称
    private String parentFlowId;       // 所属流程 ID
    private JsonNode inputsSummary;    // 输入概要
    private String reasoningTrace;     // 推理过程
    private JsonNode outputsSummary;   // 输出概要
    private String status;             // SUCCESS/FAILED/SUSPENDED
    private Long durationMs;           // 耗时
    private String errorDetail;        // 错误详情
    private LocalDateTime createdAt;   // 执行时间
}
```

### 7.3 安全护栏实现

```java
public class AmountGuardrail implements Guardrail {
    
    @Override
    public void check(Decision decision) throws GuardrailException {
        // 检查是否涉及金额变动
        if (decision.involvesAmountChange()) {
            // 检查是否有 HR 审核批准
            if (!decision.hasApproval(HR_APPROVAL)) {
                throw new GuardrailException(
                    "金额变动需要人事专员审核批准"
                );
            }
            // 检查金额合理性
            BigDecimal amount = decision.getAmount();
            if (amount.compareTo(BigDecimal.ZERO) < 0) {
                throw new GuardrailException("金额不能为负数");
            }
        }
    }
}

public class ReasoningGuardrail implements Guardrail {
    
    @Override
    public void check(Decision decision) throws GuardrailException {
        // 评分范围检查
        if (decision.isScoringResult()) {
            int score = decision.getScore();
            if (score < 0 || score > 100) {
                throw new GuardrailException(
                    String.format("评分 %d 超出 [0,100] 范围", score)
                );
            }
        }
        // 薪资非零检查
        if (decision.isPayrollResult()) {
            BigDecimal salary = decision.getSalary();
            if (salary.compareTo(BigDecimal.ZERO) == 0) {
                throw new GuardrailException("薪资不能为零");
            }
        }
    }
}
```

---

## 8. RPA 引擎设计

> **架构决策**：RPA 引擎作为独立的 Python 子服务运行，通过 HTTP API 与 Java 主服务通信。Playwright 在 Python 生态中比 Java 更成熟，社区资源丰富，版本迭代快。浏览器进程与 API 服务进程隔离，避免资源竞争。
>
> Python 子服务的部署方案详见 1.5 节。

### 8.1 RPA 子服务通信

Java 主服务通过 HTTP REST API 调用 Python RPA 子服务：

```java
@Service
public class RPAService {
    
    private final WebClient webClient;
    private final ObjectMapper objectMapper;
    
    @Value("${rpa.service.url:http://localhost:8090}")
    private String rpaServiceUrl;
    
    public RPAService(WebClient.Builder webClientBuilder, ObjectMapper objectMapper) {
        this.webClient = webClientBuilder
            .baseUrl(rpaServiceUrl)
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .codecs(configurer -> configurer.defaultCodecs().maxInMemorySize(10 * 1024 * 1024))
            .build();
        this.objectMapper = objectMapper;
    }
    
    /**
     * 提交 RPA 任务到 Python 子服务
     * 
     * 熔断器配置（Resilience4j）：
     * - 滑动窗口：100 个样本
     * - 失败率 > 50% 触发熔断
     * - 熔断后等待 30s 进入半开状态
     * - 半开状态下单次成功即恢复
     */
    @CircuitBreaker(name = "rpaService", 
        failureRateThreshold = 50, 
        slidingWindowSize = 100,
        waitDurationInOpenState = 30000)
    @TimeLimiter(name = "rpaService")
    public CompletableFuture<RPAResult> executeAsync(RPATask task) {
        RPARequest request = RPARequest.builder()
            .taskId(task.getTaskId())
            .targetSystem(task.getTargetSystem())
            .targetUrl(task.getTargetUrl())
            .credentials(task.getCredentials())
            .actions(task.getActions())
            .timeoutSeconds(task.getTimeoutSeconds())
            .build();
        
        return webClient.post()
            .uri("/api/v1/rpa/execute")
            .bodyValue(request)
            .retrieve()
            .bodyToMono(RPAResult.class)
            .timeout(Duration.ofMillis(120000))
            .onErrorMap(ResourceExhaustedException.class, 
                e -> new RPAServiceTimeoutException("RPA 子服务调用超时: taskId=" + task.getTaskId(), e))
            .onErrorMap(WebClientRequestException.class, 
                e -> new RPAServiceUnavailableException("RPA 服务不可用: taskId=" + task.getTaskId(), e))
            .toFuture();
    }
    
    /**
     * 同步调用（内部转为异步+等待）
     */
    public RPAResult execute(RPATask task) {
        try {
            return executeAsync(task).get(120, TimeUnit.SECONDS);
        } catch (TimeoutException e) {
            log.error("RPA 子服务调用超时: taskId={}", task.getTaskId(), e);
            return RPAResult.degraded("RPA 服务超时，请人工处理");
        } catch (InterruptedException | ExecutionException e) {
            log.error("RPA 子服务调用失败: taskId={}", task.getTaskId(), e);
            return RPAResult.degraded("RPA 服务不可用，请人工处理");
        }
    }
    
    /**
     * RPA 不可用时的降级方法
     */
    public RPAResult fallback(RPATask task, Exception e) {
        log.warn("RPA 降级处理: taskId={}, 原因={}", task.getTaskId(), e.getMessage());
        return RPAResult.degraded("RPA 服务不可用，已触发降级，请人工处理");
    }
    
    /**
     * 查询 RPA 任务状态
     */
    @CircuitBreaker(name = "rpaService", 
        failureRateThreshold = 50, 
        slidingWindowSize = 100,
        waitDurationInOpenState = 30000)
    public Mono<RPAStatus> getStatus(String taskId) {
        return webClient.get()
            .uri("/api/v1/rpa/status/{taskId}", taskId)
            .retrieve()
            .bodyToMono(RPAStatus.class)
            .timeout(Duration.ofSeconds(10))
            .onErrorResume(e -> {
                log.error("RPA 状态查询失败: taskId={}", taskId, e);
                return Mono.just(RPAStatus.unknown("RPA 服务不可用"));
            });
    }
}
```

> **Resilience4j 配置类**：
```java
@Configuration
public class Resilience4jConfig {
    
    @Bean
    public CircuitBreakerRegistry circuitBreakerRegistry() {
        CircuitBreakerConfig config = CircuitBreakerConfig.custom()
            .slidingWindowSize(100)
            .failureRateThreshold(50)
            .waitDurationInOpenState(Duration.ofSeconds(30))
            .permittedNumberOfCallsInHalfOpenState(1)
            .automaticTransitionFromOpenToHalfOpenEnabled(true)
            .build();
        
        return CircuitBreakerRegistry.of(config);
    }
    
    @Bean
    public TimeLimiterRegistry timeLimiterRegistry() {
        TimeLimiterConfig config = TimeLimiterConfig.custom()
            .timeoutDuration(Duration.ofMinutes(2))
            .cancelRunningFuture(true)
            .build();
        
        return TimeLimiterRegistry.of(config);
    }
}
```

> **WebClient 选型说明**：Spring Boot 3.x 中 `RestTemplate` 已标记为 legacy，推荐使用 `WebClient`（基于 Project Reactor，支持非阻塞 I/O 和响应式编程）。配合 Resilience4j 实现熔断、超时、限流等弹性容错能力。Resilience4j 依赖：`resilience4j-spring-boot3` + `resilience4j-reactor`。

### 8.2 RPA 任务定义

```java
public class RPATask {
    private String taskId;             // 任务 ID
    private String targetSystem;       // 目标系统 (社保/公积金)
    private String targetUrl;          // 目标 URL
    private Credentials credentials;   // 登录凭证 (加密)
    private List<RPAAction> actions;   // 操作序列
    private int timeoutSeconds;        // 超时时间
    private int maxRetries;            // 最大重试次数
}

public class RPAAction {
    private ActionType type;           // CLICK/TYPE/SELECT/UPLOAD/WAIT/SCROLL
    private String selector;           // CSS 选择器
    private String value;              // 输入值
    private String file;               // 上传文件路径
    private int timeout;               // 等待时间
    private int scrollAmount;          // 滚动距离
}
```

### 8.3 RPA 自适应检测

```java
@Component
public class RPAAdaptationService {
    
    /**
     * 每周验证 RPA 流程可用性
     * 由 XXL-JOB 调度，对应 Job Handler: RPAValidationJob
     * 已废弃 @Scheduled 注解，统一使用 XXL-JOB 管理
     */
    @XxlJob("RPAValidationJob")
    public ReturnT<String> validateRPAFlows(String param) {
        XxlJobHelper.log("开始执行 RPA 流程验证...");
        
        for (RPAFlow flow : rpaFlowRepository.findAll()) {
            ValidationResult result = dryRun(flow);
            
            if (!result.isAdaptable()) {
                alertService.sendAlert(
                    String.format("RPA 流程 '%s' 检测到页面变化", flow.getName()),
                    AlertLevel.WARNING,
                    result.getChanges()
                );
            }
            
            if (flow.getFailureRate() > 0.05) {
                alertService.sendAlert(
                    String.format("RPA 流程 '%s' 失败率 %.1f%%，需要重新配置",
                        flow.getName(), flow.getFailureRate() * 100),
                    AlertLevel.CRITICAL
                );
            }
        }
        
        return ReturnT.SUCCESS;
    }
}
```

> **定时任务统一说明**：所有定时任务统一由 XXL-JOB 调度管理（详见 5.4 节），不再使用 Spring `@Scheduled` 注解，避免维护两套调度体系。XXL-JOB 提供任务分片、失败重试、执行日志等能力。

#### 8.3.1 XXL-JOB 执行器配置

```java
@Configuration
public class XxlJobConfig {

    @Value("${xxl.job.admin.addresses}")
    private String adminAddresses;

    @Value("${xxl.job.accessToken}")
    private String accessToken;

    @Value("${xxl.job.executor.appname}")
    private String appname;

    @Value("${xxl.job.executor.address}")
    private String address;

    @Value("${xxl.job.executor.ip}")
    private String ip;

    @Value("${xxl.job.executor.port:9999}")
    private int port;

    @Value("${xxl.job.executor.logpath}")
    private String logPath;

    @Value("${xxl.job.executor.logretentiondays:30}")
    private int logRetentionDays;

    @Bean
    public XxlJobSpringExecutor xxlJobExecutor() {
        XxlJobSpringExecutor executor = new XxlJobSpringExecutor();
        executor.setAdminAddresses(adminAddresses);
        executor.setAccessToken(accessToken);
        executor.setAppname(appname);
        executor.setAddress(address);
        executor.setIp(ip);
        executor.setPort(port);
        executor.setLogPath(logPath);
        executor.setLogRetentionDays(logRetentionDays);
        return executor;
    }
}
```

> **XXL-JOB 配置说明**：
> - 上述配置类为 XXL-JOB 执行器必需 Bean，缺少则 `@XxlJob` 注解无法生效
> - 配置项通过 Nacos 配置中心管理，支持热更新
> - `accessToken` 需与 XXL-JOB 调度中心保持一致，确保任务调用安全
> - `logretentiondays` 设置为 30 天，满足审计追溯需求

#### 8.3.2 application.yml 配置示例

```yaml
# XXL-JOB 执行器配置
xxl:
  job:
    admin:
      addresses: http://xxl-job-admin:8080/xxl-job-admin
    accessToken: default_token  # 与调度中心保持一致
    executor:
      appname: gbm-hr-executor
      address:                   # 留空自动注册
      ip:                        # 留空自动获取
      port: 9999
      logpath: /data/applogs/xxl-job/jobhandler
      logretentiondays: 30
```

---

## 9. 错误处理与异常管理

### 9.1 异常分类

| 异常类 | 父类 | HTTP 状态码 | 说明 |
|--------|------|------------|------|
| BusinessException | RuntimeException | 400 | 业务逻辑异常 |
| ValidationException | BusinessException | 400 | 参数校验失败 |
| AuthenticationException | RuntimeException | 401 | 认证失败 |
| AuthorizationException | RuntimeException | 403 | 权限不足 |
| ResourceNotFoundException | BusinessException | 404 | 资源不存在 |
| RateLimitException | BusinessException | 429 | 请求频率限制 |
| AgentExecutionException | RuntimeException | 500 | Agent 执行失败 |
| RPAException | AgentExecutionException | 500 | RPA 操作失败 |
| ExternalAPIException | AgentExecutionException | 502 | 外部 API 失败 |
| DataConsistencyException | RuntimeException | 500 | 数据一致性异常 |

### 9.2 全局异常处理器

```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    
    @ExceptionHandler(BusinessException.class)
    public Result<Void> handleBusinessException(BusinessException e) {
        log.warn("Business exception: {}", e.getMessage());
        return Result.error(400, e.getMessage());
    }
    
    @ExceptionHandler(AuthenticationException.class)
    public Result<Void> handleAuthException(AuthenticationException e) {
        log.warn("Authentication failed: {}", e.getMessage());
        return Result.error(401, e.getMessage());
    }
    
    @ExceptionHandler(AuthorizationException.class)
    public Result<Void> handleAuthorizationException(AuthorizationException e) {
        log.warn("Authorization denied: {}", e.getMessage());
        return Result.error(403, e.getMessage());
    }
    
    @ExceptionHandler(AgentExecutionException.class)
    public Result<Void> handleAgentException(AgentExecutionException e) {
        log.error("Agent execution failed", e);
        // 触发告警
        alertService.sendAgentAlert(e);
        return Result.error(500, "Agent 执行失败，已自动记录并告警");
    }
    
    @ExceptionHandler(Exception.class)
    public Result<Void> handleUnexpectedException(Exception e) {
        log.error("Unexpected error", e);
        return Result.error(500, "系统内部错误");
    }
}
```

### 9.3 分级异常处理

```
Agent 执行异常
    ↓
异常分级:
    ├── 低级别 (可自动恢复)
    │   └── 自动重试 (指数退避，最多 3 次)
    │       └── 成功 → 继续
    │       └── 失败 → 升级为中级别
    │
    ├── 中级别 (需人工审核)
    │   └── 标记为"待人工处理"
    │   └── 生成故障摘要 (Error Report)
    │   └── 通知相关人员 (下一工作日)
    │
    └── 高级别 (需立即处理)
        └── 立即告警 (电话/短信，5 分钟内)
        └── 暂停相关 Agent
        └── 15 分钟无人确认 → 升级通知部门负责人
```

---

## 10. 性能优化策略

### 10.1 数据库优化

| 优化手段 | 实施方式 |
|---------|---------|
| 索引优化 | 为高频查询字段建立索引 (employee_id, date, status 等) |
| 分页查询 | 使用 MyBatis-Plus 分页插件，避免全表扫描 |
| 读写分离 | MySQL 主从复制，读操作走从库 |
| 连接池 | HikariCP 连接池，最大连接数 50 |
| SQL 优化 | 避免 N+1 查询，使用 JOIN 或批量查询 |
| 缓存热点数据 | Redis 缓存薪资规则、岗位信息等热点数据 |

### 10.2 API 性能优化

| 优化手段 | 实施方式 |
|---------|---------|
| 响应压缩 | GZIP 压缩响应体 |
| 分页限制 | 默认 20 条/页，最大 100 条/页 |
| 字段过滤 | 支持 SELECT 字段过滤，减少数据传输 |
| 批量操作 | 支持批量导入/导出/更新 |
| 异步处理 | 长时间操作 (薪资核算、RPA) 采用异步 + 回调 |
| CDN  | 静态资源走 CDN |

### 10.3 Agent 性能优化

| 优化手段 | 实施方式 |
|---------|---------|
| LLM 缓存 | 相同输入的 LLM 请求结果缓存 (Redis) |
| 批量请求 | 批量简历评分使用 LLM Batch API |
| 并行处理 | Fan-Out 模式并行拉取数据 |
| 流式响应 | LLM 流式输出，减少等待时间 |
| 模型选择 | 简单任务用小模型，复杂任务用大模型 |
| 预计算 | 常用评分/规则提前计算并缓存 |

### 10.4 性能指标

| 指标 | 目标值 | 监控方式 |
|------|--------|---------|
| API P95 响应时间 | ≤ 3s | Prometheus + Grafana |
| Agent 执行成功率 | ≥ 95% | 自定义指标 |
| 数据库查询 P95 | ≤ 200ms | Slow Query Log |
| 缓存命中率 | ≥ 90% | Redis INFO stats |
| Redis Stream 消费延迟 | ≤ 5s | Redis Stream Pending |
| 系统 CPU 使用率 | ≤ 85% (5min) | Prometheus |
| 系统内存使用率 | ≤ 90% (5min) | Prometheus |

---

*文档结束*
