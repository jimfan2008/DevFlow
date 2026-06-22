Here's a thinking process:

1.  **Analyze User Input:**
    - **Role:** 资深数据库架构师后旺-DATABASE（HouWang）
    - **Task:** 设计数据库架构，输出完整的数据库设计文档。
    - **Context:** The user provided a detailed SRS (Software Requirements Specification) V15 for "GBM AI Agent HR 智能人力管理系统". Key characteristics: AI-native, AI Agent-driven, fully automated, zero manual operation principle, covers full HR lifecycle (recruitment, onboarding, probation, offboarding, training, attendance, payroll, performance, external affairs, certificates, etc.), uses RPA-Agent, Multi-Modal LLM, Agent Orchestration Layer, Chain-of-Thought Verification.
    - **Constraint:** "不要输出推理过程。" (Do not output reasoning process.)

2.  **Identify Key Requirements for Database Design from SRS:**
    - **Domain:** HR Management (Recruitment, Onboarding, Probation, Offboarding, Training, Attendance, Payroll, Performance, External Affairs/Government, Certificates, Employee Documents/Proofs).
    - **Architecture Style:** AI-Native, Agent-Driven. This implies the database needs to support:
        - Agent state management, task queues, orchestration logs.
        - Multi-modal data storage (documents, images, audio, videos for certificates, IDs, training materials).
        - Audit trails & Chain-of-Thought (CoT) verification logs.
        - High consistency for payroll/attendance, high availability for agent operations.
        - Strict compliance with Chinese data security laws (PIPL, Data Security Law, Cybersecurity Law) - requires encryption, access control, data masking, retention policies.
        - RPA-Agent interaction logs (external system interactions).
        - Degradation mode logs (manual override records).
    - **Data Types:** Structured (employee info, payroll, attendance), Semi-structured (JSON for agent configs, task definitions, CoT logs), Unstructured/Objects (documents, images, audio, video).
    - **Key Entities (Mental Draft):**
        - `hr_employees` (员工主数据)
        - `hr_recruitment_jobs` (招聘岗位)
        - `hr_candidates` (候选人)
        - `hr_interviews` (面试记录)
        - `hr_onboarding_tasks` (入职任务/流程)
        - `hr_documents` (员工档案/证件/合同)
        - `hr_attendance_records` (考勤记录)
        - `hr_payroll_cycles` (薪资周期)
        - `hr_payroll_items` (薪资明细)
        - `hr_training_courses` (培训课程)
        - `hr_training_sessions` (培训场次/签到)
        - `hr_performance_reviews` (绩效考核)
        - `hr_external_affairs` (外务申报记录 - 社保/公积金/工伤)
        - `hr_certificates` (证书证照)
        - `agent_tasks` (Agent任务队列)
        - `agent_executions` (Agent执行日志/CoT)
        - `agent_rpa_sessions` (RPA会话记录)
        - `audit_logs` (审计日志)
        - `system_configs` (系统配置)
        - `human_reviews` (人工审核/仲裁记录)

3.  **Structure the Database Design Document:**
    A standard, professional database design document should include:
    - 文档概述 (Document Overview)
    - 设计原则与规范 (Design Principles & Standards)
    - 架构选型 (Architecture Selection)
    - 逻辑数据模型 (Logical Data Model - ER Diagram/Tables)
    - 物理数据模型与存储设计 (Physical Model & Storage)
    - 索引与性能优化 (Indexing & Performance)
    - 安全与合规设计 (Security & Compliance)
    - 数据生命周期与备份策略 (Data Lifecycle & Backup)
    - 附录 (Appendix - DDL snippets, naming conventions)

4.  **Flesh out each section (Mental Refinement & Drafting):**

    *1. 文档概述*
    - 项目名称: GBM AI Agent HR
    - 版本: DB-V1.0
    - 目标: 支撑AI原生HR系统全生命周期数据流转，满足零操作性原则、高可用、强合规要求。

    *2. 设计原则与规范*
    - 命名规范: 表名 `模块_实体` (小写蛇形), 字段 `类型_含义`, 主键 `id` (UUID v7 or Snowflake), 外键 `xxx_id`。
    - 数据类型: 统一使用 `VARCHAR`, `DECIMAL`, `TIMESTAMP`, `JSONB`, `UUID`。
    - 软删除: `is_deleted` (BOOLEAN), `deleted_at`。
    - 审计字段: `created_by`, `created_at`, `updated_by`, `updated_at`。
    - 多租户/隔离: 虽未明确提多租户，但按企业标准设计 `tenant_id` 或 `org_id` 预留扩展。
    - AI原生适配: 专门设计 Agent 状态机表、CoT 验证表、RPA 会话表。

    *3. 架构选型*
    - 核心业务库: PostgreSQL 16+ (强事务、JSONB支持、扩展性好、适合复杂查询与AI数据)
    - 缓存/会话: Redis 7+ (Agent状态缓存、分布式锁、RPA会话状态)
    - 对象存储: MinIO / AWS S3 (证件、合同、培训资料、音视频，数据库仅存元数据与路径)
    - 向量数据库: Milvus / pgvector (用于简历语义匹配、知识库检索、Agent记忆)
    - 消息队列: RabbitMQ / Kafka (Agent任务分发、事件驱动架构)
    - 搜索引擎: Elasticsearch (日志、CoT记录、全文检索)

    *4. 逻辑数据模型 (核心表设计)*
    Need to define key tables with fields, types, constraints. I'll group them by domain.
    - **基础与主数据 (Base & Master)**
      - `hr_employees`: id, emp_no, name, gender, id_card, phone, email, dept_id, position_id, status, hire_date, entry_date, ...
      - `hr_organizations`: id, dept_code, dept_name, parent_id, ...
      - `hr_positions`: id, pos_code, pos_name, dept_id, ...
    - **招聘与候选人 (Recruitment)**
      - `hr_candidates`: id, name, phone, email, resume_url, status, source, ...
      - `hr_interviews`: id, candidate_id, interviewer_id, schedule_time, result, feedback_json, ...
    - **员工档案与证件 (Documents & Certificates)**
      - `hr_documents`: id, emp_id, doc_type, file_path, hash, expire_date, status, ...
      - `hr_certificates`: id, emp_id, cert_name, cert_no, issue_date, expire_date, reminder_days, ...
    - **考勤与薪资 (Attendance & Payroll)**
      - `hr_attendance_records`: id, emp_id, work_date, check_in, check_out, hours, status, rule_applied, ...
      - `hr_payroll_cycles`: id, cycle_name, start_date, end_date, status, ...
      - `hr_payroll_ledgers`: id, cycle_id, emp_id, gross_salary, deductions, net_salary, status, approved_by, ...
    - **培训与绩效 (Training & Performance)**
      - `hr_training_sessions`: id, course_id, start_time, end_time, location, status, ...
      - `hr_training_attendees`: id, session_id, emp_id, check_in_status, score, ...
      - `hr_performance_reviews`: id, emp_id, period, reviewer_id, score, comments, status, ...
    - **外务与政府申报 (External Affairs)**
      - `hr_external_tasks`: id, emp_id, task_type (社保/公积金/工伤), target_system, status, rpa_session_id, ...
      - `hr_gov_submissions`: id, task_id, submit_date, result, receipt_url, ...
    - **AI Agent 核心引擎 (AI Agent Core)**
      - `agent_task_queue`: id, task_type, payload_json, status, priority, created_at, scheduled_at, ...
      - `agent_execution_logs`: id, task_id, agent_id, chain_of_thought_json, action_taken, result_status, error_trace, ...
      - `agent_memory_knowledge`: id, emp_id, context_type, embedding_vector, raw_text, updated_at, ... (pgvector)
      - `human_review_records`: id, task_id, reviewer_id, review_result, comments, reviewed_at, ... (战略性审核/争议仲裁)
    - **系统与安全 (System & Security)**
      - `audit_logs`: id, actor_type, actor_id, action, resource, old_value, new_value, ip, created_at, ...
      - `degradation_logs`: id, start_time, end_time, reason, manual_interventions_count, resolved_by, ...

    *5. 物理设计与存储策略*
    - 分区策略: 考勤表按年月分区 (`PARTITION BY RANGE (work_date)`)，日志表按时间分区。
    - 存储介质: 热数据(SSD)、温数据(HDD)、冷数据/归档(对象存储+压缩)。
    - 数据加密: 敏感字段(id_card, phone, bank_account) 使用 AES-256-GCM 加密存储，密钥由 KMS 管理。传输 TLS 1.3。
    - 字段设计细节: 使用 `JSONB` 存储灵活的 Agent 配置、CoT 推理链、RPA 步骤序列。使用 `UUIDv7` 保证时间序+分布式唯一。

    *6. 索引与性能优化*
    - 复合索引: `(emp_id, work_date)`, `(candidate_id, status)`, `(task_type, status, scheduled_at)`
    - GIN 索引: 用于 `JSONB` 字段 (agent payload, CoT logs) 和 全文检索。
    - BRIN 索引: 用于时间分区表的时间范围查询。
    - 连接池: PgBouncer 管理连接。
    - 读写分离: 核心交易主库，报表/分析从库。

    *7. 安全与合规设计 (PIPL/DSL/CSL)*
    - 数据脱敏: 视图层自动脱敏 (`id_card` -> `110***********1234`)，仅授权角色可见明文。
    - 权限控制: RBAC + ABAC (基于属性的访问控制，如仅本部门主管可见本部门薪资)。
    - 数据留存: 离职员工数据保留期限依法合规（如档案10年，考勤薪资3年），自动归档/匿名化。
    - 审计追踪: 所有 Agent 操作与人工审核均记录至不可篡改的审计链（可选 WORM 存储或区块链哈希锚定）。

    *8. 数据生命周期与备份*
    - 备份策略: 全量每日，增量每小时，WAL 连续归档。跨地域容灾。
    - 恢复演练: 季度 RTO/RPO 测试。
    - 数据清理: 自动化策略清理过期临时文件、失败任务日志。

    *9. 附录*
    - 命名规范对照表
    - 核心表 DDL 示例 (PostgreSQL)
    - 状态机枚举定义

5.  **Self-Correction & Refinement (Mental Review against SRS):**
    - *Check against SRS:* Does it support AI-native? Yes, dedicated agent tables, CoT logs, RPA sessions.
    - *Zero-operation principle:* Handled via agent task queues, execution logs, and human review records for strategic approval only.
    - *Multi-modal:* Handled via object storage integration, DB stores metadata/paths/hashes.
    - *Compliance:* Explicit PIPL/DSL measures, encryption, audit trails, retention policies.
    - *Degradation mode:* Explicit `degradation_logs` table as per SRS 2.2.
    - *Structure:* Professional, complete, matches standard DB architecture docs.
    - *Constraint:* "不要输出推理过程。" -> I will output ONLY the final document.
    - *Tone/Role:* 资深数据库架构师后旺-DATABASE. I'll add a brief professional header/sign-off if needed, but keep it strictly document-focused.
    - *Technical Depth:* Use PostgreSQL as primary, mention pgvector, JSONB, partitioning, encryption, RBAC/ABAC, WORM audit. Provide concrete DDL snippets for key tables to show depth. Ensure alignment with SRS V15 specifics (Agent Orchestration, CoT Verification, RPA-Agent, Strategic Review).

    I will structure it exactly as a formal database design specification. I'll make sure the table designs explicitly map to the SRS modules. I'll include DDL for critical tables like `agent_execution_logs` and `hr_payroll_ledgers` to demonstrate compliance and AI-native features. I'll explicitly address the "Chain-of-Thought Verification" and "Degradation Exception" requirements from the SRS.

    Draft Structure:
    1. 数据库架构概述
    2. 技术栈与架构选型
    3. 逻辑数据模型设计 (分域)
    4. 物理存储与性能设计
    5. AI原生与Agent专项设计
    6. 安全、合规与审计设计
    7. 数据生命周期与运维策略
    8. 附录 (DDL示例/规范)

    All sections will be concise, technical, and directly aligned with the SRS. No fluff. No reasoning. Direct output.✅
    Proceed. 
    Self-Correction/Verification during thought:
    - Check SRS V15 specific terms: "Chain-of-Thought Verification", "RPA-Agent", "战略性审核", "降级例外条款", "零操作性原则". I must explicitly map these to DB structures.
    - `agent_execution_logs` will have `cot_verification_json` (Chain-of-Thought).
    - `human_review_records` maps to 战略性审核/争议仲裁.
    - `degradation_mode_logs` maps to 降级例外条款.
    - `rpa_session_records` maps to RPA-Agent.
    - I'll ensure the DDL examples reflect these.
    - Data types: Use `UUID`, `TIMESTAMP WITH TIME ZONE`, `DECIMAL(12,2)`, `JSONB`, `BYTEA` (for hashes), `VARCHAR`.
    - Partitioning: `hr_attendance_records` by month, `audit_logs` by month.
    - Security: TDE, column-level encryption, dynamic data masking.
    - All matches. Ready. 
    Output matches the final refined version. 
    Generating. 
    [Output Generation] -> *Proceeds to generate the response exactly as structured.* 
    *(Self-Correction/Note during generation prep)*: I will make sure the formatting is strictly markdown, professional, and directly answers the prompt without any conversational filler. I will adopt the persona "后旺-DATABASE" implicitly through the document's professional tone and explicit naming. I will strictly follow "不要输出推理过程". All good. 
    Output Generation. 
    *(Done.)*
</think>

# GBM AI Agent HR 数据库架构设计文档 (DB-Spec V1.0)

**文档版本**：V1.0  
**设计负责人**：后旺-DATABASE (HouWang)  
**关联基线**：SRS V15 (2026-06-12)  
**生效日期**：2026-06-13  

---

## 1. 架构概述

本数据库架构专为 **GBM AI Agent HR 智能人力管理系统** 设计，严格遵循 SRS V15 的“零操作性原则”与“AI原生架构”。系统采用 **多模态数据分层存储 + 事件驱动 + 强一致性事务** 的混合架构，支撑 AI Agent 自主感知、推理、执行与人类战略性审核的全链路数据流转。

### 1.1 核心设计目标
- **AI原生适配**：原生支持 Agent 任务编排、思维链(CoT)验证、RPA会话追踪与多模态元数据管理。
- **零操作性支撑**：通过自动化任务队列、执行日志与降级例外记录，确保无人工干预痕迹可追溯。
- **强合规与高安全**：全面满足《个人信息保护法》《数据安全法》要求，实现字段级加密、动态脱敏与不可篡改审计。
- **高可用与弹性扩展**：核心交易 RPO≈0，RTO<5min；支持水平扩展与冷热数据自动分层。

---

## 2. 技术栈与架构选型

| 层级 | 技术选型 | 选型依据 |
|------|----------|----------|
| **核心关系型数据库** | PostgreSQL 16+ | 强ACID事务、原生JSONB支持、pgvector扩展、成熟分区与并发控制，适配复杂HR业务与AI推理数据 |
| **缓存与分布式协调** | Redis 7+ Cluster | Agent状态机缓存、分布式锁、RPA会话临时状态、高频配置热加载 |
| **对象存储** | MinIO / S3 兼容协议 | 存储证件、合同、培训音视频、RPA截图等大容量非结构化数据，DB仅存元数据与哈希校验 |
| **向量检索引擎** | pgvector (内置) / Milvus | 简历语义匹配、员工画像检索、Agent长期记忆与知识库检索 |
| **消息与事件总线** | RabbitMQ / Apache Kafka | Agent任务分发、业务事件驱动(如入职完成触发薪资初始化)、降级模式通知 |
| **日志与检索** | Elasticsearch 8.x | CoT验证日志、审计日志、RPA操作轨迹的全文检索与聚合分析 |

---

## 3. 逻辑数据模型设计

数据库按业务域划分为 6 大逻辑模块，采用规范化设计(3NF)，关键大表采用分区策略。

### 3.1 基础与主数据域 (`base_`)
| 表名 | 核心字段 | 说明 |
|------|----------|------|
| `base_employees` | `id(UUID)`, `emp_no`, `name`, `id_card_enc`, `phone_enc`, `email`, `dept_id`, `position_id`, `status`, `hire_date`, `entry_date`, `created_at` | 员工主数据，敏感字段加密存储 |
| `base_organizations` | `id`, `org_code`, `org_name`, `parent_id`, `manager_id`, `path`, `status` | 组织架构树 |
| `base_positions` | `id`, `pos_code`, `pos_name`, `dept_id`, `level`, `salary_band`, `status` | 岗位字典 |

### 3.2 招聘与候选人域 (`rec_`)
| 表名 | 核心字段 | 说明 |
|------|----------|------|
| `rec_candidates` | `id`, `name`, `phone`, `email`, `resume_obj_path`, `resume_hash`, `status`, `source`, `match_score`, `created_at` | 候选人池，简历文件存对象存储 |
| `rec_interviews` | `id`, `candidate_id`, `interviewer_ids`, `schedule_time`, `location`, `result`, `feedback_json`, `created_at` | 面试安排与结果 |

### 3.3 员工档案与外务域 (`hr_`)
| 表名 | 核心字段 | 说明 |
|------|----------|------|
| `hr_documents` | `id`, `emp_id`, `doc_type`, `obj_path`, `file_hash`, `expire_date`, `status`, `verified_at` | 劳动合同、身份证、学历证等 |
| `hr_certificates` | `id`, `emp_id`, `cert_name`, `cert_no`, `issue_date`, `expire_date`, `reminder_days`, `status` | 职业资格证、特种作业证等 |
| `hr_external_tasks` | `id`, `emp_id`, `task_type`, `target_system`, `status`, `rpa_session_id`, `submit_result_json`, `created_at` | 社保/公积金/工伤等外务申报 |

### 3.4 考勤与薪资域 (`pay_`)
| 表名 | 核心字段 | 说明 |
|------|----------|------|
| `pay_attendance_records` | `id`, `emp_id`, `work_date`, `check_in`, `check_out`, `overtime_hours`, `leave_hours`, `status`, `rule_applied`, `created_at` | 按 `work_date` 范围分区 |
| `pay_payroll_cycles` | `id`, `cycle_name`, `start_date`, `end_date`, `status`, `batch_no` | 薪资计算周期 |
| `pay_payroll_ledgers` | `id`, `cycle_id`, `emp_id`, `gross_salary`, `social_deduction`, `tax_deduction`, `net_salary`, `status`, `approved_by`, `approved_at` | 薪资明细，强事务控制 |

### 3.5 培训与绩效域 (`perf_`)
| 表名 | 核心字段 | 说明 |
|------|----------|------|
| `perf_training_sessions` | `id`, `course_id`, `start_time`, `end_time`, `location`, `status`, `sign_in_obj_path` | 培训场次 |
| `perf_training_attendees` | `id`, `session_id`, `emp_id`, `check_in_status`, `score`, `feedback` | 参训记录 |
| `perf_reviews` | `id`, `emp_id`, `period`, `reviewer_id`, `score`, `comments`, `status`, `created_at` | 绩效考核 |

### 3.6 AI Agent 引擎域 (`agent_`)
| 表名 | 核心字段 | 说明 |
|------|----------|------|
| `agent_task_queue` | `id`, `task_type`, `payload_jsonb`, `status`, `priority`, `scheduled_at`, `retry_count`, `created_at` | Agent任务调度中枢 |
| `agent_execution_logs` | `id`, `task_id`, `agent_id`, `cot_verification_jsonb`, `action_trace`, `result_status`, `error_trace`, `duration_ms`, `created_at` | **思维链验证核心表** |
| `agent_rpa_sessions` | `id`, `task_id`, `target_url`, `browser_profile`, `step_sequence_jsonb`, `status`, `screenshot_obj_paths`, `created_at` | RPA-Agent操作轨迹 |
| `agent_human_reviews` | `id`, `task_id`, `reviewer_id`, `review_type`, `decision`, `comments`, `reviewed_at` | 战略性审核/争议仲裁记录 |
| `agent_degradation_logs` | `id`, `start_time`, `end_time`, `trigger_reason`, `manual_interventions_count`, `resolved_by`, `resolved_at` | 降级例外条款审计表 |

---

## 4. 物理存储与性能设计

### 4.1 分区策略
- `pay_attendance_records`：`PARTITION BY RANGE (work_date)`，按月自动分区，历史数据自动归档至冷存储。
- `agent_execution_logs`、`audit_logs`：`PARTITION BY RANGE (created_at)`，保留策略：热数据3个月，温数据1年，冷数据依法定年限归档。

### 4.2 索引设计
| 表名 | 索引类型 | 字段/表达式 | 用途 |
|------|----------|-------------|------|
| `base_employees` | B-Tree | `(emp_no)`, `(dept_id, status)` | 主键查询、部门过滤 |
| `rec_candidates` | GIN | `resume_metadata_jsonb` | 简历关键字/技能语义检索 |
| `agent_task_queue` | B-Tree | `(status, scheduled_at)` | 任务调度高效拉取 |
| `agent_execution_logs` | GIN | `cot_verification_jsonb` | 思维链关键字检索与验证 |
| `pay_attendance_records` | BRIN | `work_date` | 大范围时间区间扫描优化 |

### 4.3 存储介质与冷热分离
- **热数据**：NVMe SSD，存放当前周期考勤、薪资、活跃Agent任务。
- **温数据**：SAS HDD，存放历史档案、已完成任务日志。
- **冷数据**：对象存储 + 压缩，存放离职员工档案、过期培训资料、法定归档数据。
- **自动迁移**：通过 `pg_partman` 或定时任务实现分区数据自动下沉。

---

## 5. AI原生与Agent专项设计

### 5.1 思维链验证 (Chain-of-Thought Verification)
- `agent_execution_logs.cot_verification_jsonb` 存储结构化推理过程：
  ```json
  {
    "goal": "计算2026-06薪资",
    "steps": [
      {"action": "fetch_attendance", "input": {"emp_id": "uuid", "cycle": "2026-06"}, "output": {"days": 22}},
      {"action": "calculate_base", "formula": "base * days", "result": 15400.00},
      {"action": "apply_tax", "rule": "progressive_2026", "deduction": 1200.00}
    ],
    "confidence": 0.98,
    "verification_hash": "sha256_..."
  }
  ```
- 人类审核时仅展示摘要与关键节点，支持一键展开完整CoT。

### 5.2 RPA-Agent 会话追踪
- `agent_rpa_sessions` 记录无官方API系统（社保/公积金网站）的自动化操作。
- `step_sequence_jsonb` 记录鼠标点击坐标、键盘输入、DOM快照哈希。
- `screenshot_obj_paths` 存储关键步骤截图，用于争议仲裁与合规审计。

### 5.3 降级例外条款支持
- `agent_degradation_logs` 严格记录 SRS V15 2.2 条款要求的降级场景。
- 字段 `manual_interventions_count` 统计人工介入次数，`trigger_reason` 记录外部API故障/LLM超时等根因。
- 降级期间所有人工操作强制写入 `audit_logs`，并与该降级记录关联。

---

## 6. 安全、合规与审计设计

### 6.1 数据加密与脱敏
- **静态加密**：`id_card_enc`, `phone_enc`, `bank_account_enc` 采用 `AES-256-GCM` 列级加密，密钥由 AWS KMS / HashiCorp Vault 统一管理。
- **动态脱敏**：通过 PostgreSQL `ROW LEVEL SECURITY (RLS)` 与视图层函数实现。非授权角色查询自动返回脱敏值（如 `110***********1234`）。
- **传输加密**：全链路 TLS 1.3，内部服务间 mTLS 双向认证。

### 6.2 权限控制模型
- **RBAC + ABAC 混合**：
  - 角色：`HR_Agent`, `Dept_Manager`, `Payroll_Auditor`, `System_Admin`
  - 属性策略：`emp_id = session.user_id` 或 `dept_id IN (session.user_depts)` 自动过滤数据行。
- **Agent 权限**：每个 Agent 实例绑定独立数据库只读/读写账号，遵循最小权限原则，禁止 `SUPERUSER` 直连。

### 6.3 审计与不可篡改
- `audit_logs` 记录所有 DML 操作、Agent 执行、人工审核、配置变更。
- 关键字段 `operation_hash` 采用链式哈希（当前记录哈希包含上一条记录哈希），支持完整性校验。
- 合规留存：员工档案依法保留至离职后10年，薪资考勤保留3年，审计日志永久归档（WORM存储）。

---

## 7. 数据生命周期与运维策略

| 策略项 | 规范说明 |
|--------|----------|
| **备份策略** | 每日全量 + 每小时增量 + WAL连续归档。跨可用区同步，异地冷备保留30天 |
| **恢复演练** | 季度 RTO/RPO 压测，目标 RTO<5min, RPO≈0 |
| **连接管理** | PgBouncer 连接池，Agent 任务并发连接限制 500，人工审核连接限制 50 |
| **监控指标** | 慢查询(>500ms)、死锁率、表膨胀率、JSONB 写入延迟、CoT 验证失败率、降级触发频次 |
| **数据清理** | 自动化策略清理过期临时文件、失败任务日志、RPA 临时截图，保留策略可配置 |

---

## 8. 附录

### 8.1 核心表 DDL 示例 (PostgreSQL)

```sql
-- AI Agent 执行日志与思维链验证表
CREATE TABLE agent_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES agent_task_queue(id),
    agent_id VARCHAR(64) NOT NULL,
    cot_verification_jsonb JSONB NOT NULL,
    action_trace TEXT,
    result_status VARCHAR(20) NOT NULL CHECK (result_status IN ('SUCCESS', 'FAILED', 'REQUIRES_REVIEW', 'DEGRADED')),
    error_trace TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_exec_task ON agent_execution_logs(task_id);
CREATE INDEX idx_agent_exec_cot ON agent_execution_logs USING GIN(cot_verification_jsonb);
COMMENT ON TABLE agent_execution_logs IS 'Agent执行日志，存储Chain-of-Thought验证数据，供人类战略性审核追溯';

-- 降级例外记录表 (SRS V15 2.2 条款)
CREATE TABLE agent_degradation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    trigger_reason VARCHAR(255) NOT NULL,
    manual_interventions_count INTEGER DEFAULT 0,
    resolved_by VARCHAR(64),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE agent_degradation_logs IS '记录系统降级模式期间的异常、人工介入次数与恢复时间，符合零操作性原则降级例外条款';
```

### 8.2 命名规范
- 表名：`{模块}_{实体}` (小写蛇形，如 `pay_payroll_ledgers`)
- 字段：`{类型/业务}_{含义}` (如 `id_card_enc`, `cot_verification_jsonb`)
- 主键：统一 `id UUID`
- 外键：`{关联表}_id` (如 `emp_id`, `task_id`)
- 审计字段：`created_at`, `updated_at`, `created_by`, `updated_by`
- 软删除：`is_deleted BOOLEAN DEFAULT FALSE`, `deleted_at TIMESTAMPTZ`

### 8.3 状态机枚举定义
- `agent_task_status`: `PENDING`, `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `REQUIRES_REVIEW`, `DEGRADED_MANUAL`
- `hr_employee_status`: `PROSPECT`, `OFFERED`, `ONBOARDING`, `ACTIVE`, `PROBATION`, `RESIGNED`, `TERMINATED`
- `payroll_status`: `DRAFT`, `CALCULATING`, `PENDING_REVIEW`, `APPROVED`, `DISBURSED`

---
**文档结束**  
*设计方：后旺-DATABASE (HouWang) | 版本：DB-Spec V1.0 | 严格对齐 SRS V15 基线*