#!/usr/bin/env python3
"""
DevFlow 项目管理平台 - API 路由注册
修复: 消除重复路由注册 (workload_router 同时注册在 workload 和 boards 前缀下)
修复: 消除重复路由注册 (boards_router 同时注册在 boards 和 projects 前缀下)
"""

from fastapi import APIRouter

main_router = APIRouter(redirect_slashes=False)

from app.api.auth import router as auth_router
from app.api.boards import router as boards_router
from app.api.tasks import router as tasks_router
from app.api.comments import router as comments_router
from app.api.attachments import router as attachments_router
from app.api.dependencies import router as dependencies_router
from app.api.workload import router as workload_router
from app.api.inbox import router as inbox_router
from app.api.requirements import router as requirements_router
from app.api.agents import router as agents_router
from app.api.tasks_srs import router as tasks_srs_router
from app.api.projects_srs import router as projects_srs_router
from app.api.files import router as files_router
from app.api.webhooks import router as webhooks_router
from app.api.websocket import router as websocket_router
from app.api.hermes_router import router as hermes_new_router
from app.api.profiles import router as profiles_router
from app.api.groups import router as groups_router
from app.api.projects import router as projects_router
from app.api.chat import router as chat_router
from app.api.repos import router as repos_router
from app.api.notifications import router as notifications_router
from app.api.meetings import router as meetings_router
from app.api.task_states import router as task_states_router
from app.api.skills import router as skills_router
from app.api.acceptance import router as acceptance_router
from app.api.ws import router as chat_ws_router
from app.api.workflow import router as workflow_router
from app.api.qa import router as qa_router
from app.api.swarms import router as swarms_router
from app.api.security import router as security_router
from app.api.hermes_integration import router as hermes_integration_router

main_router.include_router(auth_router, prefix="/api/auth", tags=["auth"])
main_router.include_router(boards_router, prefix="/api/boards", tags=["boards"])
main_router.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])
main_router.include_router(
    comments_router, prefix="/api/comments", tags=["comments"]
)
main_router.include_router(
    attachments_router, prefix="/api/attachments", tags=["attachments"]
)
main_router.include_router(
    dependencies_router, prefix="/api/dependencies", tags=["dependencies"]
)
main_router.include_router(workload_router, prefix="/api/workload", tags=["workload"])
main_router.include_router(inbox_router, prefix="/api/inbox", tags=["inbox"])
# ── SRS Modules ──────────────────────────────────────
main_router.include_router(
    requirements_router, prefix="/api/projects", tags=["requirements"]
)
main_router.include_router(
    projects_srs_router, prefix="/api/projects", tags=["projects-srs"]
)
main_router.include_router(agents_router, prefix="/api", tags=["agents"])
main_router.include_router(tasks_srs_router, prefix="/api", tags=["tasks-srs"])
# ── Infrastructure ───────────────────────────────────
main_router.include_router(files_router, prefix="/api/files", tags=["files"])
main_router.include_router(webhooks_router, prefix="/api", tags=["webhooks"])
main_router.include_router(websocket_router, prefix="/ws", tags=["websocket"])
main_router.include_router(hermes_new_router, prefix="/api", tags=["hermes"])
main_router.include_router(profiles_router)
main_router.include_router(groups_router)
main_router.include_router(chat_router)
main_router.include_router(projects_router, prefix="/api/projects", tags=["projects"])
main_router.include_router(repos_router, prefix="/api/repos", tags=["repos"])
main_router.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])
main_router.include_router(meetings_router, prefix="/api/groups", tags=["meetings"])
main_router.include_router(task_states_router, prefix="/api/task-states", tags=["task-states"])
main_router.include_router(skills_router, prefix="/api/skills", tags=["skills"])
main_router.include_router(acceptance_router, prefix="/api/acceptance", tags=["acceptance"])
main_router.include_router(chat_ws_router, prefix="/api", tags=["chat-ws"])
main_router.include_router(workflow_router, prefix="/api/v1/workflow", tags=["workflow"])
main_router.include_router(qa_router, prefix="/api/v1/qa", tags=["qa"])
main_router.include_router(swarms_router, prefix="/api/v1/swarms", tags=["swarms"])
main_router.include_router(security_router, prefix="/api/v1/security", tags=["security"])
main_router.include_router(hermes_integration_router, prefix="/api", tags=["hermes-integration"])

from app.api.scheduling import router as scheduling_router
main_router.include_router(scheduling_router, tags=["scheduling"])

__all__ = ["main_router"]


from . import agents, requirements, scheduling