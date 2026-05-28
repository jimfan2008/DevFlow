# DevFlow 部署指南

## 环境要求

- Docker 24.0+
- Docker Compose v2.20+
- 4GB+ 内存
- 20GB+ 磁盘空间

## Docker Compose 启动步骤

### 1. 克隆项目

```bash
git clone https://gitea.example.com/devflow/devflow.git
cd devflow
```

### 2. 配置环境变量

```bash
cp .env.example .env.production
```

编辑 `.env.production`，填入以下关键变量：

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `SECRET_KEY` | JWT签名密钥，生产环境必须替换 | 是 |
| `JWT_SECRET` | JWT令牌密钥 | 是 |
| `GITEA_API_TOKEN` | Gitea管理员API Token | 是 |
| `GITEA_ADMIN_PASSWORD` | Gitea管理员密码 | 是 |
| `HERMES_API_BASE` | Hermes Agent API地址 | 否 |
| `HERMES_API_KEY` | Hermes Agent API密钥 | 否 |

### 3. 启动服务

```bash
# 开发环境
docker compose -f docker-compose.dev.yml up -d

# 生产环境（完整部署）
docker compose up -d

# 最小化部署（不含Gitea）
docker compose -f docker-compose.min.yml up -d
```

### 4. 验证服务状态

```bash
# 检查后端健康
curl http://localhost:8000/health

# 检查所有容器状态
docker compose ps

# 查看日志
docker compose logs -f backend
```

### 5. 访问服务

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:8080 |
| 后端API | http://localhost:8000 |
| API文档 | http://localhost:8000/docs |
| ReDoc文档 | http://localhost:8000/redoc |
| Gitea | http://localhost:3000 |
| PostgreSQL | localhost:15432 |
| Redis | localhost:6379 |

## 环境变量配置说明

### 应用配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_NAME` | DevFlow | 应用名称 |
| `APP_DEBUG` | false | 调试模式 |
| `APP_HOST` | 0.0.0.0 | 监听地址 |
| `APP_PORT` | 8000 | 监听端口 |
| `FRONTEND_URL` | http://localhost | 前端URL（CORS） |
| `SECRET_KEY` | - | 加密密钥 |
| `JWT_SECRET` | - | JWT密钥 |
| `JWT_ALGORITHM` | HS256 | JWT算法 |
| `JWT_EXPIRE_MINUTES` | 30 | JWT过期时间(分钟) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | 访问令牌过期时间 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | 刷新令牌过期时间 |

### 数据库配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_URL` | postgresql+asyncpg://... | 主数据库连接 |
| `REDIS_URL` | redis://redis:6379/0 | Redis连接 |

### Gitea配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `GITEA_URL` | http://gitea:3000 | Gitea服务地址 |
| `GITEA_API_TOKEN` | - | API访问令牌 |
| `GITEA_ADMIN_USER` | devflow | 管理员用户名 |
| `GITEA_ADMIN_PASSWORD` | - | 管理员密码 |

### Hermes Agent配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `HERMES_API_BASE` | - | Hermes API地址 |
| `HERMES_API_KEY` | - | Hermes API密钥 |
| `HERMES_MODEL` | - | 模型名称 |
| `AGENT_TIMEOUT` | 60 | Agent超时(秒) |
| `MAX_CONCURRENT_AGENTS` | 5 | 最大并发Agent数 |

### Celery配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `CELERY_BROKER_URL` | redis://redis:6379/1 | 消息队列 |
| `CELERY_RESULT_BACKEND` | redis://redis:6379/2 | 结果存储 |

### 文件上传配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `UPLOAD_DIR` | /tmp/attachments | 上传目录 |
| `MAX_UPLOAD_SIZE_MB` | 10 | 最大上传大小(MB) |
| `ALLOWED_EXTENSIONS` | .pdf,.doc,.docx,... | 允许的文件扩展名 |

## 停止与清理

```bash
# 停止所有服务
docker compose down

# 停止并删除数据卷
docker compose down -v

# 重新构建
docker compose build --no-cache
docker compose up -d
```
