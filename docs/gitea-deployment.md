# Gitea 部署与初始化指南

## Docker 安装

Gitea 已集成在 DevFlow 的 Docker Compose 配置中，无需单独安装。

### 手动安装（可选）

如需独立安装 Gitea：

```bash
docker run -d \
  --name gitea \
  -p 3000:3000 \
  -p 2222:22 \
  -e GITEA__database__DB_TYPE=postgres \
  -e GITEA__database__HOST=gitea-db:5432 \
  -e GITEA__database__NAME=gitea \
  -e GITEA__database__USER=gitea \
  -e GITEA__database__PASSWD=gitea_password \
  -v gitea_data:/data \
  gitea/gitea:latest
```

## 安装向导

首次访问 `http://localhost:3000` 将进入安装向导：

### 1. 数据库配置

| 字段 | 值 |
|------|-----|
| 数据库类型 | PostgreSQL |
| 主机 | gitea-db:5432 |
| 用户名 | gitea |
| 密码 | gitea_password |
| 数据库名 | gitea |

### 2. 服务器配置

| 字段 | 值 |
|------|-----|
| 服务器域名 | localhost |
| HTTP端口 | 3000 |
| 根URL | http://localhost:3000 |

### 3. 管理员账号

- 首个注册用户自动成为管理员
- 建议使用 `devflow` 作为管理员用户名

## DevFlow 连接配置

### 1. 生成 API Token

1. 登录 Gitea 管理员账号
2. 进入 **设置 → 应用 → 管理 Access Token**
3. 生成新 Token，权限选择 `全部`
4. 复制 Token 值

### 2. 配置 DevFlow

在 `.env.production` 中设置：

```env
GITEA_URL=http://gitea:3000
GITEA_API_TOKEN=<your-token>
GITEA_ADMIN_USER=devflow
GITEA_ADMIN_PASSWORD=<your-password>
```

### 3. 创建组织

在 Gitea 中创建组织用于项目仓库管理：

1. 进入 **组织 → 创建组织**
2. 组织名称建议与 DevFlow 项目命名空间一致
3. 可见性选择 `私有`

### 4. 验证连接

```bash
curl -H "Authorization: token <your-token>" \
  http://localhost:3000/api/v1/user
```

返回用户信息表示连接成功。

## Git Flow 初始化

DevFlow 创建项目仓库时会自动初始化 Git Flow：

- `main` 分支：受保护，需要2人审核
- `develop` 分支：受保护，需要1人审核
- 功能分支从 `develop` 创建
- 发布分支从 `develop` 创建
- 热修复分支从 `main` 创建

## Webhook 配置

DevFlow 自动为项目仓库注册 Webhook：

- URL: `http://backend:8000/api/webhooks/gitea`
- 事件: `push`, `pull_request`
- 支持提交校验（Conventional Commits 规范）
