# GBM AI Agent HR 智能人力管理系统 — 前端设计文档 (V10)

## 版本信息

| 字段 | 值 |
|------|-----|
| 文档名称 | GBM AI Agent HR 前端设计文档 |
| 版本号 | V10.0 |
| 基于 SRS | V15.0 |
| 日期 | 2026-06-12 |
| 作者 | 后旺 (HouWang) |
| 角色 | 前端架构师 |

## 修订说明

V9.0→V10.0：根据后荣检验报告修复以下问题：
1. 解决 Zustand 与 React Query 职责定义自相矛盾：移除 stores/ 目录下 7 个业务模块 store（recruitmentStore、onboardingStore、trainingStore、attendanceStore、payrollStore、performanceStore、agentStore），Zustand 仅保留 authStore.ts（认证 UI 状态）和 uiStore.ts（全局 UI 状态），所有业务数据统一由 React Query 管理
2. 补充完整文档内容：确保所有章节（第 1-11 章）完整无缺失
3. 明确分片上传实现方案：Ant Design Upload 仅提供 UI 外壳，分片逻辑（文件切割、MD5 校验、断点续传）由自定义 useFileUpload Hook 实现
4. 补充 ECharts 骨架屏与预加载策略：Dashboard 加载 ECharts 模块时显示骨架屏，用户首次登录后预加载 ECharts chunk
5. 确认 @axe-core/react 仅开发环境集成与 SRS V15.0 无障碍合规要求的关系
6. 修正 @dnd-kit 版本号：8.x 修正为 6.x（当前最新稳定版本）

---

## 目录

1. 前端技术栈
2. 项目结构
3. 路由设计
4. 状态管理
5. 组件体系
6. 页面布局设计
7. 关键页面设计
8. 无障碍访问设计
9. 国际化设计
10. PWA 与移动端设计
11. 安全与性能

---

## 1. 前端技术栈

### 1.1 核心技术

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| 语言 | TypeScript | 5.x | 类型安全 |
| 框架 | React | 18.x | 组件化 UI 框架 |
| UI 组件库 | Ant Design | 5.x | 企业级组件库 |
| CSS 方案 | Ant Design 5.x Token | - | 使用 Ant Design ConfigProvider 管理全局 Design Token |
| 路由 | React Router | 6.x | 声明式路由 |
| 状态管理 | Zustand | 4.x | 轻量级状态管理 |
| HTTP 客户端 | Axios | 1.x | 请求封装与拦截 |
| 国际化 | i18next + react-i18next | - | 中/英双语 |
| 构建工具 | Vite | 5.x | 快速构建 |
| 测试 | Vitest + Testing Library | - | 单元测试 |
| 表单 | react-hook-form + zod | - | 表单验证 |
| 数据表格 | Ant Design Table | 5.x | 内置高级表格 |
| 数据请求 | @tanstack/react-query | 5.x | 服务端状态管理（替代自定义 useApi） |
| 图表 | ECharts | 5.x | 数据可视化 |
| 文件上传 | Ant Design Upload + 自定义分片逻辑 | 5.x | Ant Design Upload 提供 UI 外壳，分片逻辑由自定义 Hook 实现 |
| PDF 预览 | react-pdf | - | 在线预览 PDF |
| 电子签名 | react-signature-canvas | - | 手写签名 |
| 无障碍 | @axe-core/react | - | 无障碍检测（仅开发环境） |
| PWA | workbox | 7.x | Service Worker |
| 日期选择 | dayjs | 2.x | 轻量日期库 |
| 拖拽 | @dnd-kit/core + @dnd-kit/sortable | 6.x (V10.0: 修正为最新稳定版本 6.x) | 拖拽排序（react-beautiful-dnd 已废弃） |
| 通知 | Ant Design Notification | 5.x | 消息通知 |

### 1.1.1 依赖加载策略

| 类别 | 加载方式 | 包含包 |
|------|---------|--------|
| 核心依赖 | 首屏加载 | React, Ant Design, React Router, Zustand, Axios, @tanstack/react-query, dayjs |
| 按需加载 | React.lazy 动态导入 | react-pdf, react-signature-canvas, ECharts (V9.0: ECharts 约 800KB+ gzip，仅在 Dashboard 和报表页面按需加载) |

**构建期配置说明：**
- **workbox (PWA)**：Service Worker 为构建时注册的独立脚本，由 Vite 插件在构建阶段生成，非运行时条件导入
- **@axe-core/react (无障碍)**：开发期集成到 React 组件树中的检测工具，仅开发环境生效，不包含在生产构建中。SRS V15.0 要求无障碍合规（WCAG 2.1 AA），合规性通过代码规范、aria 属性、键盘操作支持等实现，而非依赖运行时无障碍检测工具

### 1.2 设计规范

- **设计系统**：Ant Design 5.x Token 系统，通过 ConfigProvider 管理全局 Design Token
- **色彩规范**：主色 #1890FF，辅助色 #52C41A（成功）、#FAAD14（警告）、#FF4D4F（错误）
- **字体**：Inter (英文) + PingFang SC / Microsoft YaHei (中文)
- **间距**：8px 基准网格系统
- **圆角**：4px (小)、8px (中)、12px (大)
- **阴影**：Ant Design 默认 elevation 层级

---

## 2. 项目结构

```
gbm-ai-agent-hr-frontend/
├── public/
│   ├── favicon.ico
│   ├── manifest.json              # PWA manifest
│   └── robots.txt
├── src/
│   ├── assets/                    # 静态资源
│   │   ├── images/
│   │   ├── icons/                 # SVG 图标
│   │   └── styles/
│   │       └── global.css  # V9.0: 仅保留非 Ant Design 覆盖的定制样式，reset.css 已移除
│   ├── components/                # 通用组件
│   │   ├── common/
│   │   │   ├── AppHeader.tsx
│   │   │   ├── AppSider.tsx
│   │   │   ├── AppFooter.tsx
│   │   │   ├── BreadcrumbNav.tsx
│   │   │   ├── SearchBar.tsx
│   │   │   ├── UserAvatar.tsx
│   │   │   ├── NotificationBell.tsx
│   │   │   ├── LanguageSwitcher.tsx
│   │   │   ├── ThemeToggle.tsx
│   │   │   └── LoadingSpinner.tsx
│   │   ├── data/
│   │   │   ├── DataTable.tsx      # 可复用数据表格
│   │   │   ├── SearchFilter.tsx   # 搜索筛选器
│   │   │   ├── PaginationBar.tsx  # 分页栏
│   │   │   ├── ExportButton.tsx   # 导出按钮
│   │   │   └── ImportDialog.tsx   # 导入对话框
│   │   ├── form/
│   │   │   ├── FormCard.tsx
│   │   │   ├── StepForm.tsx       # 分步表单
│   │   │   ├── FileUpload.tsx     # 文件上传（Ant Design Upload + 自定义分片 Hook）
│   │   │   ├── ImageCropper.tsx   # 图片裁剪
│   │   │   ├── SignaturePad.tsx   # 电子签名
│   │   │   └── DatePickerRange.tsx
│   │   ├── feedback/
│   │   │   ├── ConfirmDialog.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   └── ErrorBoundary.tsx
│   │   └── layout/
│   │       ├── MainLayout.tsx     # 主布局
│   │       ├── PageHeader.tsx
│   │       ├── CardContainer.tsx
│   │       ├── TabContainer.tsx
│   │       ├── BottomTabBar.tsx   # 移动端底部 Tab 栏
│   │       └── MobileLayout.tsx   # 移动端布局
│   ├── hooks/                     # 自定义 Hooks
│   │   ├── useAuth.ts
│   │   ├── usePermission.ts
│   │   ├── usePagination.ts
│   │   ├── useDebounce.ts
│   │   ├── useLocalStorage.ts
│   │   ├── useNotification.ts
│   │   ├── useFileUpload.ts       # 分片上传逻辑（文件切割、MD5 校验、断点续传）
│   │   └── useChartPreload.ts     # V10.0: ECharts 预加载 Hook
│   ├── stores/                    # Zustand 状态存储 (V10.0: 仅保留 UI 交互状态)
│   │   ├── authStore.ts           # 认证 UI 状态（isAuthenticated、user、roles、permissions）
│   │   └── uiStore.ts             # 全局 UI 状态（侧栏折叠、主题、语言、通知、面包屑）
│   ├── services/                  # API 服务层
│   │   ├── apiClient.ts           # Axios 实例配置
│   │   ├── authService.ts
│   │   ├── recruitmentService.ts
│   │   ├── onboardingService.ts
│   │   ├── trainingService.ts
│   │   ├── attendanceService.ts
│   │   ├── payrollService.ts
│   │   ├── performanceService.ts
│   │   ├── externalService.ts
│   │   ├── employeeService.ts
│   │   ├── agentService.ts
│   │   └── fileService.ts
│   ├── pages/                     # 页面组件
│   │   ├── auth/
│   │   │   ├── Login.tsx
│   │   │   ├── MFAVerify.tsx
│   │   │   └── ForgotPassword.tsx
│   │   ├── dashboard/
│   │   │   ├── AdminDashboard.tsx
│   │   │   ├── HRDashboard.tsx
│   │   │   ├── ManagerDashboard.tsx
│   │   │   └── EmployeeDashboard.tsx
│   │   ├── recruitment/
│   │   │   ├── JobPostList.tsx
│   │   │   ├── JobPostDetail.tsx
│   │   │   ├── ResumeList.tsx
│   │   │   ├── ResumeDetail.tsx
│   │   │   ├── ResumeImport.tsx
│   │   │   ├── InterviewExam.tsx
│   │   │   ├── ExamManagement.tsx
│   │   │   ├── QuestionBank.tsx
│   │   │   └── TalentPool.tsx
│   │   ├── onboarding/
│   │   │   ├── OnboardingPortal.tsx    # 新员工入职门户
│   │   │   ├── DocumentUpload.tsx
│   │   │   ├── IdentityVerification.tsx
│   │   │   ├── AgreementSign.tsx
│   │   │   ├── FaceCapture.tsx
│   │   │   └── OnboardingProgress.tsx
│   │   ├── training/
│   │   │   ├── TrainingPlan.tsx
│   │   │   ├── TrainingList.tsx
│   │   │   ├── TrainingDetail.tsx
│   │   │   ├── CheckIn.tsx             # 扫码签到
│   │   │   ├── ExamPage.tsx            # 在线考试
│   │   │   ├── VideoCourse.tsx         # 视频课程
│   │   │   ├── CertificateList.tsx
│   │   │   └── AuditMaterials.tsx      # 体系审核资料
│   │   ├── attendance/
│   │   │   ├── AttendanceCalendar.tsx
│   │   │   ├── AttendanceSummary.tsx
│   │   │   ├── AnomalyList.tsx
│   │   │   ├── LeaveRequest.tsx
│   │   │   └── ShiftSchedule.tsx
│   │   ├── payroll/
│   │   │   ├── PayrollReview.tsx       # 薪资审核
│   │   │   ├── PayslipView.tsx         # 工资条查看
│   │   │   ├── PayrollRules.tsx        # 薪资规则管理
│   │   │   └── SalaryBudget.tsx        # 薪资预算
│   │   ├── performance/
│   │   │   ├── SelfEvaluation.tsx
│   │   │   ├── ReviewManagement.tsx
│   │   │   ├── PerformanceReport.tsx
│   │   │   └── RatingDistribution.tsx
│   │   ├── external/
│   │   │   ├── InjuryCaseList.tsx      # 工伤管理
│   │   │   ├── InjuryCaseDetail.tsx
│   │   │   ├── HousingFundList.tsx     # 公积金管理
│   │   │   └── GovernmentDeclaration.tsx
│   │   ├── employee/
│   │   │   ├── EmployeeList.tsx
│   │   │   ├── EmployeeProfile.tsx
│   │   │   ├── ResignationApply.tsx    # 离职申请
│   │   │   ├── ResignationProcess.tsx
│   │   │   ├── CertificateRequest.tsx  # 证明申请
│   │   │   └── ExpenseClaim.tsx        # 费用报销
│   │   ├── agent/
│   │   │   ├── AgentDashboard.tsx      # Agent 监控面板
│   │   │   ├── AgentLogList.tsx        # Agent 执行日志
│   │   │   ├── AgentConfig.tsx         # Agent 参数配置
│   │   │   └── AgentAlert.tsx          # Agent 告警
│   │   ├── system/
│   │   │   ├── UserManagement.tsx
│   │   │   ├── RoleManagement.tsx
│   │   │   ├── AuditLog.tsx
│   │   │   ├── SystemConfig.tsx
│   │   │   └── BackupRestore.tsx
│   │   └── error/
│   │       ├── NotFound.tsx
│   │       ├── Forbidden.tsx
│   │       └── ServerError.tsx
│   ├── routes/                    # 路由定义
│   │   ├── index.tsx              # 路由入口
│   │   ├── protectedRoute.tsx     # 受保护路由
│   │   ├── roleRoute.tsx          # 角色路由
│   │   └── routeConfig.ts        # 路由配置表
│   ├── types/                     # TypeScript 类型定义
│   │   ├── index.ts
│   │   ├── user.ts
│   │   ├── recruitment.ts
│   │   ├── onboarding.ts
│   │   ├── training.ts
│   │   ├── attendance.ts
│   │   ├── payroll.ts
│   │   ├── performance.ts
│   │   ├── external.ts
│   │   ├── agent.ts
│   │   └── common.ts
│   ├── utils/                     # 工具函数
│   │   ├── format.ts
│   │   ├── validate.ts
│   │   ├── permission.ts
│   │   ├── download.ts
│   │   ├── qrCode.ts
│   │   └── constants.ts
│   ├── i18n/                      # 国际化资源
│   │   ├── index.ts
│   │   ├── zh-CN/
│   │   │   ├── common.json
│   │   │   ├── recruitment.json
│   │   │   ├── onboarding.json
│   │   │   └── ...
│   │   └── en/
│   │       ├── common.json
│   │       ├── recruitment.json
│   │       ├── onboarding.json
│   │       └── ...
│   ├── App.tsx                    # 应用根组件
│   └── main.tsx                   # 入口文件
├── tests/                         # 测试文件
│   ├── unit/
│   ├── integration/
│   └── accessibility/
├── vite.config.ts                 # Vite 配置
├── tsconfig.json
├── package.json
└── index.html
```

---

## 3. 路由设计

### 3.1 路由结构总览

```
/
├── /login                          # 登录页（公开）
├── /mfa-verify                     # MFA 验证（公开）
├── /forgot-password                # 忘记密码（公开）
│
├── /                               # 首页 → 根据角色重定向到对应 Dashboard
│
├── /dashboard                      # 工作台（角色差异化）
│   ├── /dashboard/admin            # 管理员 Dashboard
│   ├── /dashboard/hr               # 人事专员 Dashboard
│   ├── /dashboard/manager          # 部门主管 Dashboard
│   └── /dashboard/employee         # 员工 Dashboard
│
├── /recruitment                    # 招聘管理
│   ├── /recruitment/jobs           # 岗位列表
│   ├── /recruitment/jobs/:id       # 岗位详情
│   ├── /recruitment/resumes        # 简历列表
│   ├── /recruitment/resumes/:id    # 简历详情
│   ├── /recruitment/import         # 简历导入
│   ├── /recruitment/exams          # 考试管理
│   ├── /recruitment/questions      # 题库管理
│   └── /recruitment/talent-pool    # 人才库
│
├── /onboarding                     # 入职管理
│   ├── /onboarding/portal          # 新员工入职门户
│   ├── /onboarding/progress        # 入职进度跟踪
│   └── /onboarding/list            # 入职名单
│
├── /training                       # 培训管理
│   ├── /training/plans             # 培训计划
│   ├── /training/list              # 培训列表
│   ├── /training/:id               # 培训详情
│   ├── /training/check-in          # 扫码签到（PWA）
│   ├── /training/exam              # 在线考试（PWA）
│   ├── /training/video             # 视频课程
│   ├── /training/certificates      # 证书管理
│   └── /training/audit             # 体系审核资料
│
├── /attendance                     # 考勤管理
│   ├── /attendance/calendar        # 考勤日历
│   ├── /attendance/summary         # 考勤汇总
│   ├── /attendance/anomalies       # 异常列表
│   ├── /attendance/leave           # 请假申请
│   └── /attendance/schedule        # 排班表
│
├── /payroll                        # 薪资管理
│   ├── /payroll/review             # 薪资审核（人事）
│   ├── /payroll/payslip            # 工资条（员工）
│   ├── /payroll/rules              # 薪资规则（管理员）
│   └── /payroll/budget             # 薪资预算（第三期）
│
├── /performance                    # 绩效管理
│   ├── /performance/evaluation     # 绩效自评
│   ├── /performance/review         # 考核管理
│   ├── /performance/report         # 绩效报告
│   └── /performance/distribution   # 等级分布
│
├── /external                       # 外务管理
│   ├── /external/injury            # 工伤管理
│   ├── /external/injury/:id        # 工伤详情
│   ├── /external/housing-fund      # 公积金管理
│   └── /external/declaration       # 政府申报
│
├── /employee                       # 员工服务
│   ├── /employee/list              # 员工列表
│   ├── /employee/:id               # 员工档案
│   ├── /employee/resignation       # 离职申请
│   ├── /employee/certificate       # 证明申请
│   └── /employee/expense           # 费用报销
│
├── /agent                          # Agent 管理（系统管理员）
│   ├── /agent/dashboard            # Agent 监控面板
│   ├── /agent/logs                 # Agent 执行日志
│   ├── /agent/config               # Agent 参数配置
│   └── /agent/alerts               # Agent 告警
│
├── /system                         # 系统管理（系统管理员）
│   ├── /system/users               # 用户管理
│   ├── /system/roles               # 角色管理
│   ├── /system/audit               # 审计日志
│   ├── /system/config              # 系统配置
│   └── /system/backup              # 备份恢复
│
├── /exam/:token                    # 考试入口（公开，Token 访问）
│
└── /404, /403, /500                # 错误页面
```

### 3.2 路由保护策略

| 路由组 | 所需角色 | 保护方式 |
|--------|---------|---------|
| /login, /mfa-verify, /forgot-password | 未认证用户 | 已登录则重定向到 Dashboard |
| /dashboard | 所有角色 | 需认证，按角色重定向 |
| /recruitment | HR、管理员 | RBAC 权限校验 |
| /onboarding/portal | 新员工 | 临时令牌验证 |
| /training/check-in | 受训员工 | 二维码 Token 验证 |
| /exam/:token | 考生 | Token 一次性验证 |
| /payroll/review | HR、管理员 | RBAC + MFA |
| /payroll/payslip | 本人 | 行级权限 |
| /agent/* | 管理员 | RBAC + MFA |
| /system/* | 管理员 | RBAC + MFA |

### 3.3 路由配置示例

```typescript
// routeConfig.ts
interface RouteConfig {
  path: string;
  component: ComponentType;
  roles: Role[];
  title: string;
  icon: string;
  hidden?: boolean;
  mfa?: boolean;
}

export const routeConfig: RouteConfig[] = [
  {
    path: '/dashboard/admin',
    component: AdminDashboard,
    roles: ['ADMIN'],
    title: 'admin.dashboard',
    icon: 'DashboardOutlined',
    mfa: true,
  },
  {
    path: '/recruitment/jobs',
    component: JobPostList,
    roles: ['HR', 'ADMIN'],
    title: 'recruitment.jobList',
    icon: 'JobAddOutlined',
  },
  // ... 更多路由配置
];
```

---

## 4. 状态管理

### 4.1 状态分层设计 (V10.0: 重新梳理)

本系统采用 Zustand 作为客户端 UI 状态管理，@tanstack/react-query 作为服务端状态管理。状态分为以下层级：

```
┌─────────────────────────────────────────────┐
│        UI State (Zustand - 仅 2 个 store)     │
│  ┌──────────┐ ┌──────────┐                  │
│  │ authStore│ │  uiStore │                  │
│  └──────────┘ └──────────┘                  │
├─────────────────────────────────────────────┤
│      Server State (React Query - 所有业务数据) │
│  - 招聘数据：useResumeList, useJobDetail    │
│  - 入职数据：useOnboardingTasks, useDocs    │
│  - 培训数据：useTrainingList, useExam       │
│  - 考勤数据：useAttendanceSummary           │
│  - 薪资数据：usePayrollReview, usePayslip   │
│  - 绩效数据：useEvaluationList              │
│  - Agent 数据：useAgentStatus, useAgentLogs │
│  - 缓存策略、请求去重、自动重试              │
│  - 列表数据缓存 5 分钟，详情数据缓存 1 分钟  │
├─────────────────────────────────────────────┤
│      Component Local State (useState)         │
│  - 表单字段值                                │
│  - 模态框可见性                              │
│  - 表格排序/筛选状态                         │
│  - 当前选中项（如 selectedResume）            │
└─────────────────────────────────────────────┘
```

**V10.0 修订说明：**
- V9.0 中 stores/ 目录下存在 7 个业务模块 store（recruitmentStore、onboardingStore、trainingStore、attendanceStore、payrollStore、performanceStore、agentStore），与声明的"Zustand 仅管理 UI 交互状态"原则相矛盾
- V10.0 彻底移除所有业务模块 store，Zustand 仅保留 authStore 和 uiStore 两个 store
- 原业务 store 中存储的"当前选中项"（如 selectedResume）、"筛选参数"（如 filterParams）等 UI 状态迁移至页面级 useState
- 原 agentStore 中的 API 数据（agents、alerts）和 API 方法（refreshStatus、acknowledgeAlert 等）迁移至 React Query 的 useQuery/useMutation

### 4.2 核心 Store 设计

#### authStore.ts

```typescript
interface AuthState {
  // [UI] 状态
  isAuthenticated: boolean;
  isLoading: boolean;
  mfaRequired: boolean;
  mfaMethod: 'sms' | 'email' | 'totp' | null;

  // [UI] 用户信息（从后端 /api/auth/me 获取，仅保留 UI 展示所需字段）
  user: UserInfo | null;
  roles: Role[];
  permissions: string[];

  // 动作
  login: (username: string, password: string) => Promise<void>;
  verifyMFA: (code: string) => Promise<void>;
  logout: () => Promise<void>;
  // V9.0: refreshSession 与 HTTP-Only Cookie 协同工作方式
  // 客户端无法直接读取 refreshToken（HTTP-Only Cookie 对 JS 不可见），
  // refreshSession() 实际触发后端中间件自动刷新：访问 /api/auth/refresh 端点，
  // 由服务端读取 Cookie 中的 refreshToken 并签发新 Token
  refreshSession: () => Promise<void>;
  clearSession: () => void;
}
```

#### uiStore.ts

```typescript
interface UIState {
  // [UI] 侧栏
  siderCollapsed: boolean;
  toggleSider: () => void;

  // [UI] 主题
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;

  // [UI] 语言
  language: 'zh-CN' | 'en';
  setLanguage: (lang: 'zh-CN' | 'en') => void;

  // [UI] 通知
  notifications: NotificationItem[];
  unreadCount: number;
  markAsRead: (id: string) => void;
  clearNotifications: () => void;

  // [UI] 面包屑
  breadcrumb: BreadcrumbItem[];
  setBreadcrumb: (items: BreadcrumbItem[]) => void;
}
```

### 4.3 React Query 数据获取策略 (V10.0: 统一管理所有业务数据)

所有数据请求统一通过 **@tanstack/react-query** 的 `useQuery` / `useMutation` 实现，不使用自定义 `useApi` Hook，也不使用 Zustand store 管理 API 数据。

- **缓存策略**：列表数据缓存 5 分钟，详情数据缓存 1 分钟
- **乐观更新**：表单提交时先更新 UI，失败则回滚
- **自动重试**：网络错误自动重试 2 次，指数退避
- **请求取消**：组件卸载时自动取消未完成的请求
- **依赖查询**：支持查询无效化（mutation 后自动 refetch 相关查询）

```typescript
// 使用 React Query 的示例
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// 查询：获取简历列表
function useResumeList(params: ResumeFilterParams) {
  return useQuery({
    queryKey: ['resumes', params],
    queryFn: () => apiClient.get('/api/recruitment/resumes', { params }),
    staleTime: 5 * 60 * 1000, // 5 分钟缓存
    retry: 2,
  });
}

// 突变：更新简历状态
function useUpdateResumeStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ resumeId, status }: { resumeId: string; status: string }) =>
      apiClient.patch(`/api/recruitment/resumes/${resumeId}`, { status }),
    onSuccess: () => {
      // 无效化相关查询，触发自动重新获取
      queryClient.invalidateQueries({ queryKey: ['resumes'] });
    },
  });
}

// 使用示例
function ResumeListPage() {
  // React Query 管理列表数据
  const { data, isLoading, error } = useResumeList({ page: 1, pageSize: 20 });
  const updateMutation = useUpdateResumeStatus();

  // 页面级本地状态（原 V9.0 recruitmentStore 中的 UI 状态迁移至此处）
  const [selectedResume, setSelectedResume] = useState<Resume | null>(null);
  const [filterParams, setFilterParams] = useState<ResumeFilterParams>({});

  const handleStatusChange = (resumeId: string, status: string) => {
    updateMutation.mutate({ resumeId, status });
  };

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorBoundary error={error} />;

  return (
    <DataTable
      columns={resumeColumns}
      dataSource={data?.data || []}
      onStatusChange={handleStatusChange}
      selectedRowKey={selectedResume?.id}
      onRowSelect={setSelectedResume}
    />
  );
}
```

**V10.0: Agent 模块数据管理示例（原 agentStore 迁移至 React Query）**

```typescript
// 查询：获取 Agent 运行状态
function useAgentStatus() {
  return useQuery({
    queryKey: ['agents', 'status'],
    queryFn: () => apiClient.get('/api/agent/status'),
    staleTime: 10 * 1000, // 10 秒缓存
    refetchInterval: 30 * 1000, // 30 秒自动轮询
    retry: 1,
  });
}

// 查询：获取 Agent 告警列表
function useAgentAlerts() {
  return useQuery({
    queryKey: ['agents', 'alerts'],
    queryFn: () => apiClient.get('/api/agent/alerts'),
    staleTime: 5 * 60 * 1000,
  });
}

// 突变：确认告警
function useAcknowledgeAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) =>
      apiClient.patch(`/api/agent/alerts/${alertId}/acknowledge`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', 'alerts'] });
    },
  });
}

// 突变：重启 Agent
function useRestartAgent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (agentName: string) =>
      apiClient.post(`/api/agent/${agentName}/restart`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', 'status'] });
    },
  });
}

// 使用示例
function AgentDashboardPage() {
  const { data: agentData, isLoading } = useAgentStatus();
  const { data: alertData } = useAgentAlerts();
  const acknowledgeMutation = useAcknowledgeAlert();
  const restartMutation = useRestartAgent();

  // 页面级本地状态
  const [selectedAgent, setSelectedAgent] = useState<AgentStatus | null>(null);

  if (isLoading) return <LoadingSpinner />;

  return (
    <div>
      <AgentStatusList
        agents={agentData?.data || []}
        onAgentClick={setSelectedAgent}
        onRestart={restartMutation.mutate}
      />
      <AlertList
        alerts={alertData?.data || []}
        onAcknowledge={acknowledgeMutation.mutate}
      />
    </div>
  );
}
```

### 4.4 Zustand 与 React Query 职责边界 (V10.0: 重新明确)

本系统同时使用 Zustand（客户端状态）和 @tanstack/react-query（服务端状态），职责划分如下：

| 维度 | Zustand (客户端状态) | React Query (服务端状态) |
|------|---------------------|------------------------|
| 职责范围 | 全局 UI 交互状态 | 所有 API 数据 |
| 包含 store | authStore（认证 UI 状态）、uiStore（全局 UI 状态） | 所有业务模块数据（招聘、入职、培训、考勤、薪资、绩效、Agent） |
| 典型内容 | isAuthenticated、user、roles、siderCollapsed、theme、language、notifications | 列表数据、详情数据、分页数据、统计数据、Agent 状态、告警列表 |
| 生命周期 | 页面会话期间 | 缓存策略控制（staleTime/gcTime） |
| 持久化 | 非敏感数据可使用 persist 中间件（如 onboarding 表单草稿） | 不持久化，依赖缓存 |

**页面级 UI 状态说明：**
- 原 V9.0 业务 store 中的 UI 状态（如 selectedResume、filterParams、currentStep）迁移至页面级 useState
- 这些状态不涉及跨页面共享，无需提升到全局 store
- 跨页面共享的 UI 状态（如全局通知、面包屑）保留在 uiStore 中

**Store 接口注释规范：**
- 每个 Store 属性应标注 `// [UI]` 以明确状态类型
- authStore 存储 isAuthenticated/user/roles/permissions（UI 状态），认证 Token 由 HTTP-Only Cookie 管理
- 不再存在管理 API 数据的 Zustand store，所有数据请求统一由 React Query 负责

---

## 5. 组件体系

### 5.1 组件分类

| 分类 | 说明 | 示例 |
|------|------|------|
| 布局组件 | 页面骨架结构 | MainLayout, PageHeader, CardContainer |
| 导航组件 | 页面导航与跳转 | AppSider, BreadcrumbNav, TabContainer |
| 数据展示 | 表格、列表、详情 | DataTable, ResumeCard, EmployeeProfileCard |
| 表单组件 | 输入、选择、上传 | StepForm, FileUpload, SignaturePad |
| 反馈组件 | 提示、确认、加载 | ConfirmDialog, Toast, LoadingSpinner |
| 图表组件 | 数据可视化 | BarChart, LineChart, PieChart, Heatmap |
| 业务组件 | 特定业务逻辑 | QRCheckIn, ExamPaper, PayrollTable |

### 5.2 关键组件设计

#### DataTable 通用数据表格

```typescript
interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  dataSource: T[];
  loading: boolean;
  pagination: PaginationConfig;
  onPaginationChange: (page: number, pageSize: number) => void;
  rowKey?: string;
  rowSelection?: RowSelectionConfig;
  actions?: ActionButton[];
  exportConfig?: ExportConfig;
  filterConfig?: FilterConfig;
  sortConfig?: SortConfig;
  // V9.0 新增：虚拟滚动配置
  // Ant Design 5.x Table 默认不开启虚拟滚动，需显式配置 scroll.y 启用
  scroll?: { x?: string | number; y?: string | number };
}
```

**功能特性：**
- 内置分页、排序、筛选
- 行选择（单选/多选）
- 列显隐控制
- 导出按钮（Excel/CSV）
- 加载状态
- 空数据提示
- 操作列（编辑、删除、查看）
- V9.0 新增：虚拟滚动（通过 scroll={{ y: height }} 启用，默认 600px）

#### StepForm 分步表单

```typescript
interface StepFormProps {
  steps: FormStep[];
  initialValues?: Record<string, any>;
  onSubmit: (values: any) => Promise<void>;
  onStepChange?: (current: number) => void;
  showStepNumbers?: boolean;
  allowSkip?: boolean;
}

interface FormStep {
  title: string;
  description?: string;
  component: React.FC<StepFormContext>;
  validate?: (values: any) => ValidationResult;
}
```

**应用场景：**
- 新员工入职引导（多步骤材料上传）
- 工伤申报（材料收集 → 审核 → 提交）
- 离职申请（填写 → 附件 → 确认）

#### QRCheckIn 扫码签到组件

```typescript
interface QRCheckInProps {
  trainingId: string;
  onSuccess: (result: CheckInResult) => void;
  onError: (error: Error) => void;
}
```

**功能：**
- 摄像头二维码扫描
- 签到成功/失败动画反馈
- 签到时间戳记录
- 防重复签到

#### SignaturePad 电子签名组件

```typescript
interface SignaturePadProps {
  width?: number;
  height?: number;
  backgroundColor?: string;
  penColor?: string;
  onSignature: (dataUrl: string) => void;
  clearOnStart?: boolean;
  showGuideline?: boolean;
  keyboardInteractive?: boolean;  // 启用键盘操作
  ariaLabel?: string;            // 无障碍标签
  ariaDescribedBy?: string;      // 描述元素 ID
}
```

**无障碍支持：**
- 支持键盘操作：方向键控制画笔位置绘制、Enter 确认签名、Escape 清空签名
- 完整的 aria 属性：`role="img"`、`aria-label="电子签名区域"`、`aria-describedby` 指向使用说明
- `aria-invalid` 在签名为空时标记为 true
- 签名区域支持 `tabindex="0"` 接收焦点，`:focus-visible` 样式提示

### 5.3 组件复用策略

#### FileUpload 文件上传组件 (V10.0: 明确分片上传实现方案)

**V10.0 修订说明：**
- Ant Design Upload 组件仅提供 UI 外壳（拖拽区域、进度条、文件列表），不提供分片上传功能
- 分片上传的完整逻辑（文件切割、MD5 校验、断点续传、并发控制、失败重试）由自定义 `useFileUpload` Hook 实现
- `FileUpload.tsx` 组件组合 Ant Design Upload UI + `useFileUpload` Hook 的业务逻辑

```typescript
interface FileUploadProps {
  // 基础配置
  accept?: string;
  maxFileSize?: number;  // 最大文件大小 (MB)
  maxSize?: number;      // Ant Design Upload 格式 (bytes)

  // 分片上传配置
  chunkSize?: number;             // 单分片大小 (默认 5MB)
  maxConcurrent?: number;         // 并发上传分片数 (默认 3)

  // 断点续传
  breakpointStorage?: 'localStorage' | 'sessionStorage' | 'memory';
  breakpointKey?: string;
  onBreakpointSave?: (progress: UploadBreakpoint) => void;

  // 失败重试
  maxRetries?: number;            // 单分片最大重试次数 (默认 3)
  retryDelay?: number;            // 重试退避基础延迟 (ms, 默认 1000)
  retryStrategy?: 'fixed' | 'exponential' | 'linear';

  // 进度反馈
  onProgress?: (info: UploadProgressInfo) => void;
  showSpeed?: boolean;
  showETA?: boolean;

  // 回调
  onSuccess?: (file: File, response: any) => void;
  onError?: (file: File, error: UploadError) => void;
  onCompleted?: (result: UploadResult) => void;
}

// 上传进度信息接口
interface UploadProgressInfo {
  percent: number;           // 总进度百分比 (0-100)
  speed: number;             // 上传速度 (KB/s)
  loaded: number;            // 已上传字节数
  total: number;             // 总字节数
  eta: number;               // 预计剩余时间 (秒)
  currentChunk: number;      // 当前分片序号
  totalChunks: number;       // 总分片数
  concurrentCount: number;   // 当前并发上传数
}

// 断点记录接口
interface UploadBreakpoint {
  fileHash: string;          // 文件哈希 (SHA-256)
  uploadedChunks: number[];  // 已上传成功的分片序号列表
  updatedAt: number;         // 最后更新时间戳
}

// 上传错误接口
interface UploadError {
  code: string;              // CHUNK_FAILED / NETWORK_ERROR / SERVER_ERROR / FILE_TOO_LARGE
  message: string;           // 错误描述
  chunkIndex?: number;       // 失败的分片序号
  retryCount?: number;       // 当前重试次数
  recoverable: boolean;      // 是否可恢复
}
```

**分片上传实现方案（useFileUpload Hook）：**

```typescript
// useFileUpload.ts — 分片上传自定义 Hook
// 该 Hook 独立于 Ant Design Upload 组件，提供完整的分片上传逻辑

interface UseFileUploadOptions {
  chunkSize?: number;
  maxConcurrent?: number;
  maxRetries?: number;
  retryDelay?: number;
  retryStrategy?: 'fixed' | 'exponential' | 'linear';
  breakpointStorage?: 'localStorage' | 'sessionStorage' | 'memory';
  uploadUrl: string;          // 分片上传接口
  mergeUrl: string;           // 分片合并接口
  hashUrl?: string;           // 哈希校验接口（秒传）
}

function useFileUpload(options: UseFileUploadOptions) {
  // 1. 文件哈希计算（Web Crypto API）
  async function calculateFileHash(file: File): Promise<string> {
    const buffer = await file.slice(0, 1024).arrayBuffer();
    // 大文件使用完整 SHA-256
    // ...
  }

  // 2. 文件分片切割（File.slice API）
  function getChunks(file: File, chunkSize: number): Blob[] {
    const chunks: Blob[] = [];
    for (let start = 0; start < file.size; start += chunkSize) {
      chunks.push(file.slice(start, start + chunkSize));
    }
    return chunks;
  }

  // 3. 断点续传
  async function getBreakpoint(fileHash: string): Promise<UploadBreakpoint | null> {
    const stored = localStorage.getItem(`upload-${fileHash}`);
    if (!stored) return null;
    const bp = JSON.parse(stored);
    if (Date.now() - bp.updatedAt > 24 * 60 * 60 * 1000) {
      localStorage.removeItem(`upload-${fileHash}`);
      return null;
    }
    return bp;
  }

  // 4. 并发控制（信号量模式）
  async function uploadWithConcurrency(
    chunks: Blob[],
    skipIndices: number[],
    maxConcurrent: number
  ) {
    const semaphores: Promise<void>[] = [];
    for (let i = 0; i < chunks.length; i++) {
      if (skipIndices.includes(i)) continue;
      const promise = uploadChunk(chunks[i], i);
      semaphores.push(promise);
      if (semaphores.length >= maxConcurrent) {
        await Promise.race(semaphores);
      }
    }
    await Promise.all(semaphores);
  }

  // 5. 失败重试（指数退避）
  async function uploadChunk(chunk: Blob, index: number) {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await doUpload(chunk, index);
      } catch (err) {
        if (attempt === maxRetries) throw err;
        const delay = retryStrategy === 'exponential'
          ? retryDelay * Math.pow(2, attempt)
          : retryDelay * (attempt + 1);
        await sleep(delay);
      }
    }
  }

  return {
    upload: (file: File) => Promise<UploadResult>,
    cancel: (fileHash: string) => void,
    progress: UploadProgressInfo,
  };
}
```

**工程化设计：**

1. **断点续传机制**
   - 文件上传前计算 SHA-256 哈希作为唯一标识
   - 已上传分片记录存储于 localStorage（大文件）或 memory（小文件）
   - 页面刷新后通过文件哈希恢复断点，仅上传未完成分片
   - 断点记录定期清理（过期时间 24 小时）

2. **并发控制**
   - 同时上传分片数限制为 3（可通过 maxConcurrent 配置）
   - 使用信号量模式管理并发，避免浏览器请求队列溢出
   - 大文件（>100MB）自动降低并发数至 2

3. **失败重试策略**
   - 单分片失败自动重试，最多 3 次
   - 指数退避策略：第 N 次重试延迟 = retryDelay * 2^(N-1) ms
   - 超过最大重试次数后标记为不可恢复错误，触发 onCompleted 回调

4. **大文件进度反馈**
   - 实时显示上传百分比、速度 (KB/s)、已上传/总大小
   - 预计剩余时间 = (总大小 - 已上传) / 当前速度
   - 当前分片序号 / 总分片数，并发上传数
   - 上传完成后触发 onCompleted 回调，返回 UploadResult

5. **分片合并策略**
   - 前端不直接合并，由后端接收全部分片后执行合并
   - 上传流程：上传分片 → 全部分片完成 → 调用合并接口 → 返回文件 URI
   - 合并接口入参：文件哈希、分片总数、文件元数据（名称、类型、大小）

- **Ant Design 组件**：直接使用 Ant Design 5.x 组件（Button, Input, Select 等）
- **封装组件**：在 Ant Design 基础上封装业务通用组件（DataTable, StepForm 等）
- **业务组件**：特定业务场景的组件（ResumeCard, PayrollTable 等）
- **Hooks 复用**：将业务逻辑抽离为自定义 Hooks，组件只负责渲染

---

## 6. 页面布局设计

### 6.1 主布局 (MainLayout)

```
┌──────────────────────────────────────────────────────────────┐
│  [Logo]  GBM AI Agent HR                     [🔔] [🌐] [👤] │  ← AppHeader (64px)
├──────────┬───────────────────────────────────────────────────┤
│          │  ┌─────────────────────────────────────────────┐  │
│ [菜单]   │  │  📍 首页 > 招聘管理 > 简历列表               │  │  ← BreadcrumbNav
│          │  ├─────────────────────────────────────────────┤  │
│ 工作台   │  │                                             │  │
│ 招聘管理  │  │  ┌─ 搜索栏 ────────────────────────┐       │  │  ← SearchBar
│ 入职管理  │  │  ┌─ 操作按钮区 ───────────────────┐ │       │  │
│ 培训管理  │  │  │ [+新建] [导入] [导出] [批量]   │ │       │  │
│ 考勤管理  │  │  ├────────────────────────────────┤ │       │  │
│ 薪资管理  │  │  │                                │ │       │  │
│ 绩效管理  │  │  │         数据表格区域           │ │       │  │  ← Page Content
│ 外务管理  │  │  │                                │ │       │  │
│ 员工服务  │  │  └────────────────────────────────┘ │       │  │
│ Agent 管理│  │                                     │       │  │
│ 系统管理  │  │                                     │       │  │
│          │  └─────────────────────────────────────────────┘  │
├──────────┴───────────────────────────────────────────────────┤
│  © 2026 GBM AI Agent HR | 版本 2.0                            │  ← AppFooter (48px)
└──────────────────────────────────────────────────────────────┘
```

**布局参数：**
- 侧栏宽度：200px（展开）/ 64px（折叠）
- 顶栏高度：64px
- 底栏高度：48px
- 内容区：自适应（无 min-width 限制，依靠 Ant Design 栅格系统自适应）

### 6.2 不同角色的侧栏菜单

#### 系统管理员

```
工作台
├── 招聘管理
│   ├── 岗位管理
│   ├── 简历管理
│   ├── 考试管理
│   └── 人才库
├── 入职管理
│   ├── 入职进度
│   └── 入职名单
├── 培训管理
│   ├── 培训计划
│   ├── 培训列表
│   ├── 证书管理
│   └── 体系审核
├── 考勤管理
│   ├── 考勤汇总
│   └── 异常处理
├── 薪资管理
│   ├── 薪资审核
│   └── 薪资规则
├── 绩效管理
│   ├── 考核管理
│   └── 绩效报告
├── 外务管理
│   ├── 工伤管理
│   └── 公积金管理
├── 员工服务
│   ├── 员工列表
│   └── 证明开具
├── Agent 管理
│   ├── 监控面板
│   ├── 执行日志
│   ├── 参数配置
│   └── 告警中心
└── 系统管理
    ├── 用户管理
    ├── 角色管理
    ├── 审计日志
    ├── 系统配置
    └── 备份恢复
```

#### 人事专员

```
工作台
├── 待办审核（聚合视图）
├── 招聘管理
├── 入职管理
├── 培训管理
├── 考勤管理
├── 薪资管理（仅审核）
├── 绩效管理
├── 外务管理
└── 员工服务
```

#### 部门主管

```
工作台
├── 待办审批
├── 团队分析
├── 绩效考核
│   └── 下属考核
└── 培训管理
    └── 部门培训
```

#### 普通员工

```
工作台
├── 我的信息
├── 工资条
├── 考勤记录
├── 培训记录
├── 证明申请
├── 费用报销
└── 离职申请
```

### 6.3 响应式布局

| 断点 | 范围 | 布局调整 |
|------|------|---------|
| xl | ≥ 1536px | 标准布局 |
| lg | 1200-1535px | 标准布局 |
| md | 992-1199px | 表格列自动折叠 |
| sm | 768-991px | 侧栏折叠，卡片堆叠 |
| xs | < 768px | 移动端布局，底部导航 |

### 6.4 移动端布局

移动端使用 `MobileLayout` 组件，配合 `BottomTabBar` 底部导航栏：

```
┌──────────────────────────────────┐
│  [☰]  GBM HR            [🔔][👤] │  ← Header (56px)
├──────────────────────────────────┤
│                                  │
│        ┌──────────────────┐      │
│        │                  │      │
│        │   页面内容区      │      │
│        │   (卡片式布局)     │      │
│        │                  │      │
│        └──────────────────┘      │
│                                  │
├──────────────────────────────────┤
│  [🏠]    [📋]    [➕]    [👤]    │  ← BottomTabBar (56px)
│  首页     待办     快捷    我的    │
└──────────────────────────────────┘
```

**移动端布局参数：**
- 顶栏高度：56px（含汉堡菜单）
- 底部 Tab 栏高度：56px
- 内容区：单列卡片式布局，表格转为卡片列表
- 手势：左滑返回，下拉刷新
- `BottomTabBar` 最多显示 5 个 Tab，更多项折叠至「更多」菜单

---

## 7. 关键页面设计

### 7.1 登录页

```
┌────────────────────────────────────────────────────┐
│                                                    │
│                  [Logo]                            │
│              GBM AI Agent HR                       │
│                                                    │
│      ┌──────────────────────────────────┐          │
│      │      欢迎回来                     │          │
│      │                                  │          │
│      │  [👤]  账号/邮箱                  │          │
│      │                                  │          │
│      │  [🔒]  密码                       │          │
│      │                                  │          │
│      │  □  记住我    忘记密码？          │          │
│      │                                  │          │
│      │  ┌─────── 登 录 ─────────┐       │          │
│      │  └───────────────────────┘       │          │
│      │                                  │          │
│      │  新用户？前往入职门户 →            │          │
│      └──────────────────────────────────┘          │
│                                                    │
│         [中] / [EN]                                │
└────────────────────────────────────────────────────┘
```

**交互流程：**
1. 输入账号密码 → 点击登录
2. 系统校验 → 如需要 MFA，跳转到 MFA 验证页
3. MFA 验证通过 → 跳转到 Dashboard

### 7.2 管理员 Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  Dashboard > 管理员工作台                                   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ 在职工人      │ │ 本月入职     │ │ 本月离职     │        │
│  │    1,256     │ │     18       │ │      5       │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐ ┌──────────────────────────────┐ │
│  │  Agent 运行状态       │ │  待办事项                    │ │
│  │                       │ │                              │ │
│  │  🟢 招聘 Agent 正常  │ │  □ 薪资审核 (3人)           │ │
│  │  🟢 入职 Agent 正常  │ │  □ 工伤申报 (1件)           │ │
│  │  🟡 RPA Agent 告警   │ │  □ 证书到期提醒 (5个)       │ │
│  │  🟢 薪资 Agent 正常  │ │  □ 面试安排 (2场)           │ │
│  │                       │ │                              │ │
│  │  成功率: 97.3%        │ │                              │ │
│  └──────────────────────┘ └──────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐   │
│  │  近 30 天 HR 业务趋势                                 │   │
│  │                                                      │   │
│  │  [折线图: 入职数/离职数/招聘数 趋势]                  │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 简历管理页

```
┌─────────────────────────────────────────────────────────────┐
│  招聘管理 > 简历列表                                        │
├─────────────────────────────────────────────────────────────┤
│  [🔍 搜索简历]                  [+新建岗位] [📥导入] [📤导出]│
├─────────────────────────────────────────────────────────────┤
│  筛选: [岗位▼] [状态▼] [分数▼] [日期范围▼] [重置]           │
├─────────────────────────────────────────────────────────────┤
│  ┌──┬ 姓名  │  岗位   │  分数  │  分类   │  状态  │ 操作  ┐│
│  ├──┼───────┼─────────┼───────┼─────────┼────────┼───────┤│
│  │☐ │ 张三  │ 前端开发 │  85.5│ 高潜    │ 已入库 │ [查看] ││
│  │☐ │ 李四  │ 后端开发 │  72.3│ 候审    │ 待审核 │ [查看] ││
│  │☐ │ 王五  │ 测试工程 │  55.0│ 淘汰    │ 已淘汰 │ [查看] ││
│  └──┴───────┴─────────┴───────┴─────────┴────────┴───────┘│
├─────────────────────────────────────────────────────────────┤
│  共 256 条  第 1/26 页  [‹] [1] [2] [3] ... [26] [›]     │
└─────────────────────────────────────────────────────────────┘
```

### 7.4 薪资审核页

```
┌─────────────────────────────────────────────────────────────┐
│  薪资管理 > 薪资审核                                        │
├─────────────────────────────────────────────────────────────┤
│  核算月份: [2026-06 ▼]    状态: 已核算 等待审核              │
│  核算完成时间: 2026-06-30 23:45:12                         │
│  核算耗时: 8 分 32 秒                                       │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────┐ │
│  │  异常数据 (3条)                                         │ │
│  │  ⚠ 张三: 实发较上月波动 +25% (超出 ±20% 阈值)          │ │
│  │  ⚠ 李四: 加班费突增 (超出 2 个标准差)                   │ │
│  │  ⚠ 王五: 社保金额为 0 但状态为在职                      │ │
│  └────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  [📊查看明细] [📥导出底稿] [✅确认审核] [❌退回重算]         │
└─────────────────────────────────────────────────────────────┘
```

### 7.5 新员工入职门户

```
┌─────────────────────────────────────────────────────────────┐
│  欢迎加入 GBM 公司！                                        │
│  请按照以下步骤完成入职手续                                   │
├─────────────────────────────────────────────────────────────┤
│  入职进度:                                                  │
│  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐                            │
│  │✓ │→ │● │→ │○ │→ │○ │→ │○ │                            │
│  └──┘  └──┘  └──┘  └──┘  └──┘                            │
│  基本信息  上传证件  签署协议  人脸采集  完成               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  步骤 2: 上传证件材料                                       │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  身份证正面       │  │  身份证反面       │               │
│  │  [📷拍照] [📁选择]│  │  [📷拍照] [📁选择]│               │
│  │  ✓ 已上传        │  │  ⏳ 待上传        │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  学历证书         │  │  证件照          │               │
│  │  [📷拍照] [📁选择]│  │  [📷拍照] [📁选择]│               │
│  │  ⏳ 待上传        │  │  ⏳ 待上传        │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                             │
│                            [上一步] [下一步 →]              │
└─────────────────────────────────────────────────────────────┘
```

### 7.6 Agent 监控面板

```
┌─────────────────────────────────────────────────────────────┐
│  Agent 管理 > 监控面板                                      │
├─────────────────────────────────────────────────────────────┤
│  系统概览                                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ 运行中 Agent  │ │ 今日任务数   │ │ 平均成功率   │        │
│  │     18/20    │ │    1,523     │ │    97.3%     │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  Agent 状态                                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 🟢 招聘渠道 Agent     运行中 | 今日: 156 次 | 成功: 98%│   │
│  │ 🟢 简历匹配 Agent     运行中 | 今日: 234 次 | 成功: 99%│   │
│  │ 🟡 RPA Agent          告警   | 今日: 12 次  | 成功: 83%│   │
│  │                      原因: 公积金网站改版，部分元素不可见│   │
│  │ 🟢 薪资 Agent         运行中 | 今日: 1 次   | 成功: 100%│   │
│  │ ...                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  最近告警                                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 10:23 ⚠ RPA Agent - 公积金网站元素识别失败            │   │
│  │ 08:15 ℹ 简历匹配 Agent - 评分偏差预警 (2份)          │   │
│  │ 昨日 23:00 ℹ 薪资 Agent - 月度核算已完成              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. 无障碍访问设计

### 8.1 WCAG 2.1 AA 合规要求

| 要求 | 实现方式 |
|------|---------|
| 键盘可操作 | Tab 键遍历所有交互元素，Esc 关闭模态框 |
| 屏幕阅读器 | aria-label, aria-describedby, role 属性 |
| 色彩对比度 | 正文 ≥ 4.5:1，大文本 ≥ 3:1 |
| 缩放支持 | 放大至 200% 时布局不破坏 |
| 焦点可见性 | :focus-visible 样式，2px 蓝色边框 |
| 表单标签 | 每个输入框关联 label，placeholder 不替代 label |
| 错误提示 | aria-invalid, aria-errormessage 属性 |
| 动态内容 | aria-live 区域播报动态变化 |

### 8.2 关键用户路径无障碍清单

1. **用户登录与身份认证流程**
   - 登录表单所有字段可键盘操作
   - 错误提示关联到对应输入框
   - MFA 验证码输入框自动聚焦

2. **人事专员审核待办事项流程**
   - 待办列表可键盘导航
   - 审核操作按钮有明确 aria-label
   - 审核结果变化通过 aria-live 播报

3. **工资条查看与导出流程**
   - 工资条表格支持键盘导航
   - 导出按钮有明确描述
   - 导出进度通过 aria-busy 反馈

4. **员工自助证明申请流程**
   - 证明类型选择可键盘操作
   - 上传区域支持拖拽和键盘操作
   - 申请状态变化有视觉和听觉反馈

5. **扫码签到流程**
   - 扫码页面支持屏幕阅读器
   - 签到成功/失败有明确反馈
   - 超时提示有合理倒计时

### 8.3 无障碍测试策略

- 开发阶段：`@axe-core/react` 集成到测试中
- CI 阶段：Playwright 无障碍自动化测试
- 发布前：手动使用 NVDA/JAWS 屏幕阅读器测试
- 定期：WAVE 浏览器插件全页面扫描

### 8.4 移动端无障碍 (V9.0 新增)

| 要求 | 实现方式 |
|------|---------|
| 触摸目标尺寸 | 所有可交互元素最小尺寸 ≥ 44×44px（WCAG 2.5.5） |
| 手势键盘替代 | 左滑返回提供按钮替代、下拉刷新提供刷新按钮 |
| 横屏布局 | 横屏模式下布局自动适配，焦点管理遵循 Tab 顺序 |
| 触摸反馈 | 按压态视觉反馈（opacity 变化或颜色变化） |
| 长按菜单 | 长按操作提供右键菜单键盘替代方案 |
| 滑动操作 | 卡片滑动删除提供按钮式操作入口 |

**移动端无障碍测试：**
- 使用 VoiceOver (iOS) / TalkBack (Android) 验证触摸目标可读性
- 验证所有手势操作均有键盘/按钮替代方案
- 横屏模式下验证焦点顺序与布局适配

---

## 9. 国际化设计

### 9.1 语言支持

| 语言 | 代码 | 默认语言 |
|------|------|---------|
| 简体中文 | zh-CN | 是 |
| 英语 | en | 否 |

### 9.2 翻译资源结构

```
i18n/
├── zh-CN/
│   ├── common.json        # 通用文本（按钮、提示等）
│   ├── recruitment.json   # 招聘模块
│   ├── onboarding.json    # 入职模块
│   ├── training.json      # 培训模块
│   ├── attendance.json    # 考勤模块
│   ├── payroll.json       # 薪资模块
│   ├── performance.json   # 绩效模块
│   ├── external.json      # 外务模块
│   ├── employee.json      # 员工模块
│   ├── agent.json         # Agent 模块
│   └── system.json        # 系统模块
└── en/
    ├── common.json
    ├── recruitment.json
    └── ... (同上)
```

### 9.3 格式适配

```typescript
// 日期格式
const formatDate = (date: Date, lang: string): string => {
  if (lang === 'zh-CN') {
    return `${date.getFullYear()}年${date.getMonth()+1}月${date.getDate()}日`;
  }
  return date.toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric'
  });
};

// 金额格式
const formatCurrency = (amount: number, lang: string): string => {
  if (lang === 'zh-CN') {
    return `¥${amount.toLocaleString('zh-CN', {minimumFractionDigits: 2})}`;
  }
  return `$${amount.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
};
```

### 9.4 翻译覆盖率指标

- 所有用户界面文本翻译覆盖率 ≥ 95%
- 中英双语一致性校验，同一术语翻译一致率 100%
- 每版本上线前执行双语全覆盖测试

---

## 10. PWA 与移动端设计

### 10.1 PWA 功能

- **安装**：用户可将应用添加到桌面（manifest.json）
- **离线**：签到页、考试页支持离线缓存
- **推送**：Service Worker 接收服务端推送通知
- **扫码**：调用设备摄像头进行二维码扫描

### 10.2 移动端适配

| 功能 | PC 端 | 移动端 |
|------|-------|--------|
| 导航 | 左侧菜单 | 底部 Tab 栏 + 汉堡菜单 |
| 表格 | 完整表格 | 卡片式列表 |
| 表单 | 多列布局 | 单列布局 |
| 文件上传 | 拖拽上传 | 选择文件/拍照 |
| 签到 | 扫码枪/摄像头 | 摄像头扫码 |
| 考试 | 完整试卷 | 逐题翻页 |

### 10.3 Service Worker 策略

```typescript
// workbox 配置
import { registerRoute } from 'workbox-routing';
import { NetworkFirst, StaleWhileRevalidate } from 'workbox-strategies';

// 应用壳资源：stale-while-revalidate，配合 Vite 哈希文件名
registerRoute(
  ({ request, url }) => request.destination === 'style' || request.destination === 'script',
  new StaleWhileRevalidate()
);

// API 请求：网络优先
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    // V9.0: 仅缓存 200 状态码，移除 0（网络错误不应缓存到 API 缓存中，走 NetworkFirst 的 fallback 机制）
    plugins: [{ cacheableResponse: { statuses: [200] } }],
  })
);

// 签到/考试页：离线可用
registerRoute(
  ({ url }) => ['/check-in', '/exam'].includes(url.pathname),
  new StaleWhileRevalidate()
);
```

### 10.4 Zustand 持久化 (V7.0/V8.0/V10.0)

```typescript
// Zustand authStore 配置
// V7.0 变更：移除 persist 中间件。token 由 HTTP-Only Cookie 管理，不应写入 localStorage（XSS 窃取风险）
// V8.0 变更：移除 token/refreshToken 字段。认证状态统一通过 HTTP-Only Cookie 管理，authStore 仅保留 isAuthenticated/user/roles/permissions
// V10.0: 维持 V8.0 方案，authStore 不使用 persist 中间件
// HR 系统涉及薪资等敏感数据，必须使用 HTTP-Only Cookie 方案
import { create } from 'zustand';

// authStore 不再使用 persist 中间件
export const useAuthStore = create((set, get) => ({
  // ... 状态定义
  user: null,
  isAuthenticated: false,
  // ... 方法定义
}));

// 业务表单数据持久化（以入职模块为例）— 非敏感数据可使用 persist
// V10.0: 原 onboardingStore 已移除，表单草稿由 react-hook-form 的 defaultValues 管理，
// 如需持久化表单草稿，使用 zustand-middleware 单独创建 persist store
export const useOnboardingDraft = create(
  persist(
    (set, get) => ({
      currentStep: 0,
      formDraft: {} as Record<string, any>,
      uploadedDocIds: [] as string[],
      setCurrentStep: (step: number) => set({ currentStep: step }),
      setFormDraft: (draft: Record<string, any>) => set({ formDraft: draft }),
    }),
    {
      name: 'gbm-hr-onboarding-form',
    }
  )
);
```

### 10.5 ECharts 动态导入与加载策略 (V10.0 新增)

**问题：** Dashboard 是系统首页，ECharts 采用 React.lazy 动态导入，首次访问 Dashboard 时必然会触发加载，首屏优化效果有限。

**解决方案：**

1. **骨架屏占位**：ECharts 模块加载期间显示骨架屏（Ant Design Skeleton），避免布局抖动
2. **预加载策略**：用户首次登录成功后，在后台预加载 ECharts chunk，确保进入 Dashboard 时图表模块已就绪

```typescript
// useChartPreload.ts — ECharts 预加载 Hook
function useChartPreload() {
  useEffect(() => {
    // 用户认证成功后预加载 ECharts chunk
    // Vite 构建后 ECharts 会被打包为独立的 chunk
    import(/* webpackChunkName: "echarts" */ '@/components/charts/EChartsWrapper')
      .then(() => {
        // 预加载完成
      })
      .catch(() => {
        // 预加载失败不影响主流程
      });
  }, []);
}

// Dashboard 页面中使用
const EChartsWrapper = React.lazy(() =>
  import(/* webpackChunkName: "echarts" */ '@/components/charts/EChartsWrapper')
);

function AdminDashboard() {
  useChartPreload();

  return (
    <Suspense fallback={<ChartSkeleton />}>
      <EChartsWrapper chartData={data} />
    </Suspense>
  );
}

// 图表骨架屏组件
function ChartSkeleton() {
  return (
    <Card>
      <Skeleton active paragraph={{ rows: 4 }} title={{ width: '60%' }} />
    </Card>
  );
}
```

3. **加载状态过渡**：ECharts 模块加载完成后，Skeleton 平滑过渡为真实图表（使用 CSS opacity 动画，200ms 淡入）

---

## 11. 安全与性能

### 11.1 前端安全

| 安全措施 | 实现方式 |
|---------|---------|
| XSS 防护 | React 默认转义 + DOMPurify 富文本 |
| CSRF 防护 | 自定义请求头 + SameSite Cookie |
| 敏感数据 | 前端不存储明文敏感数据 |
| Token 管理 | HTTP-Only Cookie + 内存 Token |
| 权限控制 | 路由守卫 + 组件级权限指令 |
| 请求签名 | 敏感操作请求携带签名 |
| 文件上传 | 文件类型白名单 + 大小限制 + 病毒扫描 |

### 11.2 性能优化

| 优化手段 | 目标 |
|---------|------|
| 代码分割 | 按路由 lazy loading，首屏 < 300KB |
| 图片优化 | WebP 格式 + 懒加载 |
| 组件懒加载 | React.lazy + Suspense |
| 缓存策略 | SWR 模式，减少重复请求 |
| 防抖节流 | 搜索输入防抖 300ms，滚动节流 |
| Tree Shaking | 按需导入 Ant Design 组件 |
| 构建优化 | Vite 生产构建，gzip 压缩 |

### 11.3 性能指标

| 指标 | 目标值 |
|------|--------|
| 首次内容绘制 (FCP) | < 1.5s |
| 最大内容绘制 (LCP) | < 2.5s |
| 首次输入延迟 (FID) | < 100ms |
| 累积布局偏移 (CLS) | < 0.1 |
| 首屏加载 | < 3s (P95) |
| 路由切换 | < 300ms |

### 11.4 错误边界与全局异常处理 (V10.0 新增)

HR 系统涉及薪资/考勤等敏感数据，需要完善的错误日志和监控方案：

**一、ErrorBoundary 组件设计**

```typescript
// ErrorBoundary.tsx
import { Component, ErrorInfo, ReactNode } from 'react';
import { Result, Button, Divider } from 'antd';
import { errorReportingService } from '../services/errorReportingService';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    errorReportingService.report({
      error: error.message,
      stack: errorInfo.componentStack,
      url: window.location.href,
      userAgent: navigator.userAgent,
      timestamp: Date.now(),
    });
    this.props.onError?.(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <Result
          status="500"
          title="页面加载出错"
          subTitle="请刷新页面重试，如问题持续存在请联系系统管理员"
          extra={[
            <Button type="primary" key="refresh" onClick={() => window.location.reload()}>
              刷新页面
            </Button>,
            <Button key="back" onClick={() => window.history.back()}>
              返回上一页
            </Button>,
          ]}
        >
          <Divider />
          <details className="error-details">
            <summary>错误详情</summary>
            <pre>{this.state.error?.stack}</pre>
          </details>
        </Result>
      );
    }
    return this.props.children;
  }
}
```

**二、全局异常捕获**

```typescript
// main.tsx - 全局异常捕获
import { errorReportingService } from './services/errorReportingService';

window.addEventListener('unhandledrejection', (event) => {
  errorReportingService.report({
    error: event.reason?.message || String(event.reason),
    type: 'unhandled-rejection',
    url: window.location.href,
    timestamp: Date.now(),
  });
});

window.addEventListener('error', (event) => {
  errorReportingService.report({
    error: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    type: 'unhandled-error',
    timestamp: Date.now(),
  });
});
```

**三、错误上报服务**

```typescript
// errorReportingService.ts
interface ErrorReport {
  error: string;
  stack?: string;
  type?: 'unhandled-rejection' | 'unhandled-error' | 'component-error';
  url: string;
  userAgent?: string;
  filename?: string;
  lineno?: number;
  colno?: number;
  timestamp: number;
}

export const errorReportingService = {
  report: (report: ErrorReport) => {
    if (import.meta.env.DEV) {
      console.error('[Error Report]', report);
    } else {
      navigator.sendBeacon('/api/errors/report', JSON.stringify(report));
    }
  },
};
```

**四、Axios 拦截器错误处理**

```typescript
// apiClient.ts - 统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().clearSession();
      window.location.href = '/login';
    }
    if (error.response?.status === 403) {
      window.location.href = '/403';
    }
    if (error.response?.status >= 500) {
      notification.error({
        message: '服务端错误',
        description: '请稍后重试，如问题持续存在请联系系统管理员',
      });
      errorReportingService.report({
        error: `HTTP ${error.response.status}: ${error.response.statusText}`,
        url: error.config?.url || '',
        timestamp: Date.now(),
      });
    }
    return Promise.reject(error);
  },
);
```

---

*文档结束*
