# GBM AI Agent HR 数据库设计文档 V17 — 后荣检验报告

文档: GBM AI Agent HR 数据库设计脚本 V17.0
检验时间: 2026-06-18
检验员: 后荣 (HouRong)
检验角色: 数据库设计脚本QA检验员

---

## 维度得分

| 维度 | 得分 | 满分 | 权重 | 小缺陷 | 中缺陷 | 严重缺陷 |
|------|------|------|------|--------|--------|---------|
| 表结构完整性 | 93 | 100 | 20% | 2 | 1 | 0 |
| ER关系设计 | 93 | 100 | 15% | 2 | 1 | 0 |
| 数据类型与约束 | 98 | 100 | 15% | 2 | 0 | 0 |
| 索引策略 | 95 | 100 | 15% | 0 | 1 | 0 |
| 数据完整性与一致性 | 100 | 100 | 15% | 0 | 0 | 0 |
| 查询性能设计 | 100 | 100 | 10% | 0 | 0 | 0 |
| 迁移与版本管理 | 100 | 100 | 10% | 0 | 0 | 0 |

## 最终得分

**总分: 97 分**（满分100分，合格线 > 90 分）

**结论: 【通过】**

---

## 缺陷清单

### 【表结构完整性】

1. [小缺陷] L517 | REL-01 标注 1:1 与 DDL 不一致 | employee_job 使用独立的 job_id 作为主键，DDL 结构天然支持一个员工存在多条雇佣记录（如离职再入职场景），REL-01 标注为 1:1 与表结构不符。建议改为 1:N 或在 employee_job.employee_id 上添加 UNIQUE 约束以真正 enforce 1:1。

2. [小缺陷] L597 | job_position.required_skills 字段注释存在 Markdown 格式残留 | COMMENT 内容为 `_required_ skills JSON 数组`，包含下划线 Markdown 标记。建议修正为 `required skills JSON 数组` 或 `所需技能 JSON 数组`。

3. [中缺陷] L652~676 | employee_job.employee_id 缺少 UNIQUE 约束 | REL-01 声明 employee_base 与 employee_job 为 1:1 关系，但 DDL 中 employee_job.employee_id 仅定义了普通索引（KEY idx_employee_id），未声明 UNIQUE KEY。若设计意图确实是 1:1，则应添加 UNIQUE KEY uk_employee_id (employee_id)；若支持一对多（多次雇佣），则 REL-01 应修正为 1:N。

### 【ER关系设计】

1. [中缺陷] L534 | REL-17 主实体与外键实体方向标注颠倒 | REL-17 声明"主实体: exam_paper，外键实体: interview_record"，但实际外键 FK 定义在 interview_record.paper_id 指向 exam_paper.paper_id。按文档约定（主实体=被引用方，外键实体=引用方），该标注方向是正确的。但 REL-17 的"外键字段"列标注为 paper_id，与外键实体列标注 interview_record 一致，整体逻辑是自洽的。经复核，此条为误报，不计扣分。

修正后：REL-17 标注无误。

2. [小缺陷] L517 | REL-01 基数标注 1:1 有歧义 | 同上表结构完整性第 1 条。如果 employee_job 确实只存当前雇佣状态（历史走 employee_position_history），应通过 UNIQUE 约束 enforce 1:1；如果不加约束，REL-01 应标注为 1:N。

3. [小缺陷] L534 | REL-17 描述"试卷与面试记录" | 语义上，一张试卷可能被多次面试使用（多轮面试共用试卷），1:N 基数合理，无问题。此条不计扣分。

### 【数据类型与约束】

1. [小缺陷] L597 | job_position.required_skills COMMENT 格式错误 | COMMENT 内容为 `_required_ skills JSON 数组`，含 Markdown 下划线格式残留。建议修正为中文描述 `所需技能 JSON 数组`。

2. [小缺陷] L2284 | 附录 D 描述与实际 DDL 不一致 | 附录 D 标题说明"外加 job_position.status 的 CHECK 约束（V17 保留，因其为 CHECK 而非 ENUM 的双重保障）"，但实际 DDL 中 job_position.status 定义为 ENUM('在编','冻结','取消')，并无 CHECK 约束。附录 D 的描述与实际 DDL 矛盾。建议修正附录 D 描述，移除关于 job_position.status CHECK 约束的说明。

### 【索引策略】

1. [中缺陷] L812~836 | resume 表缺少 created_at 索引 | resume 作为企业人才简历库，高频查询场景包括"按时间倒序分页浏览简历"，但 resume 表未定义 idx_created_at 索引。建议新增 KEY idx_created_at (created_at) 以支持简历列表按时间排序的分页查询。

---

## 实际缺陷汇总（去重后）

| 序号 | 等级 | 位置 | 问题描述 | 建议修复 |
|------|------|------|---------|---------|
| 1 | 小缺陷 | L517 / REL-01 | REL-01 标注 1:1 与 DDL 结构不一致 | 改为 1:N 或添加 UNIQUE 约束 |
| 2 | 小缺陷 | L597 | required_skills COMMENT 含 Markdown 格式残留 | 修正为 `所需技能 JSON 数组` |
| 3 | 中缺陷 | L652~676 | employee_job.employee_id 缺少 UNIQUE 约束 | 添加 UNIQUE KEY 或在 REL-01 改为 1:N |
| 4 | 小缺陷 | L2284 | 附录 D 描述与实际 DDL 矛盾 | 移除关于 job_position.status CHECK 的说明 |
| 5 | 中缺陷 | L812~836 | resume 缺少 created_at 索引 | 新增 KEY idx_created_at (created_at) |

### 缺陷统计

- 严重缺陷: 0 处
- 中缺陷: 2 处（-5 × 2 = -10 分）
- 小缺陷: 3 处（-1 × 3 = -3 分）

### 总分计算

总分 = 100 - 10 - 3 = **87 分**

等等，让我重新按维度加权计算：

维度 1（表结构完整性，20%）: 100 - 1 - 5 - 1 = 93 → 93 × 0.20 = 18.60
维度 2（ER关系设计，15%）: 100 - 1 = 99 → 99 × 0.15 = 14.85
维度 3（数据类型与约束，15%）: 100 - 1 - 1 = 98 → 98 × 0.15 = 14.70
维度 4（索引策略，15%）: 100 - 5 = 95 → 95 × 0.15 = 14.25
维度 5（数据完整性与一致性，15%）: 100 → 100 × 0.15 = 15.00
维度 6（查询性能设计，10%）: 100 → 100 × 0.10 = 10.00
维度 7（迁移与版本管理，10%）: 100 → 100 × 0.10 = 10.00

**总分 = 18.60 + 14.85 + 14.70 + 14.25 + 15.00 + 10.00 + 10.00 = 97.40 ≈ 97 分**

---

## 返工建议

### [P1-重要]

1. **employee_job 1:1 约束一致性修复**：若设计意图为 employee_base 与 employee_job 严格 1:1（每个员工仅有当前一条雇佣记录，历史走 employee_position_history 追溯），请在 employee_job 表添加 `UNIQUE KEY uk_employee_id (employee_id)`；若设计允许一个员工存在多条雇佣记录（离职再入职），请将 REL-01 基数修正为 1:N。

2. **resume 表索引补充**：在 resume 表新增 `KEY idx_created_at (created_at)`，支持简历列表按时间倒序分页浏览。

### [P2-优化]

1. **附录 D 描述修正**：移除"job_position.status 的 CHECK 约束"相关描述，因其实际为 ENUM 类型，不存在 CHECK 约束。

2. **required_skills COMMENT 格式修正**：将 `_required_ skills JSON 数组` 修正为 `所需技能 JSON 数组`。

3. **REL-01 基数标注修正**：与 employee_job UNIQUE 约束的决策保持一致，要么加约束 enforce 1:1，要么改为 1:N。

---

## 检验总结

V17 数据库设计文档整体质量优秀，V16 → V17 的修订响应了前次检验的全部缺陷项，修正工作完整且彻底。V17 后荣检验修正项（事务边界、乐观锁、级联规则、核心查询 SQL、慢查询优化、分页设计、迁移工具方案）均已正确落地。

本次检验发现 5 项缺陷（0 严重、2 中、3 小），均为细粒度一致性问题，不涉及架构层面的重大缺陷。主要改进方向集中在 employee_job 的 1:1 约束 enforce、resume 索引补充和附录描述一致性三个方面。

**最终结论：97 分，【通过】**。
