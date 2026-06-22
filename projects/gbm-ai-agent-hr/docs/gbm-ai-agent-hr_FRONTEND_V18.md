# GBM AI Agent HR 智能人力管理系统 — 前端设计文档 (V18)

## 版本信息

| 字段 | 值 |
|------|-----|
| 文档名称 | GBM AI Agent HR 前端设计文档 |
| 版本号 | V18.0 |
| 基于 SRS | V15.0 |
| 日期 | 2026-06-15 |
| 作者 | 后旺 (HouWang) |
| 角色 | 前端架构师 |

## 修订说明

V17→V18：修复后荣提出的全部问题：(a) 大幅压缩文档体积至可完整传输 (b) 电子签名触摸事件处理方案细化 (c) 文件分片哈希计算方案补充完整细节 (d) 核实 @dnd-kit 版本号 (e) ECharts 改用按需引入策略。内容无功能性变更。

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
| 状态管理 | Zustand | 4.x | 轻量级状态管理（仅 UI 状态） |
| 服务端状态 | @tanstack/react-query | 5.x | 所有业务数据管理 |
| HTTP 客户端 | Axios | 1.x | 请求封装与拦截 |
| 国际化 | i18next + react-i18next | - | 中/英双语 |
| 构建工具 | Vite | 5.x | 快速构建 |
| 测试 | Vitest + Testing Library | - | 单元测试 |
| 表单 | react-hook-form + zod | - | 表单验证 |
| 数据表格 | Ant Design Table | 5.x | 内置高级表格 |
| 图表 | ECharts | 5.x | 数据可视化（按需引入，体积 300-400KB gzip） |
| 文件上传 | Ant Design Upload + 自定义分片 | 5.x | Upload 提供 UI，分片逻辑由自定义 Hook 实现 |
| PDF 预览 | react-pdf | - | 在线预览 PDF |
| 电子签名 | react-signature-canvas | - | 手写签名（触摸事件需显式 preventDefault） |
| 无障碍 | @axe-core/react | - | 无障碍检测（仅开发环境） |
| PWA | workbox | 7.x | Service Worker |
| 日期选择 | dayjs | 2.x | 轻量日期库 |
| 拖拽 | @dnd-kit/core + @dnd-kit/sortable | 8.x | 拖拽排序（V18 核实：截至 2026 年中，@dnd-kit 最新稳定版为 8.x，主流生态已迁移至 8.x） |
| 通知 | Ant Design Notification | 5.x | 消息通知 |

### 1.1.1 依赖加载策略

| 类别 | 加载方式 | 包含包 |
|------|---------|--------|
| 核心依赖 | 首屏加载 | React, Ant Design, React Router, Zustand, Axios, @tanstack/react-query, dayjs |
| 按需加载 | React.lazy 动态导入 | react-pdf, react-signature-canvas |
| 按需引入 | Vite 插件按图表类型拆分 | ECharts（仅引入需要的图表类型：折线图、柱状图、饼图、热力图，体积压缩至 300-400KB gzip） |

**ECharts 按需引入方案（V18 新增）：**
- 不使用 ECharts 完整构建（~900KB gzip），改为按需引入
- Vite 配置中设置 `echarts` 插件，仅打包使用的图表模块
- 代码层面使用 `import { init } from 'echarts/core'` + `import { BarChart, LineChart, PieChart, HeatmapChart } from 'echarts/charts'` + `import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'`
- 完整构建仅用于开发环境快速调试

**构建期配置说明：**
- **workbox (PWA)**：Service Worker 为构建时注册的独立脚本，由 Vite 插件在构建阶段生成
- **@axe-core/react (无障碍)**：开发期工具，仅开发环境生效，不包含在生产构建中

### 1.2 设计规范

- **设计系统**：Ant Design 5.x Token 系统，ConfigProvider 管理全局 Design Token
- **色彩规范**：主色 #1890FF，辅助色 #52C41A（成功）、#FAAD14（警告）、#FF4D4F（错误）
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
│   ├── feedback/   # ConfirmDialog, Toast, EmptyState, ErrorBoundary
│   └── layout/     # MainLayout, PageHeader, CardContainer, TabContainer, BottomTabBar, MobileLayout
├── hooks/          # useAuth, usePermission, usePagination, useDebounce, useFileUpload(分片上传), useChartPreload
├── stores/         # Zustand 状态（仅 UI 交互状态）
│   ├── authStore.ts    # 认证 UI 状态
│   └── uiStore.ts      # 全局 UI 状态（侧栏、主题、语言、通知、面包屑）
├── services/       # API 服务层（auth, recruitment, onboarding, training, attendance, payroll, performance, external, employee, agent, file）
├── pages/          # 页面组件（按功能模块：auth, dashboard, recruitment, onboarding, training, attendance, payroll, performance, external, employee, agent, system, error）
├── routes/         # 路由配置（index.tsx, protectedRoute.tsx, roleRoute.tsx, routeConfig.ts）
├── types/          # TypeScript 类型定义
├── utils/          # 工具函数
├── i18n/           # 国际化（zh-CN/, en/ 各 11 个模块翻译文件）
├── App.tsx
└── main.tsx
tests/              # unit/, integration/, accessibility/
```

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

- **认证守卫**：ProtectedRoute 组件检查 authStore.isAuthenticated，未认证重定向到 /login
- **MFA 守卫**：标记 `mfa: true` 的路由需二次验证，未验证跳转 /mfa-verify
- **角色守卫**：RoleRoute 组件对比 authStore.roles 与路由配置 roles 数组
- **行级权限**：工资条等页面由后端 API 返回用户有权查看的数据，前端不自行过滤
- **临时令牌**：入职门户使用一次性 Token，考试页使用一次性 Token，验证后失效

### 3.3 路由配置

路由配置采用 `RouteConfig` 数组定义，每条目含 path、component、roles、title(i18n key)、icon、hidden(是否侧栏隐藏)、mfa 字段。运行时由 `routeConfig.ts` 导出，`index.tsx` 将其映射为 React Router 的 `createBrowserRouter` 路由树。

---

## 4. 状态管理

### 4.1 状态分层

三层架构：(a) Zustand 管理全局 UI 交互状态（仅 2 个 store） (b) React Query 管理所有业务数据（服务端状态） (c) useState 管理页面级本地状态

### 4.2 authStore（认证 UI 状态）

存储 isAuthenticated、isLoading、mfaRequired、mfaMethod、user(仅 UI 展示字段)、roles、permissions。

**边界说明：** authStore 存储的是 UI 展示状态，用于控制界面渲染（侧栏菜单、头像等）。认证 Token 由 HTTP-Only Cookie 管理，前端 JS 不可访问。真正认证验证由后端中间件完成。用户信息刷新通过 React Query `useQuery(['auth','me'])` 调用后同步更新 authStore。

### 4.3 uiStore（全局 UI 状态）

存储 siderCollapsed、theme、language、notifications、unreadCount、breadcrumb。通过 ConfigProvider 联动 Ant Design 全局样式。

### 4.4 React Query 数据获取

- **缓存**：列表 5 分钟、详情 1 分钟 staleTime
- **乐观更新**：表单提交先更新 UI，失败回滚
- **自动重试**：网络错误重试 2 次，指数退避
- **请求取消**：组件卸载自动取消
- **依赖查询**：mutation 后 invalidate 相关查询
- **Agent 轮询**：Agent 状态使用 `refetchInterval: 30s` 轮询

### 4.5 Zustand 持久化

authStore 不使用 persist（Token 在 HTTP-Only Cookie）。非敏感表单草稿（如入职模块）使用 Zustand persist 中间件，key 为 `gbm-hr-onboarding-form`。

---

## 5. 组件体系

### 5.1 组件分类

| 分类 | 说明 | 代表组件 |
|------|------|---------|
| 布局组件 | 页面骨架 | MainLayout, PageHeader, CardContainer, MobileLayout, BottomTabBar |
| 导航组件 | 页面导航 | AppSider, BreadcrumbNav, TabContainer |
| 数据展示 | 表格/列表/详情 | DataTable (含分页/排序/筛选/虚拟滚动/导出), ResumeCard, EmployeeProfileCard |
| 表单组件 | 输入/选择/上传 | StepForm(入职/工伤/离职分步表单), FileUpload, ImageCropper, SignaturePad, DatePickerRange |
| 反馈组件 | 提示/确认/加载 | ConfirmDialog, Toast, EmptyState, ErrorBoundary |
| 业务组件 | 特定业务逻辑 | QRCheckIn(摄像头扫码签到), ExamPaper(在线考试), PayrollTable(薪资审核表格) |

### 5.2 SignaturePad 电子签名组件

**移动端触摸支持方案（V18 修复）：**
- react-signature-canvas 底层依赖 signature_pad，监听 touchstart/touchmove/touchend 事件
- **关键处理**：触摸事件回调中必须调用 `e.preventDefault()` 阻止页面跟随滚动，否则签名时页面会滚动导致签名线条偏移
- 组件封装层在 canvas 容器上额外添加 `touchstart` 监听器执行 `e.preventDefault()`，确保触摸事件不冒泡触发页面滚动
- Canvas 触摸坐标通过 `e.touches[0].clientX/Y` 转换，使用 `getBoundingClientRect()` 计算相对坐标
- 不支持多点触控签名，多点触控场景下仅跟踪主触点（index=0）

**无障碍支持：**
- 键盘操作：方向键控制画笔、Enter 确认、Escape 清空
- aria 属性：`role="img"`、`aria-label="电子签名区域"`、`aria-invalid`(签名为空时 true)、`tabindex="0"`、`:focus-visible` 样式

### 5.3 FileUpload 文件上传与分片上传

**实现架构：** Ant Design Upload 仅提供 UI 外壳（拖拽区、进度条、文件列表），分片逻辑由 `useFileUpload` Hook 实现。

**哈希计算方案（V18 修复）：**
- 算法：SHA-256，使用浏览器原生 **Web Crypto API** `crypto.subtle.digest('SHA-256', buffer)`，无需第三方库
- **大文件处理**：采用分片读取 + 累积哈希，每次读取 1MB 块 (`file.slice(offset, offset+1MB).arrayBuffer()`)，逐块喂入 `crypto.subtle.digest()`，避免 1GB 文件一次性加载导致内存溢出
- **内存控制**：单块 buffer 固定 1MB，计算完即释放；使用 `for` 循环逐块处理（非并行），确保同一时刻仅存在 1MB buffer
- **分片哈希 vs 全量哈希**：前端计算文件全量 SHA-256 作为唯一标识（用于断点续传匹配），分片上传时每个分片不单独计算哈希，由后端接收全部分片后合并并验证完整性
- 浏览器兼容性：Web Crypto API 支持 Chrome 54+、Firefox 42+、Safari 10+、Edge 79+

**useFileUpload 核心流程：**
1. 文件选择 → 计算 SHA-256 哈希（分片读取，1MB/块）→ 查询已上传分片记录（localStorage，24h 过期）→ 跳过已完成分片
2. 剩余分片并发上传（信号量模式，默认 3 并发，>100MB 自动降为 2）
3. 单分片失败重试 3 次（指数退避：`retryDelay * 2^(N-1) ms`）
4. 全部分片完成 → 调用后端合并接口 → 返回文件 URI
5. 进度实时反馈：百分比、速度(KB/s)、已上传/总大小、ETA、当前/总分片、并发数

---

## 6. 页面布局设计

### 6.1 主布局 MainLayout

顶栏 64px（Logo + 通知铃 + 语言切换 + 用户头像） + 侧栏 200px（展开）/ 64px（折叠） + 底栏 48px + 内容区自适应。内容区内含面包屑导航、搜索栏、操作按钮区、数据表格/表单区域。

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

---

## 7. 关键页面设计

### 7.1 登录页

居中卡片：Logo + 账号/邮箱输入 + 密码输入 + 记住我复选框 + 忘记密码链接 + 登录按钮 + 新用户入职门户入口。底部语言切换（中/EN）。流程：输入 → 校验 → MFA 验证 → Dashboard。

### 7.2 管理员 Dashboard

统计卡片（在职工人/本月入职/本月离职） + Agent 运行状态面板（各 Agent 状态指示灯 + 成功率） + 待办事项列表 + 近 30 天 HR 业务趋势折线图。

### 7.3 简历管理页

搜索栏 + 新建/导入/导出操作按钮 + 筛选区（岗位/状态/分数/日期范围） + DataTable 简历列表（姓名/岗位/分数/分类/状态/操作） + 分页栏。

### 7.4 薪资审核页

核算月份选择 + 核算状态 + 核算完成时间 + 耗时 + 异常数据区（高亮标记：工资波动超 ±20%、加班费突超 2 个标准差、社保金额为 0 但在职等） + 操作按钮（查看明细/导出底稿/确认审核/退回重算）。

### 7.5 新员工入职门户

StepForm 分步引导：基本信息 → 上传证件（身份证正反面/学历/证件照，支持拍照和文件选择） → 签署协议（SignaturePad 手写签名） → 人脸采集（摄像头 + WebRTC） → 完成。每步进度指示器（已完成/当前/待完成状态）。

### 7.6 Agent 监控面板

系统概览统计卡（运行中 Agent/今日任务数/平均成功率） + Agent 状态列表（名称/状态指示灯/今日执行次数/成功率/异常原因） + 最近告警时间线。

---

## 8. 无障碍访问设计

### 8.1 WCAG 2.1 AA 合规

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

### 8.2 关键路径无障碍清单

1. **登录认证**：所有字段可键盘操作，错误提示关联输入框，MFA 验证码输入框自动聚焦
2. **待办审核**：列表键盘导航，审核按钮明确 aria-label，结果变化 aria-live 播报
3. **工资条查看**：表格键盘导航，导出按钮明确描述，导出进度 aria-busy 反馈
4. **证明申请**：类型选择键盘操作，上传区支持拖拽和键盘，状态变化有视觉+听觉反馈
5. **扫码签到**：屏幕阅读器支持，成功/失败明确反馈，超时合理倒计时

### 8.3 无障碍测试

开发期 `@axe-core/react` 集成；CI 期 Playwright 无障碍自动化测试；发布前 NVDA/JAWS 手动测试；定期 WAVE 插件全页面扫描。

### 8.4 移动端无障碍

触摸目标 ≥44×44px（WCAG 2.5.5）；手势键盘替代（左滑返回有按钮替代，下拉刷新有刷新按钮）；横屏布局自动适配，焦点管理遵循 Tab 顺序；按压态视觉反馈（opacity/颜色变化）；长按菜单提供右键键盘替代；卡片滑动删除提供按钮式入口；使用 VoiceOver/TalkBack 验证。

---

## 9. 国际化设计

### 9.1 语言支持

简体中文 (zh-CN，默认) + 英语 (en)。

### 9.2 翻译资源

`i18n/zh-CN/` 和 `i18n/en/` 各 11 个 JSON 文件：common, recruitment, onboarding, training, attendance, payroll, performance, external, employee, agent, system。

### 9.3 格式适配

日期：zh-CN → `YYYY年MM月DD日`，en → `toLocaleDateString('en-US')`；金额：zh-CN → `¥X,XXX.XX`，en → `$X,XXX.XX`。

### 9.4 覆盖率

UI 文本翻译覆盖率 ≥95%；同术语翻译一致率 100%；每版本上线前双语全覆盖测试。

---

## 10. PWA 与移动端设计

### 10.1 PWA 功能

- **安装**：manifest.json 支持桌面安装
- **离线**：签到页、考试页支持离线缓存
- **推送**：Service Worker 接收服务端推送通知
- **扫码**：调用设备摄像头进行二维码扫描（WebRTC）

**SRS V15 需求对照：** SRS 4.3 节要求"支持移动端浏览与 PC 端使用"为 Web/PWA 要求，非原生应用；5.1.6 节摄像头接口形态为"WebRTC 实时视频流"；考勤数据采集来自打卡设备，非浏览器 GPS。PWA 方案完全满足 SRS 要求。

### 10.2 移动端适配

| 功能 | PC 端 | 移动端 |
|------|-------|--------|
| 导航 | 左侧菜单 | 底部 Tab + 汉堡菜单 |
| 表格 | 完整表格 | 卡片式列表 |
| 表单 | 多列布局 | 单列布局 |
| 文件上传 | 拖拽上传 | 选择文件/拍照 |
| 签到 | 扫码枪/摄像头 | 摄像头扫码 |
| 考试 | 完整试卷 | 逐题翻页 |

### 10.3 Service Worker 策略

- 应用壳资源：StaleWhileRevalidate
- API 请求：NetworkFirst，仅缓存 200 状态码
- 签到/考试页：StaleWhileRevalidate（离线可用）

### 10.4 ECharts 动态导入

ECharts 采用 React.lazy 按需加载；Dashboard 首次访问触发加载，使用骨架屏（Skeleton）占位避免布局抖动；用户登录后后台预加载 ECharts chunk；加载完成后 CSS opacity 动画 200ms 淡入。

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
| 文件上传 | 类型白名单 + 大小限制 + 病毒扫描 |

### 11.2 性能优化

| 优化手段 | 目标 |
|---------|------|
| 代码分割 | 按路由 lazy loading，首屏 <300KB |
| 图片优化 | WebP 格式 + 懒加载 |
| 组件懒加载 | React.lazy + Suspense |
| 缓存策略 | SWR 模式，减少重复请求 |
| 防抖节流 | 搜索输入防抖 300ms，滚动节流 |
| Tree Shaking | 按需导入 Ant Design 组件 |
| 构建优化 | Vite 生产构建，gzip 压缩 |
| ECharts 按需引入 | 仅打包使用的图表模块，300-400KB gzip |

### 11.3 性能指标

| 指标 | 目标值 |
|------|--------|
| FCP | <1.5s |
| LCP | <2.5s |
| FID | <100ms |
| CLS | <0.1 |
| 首屏加载 | <3s (P95) |
| 路由切换 | <300ms |

### 11.4 错误边界与全局异常处理

**ErrorBoundary 组件**：捕获子组件渲染错误，显示友好错误页（刷新/返回按钮），开发环境展示错误详情（details/pre），生产环境隐藏堆栈。

**全局异常捕获**：`unhandledrejection` 和 `error` 事件监听，通过 `navigator.sendBeacon` 上报错误到 `/api/errors/report`；开发环境 `console.error`。

**Axios 拦截器**：401 → 清除 Session 并跳转 /login；403 → 跳转 /403；≥500 → 弹出通知 + 错误上报。

---

*文档结束 — V18.0 — 共 11 章，确保完整交付*
