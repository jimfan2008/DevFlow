# GBM AI Agent HR 智能人力管理系统 — 前端设计文档 (V25)

## 版本信息

| 字段 | 值 |
|------|-----|
| 文档名称 | GBM AI Agent HR 前端设计文档 |
| 版本号 | V25.0 |
| 基于 SRS | V15.0 |
| 日期 | 2026-06-15 |
| 作者 | 后旺 (HouWang) |
| 角色 | 前端架构师 |

## 修订说明

V24→V25：根据跨文档一致性检验意见进行最终修正：

1. 【React 语法残留修复】第 4.6 节 Vue Query DevTools 集成方式中 `initialIsOpen={false}` 为 React JSX 语法，修正为 Vue 属性语法 `:initial-is-open="false"`。

2. 【章节编号一致性修复】V24 中目录编号为 13 章，但正文实际为 14 章（第 8 章"关键用户路径交互流程图"未列入目录），修正目录和章节编号使其一一映射。

3. 【跨文档一致性声明强化】新增与架构设计文档、后端设计文档、数据库设计文档的交叉引用声明。

V23→V24：根据后荣跨文档一致性检验意见进行技术栈全面修正：

**严重缺陷修复：**
1. 【严重缺陷】技术栈与架构文档不一致：架构文档强制规定前端采用 Vue 3.4.x + Element Plus、状态管理 Pinia 2.1.x、移动端 UniApp 3.0.x；而 V23 采用 React 18.x + Ant Design 5.x、状态管理 Zustand 4.x + @tanstack/react-query 5.x、移动端 PWA + workbox 7.x。本次进行全面技术栈替换：
   - React 18.x → Vue 3.4.x（Composition API + `<script setup>`）
   - Ant Design 5.x → Element Plus 2.x
   - Zustand 4.x → Pinia 2.1.x
   - @tanstack/react-query 5.x → @tanstack/vue-query 5.x
   - React Router 6.x → Vue Router 4.x
   - react-hook-form → VueUse Form + zod
   - react-i18next → vue-i18n 9.x
   - framer-motion → @vueuse/motion
   - @dnd-kit/core + @dnd-kit/sortable → vue-draggable-plus
   - react-pdf → pdfjs-dist (Vue 封装)
   - react-signature-canvas → vue-signature-pad
   - @axe-core/react → axe-core (Vue 集成)
   - workbox 7.x (PWA) → UniApp 3.0.x (移动端) + Vite PWA (PC 端)
   - @sentry/react → @sentry/vue

2. 【依赖一致性】所有技术栈相关描述、代码示例、项目结构、组件定义、Props 接口等全部更新为 Vue 生态对应方案。

3. 【移动端方案】原 PWA + workbox 方案改为 UniApp 3.0.x 跨平台方案，与架构文档保持一致。

---

## 目录

1. 前端技术栈
2. 项目结构
3. 路由设计
4. 状态管理
5. 组件体系
6. 页面布局设计
7. 关键页面设计
8. 关键用户路径交互流程图
9. 无障碍访问设计
10. UniApp 与移动端设计
11. 安全与性能
12. 深色模式设计
13. 业务状态与交互设计
14. 跨文档一致性声明

---

## 1. 前端技术栈

### 1.1 核心技术

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| 语言 | TypeScript | 5.x | 类型安全 |
| 框架 | Vue | 3.4.x | 响应式 UI 框架（Composition API + `<script setup>`） |
| UI 组件库 | Element Plus | 2.x | 企业级组件库 |
| CSS 方案 | Element Plus 内置变量 + Scoped CSS | - | CSS 变量管理全局 Design Token |
| 路由 | Vue Router | 4.x | 声明式路由 |
| 状态管理 | Pinia | 2.1.x | 轻量级状态管理（UI 状态 + 全局状态） |
| 服务端状态 | @tanstack/vue-query | 5.x | 所有业务数据管理 |
| HTTP 客户端 | Axios | 1.x | 请求封装与拦截 |
| 国际化 | vue-i18n | 9.x | 中/英双语 |
| 构建工具 | Vite | 5.x | 快速构建 |
| 测试 | Vitest + Testing Library | - | 单元测试 |
| 表单 | VueUse Form + zod | ≥3.23 | 表单验证（V22：明确最低版本以支持 `base64url()` 校验器） |
| 数据表格 | Element Plus Table | 2.x | 内置高级表格 |
| 图表 | ECharts | 5.x | 数据可视化（按需引入） |
| 文件上传 | Element Plus Upload + 自定义分片 | 2.x | Upload 提供 UI，分片逻辑由自定义 Composable 实现 |
| 文件哈希 | js-sha256 | 3.x | 支持增量 SHA-256 计算（V21 新增，替代 crypto-js 错误方案） |
| PDF 预览 | pdfjs-dist + vue-pdf-embed | - | 在线预览 PDF |
| 电子签名 | vue-signature-pad | - | 手写签名（触摸事件需显式 preventDefault） |
| 无障碍 | axe-core | - | 无障碍检测（仅开发环境） |
| PC 端 PWA | vite-plugin-pwa | 0.x | Service Worker（PC 端渐进式增强） |
| 移动端 | UniApp | 3.0.x | 跨平台移动端（H5/小程序/App） |
| 日期选择 | dayjs | 2.x | 轻量日期库 |
| 拖拽 | vue-draggable-plus | 2.x | 拖拽排序（基于 Sortable.js） |
| 通知 | Element Plus Notification | 2.x | 消息通知 |
| 错误监控 | Sentry | 8.x | 前端错误监控（V21 新增，@sentry/vue 8.x） |
| 页面动画 | @vueuse/motion | - | 路由过渡动画（Vue 版动画方案） |
| 工具库 | VueUse | 10.x | Vue 组合式 API 工具库 |

### 1.1.1 依赖加载策略

| 类别 | 加载方式 | 包含包 |
|------|---------|--------|
| 核心依赖 | 首屏加载 | Vue, Element Plus, Vue Router, Pinia, Axios, @tanstack/vue-query, dayjs, js-sha256, VueUse Form, zod, @vueuse/motion |
| 按需加载 | defineAsyncComponent 动态导入 | pdfjs-dist/vue-pdf-embed, vue-signature-pad, ECharts |
| 环境依赖 | 仅开发环境 | axe-core, Pinia DevTools, Vue Query DevTools |
| 环境依赖 | 仅生产环境 | Sentry SDK（条件导入） |

**ECharts 按需引入方案（V18 新增，V21 统一描述）：**
- ECharts 完整构建约 900KB gzip，按需引入后压缩至 300-400KB gzip
- Vite 配置中设置 `echarts` 插件，仅打包使用的图表模块
- 代码层面使用 `import { init } from 'echarts/core'` + `import { BarChart, LineChart, PieChart, HeatmapChart } from 'echarts/charts'` + `import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'`
- 完整构建仅用于开发环境快速调试

**js-sha256 引入方案（V21 新增）：**
- 仅引入 `sha256` 模块，gzip 后约 8KB
- 使用方式：`import { sha256 } from 'js-sha256'`，`const hasher = new sha256()` 返回 Hasher 实例
- 支持 `hasher.update(chunk)` 增量喂入 + `hasher.hex()` 输出十六进制哈希字符串
- 替代 V20 中错误的 crypto-js 方案

**构建期配置说明：**
- **vite-plugin-pwa (PC 端 PWA)**：Service Worker 为构建时注册的独立脚本，由 Vite 插件在构建阶段生成
- **UniApp (移动端)**：独立构建目标，使用 UniApp CLI 编译为 H5/小程序/App
- **axe-core (无障碍)**：开发期工具，仅开发环境生效，不包含在生产构建中
- **Sentry SDK**：生产环境通过 Vite 环境变量 `import.meta.env.VITE_SENTRY_DSN` 条件导入

### 1.2 设计规范

- **设计系统**：Element Plus 内置 CSS 变量系统，通过覆盖 CSS 变量管理全局 Design Token
- **色彩规范**：主色 #409EFF（Element Plus 默认），辅助色 #67C23A（成功）、#E6A23C（警告）、#F56C6C（错误）
- **字体**：Inter (英文) + PingFang SC / Microsoft YaHei (中文)
- **间距**：8px 基准网格系统
- **圆角**：4px (小)、8px (中)、12px (大)

---

## 2. 项目结构

```
src/
├── assets/         # 图片、图标、全局样式
├── components/     # 组件库
│   ├── common/     # AppHeader, AppSider, UserAvatar, NotificationBell, LanguageSwitcher, ThemeToggle, LoadingSpinner
│   ├── data/       # DataTable, SearchFilter, PaginationBar, ExportButton, ImportDialog
│   ├── form/       # FormCard, StepForm, FileUpload, ImageCropper, SignaturePad, DatePickerRange
│   ├── feedback/   # ConfirmDialog, Toast, EmptyState, ErrorBoundary, UndoBanner
│   └── layout/     # MainLayout, PageHeader, CardContainer, TabContainer, BottomTabBar, MobileLayout
├── composables/    # useAuth, usePermission, usePagination, useDebounce, useFileUpload(分片上传), useChartPreload, useUndo
├── stores/         # Pinia 状态（UI 交互状态 + 全局状态）
│   ├── auth.ts     # 认证状态
│   └── ui.ts       # 全局 UI 状态（侧栏、主题、语言、通知、面包屑）
├── services/       # API 服务层（auth, recruitment, onboarding, training, attendance, payroll, performance, external, employee, agent, file）
├── views/          # 页面组件（按功能模块：auth, dashboard, recruitment, onboarding, training, attendance, payroll, performance, external, employee, agent, system, error）
├── router/         # 路由配置（index.ts, guards.ts, roleGuard.ts, routeConfig.ts）
├── types/          # TypeScript 类型定义
├── utils/          # 工具函数
├── i18n/           # 国际化（zh-CN/, en/ 各 11 个模块翻译文件）
├── App.vue
└── main.ts
uniapp/             # UniApp 移动端项目（独立目录）
├── pages/          # 移动端页面
├── components/     # 移动端组件
├── stores/         # 移动端状态（Pinia 共享）
├── services/       # API 服务层（与 Web 端共享）
├── static/         # 静态资源
├── App.vue
├── main.ts
├── pages.json
└── manifest.json
tests/              # unit/, integration/, accessibility/
```

**项目结构说明（V24 新增）：**
- Web 端（PC）：`src/` 目录，Vue 3.4.x + Element Plus
- 移动端：`uniapp/` 目录，UniApp 3.0.x，支持编译为 H5/微信小程序/App
- 共享层：`services/` API 服务层在两端共享，`types/` 类型定义在两端共享
- 状态管理：Pinia store 在 Web 端和 UniApp 端均可使用

---

## 3. 路由设计

### 3.1 路由结构

| 路径前缀 | 模块 | 公开/需认证 | 角色要求 |
|---------|------|-----------|---------|
| /login, /mfa-verify, /forgot-password | 认证 | 公开（已登录重定向） | 未认证用户 |
| / → /dashboard/* | 工作台 | 需认证 | 按角色重定向（admin/hr/manager/employee） |
| /recruitment/* | 招聘管理 | 需认证 | HR、管理员 |
| /onboarding/portal | 新员工门户 | Token 验证 | 新员工（临时令牌） |
| /onboarding/list, /onboarding/progress | 入职管理 | 需认证 | HR、管理员 |
| /training/* | 培训管理 | 需认证 | 按子路由差异化 |
| /training/check-in | 扫码签到 | 二维码 Token | 受训员工 |
| /exam/:token | 在线考试 | Token 一次性验证 | 考生 |
| /attendance/* | 考勤管理 | 需认证 | 按角色差异化 |
| /payroll/review | 薪资审核 | 需认证+MFA | HR、管理员 |
| /payroll/payslip | 工资条 | 行级权限 | 本人 |
| /performance/* | 绩效管理 | 需认证 | 按角色差异化 |
| /external/* | 外务管理 | 需认证 | HR、管理员 |
| /employee/* | 员工服务 | 需认证 | 按子路由差异化 |
| /agent/* | Agent 管理 | 需认证+MFA | 管理员 |
| /system/* | 系统管理 | 需认证+MFA | 管理员 |
| /404, /403, /500 | 错误页 | 公开 | 无 |

### 3.2 路由保护

- **认证守卫**：通过 Vue Router `beforeEach` 全局前置守卫检查 `authStore.isAuthenticated`，未认证重定向到 /login
- **MFA 守卫**：标记 `meta: { mfa: true }` 的路由需二次验证，未验证跳转 /mfa-verify
- **角色守卫**：通过 `beforeEach` 守卫对比 `authStore.roles` 与路由 `meta.roles` 数组
- **行级权限**：工资条等页面由后端 API 返回用户有权查看的数据，前端不自行过滤
- **临时令牌**：入职门户使用一次性 Token，考试页使用一次性 Token，验证后失效

### 3.3 路由配置

路由配置采用 `RouteConfig` 数组定义，每条目含 path、component、meta（含 roles、title(i18n key)、icon、hidden(是否侧栏隐藏)、mfa）字段。运行时由 `routeConfig.ts` 导出，`index.ts` 将其传入 Vue Router 的 `createRouter` 创建路由实例。

### 3.4 路由参数定义（V21 新增）

| 参数 | 路由 | 格式 | 长度 | 校验规则 | 生成方 |
|------|------|------|------|---------|--------|
| :token | /exam/:token | Base64URL 编码 UUID | 22 字符 | 仅含 A-Z/a-z/0-9/-/_，无填充符 | 后端生成 |
| :token | /onboarding/portal?token= | Base64URL 编码 UUID | 22 字符 | 同上，查询参数形式 | 后端生成 |
| :id | 各模块详情页（如 /recruitment/resume/:id） | UUID v4 | 36 字符 | 标准 UUID 格式 xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx | 后端生成 |
| :date | /payroll/review?month= | YYYY-MM | 7 字符 | 合法年月格式 | 前端选择器 |

**参数校验实现：**
- 路由层面使用 Vue Router `route.query` / `route.params` 获取参数
- Token 参数使用 zod schema 校验：`z.string().base64url().length(22)`
- ID 参数使用 zod schema 校验：`z.string().uuid()`
- 校验失败时跳转 /404 并记录错误日志
- **zod 版本要求（V22 新增）**：`z.string().base64url()` 需要 zod ≥3.23。项目已锁定 zod ≥3.23。若因依赖降级无法使用，fallback 方案为正则校验：`z.string().regex(/^[A-Za-z0-9_-]{22}$/)` 等效验证 Base64URL 编码的 UUID（22 字符，无填充符）

### 3.5 面包屑与路由层级对应关系（V21 新增）

面包屑层级与路由层级一一映射，由 `routeConfig.ts` 中的 `meta.title` 字段生成：

| 路由路径 | 面包屑 |
|---------|--------|
| /dashboard | 工作台 |
| /recruitment/resume | 招聘管理 / 简历管理 |
| /recruitment/resume/:id | 招聘管理 / 简历管理 / 简历详情 |
| /onboarding/list | 入职管理 / 入职列表 |
| /onboarding/portal | 新员工门户（无面包屑，独立门户） |
| /training/courses | 培训管理 / 课程管理 |
| /performance/review | 绩效管理 / 绩效考核 |
| /external/work-injury | 外务管理 / 工伤处理 |
| /employee/certificate | 员工服务 / 证明申请 |
| /agent/list | Agent 管理 / Agent 列表 |
| /system/settings | 系统管理 / 系统设置 |

**实现方式：**
- `uiStore.breadcrumb` 数组存储当前面包屑项：`[{title: string, path: string?}][]`
- 导航时根据路由匹配自动填充，有 path 的项可点击跳转
- 最后一项（当前页）不可点击

### 3.6 站点导航关系图（V21 新增）

```
登录页 /login
  └── 认证通过
       └── /dashboard（按角色重定向）
            ├── 系统管理员视角
            │    ├── 工作台 /dashboard
            │    ├── 招聘管理 /recruitment/*
            │    ├── 入职管理 /onboarding/list, /onboarding/progress
            │    ├── 培训管理 /training/*
            │    ├── 考勤管理 /attendance/*
            │    ├── 薪资管理 /payroll/*
            │    ├── 绩效管理 /performance/*
            │    ├── 外务管理 /external/*
            │    ├── 员工服务 /employee/*
            │    ├── Agent 管理 /agent/*
            │    └── 系统管理 /system/*
            ├── 人事专员视角
            │    ├── 待办审核（聚合视图）
            │    ├── 招聘管理 /recruitment/*
            │    ├── 入职管理 /onboarding/*
            │    ├── 培训管理 /training/*
            │    ├── 考勤管理 /attendance/*
            │    ├── 薪资审核 /payroll/review
            │    ├── 绩效管理 /performance/*
            │    ├── 外务管理 /external/*
            │    └── 员工服务 /employee/*
            ├── 部门主管视角
            │    ├── 待办审批
            │    ├── 团队分析
            │    ├── 绩效考核（下属）/performance/*
            │    └── 培训管理（部门）/training/*
            └── 普通员工视角
                 ├── 我的信息 /employee/profile
                 ├── 工资条 /payroll/payslip
                 ├── 考勤记录 /attendance/my
                 ├── 培训记录 /training/my
                 ├── 证明申请 /employee/certificate
                 ├── 费用报销 /employee/reimbursement
                 └── 离职申请 /employee/resignation

独立入口（不经过侧栏导航）
  ├── /onboarding/portal（新员工临时令牌）
  ├── /training/check-in（扫码签到 Token）
  └── /exam/:token（在线考试 Token）
```

### 3.7 路由动画/过渡效果（V21 新增，V23 真正落实，V24 技术栈替换）

- **路由切换**：使用 `@vueuse/motion` 配合 Vue Router 的 `<router-view>` 的 `<Transition>` 组件实现页面过渡效果。具体实现：在 `<router-view>` 外层包裹 `<Transition name="fade">`，CSS 定义 `.fade-enter-active` / `.fade-leave-active`（opacity 0→1，200ms；opacity 1→0，150ms）。
- **页面内切换**：Tab 切换使用 Element Plus Tab 内置动画（fade 200ms）
- **模态框**：Element Plus Dialog 默认 fade 动画
- **移动端返回**：手势左滑返回时，页面从左向右滑出（300ms ease-out），由 @vueuse/motion 的 `useDraggable` 和 `useTransition` 实现
- **降级方案**：若浏览器不支持 CSS 过渡，页面直接切换无动画

---

## 4. 状态管理

### 4.1 状态分层

三层架构：(a) Pinia 管理全局状态（UI 交互状态 + 认证状态） (b) Vue Query 管理所有业务数据（服务端状态） (c) `ref()`/`reactive()` 管理页面级本地状态

### 4.2 authStore（认证状态）

存储 isAuthenticated、isLoading、mfaRequired、mfaMethod、user(仅 UI 展示字段)、roles、permissions。

**边界说明：** authStore 存储的是 UI 展示状态，用于控制界面渲染（侧栏菜单、头像等）。认证 Token 由 HTTP-Only Cookie 管理，前端 JS 不可访问。真正认证验证由后端中间件完成。用户信息刷新通过 Vue Query `useQuery(['auth','me'])` 调用后同步更新 authStore。

**Pinia Store 定义（伪代码）：**
```
export const useAuthStore = defineStore('auth', {
  state: () => ({
    isAuthenticated: false,
    isLoading: false,
    mfaRequired: false,
    mfaMethod: null as string | null,
    user: null as UserInfo | null,
    roles: [] as string[],
    permissions: [] as string[]
  }),
  actions: {
    async login(credentials: LoginCredentials) { /* ... */ },
    async verifyMfa(code: string) { /* ... */ },
    logout() { /* ... */ }
  }
})
```

### 4.3 uiStore（全局 UI 状态）

存储 siderCollapsed、theme、language、notifications、unreadCount、breadcrumb。通过 CSS 变量联动 Element Plus 全局样式。

**Pinia Store 定义（伪代码）：**
```
export const useUiStore = defineStore('ui', {
  state: () => ({
    siderCollapsed: false,
    theme: 'light' as 'light' | 'dark',
    language: 'zh-CN' as 'zh-CN' | 'en',
    notifications: [] as NotificationItem[],
    unreadCount: 0,
    breadcrumb: [] as BreadcrumbItem[]
  }),
  actions: {
    toggleSider() { /* ... */ },
    setTheme(theme: 'light' | 'dark') { /* ... */ },
    setLanguage(lang: 'zh-CN' | 'en') { /* ... */ }
  },
  persist: { key: 'gbm-hr-ui', storage: localStorage }
})
```

### 4.4 Vue Query 数据获取

- **缓存**：列表 5 分钟、详情 1 分钟 staleTime
- **乐观更新**：表单提交先更新 UI，失败回滚
- **自动重试**：网络错误重试 2 次，指数退避
- **请求取消**：组件卸载自动取消
- **依赖查询**：mutation 后 invalidate 相关查询
- **Agent 轮询**：Agent 状态使用 `refetchInterval: 30s` 轮询

### 4.5 Pinia 持久化

authStore 不使用 persist（Token 在 HTTP-Only Cookie）。非敏感表单草稿（如入职模块）使用 Pinia persist 插件（`pinia-plugin-persistedstate`），key 为 `gbm-hr-onboarding-form`。

### 4.6 状态调试方案（V21 新增）

| 调试工具 | 集成方式 | 环境 |
|---------|---------|------|
| Pinia DevTools | `createPinia()` + `pinia-plugin-persistedstate`，连接 Vue DevTools 浏览器扩展的 Pinia 面板 | 开发环境 |
| Vue Query DevTools | `<VueQueryDevtools :initial-is-open="false" />` 组件挂载，右下角浮动按钮 | 开发环境 |
| Vue DevTools | 浏览器扩展，Time Travel 和 Component 面板 | 开发环境 |

**条件导入实现：**
```
const pinia = createPinia()
if (import.meta.env.DEV) {
  pinia.use(createDevtools())
}
```

---

## 5. 组件体系

### 5.1 组件分类

| 分类 | 说明 | 代表组件 |
|------|------|---------|
| 布局组件 | 页面骨架 | MainLayout, PageHeader, CardContainer, MobileLayout, BottomTabBar |
| 导航组件 | 页面导航 | AppSider, BreadcrumbNav, TabContainer |
| 数据展示 | 表格/列表/详情 | DataTable (含分页/排序/筛选/虚拟滚动/导出), ResumeCard, EmployeeProfileCard |
| 表单组件 | 输入/选择/上传 | StepForm(入职/工伤/离职分步表单), FileUpload, ImageCropper, SignaturePad, DatePickerRange |
| 反馈组件 | 提示/确认/加载 | ConfirmDialog, Toast, EmptyState, ErrorBoundary, UndoBanner |
| 业务组件 | 特定业务逻辑 | QRCheckIn(摄像头扫码签到), ExamPaper(在线考试), PayrollTable(薪资审核表格) |

### 5.2 核心组件 Props 接口定义（V21 新增，V24 转换为 Vue 风格）

#### 5.2.1 DataTable Props

```typescript
interface DataTableProps<T = any> {
  // 数据源
  columns: TableColumn<T>[]         // Element Plus Table Column 定义
  dataSource: T[]                    // 表格数据 (v-model:data)
  loading?: boolean                  // 加载中状态
  // 分页
  pagination?: PaginationConfig | false  // 分页配置，false 禁用
  defaultPageSize?: number           // 默认每页条数，默认 20
  // 排序
  sortOrder?: SortOrder              // 当前排序状态
  onSortChange?: (field: string, order: SortOrder) => void  // 排序回调
  // 筛选
  filters?: Record<string, any>     // 筛选条件
  onFilterChange?: (filters: Record<string, any>) => void   // 筛选回调
  // 选择
  rowKey?: string                   // 行唯一键字段名，默认 'id'
  rowSelection?: RowSelection       // 行选择配置
  // 展开
  expandable?: boolean              // 启用展开行
  // 导出
  enableExport?: boolean            // 是否显示导出按钮，默认 false
  onExport?: (data: T[]) => void    // 导出回调 (emit)
  // 虚拟滚动
  virtual?: boolean                 // 启用虚拟滚动（数据量 >1000 时建议开启）
  rowHeight?: number                // 固定行高（虚拟滚动时必须设置），默认 54
  // 空状态
  emptyText?: string                // 空状态文案
  // 其他
  scroll?: ScrollConfig             // 滚动配置 {x: number, y: number}
  onRowClick?: (record: T) => void  // 行点击回调 (emit)
}
```

#### 5.2.2 SignaturePad Props

```typescript
interface SignaturePadProps {
  // 尺寸
  width?: number | string           // 画布宽度，默认 '100%'
  height?: number                   // 画布高度，默认 200
  // 笔触
  penColor?: string                 // 笔触颜色，默认 '#000'
  lineWidth?: number                // 笔触宽度，默认 2
  // 值绑定
  modelValue?: string               // 签名 base64 值 (v-model)
  // 验证
  required?: boolean                // 是否必填，默认 false
  errorMessage?: string             // 必填未满足时的错误文案
  // 操作
  disabled?: boolean                // 是否禁用
  // 无障碍
  ariaLabel?: string                // aria-label 值，默认 '电子签名区域'
}
// Emit: 'update:modelValue'(base64: string | null), 'clear'
```

#### 5.2.3 FileUpload Props

```typescript
interface FileUploadProps {
  // 上传配置
  action?: string                   // 上传地址（不使用分片时）
  maxCount?: number                 // 最大文件数，默认 1
  accept?: string                   // 接受的文件类型，如 '.pdf,.jpg,.png'
  maxSize?: number                  // 最大文件大小（MB），默认 100
  // 分片上传
  chunkSize?: number                // 分片大小（MB），默认 1
  concurrency?: number              // 并发分片数，默认 3
  enableHashCheck?: boolean         // 启用 SHA-256 哈希检查（断点续传），默认 true
  // 进度
  // 结果
  modelValue?: FileInfo[]           // 已上传文件列表 (v-model)
  // UI
  showButton?: boolean              // 显示选择按钮，默认 true
  showList?: boolean                // 显示文件列表，默认 true
  drag?: boolean                    // 启用拖拽上传，默认 true
  text?: string                     // 上传区提示文案
  // 其他
  disabled?: boolean                // 是否禁用
}

interface UploadProgress {
  percent: number                   // 百分比 0-100
  speed: number                     // 传输速度 KB/s
  uploaded: number                  // 已上传字节数
  total: number                     // 总字节数
  eta: number                       // 预计剩余时间（秒）
  currentChunk: number              // 当前分片序号
  totalChunks: number               // 总分片数
}

interface FileInfo {
  uid: string                       // 文件唯一标识（SHA-256 哈希）
  name: string                      // 文件名
  size: number                      // 文件大小（字节）
  url: string                       // 后端返回的文件 URI
  status: 'done' | 'error'          // 上传状态
}
// Emit: 'update:modelValue'(FileInfo[]), 'progress'(UploadProgress)
```

#### 5.2.4 StepForm Props

```typescript
interface StepFormProps {
  // 步骤定义
  steps: StepItem[]                 // 步骤数组
  // 当前状态
  current?: number                  // 当前步骤索引 (v-model:current)
  // 导航
  enableNav?: boolean               // 显示上一步/下一步按钮，默认 true
  enableSkip?: boolean              // 允许跳过步骤，默认 false
  // 验证
  validateBeforeNext?: boolean      // 下一步前验证当前步骤，默认 true
  // 提交
  submitting?: boolean              // 提交中状态
  // UI
  layout?: 'horizontal' | 'vertical'  // 步骤条布局，默认 'horizontal'
  size?: 'small' | 'default' | 'large' // 尺寸，默认 'default'
  // 响应式
  mobileBreakpoint?: number         // 移动端断点，默认 768
}

interface StepItem {
  title: string                     // 步骤标题（i18n key）
  component: DefineComponent        // 步骤内容组件 (Vue 组件)
  validate?: (values: any) => Promise<boolean>   // 步骤验证函数
  skipable?: boolean                // 是否可跳过
}
// Emit: 'update:current'(step: number), 'submit'(values: Record<string, any>)
```

### 5.3 SignaturePad 电子签名组件

**移动端触摸支持方案（V18 修复）：**
- vue-signature-pad 底层依赖 signature_pad，监听 touchstart/touchmove/touchend 事件
- **关键处理**：触摸事件回调中必须调用 `e.preventDefault()` 阻止页面跟随滚动，否则签名时页面会滚动导致签名线条偏移
- 组件封装层在 canvas 容器上额外添加 `touchstart` 监听器执行 `e.preventDefault()`，确保触摸事件不冒泡触发页面滚动
- Canvas 触摸坐标通过 `e.touches[0].clientX/Y` 转换，使用 `getBoundingClientRect()` 计算相对坐标
- 不支持多点触控签名，多点触控场景下仅跟踪主触点（index=0）

**无障碍支持：**
- 键盘操作：方向键控制画笔、Enter 确认、Escape 清空
- aria 属性：`role="img"`、`aria-label="电子签名区域"`、`aria-invalid`(签名为空时 true)、`tabindex="0"`、`:focus-visible` 样式

### 5.4 FileUpload 文件上传与分片上传

**实现架构：** Element Plus Upload 仅提供 UI 外壳（拖拽区、进度条、文件列表），分片逻辑由 `useFileUpload` Composable 实现。

**哈希计算方案（V21 修正）：**
- **V20 问题分析**：crypto-js 的 `SHA256()` 接收完整数据返回 WordArray，不返回 Hasher 实例，调用 `hasher.update()` 将抛出 TypeError
- **修正方案**：改用 `js-sha256` 库，其 `sha256()` 为类构造函数，`new sha256()` 返回 Hasher 实例，支持真正的增量哈希
- **具体实现伪代码：**
  ```
  import { sha256 } from 'js-sha256'

  async function computeFileHash(file: File): Promise<string> {
    const hasher = new sha256()
    const CHUNK_SIZE = 1024 * 1024  // 1MB
    let offset = 0
    while (offset < file.size) {
      const chunk = file.slice(offset, offset + CHUNK_SIZE)
      const buffer = await chunk.arrayBuffer()
      const uint8 = new Uint8Array(buffer)
      hasher.update(uint8)
      offset += CHUNK_SIZE
    }
    return hasher.hex()  // 返回十六进制 SHA-256 字符串
  }
  ```
- `js-sha256` gzip 后约 8KB，轻量且无额外依赖
- **大文件处理**：分片读取 1MB/块 (`file.slice(offset, offset+1MB).arrayBuffer()`)，逐块喂入 `hasher.update()`，避免 1GB 文件一次性加载导致内存溢出
- **内存控制**：单块 buffer 固定 1MB，计算完即释放；使用 `for` 循环逐块处理（非并行），确保同一时刻仅存在 1MB buffer
- **分片哈希 vs 全量哈希**：前端计算文件全量 SHA-256 哈希作为唯一标识（用于断点续传匹配），分片上传时每个分片不单独计算哈希，由后端接收全部分片后合并并验证完整性
- 浏览器兼容性：`js-sha256` 无特殊浏览器依赖，ES5 兼容

**useFileUpload 核心流程（V20 补全）：**
1. **文件选择与哈希**：用户选择文件 → 按 1MB 分片读取 → 通过 `js-sha256` 的 `hasher.update()` 逐块累积计算全量 SHA-256 哈希 → 将哈希作为文件唯一标识
2. **断点续传检查**：使用文件哈希查询 localStorage 中已上传的分片记录（24 小时过期策略），跳过已完成分片，仅上传剩余分片
3. **并发分片上传**：剩余分片采用信号量模式并发上传，默认 3 并发，文件大小超过 100MB 时自动降为 2 并发以降低网络压力
4. **重试机制**：单个分片上传失败后重试 3 次，采用指数退避策略（`retryDelay * 2^(N-1) ms`），3 次均失败则暂停上传并提示用户
5. **分片合并**：全部分片上传完成后，调用后端合并接口（POST `/api/files/{fileHash}/merge`），后端按序合并分片并验证文件完整性，返回文件 URI
6. **进度反馈**：实时更新显示上传百分比、传输速度（KB/s）、已上传/总大小、预计剩余时间（ETA）、当前/总分片数量、当前并发数
7. **取消与恢复**：用户可取消上传，取消后已完成分片保留在 localStorage 中，下次选择同一文件时可断点续传
8. **错误处理**：网络断开时自动暂停，网络恢复后提示用户继续；浏览器关闭时进度保存在 localStorage，下次打开可恢复

---

## 6. 页面布局设计

### 6.1 主布局 MainLayout

顶栏 64px（Logo + 通知铃 + 语言切换 + 用户头像） + 侧栏 200px（展开）/ 64px（折叠） + 底栏 48px + 内容区自适应。内容区内含面包屑导航、搜索栏、操作按钮区、数据表格/表单区域。

**Element Plus 组件映射：**
- 顶栏：`el-header` 或自定义 div + CSS 变量
- 侧栏：`el-aside` + `el-menu` 菜单组件
- 内容区：`el-main` + `el-container` 布局容器
- 底栏：`el-footer` 或自定义 div

### 6.2 角色侧栏菜单

| 角色 | 菜单范围 |
|------|---------|
| 系统管理员 | 全模块：工作台、招聘、入职、培训、考勤、薪资、绩效、外务、员工服务、Agent 管理、系统管理 |
| 人事专员 | 待办审核(聚合视图)、招聘、入职、培训、考勤、薪资(仅审核)、绩效、外务、员工服务 |
| 部门主管 | 待办审批、团队分析、绩效考核(下属)、培训管理(部门) |
| 普通员工 | 我的信息、工资条、考勤记录、培训记录、证明申请、费用报销、离职申请 |

### 6.3 响应式布局

| 断点 | 范围 | 布局调整 |
|------|------|---------|
| xl | ≥1536px | 标准布局 |
| lg | 1200-1535px | 标准布局 |
| md | 992-1199px | 表格列自动折叠 |
| sm | 768-991px | 侧栏折叠，卡片堆叠 |
| xs | <768px | 移动端布局 + 底部导航 |

### 6.4 移动端布局

MobileLayout 组件 + BottomTabBar（最多 5 Tab：首页、待办、快捷、我的）。顶栏 56px、底部 Tab 56px、单列卡片式布局、表格转卡片列表、手势左滑返回 + 下拉刷新。

**UniApp 实现：** UniApp 项目使用 `pages.json` 配置底部 TabBar，使用 `uni-app` 原生组件（`<scroll-view>`, `<swiper>`, `<picker>` 等）和 Element Plus 的 UniApp 兼容版本。

---

## 7. 关键页面设计

### 7.1 登录页

居中卡片：Logo + 账号/邮箱输入 + 密码输入 + 记住我复选框 + 忘记密码链接 + 登录按钮 + 新用户入职门户入口。底部语言切换（中/EN）。流程：输入 → 校验 → MFA 验证 → Dashboard。

**Element Plus 组件：** `el-form` + `el-form-item` + `el-input` + `el-checkbox` + `el-button` + `el-link`

### 7.2 管理员 Dashboard

统计卡片（在职工人/本月入职/本月离职） + Agent 运行状态面板（各 Agent 状态指示灯 + 成功率） + 待办事项列表 + 近 30 天 HR 业务趋势折线图。

**Element Plus 组件：** `el-card` + `el-row`/`el-col` 栅格 + `el-table` + ECharts

### 7.3 简历管理页

搜索栏 + 新建/导入/导出操作按钮 + 筛选区（岗位/状态/分数/日期范围） + DataTable 简历列表（姓名/岗位/分数/分类/状态/操作） + 分页栏。

**Element Plus 组件：** `el-input`(搜索) + `el-button-group` + `el-select`/`el-date-picker`(筛选) + `el-table` + `el-pagination`

### 7.4 薪资审核页

核算月份选择 + 核算状态 + 核算完成时间 + 耗时 + 异常数据区（高亮标记：工资波动超 ±20%、加班费突超 2 个标准差、社保金额为 0 但在职等） + 操作按钮（查看明细/导出底稿/确认审核/退回重算）。

**Element Plus 组件：** `el-date-picker` + `el-tag`(状态) + `el-table`(表格，使用 `cell-style` 高亮异常行) + `el-button`

### 7.5 新员工入职门户

StepForm 分步引导：基本信息 → 上传证件（身份证正反面/学历/证件照，支持拍照和文件选择） → 签署协议（SignaturePad 手写签名） → 人脸采集（摄像头 + WebRTC） → 完成。每步进度指示器（已完成/当前/待完成状态）。

**Element Plus 组件：** `el-steps` + `el-form` + `el-upload` + vue-signature-pad + WebRTC 自定义组件

### 7.6 Agent 监控面板

系统概览统计卡（运行中 Agent/今日任务数/平均成功率） + Agent 状态列表（名称/状态指示灯/今日执行次数/成功率/异常原因） + 最近告警时间线。

**Element Plus 组件：** `el-card` + `el-table` + `el-timeline` + `el-tag`(状态指示灯)

### 7.7 绩效管理页面（V21 新增）

#### 7.7.1 绩效考核列表页 /performance/review

- **页面布局**：顶部筛选栏（考核周期/部门/状态） + DataTable 考核列表（员工姓名/部门/考核周期/自评状态/上级评分状态/最终结果/操作）
- **角色差异化**：
  - 员工：仅查看自己的考核记录，可查看"发起自评"按钮（考核窗口期内）
  - 部门主管：查看下属考核记录，可查看"进行评分"按钮（自评为完成后）
  - HR/管理员：查看全公司考核记录，可"催办"、"强制完成"
- **操作区**：新建考核周期（HR/管理员）、导出考核结果、查看考核统计

#### 7.7.2 考核详情页 /performance/review/:id

- **页面布局**：左侧员工基本信息卡片 + 右侧考核内容区
- **考核内容区**：Tab 切换（考核指标/自评内容/上级评分/历史考核）
  - 考核指标：指标名称/权重/评分标准/目标值
  - 自评内容：员工自评描述 + 自评分 + 佐证材料
  - 上级评分：上级评分 + 评语 + 综合等级
  - 历史考核：历史考核记录时间线
- **操作按钮**：提交自评、提交评分、确认结果、下载考核表

**Element Plus 组件：** `el-card` + `el-tabs`/`el-tab-pane` + `el-table` + `el-timeline` + `el-button`

#### 7.7.3 考核统计页 /performance/statistics

- **页面布局**：考核周期选择 + 统计卡片（完成率/平均分分布/等级分布） + ECharts 图表（部门平均分柱状图、等级分布饼图、历史趋势折线图）

### 7.8 外务管理页面（V21 新增）

#### 7.8.1 外务总览页 /external/dashboard

- **页面布局**：顶部统计卡片（待办工伤/待办公积金/待办社保/即将到期证照） + 待办事项列表（事项类型/相关人员/截止日期/状态/操作） + 证照效期预警区（即将到期 <30 天红色、<60 天黄色、>60 天绿色）

#### 7.8.2 工伤处理页 /external/work-injury

- **页面布局**：StepForm 分步表单（工伤申报信息 → 上传证明材料 → Agent 处理进度 → 结果确认）
- **Agent 处理进度**：实时展示 Agent 自动化处理状态（信息填报中/材料审核中/系统申报中/等待审批/已完成），每步骤显示开始时间、预计完成时间、当前操作详情

#### 7.8.3 公积金管理页 /external/housing-fund

- **页面布局**：增减员操作区（新增/减少人员表格） + 申报记录列表（申报月份/增减人数/申报状态/申报时间/操作） + 历史申报导出

#### 7.8.4 社保申报页 /external/social-security

- **页面布局**：与公积金管理页类似，含增减员操作区 + 申报记录列表 + 基数调整功能

#### 7.8.5 证照管理页 /external/certificates

- **页面布局**：证照列表（证照名称/持证单位/发证日期/有效期至/状态/操作） + 效期预警统计 + renewal 提醒设置

### 7.9 系统管理页面（V21 新增）

#### 7.9.1 系统设置页 /system/settings

- **页面布局**：Tab 切换（基础设置/邮件通知/短信通知/审批流程/数据备份）
  - 基础设置：公司名称、Logo、系统公告
  - 邮件通知：SMTP 配置、邮件模板管理
  - 短信通知：短信服务商配置、短信模板
  - 审批流程：审批节点配置（可视化的流程编辑器）
  - 数据备份：备份策略设置、手动备份按钮、备份历史

**Element Plus 组件：** `el-tabs`/`el-tab-pane` + `el-form` + `el-input` + `el-button`

#### 7.9.2 用户管理页 /system/users

- **页面布局**：搜索栏 + DataTable 用户列表（姓名/工号/部门/角色/状态/最后登录/操作） + 新增用户按钮
- **操作**：编辑用户信息、分配角色、禁用/启用账号、重置密码

#### 7.9.3 角色权限页 /system/roles

- **页面布局**：左侧角色列表 + 右侧权限矩阵（模块 × 操作权限的复选框矩阵）
- **操作**：新建角色、编辑权限、复制角色

**Element Plus 组件：** `el-tree` 或 `el-menu`(左侧角色列表) + `el-table`(权限矩阵) + `el-checkbox`

#### 7.9.4 审计日志页 /system/audit

- **页面布局**：筛选区（时间范围/操作人/操作类型/模块） + DataTable 日志列表（时间/操作人/操作类型/模块/详情/IP 地址） + 导出按钮

### 7.10 培训管理页面（V21 新增）

#### 7.10.1 课程管理页 /training/courses

- **页面布局**：搜索栏 + 新建课程按钮 + DataTable 课程列表（课程名称/类型/时长/讲师/状态/参与人数/操作）
- **操作**：编辑课程、上传课程资料、安排培训计划、查看课程评价

#### 7.10.2 培训计划页 /training/plans

- **页面布局**：计划列表（计划名称/关联课程/培训日期/参与部门/状态/操作） + 日历视图（月度培训计划日历）
- **操作**：新建培训计划、分配学员、发送培训通知、查看培训报告

#### 7.10.3 我的培训页 /training/my（员工视角）

- **页面布局**：Tab 切换（待参加/进行中/已完成） + 课程卡片列表（课程名称/时间/地点/状态/签到按钮）

### 7.11 员工服务页面（V21 新增）

#### 7.11.1 证明申请页 /employee/certificate

- **页面布局**：证明类型选择（在职证明/收入证明/离职证明/其他） + StepForm 申请表单（证明信息 → 上传补充材料 → 提交确认） + 申请历史列表
- **操作**：新建申请、查看申请进度、下载已审批证明

#### 7.11.2 费用报销页 /employee/reimbursement

- **页面布局**：新建报销按钮 + DataTable 报销列表（报销类型/金额/提交日期/审批状态/操作）
- **新建报销**：StepForm（费用明细 → 上传发票 → 确认提交）

#### 7.11.3 离职申请页 /employee/resignation

- **页面布局**：离职申请表单（离职原因/最后工作日/工作交接清单） + 离职进度时间线（申请提交 → 主管审批 → HR 确认 → 离职手续 → 完成）
- **操作**：提交申请、查看进度、下载离职证明

**Element Plus 组件：** `el-form` + `el-timeline` + `el-button`

#### 7.11.4 我的信息页 /employee/profile

- **页面布局**：个人信息卡片（头像/姓名/工号/部门/职位/入职日期） + editable 信息编辑（联系方式/紧急联系人/银行卡信息） + 操作记录时间线

**Element Plus 组件：** `el-card` + `el-form` + `el-avatar` + `el-timeline`

---

## 8. 关键用户路径交互流程图（V21 新增）

### 8.1 登录认证流程

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  访问 /login │────→│  输入账号密码  │────→│  前端表单校验   │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                  │
                                   ┌──────────────┼──────────────┐
                                   │ 校验失败      │ 校验通过      │
                                   │ 显示错误提示  │              │
                                   └──────────────┘              │
                                                                 ▼
                                                    ┌───────────────────┐
                                                    │ POST /api/auth/login │
                                                    │ 提交 credentials    │
                                                    └─────────┬─────────┘
                                                              │
                                              ┌───────────────┼───────────────┐
                                              │               │               │
                                     ┌────────┴──────┐ ┌──────┴───────┐ ┌────┴────────┐
                                     │ 登录失败       │ │ 需要 MFA     │ │ 登录成功     │
                                     │ 显示错误+重试  │ │ mfa_required │ │ 设置 Cookie  │
                                     └────────────────┘ └──────┬───────┘ └────┬────────┘
                                                               │               │
                                                       ┌───────┴──────┐        │
                                                       │ 跳转 /mfa-verify│       │
                                                       │ 输入验证码     │        │
                                                       └───────┬──────┘        │
                                                               │               │
                                                   ┌───────────┼──────────┐    │
                                                   │ 验证失败   │ 验证通过   │    │
                                                   │ 重新输入   │ 设置 Cookie│    │
                                                   └───────────┘ ┌────────┴────────┐
                                                                 │                  │
                                                                 ▼                  ▼
                                                      ┌───────────────────────────────────┐
                                                      │ 跳转 / → 按角色重定向到 Dashboard  │
                                                      └───────────────────────────────────┘
```

### 8.2 入职引导流程（新员工门户）

```
┌──────────────┐     ┌──────────────┐     ┌───────────────┐
│ 收到入职邮件  │────→│ 点击链接     │────→│ 访问         │
│ 含临时令牌   │     │ 含 token 参数 │     │ /onboarding/portal?token=xxx │
└──────────────┘     └──────────────┘     └───────┬───────┘
                                                   │
                                          ┌────────┴────────┐
                                          │ Token 验证      │
                                          │ 后端验证有效性   │
                                          └────────┬────────┘
                                               ┌───┴───┐
                                               │       │
                                        ┌──────┴    ┌──┴──────┐
                                        │ Token      │ Token   │
                                        │ 无效/过期  │ 有效    │
                                        │ 显示 403   │         │
                                        └──────┘    └────┬────┘
                                                         │
                                          ┌──────────────┼──────────────┐
                                          │ Step 1: 基本信息              │
                                          │ 姓名/工号/部门/职位/入职日期   │
                                          │ 校验 → 下一步 ──────────────→ │
                                          │ Step 2: 上传证件               │
                                          │ 身份证正反面/学历/证件照       │
                                          │ FileUpload 组件 → 下一步 ───→ │
                                          │ Step 3: 签署协议               │
                                          │ 劳动合同/保密协议预览           │
                                          │ SignaturePad 手写签名 ──────→ │
                                          │ Step 4: 人脸采集               │
                                          │ WebRTC 摄像头采集 ──────────→ │
                                          │ Step 5: 完成                   │
                                          │ 显示完成提示 + 入职须知        │
                                          └────────────────────────────┘
                                                         │
                                                  ┌──────┴──────┐
                                                  │ Token 失效   │
                                                  │ 数据提交后端  │
                                                  └─────────────┘
```

### 8.3 薪资审核流程

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ HR 登录系统   │────→│ 进入薪资审核页   │────→│ 选择核算月份     │
│ 需 MFA 验证   │     │ /payroll/review  │     │ (需已通过 MFA)   │
└──────────────┘     └──────────────────┘     └───────┬──────────┘
                                                       │
                                              ┌────────┴────────┐
                                              │ 查询核算状态     │
                                              └────────┬────────┘
                                                   ┌───┴───┐
                                                   │       │
                                            ┌──────┴    ┌──┴──────┐
                                            │ Agent     │ Agent   │
                                            │ 核算中    │ 核算完成 │
                                            │ 显示进度  │          │
                                            │ 轮询 30s  │          │
                                            └──────┘   └────┬────┘
                                                             │
                                                    ┌────────┴────────┐
                                                    │ 展示核算结果     │
                                                    │ 统计卡片：       │
                                                    │ 总人数/总金额/   │
                                                    │ 平均薪资/耗时    │
                                                    │                  │
                                                    │ 异常数据区：     │
                                                    │ 高亮标记异常记录  │
                                                    └────────┬────────┘
                                                             │
                                              ┌──────────────┼──────────────┐
                                              │ 查看明细      │              │
                                              │ 弹窗展示      │              │
                                              │ 异常详情      │              │
                                              └──────────────┘              │
                                                                            │
                                                     ┌──────────────────────┼──────────────────────┐
                                                     │ 操作选择：            │                      │
                                                     │                      │                      │
                                            ┌────────┴───────┐    ┌────────┴───────┐    ┌────────┴───────┐
                                            │ 退回重算       │    │ 确认审核       │    │ 导出底稿       │
                                            │ 填写退回原因   │    │ 二次确认弹窗   │    │ 下载 PDF       │
                                            │ Agent 重新核算 │    │ 记录审计日志   │    │ 含核算明细     │
                                            └───────────────┘    └───────┬───────┘    └───────────────┘
                                                                         │
                                                                   ┌─────┴─────┐
                                                                   │ 薪资发布   │
                                                                   │ 通知员工   │
                                                                   └───────────┘
```

### 8.4 绩效考核流程

```
员工视角:
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ 收到考核通知  │────→│ 进入考核页       │────→│ 查看考核指标     │
│ (推送通知)    │     │ /performance/    │     │ 指标/权重/标准   │
└──────────────┘     └──────────────────┘     └───────┬──────────┘
                                                       │
                                              ┌────────┴────────┐
                                              │ 填写自评         │
                                              │ 每项指标评分+    │
                                              │ 描述+佐证材料    │
                                              └────────┬────────┘
                                                       │
                                              ┌────────┴────────┐
                                              │ 提交自评         │
                                              │ 状态变为"待上级  │
                                              │ 评分"           │
                                              └────────┬────────┘
                                                       │
                                              ┌────────┴────────┐
                                              │ 查看上级评分     │
                                              │ (评分完成后)     │
                                              └─────────────────┘

部门主管视角:
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ 查看待办考核  │────→│ 进入考核详情页   │────→│ 查看员工自评     │
│ (待办列表)    │     │ /performance/:id │     │ 评分/描述/材料   │
└──────────────┘     └──────────────────┘     └───────┬──────────┘
                                                       │
                                              ┌────────┴────────┐
                                              │ 填写评分         │
                                              │ 逐项评分+综合    │
                                              │ 评语+等级评定    │
                                              └────────┬────────┘
                                                       │
                                              ┌────────┴────────┐
                                              │ 提交评分         │
                                              │ 通知员工查看     │
                                              └─────────────────┘

HR/管理员视角:
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ 创建考核周期  │────→│ 设置指标/权重    │────→│ 分配考核对象     │
│ /performance/ │     │ 选择考核模板     │     │ 按部门/全员      │
└──────────────┘     └──────────────────┘     └───────┬──────────┘
                                                       │
                                              ┌────────┴────────┐
                                              │ 监控进度         │
                                              │ 完成率/催办/     │
                                              │ 强制完成         │
                                              └────────┬────────┘
                                                       │
                                              ┌────────┴────────┐
                                              │ 确认最终结果     │
                                              │ 导出考核报告     │
                                              └─────────────────┘
```

---

## 9. 无障碍访问设计

### 9.1 WCAG 2.1 AA 合规

| 要求 | 实现方式 |
|------|---------|
| 键盘可操作 | Tab 遍历所有交互元素，Esc 关闭模态框 |
| 屏幕阅读器 | aria-label, aria-describedby, role 属性全覆盖 |
| 色彩对比度 | 正文 ≥4.5:1，大文本 ≥3:1 |
| 缩放支持 | 放大至 200% 布局不破坏 |
| 焦点可见性 | :focus-visible 2px 蓝色边框 |
| 表单标签 | 每个输入框关联 label，placeholder 不替代 label |
| 错误提示 | aria-invalid + aria-errormessage |
| 动态内容 | aria-live 区域播报动态变化 |

### 9.2 关键路径无障碍清单

1. **登录认证**：所有字段可键盘操作，错误提示关联输入框，MFA 验证码输入框自动聚焦
2. **待办审核**：列表键盘导航，审核按钮明确 aria-label，结果变化 aria-live 播报
3. **工资条查看**：表格键盘导航，导出按钮明确描述，导出进度 aria-busy 反馈
4. **证明申请**：类型选择键盘操作，上传区支持拖拽和键盘，状态变化有视觉+听觉反馈
5. **扫码签到**：屏幕阅读器支持，成功/失败明确反馈，超时合理倒计时

### 9.3 无障碍测试

开发期 `axe-core` 集成（Vue 插件形式）；CI 期 Playwright 无障碍自动化测试；发布前 NVDA/JAWS 手动测试；定期 WAVE 插件全页面扫描。

### 9.4 移动端无障碍

触摸目标 ≥44×44px（WCAG 2.5.5）；手势键盘替代（左滑返回有按钮替代，下拉刷新有刷新按钮）；横屏布局自动适配，焦点管理遵循 Tab 顺序；按压态视觉反馈（opacity/颜色变化）；长按菜单提供右键键盘替代；卡片滑动删除提供按钮式入口；使用 VoiceOver/TalkBack 验证。

---

## 10. UniApp 与移动端设计

### 10.1 UniApp 架构

采用 UniApp 3.0.x 跨平台框架，一套代码编译为多端：

| 目标平台 | 编译方式 | 说明 |
|---------|---------|------|
| H5 | `uni build --platform h5` | 移动端 H5 应用 |
| 微信小程序 | `uni build --platform mp-weixin` | 微信小程序 |
| App (iOS/Android) | `uni build --platform app` | 原生 App（通过原生封装） |

**UniApp 项目结构：**
```
uniapp/
├── pages/
│   ├── index/        # 首页
│   ├── todo/         # 待办
│   ├── recruitment/  # 招聘
│   ├── onboarding/   # 入职
│   ├── training/     # 培训
│   ├── attendance/   # 考勤
│   ├── payroll/      # 薪资
│   ├── performance/  # 绩效
│   ├── external/     # 外务
│   ├── employee/     # 员工服务
│   └── login/        # 登录
├── components/       # 通用组件
├── composables/      # 组合式函数
├── stores/           # Pinia 状态管理
├── services/         # API 服务层（与 Web 端共享）
├── static/           # 静态资源
├── uni_modules/      # UniApp 模块
├── App.vue
├── main.ts
├── pages.json        # 页面路由配置
├── manifest.json     # 应用配置
└── tsconfig.json
```

### 10.2 移动端功能

- **安装**：UniApp 编译为 App 支持原生安装；H5 端通过 vite-plugin-pwa 支持 PWA 安装
- **离线**：签到页、考试页支持离线缓存（H5 端 PWA Service Worker + App 端原生缓存）
- **推送**：H5 端通过 Service Worker 接收推送；App 端通过原生推送（极光推送/个推）；小程序端通过订阅消息
- **扫码**：调用设备摄像头进行二维码扫描（UniApp `uni.scanCode` API，跨平台统一）

**SRS V15 需求对照：** SRS 4.3 节要求"支持移动端浏览与 PC 端使用"；5.1.6 节摄像头接口形态为"WebRTC 实时视频流"；考勤数据采集来自打卡设备，非浏览器 GPS。UniApp 方案完全满足 SRS 要求，且额外提供小程序和原生 App 能力。

### 10.3 移动端适配

| 功能 | PC 端 (Web) | 移动端 (UniApp) |
|------|-----------|----------------|
| 导航 | 左侧菜单 (`el-menu`) | 底部 TabBar + 侧滑菜单 |
| 表格 | `el-table` 完整表格 | 卡片式列表 (`uni-card`) |
| 表单 | 多列 `el-form` | 单列 `uni-forms` |
| 文件上传 | 拖拽上传 | 选择文件/拍照 (`uni.chooseImage`) |
| 签到 | 扫码枪/摄像头 | `uni.scanCode` 扫码 |
| 考试 | 完整试卷 | 逐题翻页 (swiper) |

### 10.4 缓存策略

| 平台 | 策略 | 说明 |
|------|------|------|
| H5 (PWA) | vite-plugin-pwa: StaleWhileRevalidate (壳), NetworkFirst (API) | 同 V23 的 SW 策略 |
| 小程序 | 本地缓存 `uni.setStorage` | 登录态、用户信息、最近访问数据 |
| App | 原生文件系统缓存 | 大文件、离线资源 |

### 10.5 ECharts 动态导入

ECharts 采用 `defineAsyncComponent` 按需加载；Dashboard 首次访问触发加载，使用骨架屏（Skeleton）占位避免布局抖动；用户登录后后台预加载 ECharts chunk；加载完成后 CSS opacity 动画 200ms 淡入。

---

## 11. 安全与性能

### 11.1 前端安全

| 安全措施 | 实现方式 |
|---------|---------|
| XSS 防护 | Vue 模板自动转义 + DOMPurify 富文本（v-html 场景） |
| CSRF 防护 | 自定义请求头 + SameSite Cookie |
| 敏感数据 | 前端不存储明文敏感数据 |
| Token 管理 | HTTP-Only Cookie + 内存 Token |
| 权限控制 | 路由守卫 + 组件级权限判断 |
| 请求签名 | 敏感操作请求携带签名 |
| 文件上传 | 类型白名单 + 大小限制 + 病毒扫描 |

### 11.2 性能优化

| 优化手段 | 目标 |
|---------|------|
| 代码分割 | 按路由 lazy loading（`defineAsyncComponent`），首屏 <300KB |
| 图片优化 | WebP 格式 + 懒加载 |
| 组件懒加载 | `defineAsyncComponent` + `<Suspense>` |
| 缓存策略 | SWR 模式，减少重复请求 |
| 防抖节流 | 搜索输入防抖 300ms，滚动节流（VueUse `useDebounceFn` / `useThrottleFn`） |
| Tree Shaking | 按需导入 Element Plus 组件 |
| 构建优化 | Vite 生产构建，gzip 压缩 |
| ECharts 按需引入 | 仅打包使用的图表模块，300-400KB gzip |

### 11.3 性能指标（V21 更新）

| 指标 | 目标值 | 说明 |
|------|--------|------|
| FCP | <1.5s | 首次内容绘制 |
| LCP | <2.5s | 最大内容绘制 |
| INP | <200ms | V21 更新：替代已废弃的 FID 指标，交互到下一次绘制 |
| CLS | <0.1 | 累积布局偏移 |
| 首屏加载 | <3s (P95) | 95 百分位首屏时间 |
| 路由切换 | <300ms | 页面间切换响应时间 |

**指标更新说明（V21）：** FID（First Input Delay）已于 2024 年被 Google 从 Core Web Vitals 中移除，替换为 INP（Interaction to Next Paint）。INP 衡量所有交互事件的延迟分布（而非仅首次），更能反映整体交互响应性。目标值从 FID 的 <100ms 调整为 INP 的 <200ms（Google 推荐良好阈值）。

### 11.4 错误边界与全局异常处理

**ErrorBoundary 组件**：使用 `app.mount()` 后注册全局 `errorHandler`，捕获组件渲染错误，显示友好错误页（刷新/返回按钮），开发环境展示错误详情（details/pre），生产环境隐藏堆栈。

**全局异常捕获**：`unhandledrejection` 和 `error` 事件监听，通过 `navigator.sendBeacon` 上报错误到 `/api/errors/report`；开发环境 `console.error`。

**Axios 拦截器**：401 → 清除 Session 并跳转 /login；403 → 跳转 /403；≥500 → 弹出通知 + 错误上报。

### 11.5 前端错误监控方案（V21 新增，V23 版本统一，V24 技术栈替换）

**Sentry SDK 集成方案：**

| 配置项 | 方案 |
|--------|------|
| SDK | @sentry/vue 8.x |
| DSN 配置 | Vite 环境变量 `VITE_SENTRY_DSN`，生产环境必填，开发环境不初始化 |
| Source Map | Vite 构建时生成 Source Map，通过 `sentry-cli` 上传到 Sentry，构建产物不包含 Source Map |
| 环境区分 | `environment: import.meta.env.MODE`（development/staging/production） |
| 版本追踪 | `release: import.meta.env.VITE_APP_VERSION`，与 git commit hash 关联 |
| 用户上下文 | 登录后自动绑定 `Sentry.setUser({ id: userId, username: name, email: email })` |
| 路由追踪 | 集成 Vue Router 4 浏览器历史追踪，自动记录路由变化 |
| 性能监控 | 启用 Transaction 追踪，追踪关键用户路径（登录、薪资审核、考核提交） |
| 采样率 | 错误上报 100%，Transaction 采样 10%（生产环境可调整为 5%） |
| 敏感信息过滤 | 自动过滤请求头中的 Authorization、Cookie；手动过滤表单中的密码字段 |
| 面包屑日志 | Axios 请求/响应自动记录为面包屑，手动记录关键用户操作 |

**Sentry 初始化代码（伪代码，V24 修正为 @sentry/vue 8.x API）：**
```
if (import.meta.env.PROD && import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    app,  // Vue 应用实例
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.MODE,
    release: import.meta.env.VITE_APP_VERSION,
    integrations: [
      Sentry.vueRouterBrowserTracingIntegration(router),  // Vue Router 追踪
      Sentry.replayIntegration()  // 会话回放
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0.1,
    beforeSend(event) {
      // 过滤敏感信息
      if (event.request?.data) {
        event.request.data = filterSensitiveData(event.request.data)
      }
      return event
    }
  })
}
```

---

## 12. 深色模式设计（V21 新增，V24 技术栈替换）

### 12.1 实现方案

使用 Element Plus 内置的深色主题 CSS 变量系统，通过覆盖 `html.dark` 下的 CSS 变量切换。

### 12.2 主题配置

| 配置项 | 亮色模式 | 深色模式 |
|--------|---------|---------|
| 机制 | Element Plus 默认 CSS 变量 | `html.dark` 下的 CSS 变量覆盖 |
| 背景色 | #FFFFFF | #141414 |
| 表面色 | #FFFFFF | #1D1E1F |
| 主色 | #409EFF | #409EFF（保持不变） |
| 文字主色 | #303133 | #E5EAF3 |
| 文字次色 | #606266 | #A3A6B0 |
| 边框色 | #DCDFE6 | #414243 |
| 组件背景 | #FFFFFF | #1D1E1F |

**深色模式切换（伪代码）：**
```
// 通过 Pinia uiStore 控制
const uiStore = useUiStore()

watch(() => uiStore.theme, (theme) => {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
})
```

### 12.3 主题切换

- **触发方式**：顶栏 ThemeToggle 组件，图标切换（太阳/月亮）
- **持久化**：uiStore.theme 值通过 `pinia-plugin-persistedstate` 存储到 localStorage，key 为 `gbm-hr-ui`
- **系统偏好跟随**：初始化时检测 `window.matchMedia('(prefers-color-scheme: dark)')`，若用户未手动设置则跟随系统
- **切换动画**：body 元素添加 CSS transition（background-color、color 200ms ease），避免闪烁
- **首次加载**：在 HTML `<head>` 中通过内联脚本检测 localStorage，设置 `class="dark"` 属性到 `<html>` 元素，防止 FOUC（无样式内容闪烁）

### 12.4 色板转换规则

- 主色、辅助色（成功/警告/错误）在深浅模式间保持不变
- 中性色（灰度）通过 CSS 变量 `html.dark` 覆盖实现自动转换
- 图表颜色：ECharts 主题通过 `useTheme` (computed) 切换 `light`/`dark` 主题配置
- 背景图片：深色模式下使用 CSS filter 调整亮度/对比度

### 12.5 深色模式注意事项

- 电子签名画布：深色模式下画布背景为 #1D1E1F，笔触颜色仍为黑色（#000），确保签名清晰可辨
- 图片/照片：深色模式下卡片背景变暗，图片自然突出，无需额外处理
- 打印样式：打印时强制使用亮色模式（`@media print` 覆盖）

---

## 13. 业务状态与交互设计（V21 新增）

### 13.1 统一业务状态 UI

| 状态 | 桌面端表现 | 移动端表现 | 触发条件 |
|------|-----------|-----------|---------|
| 加载中（列表） | Skeleton 骨架屏（3-5 行模拟卡片，Element Plus `el-skeleton`） | Skeleton 骨架屏（2-3 行） | Vue Query fetching 状态 |
| 加载中（操作） | Spin 旋转图标 + 按钮 disabled（Element Plus `el-button.loading`） | Spin 旋转图标 + 按钮 disabled | mutation isLoading 状态 |
| 空状态（无数据） | EmptyState 组件：插画 + "暂无数据"文案 + 操作按钮（如"新建"） | EmptyState 组件：小插画 + 文案 | 数据源为空数组 |
| 空状态（搜索无结果） | EmptyState 组件：插画 + "未找到匹配结果" + "清除筛选"按钮 | 同左 | 搜索/筛选后无结果 |
| 加载失败 | ErrorBoundary 捕获 + Alert 组件（Element Plus `el-alert` 红色）+ "重试"按钮 | 同左 | 网络错误、API 500 |
| 权限不足 | 跳转 /403 页面：插画 + "无权访问" + "返回"按钮 | 同左 | 403 响应 |
| 离线 | 顶部 Banner 提示 + 部分功能 disabled | 同左 | navigator.onLine === false |

### 13.2 操作撤销/恢复机制（V21 新增）

**适用场景：** 删除简历、撤回审核、取消申请、撤销评分等关键操作。

**实现方案：**

| 操作类型 | 撤销方式 | 撤销窗口 | 实现机制 |
|---------|---------|---------|---------|
| 删除简历 | Toast 提示条 + "撤销"按钮 | 5 秒 | 前端延迟删除：点击删除后标记为 pending-delete 状态，UI 移除但保留内存数据；5 秒内点击撤销则恢复；超时后调用后端删除 API |
| 撤回审核 | ConfirmDialog 二次确认 | 即时 | 后端支持撤回接口，前端调用后 Vue Query 乐观回滚 + invalidate |
| 取消申请 | ConfirmDialog 二次确认 | 即时 | 后端支持取消接口，前端调用后更新列表 |
| 撤销评分 | ConfirmDialog + 原因说明 | 即时 | 后端支持撤销接口（仅限上级评分未确认前） |

**UndoBanner 组件（V21 新增，V24 转换为 Vue 风格）：**
```typescript
interface UndoBannerProps {
  message: string                    // 提示文案
  undoText?: string                  // 撤销按钮文案，默认 '撤销'
  duration?: number                  // 自动消失时间（ms），默认 5000
}
// Emit: 'undo'
```

**实现逻辑：**
1. 用户点击删除 → 前端标记 pending-delete → 列表 UI 移除该行 → 显示 UndoBanner
2. 用户点击"撤销" → 恢复 pending-delete 数据到列表 → 隐藏 UndoBanner
3. 超时（5 秒）或用户关闭 → 调用后端 DELETE API → 真正删除
4. Vue Query mutation 的 onSuccess 中 invalidate 相关查询，确保数据一致性

### 13.3 路由动画/过渡效果（V21 新增）

详见 3.7 节路由动画设计。

---

## 14. 跨文档一致性声明（V24 新增）

本文档与以下设计文档保持技术栈一致性：

| 文档 | 一致性要求 |
|------|-----------|
| 架构设计文档 | 前端框架：Vue 3.4.x、UI 组件库：Element Plus、状态管理：Pinia 2.1.x、移动端：UniApp 3.0.x |
| 后端设计文档 | API 接口风格（RESTful）、认证方式（JWT + HTTP-Only Cookie）、数据格式（JSON） |
| 数据库设计文档 | 数据模型映射、字段命名约定 |

**V24 修正记录：**
- 已修正与架构设计文档的技术栈不一致问题（React → Vue、Ant Design → Element Plus、Zustand → Pinia、PWA → UniApp）
- 全文档所有技术引用、代码示例、组件名称、依赖列表均已更新为 Vue 生态对应方案

**V25 修正记录：**
- 已修正 Vue Query DevTools 组件 React JSX 语法残留（`initialIsOpen={false}` → `:initial-is-open="false"`）
- 已修正目录章节编号与正文不一致问题（13 章 → 14 章，补充第 8 章"关键用户路径交互流程图"）

---

*文档结束 — V25.0 — 共 14 章，V25 完成 React 语法残留修复和章节编号一致性修正*
