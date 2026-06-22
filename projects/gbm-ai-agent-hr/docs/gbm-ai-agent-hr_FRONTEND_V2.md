# GBM AI Agent HR 智能人力管理系统 — 前端设计文档 (V2)

## 版本信息

| 版本号 | 日期 | 作者 | 说明 |
|--------|------|------|------|
| 2.0 | 2026-06-13 | 后旺 | 基于 SRS V15 生成前端设计 |

---

## 目录

1. 前端技术栈
2. 项目结构
3. 路由设计
4. 状态管理
5. 组件架构
6. 页面布局
7. 移动端设计
8. 通用组件库
9. 国际化
10. 无障碍

---

## 1. 前端技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | Vue 3 | 3.4+ | 核心框架 |
| 语言 | TypeScript | 5.x | 类型安全 |
| 构建 | Vite | 5.x | 构建工具 |
| UI 框架 | Element Plus | 2.9+ | 组件库 |
| 状态管理 | Pinia | 2.2+ | 全局状态 |
| 路由 | Vue Router | 4.x | 页面路由 |
| HTTP 客户端 | Axios | 1.x | API 请求 |
| 图表 | ECharts | 5.x | 数据可视化 |
| 富文本 | WangEditor | 5.x | 富文本编辑器 |
| 文件上传 | 自定义 + Element Plus | — | 多文件拖拽上传 |
| 视频播放 | Video.js | 8.x | 培训视频播放 |
| 打印 | html2pdf.js | — | 证明/报告 PDF 导出 |
| 移动端 | UniApp | 3.x | 跨平台移动端 |
| 扫码 | wechat-jssdk / html5-qrcode | — | 扫码签到 |
| 签名 | signature_pad | — | 手写签名 |
| 代码规范 | ESLint + Prettier | — | 代码质量 |
| CSS 预处理 | Sass | — | 样式预编译 |
| 动画 | Vue Transition + Animate.css | — | 过渡动画 |
| 单元测试 | Vitest | 2.x | 单元测试 |
| E2E 测试 | Playwright | — | 端到端测试 |

---

## 2. 项目结构

```
gbm-ai-agent-hr-frontend/
├── public/                          # 静态资源
│   ├── favicon.ico
│   └── logo.png
├── src/
│   ├── api/                         # API 接口层
│   │   ├── index.ts                 # Axios 实例配置
│   │   ├── recruitment.ts           # 招聘相关 API
│   │   ├── onboarding.ts            # 入职相关 API
│   │   ├── training.ts              # 培训相关 API
│   │   ├── attendance.ts            # 考勤相关 API
│   │   ├── payroll.ts               # 薪资相关 API
│   │   ├── performance.ts           # 绩效相关 API
│   │   ├── external.ts              # 外务相关 API
│   │   ├── certificate.ts           # 证明相关 API
│   │   ├── system.ts                # 系统管理 API
│   │   └── analytics.ts             # 数据分析 API
│   ├── assets/                      # 静态资源
│   │   ├── images/
│   │   ├── styles/
│   │   │   ├── global.scss          # 全局样式
│   │   │   ├── variables.scss       # 变量定义
│   │   │   └── mixins.scss          # 样式混入
│   │   └── icons/
│   ├── components/                  # 通用组件
│   │   ├── common/
│   │   │   ├── GbmTable.vue         # 封装表格组件
│   │   │   ├── GbmForm.vue          # 封装表单组件
│   │   │   ├── GbmSearchBar.vue     # 搜索栏组件
│   │   │   ├── GbmFileUpload.vue    # 文件上传组件
│   │   │   ├── GbmSignaturePad.vue  # 手写签名组件
│   │   │   ├── GbmVideoPlayer.vue   # 视频播放器
│   │   │   ├── GbmQRCode.vue        # 二维码组件
│   │   │   ├── GbmDataExport.vue    # 数据导出组件
│   │   │   └── GbmAuditLogViewer.vue # 审计日志查看器
│   │   └── business/
│   │       ├── ResumeCard.vue       # 简历卡片
│   │       ├── ScoreRadar.vue       # 评分雷达图
│   │       ├── ExamPaper.vue        # 试卷组件
│   │       ├── PayrollSheet.vue     # 工资条组件
│   │       └── TimelineViewer.vue   # 时间线组件
│   ├── composables/                 # 组合式函数
│   │   ├── useApi.ts                # API 请求封装
│   │   ├── usePermission.ts         # 权限判断
│   │   ├── usePagination.ts         # 分页逻辑
│   │   ├── useExport.ts             # 导出逻辑
│   │   └── useWebSocket.ts          # WebSocket 连接
│   ├── directives/                  # 自定义指令
│   │   ├── permission.ts            # v-permission 权限指令
│   │   └── debounce.ts              # v-debounce 防抖指令
│   ├── layouts/                     # 布局组件
│   │   ├── DefaultLayout.vue        # 默认后台布局
│   │   ├── BlankLayout.vue          # 空白布局（登录/考试）
│   │   └── MobileLayout.vue         # 移动端布局
│   ├── router/                      # 路由配置
│   │   ├── index.ts                 # 路由入口
│   │   ├── modules/                 # 路由模块
│   │   │   ├── recruitment.ts
│   │   │   ├── onboarding.ts
│   │   │   ├── training.ts
│   │   │   ├── attendance.ts
│   │   │   ├── payroll.ts
│   │   │   ├── performance.ts
│   │   │   ├── external.ts
│   │   │   ├── certificate.ts
│   │   │   ├── system.ts
│   │   │   └── analytics.ts
│   │   └── guards.ts                # 路由守卫
│   ├── stores/                      # Pinia 状态管理
│   │   ├── modules/
│   │   │   ├── user.ts              # 用户状态
│   │   │   ├── permission.ts        # 权限状态
│   │   │   ├── app.ts               # 应用状态
│   │   │   ├── recruitment.ts       # 招聘状态
│   │   │   ├── training.ts          # 培训状态
│   │   │   ├── payroll.ts           # 薪资状态
│   │   │   └── notification.ts      # 通知状态
│   │   └── index.ts
│   ├── views/                       # 页面视图
│   │   ├── login/
│   │   │   └── Login.vue
│   │   ├── dashboard/
│   │   │   └── Dashboard.vue
│   │   ├── recruitment/
│   │   │   ├── JobPosting.vue
│   │   │   ├── ResumeList.vue
│   │   │   ├── ResumeDetail.vue
│   │   │   ├── ExamGeneration.vue
│   │   │   ├── ScoreManagement.vue
│   │   │   └── TalentPool.vue
│   │   ├── onboarding/
│   │   │   ├── OnboardingPortal.vue
│   │   │   ├── DocumentUpload.vue
│   │   │   ├── FaceCapture.vue
│   │   │   ├── ESignature.vue
│   │   │   └── OnboardingProgress.vue
│   │   ├── training/
│   │   │   ├── TrainingPlan.vue
│   │   │   ├── SignIn.vue
│   │   │   ├── ExamOnline.vue
│   │   │   ├── CertificateManage.vue
│   │   │   ├── VideoLibrary.vue
│   │   │   └── AuditPackage.vue
│   │   ├── attendance/
│   │   │   ├── AttendanceDashboard.vue
│   │   │   ├── AttendanceRecord.vue
│   │   │   ├── AnomalyList.vue
│   │   │   └── ShiftManage.vue
│   │   ├── payroll/
│   │   │   ├── PayrollCalculation.vue
│   │   │   ├── PayrollReview.vue
│   │   │   ├── Payslip.vue
│   │   │   └── SalaryRuleConfig.vue
│   │   ├── performance/
│   │   │   ├── PerformanceCycle.vue
│   │   │   ├── SelfAssessment.vue
│   │   │   ├── ManagerReview.vue
│   │   │   └── PerformanceReport.vue
│   │   ├── external/
│   │   │   ├── InjuryCase.vue
│   │   │   ├── HousingFund.vue
│   │   │   └── RpaStatus.vue
│   │   ├── certificate/
│   │   │   ├── SelfService.vue
│   │   │   └── CertificateReview.vue
│   │   ├── system/
│   │   │   ├── UserManage.vue
│   │   │   ├── RoleManage.vue
│   │   │   ├── DeptManage.vue
│   │   │   ├── AgentMonitor.vue
│   │   │   ├── AuditLog.vue
│   │   │   └── SystemConfig.vue
│   │   └── analytics/
│   │       ├── HrDashboard.vue
│   │       ├── ReportCenter.vue
│   │       └── ModelEvaluation.vue
│   ├── utils/                       # 工具函数
│   │   ├── request.ts               # Axios 封装
│   │   ├── storage.ts               # 本地存储
│   │   ├── validate.ts              # 表单校验
│   │   ├── format.ts                # 数据格式化
│   │   ├── permission.ts            # 权限工具
│   │   └── i18n.ts                  # 多语言工具
│   ├── types/                       # TypeScript 类型定义
│   │   ├── api.d.ts                 # API 类型
│   │   ├── module/
│   │   │   ├── recruitment.d.ts
│   │   │   ├── employee.d.ts
│   │   │   ├── attendance.d.ts
│   │   │   ├── payroll.d.ts
│   │   │   └── performance.d.ts
│   │   └── global.d.ts
│   ├── plugins/                     # 插件配置
│   │   ├── element-plus.ts
│   │   ├── echarts.ts
│   │   └── i18n.ts
│   ├── App.vue                      # 根组件
│   └── main.ts                      # 入口文件
├── tests/                           # 测试
│   ├── unit/
│   └── e2e/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── README.md
```

---

## 3. 路由设计

### 3.1 路由结构

```
/
├── /login                              # 登录
├── /dashboard                          # 工作台（默认首页）
├── /recruitment                        # 招聘管理
│   ├── /jobs                           # 职位发布
│   ├── /resumes                        # 简历管理
│   │   └── /:id                        # 简历详情
│   ├── /exams                          # 组卷管理
│   ├── /scores                         # 成绩管理
│   └── /talent-pool                    # 人才库
├── /onboarding                         # 入职管理
│   ├── /portal                         # 入职门户（新员工）
│   ├── /documents                      # 资料管理
│   ├── /face                           # 人脸采集
│   ├── /signature                      # 电子签名
│   └── /progress                       # 入职进度
├── /training                           # 培训管理
│   ├── /plan                           # 培训计划
│   ├── /signin                         # 签到管理
│   ├── /exam                           # 在线考试
│   ├── /certificates                   # 证书管理
│   ├── /videos                         # 视频库
│   └── /audit-package                  # 审核资料包
├── /attendance                         # 考勤管理
│   ├── /dashboard                      # 考勤总览
│   ├── /records                        # 考勤记录
│   ├── /anomalies                      # 异常管理
│   └── /shifts                         # 排班管理
├── /payroll                            # 薪资管理
│   ├── /calculation                    # 薪资核算
│   ├── /review                         # 薪资审核
│   ├── /payslip                        # 工资条
│   └── /rules                          # 薪资规则
├── /performance                        # 绩效管理
│   ├── /cycle                          # 考核周期
│   ├── /self                           # 自评
│   ├── /review                         # 上级审核
│   └── /report                         # 绩效报告
├── /external                           # 外务管理
│   ├── /injury                         # 工伤管理
│   ├── /fund                           # 公积金管理
│   └── /rpa-status                     # RPA 状态
├── /certificate                        # 证明管理
│   ├── /self-service                   # 自助申请
│   └── /review                         # 证明审核
├── /system                             # 系统管理
│   ├── /users                          # 用户管理
│   ├── /roles                          # 角色管理
│   ├── /departments                    # 部门管理
│   ├── /agent-monitor                  # Agent 监控
│   ├── /audit-log                      # 审计日志
│   └── /config                         # 系统配置
└── /analytics                          # 数据分析
    ├── /hr-dashboard                   # HR 看板
    ├── /reports                        # 报表中心
    └── /model-evaluation               # 模型评估
```

### 3.2 路由守卫

| 守卫 | 触发时机 | 逻辑 |
|------|---------|------|
| 全局前置守卫 | 每次路由切换前 | 检查 Token 有效性；未登录重定向到 /login |
| 权限守卫 | 进入受保护路由前 | 检查用户角色和权限码；无权限 403 |
| MFA 守卫 | 进入薪资/外务模块前 | 检查是否完成二因子认证 |
| 角色守卫 | 特定角色页面 | 员工只能访问自助页面，管理员才能访问管理页面 |

### 3.3 路由元信息

```typescript
interface RouteMeta {
  title: string;           // 页面标题
  icon: string;            // 菜单图标
  roles?: string[];        // 可访问角色
  permissions?: string[];  // 所需权限码
  requireMfa?: boolean;    // 是否需要 MFA
  keepAlive?: boolean;     // 是否缓存
  hidden?: boolean;        // 是否隐藏菜单
  breadcrumb?: string[];   // 面包屑路径
}
```

---

## 4. 状态管理

### 4.1 Pinia Store 架构

| Store | 职责 | 关键状态 |
|-------|------|---------|
| userStore | 用户信息 | userInfo, token, roles, permissions |
| permissionStore | 权限路由 | routes, menuList, isLoaded |
| appStore | 应用全局 | sidebarCollapsed, theme, language, isMobile |
| recruitmentStore | 招聘模块 | resumeList, currentJob, examData, filterParams |
| trainingStore | 培训模块 | trainingList, examPaper, videoList |
| payrollStore | 薪资模块 | payrollData, calculationResult, reviewStatus |
| notificationStore | 通知 | notificationList, unreadCount, wsConnected |

### 4.2 状态持久化

- Token、用户信息、语言偏好通过 pinia-plugin-persistedstate 持久化到 localStorage
- 敏感数据（薪资详情）不持久化，仅在 Session 中保留
- 退出登录时清除所有持久化状态

### 4.3 全局状态流

```
用户登录 → userStore.setToken() → 获取用户信息 → 获取权限 →
permissionStore.generateRoutes() → 动态添加路由 → 进入 Dashboard
```

---

## 5. 组件架构

### 5.1 组件分类

**基础组件（Common）：**
- GbmTable：封装 el-table，支持分页、排序、多选、列配置、导出
- GbmForm：封装 el-form，支持动态字段、校验规则、重置
- GbmSearchBar：组合搜索条件 + 查询/重置按钮
- GbmFileUpload：多文件拖拽上传，支持预览、进度、断点续传
- GbmSignaturePad：手写签名画板
- GbmVideoPlayer：视频播放器（Video.js 封装）
- GbmQRCode：二维码生成/扫描组件
- GbmDataExport：数据导出（Excel/CSV）
- GbmAuditLogViewer：审计日志查看面板

**业务组件（Business）：**
- ResumeCard：简历卡片展示
- ScoreRadar：多维评分雷达图
- ExamPaper：试卷展示与作答
- PayrollSheet：工资条展示
- TimelineViewer：业务流程时间线

### 5.2 组件通信

| 场景 | 方式 |
|------|------|
| 父子组件 | props / emit |
| 跨级组件 | provide / inject |
| 兄弟组件 | Pinia Store |
| 事件总线 | mitt（轻量发布订阅） |
| 实时推送 | WebSocket → notificationStore |

### 5.3 组件生命周期管理

- 定时器在 onUnmounted 中清理
- WebSocket 连接在页面切换时保持不断（全局单例）
- 大数据表格使用虚拟滚动（vxe-table）

---

## 6. 页面布局

### 6.1 后台管理布局 (DefaultLayout)

```
┌────────────────────────────────────────────────────┐
│  TopBar (60px)                                      │
│  ┌──────────┬─────────────────────┬───────────────┐ │
│  │ Logo     │ 面包屑导航           │ 用户菜单      │ │
│  │ GBM-HR   │ > 招聘 > 简历管理    │ 通知/头像/设置 │ │
│  └──────────┴─────────────────────┴───────────────┘ │
├────────┬───────────────────────────────────────────┤
│ SideBar│                                           │
│ (200px)│  Main Content Area                        │
│        │                                           │
│ ┌─────┐│  ┌──────────────────────────────────┐    │
│ │招聘管理│ │  Page Content                     │    │
│ ├─────┤│  └──────────────────────────────────┘    │
│ │入职管理│                                         │
│ ├─────┤│                                         │
│ │培训管理│                                         │
│ ├─────┤│                                         │
│ │考勤管理│                                         │
│ ├─────┤│                                         │
│ │薪资管理│  ───┐ Footer (fixed bottom)           │
│ ├─────┤│  ┌────┘                                │
│ │绩效管理│  │ Copyright © 2026 GBM              │
│ ├─────┤│  └───────────────────────────────────┐ │
│ │外务管理│                                    │ │
│ ├─────┤│                                    │ │
│ │证明管理│                                    │ │
│ ├─────┤│                                    │ │
│ │系统管理│                                    │ │
│ ├─────┤│                                    │ │
│ │数据分析│                                    │ │
│ └─────┘│                                    │ │
└────────┴───────────────────────────────────────────┘
```

### 6.2 布局特性

- **侧边栏**：可折叠（200px ↔ 64px），折叠后显示图标
- **顶部栏**：固定位置，包含面包屑和用户操作区
- **内容区**：scroll 独立滚动，不影响侧边栏和顶部栏
- **标签页**：支持多标签页打开（可选功能）
- **响应式**：手机端侧边栏自动隐藏，通过汉堡按钮切换

### 6.3 空白布局 (BlankLayout)

用于登录页、考试页、扫码签到页等不需要框架的页面。

### 6.4 移动端布局 (MobileLayout)

- 底部 TabBar 导航
- 顶部标题栏
- 全屏内容区

---

## 7. 移动端设计

### 7.1 移动端功能覆盖

| 功能 | 端 | 说明 |
|------|-----|------|
| 扫码签到 | 移动端 | 相机扫码，自动签到 |
| 工资条查看 | 移动端 | 查看/下载电子工资条 |
| 证明申请 | 移动端 | 选择证明类型，提交申请 |
| 培训视频 | 移动端 | 在线学习视频 |
| 考试作答 | 移动端 | 在线答题 |
| 请假/加班 | 移动端 | 提交申请 |
| 人脸采集 | 移动端 | 调用前置摄像头 |
| 消息通知 | 移动端 | 推送通知 |
| 简历上传 | 移动端 | 新员工上传资料 |

### 7.2 UniApp 页面结构

```
gbm-ai-agent-hr-mobile/
├── pages/
│   ├── index/          # 首页（待办列表）
│   ├── login/          # 登录
│   ├── signin/         # 扫码签到
│   ├── payslip/        # 工资条
│   ├── certificate/    # 证明申请
│   ├── training/       # 培训视频
│   ├── exam/           # 在线考试
│   ├── upload/         # 资料上传
│   ├── profile/        # 个人中心
│   └── message/        # 消息通知
├── static/             # 静态资源
├── store/              # Vuex 状态
├── utils/              # 工具函数
└── uni.scss            # 全局样式
```

---

## 8. 通用组件库

### 8.1 GbmTable 表格组件

```vue
<GbmTable
  :columns="columns"
  :data="tableData"
  :pagination="pagination"
  @page-change="handlePageChange"
  @sort-change="handleSortChange"
  :exportable="true"
  export-name="简历列表"
  :row-selectable="true"
  @selection-change="handleSelectionChange"
/>
```

特性：
- 列配置（宽度、排序、固定、隐藏）
- 分页（服务端/客户端）
- 多选
- 导出按钮
- 加载状态

### 8.2 GbmForm 表单组件

```vue
<GbmForm
  :fields="formFields"
  :rules="validationRules"
  :model="formData"
  layout="horizontal"
  :submit-text="'提交审核'"
  @submit="handleSubmit"
  @reset="handleReset"
/>
```

特性：
- 动态字段配置
- 校验规则
- 横向/纵向布局
- 自定义插槽

### 8.3 GbmFileUpload 文件上传

```vue
<GbmFileUpload
  :limit="10"
  :max-size="10"
  accept=".pdf,.jpg,.png,.doc,.docx"
  :drag="true"
  :preview="true"
  :show-progress="true"
  @success="handleSuccess"
  @error="handleError"
/>
```

特性：
- 拖拽上传
- 图片预览
- 进度条
- 文件大小/类型校验
- 断点续传

---

## 9. 国际化

### 9.1 语言支持

- 简体中文 (zh-CN) — 默认
- 英语 (en-US)

### 9.2 实现方案

```
src/
├── locales/
│   ├── zh-CN/
│   │   ├── common.json
│   │   ├── recruitment.json
│   │   ├── onboarding.json
│   │   └── ...
│   └── en-US/
│       ├── common.json
│       ├── recruitment.json
│       └── ...
```

- 使用 vue-i18n 9.x
- 语言切换实时生效（不刷新页面）
- 日期/数字格式随语言自动适配

### 9.3 翻译覆盖率要求

- 所有用户界面文本翻译覆盖率 ≥ 95%
- 中英双语一致性校验
- 每版本上线前执行双语全覆盖测试

---

## 10. 无障碍

### 10.1 遵循标准

WCAG 2.1 AA 级无障碍标准

### 10.2 实现要点

| 要求 | 实现方式 |
|------|---------|
| 屏幕阅读器 | 所有交互元素添加 aria-label、aria-describedby |
| 键盘操作 | Tab 遍历所有交互元素，Enter/Space 触发 |
| 色彩对比度 | 正文 ≥ 4.5:1，大文本 ≥ 3:1 |
| 缩放 | 放大至 200% 时布局不破坏 |
| 焦点管理 | 路由切换、弹窗打开时自动聚焦 |
| 表单标签 | 所有 input 关联 label 元素 |
| 图片替代文本 | 所有 img 添加 alt 属性 |

### 10.3 关键用户路径无障碍覆盖

以下路径须 100% 覆盖无障碍测试：
1. 用户登录与身份认证流程
2. 人事专员审核待办事项流程
3. 工资条查看与导出流程
4. 员工自助证明申请流程
5. 扫码签到流程

### 10.4 测试工具

- WAVE 浏览器插件 — 自动检测 A 级缺陷为 0，AA 级缺陷 ≤ 5
- axe 浏览器插件 — 辅助检测
- NVDA / JAWS — 屏幕阅读器手动测试
- 键盘操作覆盖率 100%

---

*文档结束*
