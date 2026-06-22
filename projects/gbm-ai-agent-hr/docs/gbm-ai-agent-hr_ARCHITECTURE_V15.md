# GBM AI Agent HR 智能人力管理系统 — 架构设计文档 (V15)

## 版本信息

| 版本号 | 日期 | 作者 | 说明 |
|--------|------|------|------|
| 15.0 | 2026-06-15 | 后旺 | 基于后荣检验意见修订：(1)确保18章完整提交 — V15以 write_file 工具写入磁盘，经行号校验确保全部 18 章内容完整无缺失；(2)简化网关架构 — 移除 Nginx Ingress 层，采用 K8s Nginx Ingress Controller 单层网关方案，移除 Spring Cloud Gateway 独立部署，鉴权/限流/路由下沉至 Agent 服务自身，理由：4 个域服务规模不足以支撑双层网关的运维成本（见第 2.2 节）；(3)重新评估微服务拆分粒度 — 将 8 个 Agent 服务群合并为 4 个域服务：用户中心域（原 user-agent + cert-agent）、招聘培训域（原 recruit-agent + train-agent）、薪酬考勤域（原 comp-agent + perf-agent）、分析自动化域（原 analytics-agent + auto-agent），提供拆分合理性论证和合并方案对比（见第 1.1/3 节/6.1 节）；(4)补充性能目标和容量规划 — 新增第 1.4 节明确并发用户数（500）、响应时间 SLA（P95 < 2s）、吞吐量目标（1000 QPS），以此作为中间件配置的合理性依据；(5)简化 Redis 部署 — 从 5 节点哨兵改为 3 节点 Redis Cluster 模式，更匹配 HR 系统缓存/会话场景（见第 5.5 节）；(6)重新评估 Camunda 8 方案 — 保留 Camunda 8 Self-managed，但简化部署组件（移除 Optimize，仅保留 Zeebe + Operate + Tasklist），补充 Temporal 方案对比论证（见第 5.5 节）；(7)统一 Face++ 本地部署 — 替换为 InsightFace 本地部署方案，符合用户"偏好本地部署，不信任云端方案"的要求（见第 2.5 节/4.3 节）；(8)明确 auto-agent 定位 — 将 auto-agent 明确定义为"共享基础设施服务"而非独立业务 Agent，在架构图中调整至 AI 模型服务层之下、Agent 服务群之上的独立层（见第 1.2/3.7 节）；(9)修正 Milvus 层级归属 — Milvus 统一归属数据基础设施层，AI 模型服务层仅保留模型推理组件（见第 1.2 节） |

---

## 目录

1. 架构概述
2. 分层架构设计
3. 模块划分与职责
4. 技术栈选型
5. 部署架构
6. 关键设计决策
7. 分布式事务与数据一致性
8. 安全合规与数据保护
9. 数据备份与灾难恢复
10. 数据库迁移与版本管理
11. 数据字典与编码规范
12. Agent 异常处理与补偿机制
13. 多租户隔离策略
14. Agent 间通信机制
15. 跨服务数据流设计
16. 需求覆盖验证矩阵
17. 国际化(i18n/l10n)架构设计
18. 无障碍访问架构设计

---

## 1. 架构概述

### 1.1 设计目标

GBM AI Agent HR 系统采用 **AI 原生微服务架构**，以 AI Agent 为系统核心执行主体，实现人力资源管理全流程的自动化。架构设计遵循以下原则：

1. **零操作性原则** — 所有操作性事务由 Agent 自主完成，人类仅承担审核与仲裁
2. **适度微服务** — 按业务域合理聚合为 **4 个域服务**（V15 修订：从 V14 的 8 个服务群合并为 4 个），避免过度拆分导致的数据分散和跨服务调用爆炸。合并理由详见第 6.1 节
3. **事件驱动** — 域服务间通过消息队列异步通信
4. **配置驱动** — 业务规则（薪资、考勤、筛选权重）以配置形式管理
5. **可观测性** — 完整的链路追踪（OpenTelemetry + Jaeger，详见第 2.4.1 节）、日志、监控
6. **服务治理** — 通过 K8s Service + Resilience4j 应用层熔断统一管理服务间通信（详见第 6.6 节服务治理方案）

### 1.2 架构全景

```
+------------------------------------------------------------------+
|                        展示层 (Frontend)                           |
|  +----------+  +----------+  +----------+  +----------+           |
|  | Web应用   |  | 移动端   |  | 扫码入口  |  | 通知推送  |           |
|  |(Vue 3)   |  |(UniApp)  |  |(H5)     |  |(SMS/邮件)|           |
|  +----------+  +----------+  +----------+  +----------+           |
+------------------------------------------------------------------+
|                      网关层 (Gateway)                              |
|  +-------------------------------------------------------------+  |
|  |  K8s Nginx Ingress Controller                              |  |
|  |  (SSL终止/路由转发/静态资源)                                 |  |
|  |  注：V15移除Spring Cloud Gateway，鉴权/限流下沉至Agent服务     |  |
|  +-------------------------------------------------------------+  |
+------------------------------------------------------------------+
|                    Agent 编排调度层 (Orchestration)                |
|  +-------------+  +-------------+  +-------------+               |
|  | 流程定义引擎  |  | 任务分解器   |  | 状态管理器   |               |
|  |(Camunda 8/  |  |  (BPMN并行   |  |(Redis+DB)   |               |
|  |  Zeebe)    |  |  网关+Worker)|               |               |
|  +-------------+  +-------------+  +-------------+               |
|  +-------------------------------------------------------------+ |
|  |              事件总线 (Kafka 3节点集群)                       | |
|  |  域服务间异步通信 / 事件发布订阅 / 流程状态流转                | |
|  |  replication-factor=3, acks=all, min.insync.replicas=2       | |
|  +-------------------------------------------------------------+ |
+------------------------------------------------------------------+
|                     AI Agent 域服务群 (4个)                        |
|  +------------------+  +------------------+                      |
|  | 用户中心域        |  | 招聘培训域        |                      |
|  | (user-domain    |  | (recruit-domain  |                      |
|  |  :8081)         |  |  :8082)          |                      |
|  | 原user-agent    |  | 原recruit-agent   |                      |
|  | + cert-agent    |  | + train-agent    |                      |
|  +------------------+  +------------------+                      |
|  +------------------+  +------------------+                      |
|  | 薪酬考勤域        |  | 分析自动化域      |                      |
|  | (payroll-domain |  | (auto-domain    |                      |
|  |  :8083)         |  |  :8084)          |                      |
|  | 原comp-agent    |  | 原analytics-agent |                      |
|  | + perf-agent    |  | + auto-agent     |                      |
|  +------------------+  +------------------+                      |
|  端口分配：8081~8084连续分配，各域内部模块端口详见第6.3节             |
+------------------------------------------------------------------+
|                   共享基础设施服务层                                |
|  +-------------------------------------------------------------+ |
|  |  auto-agent (OCR + RPA 共享服务 :8085)                      | |
|  |  定位：共享基础设施服务，非独立业务 Agent                       | |
|  |  被用户中心域、招聘培训域、薪酬考勤域调用                       | |
|  +-------------------------------------------------------------+ |
+------------------------------------------------------------------+
|                      AI 模型服务层                                 |
|  +----------+ +----------+ +----------+ +----------+             |
|  | LLM推理   | | OCR推理   | | 人脸服务   | | Embedding|             |
|  |(vLLM)    | |(PaddleOCR)| |(InsightFa | |(bge-m3)  |             |
|  |          | |          | | ce本地)   | |          |             |
|  +----------+ +----------+ +----------+ +----------+             |
|  +----------+ +----------+ +----------+                          |
|  | ASR语音   | | 多模态    | | TTS语音   |                          |
|  |(Whisper) | |(Qwen-VL) | |(Edge-TTS)|                          |
|  +----------+ +----------+ +----------+                          |
|  调用方式：HTTP REST / gRPC，统一通过 AI 模型网关组件管理            |
|  降级策略：本地模型不可用时自动切换云端 API                         |
|  Embedding与Milvus关系：bge-m3生成向量→写入Milvus供检索            |
|  V15修订：人脸服务由 Face++ 改为 InsightFace 本地部署               |
+------------------------------------------------------------------+
|                      数据基础设施层                                 |
|  +------+ +------+ +------+ +------+ +------+ +------+           |
|  |MySQL | |Redis | |Kafka | |MinIO | |ES    | |Milvus|           |
|  |8.x   | |7.x   | |3.x   |      | |8.x   |      |           |
|  |(主从) | |(集群) | |(集群) |      | (集群) |      |           |
|  +------+ +------+ +------+ +------+ +------+ +------+           |
|  MinIO职责：培训视频/OCR原始图片/入职材料归档/备份存储               |
+------------------------------------------------------------------+
```

### 1.3 架构原则

| 原则 | 说明 |
|------|------|
| Agent-First | 每项功能以 AI Agent 为核心设计，不存在先人工后自动化的过渡路径 |
| 适度微服务 | 按业务域聚合为 **4 个域服务**，V15 从 V14 的 8 个合并，详见第 6.1 节 |
| 事件驱动 | 域服务间通过 Kafka 异步通信，降低耦合度 |
| 配置驱动 | 薪资规则、考勤规则、筛选权重等以配置化管理 |
| 端到端可追溯 | 每条业务流程拥有唯一 flow_id，全链路 trace-id 追踪；技术选型：OpenTelemetry + Jaeger，详见第 2.4.1 节 |
| 安全护栏 | 关键操作设有自动阻断规则，需满足预设条件方可放行 |

### 1.4 性能目标与容量规划（V15 新增）

**系统规模预估**：

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 并发在线用户数 | 500 | 企业 HR 系统规模，含在职员工、人事专员、部门主管 |
| 峰值 QPS | 1,000 | 集中在薪资发放日、考勤汇总日等业务高峰 |
| 响应时间 SLA (P95) | < 2 秒 | 普通查询/操作类接口 |
| 响应时间 SLA (P99) | < 5 秒 | 复杂报表/批量操作类接口 |
| Agent 推理响应 | < 10 秒 | 简历匹配、薪资核算等 AI 推理场景 |
| 系统可用性 | 99.9% | 全年计划外停机时间 < 8.76 小时 |
| 数据 RPO | ≤ 5 分钟 | 基于 MySQL binlog 实时同步 |
| 数据 RTO | ≤ 2 小时 | 应用层无状态，重启即可恢复 |

**中间件配置依据**：

| 组件 | 配置 | 与性能目标的关联 |
|------|------|----------------|
| Kafka 3 节点 | replication-factor=3, acks=all | 500 并发用户 × 日均操作 50 次 = 25,000 事件/天，Kafka 万级吞吐绰绰有余 |
| Redis Cluster 3 节点 | 主从复制 + Cluster 分片 | 500 用户 Session 缓存 + 高频查询缓存，3 节点 Redis Cluster 足以承载 < 10,000 QPS 的缓存请求 |
| MySQL 主从 | 1 主 2 从 | 写操作 < 100 QPS（HR 系统写操作低频），读操作 < 1,000 QPS，单主库完全满足 |
| ES 3 节点 | 标准集群 | 简历检索和日志检索，峰值 < 100 QPS，3 节点提供冗余和高可用 |
| Milvus | 单节点起步 | 向量检索低频场景（简历语义检索 < 50 QPS），单节点 + 定期备份即可 |

**容量扩展触发条件**：

| 指标 | 触发阈值 | 扩展方案 |
|------|---------|---------|
| CPU 使用率 | 持续 > 70% 超过 1 小时 | 域服务 HPA 自动扩容 |
| 数据库连接池 | 使用率 > 80% | 增加从库节点或调整连接池上限 |
| Kafka 消息堆积 | 消费者延迟 > 30 秒 | 增加消费者副本或分区数 |
| 单表数据量 | > 2,000 万行 | 触发分库分表评估（见第 2.6.1 节） |

---

## 2. 分层架构设计

### 2.1 展示层 (Presentation Layer)

**职责**：面向不同用户角色提供交互界面，统一入口。

**子层**：
- **Web UI**：面向人事专员、部门主管、系统管理员的桌面端操作界面
- **Mobile UI**：面向在职员工、新员工的移动端自助服务
- **扫码页**：H5 应用，用于考试签到、培训签到等场景
- **通知渠道**：邮件和短信通知，由后端服务主动推送

**技术选型**：
- 框架：Vue 3 + TypeScript
- UI 库：Element Plus
- 移动端：UniApp（一套代码多端发布）
- 构建工具：Vite
- 状态管理：Pinia
- 路由：Vue Router 4
- HTTP 客户端：Axios + 请求拦截器

### 2.2 网关层 (Gateway Layer)

**职责**：

V15 修订：**移除双层网关，采用 K8s Nginx Ingress Controller 单层方案。**

原 V14 采用 Nginx Ingress + Spring Cloud Gateway 双层架构。经后荣检验指出，对于 4 个域服务的规模，双层网关过度设计。V15 简化为：

| 层级 | 组件 | 职责范围 | 处理内容 |
|------|------|---------|---------|
| 入口层 | K8s Nginx Ingress Controller | SSL 终止、路由转发、静态资源、基础限流 | TLS 1.2+ 解密、路径路由至域服务、静态文件缓存、连接级限流、健康检查 |

**移除 Spring Cloud Gateway 的理由**：

| 维度 | 双层方案 (V14) | 单层方案 (V15) | 决策依据 |
|------|---------------|---------------|---------|
| 延迟 | Nginx + SCG 双层跳转，增加 5-15ms | 仅 Nginx 一层，延迟 < 2ms | 4 个域服务的路由规则简单，无需 Java 层网关 |
| 运维 | 需维护 SCG 独立 Pod 集群 + 配置 | 仅维护 K8s Ingress 资源 | SCG 需要独立部署、独立监控、独立扩缩容 |
| 鉴权 | SCG 统一 JWT 校验 | 各域服务内置 Spring Security 校验 | JWT 校验是轻量操作（< 1ms），下沉至域服务不会造成性能瓶颈 |
| 限流 | SCG + Sentinel 业务维度限流 | Nginx Ingress 连接级限流 + 域服务内 Resilience4j | HR 系统峰值 1,000 QPS，Nginx 连接级限流（如 `limit_req`）已足够 |
| API 版本管理 | SCG 路径路由 | Nginx Ingress 路径路由 | `/api/v1/...` 路由规则 Nginx 完全可处理 |

**网关功能清单**（由 Nginx Ingress + 域服务内置能力分担）：
- 请求路由与负载均衡（Nginx Ingress 根据路径前缀路由至对应域服务）
- JWT 认证过滤（各域服务内置 Spring Security 认证过滤器，详见第 2.2.1 节）
- 速率限制（Nginx Ingress `limit_req` 模块实现连接级限流；业务维度限流由域服务内 Resilience4j 的 RateLimiter 组件承担）
- CORS 跨域处理（Nginx Ingress 配置 `add_header` 实现）
- 请求/响应日志记录（Nginx 访问日志 → Filebeat → ELK）
- API 版本管理（Nginx Ingress 路径路由 `/api/v1/...`，详见第 2.2.2 节）
- 统一错误码映射（各域服务内置全局异常处理器）

**Ingress 路由规则示例**：
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: hr-ingress
  annotations:
    nginx.ingress.kubernetes.io/limit-rps: "500"
spec:
  rules:
  - host: hr.gbm.com
    http:
      paths:
      - path: /api/v1/auth
        pathType: Prefix
        backend:
          service:
            name: user-domain
            port:
              number: 8081
      - path: /api/v1/recruit
        pathType: Prefix
        backend:
          service:
            name: recruit-domain
            port:
              number: 8082
      - path: /api/v1/payroll
        pathType: Prefix
        backend:
          service:
            name: payroll-domain
            port:
              number: 8083
      - path: /api/v1/analytics
        pathType: Prefix
        backend:
          service:
            name: auto-domain
            port:
              number: 8084
```

#### 2.2.1 认证授权完整策略

**JWT 签发方**：
- JWT 由 **用户中心域服务（user-domain, :8081）** 内的认证服务签发
- 认证流程：用户提交凭证 → Nginx Ingress 路由至 user-domain 的 `/auth/login` → 验证通过后生成 JWT → 返回客户端
- JWT 结构：`header.payload.signature`，payload 包含 `user_id`、`roles`、`permissions`、`tenant_id`、`exp`、`iat`、`jti`

**Token 类型与刷新机制**：
- **Access Token**：有效期 30 分钟，用于 API 请求鉴权
- **Refresh Token**：有效期 7 天，存储于 HttpOnly Cookie，用于静默刷新 Access Token
- **刷新流程**：Access Token 过期 → 前端拦截 401 → 携带 Refresh Token 调用 `/auth/refresh` → 获得新 Access Token → 自动重试原请求
- **Refresh Token 轮换**：每次刷新颁发新 Refresh Token，旧 Token 立即失效，防止 Token 泄露后被长期利用

**多端共享认证**：
- Web、移动端（UniApp）、H5 扫码页共享同一套 JWT 认证体系
- Token 中 `device_type` 字段标识来源设备（`web`/`mobile`/`h5`）
- 同一用户多端同时在线时，各端拥有独立 Token 生命周期，互不影响
- 用户注销（logout）可指定设备类型仅注销单端，或选择"全部设备下线"（吊销该用户所有未过期 Token，记录至 Redis 黑名单）

**移动端敏感操作二次验证**：
- 触发场景：薪资查询、个人信息修改、离职申请、批量导出
- 方案：短信验证码 + 生物识别（移动端指纹/Face ID）
- 流程：用户发起敏感操作 → 域服务拦截 → 返回 403 + `requires_mfa` 标记 → 前端弹出验证码输入框 → 提交验证码 → user-domain 验证通过 → 颁发短期授权凭证（10 分钟有效） → 放行原请求
- 验证码有效期 5 分钟，错误 3 次锁定 30 分钟

**Token 存储安全策略**：

| Token 类型 | 存储位置 | Cookie 配置 | 安全考虑 |
|-----------|---------|------------|---------|
| Access Token | 前端内存（JavaScript 变量） | 不使用 Cookie | 防 XSS，页面刷新后需 Refresh Token 重新获取 |
| Refresh Token | HttpOnly Cookie | `HttpOnly=True`、`Secure=True`、`SameSite=Strict`、`Path=/auth/refresh` | 防 XSS/CSRF，仅 HTTPS |
| 移动端 Token | 原生安全存储 | iOS Keychain / Android Keystore | 防逆向，卸载后清除 |

**Token 撤销与黑名单机制**：

| 撤销场景 | 处理方式 | 影响范围 |
|---------|---------|---------|
| 用户主动登出 | 当前 Token jti 写入 Redis 黑名单 | 仅当前设备 |
| 密码修改 | 该用户所有未过期 Token jti 写入黑名单 | 全设备强制下线 |
| 管理员禁用账号 | 所有 Token jti 写入黑名单 + Redis Session 清除 | 全设备强制下线 |
| 检测到异常行为 | 所有 Token jti 写入黑名单，触发安全告警 | 全设备强制下线 |
| Token 轮换 | 旧 Refresh Token jti 写入黑名单 | 仅旧 Refresh Token 失效 |

- Redis 黑名单 Key：`token:blacklist:{jti}`，TTL = Token 剩余有效期（最大 7 天）
- 域服务认证过滤器：解析 JWT → 检查签名 → 检查过期 → **检查 Redis 黑名单** → 放行
- 黑名单性能：Redis 单 Key 查询 < 1ms；高峰期可引入 Caffeine 本地缓存（TTL 5 分钟）

**单点登出策略**：

| 登出类型 | 触发方式 | 处理逻辑 |
|---------|---------|---------|
| 单端登出 | 用户点击"退出登录" | 仅撤销当前设备 Refresh Token（`device_id` 标识） |
| 全部设备下线 | 安全设置选择"全部设备下线" | 遍历 Redis 中该用户所有活跃 Session，全量加入黑名单 |
| 被动登出 | 密码修改/账号禁用/安全策略触发 | 自动执行"全部设备下线"，通知所有活跃设备 |

**多设备登录并发控制**：

- 最大并发设备数：默认 5 个（web/mobile/h5 各可独立登录）
- 超限处理：最早登录的设备 Refresh Token 自动撤销（踢下线）
- 活跃设备管理：用户可在安全设置查看活跃设备列表，支持手动踢出
- Redis Session 结构：
  - `user:sessions:{user_id}` → Set，包含所有活跃 Session ID
  - `user:session:{session_id}` → Hash，包含 device_type/login_time/last_active/ip/refresh_token_jti
- 管理员可配置：Nacos 中按角色配置 `auth.max.devices.{role} = 5`

**权限模型（RBAC）**：

采用 **RBAC（基于角色的访问控制）**，不使用 ABAC，理由：HR 系统权限边界清晰，RBAC 足以满足。

| 角色 | 权限范围 | 数据行级隔离 |
|------|---------|------------|
| 系统管理员 | 全部功能 | 无限制 |
| 人事专员 | 招聘/入职/培训/考勤/薪资/证明全部操作 | 全公司数据 |
| 部门主管 | 本部门数据查看、绩效审批 | 仅本部门及下级部门 |
| 外务专员 | 工伤/公积金/社保申报操作 | 全公司数据 |
| 普通员工 | 个人信息查看、工资条、证明申请 | 仅自身数据 |

- 权限校验：域服务内置 Spring Security `@PreAuthorize` → MyBatis-Plus 数据权限拦截器附加部门过滤
- 权限变更生效：下次 Token 刷新时加载最新权限（≤30 分钟），紧急变更可强制重新登录

#### 2.2.2 API 版本策略

**采用 URL 路径版本策略**：

- 格式：`/api/v{major}/{resource}`，如 `/api/v1/employees`、`/api/v2/employees`
- 当前系统初始版本为 **v1**
- **版本管理规则**：
  - **向后兼容的变更**（新增查询参数、新增非必填字段、新增接口）：不升级版本号，在同一大版本内发布
  - **破坏性变更**（删除字段、修改字段类型、删除接口、修改语义）：必须升级大版本号（v1 → v2）
  - 旧版本至少保留 **12 个月**，期间 Ingress 同时路由 v1 和 v2 请求
  - 版本废弃需提前 3 个月通知，返回 `Deprecation-Date` 和 `Sunset` 响应头
- **版本号不在请求头中传递**（避免 Content Negotiation 带来的复杂度），仅在 URL 路径中体现，便于 Ingress 路由和日志统计
- 内部微服务间通信使用最新版本，不携带版本号（服务间为私有大版本）

### 2.3 业务服务层 (Service Layer)

**职责**：承载各业务模块的后端 API 服务，负责 HTTP 接口暴露、数据持久化、事务管理和安全控制。

**架构模式**：松耦合的微服务架构，按业务域聚合为 **4 个域服务**（V15 修订：从 V14 的 8 个合并）。

**域服务合并方案**（V15 新增）：

| 域服务 | 合并来源 | 端口 | 包含能力 | 合并理由 |
|--------|---------|------|---------|---------|
| 用户中心域 (user-domain) | user-agent + cert-agent | :8081 | 用户管理、权限管理、组织架构、认证鉴权、证明开具 | 证明开具依赖用户认证和权限校验，同域内可共享用户数据，减少跨服务调用 |
| 招聘培训域 (recruit-domain) | recruit-agent + train-agent | :8082 | 招聘管理、入职办理、培训管理、教材转视频、审核资料 | 招聘和培训共享"人员成长"业务域，入职后培训流程衔接紧密，同域内共享员工档案数据 |
| 薪酬考勤域 (payroll-domain) | comp-agent + perf-agent | :8083 | 薪资核算、考勤管理、绩效管理、外务申报 | 薪资和绩效共享"人员评估与薪酬"业务域，绩效结果直接影响薪资核算，同域内避免跨服务传递绩效数据 |
| 分析自动化域 (auto-domain) | analytics-agent + auto-agent | :8084 | 分析报表、AI 偏见测试、OCR 识别、RPA 自动化 | OCR 和 RPA 是共享基础设施能力，分析与自动化天然关联，统一管理和监控 |

**合并后优势**：
- 跨服务调用从 8 个服务间的 C(8,2)=28 条减少到 4 个服务间的 C(4,2)=6 条
- 每个域服务内部共享数据库 Schema，减少分布式事务复杂度
- 运维成本降低：部署单元从 8 个降至 4 个，监控告警规则减少一半
- 与 SRS 中"适度微服务"原则一致：中规模企业内部系统，4 个域服务是合理粒度

### 2.4 Agent 编排层 (Orchestration Layer)

**职责**：业务流程编排、Agent 调度、状态持久化、断点恢复。

**技术选型**：
- 流程引擎：Camunda 8 (Zeebe) — 原生支持事件驱动和高并发
- 消息队列：Kafka 3 节点集群 — 高吞吐、持久化保障
- 自定义编排 SDK：Java 实现的 Agent 内部推理-行动循环客户端

**Camunda 8 与自定义 SDK 的边界**：
- Camunda 8 负责 **业务流程编排**：定义跨域服务的 BPMN 流程
- 自定义 Agent SDK 负责 **Agent 内部的推理-行动循环**
- 两者协作方式：Camunda 8 流程定义中的 Service Task 节点通过 External Task Worker 模式调用对应域服务

**Camunda 8 与 4 个域服务的 BPMN 映射关系**：

| BPMN 流程文件 | 业务场景 | Service Task 节点 | 调用的域服务 | 端口 |
|-------------|---------|------------------|-------------|------|
| `onboarding-process.bpmn` | 入职办理 | ST-01 创建入职申请 | recruit-domain | :8082 |
| | | ST-02 OCR识别证件 | auto-domain | :8084 |
| | | ST-03 人脸采集建档 | auto-domain | :8084 |
| | | ST-04 创建系统账号 | user-domain | :8081 |
| | | ST-05 生成人事档案 | recruit-domain | :8082 |
| | | ST-06 发送入职通知 | recruit-domain | :8082 |
| `recruitment-process.bpmn` | 招聘管理 | ST-01 发布岗位需求 | recruit-domain | :8082 |
| | | ST-02 简历抓取与解析 | recruit-domain | :8082 |
| | | ST-03 简历匹配评分 | recruit-domain | :8082 |
| | | ST-04 生成面试试卷 | recruit-domain | :8082 |
| | | ST-05 自动阅卷 | recruit-domain | :8082 |
| | | ST-06 人才入库 | recruit-domain | :8082 |
| `training-process.bpmn` | 培训管理 | ST-01 生成培训计划 | recruit-domain | :8082 |
| | | ST-02 签到统计 | recruit-domain | :8082 |
| | | ST-03 组卷与阅卷 | recruit-domain | :8082 |
| | | ST-04 教材转视频 | recruit-domain | :8082 |
| | | ST-05 生成结业证书 | recruit-domain | :8082 |
| | | ST-06 审核资料打包 | recruit-domain | :8082 |
| `payroll-process.bpmn` | 薪资核算 | ST-01 生成数据快照 | payroll-domain | :8083 |
| | | ST-02 拉取考勤数据 | payroll-domain | :8083 |
| | | ST-03 拉取社保公积金 | payroll-domain | :8083 |
| | | ST-04 薪资计算 | payroll-domain | :8083 |
| | | ST-05 异常检测 | payroll-domain | :8083 |
| | | ST-06 工资条发放 | payroll-domain | :8083 |
| `performance-process.bpmn` | 绩效管理 | ST-01 启动考核周期 | payroll-domain | :8083 |
| | | ST-02 自评回收 | payroll-domain | :8083 |
| | | ST-03 上级审批汇总 | payroll-domain | :8083 |
| | | ST-04 绩效分析 | payroll-domain | :8083 |
| `external-process.bpmn` | 外务申报 | ST-01 事件受理 | payroll-domain | :8083 |
| | | ST-02 材料收集校验 | payroll-domain | :8083 |
| | | ST-03 RPA登录政府网站 | auto-domain | :8084 |
| | | ST-04 自动填表提交 | auto-domain | :8084 |
| | | ST-05 跟踪进度 | payroll-domain | :8083 |
| `certificate-process.bpmn` | 证明开具 | ST-01 申请校验 | user-domain | :8081 |
| | | ST-02 数据提取 | user-domain | :8081 |
| | | ST-03 生成PDF证明 | user-domain | :8081 |
| | | ST-04 发放与归档 | user-domain | :8081 |
| `analytics-process.bpmn` | 分析报表 | ST-01 数据采集 | auto-domain | :8084 |
| | | ST-02 统计分析 | auto-domain | :8084 |
| | | ST-03 报告生成 | auto-domain | :8084 |
| | | ST-04 偏见测试 | auto-domain | :8084 |
| `bias-test-monthly.bpmn` | 月度偏见测试 | ST-01 测试数据准备 | auto-domain | :8084 |
| | | ST-02 偏见检测执行 | auto-domain | :8084 |
| | | ST-03 结果评估 | auto-domain | :8084 |
| | | ST-04 报告生成 | auto-domain | :8084 |
| | | ST-05 整改跟踪 | auto-domain | :8084 |

**External Task Worker 调用机制**：
- 每个域服务内置 External Task Worker 客户端，启动时向 Camunda 8 Zeebe 注册其处理的 `taskType`
- Camunda 8 流程到达 Service Task 节点时，将任务发布到对应 `taskType` 的队列
- 域服务端的 Worker 轮询获取任务 → 执行业务逻辑 → 调用 Zeebe Complete API 回传结果
- 任务超时或失败时，Worker 调用 Fail API，Camunda 8 根据 Boundary Event 定义走补偿路径
- 每个 Service Task 配置：`retries=3`，退避间隔 30 秒，超时阈值按业务场景配置（简历筛选 5 分钟、薪资核算 10 分钟、RPA 操作 15 分钟）

**编排模式**：

| 模式 | 应用场景 | 示例 |
|------|---------|------|
| Pipeline 流水线 | 顺序执行端到端流程 | 入职办理流程 |
| Fan-Out/Fan-In | 并行处理后汇聚 | 薪资核算并行拉取数据 |
| Decision Tree | 条件分支 | 简历评分分拣 |
| Feedback Loop | 结果反馈决定是否继续 | 材料校验-补传循环 |

**DAG 引擎技术选型说明**：

架构全景图中"任务分解器(DAG引擎)"即 **Camunda 8 BPMN 并行网关 + External Task Worker 模式的组合能力**，无需引入独立 DAG 引擎组件（如 Apache Airflow/Temporal），理由如下：

- Camunda 8 BPMN 的 **Parallel Gateway** 天然支持 DAG 风格的有向无环图任务分解
- External Task Worker 模式允许不同域服务并行拾取同一并行分支中的不同任务类型
- 4 个域服务的 BPMN 流程已涵盖所有 DAG 场景
- 引入独立 DAG 引擎会增加运维复杂度，与"适度微服务"原则冲突

**Camunda 8 与 Kafka 协作关系**：

| 维度 | Camunda 8 (Zeebe) | Kafka | 边界说明 |
|------|-------------------|-------|---------|
| 流程状态管理 | Zeebe 内部 Raft 共识维护流程实例状态 | 不参与流程状态管理 | Camunda 8 是流程状态的唯一权威源 |
| 任务分发 | Service Task 通过 External Task Worker 分发给域服务 | 不参与任务分发 | 域服务向 Zeebe 轮询获取任务 |
| 事件传递 | 流程到达节点时向 Kafka 发布事件 | 承载域服务间异步通信 | Kafka 是域服务间事件总线的传输层 |
| 流程触发 | 定时触发或外部 API 调用 | Kafka 事件可作为 Camunda 8 Correlate Message 触发源 | Kafka 事件 → Camunda 8 Message Start Event |
| 状态查询 | Operate 提供流程实例查询 UI | 不存储流程状态 | 运维通过 Operate 查看流程进度 |

**协作流程示例（入职流程）**：
```
1. Camunda 8 启动 onboarding-process.bpmn → 到达 ST-01(创建入职申请)
2. recruit-domain Worker 拾取 ST-01 → 执行 → 向 Zeebe 回传 Complete
3. Camunda 8 推进至 ST-02(OCR识别证件) → 同时向 Kafka 发布 hr.onboarding.events 事件
4. auto-domain Worker 拾取 ST-02 → OCR 识别 → Complete
5. 其他域服务通过订阅 Kafka Topic 监听入职事件
```

### 2.4.1 分布式追踪方案

**技术选型**：OpenTelemetry + Jaeger

| 组件 | 选型 | 用途 |
|------|------|------|
| 埋点 SDK | OpenTelemetry Java SDK 1.x | 各域服务自动埋点（HTTP 客户端/服务端、Kafka 生产者/消费者） |
| 数据收集 | OpenTelemetry Collector | 各域服务 Pod 同部署 Sidecar，收集 trace/span 数据并导出至 Jaeger |
| 存储与查询 | Jaeger (all-in-one) | 存储追踪数据，提供 UI 可视化调用链 |

**trace-id 传递机制**：

| 传递场景 | 传递方式 | 实现 |
|---------|---------|------|
| 前端 → Ingress | HTTP Header `X-Trace-Id` | Ingress 透传 |
| Ingress → 域服务 | HTTP Header `X-Trace-Id` + W3C `traceparent` | 域服务 OpenTelemetry 自动提取 |
| 域服务 → 域服务 (HTTP) | HTTP Header `X-Trace-Id` | OpenTelemetry HTTP 客户端拦截器自动附加 |
| 域服务 → Kafka → 域服务 | Kafka 消息头 `traceparent` | OpenTelemetry Kafka 拦截器自动序列化/反序列化 |
| 域服务 → AI 模型网关 | HTTP Header `X-Trace-Id` | 同上 |

**OpenTelemetry 自动埋点配置**：
```yaml
otel:
  service.name: ${spring.application.name}
  resource.attributes:
    deployment.environment: ${SPRING_PROFILES_ACTIVE}
  exporter:
    otlp:
      endpoint: http://otel-collector:4317
```

**关键 Span 命名规范**：
- HTTP 请求：`HTTP GET /api/v1/employees`
- Kafka 发送/消费：`Kafka hr.payroll.events SEND` / `RECEIVE`
- 域服务业务操作：`recruit-domain.resume.score` / `payroll-domain.payroll.calculate`
- AI 模型调用：`ai-model.embedding` / `ai-model.ocr`

**Jaeger 可视化**：通过 flow_id 查询完整业务流程调用链，支持按服务/操作/状态过滤，慢调用告警。

### 2.5 AI 模型服务层 (AI Model Layer)

**职责**：提供 AI 推理能力，屏蔽模型细节，统一接口。

**服务清单**：

| 服务 | 技术选型 | 部署方式 |
|------|---------|---------|
| LLM 推理 | vLLM + Qwen/DeepSeek 等 | 本地 GPU 服务器或云端 API |
| OCR 识别 | PaddleOCR | 本地部署 |
| 人脸识别 | **InsightFace** (V15 修订) | 本地部署（数据不出境、隐私优先） |
| Embedding | bge-m3 或 text-embedding-3 | 本地 CPU 可运行 |
| ASR 语音 | Whisper (本地化) | 本地部署 |
| 多模态 | Qwen-VL 或 GPT-4V API | 云端 API |
| TTS 语音 | Edge-TTS | 本地部署 |

**V15 人脸服务修订说明**：

原 V14 采用 Face++（云端 API），与用户"偏好本地部署，不信任云端方案"的偏好冲突。V15 修订为：

| 维度 | Face++ (V14) | InsightFace (V15) | 修订理由 |
|------|-------------|-------------------|---------|
| 部署方式 | 云端 API | 本地部署 | 符合用户本地部署偏好 |
| 数据出境 | 人脸数据上传至云端 | 人脸数据完全本地处理 | PIPL 合规要求 |
| 功能覆盖 | 人脸检测/识别/比对/属性分析 | 人脸检测/识别/比对/属性分析 | 功能对等 |
| 性能 | 依赖网络延迟 | 本地 GPU/CPU 推理，无网络延迟 | 更稳定 |
| 成本 | 按次计费 | 一次性 GPU 投入 | 长期使用更经济 |
| 开源许可 | 商业授权 | MIT 开源 | 无许可证费用 |

**InsightFace 部署方案**：
- 框架：InsightFace PyTorch 版本（arcface 预训练模型）
- 硬件要求：单 GPU（NVIDIA T4 或更高），显存 ≥ 8GB
- 接口封装：Python FastAPI 服务，通过 AI 模型网关统一调用
- 推理精度：MS1MV3 预训练模型，LFW 准确率 99.82%
- 降级方案：GPU 不可用时切换 CPU 推理（速度降低约 5 倍但仍可用）

**Embedding 与 Milvus 关联架构**：

| 角色 | 组件 | 职责 | 数据流方向 |
|------|------|------|-----------|
| 向量生产者 | bge-m3 Embedding 服务 | 接收文本输入，生成固定维度向量（如 1024 维） | 接收域服务调用的文本 → 输出向量 |
| 向量存储与检索 | Milvus 向量数据库 | 存储向量索引，支持相似度检索（ANN） | 接收 bge-m3 写入的向量 → 返回最近邻查询结果 |
| 调用方 | 各域服务（recruit-domain 等） | 发起 Embedding 请求或向量检索请求 | 调用 AI 模型网关 → 路由至 bge-m3 或 Milvus |

**数据流示例（简历语义检索）**：
```
recruit-domain → AI模型网关 → bge-m3(生成查询向量) → AI模型网关 → Milvus(ANN检索) → 返回TOP-K相似简历向量ID → Milvus → 回传recruit-domain
```

**Milvus 配置**：
- 索引类型：HNSW（平衡检索速度与精度）
- 距离度量：COSINE（余弦相似度）
- 分区策略：按业务域分区（`resume_collection`、`document_collection`）
- 保留策略：简历向量 3 年，文档向量永久保留

**模型治理**：
- 每个模型服务封装为独立微服务
- 统一 gRPC/HTTP 接口，域服务无需感知底层模型差异
- 模型版本管理：每次更新带版本号，旧版本保留 30 天
- A/B 测试：新模型 5% 流量灰度，指标达标后全量

#### 2.5.1 AI 模型网关与成本监控方案

**AI 模型网关** 统一管理和路由所有模型调用请求，位于域服务群与模型服务层之间：

```
域服务 → AI模型网关 → [vLLM / PaddleOCR / InsightFace / bge-m3 / Whisper / ...]
```

**网关功能**：
- 统一路由：域服务调用 `/ai/v1/embedding`、`/ai/v1/ocr` 等统一接口
- 负载均衡：同模型多实例间轮询/加权分发
- 降级切换：本地模型不可用 → 自动切换云端 API（配置化）
- 请求/响应缓存：相同输入结果缓存（TTL 1 小时，适用于 Embedding/OCR）

**成本监控方案**：

| 监控维度 | 指标 | 实现方式 | 告警阈值 |
|---------|------|---------|---------|
| 月费用预警 | 累计 API 调用费用（按 Token/按次计费） | 网关拦截器记录每次调用的 model_id、token_count、cost → 写入 `ai_cost_log` 表 → Prometheus 聚合 | 月度预算 80% 触发黄色预警，95% 触发红色告警 |
| 部门分摊 | 各部门域服务调用产生的费用归属 | JWT 中的 `tenant_id`/`dept_id` 透传至 AI 网关 → 按部门维度聚合统计 | 单部门费用超过分配预算时冻结该部门非关键域服务调用 |
| ROI 追踪 | 域服务自动化节省的人工时数 vs AI 调用成本 | 每月对比：(域服务处理任务数 × 人工处理基准时长 × 人力单价) - AI 调用总费用 → 输出 ROI 报表 | ROI 低于 1.5 时标记待优化域服务 |

**费用统计实现细节**：
- 每次 AI 调用完成后，网关拦截器异步写入 `ai_cost_log` 记录：`{model_id, provider, token_count, cost_usd, dept_id, agent_id, timestamp, trace_id}`
- 每日定时任务（CronJob）聚合当日费用，更新 `ai_cost_daily_summary` 表
- Grafana 仪表盘展示：实时费用、部门排名、模型消耗 TOP10、趋势预测
- 预算配置：管理员在 Nacos 中配置各部门月度预算（`ai.budget.dept.{dept_id} = 5000`）

### 2.6 数据基础设施层 (Data Infrastructure Layer)

| 组件 | 用途 | 规格 |
|------|------|------|
| MySQL 8.x | 结构化数据存储 | 主从复制，InnoDB 引擎 |
| Redis 7.x | 会话、缓存、分布式锁 | **3 节点 Cluster 模式**（V15 修订） |
| Kafka 3.x | 消息队列、事件总线 | 3 节点集群，replication-factor=3 |
| MinIO | 对象存储（文件、影像、视频） | 4 节点纠删码集群（EC:2），初始 1TB，可弹性扩展 |
| Elasticsearch 8.x | 简历搜索、日志检索 | 3 节点集群 |
| Milvus | 向量数据库（简历向量化检索） | 本地部署 |

**MinIO 集群拓扑与纠删码配置**：

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 节点数量 | 4 节点 | 每个节点独立磁盘，组成单一 MinIO 集群 |
| 纠删码模式 | EC:2（Erasure Coding 2 parity） | 4 个数据块 + 2 个校验块共需 6 磁盘/节点时适用；4 节点模式下每节点至少 2 块盘，可容忍任意 2 块磁盘或 1 个节点完全故障 |
| 实际部署建议 | 每节点 2 块盘，共 8 盘 | 纠删码组大小为 8（6 数据 + 2 校验），可容忍任意 2 块磁盘同时故障 |
| 容量计算 | 8 盘中 6 盘存储数据，2 盘冗余 | 有效容量 = 总容量 × 6/8 = 75% |
| 扩展方式 | 使用 MinIO 分布式扩容命令在线添加节点 | 支持从 4 节点扩展至 8/16 节点，数据自动重新平衡 |

**MinIO 对象存储职责**：

| 存储类别 | 用途 | 存储路径前缀 | 保留策略 |
|---------|------|------------|---------|
| 培训视频 | 教材转视频域服务生成的 MP4 视频课程 | `/training/videos/` | 永久保留 |
| OCR 原始图片 | 证件扫描件、合同扫描件等 OCR 输入原图 | `/ocr/originals/` | 保留 15 年（合规要求） |
| 入职材料归档 | 新员工入职上传的证件照、学历证书等 | `/onboarding/{employee_id}/` | 保留 15 年（合规要求） |
| 离职材料归档 | 离职交接单、离职证明等 | `/offboarding/{employee_id}/` | 保留 15 年（合规要求） |
| 备份存储 | 数据库全量/增量备份文件的存储目的地 | `/backups/mysql/`、`/backups/minio/` | 按备份策略保留 |
| 电子协议存证 | 签署后的电子协议 PDF 文件 | `/contracts/` | 永久保留 |

#### 2.6.1 数据库设计细节

**连接池配置策略**：
- 使用 HikariCP 连接池
- 初始连接数：10，最大连接数：50（按 CPU 核数 × 2 + 有效磁盘数 公式计算，4 核服务器 = 50）
- 连接超时：30s，空闲超时：10 分钟，最大生命周期：30 分钟
- 各域服务独立连接池，不共享，避免单域服务连接耗尽影响全局

**读写分离实现**：
- 主库：处理所有写操作 + 强一致性读（如薪资核算、权限校验）
- 从库：处理查询类读操作（如简历搜索、报表统计、列表页）
- 实现方式：MyBatis-Plus 动态数据源路由，通过 `@DS("master")` / `@DS("slave")` 注解指定
- 默认读操作走从库，写操作强制走主库
- 从库延迟监控：Prometheus 采集 `seconds_behind_master`，延迟 > 30s 时自动切换至主库读

**分库分表策略**：
- **初期不分库分表**：单表预估 < 1000 万行，MySQL 单表性能充足
- **扩展触发条件**：单表 > 2000 万行 或 QPS > 5000 时触发拆分评估
- **拆分方案**：
  - 水平分表：按 `employee_id` 哈希分片（如 `employee_0` ~ `employee_15`）
  - 分库：按 `dept_id` 范围分库（如 A-F 部门库 1，G-M 部门库 2）
  - 中间件：ShardingSphere-Proxy 5.x（透明代理模式，无需修改应用代码）
- **历史数据归档**：3 年以上薪资记录自动归档至 `payroll_archive` 库，不影响线上查询性能

**索引设计规范**：
- 主键：自增 BIGINT（非 UUID，减少页分裂）
- 唯一索引：业务唯一键（如 `employee_no`、`id_card_no`）
- 查询索引：覆盖高频查询 WHERE/ORDER BY 字段组合，优先联合索引
- 索引数量控制：单表索引 ≤ 8 个，避免写入性能下降
- 定期分析：`EXPLAIN` 审查慢查询（> 1s），每季度清理未使用索引（通过 `sys.schema_unused_indexes` 视图）

---

## 3. 模块划分与职责

### 3.1 招聘管理模块 (recruit-domain :8082)

**包含 Agent**：招聘渠道 Agent、简历匹配 Agent、组卷 Agent、阅卷 Agent

**核心流程**：
1. 岗位需求录入 → 招聘渠道 Agent 自动发布至各招聘平台
2. 简历抓取 → 简历匹配 Agent 评分分拣
3. 面试安排 → 组卷 Agent 出题 → 阅卷 Agent 评分

**关键接口**：
- `POST /api/v1/recruit/jobs` — 创建岗位需求
- `POST /api/v1/recruit/resumes/batch` — 简历批量导入
- `GET /api/v1/recruit/resumes/{id}/score` — 获取简历匹配分
- `POST /api/v1/recruit/exam/generate` — 生成面试试卷
- `POST /api/v1/recruit/exam/grade` — 自动阅卷

### 3.2 入职管理模块 (recruit-domain :8082 含入职子模块)

**包含 Agent**：入职引导 Agent、OCR Agent（调用 auto-domain）、人脸 Agent（调用 AI 模型层 InsightFace）

**核心流程**：
1. 新员工扫码 → 入职引导 Agent 引导材料上传
2. auto-domain 的 OCR 能力识别证件 → 结构化信息提取
3. AI 模型层 InsightFace 人脸采集 → 比对建档

**关键接口**：
- `POST /api/v1/onboarding/qrcode` — 生成入职扫码链接
- `POST /api/v1/onboarding/upload` — 上传入职材料
- `POST /api/v1/onboarding/ocr` — 证件 OCR 识别（透调 auto-domain）
- `POST /api/v1/onboarding/face/enroll` — 人脸采集建档（透调 AI 模型层）

### 3.3 培训管理模块 (recruit-domain :8082 含培训子模块)

**包含 Agent**：培训 Agent、教材转视频 Agent、审核资料 Agent

**核心流程**：
1. 培训计划自动生成 → 签到二维码生成
2. 扫码签到 → 自动统计
3. 结业考试 → 自动阅卷 → 证书生成

**关键接口**：
- `POST /api/v1/training/plans` — 创建培训计划
- `POST /api/v1/training/signin/qrcode` — 生成签到码
- `POST /api/v1/training/exam` — 考试管理
- `POST /api/v1/training/video/generate` — 教材转视频
- `POST /api/v1/training/audit/package` — 审核资料打包

### 3.4 薪资与考勤模块 (payroll-domain :8083)

**包含 Agent**：考勤 Agent、薪资 Agent、工资条 Agent

**核心流程**：
1. 考勤：定时拉取打卡数据 → 与排班表对照 → 异常识别 → 汇总报表
2. 薪资：月末定时触发 → **数据快照**（`payroll_snapshot_{year_month}_{snapshot_id}`）→ 并行拉取 → 核算 → 审核 → 发放

**关键接口**：
- `GET /api/v1/attendance/summary` — 考勤汇总
- `POST /api/v1/payroll/calculate` — 触发薪资核算
- `GET /api/v1/payroll/snapshot/{id}` — 获取薪资快照
- `POST /api/v1/payroll/distribute` — 工资条发放

### 3.5 绩效与外务模块 (payroll-domain :8083)

**包含 Agent**：绩效 Agent、外务 Agent（RPA 能力通过调用 auto-domain 的 OCR/RPA 共享服务获取）

**核心流程**：
1. 绩效：考核期初提醒 → 自评回收 → 上级审批 → 汇总分析
2. 外务：事件触发 → payroll-domain 调用 auto-domain 的 RPA 能力登录政府网站 → 自动填表提交 → 跟踪进度

**关键接口**：
- `POST /api/v1/performance/cycle/start` — 启动考核周期
- `GET /api/v1/performance/summary` — 绩效汇总
- `POST /api/v1/external/report` — 外务申报
- `GET /api/v1/external/rpa/status` — RPA 执行状态（透调 auto-domain）

**RPA 安全护栏**（由 auto-domain 执行，payroll-domain 调用）：
- 容器网络隔离：仅允许访问 `*.gov.cn`/`*.gov.tw` 白名单
- 沙箱机制：只读根文件系统，tmpfs 临时文件
- 资源限制：CPU ≤ 2 核、内存 ≤ 4GB
- 外网代理：Squid 代理转发，完整日志记录

### 3.6 证明开具模块 (user-domain :8081)

**包含 Agent**：证明 Agent（V15 修订：从原 cert-agent 合并至 user-domain）

**核心流程**：员工申请 → user-domain 内置证明 Agent 自动校验数据 → 生成 PDF 证明 → 发放

**关键接口**：
- `POST /api/v1/certificate/apply` — 申请证明
- `GET /api/v1/certificate/{id}/download` — 下载证明
- `GET /api/v1/certificate/types` — 证明类型列表

**合并理由**：证明开具需要用户身份认证和数据权限校验，与用户中心域天然关联。合并后证明 Agent 可直接访问用户数据，无需跨服务调用。

### 3.7 共享基础设施服务 (auto-domain :8084 含 OCR/RPA 子模块)

**V15 修订：auto-domain 定位为"共享基础设施服务"，非独立业务 Agent。**

**包含能力**：OCR 识别服务、RPA 自动化服务

**职责**：为其他域服务提供 OCR 识别和 RPA 自动化能力。auto-domain 本身不拥有独立业务领域，而是作为跨域共享工具被调用。

**架构定位说明**：
- auto-domain 在架构全景图中位于"共享基础设施服务层"，独立于 4 个业务域服务
- 被用户中心域、招聘培训域、薪酬考勤域调用
- 不直接面向终端用户暴露业务 API，仅通过域服务间接调用
- Camunda 8 BPMN 流程中，OCR/RPA 相关的 Service Task 节点统一调用 auto-domain

**关键接口**（内部接口，仅域服务可调用）：
- `POST /api/v1/auto/ocr` — OCR 识别
- `POST /api/v1/auto/rpa/task` — 提交 RPA 任务
- `GET /api/v1/auto/rpa/{task_id}/status` — RPA 任务状态

### 3.8 分析与自动化模块 (auto-domain :8084)

**包含 Agent**：分析 Agent、OCR Agent、RPA Agent

**核心流程**：跨域服务数据采集 → 统计分析 → 洞察报告生成 → AI 偏见测试

**关键接口**：
- `POST /api/v1/analytics/report/generate` — 生成分析报告
- `GET /api/v1/analytics/dashboard` — 数据仪表盘
- `POST /api/v1/analytics/bias-test` — AI 偏见测试触发

**AI 偏见测试与 Camunda 8 集成**：

分析 Agent 内置偏见检测模块，与 Camunda 8 流程引擎集成方式如下：

1. **定时触发**：Camunda 8 定义月度偏见测试流程（BPMN `bias-test-monthly.bpmn`），每月 1 号凌晨定时启动
2. **测试数据准备**：流程节点 1 — 从员工数据中按性别/年龄/部门/学历等维度分层抽样，生成测试数据集（确保各维度分布均匀）
3. **偏见检测执行**：流程节点 2 — 调用 auto-domain 的 `/analytics/bias-test` 接口，分析 Agent 执行：
   - 简历筛选偏见检测：对比同条件不同性别/年龄候选人的评分差异
   - 薪资核算偏见检测：对比同岗位同绩效的薪资差异
   - 培训推荐偏见检测：对比不同部门的培训资源分配均衡性
4. **结果评估**：流程节点 3 — 设定阈值（如评分差异 > 5% 标记为潜在偏见），Camunda 8 根据返回值走不同分支
5. **报告生成**：流程节点 4 — 生成偏见测试报告，包含检测维度、差异数据、风险等级
6. **人工审核分支**：若检测到高风险偏见，流程自动进入人工审核节点（Boundary Event），通知 HR 主管；低风险则自动归档
7. **整改跟踪**：流程节点 5 — 对确认的偏见问题，Camunda 8 创建整改子流程，跟踪至解决

偏见测试结果存储于 `analytics_bias_test` 表，字段包括：`test_id`、`test_date`、`dimension`（性别/年龄/部门/学历）、`metric`（评分差异/薪资差异）、`value`、`threshold`、`risk_level`、`status`、`remediation_deadline`。

### 3.9 用户与权限模块 (user-domain :8081)

**包含 Agent**：用户管理 Agent、权限管理 Agent、组织架构 Agent、证明 Agent

**核心流程**：用户注册/创建 → 角色分配 → 权限配置 → 认证鉴权 → 证明开具

**关键接口**：
- `POST /api/v1/auth/login` — 登录
- `POST /api/v1/auth/refresh` — Token 刷新
- `POST /api/v1/auth/logout` — 注销
- `POST /api/v1/users` — 创建用户
- `GET /api/v1/users/{id}/permissions` — 获取用户权限
- `POST /api/v1/org/departments` — 组织架构管理

---

## 4. 技术栈选型

### 4.1 后端技术栈

| 层次 | 选型 | 理由 |
|------|------|------|
| 语言 | Java 17 | 企业级稳定性、Agent 编排生态成熟 |
| 框架 | Spring Boot 3.x + Spring Cloud | 微服务生态完整、与 Camunda 8 集成良好 |
| ORM | MyBatis-Plus | 灵活 SQL 控制、适合复杂查询 |
| API | RESTful + OpenAPI 3.0 | 标准化接口、自动生成文档 |
| 消息队列 | Kafka 3.x | 高吞吐、持久化、原生支持分区并行 |
| 流程引擎 | Camunda 8 (Zeebe) | 原生支持事件驱动和高并发 |
| 认证 | Spring Security + JWT | 成熟安全框架 |
| 配置中心 | Nacos | 集中管理应用配置，支持热更新 |
| AI 集成 | 自定义 Agent SDK | 统一模型调用接口、版本管理 |
| RPA | Playwright Python (HTTP API 调用) | 社区支持成熟，运维友好 |
| 日志 | SLF4J + Logback + ELK | 结构化日志、集中检索 |
| 熔断降级 | Resilience4j | 轻量级、Spring Boot 原生集成、功能完整（熔断器/重试/限流/舱壁隔离） |

### 4.2 前端技术栈

| 层次 | 选型 | 理由 |
|------|------|------|
| 框架 | Vue 3 + TypeScript | 响应式、类型安全、组件化 |
| UI 库 | Element Plus | 企业级组件库、内置表格/表单 |
| 状态管理 | Pinia | Vue 3 官方推荐、轻量 |
| 路由 | Vue Router 4 | Vue 官方路由方案 |
| HTTP | Axios | 拦截器、超时控制 |
| 国际化 | vue-i18n 9.x | 中/英双语切换、路由级 i18n |
| 移动端 | UniApp | 一套代码发布 iOS/Android/H5 |
| 构建 | Vite | 快速热更新、生产构建优化 |
| 无障碍 | axe-core + Vue-Axe | WCAG 2.1 AA 检测 |
| 代码规范 | ESLint + Prettier | 统一代码风格、CI 拦截不合格提交 |

**前端代码规范统一配置**：

- ESLint 配置：`@vue/eslint-config-typescript` + `plugin:prettier/recommended`，项目根目录 `eslint.config.js` 统一配置，所有前端模块（Web、Mobile、H5）共享同一份配置
- Prettier 配置：`prettier.config.js`，`printWidth=100`、`semi=true`、`singleQuote=true`、`trailingComma='es5'`
- 格式化钩子：`lint-staged` + `husky` pre-commit 钩子，提交前自动执行 `eslint --fix` + `prettier --write`
- CI 拦截：GitHub Actions 构建流水线中运行 `npm run lint`，发现错误则阻断合并
- 编辑器集成：`.vscode/settings.json` 配置 `editor.formatOnSave=true`、`editor.defaultFormatter=esbenp.prettier-vscode`

### 4.3 AI 技术栈

| 能力 | 选型 | 部署 |
|------|------|------|
| LLM | Qwen / DeepSeek / GPT-4 | 云端 API 或本地 vLLM |
| OCR | PaddleOCR | 本地部署 |
| 人脸 | **InsightFace** (V15 修订) | 本地部署（数据不出境） |
| Embedding | bge-m3 | 本地 CPU 可运行 |
| ASR | Whisper | 本地部署 |
| 向量检索 | Milvus | 本地部署 |
| RPA | Playwright Python | 无头浏览器集群 |
| TTS | Edge-TTS | 本地部署 |

### 4.4 基础设施

| 组件 | 选型 | 用途 |
|------|------|------|
| 容器化 | Docker + K8s (生产) | 部署与编排 |
| CI/CD | GitHub Actions | 自动化构建、测试、部署 |
| 监控 | Prometheus + Grafana | 指标采集与可视化 |
| 链路追踪 | OpenTelemetry + Jaeger | 全链路追踪 |
| 日志 | ELK | 集中日志管理 |
| 对象存储 | MinIO | 文件存储 |
| 密钥管理 | HashiCorp Vault | API 密钥、凭证安全管理 |
| 数据库迁移 | Flyway | Schema 版本管理 |

---

## 5. 部署架构

### 5.1 开发环境

- 本地 Docker Compose 一键启动
- 包含：MySQL、Redis、Kafka、MinIO、ES、Milvus
- 前端开发服务器（Vite dev server）
- 后端 Spring Boot 开发模式（热重载）

### 5.2 测试环境

- 独立 K8s 命名空间（`hr-test`）
- 完整的生产镜像部署
- 自动化测试流水线（GitHub Actions）
- 自动化测试覆盖：单元测试 → 集成测试 → E2E 测试

### 5.3 生产环境

```
┌─────────────────────────────────────────────────────┐
│                  Kubernetes 集群                      │
│                                                      │
│  ┌──────────── Ingress Controller ───────────────┐  │
│  │         Nginx Ingress (单层网关)                │  │
│  └────────────────────┬──────────────────────────┘  │
│                       │                             │
│  ┌────────────────────▼───────────────────────────┐ │
│  │          AI Agent 域服务 Pods (各 2+ 副本)       │ │
│  │                                                │ │
│  │  ┌──────────┐ ┌──────────┐                    │ │
│  │  │user-domain│ │recruit-do│                    │ │
│  │  │  :8081   │ │main:8082 │                    │ │
│  │  │ (2 pods) │ │ (2 pods) │                    │ │
│  │  └──────────┘ └──────────┘                    │ │
│  │  ┌──────────┐ ┌──────────┐                    │ │
│  │  │payroll-do│ │auto-domai│                    │ │
│  │  │main:8083 │ │n :8084  │                    │ │
│  │  │ (2 pods) │ │ (2 pods) │                    │ │
│  │  └──────────┘ └──────────┘                    │ │
│  └────────────────────┬───────────────────────────┘ │
│                       │                             │
│  ┌────────────────────▼───────────────────────────┐ │
│  │          数据层 (StatefulSet)                    │ │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │ │
│  │  │MySQL │ │Redis │ │Kafka │ │MinIO │ │  ES  │ │ │
│  │  │主从  │ │集群  │ │集群  │ │集群  │ │集群  │ │ │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ │ │
│  │  ┌──────┐ ┌──────┐                            │ │
│  │  │Milvus│ │Camunda│                           │ │
│  │  └──────┘ │  8   │                            │ │
│  │           └──────┘                            │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 5.4 部署模式

| 模式 | 适用场景 | AI 推理位置 |
|------|---------|------------|
| 公有云 SaaS | 中小型企业 | 云端 GPU API |
| 私有云 | 大型企业、数据主权要求高 | 本地 GPU 服务器 |
| Hybrid | 敏感数据本地、推理云端 | 混合部署 |

### 5.5 高可用设计

- 域服务：每个域服务至少 2 个副本，支持独立自动扩容（HPA）
- MySQL：主从复制，自动故障切换（15 分钟内）
- Redis：**3 节点 Cluster 模式**（V15 修订：从 V14 的 5 节点哨兵简化）
- Kafka：3 节点集群，replication-factor=3，acks=all，min.insync.replicas=2
- Camunda 8 (Zeebe)：3 节点集群，raft 共识保证流程状态一致性

**V15 Redis 部署修订说明**：

原 V14 采用 5 节点哨兵模式（1主2从2哨兵），后荣指出对 HR 内部系统缓存/会话场景而言运维复杂度与收益不成比例。V15 修订为：

| 维度 | 哨兵模式 (V14) | Cluster 模式 (V15) | 修订理由 |
|------|---------------|-------------------|---------|
| 节点数 | 5 个（1主2从2哨兵） | 3 个（每个节点既是数据节点又参与故障检测） | 3 节点 Cluster 已提供数据冗余和自动故障转移 |
| 数据分片 | 主节点承载全部数据 | 3 节点分 16,384 个 hash slot | 天然支持横向扩展，数据自动分片 |
| 故障转移 | 哨兵投票决定 | Cluster 节点自行协商 | 无需额外哨兵进程，运维更简单 |
| 客户端支持 | 需哨兵发现协议 | 原生 Cluster 协议 | Spring Boot `spring-boot-starter-data-redis` 直接支持 |
| 性能 | 主节点单点写瓶颈 | 写入分散到 3 个节点 | 缓存写入性能提升 |
| 适用场景 | 需要严格主从架构的场景 | 缓存/会话/分布式锁等通用场景 | HR 系统缓存场景 Cluster 完全满足 |

**Redis Cluster 配置**：

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 节点数 | 3 节点 | 每节点 1 个 master，无额外 slave（3 master 已覆盖 16,384 hash slot） |
| 内存配置 | 每节点 4GB | 500 用户 Session + 缓存数据，4GB/节点绰绰有余 |
| 持久化 | AOF `appendfsync=everysec` | 每秒 fsync，平衡性能与安全性 |
| 最大内存策略 | `allkeys-lru` | 内存满时淘汰 LRU 键，保护业务缓存 |
| 客户端配置 | `spring.redis.cluster.nodes` = 3 节点地址 | Spring Boot 自动发现 hash slot 分布 |

**Camunda 8 部署模式说明**：

本系统采用 **Self-managed 自部署模式**（非 Camunda Cloud），理由如下：

| 维度 | Self-managed | Camunda Cloud | 选型依据 |
|------|-------------|---------------|---------|
| 数据主权 | 数据完全本地控制 | 数据存储于 Camunda 云平台 | 员工敏感数据不出境，PIPL 合规要求 |
| 成本 | 一次性基础设施投入 | 按流程实例/月付费，长期成本高 | 预计月流程实例 10 万+，Self-managed 更经济 |
| 自定义扩展 | 完全自由 | 受云平台限制 | 需深度集成 Kafka 事件总线与自定义 Agent SDK |
| 运维复杂度 | 需自行运维 Zeebe + PostgreSQL | 运维由 Camunda 承担 | 团队已有 K8s 运维能力，可接受 |

**Camunda 8 与 Temporal 方案对比**（V15 新增，回应后荣建议）：

| 维度 | Camunda 8 | Temporal | 选型依据 |
|------|----------|----------|---------|
| 流程可视化 | BPMN 标准，Operate UI 提供完整流程图和实例追踪 | 代码定义工作流，无标准流程图 | HR 流程（入职、考勤审批、绩效评估等）利益相关者包括非技术人员，BPMN 便于业务人员理解和协作 |
| 人工审批节点 | 原生支持 User Task + Tasklist UI | 需自行实现审批 UI | HR 系统大量人工审批场景（绩效审批、PIA 审批、薪资审核），Camunda 8 Tasklist 开箱即用 |
| 生态系统 | 成熟的 BPMN 工具链（Camunda Modeler 等） | 开发者友好的 SDK | 团队对 BPMN 更熟悉，降低学习成本 |
| 运维复杂度 | Zeebe + Operate + Tasklist + PostgreSQL | Temporal Server + Cassandra/PostgreSQL | 两者运维复杂度相当，Camunda 8 因 BPMN 优势被选中 |
| 结论 | **选用 Camunda 8** | 适用于纯代码驱动的工作流场景 | HR 场景的 BPMN 可视化价值 > Temporal 的代码优先优势 |

**Self-managed 部署架构**（V15 修订：简化组件）：
- **Zeebe 集群**：3 节点，部署于 K8s StatefulSet，raft 共识协议保证流程状态一致性
- **状态存储**：PostgreSQL 15（独立于业务 MySQL），存储 Zeebe 流程定义、变量快照、流程实例元数据
- **操作日志存储**：Elasticsearch 8.x（与简历搜索 ES 共用集群，通过独立 Index 隔离），存储 Zeebe 的导出记录，用于流程实例查询和历史回溯
- **Camunda 8 Operate**：1 个 Pod，提供流程实例监控、查询 UI（面向运维和 HR 管理员）
- **Camunda 8 Tasklist**：1 个 Pod，提供人工审批任务的 UI（如绩效审批、PIA 审批等）
- **V15 移除**：Camunda 8 Optimize（流程性能分析）不在初始部署范围内，按需启用

**Kafka 集群完整配置**：

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `replication.factor` | 3 | 每个分区 3 个副本，3 节点全冗余 |
| `acks` | all | 生产者发送需等待所有 ISR 副本确认，确保消息不丢失 |
| `min.insync.replicas` | 2 | ISR 中至少 2 个副本存活才允许写入，1 个副本故障仍可写入 |
| `unclean.leader.election.enable` | false | 禁止非 ISR 副本成为 leader，防止数据丢失 |
| `retention.ms` | 按 Topic 配置 | 默认 7 天，关键业务 Topic（如薪资）90 天 |
| `cleanup.policy` | delete | 到期自动清理 |
| `max.message.bytes` | 1048576 (1MB) | 单条消息最大 1MB，防止大消息阻塞 |

### 5.6 灾备设计

- **RPO 目标**：≤ 5 分钟（基于 MySQL binlog 实时同步）
- **RTO 目标**：≤ 2 小时（应用层无状态，重启即可恢复）
- **异地灾备**：生产数据中心 + 异地灾备中心，MySQL 主从异步复制
- **数据备份策略**：
  - 全量备份：每周日凌晨 2:00，保留 ≥ 15 年（薪资、工伤、电子协议）
  - 增量备份：每日凌晨 3:00，保留 ≥ 1 年
  - 备份存储：MinIO 对象存储 + 离线磁带库（每月归档）
  - 备份验证：每月随机恢复 1 个备份集校验

---

## 6. 关键设计决策

### 6.1 微服务拆分粒度（V15 修订）

**决策**：按业务域聚合为 **4 个域服务**（从 V14 的 8 个合并）。

**合并方案对比分析**：

| 方案 | 服务数量 | 预估 QPS/服务 | 运维复杂度 | 跨服务调用数 | 适用场景 |
|------|---------|-------------|-----------|------------|---------|
| 单体 | 1 | 1,000 | 最低 | 0 | < 100 用户的小型系统 |
| 4 域服务 (V15) | 4 | 250 | 中等 | 6 | **500 用户的中型 HR 系统（本方案）** |
| 8 微服务 (V14) | 8 | 125 | 高 | 28 | 1000+ 用户、多团队并行开发的大型系统 |

**选择 4 域服务的理由**：

1. **规模匹配**：SRS 定义的系统目标为"提升 HR 和行政团队的工作效率"，属于中规模企业内部系统，预估并发用户 500 人，峰值 QPS 1,000。4 个域服务完全能够承载此负载。
2. **运维成本**：每个独立服务需要独立的部署、监控、日志、告警、扩缩容配置。8 个服务的运维工作量是 4 个服务的 2 倍，但本系统的团队规模和业务复杂度不足以支撑 8 个服务的运维投入。
3. **跨服务调用**：8 个服务间最多 C(8,2)=28 条调用链路，4 个域服务间仅 C(4,2)=6 条，大幅降低了分布式事务和数据一致性的复杂度。
4. **业务域内聚合**：同一业务域内的 Agent 共享数据库 Schema（如 user-domain 内用户管理和证明开具共享用户表），合并后避免了域内的跨服务调用。
5. **扩展路径**：若未来用户规模增长至 2,000+ 或业务复杂度显著提升，4 个域服务可按需拆分为更细粒度的微服务。当前保留扩展弹性优于过度拆分。

### 6.2 Kafka 替代 RabbitMQ

**决策**：事件总线选用 Kafka 而非 RabbitMQ。

**理由**：
- HR 事件数据量大（简历流入、考勤打卡高频），Kafka 吞吐（万级/s）优于 RabbitMQ
- Kafka 支持事件回溯（retention=7d），便于流程重放和审计
- replication-factor=3 + acks=all + min.insync.replicas=2 保障关键业务事件真正不丢失
- RabbitMQ 适合低延迟场景，但 HR 场景对延迟不敏感（秒级可接受）

### 6.3 端口分配与内部端口规划（V15 修订）

**决策**：4 个域服务使用连续端口 8081~8084，auto-domain 共享基础设施服务使用 8085。

| 服务 | HTTP 服务端口 | Actuator 管理端点 | Metrics 指标端点 | 说明 |
|------|-------------|-------------------|-----------------|------|
| user-domain | 8081 | 9081 | 10081 | 用户中心域 |
| recruit-domain | 8082 | 9082 | 10082 | 招聘培训域 |
| payroll-domain | 8083 | 9083 | 10083 | 薪酬考勤域 |
| auto-domain | 8084 | 9084 | 10084 | 分析自动化域 |
| auto-domain/OCR-RPA | 8085 | 9085 | 10085 | OCR+RPA 共享服务（auto-domain 内部子模块） |

**内部端口分配规则**：
- **HTTP 服务端口**：8081~8085，对外暴露的业务 API 端口
- **Actuator 管理端点**：9081~9085，`/actuator/health`、`/actuator/info`、`/actuator/env` 等 Spring Boot Actuator 端点，仅 K8s 内部网络可达
- **Metrics 指标端点**：10081~10085，Prometheus `/metrics` 端点，仅 Prometheus Server 可抓取
- 端口分配遵循公式：`管理端点 = HTTP端口 + 1000`，`指标端点 = HTTP端口 + 2000`
- 所有管理端点和指标端点通过 K8s NetworkPolicy 限制仅内部访问

### 6.4 本地模型优先

**决策**：AI 模型优先本地部署，云端 API 作为降级备选。

**理由**：
- 员工敏感数据（身份证、人脸、薪资）不出境，符合 PIPL 要求
- 本地部署长期成本更低（无按量计费波动）
- 云端 API 作为降级方案，保障服务可用性

### 6.5 配置中心选择 Nacos

**决策**：使用 Nacos 作为配置中心，K8s Service Discovery 作为服务发现。

**理由**：
- Nacos 支持配置热更新（薪资规则、考勤规则等无需重启）
- Nacos 配置支持版本历史和灰度发布
- K8s 原生 Service Discovery 满足服务发现需求，无需额外引入 Eureka/Consul

### 6.6 服务治理方案

**决策**：采用应用层熔断（Resilience4j）替代 V8 版本中的 Istio 服务网格方案。

**V8 版 Istio 移除原因**：
- V8 版本设计了 Istio 服务网格用于管理微服务间通信，但评估后发现：当前微服务数量仅 4 个（V15），Istio Sidecar 代理（每个 Pod 额外注入 Envoy 容器）带来的资源开销（每 Pod 额外 50-100MB 内存）和服务延迟（5-10ms）不成比例
- Istio 的学习曲线和运维复杂度较高（配置 VirtualService、DestinationRule、PeerAuthentication 等），对当前团队规模而言维护成本过高
- 4 个域服务的调用关系清晰且稳定（由 Camunda 8 BPMN 流程定义），不需要服务网格的动态流量治理能力
- 移除 Istio 后，服务治理职责由以下组件分担：K8s Service（负载均衡）、Resilience4j（熔断/降级/舱壁隔离）、Nginx Ingress（连接级限流）、OpenTelemetry（链路追踪）

**Resilience4j 熔断降级方案**：

每个域服务内置 Resilience4j 组件，对所有跨服务 HTTP 调用和 AI 模型调用应用熔断保护。

| 组件 | 用途 | 配置参数 |
|------|------|---------|
| CircuitBreaker（熔断器） | 连续失败时自动熔断，避免级联故障 | `failureRateThreshold=50%`、`slowCallRateThreshold=80%`、`slowCallDurationThreshold=3s`、`minimumNumberOfCalls=20`、`slidingWindowSize=50`、`waitDurationInOpenState=30s`、`permittedNumberOfCallsInHalfOpenState=5` |
| Retry（重试） | 瞬态故障自动重试 | 最大重试次数 3 次，初始间隔 500ms，倍增系数 2.0，重试条件：5xx 错误、连接超时、Socket 超时 |
| RateLimiter（限流） | 保护下游服务不被过量请求压垮 | 限定周期 1 秒，限定请求数 100（按调用目标服务配置），等待超时 0（超出限流直接拒绝） |
| Bulkhead（舱壁隔离） | 限制对单一下游服务的并发调用数，防止线程/连接耗尽 | `maxConcurrentCalls=25`、`maxWaitDuration=0`（超出直接拒绝，不排队） |

**熔断策略按调用目标分类配置**（通过 Nacos 配置中心管理，支持热更新）：

| 调用目标 | 熔断阈值 | 重试次数 | 舱壁并发上限 | 超时 | 理由 |
|---------|---------|---------|-------------|------|------|
| 同集群域服务（HTTP） | failureRate 50% | 3 次 | 25 | 5s | 内网调用，期望低延迟和高可用 |
| AI 模型网关（HTTP/gRPC） | failureRate 40% | 2 次 | 15 | 30s | 模型推理耗时较长，降低重试避免放大负载 |
| 外部 API（招聘平台等） | failureRate 60% | 1 次 | 10 | 10s | 外部服务不可控，快速熔断保护 |
| RPA 任务提交（auto-domain） | failureRate 50% | 2 次 | 5 | 60s | RPA 任务提交本身轻量，但需等待浏览器初始化 |

**熔断状态监控**：
- Resilience4j 内置 Micrometer 指标暴露，通过域服务的 Metrics 端点（10081~10085）输出至 Prometheus
- Grafana 仪表盘展示：各熔断器状态（CLOSED/OPEN/HALF_OPEN）、失败率趋势、慢调用比例
- 告警规则：熔断器进入 OPEN 状态超过 1 分钟 → 发送告警至运维频道

**与 Nginx Ingress 的协同**（V15 修订：替代原 Spring Cloud Gateway）：
- Nginx Ingress 负责 **入向流量** 的连接级限流（`limit_req` 模块）
- 域服务层使用 Resilience4j 负责 **出向调用** 的熔断和降级保护
- 两者职责不重叠：Nginx 保护系统不被外部过量请求压垮，Resilience4j 保护域服务的下游依赖不引发级联故障

**服务间调用完整治理链路**：
```
客户端请求 → Nginx Ingress(TLS终止+路径路由+限流) → 域服务A(Spring Security鉴权+Resilience4j舱壁隔离+OpenTelemetry埋点) → HTTP调用(trace-id透传)
  → Resilience4j熔断器+重试 → 域服务B(OpenTelemetry埋点) → 业务处理 → 返回
  全程由 OpenTelemetry 自动记录 trace_id/span，Jaeger 可视化调用链
  trace-id 传递：Ingress 透传 → HTTP Header X-Trace-Id → 各域服务透传 → Kafka 消息头
  详见第 2.4.1 节分布式追踪方案
```

---

## 7. 分布式事务与数据一致性

### 7.1 Saga 模式

跨域服务操作采用 **Saga 模式** 保证最终一致性，由 Camunda 8 作为协调器。

**补偿机制**：每个业务步骤定义对应的补偿操作。

**典型场景 — 入职流程**：

| 步骤 | 域服务 | 操作 | 补偿操作 |
|------|--------|------|---------|
| 1 | recruit-domain | 创建入职申请 | 撤销申请 |
| 2 | user-domain | 创建系统账号 | 删除账号 |
| 3 | user-domain | 创建员工档案 | 标记档案无效 |
| 4 | recruit-domain | 发送入职通知 | 撤销通知 |

### 7.2 幂等性保证

- 所有写接口支持 `idempotency-key` 请求头
- Nginx Ingress 层透传 `idempotency-key`
- 服务端：首次请求正常执行，后续相同 key 直接返回缓存结果
- Key 有效期：24 小时，过期自动清理

### 7.3 数据快照机制

薪资核算等关键场景采用数据快照：
- 核算触发时生成 `payroll_snapshot_{year_month}_{snapshot_id}`
- 快照关联考勤、补贴、社保、公积金数据源的时间戳
- 快照存储于 `payroll_snapshot` 表，保留最近 12 个月
- 每条薪资记录携带 `snapshot_id`，可回溯至核算时原始数据

### 7.4 事件溯源

- 所有业务事件持久化至 `event_log` 表
- 事件格式：`{event_id, aggregate_type, aggregate_id, event_type, payload, timestamp, trace_id}`
- 支持事后审计、流程重放、数据修复

---

## 8. 安全合规与数据保护

### 8.1 认证与授权

详见第 2.2.1 节认证授权完整策略。

**授权模型**：RBAC（基于角色的访问控制）

| 角色 | 权限范围 |
|------|---------|
| 系统管理员 | 全部功能 |
| 人事专员 | 招聘/入职/培训/考勤/薪资/证明模块全部操作 |
| 部门主管 | 本部门下属数据查看、绩效审批 |
| 外务专员 | 工伤/公积金/社保申报操作 |
| 普通员工 | 个人信息查看、工资条查看、证明申请 |

**数据行级隔离**：部门主管仅可查看本部门下属数据。

**临时授权**：面试官凭二维码登录，时效 ≤ 2 小时。

### 8.2 数据安全

- **加密存储**：AES-256 加密敏感字段（身份证号、人脸特征、薪资数据）
- **传输加密**：强制 TLS 1.2+
- **密钥管理**：HashiCorp Vault 管理加密密钥，定期轮换（90 天）
- **数据不出境**：符合 PIPL 要求

### 8.3 操作审计

- **审计字段**：操作时间、操作人、IP、操作类型、模块、对象、前后快照、结果、耗时
- **不可篡改**：审计日志写入独立存储，保藏 ≥ 10 年
- **审计范围**：所有增删改查、导出、登录登出、Agent 调用操作

### 8.4 Agent 安全护栏

| 护栏类型 | 规则 |
|---------|------|
| 金额操作 | 未获审核批准不得修改金额变动记录 |
| 对外通讯 | 发送外部邮件前需预审确认 |
| 数据删除 | 不得无条件删除归档数据，删除需二次审批 |
| 推理校验 | 输出结果过合理性阈值检查 |
| Prompt 注入 | 用户输入和内部 Prompt 统一安全过滤 |

### 8.5 PIA（个人信息影响评估）流程设计

**触发条件**：

| 触发场景 | 评估级别 | 说明 |
|---------|---------|------|
| 新增采集个人信息类型 | 强制评估 | 如新增指纹采集、健康信息采集 |
| 个人信息处理目的变更 | 强制评估 | 如员工数据用于 AI 训练 |
| 个人信息共享/转让 | 强制评估 | 如向第三方共享员工信息 |
| 大规模自动化决策 | 强制评估 | 如 AI 筛选简历影响员工权益 |
| 个人信息处理系统重大升级 | 定期评估 | 每年至少 1 次全面评估 |
| 监管要求或投诉触发 | 强制评估 | 收到投诉或监管机构要求 |

**PIA 评估流程（Camunda 8 BPMN 定义）**：

```
[触发 PIA] → [PIA 申请节点] → [风险评估节点] →
  ├─ 低风险 → [简易评估] → [HR 主管审批] → [归档]
  ├─ 中风险 → [详细评估] → [HR 主管+法务审批] → [归档]
  └─ 高风险 → [详细评估] → [HR 主管+法务+外部专家审批] →
      [整改方案制定] → [整改执行] → [复查确认] → [归档]
```

**评估内容**：
1. 个人信息类型和范围
2. 处理目的和方式
3. 对员工权益的影响程度
4. 安全保护措施充分性
5. 合法合规性分析
6. 风险等级判定（低/中/高）

**审批机制**：
- 低风险：HR 主管审批即可
- 中风险：HR 主管 + 法务部门会签
- 高风险：HR 主管 + 法务 + 外部隐私专家三方审批，需附整改方案
- 所有 PIA 记录存储于 `pia_assessment` 表，不可删除仅可追加修订记录

**评估周期**：
- 强制评估：触发后 30 个工作日内完成
- 定期评估：每年 Q1 完成上一财年的全面 PIA 回顾
- PIA 评估报告保存期限 ≥ 10 年

---

## 9. 数据备份与灾难恢复

### 9.1 备份策略

| 类型 | 频率 | 保留期 | 存储位置 |
|------|------|--------|---------|
| 全量备份 | 每周日 02:00 | ≥ 15 年（薪资/工伤/协议） | MinIO + 离线磁带库 |
| 增量备份 | 每日 03:00 | ≥ 1 年 | MinIO |
| 配置备份 | 变更即时触发 | 永久 | Git 仓库 |
| 对象存储备份 | 每日快照 | ≥ 15 年 | MinIO 跨区域复制 |

### 9.2 灾难恢复流程

1. **检测与判断**：监控告警 → 运维确认主数据中心不可用
2. **决策**：运维负责人确认启动灾备切换（需 2 人确认）
3. **DNS 切换**：将域名解析指向灾备中心（预计 5~15 分钟生效）
4. **数据验证**：确认从库数据同步状态，补齐最后增量 binlog
5. **服务启动**：按依赖顺序启动数据层 → 域服务 → Ingress
6. **业务验证**：运行预定义的验证脚本（登录、查询、写入各 1 次）
7. **通知**：向 HR 团队发送系统恢复通知

### 9.3 恢复演练

- 每半年进行 1 次完整灾备切换演练
- 每次演练生成报告，记录实际 RTO/RPO
- 演练发现问题纳入改进项，限期解决

---

## 10. 数据库迁移与版本管理

### 10.1 Flyway 迁移管理

- **迁移脚本管理**：存放于 `db/migration/` 目录
- 命名规则：`V{version}__{description}.sql`（如 `V1.2.0__add_employee_table.sql`）
- **自动化执行**：应用启动时自动检查 `flyway_schema_history` 表
- **版本回滚**：支持反向迁移脚本（`R1.2.0__rollback_employee_table.sql`），仅测试环境使用
- **环境隔离**：开发/测试/生产独立 Flyway 配置，禁止跨环境迁移
- **变更审批**：生产 Schema 变更需 代码审查 + 测试验证 + DBA 审批

### 10.2 迁移脚本规范

- 每个脚本包含回滚注释（`-- rollback: DROP TABLE ...`）
- 禁止在迁移脚本中修改历史数据（数据变更使用独立的数据迁移脚本 `D{version}__{description}.sql`）
- 加锁操作在低峰期执行（周末凌晨）
- 大表 ALTER 使用 `pt-online-schema-change` 避免锁表

---

## 11. 数据字典与编码规范

### 11.1 编码规范

| 数据类型 | 编码规则 | 示例 |
|---------|---------|------|
| 员工编号 | `E` + 6 位自增 | E000001 |
| 部门编号 | `D` + 4 位层级编码 | D0101（研发一部） |
| 岗位编号 | `P` + 6 位 | P001001 |
| 入职单号 | `ON` + YYYYMMDD + 4 位 | ON202606130001 |
| 培训编号 | `TR` + YYYYMM + 4 位 | TR2026060001 |
| 薪资单号 | `PY` + YYYYMM + 6 位 | PY202606000001 |
| 证明编号 | `CT` + YYYYMMDD + 6 位 | CT20260613000001 |
| 流程实例 ID | UUID v4 | 550e8400-e29b-4144... |

### 11.2 核心数据字典

| 字段名 | 类型 | 说明 | 枚举值 |
|--------|------|------|--------|
| gender | TINYINT | 性别 | 0=未知, 1=男, 2=女 |
| marital_status | TINYINT | 婚姻状况 | 0=未知, 1=未婚, 2=已婚, 3=离异, 4=丧偶 |
| education | TINYINT | 学历 | 1=高中及以下, 2=大专, 3=本科, 4=硕士, 5=博士 |
| employment_type | TINYINT | 用工类型 | 1=正式, 2=试用, 3=实习, 4=劳务派遣, 5=兼职 |
| leave_type | TINYINT | 假期类型 | 1=年假, 2=病假, 3=事假, 4=婚假, 5=产假, 6=陪产假, 7=丧假 |
| attendance_status | TINYINT | 考勤状态 | 0=正常, 1=迟到, 2=早退, 3=缺勤, 4=请假, 5=加班, 6=出差 |
| performance_level | TINYINT | 绩效等级 | 1=优秀, 2=良好, 3=合格, 4=需改进, 5=不合格 |
| resign_reason | TINYINT | 离职原因 | 1=个人原因, 2=合同到期, 3=公司裁员, 4=协商解除, 5=违纪解除 |

---

## 12. Agent 异常处理与补偿机制

### 12.1 异常分类

| 类型 | 说明 | 处理方式 |
|------|------|---------|
| 瞬态异常 | 网络超时、数据库锁竞争 | 自动重试（指数退避 1s→3s→9s，最多 3 次） |
| 业务异常 | 数据校验失败、业务规则冲突 | 返回错误码，触发补偿流程 |
| 模型异常 | LLM 返回异常、OCR 识别失败 | 降级至规则引擎，记录告警 |
| 外部系统异常 | 招聘平台 API 不可用、政府网站拦截 | RPA 重试 → 降级告警 → 人工介入 |
| 系统性异常 | 服务崩溃、K8s Pod 重启 | 根据 flow_id 从断点恢复 |

### 12.2 Camunda 8 容错与回传机制

Camunda 8 将 External Task 标记为失败但保留重试次数，按 BPMN 定义的 Boundary Event 或错误序列流执行补偿路径：

**重试策略**：
- 瞬态错误（网络超时、服务不可用）：Camunda 8 内置重试，`retries=3`，退避策略为固定间隔 30 秒
- 业务错误（数据校验失败）：不重试，直接走错误序列流至补偿节点
- 模型错误（LLM 返回异常）：重试 1 次，失败后降级至规则引擎

**Boundary Event 设计**：
- 每个关键 Service Task 节点绑定 Error Boundary Event
- 超时边界事件（Timer Boundary Event）：任务超过 SLA 时限（如简历筛选 > 5 分钟）触发告警
- 补偿边界事件（Compensation Boundary Event）：操作完成后若后续步骤失败，触发已执行步骤的补偿

**断点恢复**：
- 域服务崩溃后，Camunda 8 保留流程实例状态和已完成节点记录
- 新的域服务 Pod 启动后通过 External Task Worker 重新拾取未完成任务
- 流程上下文（变量、中间结果）存储在 Zeebe 状态存储中，自动恢复

### 12.3 降级方案

| 场景 | 降级方案 | 人工介入 SLA |
|------|---------|-------------|
| LLM 不可用 | 简历筛选退化为关键词匹配 | 无需（降级后仍可运行） |
| OCR 不可用 | 转手动录入表单 | 2 小时内完成 |
| RPA 连续失败 ≥ 3 次 | 邮件+短信通知 HR 专员，转人工 | 2 小时内确认 |
| Kafka 不可用 | 本地队列缓冲，恢复后重放 | 监控告警，15 分钟内恢复 |
| 向量检索不可用 | 退化为关键词搜索（ES） | 无需（降级后可运行） |

---

## 13. 多租户隔离策略

### 13.1 租户模型

本系统当前为 **单租户模式**（GBM 企业自用），但架构预留多租户扩展能力。

**租户标识传递策略**：
- JWT Token payload 中携带 `tenant_id` 字段
- Nginx Ingress 透传 `X-Tenant-Id` Header 至下游域服务
- 域服务从 Header 读取 `tenant_id`，所有数据库查询自动附加 `WHERE tenant_id = ?` 过滤条件
- Kafka 消息中 `payload` 包含 `tenant_id` 字段，消费者据此过滤
- Redis Key 统一格式：`{tenant_id}:{key_type}:{key_id}`（如 `gbm:session:user_001`）

### 13.2 隔离设计

| 维度 | 隔离方式 | 说明 |
|------|---------|------|
| 数据隔离 | 逻辑隔离（`tenant_id` 字段） | 所有业务表含 `tenant_id`，查询自动过滤 |
| 存储隔离 | MinIO 按租户前缀分桶 | `/{tenant_id}/files/...` |
| 缓存隔离 | Redis Key 带租户前缀 | `{tenant_id}:session:{user_id}` |
| 计算隔离 | K8s Namespace 隔离（物理隔离模式） | 每个租户独立命名空间 |

### 13.3 扩展路径

若未来支持多租户：
1. Phase 1：逻辑隔离（当前设计已支持）
2. Phase 2：独立数据库（按租户分配独立 MySQL 实例，通过 ShardingSphere 路由）
3. Phase 3：物理隔离（独立 K8s 集群，适用于高安全要求客户）

---

## 14. Agent 间通信机制

### 14.1 通信协议

域服务间通信采用 **Kafka 作为传输层 + JSON 作为消息格式**。

**统一消息格式**：

```json
{
  "message_id": "uuid",
  "trace_id": "uuid",
  "flow_id": "uuid",
  "source_agent": "agent_name",
  "target_agent": "agent_name",
  "priority": "HIGH|MEDIUM|LOW",
  "ttl_seconds": 3600,
  "payload": {
    "action": "string",
    "data": {}
  },
  "timestamp": "2026-06-13T10:00:00Z"
}
```

**Kafka 消息头传递**：
除 JSON payload 中的 `trace_id` 字段外，Kafka 消息头还携带 OpenTelemetry 标准 `traceparent` 头（`00-{trace_id}-{span_id}-01`），用于自动关联上下游 Span。由 OpenTelemetry Kafka 拦截器自动附加/提取。

### 14.2 通信模式

| 模式 | 实现 | 场景 |
|------|------|------|
| 发布/订阅 | Kafka Topic Exchange | 简历入库通知招聘+分析域服务 |
| 请求/响应 | Kafka 队列 + Reply-To | auto-domain OCR 向域服务请求比对 |
| 事件溯源 | 消息持久化至 `event_log` 表 | 事后审计和流程重放 |

### 14.3 消息主题设计

| Topic | 分区数 | 保留期 | 说明 |
|-------|--------|--------|------|
| `hr.resume.inbound` | 4 | 7d | 简历入库事件 |
| `hr.onboarding.events` | 2 | 30d | 入职流程事件 |
| `hr.training.events` | 2 | 30d | 培训流程事件 |
| `hr.payroll.events` | 2 | 90d | 薪资核算事件 |
| `hr.attendance.events` | 4 | 7d | 考勤事件（高频） |
| `hr.performance.events` | 2 | 30d | 绩效流程事件 |
| `hr.external.events` | 2 | 30d | 外务申报事件 |
| `hr.analytics.events` | 2 | 7d | 分析数据事件 |
| `hr.system.alerts` | 1 | 30d | 系统告警事件 |

---

## 15. 跨服务数据流设计

### 15.1 核心数据流

**入职流程数据流**：
```
新员工扫码 → recruit-domain(入职申请) →
  → Kafka(hr.onboarding.events) →
  → auto-domain(OCR 识别证件) →
  → AI模型层(InsightFace 人脸采集) →
  → user-domain(创建账号+档案) →
  → recruit-domain(发送入职通知)
```

**薪资核算数据流**：
```
月末定时触发 → payroll-domain(生成快照) →
  → 并行拉取: payroll-domain(考勤数据) + payroll-domain(社保数据) +
    payroll-domain(公积金数据) + payroll-domain(补贴数据) →
  → payroll-domain(核算计算) →
  → Kafka(hr.payroll.events) →
  → auto-domain(数据统计) →
  → payroll-domain(工资条发放)
```

**招聘流程数据流**：
```
岗位发布 → recruit-domain(发布至渠道) →
  → 简历流入 → recruit-domain(简历匹配评分) →
  → Kafka(hr.resume.inbound) →
  → auto-domain(数据统计) →
  → recruit-domain(安排面试+组卷) →
  → recruit-domain(阅卷评分)
```

### 15.2 数据一致性保障

- 跨域服务数据通过事件最终一致性（非强一致性）
- 关键操作（薪资、权限变更）采用 Saga + 补偿
- 数据对账：每日凌晨运行对账任务，检测跨域服务数据差异并自动修复

---

## 16. 需求覆盖验证矩阵

| SRS 章节 | 需求描述 | 架构对应 | 覆盖状态 |
|---------|---------|---------|---------|
| 3.1 招聘管理 | 简历自动筛选、面试安排 | recruit-domain (:8082) | ✅ |
| 3.2 入职管理 | 证件 OCR、人脸采集、协议签署 | recruit-domain + auto-domain | ✅ |
| 3.3 培训管理 | 签到、考试、视频生成 | recruit-domain (:8082 培训子模块) | ✅ |
| 3.4 考勤管理 | 打卡采集、异常识别 | payroll-domain (:8083) | ✅ |
| 3.5 薪资管理 | 自动核算、工资条发放 | payroll-domain (:8083) | ✅ |
| 3.6 绩效管理 | 考核流程、汇总分析 | payroll-domain (:8083) | ✅ |
| 3.7 外务管理 | 工伤/公积金 RPA 申报 | payroll-domain + auto-domain | ✅ |
| 3.8 证明开具 | 自助签发证明 | user-domain (:8081) | ✅ |
| 3.9 离职管理 | 离职交接、证明开具 | user-domain + payroll-domain | ✅ |
| 4.1 性能要求 | 简历匹配 < 2s | 第 1.4 节性能目标 P95 < 2s | ✅ |
| 4.2 可用性要求 | 99.9% 可用性 | 第 5 章高可用设计 | ✅ |
| 4.3 安全要求 | 数据加密、RBAC | 第 8 章安全合规 | ✅ |
| 4.4 合规要求 | PIPL 合规、审计日志 | 第 8 章 PIA 流程 | ✅ |
| 5.1 接口需求 | 招聘平台 API 对接 | recruit-domain 适配层 | ✅ |
| 5.2 接口需求 | 政府网站 RPA | auto-domain RPA 集群 | ✅ |
| 6.1 数据需求 | 数据保留 ≥ 15 年 | 第 9 章备份策略 | ✅ |
| 7.1 AI 原生架构 | Agent 为核心执行主体 | 第 1 章架构全景 | ✅ |
| 7.2 零操作性 | 全部操作自动化 | 第 1 章设计原则 | ✅ |
| 8.1 部署架构 | K8s 容器化部署 | 第 5 章部署架构 | ✅ |
| 8.3 降级模式 | 外部故障降级方案 | 第 12 章降级方案 | ✅ |
| 9.1 运维保障 | 监控、告警、日志 | 第 1 章可观测性 | ✅ |
| 10.1 测试策略 | 自动化测试 | 第 5 章测试环境 | ✅ |

---

## 17. 国际化(i18n/l10n)架构设计

### 17.1 前端 i18n 方案

**技术选型**：vue-i18n 9.x

**实现方式**：
- 翻译资源文件按语言分目录：`locales/zh-CN/`、`locales/en-US/`
- 每个功能模块独立 JSON 文件：`locales/zh-CN/recruit.json`、`locales/zh-CN/payroll.json`
- 懒加载：按路由按需加载对应翻译文件，减少首屏体积
- 语言切换：用户设置中切换，偏好存储于 localStorage + 后端用户配置表
- 默认语言：中文（zh-CN），备选：英文（en-US）

**翻译管理流程**：
1. 前端代码使用 `$t('recruit.job.title')` 引用翻译键
2. 新增翻译键时，CI 流水线检查所有语言文件是否包含该键（缺失则告警）
3. 翻译内容由专业翻译人员审核，不依赖机器翻译
4. 翻译版本随代码一起发布，不支持运行时热更

### 17.2 后端多语言消息管理

**错误码国际化**：
- 后端返回统一错误码（数字），不直接返回错误消息文本
- 前端根据错误码 + 当前语言映射为对应提示
- 错误码定义于共享模块 `gbm-hr-error-codes`，格式：`{module_id}{error_id}`（如 `01001` = 用户模块-用户不存在）

**Agent 生成内容多语言**：
- Agent 输出时携带 `target_language` 参数（从请求上下文获取）
- LLM Prompt 中注入目标语言指令：`请用{language}回复`
- 多语言模板存储于 `i18n_template` 表：`{template_id, language, content}`

### 17.3 日期/金额格式化策略

| 类型 | 中文 (zh-CN) | 英文 (en-US) | 实现方式 |
|------|-------------|-------------|---------|
| 日期 | 2026 年 6 月 15 日 | June 15, 2026 | 前端使用 `dayjs` + locale |
| 时间 | 14:30:25 | 2:30:25 PM | 前端格式化，后端统一存储 UTC |
| 金额 | ￥12,345.67 | $12,345.67 | 前端 `Intl.NumberFormat` |
| 数字 | 12,345 | 12,345 | 前端 `Intl.NumberFormat` |
| 货币符号 | ￥ (CNY) | $ (USD) | 配置化，存储于系统参数表 |

**后端存储规范**：
- 日期/时间：统一存储为 UTC 时间戳（`DATETIME` 类型）
- 金额：存储为整数分（`BIGINT`，避免浮点精度问题），前端格式化展示
- 时区：用户配置中存储 `timezone`（如 `Asia/Shanghai`），前端据此格式化

---

## 18. 无障碍访问架构设计

### 18.1 WCAG 2.1 AA 技术要求

系统前端遵循 WCAG 2.1 AA 级标准，覆盖以下维度：

| 原则 | 要求 | 实现方式 |
|------|------|---------|
| 可感知性 | 非文本内容提供替代文本 | 所有图片 `alt` 属性、图标按钮 `aria-label` |
| 可操作 | 键盘可完成所有操作 | Tab 顺序导航、焦点可见、跳过导航链接 |
| 可理解 | 界面一致且可预测 | 表单标签关联 `for/id`、错误提示关联输入字段 |
| 鲁棒性 | 兼容辅助技术 | 语义化 HTML 标签、ARIA 角色标注 |

### 18.2 关键技术措施

- **颜色对比度**：文本与背景对比度 ≥ 4.5:1（正常文字）、≥ 3:1（大文字）
- **焦点管理**：模态弹窗打开时焦点锁定、关闭后恢复至触发元素
- **屏幕阅读器**：动态内容更新使用 `aria-live` 区域，通知类内容使用 `aria-live="polite"`
- **表单可访问性**：每个输入字段有 `<label>` 关联，错误提示使用 `aria-describedby`
- **键盘导航**：所有交互元素可通过 Tab 到达，快捷键文档可访问

### 18.3 关键路径无障碍设计（5 条核心路径）

| 路径 | 用户 | 无障碍要点 |
|------|------|-----------|
| 1. 新员工入职扫码 | 新员工 | 扫码页支持语音引导、大字体模式、高对比度主题 |
| 2. 薪资查询与工资条查看 | 在职员工 | 表格支持键盘导航、数据可导出为纯文本 |
| 3. 请假申请提交 | 在职员工 | 表单完整 label、日期选择器键盘可用、提交确认语音提示 |
| 4. 部门主管绩效审批 | 部门主管 | 审批列表屏幕阅读器友好、操作按钮明确焦点、批量操作键盘可用 |
| 5. 人事专员招聘管理 | 人事专员 | 复杂表格列排序键盘可用、筛选条件表单 label 完整、操作反馈 aria-live |

### 18.4 测试与验证

- **自动化检测**：CI 流水线集成 axe-core，每次构建运行无障碍扫描
- **手动测试**：每条核心路径使用 NVDA（Windows）/ VoiceOver（macOS）进行人工验证
- **定期审计**：每季度进行 1 次 WCAG 2.1 AA 全面审计，输出报告
- **用户反馈**：系统设置中提供"无障碍问题反馈"入口

---

*文档结束 — GBM AI Agent HR 架构设计文档 V15 全部 18 章完整呈现*
