# GBM AI Agent HR - 开发环境配置文档 V2

## 版本信息

| 字段 | 值 |
|------|-----|
| 文档名称 | GBM AI Agent HR 开发环境配置 |
| 版本号 | V2.0 |
| 基于 SRS | V15.0 |
| 基于架构文档 | ARCHITECTURE_V24 |
| 基于后端设计 | BACKEND_V35 |
| 基于数据库设计 | DATABASE_V19 |
| 基于前端设计 | FRONTEND_V26 |
| 日期 | 2026-06-22 |
| 作者 | 后富 (HouFu) |
| 角色 | CI/CD 工程师 |

---

## 1. 技术栈总览

### 1.1 后端技术栈

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| 语言 | Java | 17 LTS | 企业级稳定性 |
| 框架 | Spring Boot | 3.2.x | 企业级应用框架 |
| ORM | MyBatis-Plus | 3.5.x | 灵活 SQL 控制 |
| API 文档 | SpringDoc OpenAPI | 2.x | 自动生成 API 文档 |
| 认证 | Keycloak SSO | 22.x | 统一身份认证（OAuth 2.0 + JWT） |
| 消息队列 | Kafka | 3.x | 3 节点集群，跨域服务可靠事件传递 |
| 流程引擎 | Camunda 8 (Zeebe) | 8.x | BPMN 2.0 流程编排 |
| 缓存 | Redis | 7.x | Redisson 客户端 |
| 配置中心 | application.yml + Spring Profile | - | 各域服务内部配置管理 |
| 链路追踪 | OpenTelemetry | 1.x | 分布式追踪 |
| 监控 | Prometheus + Grafana | - | 指标采集与可视化 |
| 弹性容错 | Resilience4j | 2.x | 熔断器、限流、超时控制 |
| 定时任务 | Spring @Scheduled + Quartz | - | 各域服务内部调度 |
| WebSocket | Spring WebSocket + STOMP | - | 实时推送 |

### 1.2 域服务划分

| 域服务 | 端口 | 职责 | 数据库 Schema |
|--------|------|------|---------------|
| user-domain | 8081 | 用户中心、认证授权、组织架构、权限管理 | hr_user |
| recruit-domain | 8082 | 招聘管理、入职管理、培训管理 | hr_recruit |
| payroll-domain | 8083 | 考勤管理、薪资管理、绩效管理 | hr_payroll |
| auto-domain | 8084 | 分析自动化、RPA/OCR/人脸共享服务、外务管理 | hr_auto |

### 1.3 Python 子服务

| 子服务 | 端口 | 职责 | 技术栈 |
|--------|------|------|--------|
| RPA 子服务 | 8090 | 浏览器自动化（社保、公积金等政府网站） | Playwright Python |
| OCR 子服务 | 8091 | 证件识别 | PaddleOCR |
| 人脸子服务 | 8092 | 人脸采集、比对、活体检测 | InsightFace 0.3.x |

### 1.4 前端技术栈

| 类别 | 选型 | 版本 |
|------|------|------|
| 框架 | Vue | 3.4.x |
| UI 库 | Element Plus | 2.x |
| 状态管理 | Pinia | 2.1.x |
| 数据请求 | @tanstack/vue-query | 5.x |
| 路由 | Vue Router | 4.x |
| 国际化 | vue-i18n | 9.x |
| 移动端 | UniApp | 3.0.x |
| 构建工具 | Vite | 5.x |

### 1.5 基础设施

| 组件 | 选型 | 版本 | 说明 |
|------|------|------|------|
| 数据库 | MySQL | 8.0 | 主从模式，4 个独立 schema |
| 缓存 | Redis | 7.x | Cluster 模式 |
| 消息队列 | Kafka | 3.x | 3 节点集群 |
| 对象存储 | MinIO | - | 文件、图片、视频存储 |
| 搜索引擎 | Elasticsearch | 8.x | 简历搜索、日志检索 |
| 向量数据库 | Milvus | - | 简历文本向量化检索 |
| 认证中心 | Keycloak | 22.x | SSO 统一认证 |
| 流程引擎 | Camunda 8 | 8.x | BPMN 流程编排 |
| 容器 | Docker | 24.x | 容器化部署 |
| 编排 | Kubernetes | - | 生产环境编排 |
| CI/CD | GitHub Actions | - | 自动化构建与部署 |
| 网关 | K8s Nginx Ingress | - | SSL 终止/路由转发 |

---

## 2. 开发环境要求

### 2.1 硬件要求

| 资源 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 8 核心 | 16 核心 |
| 内存 | 32 GB | 64 GB |
| 存储 | 500 GB SSD | 1 TB NVMe SSD |
| GPU | 无（开发环境） | NVIDIA GPU 8GB+ VRAM（本地 LLM 推理） |

### 2.2 软件要求

| 软件 | 版本 | 用途 |
|------|------|------|
| OS | Ubuntu 22.04 LTS / WSL2 | 开发操作系统 |
| JDK | 17 LTS (Eclipse Temurin) | Java 开发 |
| Maven | 3.8+ | Java 构建工具 |
| Node.js | 18.x LTS | 前端开发 |
| npm | 9.x+ | Node.js 包管理 |
| Python | 3.11+ | Python 子服务开发 |
| Docker | 24.x | 容器化 |
| Docker Compose | 2.20+ | 本地服务编排 |
| Git | 2.30+ | 版本控制 |
| MySQL Client | 8.0+ | 数据库客户端 |
| Redis CLI | 7.x+ | Redis 客户端 |

---

## 3. 代码仓库初始化

### 3.1 仓库结构

```
gbm-ai-agent-hr/
├── .github/
│   └── workflows/
│       ├── backend-ci.yml              # 后端 CI 流水线
│       ├── frontend-ci.yml             # 前端 CI 流水线
│       ├── python-subservice-ci.yml    # Python 子服务 CI 流水线
│       └── deploy.yml                  # 部署流水线
├── backend/
│   ├── user-domain/                    # 用户域服务 (:8081)
│   │   ├── src/main/java/com/gbm/hr/user/
│   │   ├── src/main/resources/
│   │   ├── src/test/java/com/gbm/hr/user/
│   │   ├── Dockerfile
│   │   └── pom.xml
│   ├── recruit-domain/                 # 招聘域服务 (:8082)
│   │   ├── src/main/java/com/gbm/hr/recruit/
│   │   ├── src/main/resources/
│   │   ├── src/test/java/com/gbm/hr/recruit/
│   │   ├── Dockerfile
│   │   └── pom.xml
│   ├── payroll-domain/                 # 薪资域服务 (:8083)
│   │   ├── src/main/java/com/gbm/hr/payroll/
│   │   ├── src/main/resources/
│   │   ├── src/test/java/com/gbm/hr/payroll/
│   │   ├── Dockerfile
│   │   └── pom.xml
│   ├── auto-domain/                    # 自动化域服务 (:8084)
│   │   ├── src/main/java/com/gbm/hr/auto/
│   │   ├── src/main/resources/
│   │   ├── src/test/java/com/gbm/hr/auto/
│   │   ├── Dockerfile
│   │   └── pom.xml
│   ├── common/                         # 公共模块
│   │   ├── src/main/java/com/gbm/hr/common/
│   │   ├── src/main/resources/
│   │   └── pom.xml
│   └── pom.xml                         # 父 POM
├── frontend/
│   ├── web/                            # Web 应用 (Vue 3 + Element Plus)
│   │   ├── src/
│   │   │   ├── views/                  # 页面视图
│   │   │   ├── components/             # 公共组件
│   │   │   ├── stores/                 # Pinia 状态管理
│   │   │   ├── api/                    # API 服务层
│   │   │   ├── router/                 # Vue Router 路由
│   │   │   ├── i18n/                   # 国际化
│   │   │   ├── utils/                  # 工具函数
│   │   │   └── assets/                 # 静态资源
│   │   ├── public/
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   └── vite.config.js
│   └── mobile/                         # 移动端应用 (UniApp)
│       ├── src/
│       ├── Dockerfile
│       └── package.json
├── python-subservices/
│   ├── rpa-service/                    # RPA 子服务 (:8090)
│   │   ├── src/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── main.py
│   ├── ocr-service/                    # OCR 子服务 (:8091)
│   │   ├── src/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── main.py
│   └── face-service/                   # 人脸子服务 (:8092)
│       ├── src/
│       ├── Dockerfile
│       ├── requirements.txt
│       └── main.py
├── database/
│   ├── init/
│   │   ├── hr_user.sql                 # 用户中心 DDL
│   │   ├── hr_recruit.sql              # 招聘入职 DDL + Camunda 8 表
│   │   ├── hr_payroll.sql              # 薪资考勤 DDL
│   │   └── hr_auto.sql                 # 自动化任务 DDL
│   └── migrations/                     # Flyway/Liquibase 迁移脚本
│       ├── hr_user/
│       ├── hr_recruit/
│       ├── hr_payroll/
│       └── hr_auto/
├── infrastructure/
│   ├── docker-compose.yml              # 本地开发环境编排
│   ├── docker-compose.override.yml     # 开发环境覆盖配置
│   ├── k8s/                            # Kubernetes 部署配置
│   │   ├── namespace.yml
│   │   ├── user-domain/
│   │   ├── recruit-domain/
│   │   ├── payroll-domain/
│   │   ├── auto-domain/
│   │   ├── python-subservices/
│   │   ├── nginx-ingress.yml
│   │   └── monitoring/
│   └── nginx/                          # Nginx 配置
│       ├── default.conf
│       └── ssl/
├── docs/                               # 项目文档
├── scripts/                            # 工具脚本
│   ├── setup-env.sh                    # 环境初始化脚本
│   ├── backup-db.sh                    # 数据库备份脚本
│   └── health-check.sh                 # 健康检查脚本
├── .env.example                        # 环境变量模板
├── .gitignore
├── README.md
└── LICENSE
```

### 3.2 Git 初始化命令

```bash
# 进入项目目录
cd /home/jim/DevFlow/projects/gbm-ai-agent-hr

# 初始化 Git 仓库（如果尚未初始化）
git init

# 创建初始目录结构
mkdir -p backend/{user-domain,recruit-domain,payroll-domain,auto-domain,common}
mkdir -p frontend/{web,mobile}
mkdir -p python-subservices/{rpa-service,ocr-service,face-service}
mkdir -p database/{init,migrations}
mkdir -p infrastructure/{k8s,nginx}
mkdir -p .github/workflows
mkdir -p scripts

# 创建初始提交
git add .
git commit -m "init: GBM AI Agent HR 项目初始化 - 多语言微服务架构"
```

---

## 4. 框架搭建

### 4.1 Java 后端域服务

#### 4.1.1 父 POM (backend/pom.xml)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.gbm.hr</groupId>
    <artifactId>gbm-hr-backend</artifactId>
    <version>1.0.0-SNAPSHOT</version>
    <packaging>pom</packaging>

    <name>GBM AI Agent HR Backend</name>
    <description>GBM AI Agent HR 智能人力管理系统 - 后端微服务</description>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
        <relativePath/>
    </parent>

    <modules>
        <module>common</module>
        <module>user-domain</module>
        <module>recruit-domain</module>
        <module>payroll-domain</module>
        <module>auto-domain</module>
    </modules>

    <properties>
        <java.version>17</java.version>
        <mybatis-plus.version>3.5.5</mybatis-plus.version>
        <redisson.version>3.25.0</redisson.version>
        <kafka.version>3.6.0</kafka.version>
        <resilience4j.version>2.1.0</resilience4j.version>
        <springdoc.version>2.3.0</springdoc.version>
        <minio.version>8.5.3</minio.version>
        <opentelemetry.version>1.34.0</opentelemetry.version>
        <camunda.version>8.4.0</camunda.version>
    </properties>

    <dependencyManagement>
        <dependencies>
            <!-- 公共模块 -->
            <dependency>
                <groupId>com.gbm.hr</groupId>
                <artifactId>gbm-hr-common</artifactId>
                <version>${project.version}</version>
            </dependency>

            <!-- MyBatis-Plus -->
            <dependency>
                <groupId>com.baomidou</groupId>
                <artifactId>mybatis-plus-spring-boot3-starter</artifactId>
                <version>${mybatis-plus.version}</version>
            </dependency>

            <!-- Redisson -->
            <dependency>
                <groupId>org.redisson</groupId>
                <artifactId>redisson-spring-boot-starter</artifactId>
                <version>${redisson.version}</version>
            </dependency>

            <!-- Resilience4j -->
            <dependency>
                <groupId>io.github.resilience4j</groupId>
                <artifactId>resilience4j-spring-boot3</artifactId>
                <version>${resilience4j.version}</version>
            </dependency>

            <!-- SpringDoc OpenAPI -->
            <dependency>
                <groupId>org.springdoc</groupId>
                <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
                <version>${springdoc.version}</version>
            </dependency>

            <!-- MinIO -->
            <dependency>
                <groupId>io.minio</groupId>
                <artifactId>minio</artifactId>
                <version>${minio.version}</version>
            </dependency>
        </dependencies>
    </dependencyManagement>

    <dependencies>
        <!-- 所有域服务共有的依赖 -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-actuator</artifactId>
        </dependency>
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
                <configuration>
                    <excludes>
                        <exclude>
                            <groupId>org.projectlombok</groupId>
                            <artifactId>lombok</artifactId>
                        </exclude>
                    </excludes>
                </configuration>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <configuration>
                    <source>17</source>
                    <target>17</target>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```

#### 4.1.2 域服务 POM 示例 (backend/user-domain/pom.xml)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.gbm.hr</groupId>
        <artifactId>gbm-hr-backend</artifactId>
        <version>1.0.0-SNAPSHOT</version>
    </parent>

    <artifactId>gbm-hr-user-domain</artifactId>
    <name>User Domain Service</name>
    <description>用户中心、认证授权、组织架构、权限管理</description>

    <dependencies>
        <!-- 公共模块 -->
        <dependency>
            <groupId>com.gbm.hr</groupId>
            <artifactId>gbm-hr-common</artifactId>
        </dependency>

        <!-- MySQL -->
        <dependency>
            <groupId>com.mysql</groupId>
            <artifactId>mysql-connector-j</artifactId>
            <scope>runtime</scope>
        </dependency>

        <!-- MyBatis-Plus -->
        <dependency>
            <groupId>com.baomidou</groupId>
            <artifactId>mybatis-plus-spring-boot3-starter</artifactId>
        </dependency>

        <!-- Redis -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-redis</artifactId>
        </dependency>
        <dependency>
            <groupId>org.redisson</groupId>
            <artifactId>redisson-spring-boot-starter</artifactId>
        </dependency>

        <!-- Kafka -->
        <dependency>
            <groupId>org.springframework.kafka</groupId>
            <artifactId>spring-kafka</artifactId>
        </dependency>

        <!-- Keycloak -->
        <dependency>
            <groupId>org.keycloak</groupId>
            <artifactId>keycloak-spring-boot-starter</artifactId>
            <version>22.0.0</version>
        </dependency>

        <!-- SpringDoc -->
        <dependency>
            <groupId>org.springdoc</groupId>
            <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
        </dependency>

        <!-- Resilience4j -->
        <dependency>
            <groupId>io.github.resilience4j</groupId>
            <artifactId>resilience4j-spring-boot3</artifactId>
        </dependency>

        <!-- OpenTelemetry -->
        <dependency>
            <groupId>io.opentelemetry.javaagent</groupId>
            <artifactId>opentelemetry-javaagent</artifactId>
            <version>${opentelemetry.version}</version>
            <scope>runtime</scope>
        </dependency>
    </dependencies>

    <build>
        <finalName>user-domain</finalName>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
```

#### 4.1.3 application.yml 示例 (backend/user-domain/src/main/resources/application.yml)

```yaml
server:
  port: 8081
  servlet:
    context-path: /

spring:
  application:
    name: gbm-hr-user-domain
  profiles:
    active: dev
  datasource:
    url: jdbc:mysql://localhost:3306/hr_user?useUnicode=true&characterEncoding=utf8mb4&useSSL=false&serverTimezone=Asia/Shanghai
    username: ${DB_USER:hr_admin}
    password: ${DB_PASSWORD:hr_admin_password}
    driver-class-name: com.mysql.cj.jdbc.Driver
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000
  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: ${REDIS_PORT:6379}
      password: ${REDIS_PASSWORD:}
      lettuce:
        pool:
          max-active: 20
          max-idle: 10
          min-idle: 5
  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP:localhost:9092,localhost:9093,localhost:9094}
    consumer:
      group-id: user-domain-group
      auto-offset-reset: earliest
      enable-auto-commit: false
    producer:
      acks: all
      retries: 3

mybatis-plus:
  mapper-locations: classpath*:/mapper/**/*.xml
  type-aliases-package: com.gbm.hr.user.entity
  configuration:
    map-underscore-to-camel-case: true
    log-impl: org.apache.ibatis.logging.stdout.StdOutImpl

# Keycloak 配置
keycloak:
  auth-server-url: http://localhost:8080/auth
  realm: gbm-hr
  resource: user-domain
  public-client: true

# SpringDoc 配置
springdoc:
  api-docs:
    path: /api-docs
  swagger-ui:
    path: /swagger-ui.html

# 日志配置
logging:
  level:
    root: INFO
    com.gbm.hr: DEBUG
  pattern:
    console: "%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] [%X{traceId}] %-5level %logger{36} - %msg%n"

# Actuator 配置
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
  endpoint:
    health:
      show-details: always
      probes:
        enabled: true
```

### 4.2 前端应用

#### 4.2.1 Web 应用 (frontend/web/package.json)

```json
{
  "name": "gbm-hr-web",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx,.cts,.mts --fix",
    "test": "vitest",
    "test:coverage": "vitest --coverage"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "@tanstack/vue-query": "^5.0.0",
    "element-plus": "^2.4.0",
    "axios": "^1.6.0",
    "vue-i18n": "^9.8.0",
    "@vueuse/core": "^10.7.0",
    "dayjs": "^1.11.0",
    "echarts": "^5.4.0",
    "vue-echarts": "^6.6.0",
    "qrcode.vue": "^3.4.0",
    "vue-signature-pad": "^3.0.0",
    "pdfjs-dist": "^3.11.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0",
    "eslint": "^8.54.0",
    "eslint-plugin-vue": "^9.18.0",
    "vitest": "^1.0.0",
    "@vue/test-utils": "^2.4.0",
    "sass": "^1.69.0",
    "unplugin-auto-import": "^0.17.0",
    "unplugin-vue-components": "^0.26.0"
  }
}
```

#### 4.2.2 Vite 配置 (frontend/web/vite.config.js)

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
    }),
    Components({
      resolvers: [ElementPlusResolver()],
    }),
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8081',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
```

### 4.3 Python 子服务

#### 4.3.1 OCR 子服务 (python-subservices/ocr-service/requirements.txt)

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
paddleocr>=2.7.0
paddlepaddle>=2.5.0
opencv-python>=4.9.0
python-multipart>=0.0.6
httpx>=0.26.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
structlog>=23.2.0
```

#### 4.3.2 RPA 子服务 (python-subservices/rpa-service/requirements.txt)

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
playwright>=1.40.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
httpx>=0.26.0
structlog>=23.2.0
aiofiles>=23.2.1
```

#### 4.3.3 人脸子服务 (python-subservices/face-service/requirements.txt)

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
insightface>=0.3.0
opencv-python>=4.9.0
numpy>=1.24.0
onnxruntime-gpu>=1.16.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
httpx>=0.26.0
structlog>=23.2.0
```

---

## 5. 数据库初始化

### 5.1 Schema 分配

| Schema | 域服务 | 表数量 | 初始化脚本 |
|--------|--------|--------|-----------|
| hr_user | user-domain (:8081) | 7 张 | database/init/hr_user.sql |
| hr_recruit | recruit-domain (:8082) | 19 张 | database/init/hr_recruit.sql |
| hr_payroll | payroll-domain (:8083) | 6 张 | database/init/hr_payroll.sql |
| hr_auto | auto-domain (:8084) | 2 张 | database/init/hr_auto.sql |

### 5.2 初始化脚本结构

```
database/
├── init/
│   ├── hr_user.sql          # CREATE DATABASE hr_user + 用户中心表 DDL
│   ├── hr_recruit.sql       # CREATE DATABASE hr_recruit + 招聘入职表 DDL + Camunda 8 表
│   ├── hr_payroll.sql       # CREATE DATABASE hr_payroll + 薪资考勤表 DDL
│   └── hr_auto.sql          # CREATE DATABASE hr_auto + 自动化任务表 DDL
└── migrations/              # 版本迁移脚本
    ├── hr_user/
    ├── hr_recruit/
    ├── hr_payroll/
    └── hr_auto/
```

### 5.3 初始化命令

```bash
# 启动 MySQL 容器
docker-compose up -d mysql

# 等待 MySQL 启动完成
sleep 30

# 执行初始化脚本
mysql -h localhost -u root -p${MYSQL_ROOT_PASSWORD} < database/init/hr_user.sql
mysql -h localhost -u root -p${MYSQL_ROOT_PASSWORD} < database/init/hr_recruit.sql
mysql -h localhost -u root -p${MYSQL_ROOT_PASSWORD} < database/init/hr_payroll.sql
mysql -h localhost -u root -p${MYSQL_ROOT_PASSWORD} < database/init/hr_auto.sql

# 验证数据库创建
mysql -h localhost -u root -p${MYSQL_ROOT_PASSWORD} -e "SHOW DATABASES;"
```

### 5.4 Docker Compose MySQL 配置

```yaml
# infrastructure/docker-compose.yml (MySQL 部分)
services:
  mysql:
    image: mysql:8.0
    container_name: gbm-hr-mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      TZ: Asia/Shanghai
    volumes:
      - mysql_data:/var/lib/mysql
      - ./database/init/hr_user.sql:/docker-entrypoint-initdb.d/hr_user.sql
      - ./database/init/hr_recruit.sql:/docker-entrypoint-initdb.d/hr_recruit.sql
      - ./database/init/hr_payroll.sql:/docker-entrypoint-initdb.d/hr_payroll.sql
      - ./database/init/hr_auto.sql:/docker-entrypoint-initdb.d/hr_auto.sql
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: on-failure
    command: >
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_unicode_ci
      --default-authentication-plugin=mysql_native_password

volumes:
  mysql_data:
    driver: local
```

---

## 6. 依赖配置

### 6.1 环境变量 (.env.example)

```bash
# ============================================
# GBM AI Agent HR - 环境变量配置
# ============================================
# 警告: 此文件包含敏感信息，切勿提交到 Git！
# 请将此文件复制到 .env，然后填入真实值
# ============================================

# --- 应用配置 ---
APP_NAME="GBM AI Agent HR"
APP_VERSION="1.0.0"
APP_ENV=dev
DEBUG=true

# --- MySQL 数据库 ---
MYSQL_ROOT_PASSWORD=change_me_root_password
DB_USER=hr_admin
DB_PASSWORD=change_me_db_password
DB_HOST=localhost
DB_PORT=3306
DB_CHARSET=utf8mb4

# --- Redis ---
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=change_me_redis_password
REDIS_DB=0
REDIS_DEFAULT_TTL=3600

# --- Kafka ---
KAFKA_BOOTSTRAP=localhost:9092,localhost:9093,localhost:9094
KAFKA_PARTITIONS=3
KAFKA_REPLICATION=1

# --- Keycloak SSO ---
KEYCLOAK_URL=http://localhost:8080/auth
KEYCLOAK_REALM=gbm-hr
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=change_me_keycloak_password

# --- MinIO 对象存储 ---
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=change_me_minio_password
MINIO_BUCKET_NAME=hr-documents
MINIO_SECURE=false

# --- Elasticsearch ---
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_USER=elastic
ELASTICSEARCH_PASSWORD=change_me_es_password

# --- Milvus 向量数据库 ---
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_USER=root
MILVUS_PASSWORD=change_me_milvus_password

# --- Camunda 8 ---
CAMUNDA_URL=http://localhost:8081
CAMUNDA_USERNAME=admin
CAMUNDA_PASSWORD=change_me_camunda_password

# --- AI/LLM 服务 ---
OPENAI_API_KEY=change_me_openai_key
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=
ANTHROPIC_API_KEY=change_me_anthropic_key
ANTHROPIC_MODEL=claude-3-opus-20240229

# --- vLLM 本地推理 ---
VLLM_ENDPOINT=http://localhost:8000
VLLM_MODEL=

# --- OCR 服务 ---
OCR_SERVICE_URL=http://localhost:8091
OCR_ENGINE=paddleocr

# --- 人脸识别 ---
FACE_SERVICE_URL=http://localhost:8092
FACE_THRESHOLD=0.85

# --- RPA 服务 ---
RPA_SERVICE_URL=http://localhost:8090

# --- 邮件服务 ---
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=hr-noreply@example.com
SMTP_PASSWORD=change_me_smtp_password
SMTP_USE_TLS=true
EMAIL_FROM=hr-noreply@example.com

# --- 短信服务 ---
SMS_PROVIDER=aliyun
SMS_ACCESS_KEY=change_me_sms_key
SMS_ACCESS_SECRET=change_me_sms_secret
SMS_SIGN_NAME=GBM-HR

# --- 外务 RPA 凭证 ---
SOCIAL_SECURITY_URL=https://example-social-security.gov.cn
SOCIAL_SECURITY_USERNAME=change_me_ss_username
SOCIAL_SECURITY_PASSWORD=change_me_ss_password
HOUSING_FUND_URL=https://example-housing-fund.gov.cn
HOUSING_FUND_USERNAME=change_me_hf_username
HOUSING_FUND_PASSWORD=change_me_hf_password

# --- 审计日志 ---
AUDIT_LOG_RETENTION_YEARS=10
AUDIT_LOG_PATH=/var/log/gbm-hr/audit

# --- 监控 ---
PROMETHEUS_ENDPOINT=http://localhost:9090
GRAFANA_ENDPOINT=http://localhost:3000
SENTRY_DSN=
METRICS_ENABLED=true

# --- 文件存储 ---
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=50
ALLOWED_EXTENSIONS=.pdf,.doc,.docx,.xlsx,.xls,.jpg,.jpeg,.png,.bmp

# --- 备份配置 ---
BACKUP_DIR=/var/backups/gbm-hr
BACKUP_RETENTION_DAYS=15
BACKUP_SCHEDULE=0 2 * * 0

# --- JWT (开发环境) ---
JWT_SECRET_KEY=change_me_jwt_secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# --- AES 加密 ---
AES_ENCRYPTION_KEY=change_me_aes_key_32_chars_long!!
```

### 6.2 .gitignore

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
build/
dist/
*.egg-info/
venv/
env/
ENV/

# Java
target/
*.class
*.jar
*.war

# Node.js
node_modules/
dist/
.nuxt/

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# Database
*.db
*.sqlite

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Docker
.docker/

# AI Models
models/
*.pth
*.onnx
*.bin

# Temporary
tmp/
temp/
*.tmp
uploads/
```

---

## 7. Docker Compose 编排

### 7.1 完整 Docker Compose 配置

```yaml
# infrastructure/docker-compose.yml
version: '3.8'

services:
  # ==================== 数据库层 ====================
  mysql:
    image: mysql:8.0
    container_name: gbm-hr-mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      TZ: Asia/Shanghai
    volumes:
      - mysql_data:/var/lib/mysql
      - ./database/init/hr_user.sql:/docker-entrypoint-initdb.d/hr_user.sql
      - ./database/init/hr_recruit.sql:/docker-entrypoint-initdb.d/hr_recruit.sql
      - ./database/init/hr_payroll.sql:/docker-entrypoint-initdb.d/hr_payroll.sql
      - ./database/init/hr_auto.sql:/docker-entrypoint-initdb.d/hr_auto.sql
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: on-failure
    command: >
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_unicode_ci
      --default-authentication-plugin=mysql_native_password

  redis:
    image: redis:7-alpine
    container_name: gbm-hr-redis
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 512mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: on-failure

  # ==================== 消息队列 ====================
  kafka-1:
    image: confluentinc/cp-kafka:7.5.0
    container_name: gbm-hr-kafka-1
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka-1:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
    ports:
      - "9092:9092"
    depends_on:
      - zookeeper
    restart: on-failure

  kafka-2:
    image: confluentinc/cp-kafka:7.5.0
    container_name: gbm-hr-kafka-2
    environment:
      KAFKA_BROKER_ID: 2
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka-2:9093
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
    ports:
      - "9093:9093"
    depends_on:
      - zookeeper
    restart: on-failure

  kafka-3:
    image: confluentinc/cp-kafka:7.5.0
    container_name: gbm-hr-kafka-3
    environment:
      KAFKA_BROKER_ID: 3
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka-3:9094
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
    ports:
      - "9094:9094"
    depends_on:
      - zookeeper
    restart: on-failure

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    container_name: gbm-hr-zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    ports:
      - "2181:2181"
    restart: on-failure

  # ==================== 对象存储 ====================
  minio:
    image: minio/minio:latest
    container_name: gbm-hr-minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: on-failure

  # ==================== 搜索引擎 ====================
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: gbm-hr-elasticsearch
    environment:
      discovery.type: single-node
      ELASTIC_PASSWORD: ${ELASTICSEARCH_PASSWORD}
      xpack.security.enabled: "true"
      xpack.security.http.ssl.enabled: "false"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    healthcheck:
      test: ["CMD-SHELL", "curl -f -u elastic:${ELASTICSEARCH_PASSWORD} http://localhost:9200/_cluster/health || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 5
    restart: on-failure

  # ==================== 向量数据库 ====================
  milvus:
    image: milvusdb/milvus:v2.3.0
    container_name: gbm-hr-milvus
    environment:
      ETCD_ENDPOINTS: etcd:2379
    volumes:
      - milvus_data:/var/lib/milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - etcd
    restart: on-failure

  etcd:
    image: quay.io/coreos/etcd:v3.5.9
    container_name: gbm-hr-etcd
    command: etcd --advertise-client-urls=http://0.0.0.0:2379 --listen-client-urls=http://0.0.0.0:2379 --data-dir=/etcd
    volumes:
      - etcd_data:/etcd
    ports:
      - "2379:2379"
    restart: on-failure

  # ==================== 认证中心 ====================
  keycloak:
    image: quay.io/keycloak/keycloak:22.0
    container_name: gbm-hr-keycloak
    environment:
      KEYCLOAK_ADMIN: ${KEYCLOAK_ADMIN_USER}
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD}
      KC_DB: mysql
      KC_DB_URL: jdbc:mysql://mysql:3306/keycloak
      KC_DB_USERNAME: ${DB_USER}
      KC_DB_PASSWORD: ${DB_PASSWORD}
      KC_PROXY: edge
    command: start-dev
    ports:
      - "8080:8080"
    depends_on:
      - mysql
    restart: on-failure

  # ==================== 后端域服务 ====================
  user-domain:
    build:
      context: ./backend/user-domain
      dockerfile: Dockerfile
    container_name: gbm-hr-user-domain
    environment:
      SPRING_PROFILES_ACTIVE: dev
      DB_HOST: mysql
      DB_PORT: 3306
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      REDIS_PASSWORD: ${REDIS_PASSWORD}
      KAFKA_BOOTSTRAP: kafka-1:9092,kafka-2:9093,kafka-3:9094
      KEYCLOAK_URL: http://keycloak:8080/auth
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
    ports:
      - "8081:8081"
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
      kafka-1:
        condition: service_started
    restart: on-failure

  recruit-domain:
    build:
      context: ./backend/recruit-domain
      dockerfile: Dockerfile
    container_name: gbm-hr-recruit-domain
    environment:
      SPRING_PROFILES_ACTIVE: dev
      DB_HOST: mysql
      DB_PORT: 3306
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      REDIS_PASSWORD: ${REDIS_PASSWORD}
      KAFKA_BOOTSTRAP: kafka-1:9092,kafka-2:9093,kafka-3:9094
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      OCR_SERVICE_URL: http://ocr-service:8091
      FACE_SERVICE_URL: http://face-service:8092
      RPA_SERVICE_URL: http://rpa-service:8090
    ports:
      - "8082:8082"
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
      kafka-1:
        condition: service_started
      ocr-service:
        condition: service_started
      face-service:
        condition: service_started
    restart: on-failure

  payroll-domain:
    build:
      context: ./backend/payroll-domain
      dockerfile: Dockerfile
    container_name: gbm-hr-payroll-domain
    environment:
      SPRING_PROFILES_ACTIVE: dev
      DB_HOST: mysql
      DB_PORT: 3306
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      REDIS_PASSWORD: ${REDIS_PASSWORD}
      KAFKA_BOOTSTRAP: kafka-1:9092,kafka-2:9093,kafka-3:9094
    ports:
      - "8083:8083"
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
      kafka-1:
        condition: service_started
    restart: on-failure

  auto-domain:
    build:
      context: ./backend/auto-domain
      dockerfile: Dockerfile
    container_name: gbm-hr-auto-domain
    environment:
      SPRING_PROFILES_ACTIVE: dev
      DB_HOST: mysql
      DB_PORT: 3306
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      REDIS_PASSWORD: ${REDIS_PASSWORD}
      KAFKA_BOOTSTRAP: kafka-1:9092,kafka-2:9093,kafka-3:9094
      OCR_SERVICE_URL: http://ocr-service:8091
      FACE_SERVICE_URL: http://face-service:8092
      RPA_SERVICE_URL: http://rpa-service:8090
      ELASTICSEARCH_URL: http://elasticsearch:9200
      ELASTICSEARCH_USER: ${ELASTICSEARCH_USER}
      ELASTICSEARCH_PASSWORD: ${ELASTICSEARCH_PASSWORD}
      MILVUS_HOST: milvus
      MILVUS_PORT: 19530
    ports:
      - "8084:8084"
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
      kafka-1:
        condition: service_started
      ocr-service:
        condition: service_started
      face-service:
        condition: service_started
    restart: on-failure

  # ==================== Python 子服务 ====================
  rpa-service:
    build:
      context: ./python-subservices/rpa-service
      dockerfile: Dockerfile
    container_name: gbm-hr-rpa-service
    environment:
      SERVICE_PORT: 8090
      KAFKA_BOOTSTRAP: kafka-1:9092,kafka-2:9093,kafka-3:9094
    ports:
      - "8090:8090"
    depends_on:
      kafka-1:
        condition: service_started
    restart: on-failure

  ocr-service:
    build:
      context: ./python-subservices/ocr-service
      dockerfile: Dockerfile
    container_name: gbm-hr-ocr-service
    environment:
      SERVICE_PORT: 8091
      KAFKA_BOOTSTRAP: kafka-1:9092,kafka-2:9093,kafka-3:9094
    ports:
      - "8091:8091"
    depends_on:
      kafka-1:
        condition: service_started
    restart: on-failure

  face-service:
    build:
      context: ./python-subservices/face-service
      dockerfile: Dockerfile
    container_name: gbm-hr-face-service
    environment:
      SERVICE_PORT: 8092
      KAFKA_BOOTSTRAP: kafka-1:9092,kafka-2:9093,kafka-3:9094
    ports:
      - "8092:8092"
    depends_on:
      kafka-1:
        condition: service_started
    restart: on-failure

  # ==================== 前端 ====================
  nginx:
    image: nginx:alpine
    container_name: gbm-hr-nginx
    volumes:
      - ./infrastructure/nginx/default.conf:/etc/nginx/conf.d/default.conf
      - ./frontend/web/dist:/usr/share/nginx/html:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - user-domain
      - recruit-domain
      - payroll-domain
      - auto-domain
    restart: on-failure

  # ==================== 监控 ====================
  prometheus:
    image: prom/prometheus:latest
    container_name: gbm-hr-prometheus
    volumes:
      - ./infrastructure/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    restart: on-failure

  grafana:
    image: grafana/grafana:latest
    container_name: gbm-hr-grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./infrastructure/monitoring/grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    restart: on-failure

volumes:
  mysql_data:
    driver: local
  minio_data:
    driver: local
  es_data:
    driver: local
  milvus_data:
    driver: local
  etcd_data:
    driver: local
  prometheus_data:
    driver: local
  grafana_data:
    driver: local
```

---

## 8. CI/CD 流水线配置

### 8.1 后端 CI 流水线 (.github/workflows/backend-ci.yml)

```yaml
name: Backend CI

on:
  push:
    branches: [main, develop]
    paths:
      - 'backend/**'
  pull_request:
    branches: [main]
    paths:
      - 'backend/**'

jobs:
  build:
    name: Build & Test
    runs-on: ubuntu-22.04
    strategy:
      matrix:
        service: [user-domain, recruit-domain, payroll-domain, auto-domain]
    defaults:
      run:
        working-directory: ./backend/${{ matrix.service }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
          cache: maven

      - name: Build with Maven
        run: |
          mvn clean package -DskipTests -B

      - name: Run Unit Tests
        run: |
          mvn test -B

      - name: Run Integration Tests
        run: |
          mvn verify -B -Pintegration-test

      - name: SonarQube Analysis
        run: |
          mvn sonar:sonar -B
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        if: github.ref == 'refs/heads/main'

      - name: Upload Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.service }}-jar
          path: backend/${{ matrix.service }}/target/*.jar
          retention-days: 7

  docker-build:
    name: Build Docker Image
    needs: build
    runs-on: ubuntu-22.04
    if: github.ref == 'refs/heads/main'
    strategy:
      matrix:
        service: [user-domain, recruit-domain, payroll-domain, auto-domain]
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and Push Docker Image
        uses: docker/build-push-action@v5
        with:
          context: ./backend/${{ matrix.service }}
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/${{ matrix.service }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}/${{ matrix.service }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### 8.2 前端 CI 流水线 (.github/workflows/frontend-ci.yml)

```yaml
name: Frontend CI

on:
  push:
    branches: [main, develop]
    paths:
      - 'frontend/**'
  pull_request:
    branches: [main]
    paths:
      - 'frontend/**'

jobs:
  build:
    name: Build & Test Web
    runs-on: ubuntu-22.04
    defaults:
      run:
        working-directory: ./frontend/web

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: npm
          cache-dependency-path: frontend/web/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Run Tests
        run: npm run test

      - name: Build
        run: npm run build

      - name: Upload Build Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: web-dist
          path: frontend/web/dist
          retention-days: 7

  docker-build:
    name: Build Docker Image
    needs: build
    runs-on: ubuntu-22.04
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Download Build Artifacts
        uses: actions/download-artifact@v4
        with:
          name: web-dist
          path: frontend/web/dist

      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and Push Docker Image
        uses: docker/build-push-action@v5
        with:
          context: ./frontend/web
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/frontend-web:${{ github.sha }}
            ghcr.io/${{ github.repository }}/frontend-web:latest
```

### 8.3 Python 子服务 CI 流水线 (.github/workflows/python-subservice-ci.yml)

```yaml
name: Python Subservice CI

on:
  push:
    branches: [main, develop]
    paths:
      - 'python-subservices/**'
  pull_request:
    branches: [main]
    paths:
      - 'python-subservices/**'

jobs:
  build:
    name: Build & Test
    runs-on: ubuntu-22.04
    strategy:
      matrix:
        service: [rpa-service, ocr-service, face-service]
    defaults:
      run:
        working-directory: ./python-subservices/${{ matrix.service }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov flake8

      - name: Lint
        run: flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

      - name: Run Tests
        run: pytest --cov=src --cov-report=xml

      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./python-subservices/${{ matrix.service }}/coverage.xml
        if: github.ref == 'refs/heads/main'
```

### 8.4 部署流水线 (.github/workflows/deploy.yml)

```yaml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

jobs:
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-22.04
    if: ${{ github.event_name == 'push' || github.event.inputs.environment == 'staging' }}
    environment: staging
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Deploy to K8s Staging
        run: |
          kubectl apply -f infrastructure/k8s/ -n gbm-hr-staging
        env:
          KUBE_CONFIG: ${{ secrets.KUBE_CONFIG_STAGING }}

      - name: Run Smoke Tests
        run: |
          curl -f http://staging.gbm-hr.example.com/actuator/health || exit 1

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-22.04
    needs: deploy-staging
    if: ${{ github.event.inputs.environment == 'production' }}
    environment: production
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Deploy to K8s Production
        run: |
          kubectl apply -f infrastructure/k8s/ -n gbm-hr-production
        env:
          KUBE_CONFIG: ${{ secrets.KUBE_CONFIG_PRODUCTION }}

      - name: Run Smoke Tests
        run: |
          curl -f http://gbm-hr.example.com/actuator/health || exit 1

      - name: Notify
        run: |
          echo "Production deployment completed successfully"
```

---

## 9. Dockerfile 配置

### 9.1 Java 域服务 Dockerfile (backend/user-domain/Dockerfile)

```dockerfile
# 多阶段构建
FROM eclipse-temurin:17-jdk-alpine AS builder
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn clean package -DskipTests -B

# 运行阶段
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

# 创建非 root 用户
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# 复制 JAR 包
COPY --from=builder /app/target/*.jar app.jar

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8081/actuator/health || exit 1

# 启动参数
ENV JAVA_OPTS="-Xms512m -Xmx1024m -XX:+UseG1GC -XX:MaxGCPauseMillis=200"
EXPOSE 8081

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
```

### 9.2 OCR 子服务 Dockerfile (python-subservices/ocr-service/Dockerfile)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8091/health')" || exit 1

EXPOSE 8091

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8091"]
```

### 9.3 人脸子服务 Dockerfile (python-subservices/face-service/Dockerfile)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8092/health')" || exit 1

EXPOSE 8092

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8092"]
```

### 9.4 RPA 子服务 Dockerfile (python-subservices/rpa-service/Dockerfile)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（Playwright 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgbm1 \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libcups2 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器
RUN playwright install chromium

# 复制代码
COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8090/health')" || exit 1

EXPOSE 8090

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]
```

---

## 10. Nginx 网关配置

### 10.1 默认配置 (infrastructure/nginx/default.conf)

```nginx
upstream user_domain {
    server user-domain:8081;
}

upstream recruit_domain {
    server recruit-domain:8082;
}

upstream payroll_domain {
    server payroll-domain:8083;
}

upstream auto_domain {
    server auto-domain:8084;
}

upstream rpa_service {
    server rpa-service:8090;
}

upstream ocr_service {
    server ocr-service:8091;
}

upstream face_service {
    server face-service:8092;
}

server {
    listen 80;
    server_name localhost;

    # 前端静态资源
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 路由
    location /api/v1/user/ {
        proxy_pass http://user_domain/api/v1/user/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/v1/recruit/ {
        proxy_pass http://recruit_domain/api/v1/recruit/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/v1/payroll/ {
        proxy_pass http://payroll_domain/api/v1/payroll/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/v1/auto/ {
        proxy_pass http://auto_domain/api/v1/auto/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Python 子服务路由
    location /api/v1/ocr/ {
        proxy_pass http://ocr_service/api/v1/ocr/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 50M;
    }

    location /api/v1/face/ {
        proxy_pass http://face_service/api/v1/face/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 50M;
    }

    location /api/v1/rpa/ {
        proxy_pass http://rpa_service/api/v1/rpa/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket 支持
    location /ws/ {
        proxy_pass http://user_domain/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Swagger 文档
    location /swagger/ {
        proxy_pass http://recruit_domain/swagger-ui.html;
    }

    # 健康检查
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

---

## 11. 环境初始化脚本

### 11.1 开发环境初始化 (scripts/setup-env.sh)

```bash
#!/bin/bash
set -e

echo "=========================================="
echo "GBM AI Agent HR 开发环境初始化"
echo "=========================================="

# 检查依赖
echo "[1/8] 检查依赖..."
for cmd in docker docker-compose git mvn node npm python; do
    if ! command -v $cmd &> /dev/null; then
        echo "ERROR: $cmd 未安装"
        exit 1
    fi
done
echo "所有依赖已安装"

# 复制 .env 文件
echo "[2/8] 初始化环境变量..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ".env 文件已创建，请编辑填入真实值"
else
    echo ".env 文件已存在，跳过"
fi

# 启动基础设施服务
echo "[3/8] 启动基础设施服务..."
docker-compose up -d mysql redis kafka-1 kafka-2 kafka-3 zookeeper minio elasticsearch milvus etcd keycloak
echo "等待基础设施服务启动..."
sleep 30

# 验证服务状态
echo "[4/8] 验证基础设施服务..."
docker-compose ps

# 初始化数据库
echo "[5/8] 数据库初始化完成（Docker Compose 自动挂载 SQL 脚本）"

# 安装前端依赖
echo "[6/8] 安装前端依赖..."
cd frontend/web && npm ci && cd ../..

# 安装 Python 依赖
echo "[7/8] 安装 Python 子服务依赖..."
for service in rpa-service ocr-service face-service; do
    cd python-subservices/$service
    pip install -r requirements.txt
    cd ../..
done

# 构建 Java 后端
echo "[8/8] 构建 Java 后端..."
cd backend && mvn clean install -DskipTests -B && cd ..

echo "=========================================="
echo "环境初始化完成！"
echo "=========================================="
echo ""
echo "访问地址："
echo "  前端:       http://localhost:80"
echo "  User域:     http://localhost:8081"
echo "  Recruit域:  http://localhost:8082"
echo "  Payroll域:  http://localhost:8083"
echo "  Auto域:     http://localhost:8084"
echo "  RPA服务:    http://localhost:8090"
echo "  OCR服务:    http://localhost:8091"
echo "  Face服务:   http://localhost:8092"
echo "  Keycloak:   http://localhost:8080/auth"
echo "  MinIO:      http://localhost:9001"
echo "  Prometheus: http://localhost:9090"
echo "  Grafana:    http://localhost:3000"
echo "  Elasticsearch: http://localhost:9200"
echo ""
echo "默认凭据："
echo "  Grafana: admin/admin"
echo "  MinIO: minioadmin/minioadmin"
echo "  Keycloak: 见 .env 文件"
```

### 11.2 健康检查脚本 (scripts/health-check.sh)

```bash
#!/bin/bash

echo "=========================================="
echo "GBM AI Agent HR 健康检查"
echo "=========================================="

check_service() {
    local name=$1
    local url=$2
    if curl -sf "$url" > /dev/null 2>&1; then
        echo "[OK]   $name"
        return 0
    else
        echo "[FAIL] $name ($url)"
        return 1
    fi
}

FAILED=0

check_service "MySQL" "http://localhost:3306" || FAILED=1
check_service "Redis" "http://localhost:6379" || FAILED=1
check_service "User Domain" "http://localhost:8081/actuator/health" || FAILED=1
check_service "Recruit Domain" "http://localhost:8082/actuator/health" || FAILED=1
check_service "Payroll Domain" "http://localhost:8083/actuator/health" || FAILED=1
check_service "Auto Domain" "http://localhost:8084/actuator/health" || FAILED=1
check_service "RPA Service" "http://localhost:8090/health" || FAILED=1
check_service "OCR Service" "http://localhost:8091/health" || FAILED=1
check_service "Face Service" "http://localhost:8092/health" || FAILED=1
check_service "Keycloak" "http://localhost:8080/auth" || FAILED=1
check_service "MinIO" "http://localhost:9001" || FAILED=1
check_service "Elasticsearch" "http://localhost:9200" || FAILED=1
check_service "Prometheus" "http://localhost:9090" || FAILED=1
check_service "Grafana" "http://localhost:3000" || FAILED=1

if [ $FAILED -eq 0 ]; then
    echo ""
    echo "所有服务运行正常！"
else
    echo ""
    echo "部分服务异常，请检查日志"
    exit 1
fi
```

---

## 12. 端口分配总览

| 服务 | 端口 | 协议 | 说明 |
|------|------|------|------|
| Nginx 网关 | 80/443 | HTTP/HTTPS | 前端静态资源 + API 反向代理 |
| User Domain | 8081 | HTTP | 用户中心域服务 |
| Recruit Domain | 8082 | HTTP | 招聘管理域服务 |
| Payroll Domain | 8083 | HTTP | 薪资管理域服务 |
| Auto Domain | 8084 | HTTP | 自动化域服务 |
| Keycloak | 8080 | HTTP | 统一认证中心 |
| RPA Service | 8090 | HTTP | RPA 浏览器自动化 |
| OCR Service | 8091 | HTTP | 证件识别 |
| Face Service | 8092 | HTTP | 人脸比对 |
| MySQL | 3306 | TCP | 关系型数据库 |
| Redis | 6379 | TCP | 缓存 |
| Kafka-1 | 9092 | TCP | 消息队列节点 1 |
| Kafka-2 | 9093 | TCP | 消息队列节点 2 |
| Kafka-3 | 9094 | TCP | 消息队列节点 3 |
| Zookeeper | 2181 | TCP | Kafka 协调 |
| MinIO | 9000/9001 | HTTP | 对象存储/API+Console |
| Elasticsearch | 9200 | HTTP | 搜索引擎 |
| Milvus | 19530 | TCP | 向量数据库 |
| Etcd | 2379 | TCP | Milvus 元数据 |
| Prometheus | 9090 | HTTP | 监控指标采集 |
| Grafana | 3000 | HTTP | 监控仪表盘 |

---

## 13. 快速启动指南

### 13.1 开发环境一键启动

```bash
# 1. 克隆代码仓库
cd /home/jim/DevFlow/projects/gbm-ai-agent-hr

# 2. 执行环境初始化脚本
chmod +x scripts/setup-env.sh
./scripts/setup-env.sh

# 3. 启动所有服务
docker-compose up -d

# 4. 等待服务启动（约 60 秒）
sleep 60

# 5. 执行健康检查
chmod +x scripts/health-check.sh
./scripts/health-check.sh
```

### 13.2 单独启动某个域服务

```bash
# 仅启动 User 域服务
cd backend/user-domain
mvn spring-boot:run

# 仅启动 OCR 子服务
cd python-subservices/ocr-service
uvicorn main:app --host 0.0.0.0 --port 8091

# 仅启动前端开发服务器
cd frontend/web
npm run dev
```

### 13.3 停止所有服务

```bash
# 停止并删除容器（保留数据卷）
docker-compose down

# 停止并删除容器和数据卷
docker-compose down -v
```

---

## 14. 文档版本

| 版本 | 日期 | 作者 | 说明 |
|------|------|------|------|
| V1.0 | 2026-06-16 | 后富 | 初始环境配置文档 |
| V2.0 | 2026-06-22 | 后富 | 基于 ARCHITECTURE_V24、BACKEND_V35、DATABASE_V19、FRONTEND_V26 全面修订；对齐 4 域服务架构、Kafka 3 节点集群、Camunda 8 (Zeebe)、Keycloak SSO、Vue 3.4 + Element Plus、InsightFace 0.3.x、完整 CI/CD 流水线、Docker Compose 编排、Nginx 网关配置 |

---

*文档结束*
