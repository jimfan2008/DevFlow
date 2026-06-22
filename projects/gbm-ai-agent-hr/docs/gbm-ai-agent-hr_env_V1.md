# GBM AI Agent HR - Development Environment Configuration V1

## Project Overview

- **Project Name**: GBM AI Agent HR 智能人力管理系统
- **Version**: 1.0.0
- **Description**: AI-Native HR Management System with Zero Operational Principle
- **Repository**: Local Git Repository
- **Last Updated**: 2026-06-22
- **Based on**: SRS V15.0, ARCHITECTURE V24, BACKEND V35, FRONTEND V26, DATABASE V19

---

## 1. Technology Stack

### 1.1 Backend Services (Java 17 + Spring Boot 3.2.x)

| Component | Selection | Version | Description |
|-----------|-----------|---------|-------------|
| Language | Java | 17 LTS | Enterprise stability |
| Framework | Spring Boot | 3.2.x | Enterprise application framework |
| ORM | MyBatis-Plus | 3.5.x | Flexible SQL control |
| API Docs | SpringDoc OpenAPI | 2.x | Auto-generated API docs |
| Auth | Keycloak SSO | 22.x | OAuth 2.0 + JWT |
| Message Queue | Kafka | 3.x | 3-node cluster, at-least-once delivery |
| Process Engine | Camunda 8 (Zeebe) | 8.x | BPMN 2.0 orchestration |
| Cache | Redis | 7.x | Redisson client |
| Config | application.yml + Spring Profile | - | Per-environment config |
| Tracing | OpenTelemetry | 1.x | Distributed tracing |
| Resilience | Resilience4j | 2.x | Circuit breaker, rate limiting |
| Monitoring | Prometheus + Grafana | - | Metrics & visualization |

### 1.2 Domain Services (4 Independent Services)

| Domain Service | Port | Responsibility | Database Schema |
|---------------|------|---------------|-----------------|
| user-domain | 8081 | User center, auth, org structure, permissions | hr_user |
| recruit-domain | 8082 | Recruitment, onboarding, training | hr_recruit |
| payroll-domain | 8083 | Attendance, payroll, performance | hr_payroll |
| auto-domain | 8084 | Analytics, RPA/OCR/Face, external affairs | hr_auto |

### 1.3 Frontend

| Component | Selection | Version |
|-----------|-----------|---------|
| Framework | Vue | 3.4.x |
| UI Library | Element Plus | 2.x |
| State Management | Pinia | 2.1.x |
| Server State | @tanstack/vue-query | 5.x |
| Router | Vue Router | 4.x |
| i18n | vue-i18n | 9.x |
| HTTP Client | Axios | 1.x |
| Build Tool | Vite | 5.x |
| Charts | ECharts | 5.x |
| Mobile | UniApp | 3.0.x |

### 1.4 Python Sub-Services

| Service | Port | Framework | Technology |
|---------|------|-----------|------------|
| RPA Service | 8090 | FastAPI | Playwright |
| OCR Service | 8091 | FastAPI | PaddleOCR |
| Face Service | 8092 | FastAPI | InsightFace 0.3.x |

### 1.5 Infrastructure

| Component | Selection | Version | Purpose |
|-----------|-----------|---------|---------|
| Database | MySQL | 8.0 | 4 schemas (hr_user/hr_recruit/hr_payroll/hr_auto) |
| Cache | Redis | 7.x | Session, hot data, agent locks |
| Message Queue | Kafka | 3.x + Zookeeper | 3-node cluster for event bus |
| Object Storage | MinIO | - | Files, images, videos |
| Auth | Keycloak | 22.x | SSO, OAuth 2.0, JWT |
| Process Engine | Camunda 8 | 8.x | BPMN workflow orchestration |
| Gateway | Nginx Ingress | - | SSL termination, routing, static resources |
| Vector DB | Milvus | 2.4.x | Resume embedding, semantic search |
| Container | Docker | 24.x | Docker Compose for dev |
| CI/CD | GitHub Actions | - | Build, test, deploy |

---

## 2. Project Structure

```
gbm-ai-agent-hr/
├── backend/                              # Multi-module Maven project
│   ├── pom.xml                           # Parent POM
│   ├── common/                           # Common module
│   │   ├── pom.xml
│   │   └── src/main/java/com/gbm/hr/common/
│   │       ├── config/                   # MyBatis-Plus, OpenAPI config
│   │       ├── dto/                      # Result, PageRequest, PageResult
│   │       ├── exception/                # Global exception handler
│   │       └── util/                     # Utility classes
│   ├── user-domain/                      # User center domain (:8081)
│   │   ├── pom.xml
│   │   └── src/main/java/com/gbm/hr/user/
│   │       ├── UserDomainApplication.java
│   │       ├── controller/
│   │       ├── service/
│   │       ├── repository/
│   │       ├── model/
│   │       ├── config/
│   │       └── security/
│   ├── recruit-domain/                   # Recruitment domain (:8082)
│   │   ├── pom.xml
│   │   └── src/main/java/com/gbm/hr/recruit/
│   │       ├── RecruitDomainApplication.java
│   │       ├── controller/
│   │       ├── service/
│   │       ├── repository/
│   │       ├── model/
│   │       ├── config/
│   │       └── workflow/                 # Camunda BPMN definitions
│   ├── payroll-domain/                   # Payroll domain (:8083)
│   │   ├── pom.xml
│   │   └── src/main/java/com/gbm/hr/payroll/
│   │       ├── PayrollDomainApplication.java
│   │       ├── controller/
│   │       ├── service/
│   │       ├── repository/
│   │       ├── model/
│   │       ├── config/
│   │       └── workflow/                 # Camunda BPMN definitions
│   ├── auto-domain/                      # Automation domain (:8084)
│   │   ├── pom.xml
│   │   └── src/main/java/com/gbm/hr/auto/
│   │       ├── AutoDomainApplication.java
│   │       ├── controller/
│   │       ├── service/
│   │       ├── repository/
│   │       ├── model/
│   │       ├── config/
│   │       └── rpa/                      # RPA/OCR/Face service calls
│   ├── Dockerfile.user-domain
│   ├── Dockerfile.recruit-domain
│   ├── Dockerfile.payroll-domain
│   └── Dockerfile.auto-domain
├── frontend/                             # Vue 3 frontend
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── api/                          # API service layer
│       ├── components/                   # Reusable components
│       ├── composables/                  # Vue composables
│       ├── pages/                        # Page components
│       ├── router/                       # Vue Router config
│       ├── stores/                       # Pinia stores
│       ├── types/                        # TypeScript types
│       └── utils/                        # Utility functions
├── sub-services/                         # Python sub-services
│   ├── rpa-service/                      # RPA (:8090)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/main.py
│   ├── ocr-service/                      # OCR (:8091)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/main.py
│   └── face-service/                     # Face recognition (:8092)
│       ├── Dockerfile
│       ├── requirements.txt
│       └── src/main.py
├── docker/                               # Docker configurations
│   ├── nginx/nginx.conf                  # Nginx ingress config
│   ├── keycloak/                         # Keycloak realm config
│   └── kafka/                            # Kafka topic config
├── database/                             # Database scripts
│   ├── init/
│   │   └── 001_init.sql                  # Schema + base data init
│   └── migrations/                       # Alembic migration scripts
├── .github/workflows/                    # CI/CD pipelines
│   ├── backend-ci.yml                    # Backend build & test
│   └── frontend-ci.yml                   # Frontend build & test
├── docker-compose.yml                    # Dev environment orchestration
├── .env.example                          # Environment variables template
├── .gitignore
└── docs/                                 # Documentation
    ├── gbm-ai-agent-hr_SRS_V15.md
    ├── gbm-ai-agent-hr_ARCHITECTURE_V24.md
    ├── gbm-ai-agent-hr_BACKEND_V35.md
    ├── gbm-ai-agent-hr_FRONTEND_V26.md
    ├── gbm-ai-agent-hr_DATABASE_V19.md
    └── gbm-ai-agent-hr_env_V1.md        # This document
```

---

## 3. Environment Variables

Copy `.env.example` to `.env` and update values:

```env
# ==================== Database ====================
MYSQL_ROOT_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=3306
DB_USERNAME=root
DB_PASSWORD=your_secure_password

# ==================== Redis ====================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# ==================== Kafka ====================
KAFKA_BROKERS=localhost:9092

# ==================== Keycloak ====================
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=your_secure_password
KEYCLOAK_URL=http://localhost:8080

# ==================== MinIO ====================
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=your_secure_password
MINIO_ENDPOINT=localhost:9000
MINIO_BUCKET=hr-files

# ==================== RabbitMQ (for RPA fallback) ====================
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=guest
RABBITMQ_PASSWORD=guest

# ==================== Python Sub-Services ====================
RPA_SERVICE_HOST=localhost
RPA_SERVICE_PORT=8090
OCR_SERVICE_HOST=localhost
OCR_SERVICE_PORT=8091
FACE_SERVICE_HOST=localhost
FACE_SERVICE_PORT=8092

# ==================== AI Models ====================
LLM_ENDPOINT=http://localhost:8000
LLM_MODEL=qwen-7b
EMBEDDING_ENDPOINT=http://localhost:8001
EMBEDDING_MODEL=bge-m3

# ==================== JWT ====================
JWT_SECRET=your_jwt_secret_key_32_bytes_min
JWT_EXPIRATION=86400

# ==================== Email ====================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_email_password

# ==================== Monitoring ====================
PROMETHEUS_ENDPOINT=http://localhost:9090
GRAFANA_ENDPOINT=http://localhost:3000

# ==================== Encryption ====================
ENCRYPTION_KEY=your_32_byte_base64_encryption_key_here

# ==================== Camunda ====================
CAMUNDA_REST_URL=http://localhost:8080
CAMUNDA_BASIC_AUTH_USER=camunda
CAMUNDA_BASIC_AUTH_PASSWORD=camunda
```

---

## 4. Development Environment Setup

### 4.1 Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| JDK | 17+ (Temurin) | Backend compilation |
| Maven | 3.8+ | Java build tool |
| Node.js | 20+ | Frontend build |
| Python | 3.11+ | Sub-services |
| Docker | 24.x | Container runtime |
| Docker Compose | 2.x | Service orchestration |
| Git | 2.30+ | Version control |

### 4.2 Hardware Requirements

- **CPU**: 8+ cores
- **RAM**: 32GB+ minimum (64GB recommended)
- **Storage**: 500GB+ SSD
- **GPU**: NVIDIA GPU with 8GB+ VRAM (for local LLM inference, optional)

### 4.3 Start Development Environment

```bash
# 1. Clone repository
cd /home/jim/DevFlow/projects/gbm-ai-agent-hr

# 2. Copy environment variables
cp .env.example .env
# Edit .env with actual values

# 3. Start infrastructure services
docker-compose up -d mysql redis kafka zookeeper minio elasticsearch milvus keycloak rabbitmq

# 4. Wait for services to be healthy
docker-compose ps

# 5. Build and start domain services
cd backend && mvn clean package -DskipTests
cd ..
docker-compose up -d user-domain recruit-domain payroll-domain auto-domain

# 6. Start Python sub-services
docker-compose up -d rpa-service ocr-service face-service

# 7. Start frontend dev server
cd frontend
npm install
npm run dev

# 8. Start Nginx gateway
docker-compose up -d nginx
```

### 4.4 Access Points

| Service | URL | Port |
|---------|-----|------|
| Frontend | http://localhost:3000 | 3000 |
| Nginx Gateway | http://localhost / https://localhost | 80/443 |
| user-domain API | http://localhost:8081 | 8081 |
| recruit-domain API | http://localhost:8082 | 8082 |
| payroll-domain API | http://localhost:8083 | 8083 |
| auto-domain API | http://localhost:8084 | 8084 |
| RPA Service | http://localhost:8090 | 8090 |
| OCR Service | http://localhost:8091 | 8091 |
| Face Service | http://localhost:8092 | 8092 |
| Keycloak Admin | http://localhost:8080 | 8080 |
| MinIO Console | http://localhost:9001 | 9001 |
| Prometheus | http://localhost:9090 | 9090 |
| Grafana | http://localhost:3000 | 3000 |
| MySQL | localhost:3306 | 3306 |
| Redis | localhost:6379 | 6379 |
| Kafka | localhost:9092 | 9092 |

---

## 5. CI/CD Pipeline

### 5.1 Backend Pipeline (.github/workflows/backend-ci.yml)

| Stage | Tool | Content | Gate Condition |
|-------|------|---------|---------------|
| Code Check | Checkstyle + SpotBugs | Code norm scan, bug detection | No blocker/critical issues |
| Unit Test | JUnit 5 + JaCoCo | Run all unit tests | Coverage >= 70%, no failures |
| Integration Test | Testcontainers | MySQL + Redis integration tests | All pass |
| Dependency Scan | OWASP Dependency-Check | CVE vulnerability scan | No critical/high vulnerabilities |
| Image Build | Docker + BuildKit | Build Java + Python images | Build success |
| Image Scan | Trivy | Image vulnerability scan | No critical vulnerabilities |
| Deploy Dev | Docker Compose | Rolling update to dev | Health check passed |
| Deploy Prod | Manual approval | Production deployment | QA + tech lead approval |

### 5.2 Frontend Pipeline (.github/workflows/frontend-ci.yml)

| Stage | Tool | Content |
|-------|------|---------|
| Install | npm ci | Install dependencies |
| Lint | ESLint | Code quality check |
| Type Check | vue-tsc | TypeScript type verification |
| Unit Test | Vitest | Component unit tests |
| Accessibility | aXe | WCAG 2.1 AA compliance |
| Build | Vite | Production build |
| Deploy | Manual | Deploy to target environment |

### 5.3 Build Matrix

The CI builds all 7 services in parallel:

- user-domain, recruit-domain, payroll-domain, auto-domain (Java)
- rpa-service, ocr-service, face-service (Python)

---

## 6. Database Initialization

### 6.1 Schema Architecture

| Schema | Tables | Domain Service | Description |
|--------|--------|---------------|-------------|
| hr_user | department, job_position, sys_user, sys_role, sys_permission, sys_user_role, sys_role_permission, audit_log | user-domain | User center, auth, org structure |
| hr_recruit | recruitment_job, resume, exam_paper, onboarding_process, Camunda 8 tables | recruit-domain | Recruitment, onboarding, training |
| hr_payroll | attendance_record, payroll, performance_review | payroll-domain | Attendance, payroll, performance |
| hr_auto | agent_run_log, rpa_task, injury_case | auto-domain | Automation tasks, external affairs |

### 6.2 Initialization

```bash
# Database scripts are mounted to /docker-entrypoint-initdb.d
# They run automatically when MySQL container starts for the first time

# Manual initialization (if needed):
mysql -h localhost -u root -p < database/init/001_init.sql
```

### 6.3 Initial Data

| Entity | Initial Records |
|--------|----------------|
| Departments | 5 (总经办, 人力资源部, 财务部, 信息技术部, 生产管理部) |
| Roles | 6 (超级管理员, 系统管理员, 人事主管, 人事专员, 部门主管, 普通员工) |
| Admin User | 1 (username: admin, password: Admin@123, BCrypt hashed) |

---

## 7. Security Configuration

### 7.1 Encryption

- **Sensitive data**: AES-256-GCM encryption for ID numbers, face features, salary data
- **Password hashing**: BCrypt with 10 rounds
- **TLS**: TLS 1.2+ for all network communications
- **Key management**: ENCRYPTION_KEY stored in .env file

### 7.2 Authentication

- **SSO**: Keycloak 22.x with OAuth 2.0 + JWT
- **MFA**: Required for admin login, salary data access, bulk export
- **Session**: HTTP-Only cookies, no token in localStorage
- **API auth**: Keycloak JWT validation via Spring Security filter

### 7.3 Authorization

- **RBAC**: Role-based access control with 6 predefined roles
- **Row-level isolation**: Department managers can only see their department data
- **Audit logging**: All operations logged with before/after snapshots (10-year retention)

---

## 8. Nginx Gateway Configuration

### 8.1 Route Mapping

| Path Prefix | Domain Service | Port | Description |
|-------------|---------------|------|-------------|
| /api/v1/user/** | user-domain | 8081 | User center API |
| /api/v1/recruit/** | recruit-domain | 8082 | Recruitment API |
| /api/v1/onboarding/** | recruit-domain | 8082 | Onboarding API |
| /api/v1/payroll/** | payroll-domain | 8083 | Payroll API |
| /api/v1/auto/** | auto-domain | 8084 | Automation API |
| /api/v1/ocr/** | ocr-service | 8091 | OCR service |
| /api/v1/face/** | face-service | 8092 | Face service |
| /api/v1/rpa/** | rpa-service | 8090 | RPA service |
| /ws/** | All domains | 8081-8084 | WebSocket connections |
| /actuator/** | All domains | 8081-8084 | Health check endpoints |
| /auth/** | keycloak | 8080 | Keycloak SSO |

### 8.2 Security Headers

- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block
- Content-Security-Policy: Strict policy
- Referrer-Policy: strict-origin-when-cross-origin

### 8.3 Rate Limiting

- API: 100 requests/second per IP (burst 20)
- Login: 5 requests/minute per IP (burst 3)

---

## 9. Deployment Strategies

| Environment | Strategy | Trigger | Description |
|------------|----------|---------|-------------|
| Dev | Auto deploy | Every main branch merge | Quick verification |
| Test | Auto deploy | After dev passes | Integration testing |
| Staging | Manual approval | After test passes, QA approval | Pre-production validation |
| Production | Manual + canary | After staging passes, tech lead approval | Rolling update, 1/3 at a time |

### 9.1 Rollback Plan

- **Auto rollback**: Health check failure or smoke test failure triggers automatic rollback
- **Manual rollback**: One-click rollback to previous stable version
- **Image retention**: Last 20 versions kept in Harbor registry
- **Database rollback**: Alembic migration scripts support forward/rollback operations

---

## 10. Monitoring & Observability

### 10.1 Metrics

| Metric | Alert Threshold | Source |
|--------|----------------|--------|
| CPU utilization | > 85% for 5 min | Prometheus |
| Memory utilization | > 90% for 5 min | Prometheus |
| Disk space | > 80% | Prometheus |
| DB connection pool | > 80% | Prometheus |
| API response P95 | > 5s | Prometheus |
| Agent success rate | < 95% | Custom metrics |
| Resume backlog | > 500 | Custom metrics |

### 10.2 Alerting

| Level | Notification | Response Time |
|-------|-------------|---------------|
| Critical | Phone/SMS within 5 min | 15 min auto-escalation |
| Major | Email/SMS within 30 min | Same day |
| Minor | Next workday notification | As scheduled |

---

## 11. Quick Start Commands

```bash
# Full environment startup
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f user-domain

# Rebuild a specific service
docker-compose up -d --build user-domain

# Run backend tests
cd backend && mvn test

# Run frontend dev server
cd frontend && npm run dev

# Database backup
mysqldump -h localhost -u root -p --all-databases > backup.sql

# Reset environment (WARNING: destroys all data)
docker-compose down -v
docker-compose up -d
```

---

*Document End*
*Version: V1.0*
*Author: HouFu (后富) - CI/CD Engineer*
*Date: 2026-06-22*
