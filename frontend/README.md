# DevFlow - 项目管理平台

轻量级团队协作项目管理平台，核心功能：看板视图、任务依赖管理、人员负载分析、个人收件箱。

## 技术栈

- **前端**: Vue 3 + Element Plus + Vite + Pinia + Vue Router
- **后端**: Python FastAPI + Celery + PostgreSQL + Redis

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 功能模块

- [x] 用户认证（注册、登录、Token管理）
- [x] 看板管理（自定义列、任务卡片拖拽）
- [x] 任务管理（CRUD、状态流转）
- [x] 依赖管理（前置/后置依赖、循环检测）
- [x] 负载分析（热力图、成员负载）
- [x] 收件箱（通知聚合、标记已读）
- [x] 评论和附件
