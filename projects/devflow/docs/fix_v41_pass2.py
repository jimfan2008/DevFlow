#!/usr/bin/env python3
"""V41 第二遍修正 - 处理剩余未替换的 V39 数据模型和一致性检查表"""

src = "/home/jim/DevFlow/projects/devflow/docs/devflow_BACKEND_V41.md"
dst = "/home/jim/DevFlow/projects/devflow/docs/devflow_BACKEND_V41.md"

with open(src, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Process line by line for more precision
for i in range(len(lines)):
    line = lines[i]

    # 1. Remove ws-token endpoint section (lines 612-635 area)
    if "**POST /api/v1/auth/ws-token** - 获取 WebSocket 专用 Token (V39 新增)" in line:
        # Replace this and following lines until next section
        lines[i] = "**V41 修正**: ws-token 端点已移除，WebSocket 认证直接使用 access_token。\n"
        # Clear next 20 lines that are part of this section
        for j in range(i+1, min(i+22, len(lines))):
            if lines[j].startswith("**") and "V41" not in lines[j] and "POST" not in lines[j] and "GET" not in lines[j]:
                break
            lines[j] = ""
        break  # Only process first occurrence

    # 2. project_status enum in data models (line 1842 area)
    if "status: str" in line and "created/in_progress/completed/cancelled" in line:
        lines[i] = line.replace("created/in_progress/completed/cancelled", "active/paused/completed/archived")
        lines[i] = line.replace("V39 修正", "V41 修正")
        lines[i] = lines[i].replace("与数据库 V30 §1.3 project_status 枚举保持一致", "与数据库 V33 §1.3 project_status 枚举保持一致")

    # 3. ProjectOut deleted_at note (line 1862 area)
    if "ProjectOut 新增 deleted_at 字段" in line:
        lines[i] = line.replace(
            "**V39 修正**: (1) ProjectOut 新增 deleted_at 字段 (Optional[datetime])，对应数据库 V30 §3.1 projects 表 deleted_at 软删除字段；(2) status 枚举值改为 created/in_progress/completed/cancelled，与数据库 V30 §1.3 project_status 枚举保持一致；(3) ProjectUpdate 配合 PATCH 方法使用。",
            "**V41 修正**: (1) ProjectOut 已移除 deleted_at 字段，与数据库 V33 §3.1 一致；(2) status 枚举值改为 active/paused/completed/archived，与数据库 V33 §1.3 project_status 枚举保持一致。"
        )

    # 4. AgentOut status V39 note (line 1872/1879 area)
    if "AgentOut.status 枚举值改为 idle/busy/error/offline" in line and "V39 修正" in line:
        lines[i] = line.replace("V39 修正", "V41 修正")
        lines[i] = line.replace("数据库 V30", "数据库 V33")

    # 5. AgentStatusReport regex pattern (line 1879)
    if "^(online|offline|busy)$" in line:
        lines[i] = line.replace("^(online|offline|busy)$", "^(idle|busy|error|offline)$")
        lines[i] = lines[i].replace("V39 修正", "V41 修正")

    # 6. users.role in database table definition (line 2385)
    if "role" in line and "user/admin/system_admin" in line and "VARCHAR" in line:
        lines[i] = line.replace("user/admin/system_admin", "user/admin")
        lines[i] = lines[i].replace("V39 修正", "V41 修正")

    # 7. user_role V39 note (line 2390)
    if "role 枚举值改为 user/admin/system_admin" in line:
        lines[i] = line.replace(
            "**V39 修正**: role 枚举值改为 user/admin/system_admin，与数据库 V30 user_role 枚举保持一致。",
            "**V41 修正**: role 枚举值改为 user/admin，与数据库 V33 §1.3 user_role 枚举保持一致（已移除 system_admin）。"
        )

    # 8. projects.status in database table (line 2403)
    if "status" in line and "created/in_progress/completed/cancelled" in line and "VARCHAR" in line:
        lines[i] = line.replace("created/in_progress/completed/cancelled", "active/paused/completed/archived")
        lines[i] = lines[i].replace("DEFAULT 'created'", "DEFAULT 'active'")

    # 9. projects deleted_at note (line 2409)
    if "新增 deleted_at 字段 (TIMESTAMPTZ NULLABLE)" in line:
        lines[i] = line.replace(
            "**V39 修正**: (1) 新增 deleted_at 字段 (TIMESTAMPTZ NULLABLE)，与数据库 V30 §3.1 projects 表 deleted_at 软删除字段保持一致；(2) status 枚举值改为 created/in_progress/completed/cancelled，与数据库 V30 §1.3 project_status 枚举保持一致。",
            "**V41 修正**: (1) 已移除 deleted_at 字段，与数据库 V33 §3.1 一致；(2) status 枚举值改为 active/paused/completed/archived，与数据库 V33 §1.3 project_status 枚举保持一致。"
        )

    # 10. agent_status in database table (line 2440/2449)
    if "status" in line and "DEFAULT 'online'" in line and "VARCHAR" in line:
        lines[i] = line.replace("DEFAULT 'online'", "DEFAULT 'idle'")
        lines[i] = lines[i].replace("online/offline/busy", "idle/busy/error/offline")

    if "status 枚举值改为 idle/busy/error/offline" in line and "DEFAULT" in line and "V39" in line:
        lines[i] = line.replace("V39 修正", "V41 修正")
        lines[i] = line.replace("默认值改为 'online'", "默认值改为 'idle'")
        lines[i] = line.replace("数据库 V30", "数据库 V33")

    # 11. sender_type in schema (line 2082)
    if "GroupMessageOut.sender_type" in line and "user/agent（二值）" in line:
        lines[i] = line.replace("user/agent（二值）", "user/agent/system（三值）")
        lines[i] = line.replace("数据库 V30", "数据库 V33")

    # 12. Consistency check table - project_status (line 3296)
    if "projects.status 枚举值不一致" in line:
        lines[i] = line.replace(
            "| 5 | projects.status 枚举值不一致：后端 V37 使用 active/paused/completed/archived，数据库 V30 §1.3 枚举 project_status 为 created/in_progress/completed/cancelled | 不一致 | 改为 created/in_progress/completed/cancelled | ✅ 已修正 | §2.3, §4.3, §5.2.2 |",
            "| 5 | V41 修正：projects.status 枚举值统一为 active/paused/completed/archived，与数据库 V33 §1.3 保持一致 | 已修正 | - | ✅ V41 | §2.3, §4.3, §5.2.2 |"
        )

    # 13. Consistency check table - user_role (line 3297)
    if "user_role 枚举不一致" in line:
        lines[i] = line.replace(
            "| 6 | user_role 枚举不一致：后端 V37 使用 user/admin，数据库 V30 枚举为 user/admin/system_admin | 不一致 | 改为 user/admin/system_admin | ✅ 已修正 | §4.2, §5.2.1 |",
            "| 6 | V41 修正：user_role 枚举统一为 user/admin（已移除 system_admin），与数据库 V33 §1.3 保持一致 | 已修正 | - | ✅ V41 | §4.2, §5.2.1 |"
        )

    # 14. Consistency check table - sender_type (line 3299)
    if "group_messages.sender_type 不一致" in line and "二值" in line:
        lines[i] = line.replace(
            "| 8 | group_messages.sender_type 不一致：后端 V37 §4.8 GroupMessageOut.sender_type 为 user/agent/system 三值，数据库 V30 §1.3 sender_type 枚举为 user/agent 二值 | 不一致 | 改为 user/agent 二值，与数据库 V30 保持一致 | ✅ 已修正 | §4.8, §5.2.10 |",
            "| 8 | V41 修正：group_messages.sender_type 统一为 user/agent/system 三值，与数据库 V33 §1.3 保持一致 | 已修正 | - | ✅ V41 | §4.8, §5.2.10 |"
        )

    # 15. HTTP method comparison table - projects (line 2987, 3281, 3335)
    if "PATCH /projects/:id" in line and "member" in line:
        lines[i] = line.replace("PATCH /projects/:id", "PUT /projects/:id").replace("(V39: PATCH)", "(V41: PUT)")

    if "项目更新 HTTP 方法不一致" in line:
        lines[i] = line.replace(
            "| 2 | 【严重】项目更新 HTTP 方法不一致：前端 V19 §5.1 updateProject 使用 api.patch，§5.2 端点清单为 PATCH /projects/:id；后端 V37 定义为 PUT | 不一致 | 改为 PATCH /api/v1/projects/:id | ✅ 已修正 | §2.3, §4.3 |",
            "| 2 | V41 修正：项目更新 HTTP 方法统一为 PUT /api/v1/projects/:id，与前端 V20 §5.2 保持一致 | 已修正 | - | ✅ V41 | §2.3 |"
        )

    if "| 项目更新 | PATCH /api/v1/projects/:id | PATCH /projects/:id | ✅ |" in line:
        lines[i] = line.replace(
            "| 项目更新 | PATCH /api/v1/projects/:id | PATCH /projects/:id | ✅ |",
            "| 项目更新 | PUT /api/v1/projects/:id | PUT /projects/:id | ✅ |"
        )

    # 16. HTTP method comparison table - tasks (line 3286, 3337)
    if "taskStore updateTaskStatus" in line and "V37 使用 PUT" in line:
        lines[i] = line.replace(
            "| 7 | 前端 V19 §4.5 taskStore updateTaskStatus 使用 api.patch(/tasks/${taskId}, {status})，后端 V37 使用 PUT /tasks/:id | 不一致 | 改为 PATCH /api/v1/tasks/:id | ✅ 已修正 | §2.5, §4.5 |",
            "| 7 | V41 修正：任务更新 HTTP 方法统一为 PUT /api/v1/tasks/:id，与前端 V20 §4.5 保持一致 | 已修正 | - | ✅ V41 | §2.5 |"
        )

    if "| 任务状态更新 | PATCH /api/v1/tasks/:id | PATCH /tasks/:id | ✅ |" in line:
        lines[i] = line.replace(
            "| 任务状态更新 | PATCH /api/v1/tasks/:id | PATCH /tasks/:id | ✅ |",
            "| 任务状态更新 | PUT /api/v1/tasks/:id | PUT /tasks/:id | ✅ |"
        )

    # 17. HTTP method comparison table - notifications (line 3282, 3336)
    if "通知已读标记 HTTP 方法不一致" in line:
        lines[i] = line.replace(
            "| 3 | 【严重】通知已读标记 HTTP 方法不一致：前端 V19 §4.6 markAsRead 使用 api.patch，§5.2 端点清单为 PATCH /notifications/:id/read；后端 V37 定义为 PUT | 不一致 | 改为 PATCH /api/v1/notifications/:id/read 和 PATCH /api/v1/notifications/read-all | ✅ 已修正 | §2.12 |",
            "| 3 | V41 修正：通知已读 HTTP 方法统一为 PUT /api/v1/notifications/:id/read，与前端 V20 §4.6 保持一致 | 已修正 | - | ✅ V41 | §2.12 |"
        )

    if "| 通知已读 | PATCH /api/v1/notifications/:id/read | PATCH /notifications/:id/read | ✅ |" in line:
        lines[i] = line.replace(
            "| 通知已读 | PATCH /api/v1/notifications/:id/read | PATCH /notifications/:id/read | ✅ |",
            "| 通知已读 | PUT /api/v1/notifications/:id/read | PUT /notifications/:id/read | ✅ |"
        )

    # 18. Comparison table - users.role (line 3322)
    if "users.role | str (user/admin/system_admin)" in line:
        lines[i] = line.replace(
            "| users.role | str (user/admin/system_admin) | user_role enum (user/admin/system_admin) | ✅ |",
            "| users.role | str (user/admin) | user_role enum (user/admin) | ✅ |"
        )

    # 19. sender_type comparison (line 3272)
    if "group_messages.sender_type 枚举不一致" in line and "human/agent" in line:
        lines[i] = line.replace(
            "| 3 | group_messages.sender_type 枚举不一致：架构 human/agent，后端 V37 user/agent/system | 不一致 | 改为 user/agent（与数据库 V30 一致），新增 sender_agent_name 字段以支持 Agent 名称记录 | ✅ 已修正 | §4.8, §5.2.10 |",
            "| 3 | V41 修正：group_messages.sender_type 统一为 user/agent/system，与数据库 V33 §1.3 保持一致 | 已修正 | - | ✅ V41 | §4.8, §5.2.10 |"
        )

# Write output
with open(dst, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("V41 第二遍修正完成")
print(f"Total lines: {len(lines)}")
