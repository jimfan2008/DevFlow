#!/usr/bin/env python3
"""Generate V15 from V14 with targeted fixes."""

with open("/home/jim/DevFlow/projects/devflow/docs/devflow_BACKEND_V14.md", "r") as f:
    content = f.read()

# Fix 1: REDIS_URL in docker-compose should be redis://redis:6379, not postgresql://...
# The devflow service REDIS_URL was incorrectly set to a PostgreSQL connection string
content = content.replace(
    "- REDIS_URL=postgresql://devflow:***@postgres:5432/devflow_db\n      - REDIS_URL=redis://redis:6379\n      - CELERY_BROKER_URL=redis://redis:6379/1\n      - CELERY_RESULT_BACKEND=redis://redis:6379/2\n      environment:\n        - REDIS_URL=redis://redis:***@postgres:5432/devflow_db",
    "- REDIS_URL=redis://redis:6379\n      - CELERY_BROKER_URL=redis://redis:6379/1\n      - CELERY_RESULT_BACKEND=redis://redis:6379/2\n    volumes:\n      - swarm_data:/data/devflow/swarms\n      - devflow_logs:/app/logs\n    depends_on:\n      - postgres\n      - redis\n\n  # Celery Worker\n  celery-worker:\n    build: .\n    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4\n    environment:\n      - DATABASE_URL=postgresql://devflow:***@postgres:5432/devflow_db\n      - REDIS_URL=redis://redis:6379\n      - CELERY_BROKER_URL=redis://redis:6379/1\n      - CELERY_RESULT_BACKEND=redis://redis:6379/2\n    volumes:\n      - swarm_data:/data/devflow/swarms\n      - devflow_logs:/app/logs\n    depends_on:\n      - redis\n      - postgres\n\n  # Celery Beat (定时调度器)\n  celery-beat:\n    build: .\n    command: celery -A app.tasks.celery_app beat --loglevel=info\n    environment:\n      - DATABASE_URL=postgresql://devflow:***@postgres:5432/devflow_db\n      - REDIS_URL=redis://redis:6379\n      - CELERY_BROKER_URL=redis://redis:6379/1\n      - CELERY_RESULT_BACKEND=redis://redis:6379/2\n    depends_on:\n      - redis\n      - celery-worker\n"
)

# Fix 2: houDa -> houda (all lowercase, consistent with other profiles)
content = content.replace("HouDa | houDa", "HouDa | houda")

# Fix 3: Update version header
content = content.replace(
    "**版本**: V14\n**日期**: 2026-06-17\n**作者**: HouWang (后旺)\n**状态**: 修订版V14（修复后荣检验全部不合格项）",
    "**版本**: V15\n**日期**: 2026-06-18\n**作者**: HouWang (后旺)\n**状态**: 修订版V15（修复后荣检验全部不合格项）"
)

# Fix 4: Add V15 revision record
old_end = """**文档结束**"""

new_end = """---

## 20. V15 修订记录

本节记录 V14 到 V15 的修订内容，对应后荣检验报告中的不合格项：

| 序号 | 严重级别 | 问题描述 | 修复方案 |
|---|---|---|---|
| 1 | 严重 | docker-compose 中 devflow 服务 REDIS_URL 错误指向 PostgreSQL 连接字符串 | 16.1 节修正 devflow 服务 REDIS_URL 为 `redis://redis:6379`，同时修正 celery-worker 和 celery-beat 中错误的 REDIS_URL |
| 2 | 中等 | 4.2 节 HouDa 的 Profile 名称 `houDa` 大小写与其他 Agent 不一致 | 统一修正为全小写 `houda`，与其他 8 个命名 Agent 的 Profile 命名规范保持一致 |
| 3 | 轻微 | 7.2 节 NAMED_AGENTS 列表中 `houDa` 大小写不一致 | 同步修正为 `houda` |

**文档结束**"""

content = content.replace(old_end, new_end)

with open("/home/jim/DevFlow/projects/devflow/docs/devflow_BACKEND_V15.md", "w") as f:
    f.write(content)

print("V15 generated successfully")
print(f"Total chars: {len(content)}")
