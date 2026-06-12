# GBM AI Agent HR 智能人力管理系统 —— 前端设计文档 (V2)

## 版本信息

| 版本号 | 日期 | 作者 | 说明 |
|--------|------|------|------|
| 2.0 | 2026-06-12 | 后旺 | 基于 SRS V15 纯净版重新设计：修复前端架构完整性、无障碍访问 (WCAG 2.1 AA) 设计、多语言国际化 (i18n) 支持、降级模式前端适配 |

---

## 1. 前端技术栈

### 1.1 核心技术选型

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|---------|
| 框架 | React | 18.x | Hooks 模式、并发特性、生态成熟 |
| 类型系统 | TypeScript | 5.x | 编译时类型检查，减少运行时错误 |
| 构建工具 | Vite | 5.x | 快速冷启动、HMR 热更新、原生 ESM |
| UI 组件库 | Ant Design | 5.x | 企业级组件、Token 主题系统、无障碍支持完善 |
| 移动端 | Taro | 3.x + React | 一套代码多端 (iOS/Android/微信小程序) |
| 状态管理 | Zustand | 4.x | 轻量级、Hook API、无 Provider 嵌套 |
| 路由 | React Router | 6.x | 声明式路由、嵌套路由、数据加载器 |
| HTTP 客户端 | Axios | 1.x | 拦截器、请求取消、超时控制 |
| 数据请求 | React Query (TanStack Query) | 5.x | 服务端状态管理、缓存、自动重试 |
| 表单 | React Hook Form + Zod | 最新版 | 高性能表单、Zod 运行时校验 |
| 可视化 | ECharts | 5.x | 丰富图表类型、支持无障碍 |
| 国际化 | i18next + react-i18next | 最新版 | 双语 (简中/英) 支持、命名空间、插值 |
| 样式 | CSS Modules + Tailwind CSS | — | 模块化样式 + 原子化类名 |
| 图标 | @ant-design/icons | — | 与 Ant Design 风格一致 |
| 测试 | Vitest + React Testing Library | — | 单元测试 + 组件测试 |
| E2E 测试 | Playwright | — | 跨浏览器 E2E 测试 |
| 无障碍检测 | axe-core + WAVE | — | WCAG 2.1 AA 自动化检测 |

### 1.2 项目结构

```
gbm-hr-frontend/
├── public/                        # 静态资源
│   ├── favicon.ico
│   ├── manifest.json             # PWA manifest
│   └── robots.txt
├── src/
│   ├── assets/                   # 全局静态资源
│   │   ├── images/
│   │   ├── fonts/
│   │   └── styles/
│   │       ├── global.css        # 全局样式
│   │       ├── variables.css     # CSS 变量 (主题色等)
│   │       └── reset.css         # 样式重置
│   ├── components/               # 通用组件
│   │   ├── common/               # 基础组件
│   │   │   ├── AppHeader.tsx
│   │   │   ├── AppSidebar.tsx
│   │   │   ├── AppFooter.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── ErrorBoundary.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   └── ConfirmDialog.tsx
│   │   ├── form/                 # 表单组件
│   │   │   ├── FormInput.tsx
│   │   │   ├── FormSelect.tsx
│   │   │   ├── FormDatePicker.tsx
│   │   │   ├── FormUpload.tsx
│   │   │   ├── FormSignature.tsx  # 手写签名组件
│   │   │   └── FormCamera.tsx     # 摄像头采集组件
│   │   ├── data/                 # 数据展示组件
│   │   │   ├── DataTable.tsx      # 可排序/筛选/分页表格
│   │   │   ├── DataCard.tsx
│   │   │   ├── StatisticsPanel.tsx
│   │   │   └── Timeline.tsx
│   │   ├── chart/                # 图表组件
│   │   │   ├── LineChart.tsx
│   │   │   ├── BarChart.tsx
│   │   │   ├── PieChart.tsx
│   │   │   └── RadarChart.tsx
│   │   ├── notification/         # 通知组件
│   │   │   ├── Toast.tsx
│   │   │   ├── NotificationBadge.tsx
│   │   │   └── MessageCenter.tsx
│   │   └── layout/               # 布局组件
│   │       ├── PageLayout.tsx
│   │       ├── CardLayout.tsx
│   │       └── DrawerLayout.tsx
│   ├── pages/                    # 页面组件 (按模块划分)
│   │   ├── auth/                 # 认证相关
│   │   │   ├── Login.tsx
│   │   │   ├── MFAVerify.tsx
│   │   │   ├── ForgotPassword.tsx
│   │   │   └── RegisterQr.tsx    # 扫码注册/入职入口
│   │   ├── dashboard/            # 仪表盘
│   │   │   ├── HrDashboard.tsx       # 人事专员工作台
│   │   │   ├── ManagerDashboard.tsx  # 部门主管工作台
│   │   │   ├── EmployeeDashboard.tsx # 员工自助门户
│   │   │   └── AdminDashboard.tsx    # 系统管理员仪表盘
│   │   ├── recruitment/          # 招聘管理
│   │   │   ├── JobPostManage.tsx
│   │   │   ├── ResumeList.tsx
│   │   │   ├── ResumeDetail.tsx
│   │   │   ├── ResumeScoreView.tsx
│   │   │   ├── ExamManage.tsx
│   │   │   ├── ExamPreview.tsx
│   │   │   ├── ExamTake.tsx          # 考生答题界面
│   │   │   ├── ScoreReport.tsx
│   │   │   └── TalentPool.tsx
│   │   ├── onboarding/           # 入职管理
│   │   │   ├── OnboardingPortal.tsx    # 新员工入职引导
│   │   │   ├── DocumentUpload.tsx
│   │   │   ├── OcrPreview.tsx
│   │   │   ├── AgreementSign.tsx
│   │   │   └── FaceCapture.tsx
│   │   ├── training/             # 培训管理
│   │   │   ├── TrainingPlan.tsx
│   │   │   ├── CheckIn.tsx         # 扫码签到
│   │   │   ├── TrainingExam.tsx
│   │   │   ├── VideoPlayer.tsx
│   │   │   ├── CertificateView.tsx
│   │   │   └── AuditPackage.tsx    # 体系审核资料
│   │   ├── attendance/           # 考勤管理
│   │   │   ├── AttendanceCalendar.tsx
│   │   │   ├── AttendanceSummary.tsx
│   │   │   ├── AnomalyList.tsx
│   │   │   └── AnomalyReport.tsx
│   │   ├── payroll/              # 薪资管理
│   │   │   ├── PayrollConfig.tsx
│   │   │   ├── PayrollCalcView.tsx
│   │   │   ├── PayrollReview.tsx    # 人事专员审核界面
│   │   │   ├── PayslipView.tsx      # 工资条查看
│   │   │   └── PayrollExport.tsx
│   │   ├── performance/          # 绩效管理
│   │   │   ├── SelfEvaluation.tsx
│   │   │   ├── ManagerReview.tsx
│   │   │   ├── PerformanceSummary.tsx
│   │   │   └── PerformanceTrend.tsx
│   │   ├── external/             # 外务管理
│   │   │   ├── InjuryCase.tsx
│   │   │   ├── HousingFund.tsx
│   │   │   └── GovDeclaration.tsx
│   │   ├── resignation/          # 离职管理
│   │   │   ├── ResignApply.tsx
│   │   │   ├── HandoverChecklist.tsx
│   │   │   └── ResignCertView.tsx
│   │   ├── certificate/          # 证明自助
│   │   │   ├── CertApply.tsx
│   │   │   ├── CertPreview.tsx
│   │   │   └── CertHistory.tsx
│   │   └── admin/                # 系统管理
│   │       ├── UserManage.tsx
│   │       ├── RoleManage.tsx
│   │       ├── AgentMonitor.tsx     # Agent 运行监控
│   │       ├── AgentParamConfig.tsx # Agent 参数配置
│   │       ├── AuditLog.tsx
│   │       ├── SystemConfig.tsx
│   │       └── AiCostReport.tsx    # AI 费用报表
│   ├── stores/                   # Zustand 状态管理
│   │   ├── authStore.ts          # 认证状态
│   │   ├── userStore.ts          # 用户信息
│   │   ├── uiStore.ts            # UI 状态 (sidebar、theme)
│   │   ├── notificationStore.ts  # 通知状态
│   │   └── agentStore.ts         # Agent 运行状态
│   ├── services/                 # API 服务层
│   │   ├── apiClient.ts          # Axios 实例配置
│   │   ├── authService.ts
│   │   ├── recruitmentService.ts
│   │   ├── onboardingService.ts
│   │   ├── trainingService.ts
│   │   ├── attendanceService.ts
│   │   ├── payrollService.ts
│   │   ├── performanceService.ts
│   │   ├── externalService.ts
│   │   ├── certificateService.ts
│   │   └── adminService.ts
│   ├── hooks/                    # 自定义 Hooks
│   │   ├── useAuth.ts
│   │   ├── usePermission.ts
│   │   ├── useMfa.ts
│   │   ├── useWebSocket.ts       # Agent 实时状态推送
│   │   ├── useFileUpload.ts
│   │   ├── useCamera.ts          # 摄像头采集 Hook
│   │   ├── useQrCode.ts          # QR 码生成/解析
│   │   └── useSignature.ts       # 手写签名 Hook
│   ├── utils/                    # 工具函数
│   │   ├── format.ts             # 日期/金额/数字格式
│   │   ├── validators.ts         # 表单验证规则
│   │   ├── constants.ts          # 常量定义
│   │   └── accessibility.ts      # 无障碍工具函数
│   ├── i18n/                     # 国际化
│   │   ├── index.ts              # i18n 配置
│   │   ├── zh-CN.json            # 简体中文
│   │   └── en-US.json            # 英语
│   ├── types/                    # TypeScript 类型定义
│   │   ├── api.ts                # API 响应类型
│   │   ├── employee.ts
│   │   ├── recruitment.ts
│   │   ├── attendance.ts
│   │   ├── payroll.ts
│   │   ├── performance.ts
│   │   └── agent.ts
│   ├── routes/                   # 路由配置
│   │   ├── index.tsx             # 路由入口
│   │   ├── protectedRoute.tsx    # 权限路由守卫
│   │   └── routes.ts             # 路由定义表
│   ├── App.tsx                   # 应用根组件
│   └── main.tsx                  # 应用入口
├── tests/                        # 测试文件
│   ├── unit/                     # 单元测试
│   ├── integration/              # 集成测试
│   ├── e2e/                      # E2E 测试
│   └── a11y/                     # 无障碍测试
├── vite.config.ts                # Vite 配置
├── tsconfig.json                 # TypeScript 配置
├── tailwind.config.js            # Tailwind 配置
├── package.json
└── README.md
```

---

## 2. 路由设计

### 2.1 路由表

| 路径 | 页面 | 角色 | 说明 |
|------|------|------|------|
| `/login` | Login | 所有 | 登录页 |
| `/mfa-verify` | MFAVerify | 管理员/外务专员 | 二因子认证页 |
| `/forgot-password` | ForgotPassword | 所有 | 密码重置 |
| `/qr/:token` | QrEntry | 所有 | 扫码入口 (考试/签到/入职) |
| `/dashboard` | Dashboard | 所有 | 仪表盘 (按角色渲染不同内容) |
| `/dashboard/hr` | HrDashboard | 人事专员 | 人事专员工作台 |
| `/dashboard/manager` | ManagerDashboard | 部门主管 | 部门主管工作台 |
| `/dashboard/employee` | EmployeeDashboard | 在职员工 | 员工自助门户 |
| `/dashboard/admin` | AdminDashboard | 系统管理员 | 系统管理员仪表盘 |
| `/recruitment/jobs` | JobPostManage | 人事专员 | 招聘信息管理 |
| `/recruitment/resumes` | ResumeList | 人事专员 | 简历列表 |
| `/recruitment/resumes/:id` | ResumeDetail | 人事专员 | 简历详情+评分 |
| `/recruitment/exams` | ExamManage | 人事专员 | 考试管理 |
| `/recruitment/exams/:id/preview` | ExamPreview | 人事专员 | 试卷预览 |
| `/recruitment/exams/:id/take` | ExamTake | 候选人 | 在线考试 |
| `/recruitment/scores` | ScoreReport | 人事专员 | 成绩报告 |
| `/recruitment/talent-pool` | TalentPool | 人事专员 | 人才简历库 |
| `/onboarding/:token` | OnboardingPortal | 新员工 | 入职引导门户 |
| `/onboarding/documents` | DocumentUpload | 新员工 | 证件上传 |
| `/onboarding/sign` | AgreementSign | 新员工 | 协议签署 |
| `/onboarding/face` | FaceCapture | 新员工 | 人脸采集 |
| `/training/plans` | TrainingPlan | 人事专员 | 培训计划 |
| `/training/checkin/:code` | CheckIn | 受训员工 | 扫码签到 |
| `/training/exam/:id` | TrainingExam | 受训员工 | 培训考试 |
| `/training/videos/:id` | VideoPlayer | 在职员工 | 培训视频 |
| `/training/certificates` | CertificateView | 在职员工 | 证书查看 |
| `/training/audit-package` | AuditPackage | 人事专员 | 体系审核资料 |
| `/attendance/calendar` | AttendanceCalendar | 人事专员/主管 | 考勤日历 |
| `/attendance/summary` | AttendanceSummary | 人事专员 | 考勤汇总 |
| `/attendance/anomalies` | AnomalyList | 人事专员 | 异常列表 |
| `/attendance/anomaly-report` | AnomalyReport | 人事专员 | 异常报告 |
| `/payroll/config` | PayrollConfig | 人事专员 | 薪资配置 |
| `/payroll/calculation` | PayrollCalcView | 人事专员 | 薪资核算结果 |
| `/payroll/review` | PayrollReview | 人事专员 | 薪资审核 |
| `/payroll/payslip` | PayslipView | 在职员工 | 工资条查看 |
| `/performance/self` | SelfEvaluation | 在职员工 | 绩效自评 |
| `/performance/review` | ManagerReview | 部门主管 | 上级评审 |
| `/performance/summary` | PerformanceSummary | 人事专员/主管 | 绩效汇总 |
| `/external/injury` | InjuryCase | 外务专员 | 工伤管理 |
| `/external/housing-fund` | HousingFund | 外务专员 | 公积金管理 |
| `/resignation/apply` | ResignApply | 在职员工 | 离职申请 |
| `/resignation/handover` | HandoverChecklist | 各部门 | 交接清单 |
| `/certificate/apply` | CertApply | 在职员工 | 证明申请 |
| `/certificate/history` | CertHistory | 在职员工 | 证明历史 |
| `/admin/users` | UserManage | 系统管理员 | 用户管理 |
| `/admin/roles` | RoleManage | 系统管理员 | 角色管理 |
| `/admin/agents` | AgentMonitor | 系统管理员 | Agent 监控 |
| `/admin/agents/config` | AgentParamConfig | 系统管理员 | Agent 参数配置 |
| `/admin/audit-logs` | AuditLog | 系统管理员 | 审计日志 |
| `/admin/config` | SystemConfig | 系统管理员 | 系统配置 |
| `/admin/ai-cost` | AiCostReport | 系统管理员 | AI 费用报表 |
| `/403` | Forbidden | — | 无权限 |
| `/404` | NotFound | — | 页面不存在 |

### 2.2 路由守卫

```
路由守卫流程:
1. 检查 JWT Token 是否有效
2. 检查用户角色是否有目标页面访问权限
3. 检查是否需要进行 MFA (管理员首次登录、薪资数据、公积金操作等)
4. 检查临时二维码授权是否过期 (面试官/候选人场景)
5. 通过则渲染页面，否则重定向到 /403 或 /login
```

### 2.3 扫码入口路由

扫码入口是独立于主应用的轻量级页面，通过 `/qr/:token` 路由解析：

| Token 类型 | 跳转目标 | 说明 |
|-----------|---------|------|
| `exam-{id}` | `/recruitment/exams/{id}/take` | 面试考试 |
| `training-checkin-{code}` | `/training/checkin/{code}` | 培训签到 |
| `onboarding-{token}` | `/onboarding/{token}` | 入职引导 |

---

## 3. 状态管理设计

### 3.1 Zustand Store 结构

#### 3.1.1 认证状态 (authStore)

```typescript
interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: UserInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  mfaRequired: boolean;
  mfaType: 'sms' | 'authenticator' | null;
  actions: {
    login: (credentials: LoginRequest) => Promise<void>;
    logout: () => Promise<void>;
    verifyMfa: (code: string) => Promise<void>;
    refreshToken: () => Promise<void>;
  };
}
```

#### 3.1.2 用户状态 (userStore)

```typescript
interface UserState {
  profile: UserProfile | null;
  permissions: Permission[];
  department: Department | null;
  actions: {
    fetchProfile: () => Promise<void>;
    updateProfile: (data: UpdateProfileRequest) => Promise<void>;
  };
}
```

#### 3.1.3 UI 状态 (uiStore)

```typescript
interface UiState {
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark';
  language: 'zh-CN' | 'en-US';
  notifications: NotificationItem[];
  loading: boolean;
  actions: {
    toggleSidebar: () => void;
    setTheme: (theme: 'light' | 'dark') => void;
    setLanguage: (lang: 'zh-CN' | 'en-US') => void;
    addNotification: (item: NotificationItem) => void;
    removeNotification: (id: string) => void;
  };
}
```

#### 3.1.4 Agent 运行状态 (agentStore)

```typescript
interface AgentState {
  agents: AgentStatus[];
  runningTasks: AgentTask[];
  selectedAgent: string | null;
  wsConnected: boolean;
  actions: {
    fetchAgentStatus: () => Promise<void>;
    connectWebSocket: () => void;
    disconnectWebSocket: () => void;
    triggerAgent: (agentName: string, params: any) => Promise<void>;
  };
}
```

### 3.2 React Query 服务端状态

使用 React Query 管理服务端数据缓存：

```typescript
// 示例：简历列表查询
const { data, isLoading } = useQuery({
  queryKey: ['resumes', { page, filter }],
  queryFn: () => recruitmentService.getResumes({ page, filter }),
  staleTime: 5 * 60 * 1000,  // 5 分钟缓存
  refetchOnWindowFocus: false,
});

// 示例：Agent 实时状态
const { data } = useQuery({
  queryKey: ['agent-status'],
  queryFn: () => adminService.getAgentStatus(),
  refetchInterval: 30 * 1000,  // 30 秒轮询
});
```

### 3.3 WebSocket 实时推送

Agent 运行状态通过 WebSocket 实时推送至前端：

```typescript
// Agent 状态变更推送
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  switch (msg.type) {
    case 'AGENT_STARTED':
      agentStore.addRunningTask(msg.payload);
      break;
    case 'AGENT_COMPLETED':
      agentStore.completeTask(msg.payload);
      break;
    case 'AGENT_ERROR':
      agentStore.onError(msg.payload);
      notificationStore.addAlert(msg.payload);
      break;
  }
};
```

---

## 4. 页面布局设计

### 4.1 全局布局 (PageLayout)

```
┌─────────────────────────────────────────────────────────────┐
│  AppHeader (固定顶部)                                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ [Logo]  GBM AI Agent HR          [搜索] [通知] [语言] [用户]│ │
│  └─────────────────────────────────────────────────────────┘ │
├──────────────────┬──────────────────────────────────────────┤
│                  │                                           │
│  AppSidebar      │  Page Content Area                       │
│  (可折叠)         │  ┌─────────────────────────────────────┐ │
│  ┌──────────────┐│  │ Breadcrumb Navigation               │ │
│  │ 招聘管理      ││  ├─────────────────────────────────────┤ │
│  │ ├─ 职位管理   ││  │                                     │ │
│  │ │ ├─ 发布    ││  │  Page Title                         │ │
│  │ │ └─ 简历    ││  │                                     │ │
│  │ ├─ 考试管理   ││  │  Main Content                       │ │
│  │ │ ├─ 组卷    ││  │  ┌───────────────────────────────┐  │ │
│  │ │ └─ 阅卷    ││  │  │                                │  │ │
│  │ ├─ 人才库    ││  │  │   Page-Specific Content        │  │ │
│  │ ├─ 入职管理   ││  │  │                                │  │ │
│  │ ├─ 培训管理   ││  │  └───────────────────────────────┘  │ │
│  │ ├─ 考勤管理   ││  │                                     │ │
│  │ ├─ 薪资管理   ││  │  Actions Bar                        │ │
│  │ ├─ 绩效管理   ││  │  [导出] [审核] [生成报告]            │ │
│  │ ├─ 外务管理   ││  └─────────────────────────────────────┘ │
│  │ ├─ 离职管理   ││                                           │
│  │ └─ 证明自助   ││                                           │
│  └──────────────┘│                                           │
│                  │                                           │
├──────────────────┴──────────────────────────────────────────┤
│  AppFooter                                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ © 2026 GBM AI Agent HR | v1.0.0                        │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 各角色仪表盘布局

#### 4.2.1 人事专员工作台 (HrDashboard)

```
┌─────────────────────────────────────────────────────────────┐
│  待办事项统计                                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │ 待审核: 5│ │ 待确认: 3│ │ 异常: 2 │ │ 预警: 1 │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
├─────────────────────────────────────────────────────────────┤
│  快捷入口                                                    │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │
│  │简历审核│ │薪资审核│ │入职办理│ │培训管理│ │考勤异常│ │证明签发││
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘    │
├─────────────────────────────────────────────────────────────┤
│  左侧 (60%)                    │  右侧 (40%)                  │
│  ┌─────────────────────────┐  │  ┌─────────────────────┐   │
│  │ Agent 运行状态            │  │  最近操作记录           │   │
│  │ ┌─────────────────────┐ │  │  ┌───────────────────┐ │   │
│  │ │ 招聘 Agent: 运行中    │ │  │  │ 10:30 薪资核算完成  │ │   │
│  │ │ 薪资 Agent: 待执行   │ │  │  │ 10:15 简历筛选完成  │ │   │
│  │ │ 考勤 Agent: 已完成   │ │  │  │ 09:50 考勤异常发现  │ │   │
│  │ │ 培训 Agent: 运行中   │ │  │  └───────────────────┘ │   │
│  │ └─────────────────────┘ │  │                         │   │
│  └─────────────────────────┘  │  Agent 异常事件           │   │
│                               │  ┌─────────────────────┐ │   │
│  HR KPI 趋势                  │  │ RPA 公积金: 成功 98% │ │   │
│  ┌─────────────────────────┐  │  │ 工伤申报: 待人工确认  │ │   │
│  │ [折线图: 简历筛选/薪资/  │  │  └─────────────────────┘ │   │
│  │  培训/考勤 近 30 天趋势] │  │                         │   │
│  └─────────────────────────┘  │                         │   │
└─────────────────────────────────┴─────────────────────────┘
```

#### 4.2.2 部门主管工作台 (ManagerDashboard)

```
┌─────────────────────────────────────────────────────────────┐
│  团队概况                                                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │ 团队人数  │ │ 出勤率    │ │ 待审批   │ │ 绩效分布  │          │
│  │ 25 人    │ │ 96.5%   │ │ 3 项    │ │ A:8 B:12 │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
├─────────────────────────────────────────────────────────────┤
│  左侧 (60%)                    │  右侧 (40%)                  │
│  ┌─────────────────────────┐  │  ┌─────────────────────┐   │
│  │ 待审批事项                │  │  团队考勤统计           │   │
│  │ ┌─────────────────────┐ │  │  ┌───────────────────┐ │   │
│  │ │ 张三 离职申请 [审批]  │ │  │  │ [柱状图: 部门考勤  │ │   │
│  │ │ 李四 绩效评审 [评审]  │ │  │  │  近 30 天趋势]    │ │   │
│  │ │ 王五 请假申请 [审批]  │ │  │  └───────────────────┘ │   │
│  │ └─────────────────────┘ │  │                         │   │
│  └─────────────────────────┘  │  团队绩效分布             │   │
│                               │  ┌─────────────────────┐ │   │
│  团队分析报告                  │  │  [饼图: A/B/C/D 等级  │ │   │
│  ┌─────────────────────────┐  │  │  分布比例]           │ │   │
│  │ [雷达图: 团队综合能力     │  │  └─────────────────────┘ │   │
│  │  评估维度]               │  │                         │   │
│  └─────────────────────────┘  │                         │   │
└─────────────────────────────────┴─────────────────────────┘
```

#### 4.2.3 员工自助门户 (EmployeeDashboard)

```
┌─────────────────────────────────────────────────────────────┐
│  欢迎, 张三                                                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  [头像]  张三 | 软件开发工程师 | 技术研发部              │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  快捷功能                                                    │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │
│  │工资条 │ │考勤   │ │培训   │ │证明   │ │绩效   │ │离职   │    │
│  │查看   │ │记录   │ │学习   │ │申请   │ │自评   │ │申请   │    │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘    │
├─────────────────────────────────────────────────────────────┤
│  左侧 (60%)                    │  右侧 (40%)                  │
│  ┌─────────────────────────┐  │  ┌─────────────────────┐   │
│  │ 本月考勤                  │  │  最近工资条             │   │
│  │ ┌─────────────────────┐ │  │  ┌───────────────────┐ │   │
│  │ │ 出勤: 20 天           │ │  │  │ 2026-05 实发      │ │   │
│  │ │ 迟到: 1 次           │ │  │  │ ¥15,234.56       │ │   │
│  │ │ 加班: 8 小时         │ │  │  │ [查看明细]        │ │   │
│  │ │ 请假: 0 天           │ │  │  └───────────────────┘ │   │
│  │ └─────────────────────┘ │  │                         │   │
│  └─────────────────────────┘  │  证书与上岗证             │   │
│                               │  ┌─────────────────────┐ │   │
│  培训进度                      │  │  特种作业证: 有效    │ │   │
│  ┌─────────────────────────┐  │  │  上岗证: 已颁发     │ │   │
│  │ [进度条: 安规培训 80%]   │  │  │  上岗证: 即将到期    │ │   │
│  │ [进度条: 技能提升 50%]   │  │  │  (30 天后)         │ │   │
│  └─────────────────────────┘  │  └─────────────────────┘ │   │
└─────────────────────────────────┴─────────────────────────┘
```

### 4.3 移动端布局

移动端采用底部 Tab 导航 + 抽屉式侧栏：

```
┌─────────────────────┐
│ [状态栏]             │
├─────────────────────┤
│ [顶部栏] 标题         │
├─────────────────────┤
│                     │
│  页面内容区域         │
│  (滚动区域)          │
│                     │
│                     │
├─────────────────────┤
│ [Tab 1] [Tab 2] [Tab 3] [Tab 4] │
│ 首页    考勤   培训   我的   │
└─────────────────────┘
```

---

## 5. 组件设计

### 5.1 通用组件规范

#### 5.1.1 数据表格 (DataTable)

```typescript
interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  pagination: {
    currentPage: number;
    pageSize: number;
    total: number;
  };
  sorting: {
    field: string;
    order: 'asc' | 'desc';
  };
  filtering: Record<string, any>;
  actions: {
    onRowClick?: (record: T) => void;
    onSort?: (field: string, order: 'asc' | 'desc') => void;
    onFilter?: (filters: Record<string, any>) => void;
    onPageChange?: (page: number) => void;
  };
  exportable?: boolean;
  selectable?: boolean;
}
```

#### 5.1.2 表单组件 (FormInput)

```typescript
interface FormInputProps {
  label: string;
  name: string;
  type?: 'text' | 'number' | 'email' | 'tel' | 'password' | 'date';
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  validate?: (value: any) => string | undefined;
  errorMessage?: string;
  helpText?: string;
  // 无障碍属性
  'aria-describedby'?: string;
  'aria-required'?: boolean;
}
```

#### 5.1.3 手写签名组件 (FormSignature)

```typescript
interface FormSignatureProps {
  label: string;
  width?: number;      // 默认 400px
  height?: number;     // 默认 150px
  penColor?: string;   // 默认 '#000'
  penWidth?: number;   // 默认 2px
  onSign?: (dataUrl: string) => void;
  onClear?: () => void;
  required?: boolean;
}
```

#### 5.1.4 摄像头采集组件 (FormCamera)

```typescript
interface FormCameraProps {
  label: string;
  mode: 'face' | 'document' | 'general';
  onCapture?: (dataUrl: string) => void;
  qualityCheck?: boolean;    // 启用质量检查 (亮度/清晰度)
  maxRetakes?: number;       // 最大重拍次数
  required?: boolean;
}
```

### 5.2 页面级组件

#### 5.2.1 简历列表页面 (ResumeList)

```
┌─────────────────────────────────────────────────────────────┐
│  简历筛选                      [导入] [导出] [自然语言搜索框]  │
├─────────────────────────────────────────────────────────────┤
│  筛选条件栏                                                    │
│  [岗位▼] [学历▼] [经验▼] [分类▼] [得分区间] [日期范围] [搜索] │
├─────────────────────────────────────────────────────────────┤
│  统计面板: 高潜 (25) | 候审 (15) | 淘汰 (8)                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ [复选] 姓名 | 岗位 | 学历 | 经验 | 综合得分 | 分类 | 时间  │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │ [  ] 张三 | 前端开发 | 本科 | 5年 | 85.5 | [高潜] | 06/10│ │
│  │ [  ] 李四 | 前端开发 | 硕士 | 3年 | 72.3 | [候审] | 06/11│ │
│  │ [  ] 王五 | 前端开发 | 大专 | 2年 | 45.1 | [淘汰] | 06/12│ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  [分页: < 1 2 3 ... 10 >]  共 2,345 条                     │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2.2 薪资审核页面 (PayrollReview)

```
┌─────────────────────────────────────────────────────────────┐
│  2026 年 06 月 薪资核算审核                                    │
│  Agent 完成时间: 2026-06-30 22:15:32                         │
├─────────────────────────────────────────────────────────────┤
│  核算概况: 应发总额 ¥2,345,678.90 | 实发总额 ¥1,876,543.21   │
│  异常数据: 3 条 (点击查看)                                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 工号 | 姓名 | 部门 | 应发 | 社保 | 公积金 | 个税 | 实发   │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │ E001 | 张三 | 研发 | 18000| 1800 | 1800  | 800  | 13600│ │
│  │ E002 | 李四 | 产品 | 15000| 1500 | 1500  | 500  | 11500│ │
│  │ E003 | 王五 | 测试 | 12000| 1200 | 1200  | 300  |  9300│ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  [导出 Excel] [查看计算底稿] [确认审核] [驳回重算]             │
│                                                              │
│  审核意见: [文本域]                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. 无障碍访问设计 (WCAG 2.1 AA)

### 6.1 无障碍要求

| 要求 | 实现方式 |
|------|---------|
| 屏幕阅读器支持 | 所有交互元素添加 aria-label、aria-describedby |
| 键盘操作 | Tab 键遍历所有交互元素，Enter/Space 触发动作 |
| 色彩对比度 | 正文 ≥ 4.5:1，大字体 ≥ 3:1 |
| 放大至 200% | 响应式布局，不使用固定像素宽度 |
| 焦点管理 | 模态框弹出时焦点锁定，关闭后恢复 |
| 表单标签 | 所有输入框关联 label，错误信息关联 aria-describedby |
| 图像替代 | 所有装饰性图像使用 aria-hidden，信息性图像使用 alt |

### 6.2 关键用户路径无障碍覆盖

| 路径 | 无障碍要求 |
|------|-----------|
| 登录与身份认证 | 表单标签完整、错误提示可读、MFA 输入框键盘可用 |
| 人事专员审核待办 | 表格键盘导航、筛选条件键盘可用、审核按钮焦点可见 |
| 工资条查看与导出 | 工资条数据可读、导出按钮键盘可用、金额格式无障碍 |
| 员工自助证明申请 | 表单标签完整、文件上传键盘可用、提交确认无障碍 |
| 扫码签到 | 二维码识别失败时有替代输入方式、倒计时可读 |

### 6.3 无障碍测试

```typescript
// 使用 axe-core 进行自动化无障碍检测
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom/extend-expect';

expect.extend(toHaveNoViolations);

test('登录页面应无 A 级和 AA 级无障碍缺陷', async () => {
  const { container } = render(<LoginPage />);
  const results = await axe(container);
  expect(results).toHaveNoViolations({
    impact: ['critical', 'serious'],  // A 级 = 0 缺陷
  });
});
```

---

## 7. 国际化 (i18n) 设计

### 7.1 语言支持

| 语言 | 代码 | 说明 |
|------|------|------|
| 简体中文 | zh-CN | 默认语言 |
| 英语 | en-US | 双语切换 |

### 7.2 翻译文件结构

```
src/i18n/
├── index.ts          # i18n 初始化配置
├── zh-CN.json        # 简体中文翻译
└── en-US.json        # 英语翻译
```

### 7.3 翻译覆盖率要求

- 所有用户界面文本翻译覆盖率 ≥ 95%
- 同一术语翻译一致率 100%
- 每版本上线前执行双语全覆盖测试

### 7.4 格式适配

| 数据类型 | 简体中文格式 | 英文格式 |
|---------|------------|---------|
| 日期 | 2026 年 6 月 12 日 | June 12, 2026 |
| 日期 (紧凑) | 2026-06-12 | 06/12/2026 |
| 金额 | ¥12,345.67 | $12,345.67 |
| 大数 | 1,234,567.89 | 1,234,567.89 |
| 百分比 | 12.5% | 12.5% |

### 7.5 语言切换实现

```typescript
// 语言切换按钮
function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const currentLang = uiStore.state.language;

  return (
    <Select
      value={currentLang}
      onChange={(lang) => {
        i18n.changeLanguage(lang);
        uiStore.actions.setLanguage(lang);
      }}
      options={[
        { label: '简体中文', value: 'zh-CN' },
        { label: 'English', value: 'en-US' },
      ]}
      aria-label="切换语言"
    />
  );
}
```

---

## 8. 降级模式前端适配

### 8.1 降级状态展示

当系统进入降级模式时，前端需要展示降级状态并适配相应功能：

| 降级场景 | 前端适配 |
|---------|---------|
| LLM 不可用 | 简历筛选页面显示"关键词匹配模式"标识；文书生成改用预置模板 |
| OCR 不可用 | 证件上传页面转为人工录入表单；显示降级提示 |
| 人脸不可用 | 人脸采集页面替换为"身份证+手机验证码"验证流程 |
| RPA 被拦截 | 外务页面显示"需人工操作"提示；提供预填数据下载 |
| 编排层异常 | 显示"手动调度模式"；开放 Agent 手动触发按钮 |

### 8.2 降级提示组件

```typescript
interface DegradedBannerProps {
  service: string;        // 受影响的服务名称
  mode: string;           // 降级模式描述
  estimatedRecovery?: string;  // 预计恢复时间
  actionRequired?: boolean;    // 是否需要人工介入
}

// 页面顶部显示降级横幅
function DegradedBanner({ service, mode, estimatedRecovery, actionRequired }) {
  return (
    <Alert
      type="warning"
      showIcon
      closable
      aria-live="polite"
      message={`服务降级: ${service}`}
      description={
        <span>
          当前运行模式: {mode}
          {estimatedRecovery && ` | 预计恢复: ${estimatedRecovery}`}
          {actionRequired && ' | 需要人工介入'}
        </span>
      }
    />
  );
}
```

---

## 9. 性能优化策略

### 9.1 代码分割

| 分割策略 | 实现 |
|---------|------|
| 路由级懒加载 | React.lazy() + Suspense |
| 组件级按需加载 | 大型组件 (图表、编辑器) 动态 import |
| Vendor 打包分离 | Vite 配置 manualChunks |

### 9.2 渲染优化

| 优化手段 | 实现 |
|---------|------|
| React.memo | 纯组件避免重复渲染 |
| useMemo/useCallback | 缓存计算结果和回调函数 |
| 虚拟列表 | 大数据量表格使用 react-window |
| 图片懒加载 | IntersectionObserver 实现 |

### 9.3 网络优化

| 优化手段 | 实现 |
|---------|------|
| 请求缓存 | React Query staleTime 配置 |
| 请求合并 | 批量请求合并 (如多简历评分) |
| 请求取消 | Axios CancelToken |
| CDN 静态资源 | 前端构建产物部署至 CDN |

---

## 10. 安全前端策略

### 10.1 XSS 防护

| 措施 | 实现 |
|------|------|
| React 自动转义 | JSX 默认转义用户输入 |
| 富文本过滤 | DOMPurify 清理 HTML 内容 |
| CSP 头 | Content-Security-Policy 配置 |
| 避免 dangerouslySetInnerHTML | 仅在必要时使用，配合 DOMPurify |

### 10.2 CSRF 防护

| 措施 | 实现 |
|------|------|
| SameSite Cookie | Cookie 设置 SameSite=Strict |
| CSRF Token | 请求头携带 CSRF Token |
| 自定义请求头 | X-Requested-With 头验证 |

### 10.3 敏感数据保护

| 措施 | 实现 |
|------|------|
| 前端不存储敏感数据 | 身份证号、薪资等不缓存到 localStorage |
| Token 安全存储 | HTTPOnly Cookie 存储 JWT |
| 脱敏展示 | 身份证号显示为 123****8901 |
| 剪贴板限制 | 敏感字段禁用复制 (contextmenu 拦截) |

---

## 11. 测试策略

### 11.1 测试金字塔

```
         ┌─────────┐
         │  E2E     │  Playwright (关键用户路径)
         │  Tests   │
      ┌──┴─────────┴──┐
      │  Integration   │  React Testing Library (组件交互)
      │  Tests         │
   ┌──┴────────────────┴──┐
   │    Unit Tests        │  Vitest (工具函数、Hooks、Store)
   │                      │
   └──────────────────────┘
```

### 11.2 测试覆盖率目标

| 层级 | 目标覆盖率 |
|------|-----------|
| 工具函数 | ≥ 95% |
| Store/Hooks | ≥ 90% |
| 通用组件 | ≥ 85% |
| 页面组件 | ≥ 70% |
| E2E 关键路径 | 100% (5 个关键用户路径) |
| 无障碍测试 | 100% (5 个关键用户路径) |

### 11.3 E2E 测试关键路径

1. 用户登录与身份认证流程
2. 人事专员审核待办事项流程
3. 工资条查看与导出流程
4. 员工自助证明申请流程
5. 扫码签到流程

---

*文档结束*
