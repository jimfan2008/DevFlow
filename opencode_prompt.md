# DevFlow 前端完整实现指令

## 项目概述
DevFlow 是一个面向小型团队(3-20人)的轻量级项目管理平台 MVP。
核心功能：看板视图、任务依赖管理、人员负载分析、个人收件箱。

## 当前状态
- 后端 FastAPI：已完整实现 ✅
- 测试：已有完整测试套件 ✅
- 前端类型定义 `src/types/api.ts`：已完整定义 ✅
- 前端 API 层 `src/api/index.ts`：已完整实现 ✅
- 前端路由 `src/router/index.js`：已配置 ✅
- 前端样式系统 `src/assets/styles/`：完整 SCSS 变量 ✅
- **前端 Views/Components/Stores：全部缺失，需要从零实现** ❌

## 技术栈
- Vue 3 (Composition API + <script setup>)
- Element Plus
- Pinia (状态管理)
- Vue Router 4
- Axios (HTTP)
- ECharts (图表)
- date-fns (日期)
- vee-validate + zod (表单验证)
- Vite 5 (构建)
- TypeScript
- markdown-it (Markdown 解析)

## 必须实现的代码清单

### Stores (5个)
1. src/stores/useAuthStore.ts - 认证（登录/注册/Token/用户信息/登出）
2. src/stores/useBoardStore.ts - 看板（列表/详情/列管理）
3. src/stores/useTaskStore.ts - 任务（列表/详情/增删改/批量移动）
4. src/stores/useInboxStore.ts - 收件箱（通知列表/标记已读/未读计数）
5. src/stores/useWebSocketStore.ts - WebSocket 实时连接

### Views (7个)
1. src/views/LoginView.vue - 登录页面
2. src/views/RegisterView.vue - 注册页面
3. src/views/BoardView.vue - 看板列表+看板详情（拖拽看板）
4. src/views/TaskDetailView.vue - 任务详情
5. src/views/InboxView.vue - 收件箱
6. src/views/ProfileView.vue - 个人资料
7. src/views/NotFoundView.vue - 404页面

### Common Components (5个)
1. src/components/common/AppHeader.vue - 顶部导航栏（Logo、搜索、通知铃铛、用户菜单）
2. src/components/common/AppSidebar.vue - 侧边栏（菜单、负载热力图）
3. src/components/common/BoardCard.vue - 看板卡片
4. src/components/common/EmptyState.vue - 空状态
5. src/components/common/ConfirmDialog.vue - 确认对话框

### Board Components (5个)
1. src/components/boards/KanbanBoard.vue - 看板主体（拖拽交互）
2. src/components/boards/KanbanColumn.vue - 看板列
3. src/components/boards/KanbanCard.vue - 任务卡片
4. src/components/boards/CreateBoardDialog.vue - 新建看板对话框
5. src/components/boards/EditColumnDialog.vue - 编辑列对话框

### Task Components (3个)
1. src/components/tasks/TaskDetailPanel.vue - 任务详情面板（侧边抽屉）
2. src/components/tasks/TaskForm.vue - 任务编辑表单
3. src/components/tasks/TaskDependencyList.vue - 依赖关系列表

### Inbox Components (2个)
1. src/components/inbox/InboxList.vue - 通知列表
2. src/components/inbox/InboxFilter.vue - 筛选器

### Workload Components (2个)
1. src/components/workload/WorkloadChart.vue - 负载热力图（ECharts）
2. src/components/workload/WorkloadBadge.vue - 负载状态徽标

### UI Components (2个)
1. src/components/ui/PriorityBadge.vue - 优先级标签
2. src/components/ui/StatusBadge.vue - 状态标签

## 关键设计要求

### 1. Pinia Stores
- useAuthStore: state(user, accessToken, refreshToken, isAuthenticated), actions(login, register, refresh, logout, fetchUser)
- useBoardStore: state(boardList, currentBoard, columns), actions(fetchList, fetchDetail, create, update, delete, manageColumns)
- useTaskStore: state(taskList, currentTask, loading), actions(fetchList, fetchDetail, create, update, delete, bulkMove)
- useInboxStore: state(notifications, unreadCount), actions(fetchList, markRead, fetchUnreadCount)
- useWebSocketStore: 建立WS连接，监听task.updated/task.created/task.deleted/board.updated/status.changed，断线重连

### 2. 看板页面 (BoardView.vue)
- 看板列表：el-card 网格布局
- 看板详情：el-row 横向列，el-col 纵向任务卡片
- 拖拽任务卡片到不同列（使用 HTML5 drag & drop）
- 拖拽完成后调用 taskApi.bulkMove
- 每列底部"添加任务"按钮

### 3. 任务卡片 (KanbanCard.vue)
- 标题、优先级标签、负责人、截止日期、阻塞标识
- 点击打开 TaskDetailPanel 抽屉
- hover 显示操作按钮

### 4. 任务详情 (TaskDetailPanel.vue)
- el-drawer 侧边抽屉，Tab页签（详情/评论/依赖）
- 评论支持 markdown 显示
- 依赖关系展示前置/后置任务

### 5. API 对接
- 所有调用通过 src/api/index.ts 的 API 对象
- 统一响应格式：{ code, message, data, errors }
- 错误处理：el-message.error
- 异步操作有 loading 状态

### 6. 样式
- 使用 src/assets/styles/variables.scss 的 SCSS 变量
- 响应式设计
- 页面切换动画

## 实现顺序
1. stores（5个）
2. UI 组件（PriorityBadge, StatusBadge, EmptyState, ConfirmDialog）
3. 布局组件（AppHeader, AppSidebar）
4. Views（7个）
5. 业务组件（Kanban系列、Task系列、Inbox系列、Workload系列）
6. 确保所有 import 路径正确
7. 确保 App.vue 引用正确

## 必须遵守
1. 禁止伪代码，必须完整可运行
2. 所有 API 调用有错误处理
3. 所有表单有验证
4. 所有异步操作有 loading 状态
5. 使用 TypeScript 类型安全
6. 使用 <script setup> 语法
7. 中文注释
8. 遵循 Element Plus 规范
9. 看板拖拽平滑流畅
