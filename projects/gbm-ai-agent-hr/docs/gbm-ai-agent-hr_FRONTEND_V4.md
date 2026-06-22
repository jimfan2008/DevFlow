# GBM AI Agent HR 智能人力管理系统 — 前端设计文档 (V4)

## 版本信息

| 字段 | 值 |
|------|-----|
| 文档名称 | GBM AI Agent HR 前端设计文档 |
| 版本号 | V5.0 |
| 基于 SRS | V15.0 |
| 日期 | 2026-06-12 |
| 作者 | 后旺 (HouWang) |
| 角色 | 前端架构师 |

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
| 虚拟列表 | react-window | - | 长列表虚拟滚动 |
| 文件上传 | Ant Design Upload | 5.x | 支持分片上传 |
| PDF 预览 | react-pdf | - | 在线预览 PDF |
| 电子签名 | react-signature-canvas | - | 手写签名 |
| 无障碍 | @axe-core/react | - | 无障碍检测 |
| PWA | workbox | 7.x | Service Worker |
| 日期选择 | dayjs | 2.x | 轻量日期库 |
| 拖拽 | @dnd-kit/core + @dnd-kit/sortable | 8.x | 拖拽排序（react-beautiful-dnd 已废弃） |
| 通知 | Ant Design Notification | 5.x | 消息通知 |

### 1.1.1 依赖加载策略

| 类别 | 加载方式 | 包含包 |
|------|---------|--------|
| 核心依赖 | 首屏加载 | React, Ant Design, React Router, Zustand, Axios, @tanstack/react-query, dayjs, ECharts |
| 按需加载 | React.lazy 动态导入 | react-pdf, react-signature-canvas |
| 可选功能 | 条件加载 | @axe-core/react(仅开发环境), workbox(仅 PWA 页面) |

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
│   │       ├── global.css
│   │       ├── variables.css
│   │       └── reset.css
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
│   │   │   ├── FileUpload.tsx     # 文件上传组件
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
│   │   └── useFileUpload.ts
│   ├── stores/                    # Zustand 状态存储
│   │   ├── authStore.ts           # 认证状态（token、用户、权限）
│   │   ├── uiStore.ts             # UI 状态（侧栏、主题、语言、通知）
│   │   ├── recruitmentStore.ts    # 招聘模块状态
│   │   ├── onboardingStore.ts     # 入职模块状态
│   │   ├── trainingStore.ts       # 培训模块状态
│   │   ├── attendanceStore.ts     # 考勤模块状态
│   │   ├── payrollStore.ts        # 薪资模块状态
│   │   ├── performanceStore.ts    # 绩效模块状态
│   │   └── agentStore.ts          # Agent 运行状态
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

### 4.1 状态分层设计

本系统采用 Zustand 作为客户端状态管理，@tanstack/react-query 作为服务端状态管理。状态分为以下层级：

```
┌─────────────────────────────────────────────┐
│              Global State (Zustand)           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ authStore│ │uiStore  │ │agentStore│    │
│  └──────────┘ └──────────┘ └──────────┘    │
├─────────────────────────────────────────────┤
│          Business State (Zustand)            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ recruit  │ │onboard   │ │training  │    │
│  │ Store    │ │Store     │ │Store     │    │
│  └──────────┘ └──────────┘ └──────────┘    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ attend   │ │payroll   │ │perform   │    │
│  │ Store    │ │Store     │ │Store     │    │
│  └──────────┘ └──────────┘ └──────────┘    │
├─────────────────────────────────────────────┤
│        Server State (React Query)            │
│  - 缓存策略、请求去重、自动重试              │
│  - 列表数据缓存 5 分钟，详情数据缓存 1 分钟  │
├─────────────────────────────────────────────┤
│        Component Local State (useState)      │
│  - 表单字段值                                │
│  - 模态框可见性                              │
│  - 表格排序/筛选状态                         │
└─────────────────────────────────────────────┘
```

### 4.2 核心 Store 设计

#### authStore.ts

```typescript
interface AuthState {
  // 状态
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  mfaRequired: boolean;
  mfaMethod: 'sms' | 'email' | 'totp' | null;

  // 用户信息
  user: UserInfo | null;
  roles: Role[];
  permissions: string[];

  // 动作
  login: (username: string, password: string) => Promise<void>;
  verifyMFA: (code: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  clearSession: () => void;
}
```

#### uiStore.ts

```typescript
interface UIState {
  // 侧栏
  siderCollapsed: boolean;
  toggleSider: () => void;

  // 主题
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;

  // 语言
  language: 'zh-CN' | 'en';
  setLanguage: (lang: 'zh-CN' | 'en') => void;

  // 通知
  notifications: NotificationItem[];
  unreadCount: number;
  markAsRead: (id: string) => void;
  clearNotifications: () => void;

  // 面包屑
  breadcrumb: BreadcrumbItem[];
  setBreadcrumb: (items: BreadcrumbItem[]) => void;
}
```

#### 业务 Store 拆分设计

业务状态按模块拆分为独立的 Store 文件，各模块状态解耦，避免单一文件过于庞大：

##### recruitmentStore.ts

```typescript
interface RecruitmentState {
  selectedJob: JobPosition | null;
  selectedResume: Resume | null;
  filterParams: ResumeFilterParams;
  setSelectedJob: (job: JobPosition | null) => void;
  setSelectedResume: (resume: Resume | null) => void;
  setFilterParams: (params: Partial<ResumeFilterParams>) => void;
}
```

##### onboardingStore.ts

```typescript
interface OnboardingState {
  currentStep: number;
  uploadedDocs: Document[];
  setCurrentStep: (step: number) => void;
  addUploadedDoc: (doc: Document) => void;
  removeUploadedDoc: (docId: string) => void;
}
```

##### trainingStore.ts

```typescript
interface TrainingState {
  selectedPlan: TrainingPlan | null;
  selectedSession: TrainingSession | null;
  setSelectedPlan: (plan: TrainingPlan | null) => void;
  setSelectedSession: (session: TrainingSession | null) => void;
}
```

##### attendanceStore.ts

```typescript
interface AttendanceState {
  selectedDate: Date;
  filterParams: AttendanceFilterParams;
  setSelectedDate: (date: Date) => void;
  setFilterParams: (params: Partial<AttendanceFilterParams>) => void;
}
```

##### payrollStore.ts

```typescript
interface PayrollState {
  selectedMonth: string;
  reviewStatus: 'pending' | 'approved' | 'rejected';
  setSelectedMonth: (month: string) => void;
  setReviewStatus: (status: 'pending' | 'approved' | 'rejected') => void;
}
```

##### performanceStore.ts

```typescript
interface PerformanceState {
  selectedEvaluation: Evaluation | null;
  filterParams: PerformanceFilterParams;
  setSelectedEvaluation: (evaluation: Evaluation | null) => void;
  setFilterParams: (params: Partial<PerformanceFilterParams>) => void;
}
```

#### agentStore.ts

```typescript
interface AgentState {
  // Agent 运行状态
  agents: AgentStatus[];
  lastUpdated: Date | null;

  // 告警
  alerts: AgentAlert[];
  unreadAlertCount: number;

  // 动作
  refreshStatus: () => Promise<void>;
  acknowledgeAlert: (alertId: string) => Promise<void>;
  restartAgent: (agentName: string) => Promise<void>;
  getAgentLogs: (agentName: string, limit: number) => Promise<void>;
}
```

### 4.3 数据获取策略

所有数据请求统一通过 **@tanstack/react-query** 的 `useQuery` / `useMutation` 实现，不使用自定义 `useApi` Hook。

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
  const { data, isLoading, error } = useResumeList({ page: 1, pageSize: 20 });
  const updateMutation = useUpdateResumeStatus();

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
    />
  );
}
```

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
}
```

**功能特性**：
- 内置分页、排序、筛选
- 行选择（单选/多选）
- 列显隐控制
- 导出按钮（Excel/CSV）
- 加载状态
- 空数据提示
- 操作列（编辑、删除、查看）

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

**应用场景**：
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

**功能**：
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

**无障碍支持**：
- 支持键盘操作：方向键控制画笔位置绘制、Enter 确认签名、Escape 清空签名
- 完整的 aria 属性：`role="img"`、`aria-label="电子签名区域"`、`aria-describedby` 指向使用说明
- `aria-invalid` 在签名为空时标记为 true
- 签名区域支持 `tabindex="0"` 接收焦点，`:focus-visible` 样式提示

### 5.3 组件复用策略

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

**布局参数**：
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

**移动端布局参数**：
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

**交互流程**：
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
import { CacheFirst, NetworkFirst, StaleWhileRevalidate } from 'workbox-strategies';

// 静态资源：缓存优先
registerRoute(
  ({ request, url }) => request.destination === 'style' || request.destination === 'script',
  new CacheFirst()
);

// API 请求：网络优先
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    plugins: [{ cacheableResponse: { statuses: [0, 200] } }],
  })
);

// 签到/考试页：离线可用
registerRoute(
  ({ url }) => ['/check-in', '/exam'].includes(url.pathname),
  new StaleWhileRevalidate()
);
```

```typescript
// Zustand persist 中间件配置
// authStore 和业务表单数据使用 localStorage 持久化，支持离线使用
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// authStore 持久化配置
export const useAuthStore = create(
  persist(
    (set, get) => ({
      // ... 状态定义
    }),
    {
      name: 'gbm-hr-auth',           // localStorage key
      partialize: (state) => ({       // 仅持久化必要字段
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// 业务表单数据持久化（以入职模块为例）
export const useOnboardingStore = create(
  persist(
    (set, get) => ({
      currentStep: 0,
      uploadedDocs: [],
      // ...
    }),
    {
      name: 'gbm-hr-onboarding-form',
    }
  )
);
```

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
| 虚拟列表 | 长列表使用 react-window |
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

---

*文档结束*