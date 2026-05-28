# DevFlow v4.0 全量重构 — 剩余任务执行计划

> **基于**: SRS_软件需求规格说明书.md v4.0
> **前期已完成**: Phase 1（数据库层）、Phase 2（服务层）、Phase 3（API文件创建）
> **本文档聚焦**: Task 3.5 + Phase 4 + Phase 5 + Phase 6

---

## 已完成任务回顾

| 任务 | 状态 | 产出 |
|------|------|------|
| Task 1.1-1.3: 数据库模型与迁移 | ✅ 完成 | agent.py(扩展), project.py(扩展), workflow_step.py, qa_record.py, swarm.py, security_audit.py, doc_version.py, enums.py, 3个迁移文件 |
| Task 2.1: 16步流程状态机引擎 | ✅ 完成 | workflow_engine.py + 23个测试 (全部通过) |
| Task 2.2: 命名Agent角色服务 | ✅ 完成 | agent_role_service.py + 18个测试 (全部通过) |
| Task 2.3: Agent蜂群管理服务 | ✅ 完成 | swarm_service.py + 11个测试 (全部通过) |
| Task 2.4: QA门控检验服务 | ✅ 完成 | qa_gate_service.py + 15个测试 (全部通过) |
| Task 3.1-3.4: API文件创建 | ✅ 完成 | workflow.py, qa.py, swarms.py, security.py |
| **Task 3.5: 注册新路由** | ⬜ 待完成 | 更新 api/__init__.py 和 main.py |
| **Phase 4: 前端核心页面** | ⬜ 待完成 | 5个子任务 |
| **Phase 5: WebSocket事件** | ⬜ 待完成 | 1个子任务 |
| **Phase 6: 集成测试** | ⬜ 待完成 | 2个子任务 |

测试总计: **68个测试全部通过**

---

## Task 3.5: 注册所有新路由到 main.py

**目标**: 将 workflow.py, qa.py, swarms.py, security.py 的路由注册到 FastAPI 应用

**文件**:
- Modify: `backend/app/api/__init__.py`
- Modify: `backend/app/main.py`

### Step 1: 在 api/__init__.py 中导出新路由器

检查现有 routers 导出模式，添加:
- `from app.api.workflow import router as workflow_router`
- `from app.api.qa import router as qa_router`
- `from app.api.swarms import router as swarms_router`
- `from app.api.security import router as security_router`

在 `routers` 列表中添加以上 router。

### Step 2: 验证 main.py 自动注册

检查 main.py 是否自动遍历 `routers` 列表，如果是自动注册则无需额外修改。

### Step 3: 验证应用启动

```bash
cd backend && python -c "from app.main import app; print('Routes:', [r.path for r in app.routes])"
```

---

## Phase 4: 前端核心页面

### Task 4.1: 16步流程进度视图 (WorkflowView)

**文件**:
- Create: `frontend/src/views/WorkflowView.vue`
- Create: `frontend/src/components/workflow/StepCard.vue`
- Create: `frontend/src/components/workflow/StepTimeline.vue`
- Create: `frontend/src/stores/useWorkflowStore.ts`

**Step 1: 编写组件测试用例**

```typescript
// 测试文件暂定在 frontend/src/__tests__/components/StepTimeline.spec.ts
describe('StepTimeline', () => {
  it('renders 16 steps', () => { ... })
  it('highlights current step in blue', () => { ... })
  it('shows passed steps in green', () => { ... })
  it('shows rejected steps in red', () => { ... })
  it('shows "QA检验中" for in-progress steps', () => { ... })
  it('emits click event when step is clicked', () => { ... })
})
```

**Step 2: 实现 Pinia Store (useWorkflowStore.ts)**

```typescript
// stores/useWorkflowStore.ts
// 管理16步流程状态
// - state: steps[], currentStep, projectId
// - actions: fetchWorkflow(), executeStep(stepNum), submitQA(stepNum, result)
// - getters: currentStepInfo, isQARequired, progressPercent
```

API 调用:
- `GET /api/projects/:id/progress` — 获取流程进度
- `POST /api/projects/:id/step{2..16}` — 执行某步
- `POST /api/qa/:task_id/inspect` — QA检验

**Step 3: 实现 StepTimeline 组件**

核心功能:
- 水平滚动时间线，16个步骤节点
- 颜色区分: pending(灰) → in_progress(蓝) → qa_review(橙) → passed(绿) → rejected(红) → completed(绿)
- 当前步骤带脉冲动画 `@keyframes pulse`
- 点击步骤可查看详情

**Step 4: 实现 StepCard 组件**

展示:
- 步骤名称和编号
- 执行者Agent（头像 + 角色名）
- 输入产出（来自上一步 artifacts）
- 本步产出（output_artifacts 展示）
- QA门控状态面板（检验维度、通过/失败、退回原因、修改建议）
- 操作按钮（执行步骤 / 提交QA检验）

**Step 5: 实现 WorkflowView 页面**

布局:
```
┌─────────────────────────────────────────────────────┐
│  StepTimeline (16步进度条，顶部固定)                  │
├─────────────────────────────────────────────────────┤
│  StepCard (当前步骤详情，中间主区域)                   │
│  ├─ 执行者信息                                       │
│  ├─ 输入/产出                                        │
│  └─ QA操作面板                                       │
├─────────────────────────────────────────────────────┤
│  历史步骤记录列表（底部）                              │
└─────────────────────────────────────────────────────┘
```

### Task 4.2: 项目讨论群视图升级

**文件**:
- Modify: `frontend/src/views/ChatView.vue` — 升级为项目讨论群视图
- Create: `frontend/src/components/chat/AgentMentionInput.vue`
- Create: `frontend/src/components/chat/MeetingLauncher.vue`
- Modify: `frontend/src/stores/useChatStore.ts`

**Step 1: AgentMentionInput 组件**

功能:
- 文本输入框中输入 `@` 触发 Agent 列表下拉
- 9个Agent角色全量可选（海梅/后兴/后旺/后发/后达/后富/后贵/后荣/后华）
- 选择Agent后高亮显示 `@Agent名称`
- 无 @mention 时默认全员可见

**Step 2: MeetingLauncher 组件**

功能:
- 会议类型选择: 需求评审会 / 技术方案讨论会 / 每日站会 / 故障复盘会
- 主持人设置（默认海梅）
- 会议时长设定
- 启动/停止会议按钮
- 会议状态指示器（进行中/已结束）

**Step 3: 讨论模式/会议模式状态切换**

在 ChatView 顶部添加模式切换器:
- 讨论模式: 自由发言，Agent状态指示器（typing/speaking/idle）
- 会议模式: 结构化议程，主持人控场，输出会议纪要

**Step 4: WebSocket 集成**

连接 `ws://{host}/ws/group-chat`:
- `subscribe` — 订阅群组消息
- `send_message` — 发送消息（支持 @mention）
- `start_meeting` / `stop_meeting` — 会议控制
- 监听: `message_new`, `message_chunk`, `meeting_started`, `meeting_phase`, `meeting_minutes`

### Task 4.3: Agent 蜂群管理视图 (SwarmView)

**文件**:
- Create: `frontend/src/views/SwarmView.vue`
- Create: `frontend/src/components/swarm/SwarmCreator.vue`
- Create: `frontend/src/components/swarm/SwarmProgress.vue`
- Create: `frontend/src/stores/useSwarmStore.ts`

**Step 1: 编写组件测试用例**

**Step 2: Pinia Store**

```typescript
// stores/useSwarmStore.ts
// - state: swarms[], currentSwarm, members[], tasks[]
// - actions: createSwarm(), addMember(), dispatchTasks(), fetchProgress(), disbandSwarm()
// - getters: activeSwarms, swarmByStep, codeWritingSwarms, testSwarms
```

**Step 3: SwarmCreator 组件**

功能:
- 蜂群名称输入
- 蜂群类型选择: 代码编写蜂群 / 测试蜂群
- 关联流程步骤（7=测试用例/9=功能代码/11=全面测试）
- 蜂群成员多选（9种Agent: Claude Code/Codex/Opencode/Cursor/CodeArts/Trae/Lingma/hermes子agent/pi-codeing-agent子agent）
- 创建按钮 + 验证（後发只能建代码蜂群，後达只能建测试蜂群）

**Step 4: SwarmProgress 组件**

功能:
- 蜂群总览卡片（成员数量、任务总数、完成数、进度百分比）
- 每个蜂群成员的任务进度条
- 实时进度更新（WebSocket 或轮询）

**Step 5: SwarmView 页面**

布局:
```
┌─────────────────────────────────────────────────────┐
│  SwarmCreator (创建蜂群面板)                          │
├─────────────────────────────────────────────────────┤
│  SwarmProgress (蜂群进度总览)                         │
├─────────────────────────────────────────────────────┤
│  MemberList (成员详情列表，含各自任务状态)             │
└─────────────────────────────────────────────────────┘
```

### Task 4.4: QA 门控面板 (QAView)

**文件**:
- Create: `frontend/src/views/QAView.vue`
- Create: `frontend/src/components/qa/InspectionForm.vue`
- Create: `frontend/src/components/qa/QAHistoryTable.vue`
- Create: `frontend/src/stores/useQAStore.ts`

**Step 1: Pinia Store**

```typescript
// stores/useQAStore.ts
// - state: records[], currentInspection, projectId
// - actions: fetchRecords(), submitInspection(), rollbackTask(), getStatus()
// - getters: passedCount, failedCount, recentRecords
```

**Step 2: InspectionForm 组件**

功能:
- 待检验产出列表（按步骤分组）
- 检验维度自动匹配（根据产出类型显示不同维度）
- 每个维度: 通过/不通过 开关
- 不通过时需填写问题详情和修改建议
- 提交检验按钮

**Step 3: QAHistoryTable 组件**

功能:
- 展示所有QA检验记录表格
- 列: 步骤号、产出类型、检验状态(passed/failed)、检验时间、查看详情
- 状态标签颜色: passed(绿) / failed(红)
- 点击查看详情弹窗（展示完整检验结果、问题详情、修改建议）
- 分页支持

**Step 4: QAView 页面**

布局:
```
┌─────────────────────────────────────────────────────┐
│  QA 统计卡片行 (总检验数/通过/失败/通过率)            │
├─────────────────────────────────────────────────────┤
│  InspectionForm (当前待检验产出)                      │
├─────────────────────────────────────────────────────┤
│  QAHistoryTable (历史检验记录)                        │
└─────────────────────────────────────────────────────┘
```

### Task 4.5: 更新路由与导航

**文件**:
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/components/common/AppSidebar.vue` (或等效的导航组件)

**Step 1: 新增路由**

```javascript
// frontend/src/router/index.js
{
  path: '/projects/:id/workflow',
  name: 'Workflow',
  component: () => import('@/views/WorkflowView.vue'),
  meta: { title: '16步流程', icon: 'timeline' }
},
{
  path: '/projects/:id/swarm',
  name: 'Swarm',
  component: () => import('@/views/SwarmView.vue'),
  meta: { title: 'Agent蜂群', icon: 'swarm' }
},
{
  path: '/projects/:id/qa',
  name: 'QA',
  component: () => import('@/views/QAView.vue'),
  meta: { title: 'QA门控', icon: 'shield-check' }
},
{
  path: '/projects/:id/chat',
  name: 'ProjectChat',
  component: () => import('@/views/ChatView.vue'),
  meta: { title: '项目讨论群', icon: 'chat' }
},
{
  path: '/projects/:id/security',
  name: 'SecurityAudit',
  component: () => import('@/views/WorkflowView.vue'), // 复用或新建
  meta: { title: '安全审计', icon: 'lock' }
}
```

**Step 2: 更新侧边导航**

在项目详情页的侧边栏中添加入口:
- 16步流程 (WorkflowView)
- 项目讨论群 (ChatView 升级版)
- Agent蜂群 (SwarmView)
- QA门控 (QAView)

### 依赖与顺序

```
Task 4.1 (WorkflowView) ────┐
Task 4.2 (ChatView升级) ────┤ 可并行进行
Task 4.3 (SwarmView)   ────┤
Task 4.4 (QAView)      ────┘
         ↓
Task 4.5 (路由导航) ← 依赖前4个任务的页面组件存在
```

---

## Phase 5: WebSocket 实时事件推送

### Task 5.1: 新增 SRS §7.2 全部 WebSocket 事件

**文件**:
- Modify: `backend/app/ws/events.py`
- Modify: `backend/app/ws/manager.py`
- Modify: `backend/app/ws/broadcast.py`

**Step 1: 定义新事件常量**

```python
# backend/app/ws/events.py
# 16步流程进展事件
PROJECT_STEP_STARTED = "project.step.started"        # 步骤开始
PROJECT_STEP_COMPLETED = "project.step.completed"    # 步骤完成
PROJECT_STEP_FAILED = "project.step.failed"          # 步骤失败

# QA门控事件
QA_INSPECTION_PASSED = "qa.inspection.passed"        # QA检验通过
QA_INSPECTION_FAILED = "qa.inspection.failed"        # QA检验未通过

# 蜂群事件
SWARM_CREATED = "swarm.created"                      # 蜂群建立
SWARM_DISBANDED = "swarm.disbanded"                  # 蜂群解散
SWARM_TASK_DISPATCHED = "swarm.task.dispatched"      # 任务分发
SWARM_TASK_COMPLETED = "swarm.task.completed"         # 任务完成
SWARM_PROGRESS_UPDATED = "swarm.progress.updated"    # 进度更新

# 安全审计事件
SECURITY_AUDIT_STARTED = "security.audit.started"    # 审计开始
SECURITY_AUDIT_COMPLETED = "security.audit.completed" # 审计完成
SECURITY_AUDIT_FAILED = "security.audit.failed"      # 审计失败

# 项目级事件
PROJECT_COMPLETED = "project.completed"              # 项目完成
TASK_ASSIGNED = "task.assigned"                      # 任务分配
TASK_STATUS_CHANGED = "task.status.changed"          # 任务状态变更
```

**Step 2: 扩展 ConnectionManager**

在 `manager.py` 中添加按项目ID分组的连接管理:
- `subscribe_project(project_id, connection)` — 订阅项目事件
- `unsubscribe_project(project_id, connection)` — 取消订阅
- `broadcast_to_project(project_id, event, data)` — 向项目所有订阅者广播

**Step 3: 集成到现有服务**

在以下服务方法中添加 `broadcast_to_project` 调用:
- `workflow_engine.py`: `complete_step()`, `pass_qa()`, `fail_qa()` 方法末尾
- `swarm_service.py`: `create_swarm()`, `dispatch_tasks()`, `disband_swarm()` 方法末尾

### 测试覆盖

```python
# tests/test_websocket_events.py (扩展)
async def test_project_step_started_event():
    """测试步骤开始时推送 WebSocket 事件"""
    
async def test_qa_inspection_passed_event():
    """测试QA检验通过时推送事件"""

async def test_swarm_progress_updated_event():
    """测试蜂群进度更新时推送事件"""
```

---

## Phase 6: 集成测试与验收

### Task 6.1: 全流程集成测试

**文件**:
- Create: `backend/tests/test_full_v4_workflow.py`

**Step 1: 编写测试用例**

```python
class TestFullV4Workflow:
    async def test_complete_16_step_flow(self):
        """测试：从项目创建到交付完成的完整16步流程"""
        # Step 1: 创建项目 → Gitea仓库自动创建
        # Step 2: 海梅确认核心目标 → QA通过 → 群组建立
        # Step 3: 后兴需求分析 → QA通过 → SRS提交代码库
        # Step 4: 后旺架构设计(4份设计文档逐份检验) → QA通过 → 提交代码库
        # Step 5: 后富开发环境 → QA通过
        # Step 6: 海梅TDD计划 → QA通过 → 提交代码库
        # Step 7: 后发蜂群TDD测试用例 → QA逐用例检验 → 提交代码库
        # Step 8: 海梅代码编写计划+依赖图 → QA通过 → 提交代码库
        # Step 9: 后发蜂群按依赖图编写功能代码 → QA逐任务检验 → 提交代码库
        # Step 10: 后富部署测试环境
        # Step 11: 后达蜂群全面测试 → QA通过 → 测试报告提交
        # Step 12: 后华安全审计 → QA通过 → 审计报告提交
        # Step 13: 后富部署生产环境
        # Step 14: 后贵文档完善+一致性校验
        # Step 15: 海梅交付报告
        # Step 16: 用户满意 → 项目结束 → 代码库打版本标签
    
    async def test_iteration_loop_step16_to_step3(self):
        """测试：第16步不满意→回到第3步重新迭代"""
        # 完成完整流程 → 第16步用户不满意
        # → current_step 重置为 3
        # → 步骤1-2的产出保留
        # → 步骤3-16状态重置
        # → 用户修改意见记录在案
    
    async def test_qa_rejection_mid_flow(self):
        """测试：中间步骤QA驳回→退回重做→重新检验通过"""
        # 第4步后旺设计 → QA检验 → 不合格（架构不合理）
        # → 步骤状态变为 rejected，附带修改建议
        # → 后旺修改 → 重新提交 → QA再检验 → 通过
    
    async def test_swarm_parallel_execution(self):
        """测试：蜂群并行执行任务"""
        # 后发建立代码蜂群(3个Agent)
        # → 分发5个原子化任务（按技能匹配+依赖图顺序）
        # → 3个Agent并行执行
        # → 收集成果 → 逐个提交QA
    
    async def test_dependency_graph_enforcement(self):
        """测试：任务依赖图强制顺序"""
        # 任务A → 任务B → 任务C (有向无环)
        # B必须在A通过QA后才能开始
        # C必须在B通过QA后才能开始
        # 验证: 跳过依赖直接执行后继任务应失败
    
    async def test_doc_consistency_enforcement(self):
        """测试：文档一致性强制校验"""
        # 代码修改后 → 后贵检测到不一致
        # → 列出需同步修改的文档
        # → 逐一修改 → 重新校验一致性
    
    async def test_concurrent_projects(self):
        """测试：多个项目并发执行"""
        # 创建3个项目 → 并行执行各自流程
        # → 每个项目的步骤状态独立
        # → 互不干扰
    
    async def test_full_qa_traceability(self):
        """测试：QA检验记录完整可追溯"""
        # 模拟完整流程
        # → 验证每个QA步骤都有检验记录
        # → 验证检验记录包含: 检验维度、结果、问题详情、修改建议
```

### Task 6.2: 前端 E2E 测试

**文件**:
- Create: `frontend/tests/e2e/workflow.spec.ts`

**测试场景** (使用 Playwright):

```typescript
test('user can create project and view 16-step workflow', async () => {
  // 1. 登录系统
  // 2. 创建新项目
  // 3. 导航到项目 → 查看 WorkflowView
  // 4. 验证16步时间线显示
  // 5. 验证当前步骤高亮
})

test('user can trigger step execution', async () => {
  // 1. 进入项目 WorkflowView
  // 2. 点击 "执行第二步"
  // 3. 验证步骤状态变为 in_progress → qa_review
  // 4. 验证 StepCard 展示正确信息
})

test('QA inspection can pass/fail a step', async () => {
  // 1. 进入 QAView
  // 2. 选择一个待检验产出
  // 3. 逐维度检验 → 全部通过
  // 4. 验证产出状态变为 passed
  // 5. 再检验一个 → 部分不通过
  // 6. 验证退回重做状态和修改建议展示
})

test('Swarm creation and task dispatch', async () => {
  // 1. 进入 SwarmView
  // 2. 创建代码编写蜂群（添加3个成员）
  // 3. 分发任务
  // 4. 验证任务分配到不同成员
  // 5. 查看蜂群进度
})

test('Discussion group messaging with @mention', async () => {
  // 1. 进入项目讨论群 (ChatView)
  // 2. 输入 @后兴 发送消息
  // 3. 验证消息发送成功
  // 4. 切换会议模式
  // 5. 验证会议状态变更
})
```

---

## 实施顺序总结

```
Task 3.5 (路由注册) ──→ 验证后端API全部可用
         ↓
Phase 4 (前端页面) ──→ 4.1/4.2/4.3/4.4 可并行 → 4.5 路由导航
         ↓
Phase 5 (WebSocket) ──→ 实时事件推送
         ↓
Phase 6 (集成测试) ──→ 6.1 后端全流程测试 → 6.2 前端E2E
```

---

## 验证命令

```bash
# 后端测试
cd backend && python -m pytest tests/ -v --override-ini="addopts="

# 前端测试
cd frontend && npm run test

# 前端E2E
cd frontend && npx playwright test

# 应用启动验证
cd backend && python -c "from app.main import app; print('OK')"
```