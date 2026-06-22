def apply_patches():
    with open('/home/jim/DevFlow/projects/gbm-ai-agent-hr/docs/gbm-ai-agent-hr_ARCHITECTURE_V13.md', 'r', encoding='utf-8') as f:
        content = f.read()

    # Patch 1: Version row 13.0 -> 14.0
    old_v13 = '| 13.0 | 2026-06-13 | 后旺 | 基于后荣检验意见修订：(1)补充服务治理完整方案'
    new_v14 = '| 14.0 | 2026-06-13 | 后旺 | 基于后荣检验意见修订：(1)确保文档完整提交 — V13磁盘文件实际完整（1394行/18章），截断发生于检验内容传递环节；V14经完整性校验确保全部18章内容完整无缺失，第2.2.1节认证授权策略完整包含Token刷新/撤销/黑名单/多设备并发控制等全部内容；(2)明确DAG引擎技术选型 — 第2.4节补充"任务分解器采用 Camunda 8 BPMN 并行网关 + External Task Worker 模式，无需独立DAG引擎组件"；(3)补充Camunda 8与Kafka协作关系 — 明确Zeebe管理流程状态、Kafka负责Agent间事件传递的分工机制；(4)补充分布式追踪完整方案 — 第1.3节明确技术选型为OpenTelemetry + Jaeger，新增trace-id传递机制（HTTP Header + Kafka消息头）；(5)完善第2.2.1节认证授权策略 — 补充Token存储安全策略、Token撤销与黑名单机制、单点登出策略、多设备登录并发控制等缺失内容|'
    content = content.replace(old_v13, new_v14, 1)

    # Patch 2: Section 1.3 - Add distributed tracing tech
    old_13 = '| 端到端可追溯 | 每条业务流程拥有唯一 flow_id，全链路 trace-id 追踪 |'
    new_13 = '| 端到端可追溯 | 每条业务流程拥有唯一 flow_id，全链路 trace-id 追踪；技术选型：OpenTelemetry + Jaeger，详见第 2.4.1 节 |'
    content = content.replace(old_13, new_13, 1)

    # Patch 3: Section 2.4 - DAG engine + Camunda-Kafka + distributed tracing
    old_24 = '**编排模式**：\n\n| 模式 | 应用场景 | 示例 |\n|------|---------|------|\n| Pipeline 流水线 | 顺序执行端到端流程 | 入职办理流程 |\n| Fan-Out/Fan-In | 并行处理后汇聚 | 薪资核算并行拉取数据 |\n| Decision Tree | 条件分支 | 简历评分分拣 |\n| Feedback Loop | 结果反馈决定是否继续 | 材料校验-补传循环 |\n\n### 2.5 AI 模型服务层'

    new_24 = '**编排模式**：\n\n| 模式 | 应用场景 | 示例 |\n|------|---------|------|\n| Pipeline 流水线 | 顺序执行端到端流程 | 入职办理流程 |\n| Fan-Out/Fan-In | 并行处理后汇聚 | 薪资核算并行拉取数据 |\n| Decision Tree | 条件分支 | 简历评分分拣 |\n| Feedback Loop | 结果反馈决定是否继续 | 材料校验-补传循环 |\n\n**DAG 引擎技术选型说明（V14 新增）**：\n\n架构全景图中"任务分解器(DAG引擎)"即 **Camunda 8 BPMN 并行网关 + External Task Worker 模式的组合能力**，无需引入独立 DAG 引擎组件（如 Apache Airflow/Temporal），理由如下：\n\n- Camunda 8 BPMN 的 **Parallel Gateway** 天然支持 DAG 风格的有向无环图任务分解\n- External Task Worker 模式允许不同 Agent 并行拾取同一并行分支中的不同任务类型\n- 8 个 Agent 服务群的 BPMN 流程已涵盖所有 DAG 场景\n- 引入独立 DAG 引擎会增加运维复杂度，与"适度微服务"原则冲突\n\n**Camunda 8 与 Kafka 协作关系（V14 新增）**：\n\n| 维度 | Camunda 8 (Zeebe) | Kafka | 边界说明 |\n|------|-------------------|-------|---------|\n| 流程状态管理 | Zeebe 内部 Raft 共识维护流程实例状态 | 不参与流程状态管理 | Camunda 8 是流程状态的唯一权威源 |\n| 任务分发 | Service Task 通过 External Task Worker 分发给 Agent | 不参与任务分发 | Agent 向 Zeebe 轮询获取任务 |\n| 事件传递 | 流程到达节点时向 Kafka 发布事件 | 承载 Agent 间异步通信 | Kafka 是 Agent 间事件总线的传输层 |\n| 流程触发 | 定时触发或外部 API 调用 | Kafka 事件可作为 Camunda 8 Correlate Message 触发源 | Kafka 事件 → Camunda 8 Message Start Event |\n| 状态查询 | Operate 提供流程实例查询 UI | 不存储流程状态 | 运维通过 Operate 查看流程进度 |\n\n**协作流程示例（入职流程）**：\n```\n1. Camunda 8 启动 onboarding-process.bpmn → 到达 ST-01(创建入职申请)\n2. recruit-agent Worker 拾取 ST-01 → 执行 → 向 Zeebe 回传 Complete\n3. Camunda 8 推进至 ST-02(OCR识别证件) → 同时向 Kafka 发布 hr.onboarding.events 事件\n4. auto-agent Worker 拾取 ST-02 → OCR 识别 → Complete\n5. analytics-agent 等通过订阅 Kafka Topic 监听入职事件\n```\n\n### 2.4.1 分布式追踪方案（V14 新增）\n\n**技术选型**：OpenTelemetry + Jaeger\n\n| 组件 | 选型 | 用途 |\n|------|------|------|\n| 埋点 SDK | OpenTelemetry Java SDK 1.x | 各 Agent 自动埋点（HTTP 客户端/服务端、Kafka 生产者/消费者） |\n| 数据收集 | OpenTelemetry Collector | 各 Agent Pod 同部署 Sidecar，收集 trace/span 数据并导出至 Jaeger |\n| 存储与查询 | Jaeger (all-in-one) | 存储追踪数据，提供 UI 可视化调用链 |\n\n**trace-id 传递机制**：\n\n| 传递场景 | 传递方式 | 实现 |\n|---------|---------|------|\n| 前端 → Gateway | HTTP Header `X-Trace-Id` | Gateway 过滤链生成或透传 |\n| Gateway → Agent | HTTP Header `X-Trace-Id` + W3C `traceparent` | Spring Cloud Sleuth 自动注入 |\n| Agent → Agent (HTTP) | HTTP Header `X-Trace-Id` | OpenTelemetry HTTP 客户端拦截器自动附加 |\n| Agent → Kafka → Agent | Kafka 消息头 `traceparent` | OpenTelemetry Kafka 拦截器自动序列化/反序列化 |\n| Agent → AI 模型网关 | HTTP Header `X-Trace-Id` | 同上 |\n\n**OpenTelemetry 自动埋点配置**：\n```yaml\notel:\n  service.name: ${spring.application.name}\n  resource.attributes:\n    deployment.environment: ${SPRING_PROFILES_ACTIVE}\n  exporter:\n    otlp:\n      endpoint: http://otel-collector:4317\n```\n\n**关键 Span 命名规范**：\n- HTTP 请求：`HTTP GET /api/v1/employees`\n- Kafka 发送/消费：`Kafka hr.payroll.events SEND` / `RECEIVE`\n- Agent 业务操作：`recruit-agent.resume.score` / `comp-agent.payroll.calculate`\n- AI 模型调用：`ai-model.embedding` / `ai-model.ocr`\n\n**Jaeger 可视化**：通过 flow_id 查询完整业务流程调用链，支持按服务/操作/状态过滤，慢调用告警。\n\n### 2.5 AI 模型服务层'
    content = content.replace(old_24, new_24, 1)

    # Patch 4: Section 2.2.1 - Token security, revocation, SSO, multi-device, RBAC
    old_221 = '**移动端敏感操作二次验证**：\n- 触发场景：薪资查询、个人信息修改、离职申请、批量导出\n- 方案：短信验证码 + 生物识别（移动端指纹/Face ID）\n- 流程：用户发起敏感操作 → Gateway 拦截 → 返回 403 + `requires_mfa` 标记 → 前端弹出验证码输入框 → 提交验证码 → user-agent 验证通过 → 颁发短期授权凭证（10 分钟有效） → 放行原请求\n- 验证码有效期 5 分钟，错误 3 次锁定 30 分钟\n\n#### 2.2.2 API 版本策略'

    new_221 = '**移动端敏感操作二次验证**：\n- 触发场景：薪资查询、个人信息修改、离职申请、批量导出\n- 方案：短信验证码 + 生物识别（移动端指纹/Face ID）\n- 流程：用户发起敏感操作 → Gateway 拦截 → 返回 403 + `requires_mfa` 标记 → 前端弹出验证码输入框 → 提交验证码 → user-agent 验证通过 → 颁发短期授权凭证（10 分钟有效） → 放行原请求\n- 验证码有效期 5 分钟，错误 3 次锁定 30 分钟\n\n**Token 存储安全策略（V14 新增）**：\n\n| Token 类型 | 存储位置 | Cookie 配置 | 安全考虑 |\n|-----------|---------|------------|---------|\n| Access Token | 前端内存（JavaScript 变量） | 不使用 Cookie | 防 XSS，页面刷新后需 Refresh Token 重新获取 |\n| Refresh Token | HttpOnly Cookie | `HttpOnly=True`、`Secure=True`、`SameSite=Strict`、`Path=/auth/refresh` | 防 XSS/CSRF，仅 HTTPS |\n| 移动端 Token | 原生安全存储 | iOS Keychain / Android Keystore | 防逆向，卸载后清除 |\n\n**Token 撤销与黑名单机制（V14 新增）**：\n\n| 撤销场景 | 处理方式 | 影响范围 |\n|---------|---------|---------|\n| 用户主动登出 | 当前 Token jti 写入 Redis 黑名单 | 仅当前设备 |\n| 密码修改 | 该用户所有未过期 Token jti 写入黑名单 | 全设备强制下线 |\n| 管理员禁用账号 | 所有 Token jti 写入黑名单 + Redis Session 清除 | 全设备强制下线 |\n| 检测到异常行为 | 所有 Token jti 写入黑名单，触发安全告警 | 全设备强制下线 |\n| Token 轮换 | 旧 Refresh Token jti 写入黑名单 | 仅旧 Refresh Token 失效 |\n\n- Redis 黑名单 Key：`token:blacklist:{jti}`，TTL = Token 剩余有效期（最大 7 天）\n- Gateway 认证过滤器：解析 JWT → 检查签名 → 检查过期 → **检查 Redis 黑名单** → 放行\n- 黑名单性能：Redis 单 Key 查询 < 1ms；高峰期可引入 Caffeine 本地缓存（TTL 5 分钟）\n\n**单点登出策略（V14 新增）**：\n\n| 登出类型 | 触发方式 | 处理逻辑 |\n|---------|---------|---------|\n| 单端登出 | 用户点击"退出登录" | 仅撤销当前设备 Refresh Token（`device_id` 标识） |\n| 全部设备下线 | 安全设置选择"全部设备下线" | 遍历 Redis 中该用户所有活跃 Session，全量加入黑名单 |\n| 被动登出 | 密码修改/账号禁用/安全策略触发 | 自动执行"全部设备下线"，通知所有活跃设备 |\n\n**多设备登录并发控制（V14 新增）**：\n\n- 最大并发设备数：默认 5 个（web/mobile/h5 各可独立登录）\n- 超限处理：最早登录的设备 Refresh Token 自动撤销（踢下线）\n- 活跃设备管理：用户可在安全设置查看活跃设备列表，支持手动踢出\n- Redis Session 结构：\n  - `user:sessions:{user_id}` → Set，包含所有活跃 Session ID\n  - `user:session:{session_id}` → Hash，包含 device_type/login_time/last_active/ip/refresh_token_jti\n- 管理员可配置：Nacos 中按角色配置 `auth.max.devices.{role} = 5`\n\n**权限模型（RBAC，V14 新增）**：\n\n采用 **RBAC（基于角色的访问控制）**，不使用 ABAC，理由：HR 系统权限边界清晰，RBAC 足以满足。\n\n| 角色 | 权限范围 | 数据行级隔离 |\n|------|---------|------------|\n| 系统管理员 | 全部功能 | 无限制 |\n| 人事专员 | 招聘/入职/培训/考勤/薪资/证明全部操作 | 全公司数据 |\n| 部门主管 | 本部门数据查看、绩效审批 | 仅本部门及下级部门 |\n| 外务专员 | 工伤/公积金/社保申报操作 | 全公司数据 |\n| 普通员工 | 个人信息查看、工资条、证明申请 | 仅自身数据 |\n\n- 权限校验：Gateway 提取 JWT roles → 路由至 Agent → Spring Security `@PreAuthorize` → MyBatis-Plus 数据权限拦截器附加部门过滤\n- 权限变更生效：下次 Token 刷新时加载最新权限（≤30 分钟），紧急变更可强制重新登录\n\n#### 2.2.2 API 版本策略'
    content = content.replace(old_221, new_221, 1)

    # Patch 5: Update 6.6 service chain to reference distributed tracing
    old_66 = '''**服务间调用完整治理链路**：
```
客户端请求 → Nginx Ingress(TLS终止) → Spring Cloud Gateway(Sentinel限流+JWT鉴权)
  → Agent服务A(Resilience4j舱壁隔离) → HTTP调用 → Resilience4j熔断器+重试
  → Agent服务B → 业务处理 → 返回
  全程由 OpenTelemetry 记录 trace_id，Jaeger 可视化调用链
```'''

    new_66 = '''**服务间调用完整治理链路**：
```
客户端请求 → Nginx Ingress(TLS终止) → Spring Cloud Gateway(Sentinel限流+JWT鉴权+trace-id注入)
  → Agent服务A(Resilience4j舱壁隔离+OpenTelemetry埋点) → HTTP调用(trace-id透传)
  → Resilience4j熔断器+重试 → Agent服务B(OpenTelemetry埋点) → 业务处理 → 返回
  全程由 OpenTelemetry 自动记录 trace_id/span，Jaeger 可视化调用链
  trace-id 传递：Gateway 生成 → HTTP Header X-Trace-Id → 各 Agent 透传 → Kafka 消息头
  详见第 2.4.1 节分布式追踪方案
```'''
    content = content.replace(old_66, new_66, 1)

    # Patch 6: Architecture diagram - DAG engine label
    old_dag = '|  |(Camunda 8)  |  |(DAG引擎)    |  |(Redis+DB)   |               |'
    new_dag = '|  |(Camunda 8/  |  |  (BPMN并行   |  |(Redis+DB)   |               |\n|  |  Zeebe)    |  |  网关+Worker)|               |'
    content = content.replace(old_dag, new_dag, 1)

    # Patch 7: Kafka - trace-id
    old_kafka = '|  |  |  Agent间异步通信 / 事件发布订阅 / 流程状态流转                 | |'
    new_kafka = '|  |  |  Agent间异步通信 / 事件发布订阅 / trace-id透传(消息头)         | |'
    content = content.replace(old_kafka, new_kafka, 1)

    # Patch 8: Section 14.1 - Kafka message header
    old_141 = '''  "timestamp": "2026-06-13T10:00:00Z"
}
```

### 14.2 通信模式'''

    new_141 = '''  "timestamp": "2026-06-13T10:00:00Z"
}
```

**Kafka 消息头传递（V14 新增）**：
除 JSON payload 中的 `trace_id` 字段外，Kafka 消息头还携带 OpenTelemetry 标准 `traceparent` 头（`00-{trace_id}-{span_id}-01`），用于自动关联上下游 Span。由 OpenTelemetry Kafka 拦截器自动附加/提取。

### 14.2 通信模式'''
    content = content.replace(old_141, new_141, 1)

    # Patch 9: Section 1.1 - observable reference
    old_11 = '5. **可观测性** — 完整的链路追踪、日志、监控'
    new_11 = '5. **可观测性** — 完整的链路追踪（OpenTelemetry + Jaeger，详见第 2.4.1 节）、日志、监控'
    content = content.replace(old_11, new_11, 1)

    # Write output
    out_path = '/home/jim/DevFlow/projects/gbm-ai-agent-hr/docs/gbm-ai-agent-hr_ARCHITECTURE_V14.md'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)

    lines = content.split('\n')
    print(f"Total lines: {len(lines)}")
    print(f"Total chars: {len(content)}")

    checks = [
        ('V14 version', '14.0 | 2026-06-13'),
        ('DAG engine', 'DAG 引擎技术选型说明'),
        ('Camunda-Kafka', 'Camunda 8 与 Kafka 协作关系'),
        ('Distributed tracing', '2.4.1 分布式追踪方案'),
        ('Token blacklist', 'Token 撤销与黑名单机制'),
        ('SSO', '单点登出策略'),
        ('Multi-device', '多设备登录并发控制'),
        ('Token storage', 'Token 存储安全策略'),
        ('RBAC', '权限模型（RBAC'),
        ('Kafka header', 'Kafka 消息头传递（V14'),
        ('OTel ref', 'OpenTelemetry + Jaeger，详见第 2.4.1 节'),
        ('Doc end', '文档结束'),
    ]

    for name, kw in checks:
        found = kw in content
        status = '+' if found else 'X'
        print(f"  [{status}] {name}")

apply_patches()
