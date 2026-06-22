# GBM AI Agent HR 智能人力管理系统 — 前端设计文档 (V17)

## 版本信息

| 字段 | 值 |
|------|-----|
| 文档名称 | GBM AI Agent HR 前端设计文档 |
| 版本号 | V17.0 |
| 基于 SRS | V15.0 |
| 日期 | 2026-06-15 |
| 作者 | 后旺 (HouWang) |
| 角色 | 前端架构师 |

## 修订说明

V16.0→V17.0：后荣持续 5 轮（V12-V16）因文档传输截断无法返回检验结果。本次精简文档体积：(a) 修订说明压缩为摘要式 (b) 代码示例精简为关键片段 (c) 删除重复性解释文字。内容无功能性变更，确保文档以完整形式交付并被后荣完整接收。

V12.0 以来的有效修订（V11→V12 后荣提出的 4 项疑问）已全部在 V12.0 完成修复：
1. authStore 与 React Query 边界澄清（第 4.2 节）
2. PWA 与移动端原生功能说明（第 10.1 节）
3. 电子签名移动端触摸支持（第 1.1 节和 5.2 节）
4. 文件分片哈希计算方案明确（第 5.3 节）

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
| CSS 方案 | Ant Design 5.x Token | - | ConfigProvider 管理全局 Design Token |
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
| 文件上传 | Ant Design Upload + 自定义分片逻辑 | 5.x | Upload 提供 UI 外壳，分片逻辑由自定义 Hook 实现 |
| PDF 预览 | react-pdf | - | 在线预览 PDF |
| 电子签名 | react-signature-canvas | - | 手写签名；基于 Canvas API 实现，原生支持鼠标和触摸事件，移动端触摸签名无需额外适配 |
| 无障碍 | @axe-core/react | - | 无障碍检测（仅开发环境） |
| PWA | workbox | 7.x | Service Worker |
| 日期选择 | dayjs | 2.x | 轻量日期库 |
| 拖拽 | @dnd-kit/core + @dnd-kit/sortable | 6.x | 拖拽排序（react-beautiful-dnd 已废弃，6.x 为当前最新稳定版本） |
| 通知 | Ant Design Notification | 5.x | 消息通知 |

### 1.1.1 依赖加载策略

| 类别 | 加载方式 | 包含包 |
|------|---------|--------|
| 核心依赖 | 首屏加载 | React, Ant Design, React Router, Zustand, Axios, @tanstack/react-query, dayjs |
| 按需加载 | React.lazy 动态导入 | react-pdf, react-signature-canvas, ECharts（约 800KB+ gzip，仅在 Dashboard 和报表页面按需加载） |

**构建期配置说明：**
- **workbox (PWA)**：Service Worker 为构建时注册的独立脚本，由 Vite 插件在构建阶段生成，非运行时条件导入
- **@axe-core/react (无障碍)**：开发期工具，仅开发环境生效，不包含在生产构建中。WCAG 2.1 AA 合规性通过代码规范、aria 属性、键盘操作支持等实现

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
│   ├── assets/
│   │   ├── images/
│   │   ├── icons/
│   │   └── styles/
│   │       └── global.css
│   ├── components/
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
│   │   │   ├── DataTable.tsx
│   │   │   ├── SearchFilter.tsx
│   │   │   ├── PaginationBar.tsx
│   │   │   ├── ExportButton.tsx
│   │   │   └── ImportDialog.tsx
│   │   ├── form/
│   │   │   ├── FormCard.tsx
│   │   │   ├── StepForm.tsx
│   │   │   ├── FileUpload.tsx
│   │   │   ├── ImageCropper.tsx
│   │   │   ├── SignaturePad.tsx
│   │   │   └── DatePickerRange.tsx
│   │   ├── feedback/
│   │   │   ├── ConfirmDialog.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   └── ErrorBoundary.tsx
│   │   └── layout/
│   │       ├── MainLayout.tsx
│   │       ├── PageHeader.tsx
│   │       ├── CardContainer.tsx
│   │       ├── TabContainer.tsx
│   │       ├── BottomTabBar.tsx
│   │       └── MobileLayout.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── usePermission.ts
│   │   ├── usePagination.ts
│   │   ├── useDebounce.ts
│   │   ├── useLocalStorage.ts
│   │   ├── useNotification.ts
│   │   ├── useFileUpload.ts       # 分片上传逻辑（SHA-256 校验、断点续传）
│   │   └── useChartPreload.ts     # ECharts 预加载
│   ├── stores/                    # Zustand 状态存储（仅 UI 交互状态）
│   │   ├── authStore.ts           # 认证 UI 状态
│   │   └── uiStore.ts             # 全局 UI 状态
│   ├── services/
│   │   ├── apiClient.ts
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
│   ├── pages/
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
│   │   │   ├── OnboardingPortal.tsx
│   │   │   ├── DocumentUpload.tsx
│   │   │   ├── IdentityVerification.tsx
│   │   │   ├── AgreementSign.tsx
│   │   │   ├── FaceCapture.tsx
│   │   │   └── OnboardingProgress.tsx
│   │   ├── training/
│   │   │   ├── TrainingPlan.tsx
│   │   │   ├── TrainingList.tsx
│   │   │   ├── TrainingDetail.tsx
│   │   │   ├── CheckIn.tsx
│   │   │   ├── ExamPage.tsx
│   │   │   ├── VideoCourse.tsx
│   │   │   ├── CertificateList.tsx
│   │   │   └── AuditMaterials.tsx
│   │   ├── attendance/
│   │   │   ├── AttendanceCalendar.tsx
│   │   │   ├── AttendanceSummary.tsx
│   │   │   ├── AnomalyList.tsx
│   │   │   ├── LeaveRequest.tsx
│   │   │   └── ShiftSchedule.tsx
│   │   ├── payroll/
│   │   │   ├── PayrollReview.tsx
│   │   │   ├── PayslipView.tsx
│   │   │   ├── PayrollRules.tsx
│   │   │   └── SalaryBudget.tsx
│   │   ├── performance/
│   │   │   ├── SelfEvaluation.tsx
│   │   │   ├── ReviewManagement.tsx
│   │   │   ├── PerformanceReport.tsx
│   │   │   └── RatingDistribution.tsx
│   │   ├── external/
│   │   │   ├── InjuryCaseList.tsx
│   │   │   ├── InjuryCaseDetail.tsx
│   │   │   ├── HousingFundList.tsx
│   │   │   └── GovernmentDeclaration.tsx
│   │   ├── employee/
│   │   │   ├── EmployeeList.tsx
│   │   │   ├── EmployeeProfile.tsx
│   │   │   ├── ResignationApply.tsx
│   │   │   ├── ResignationProcess.tsx
│   │   │   ├── CertificateRequest.tsx
│   │   │   └── ExpenseClaim.tsx
│   │   ├── agent/
│   │   │   ├── AgentDashboard.tsx
│   │   │   ├── AgentLogList.tsx
│   │   │   ├── AgentConfig.tsx
│   │   │   └── AgentAlert.tsx
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
│   ├── routes/
│   │   ├── index.tsx
│   │   ├── protectedRoute.tsx
│   │   ├── roleRoute.tsx
│   │   └── routeConfig.ts
│   ├── types/
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
│   ├── utils/
│   │   ├── format.ts
│   │   ├── validate.ts
│   │   ├── permission.ts
│   │   ├── download.ts
│   │   ├── qrCode.ts
│   │   └── constants.ts
│   ├── i18n/
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
│   ├── App.tsx
│   └── main.tsx
├── tests/
│   ├── unit/
│   ├── integration/
│   └── accessibility/
├── vite.config.ts
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
│   ├── /dashboard/admin
│   ├── /dashboard/hr
│   ├── /dashboard/manager
│   └── /dashboard/employee
│
├── /recruitment                    # 招聘管理
│   ├── /recruitment/jobs
│   ├── /recruitment/jobs/:id
│   ├── /recruitment/resumes
│   ├── /recruitment/resumes/:id
│   ├── /recruitment/import
│   ├── /recruitment/exams
│   ├── /recruitment/questions
│   └── /recruitment/talent-pool
│
├── /onboarding                     # 入职管理
│   ├── /onboarding/portal          # 新员工入职门户
│   ├── /onboarding/progress
│   └── /onboarding/list
│
├── /training                       # 培训管理
│   ├── /training/plans
│   ├── /training/list
│   ├── /training/:id
│   ├── /training/check-in          # 扫码签到（PWA）
│   ├── /training/exam              # 在线考试（PWA）
│   ├── /training/video
│   ├── /training/certificates
│   └── /training/audit
│
├── /attendance                     # 考勤管理
│   ├── /attendance/calendar
│   ├── /attendance/summary
│   ├── /attendance/anomalies
│   ├── /attendance/leave
│   └── /attendance/schedule
│
├── /payroll                        # 薪资管理
│   ├── /payroll/review             # 薪资审核（人事）
│   ├── /payroll/payslip            # 工资条（员工）
│   ├── /payroll/rules              # 薪资规则（管理员）
│   └── /payroll/budget             # 薪资预算（第三期）
│
├── /performance                    # 绩效管理
│   ├── /performance/evaluation
│   ├── /performance/review
│   ├── /performance/report
│   └── /performance/distribution
│
├── /external                       # 外务管理
│   ├── /external/injury
│   ├── /external/injury/:id
│   ├── /external/housing-fund
│   └── /external/declaration
│
├── /employee                       # 员工服务
│   ├── /employee/list
│   ├── /employee/:id
│   ├── /employee/resignation
│   ├── /employee/certificate
│   └── /employee/expense
│
├── /agent                          # Agent 管理（系统管理员）
│   ├── /agent/dashboard
│   ├── /agent/logs
│   ├── /agent/config
│   └── /agent/alerts
│
├── /system                         # 系统管理（系统管理员）
│   ├── /system/users
│   ├── /system/roles
│   ├── /system/audit
│   ├── /system/config
│   └── /system/backup
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

本系统采用 Zustand 作为客户端 UI 状态管理，@tanstack/react-query 作为服务端状态管理。

```
┌─────────────────────────────────────────────┐
│        UI State (Zustand - 仅 2 个 store)     │
│  ┌──────────┐ ┌──────────┐                  │
│  │ authStore│ │  uiStore │                  │
│  └──────────┘ └──────────┘                  │
├─────────────────────────────────────────────┤
│      Server State (React Query - 所有业务数据) │
│  招聘/入职/培训/考勤/薪资/绩效/Agent 数据      │
│  缓存策略、请求去重、自动重试                  │
│  列表缓存 5 分钟，详情缓存 1 分钟             │
├─────────────────────────────────────────────┤
│      Component Local State (useState)         │
│  表单字段值、模态框可见性、表格排序/筛选状态     │
└─────────────────────────────────────────────┘
```

**设计决策说明：**
- Zustand 仅保留 authStore（认证 UI 状态）和 uiStore（全局 UI 状态）两个 store
- 所有业务模块数据统一由 React Query 管理
- 原业务 store 中的 UI 状态（如 selectedResume、filterParams）迁移至页面级 useState
- 原 agentStore 中的 API 数据和 API 方法迁移至 React Query 的 useQuery/useMutation

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
  refreshSession: () => Promise<void>;
  clearSession: () => void;
}
```

**authStore 职责说明（V12 补充）：**
- authStore 存储的 isAuthenticated/user/roles/permissions 均为 **UI 展示状态**，用于控制界面渲染（如侧栏菜单权限、头像显示等）
- 这些字段来源于后端 `/api/auth/me` 接口响应，在 authStore 中的角色是 **缓存用户 UI 展示信息**，而非管理服务端状态
- 认证 Token 由 HTTP-Only Cookie 管理，前端 JavaScript 不可访问，不存在 XSS 窃取风险
- 真正的认证验证由后端中间件完成，前端仅根据 authStore 中的 UI 状态决定界面展示
- 用户信息如需重新获取（如角色变更），通过 React Query 的 `useQuery(['auth', 'me'], ...)` 调用，刷新后同步更新 authStore 中的 UI 状态

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

### 4.3 React Query 数据获取策略

所有数据请求统一通过 **@tanstack/react-query** 的 `useQuery` / `useMutation` 实现。

- **缓存策略**：列表数据缓存 5 分钟，详情数据缓存 1 分钟
- **乐观更新**：表单提交时先更新 UI，失败则回滚
- **自动重试**：网络错误自动重试 2 次，指数退避
- **请求取消**：组件卸载时自动取消未完成的请求
- **依赖查询**：mutation 后自动 invalid 相关查询

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// 查询：获取简历列表
function useResumeList(params: ResumeFilterParams) {
  return useQuery({
    queryKey: ['resumes', params],
    queryFn: () => apiClient.get('/api/recruitment/resumes', { params }),
    staleTime: 5 * 60 * 1000,
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
      queryClient.invalidateQueries({ queryKey: ['resumes'] });
    },
  });
}

// 使用示例
function ResumeListPage() {
  const { data, isLoading, error } = useResumeList({ page: 1, pageSize: 20 });
  const updateMutation = useUpdateResumeStatus();

  // 页面级本地状态
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

**Agent 模块数据管理示例（React Query 统一管理）**

```typescript
// 查询：获取 Agent 运行状态（30 秒自动轮询）
function useAgentStatus() {
  return useQuery({
    queryKey: ['agents', 'status'],
    queryFn: () => apiClient.get('/api/agent/status'),
    staleTime: 10 * 1000,
    refetchInterval: 30 * 1000,
    retry: 1,
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
```

### 4.4 Zustand 与 React Query 职责边界

| 维度 | Zustand (客户端状态) | React Query (服务端状态) |
|------|---------------------|------------------------|
| 职责范围 | 全局 UI 交互状态 | 所有 API 数据 |
| 包含 store | authStore、uiStore | 所有业务模块数据 |
| 典型内容 | isAuthenticated、user、roles、siderCollapsed、theme、language | 列表数据、详情数据、分页数据、统计数据、Agent 状态 |
| 生命周期 | 页面会话期间 | 缓存策略控制（staleTime/gcTime） |
| 持久化 | 非敏感数据可使用 persist 中间件（如 onboarding 表单草稿） | 不持久化，依赖缓存 |
| 数据来源 | 登录时一次性获取，角色变更时刷新 | 每次查询从后端 API 获取，支持缓存和自动刷新 |

**页面级 UI 状态说明：**
- 业务模块中的 UI 状态（如 selectedResume、filterParams、currentStep）使用页面级 useState 管理
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
  scroll?: { x?: string | number; y?: string | number };  // 虚拟滚动配置
}
```

**功能特性：** 内置分页/排序/筛选、行选择、列显隐控制、导出按钮、加载状态、空数据提示、操作列、虚拟滚动（默认 600px）

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

**应用场景：** 新员工入职引导、工伤申报、离职申请

#### QRCheckIn 扫码签到组件

```typescript
interface QRCheckInProps {
  trainingId: string;
  onSuccess: (result: CheckInResult) => void;
  onError: (error: Error) => void;
}
```

**功能：** 摄像头二维码扫描、签到成功/失败动画反馈、签到时间戳记录、防重复签到

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
  keyboardInteractive?: boolean;
  ariaLabel?: string;
  ariaDescribedBy?: string;
}
```

**移动端触摸支持说明（V12 补充）：**
- react-signature-canvas 基于 HTML Canvas API 实现，底层监听 `touchstart`/`touchmove`/`touchend` 触摸事件和 `mousedown`/`mousemove`/`mouseup` 鼠标事件
- 移动端触摸签名无需额外适配，Canvas 触摸事件为浏览器原生能力
- 签名画布支持多点触摸，自动处理触摸坐标转换

**无障碍支持：**
- 键盘操作：方向键控制画笔、Enter 确认、Escape 清空
- 完整 aria 属性：`role="img"`、`aria-label="电子签名区域"`、`aria-describedby`
- `aria-invalid` 在签名为空时标记为 true
- `tabindex="0"` 接收焦点，`:focus-visible` 样式提示

### 5.3 组件复用策略

#### FileUpload 文件上传组件

**实现方案：**
- Ant Design Upload 提供 UI 外壳（拖拽区域、进度条、文件列表），不提供分片上传功能
- 分片上传的完整逻辑由自定义 `useFileUpload` Hook 实现
- `FileUpload.tsx` 组合 Ant Design Upload UI + `useFileUpload` Hook

**文件哈希计算方案说明（V12 补充）：**
- 文件唯一标识采用 **SHA-256 算法**，使用浏览器原生的 **Web Crypto API** (`crypto.subtle.digest('SHA-256', data)`)
- 不使用 spark-md5 或 MD5：SHA-256 为浏览器原生 API，无需额外依赖；安全性优于 MD5；与后端文件去重和秒传机制保持一致
- Web Crypto API 在所有现代浏览器中均支持（Chrome 37+、Firefox 34+、Safari 7+、Edge 12+）
- 大文件哈希计算采用分片读取方式，避免一次性加载整个文件到内存

```typescript
interface FileUploadProps {
  accept?: string;
  maxFileSize?: number;           // 最大文件大小 (MB)
  chunkSize?: number;             // 单分片大小 (默认 5MB)
  maxConcurrent?: number;         // 并发上传分片数 (默认 3)
  breakpointStorage?: 'localStorage' | 'sessionStorage' | 'memory';
  maxRetries?: number;            // 单分片最大重试次数 (默认 3)
  retryDelay?: number;            // 重试退避基础延迟 (ms, 默认 1000)
  retryStrategy?: 'fixed' | 'exponential' | 'linear';
  onProgress?: (info: UploadProgressInfo) => void;
  showSpeed?: boolean;
  showETA?: boolean;
  onSuccess?: (file: File, response: any) => void;
  onError?: (file: File, error: UploadError) => void;
  onCompleted?: (result: UploadResult) => void;
}

interface UploadProgressInfo {
  percent: number;      // 总进度 (0-100)
  speed: number;        // 上传速度 (KB/s)
  loaded: number;       // 已上传字节数
  total: number;        // 总字节数
  eta: number;          // 预计剩余时间 (秒)
  currentChunk: number; // 当前分片序号
  totalChunks: number;  // 总分片数
  concurrentCount: number; // 当前并发上传数
}

interface UploadBreakpoint {
  fileHash: string;           // 文件哈希 (SHA-256)
  uploadedChunks: number[];   // 已上传成功的分片序号列表
  updatedAt: number;          // 最后更新时间戳
}

interface UploadError {
  code: string;               // CHUNK_FAILED / NETWORK_ERROR / SERVER_ERROR / FILE_TOO_LARGE
  message: string;
  chunkIndex?: number;
  retryCount?: number;
  recoverable: boolean;
}
```

**useFileUpload Hook 核心逻辑：**

```typescript
function useFileUpload(options: UseFileUploadOptions) {
  // 1. 文件哈希计算（Web Crypto API - SHA-256）
  async function calculateFileHash(file: File): Promise<string> {
    const chunkSize = 1024 * 1024; // 1MB per chunk
    let offset = 0;
    // 分片读取避免大文件内存溢出
    while (offset < file.size) {
      const chunk = await file.slice(offset, offset + chunkSize).arrayBuffer();
      // 使用 crypto.subtle.digest('SHA-256', ...) 逐块累积计算
      offset += chunkSize;
    }
    // 返回十六进制字符串
  }

  // 2. 文件分片切割（File.slice API）
  function getChunks(file: File, chunkSize: number): Blob[] {
    const chunks: Blob[] = [];
    for (let start = 0; start < file.size; start += chunkSize) {
      chunks.push(file.slice(start, start + chunkSize));
    }
    return chunks;
  }

  // 3. 断点续传（localStorage 存储已上传分片记录，24 小时过期）
  // 4. 并发控制（信号量模式，默认 3 并发，>100MB 自动降为 2）
  // 5. 失败重试（指数退避：retryDelay * 2^(N-1) ms，最多 3 次）

  return { upload, cancel, progress };
}
```

**工程化设计：**
1. **断点续传**：SHA-256 哈希作为文件唯一标识，已上传分片记录存储于 localStorage，页面刷新后通过文件哈希恢复断点，过期时间 24 小时
2. **并发控制**：同时上传分片数限制为 3（可配置），信号量模式管理并发，>100MB 自动降为 2
3. **失败重试**：单分片失败最多重试 3 次，指数退避策略，超过后标记为不可恢复错误
4. **进度反馈**：实时显示百分比、速度 (KB/s)、已上传/总大小、ETA、当前分片/总分片、并发数
5. **分片合并**：前端不直接合并，由后端接收全部分片后执行合并。流程：上传分片 → 全部完成 → 调用合并接口 → 返回文件 URI

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
│ 工作台   │  │  ┌─ 搜索栏 ────────────────────────┐       │  │
│ 招聘管理  │  │  ┌─ 操作按钮区 ───────────────────┐ │       │  │
│ 培训管理  │  │  │ [+新建] [导入] [导出] [批量]   │ │       │  │
│ 考勤管理  │  │  ├────────────────────────────────┤ │       │  │
│ 薪资管理  │  │  │         数据表格区域           │ │       │  │  ← Page Content
│ 员工服务  │  │  │                                │ │       │  │
│ Agent 管理│  │  └────────────────────────────────┘ │       │  │
│ 系统管理  │  │                                     │       │  │
│          │  └─────────────────────────────────────────────┘  │
├──────────┴───────────────────────────────────────────────────┤
│  © 2026 GBM AI Agent HR | 版本 2.0                            │  ← AppFooter (48px)
└──────────────────────────────────────────────────────────────┘
```

**布局参数：** 侧栏 200px（展开）/ 64px（折叠）、顶栏 64px、底栏 48px、内容区自适应

### 6.2 不同角色的侧栏菜单

#### 系统管理员

```
工作台
├── 招聘管理（岗位管理、简历管理、考试管理、人才库）
├── 入职管理（入职进度、入职名单）
├── 培训管理（培训计划、培训列表、证书管理、体系审核）
├── 考勤管理（考勤汇总、异常处理）
├── 薪资管理（薪资审核、薪资规则）
├── 绩效管理（考核管理、绩效报告）
├── 外务管理（工伤管理、公积金管理）
├── 员工服务（员工列表、证明开具）
├── Agent 管理（监控面板、执行日志、参数配置、告警中心）
└── 系统管理（用户管理、角色管理、审计日志、系统配置、备份恢复）
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
├── 绩效考核 → 下属考核
└── 培训管理 → 部门培训
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

**移动端布局参数：** 顶栏 56px、底部 Tab 栏 56px、单列卡片式布局、表格转卡片列表、手势左滑返回和下拉刷新、BottomTabBar 最多 5 个 Tab

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
│      │  [👤]  账号/邮箱                  │          │
│      │  [🔒]  密码                       │          │
│      │  □  记住我    忘记密码？          │          │
│      │  ┌─────── 登 录 ─────────┐       │          │
│      │  └───────────────────────┘       │          │
│      │  新用户？前往入职门户 →            │          │
│      └──────────────────────────────────┘          │
│                                                    │
│         [中] / [EN]                                │
└────────────────────────────────────────────────────┘
```

**交互流程：** 输入账号密码 → 系统校验 → 如需 MFA 跳转验证页 → 验证通过跳转 Dashboard

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
│  │  🟢 招聘 Agent 正常  │ │  □ 薪资审核 (3人)           │ │
│  │  🟢 入职 Agent 正常  │ │  □ 工伤申报 (1件)           │ │
│  │  🟡 RPA Agent 告警   │ │  □ 证书到期提醒 (5个)       │ │
│  │  成功率: 97.3%       │ │  □ 面试安排 (2场)           │ │
│  └──────────────────────┘ └──────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐   │
│  │  近 30 天 HR 业务趋势 (折线图: 入职数/离职数/招聘数)   │   │
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
│  欢迎加入 GBM 公司！ 请按照以下步骤完成入职手续                │
├─────────────────────────────────────────────────────────────┤
│  入职进度:                                                  │
│  ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐                            │
│  │✓ │→ │● │→ │○ │→ │○ │→ │○ │                            │
│  └──┘  └──┘  └──┘  └──┘  └──┘                            │
│  基本信息  上传证件  签署协议  人脸采集  完成               │
├─────────────────────────────────────────────────────────────┤
│  步骤 2: 上传证件材料                                       │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  身份证正面       │  │  身份证反面       │               │
│  │  [📷拍照] [📁选择]│  │  [📷拍照] [📁选择]│               │
│  │  ✓ 已上传        │  │  ⏳ 待上传        │               │
│  └──────────────────┘  └──────────────────┘               │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  学历证书         │  │  证件照          │               │
│  │  [📷拍照] [📁选择]│  │  [📷拍照] [📁选择]│               │
│  │  ⏳ 待上传        │  │  ⏳ 待上传        │               │
│  └──────────────────┘  └──────────────────┘               │
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
│  │     原因: 公积金网站改版，部分元素不可见               │   │
│  │ 🟢 薪资 Agent         运行中 | 今日: 1 次   | 成功: 100%│   │
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

1. **用户登录与身份认证流程**：所有字段可键盘操作、错误提示关联对应输入框、MFA 验证码输入框自动聚焦
2. **人事专员审核待办事项流程**：待办列表可键盘导航、审核按钮有明确 aria-label、结果变化通过 aria-live 播报
3. **工资条查看与导出流程**：表格支持键盘导航、导出按钮有明确描述、导出进度通过 aria-busy 反馈
4. **员工自助证明申请流程**：证明类型选择可键盘操作、上传区域支持拖拽和键盘操作、状态变化有视觉和听觉反馈
5. **扫码签到流程**：支持屏幕阅读器、签到成功/失败有明确反馈、超时提示有合理倒计时

### 8.3 无障碍测试策略

- 开发阶段：`@axe-core/react` 集成到测试中
- CI 阶段：Playwright 无障碍自动化测试
- 发布前：手动使用 NVDA/JAWS 屏幕阅读器测试
- 定期：WAVE 浏览器插件全页面扫描

### 8.4 移动端无障碍

| 要求 | 实现方式 |
|------|---------|
| 触摸目标尺寸 | 所有可交互元素最小尺寸 ≥ 44×44px（WCAG 2.5.5） |
| 手势键盘替代 | 左滑返回提供按钮替代、下拉刷新提供刷新按钮 |
| 横屏布局 | 横屏模式下布局自动适配，焦点管理遵循 Tab 顺序 |
| 触摸反馈 | 按压态视觉反馈（opacity 变化或颜色变化） |
| 长按菜单 | 长按操作提供右键菜单键盘替代方案 |
| 滑动操作 | 卡片滑动删除提供按钮式操作入口 |

**移动端无障碍测试：** 使用 VoiceOver/TalkBack 验证触摸目标可读性；验证所有手势操作均有键盘/按钮替代方案；横屏模式下验证焦点顺序与布局适配

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
│   ├── common.json         # 通用文本
│   ├── recruitment.json    # 招聘模块
│   ├── onboarding.json     # 入职模块
│   ├── training.json       # 培训模块
│   ├── attendance.json     # 考勤模块
│   ├── payroll.json        # 薪资模块
│   ├── performance.json    # 绩效模块
│   ├── external.json       # 外务模块
│   ├── employee.json       # 员工模块
│   ├── agent.json          # Agent 模块
│   └── system.json         # 系统模块
└── en/
    ├── common.json
    ├── recruitment.json
    └── ... (同上)
```

### 9.3 格式适配

```typescript
// 日期格式
const formatDate = (date: Date, lang: string): string => {
  if (lang === 'zh-CN') return `${date.getFullYear()}年${date.getMonth()+1}月${date.getDate()}日`;
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
};

// 金额格式
const formatCurrency = (amount: number, lang: string): string => {
  if (lang === 'zh-CN') return `¥${amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`;
  return `$${amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
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

**SRS V15.0 移动端需求对照说明（V12 补充）：**
- SRS V15.0 4.3 节要求「支持移动端浏览与 PC 端使用」—— 此为 Web/PWA 要求，非原生应用要求
- SRS V15.0 5.1.6 节摄像头接口形态明确为「WebRTC 实时视频流或硬件 SDK」—— 确认采用 Web 技术栈
- SRS V15.0 中无 GPS 定位签到要求，考勤数据采集来自打卡设备（指纹、人脸、IC 卡、APP 等多类终端），非浏览器端 GPS
- PWA 方案完全满足 SRS 要求，无需开发原生应用

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
import { registerRoute } from 'workbox-routing';
import { NetworkFirst, StaleWhileRevalidate } from 'workbox-strategies';

// 应用壳资源：stale-while-revalidate
registerRoute(
  ({ request }) => request.destination === 'style' || request.destination === 'script',
  new StaleWhileRevalidate()
);

// API 请求：网络优先，仅缓存 200 状态码
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    plugins: [{ cacheableResponse: { statuses: [200] } }],
  })
);

// 签到/考试页：离线可用
registerRoute(
  ({ url }) => ['/check-in', '/exam'].includes(url.pathname),
  new StaleWhileRevalidate()
);
```

### 10.4 Zustand 持久化

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// authStore 不使用 persist 中间件（token 由 HTTP-Only Cookie 管理，不应写入 localStorage）
export const useAuthStore = create((set, get) => ({
  user: null,
  isAuthenticated: false,
  // ... 方法定义
}));

// 非敏感业务表单草稿可使用 persist（如入职模块）
export const useOnboardingDraft = create(
  persist(
    (set) => ({
      currentStep: 0,
      formDraft: {} as Record<string, any>,
      uploadedDocIds: [] as string[],
      setCurrentStep: (step: number) => set({ currentStep: step }),
      setFormDraft: (draft: Record<string, any>) => set({ formDraft: draft }),
    }),
    { name: 'gbm-hr-onboarding-form' }
  )
);
```

### 10.5 ECharts 动态导入与加载策略

**问题：** Dashboard 是系统首页，ECharts 采用 React.lazy 动态导入，首次访问必然触发加载，首屏优化效果有限。

**解决方案：**
1. **骨架屏占位**：加载期间显示 Ant Design Skeleton，避免布局抖动
2. **预加载策略**：用户首次登录成功后，后台预加载 ECharts chunk
3. **加载状态过渡**：加载完成后 Skeleton 平滑过渡为真实图表（CSS opacity 动画 200ms 淡入）

```typescript
// useChartPreload.ts
function useChartPreload() {
  useEffect(() => {
    import('@/components/charts/EChartsWrapper')
      .then(() => {})
      .catch(() => {});
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

function ChartSkeleton() {
  return (
    <Card>
      <Skeleton active paragraph={{ rows: 4 }} title={{ width: '60%' }} />
    </Card>
  );
}
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

### 11.4 错误边界与全局异常处理

**ErrorBoundary 组件设计：**

```typescript
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
            <Button type="primary" key="refresh" onClick={() => window.location.reload()}>{'刷新页面'}</Button>,
            <Button key="back" onClick={() => window.history.back()}>{'返回上一页'}</Button>,
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

**全局异常捕获（main.tsx）：**

```typescript
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

**错误上报服务：**

```typescript
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

**Axios 拦截器错误处理（apiClient.ts）：**

```typescript
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
      notification.error({ message: '服务端错误', description: '请稍后重试' });
      errorReportingService.report({
        error: `HTTP ${error.response.status}: ${error.response.statusText}`,
        url: error.config?.url || '',
        timestamp: Date.now(),
      });
    }
    return Promise.reject(error);
  }
);
```

---

*文档结束*
