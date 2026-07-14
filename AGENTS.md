# Agent Instructions

This file gives MiMo Code CLI (and any other compatible coding agent)
project-specific guidance. Edit it freely.

## Project overview

<!-- 1–2 sentences about what this project does. -->

## Build, test, lint

<!-- Common commands the agent should know about. -->

## 强制规则：每次修改后必须测试

**每次修改代码后，必须做一次最小验证测试，禁止口头说「改好了」就了事。**
- 后端修改 → 检查 Python 编译（`python3 -c "compile(open(...).read(), 'test', 'exec')"`）或运行相关测试
- 前端修改 → 检查 `npm run build` 或 `npx vite build` 是否通过
- 外部脚本修改 → 检查语法（`python3 -c "ast.parse(open(...).read())"`）或 `--help` 运行
- 配置文件修改 → 检查 YAML/JSON 格式是否正确
- 若验证失败 → 继续修，直到通过为止
- 修改完成的通知中附上验证结果

## Conventions

**必须用中文回复。** 所有与用户的交流、注释、错误信息、文档等一律使用中文。英文代码标识符（变量名、函数名等）保持原样，但注释和沟通必须用中文。

## Bug 修复规则（强制）

**修复 BUG 前必须找到根因，禁止猜测式修改。**

流程：
1. **收集证据** — 复现路径、日志、错误堆栈、用户描述的具体现象
2. **定位根因** — 沿着数据流/调用链逐层追踪，直到找到确凿的因果关系
3. **确认根因** — 用日志或测试证明「就是这个原因」
4. **最小修改** — 只改根因涉及的代码，不改无关区域
5. **验证** — 修改后必须证明问题已修复（测试通过或日志显示正常）

禁止行为：
- 不做分析就直接改代码
- 凭经验/直觉猜原因，猜中就算了，猜不中就反复试
- 一次性改多处无关代码试图「覆盖所有可能」
- 不改根因，只改表面现象

每次修复后，在注释或 commit message 中写明根因。

**修复后必须主动验证，禁止口头说「改好了」就了事。**
- 有测试 → 跑相关测试，确认全部通过
- 无测试但可手动验证 → 跑一次最小验证命令（编译检查、lint、启动检查等）
- 前端修改 → 检查编译/类型检查是否通过
- 后端修改 → 检查编译/导入是否正常、相关测试是否通过
- 若验证失败 → 继续修，直到通过为止
- 修改完成的通知中附上验证结果（如「测试X通过」或「编译OK」）


## Git rules

**禁止随意提交代码到git。执行任何git代码库相关的命令（包括但不限于 git add、git commit、git push、git reset、git stash 等），必须事先征得我的同意。**

## Hourong（后荣）检验流程规范（强制）

**所有 hourong 的 QA 检验必须通过子 agent 完成，禁止直接调用 hourong 模型。**

流程：
1. **委托子 agent** — 使用 `delegate_task(profile_name="hourong")` 生成检验子 agent
2. **子 agent 检验** — 子 agent 读取检验 prompt，执行 QA 检查
3. **生成标准报告** — 子 agent 输出标准 JSON 格式检验报告（格式见下）
4. **保存到工作空间** — 报告保存到 `{project_docs_dir}/qa_reports/`
5. **返回文件路径** — 子 agent 只返回报告文件的绝对路径，不返回报告内容
6. **主 agent 读取** — hourong 主流程从文件路径读取报告，继续后续处理

### 标准检验报告 JSON 格式

```json
{
  "report_type": "hourong_qa_inspection",
  "version": "1.0",
  "dimension_key": "completeness",
  "dimension_label": "完整性",
  "score": 95,
  "passed": true,
  "summary": "总体评价...",
  "defect_chapters": [
    {
      "shard_file": "/完整/路径/分片文件.md",
      "chapter_key": "functional",
      "defect_count": 2,
      "defects": [
        {
          "reason": "不合格的具体原因",
          "evidence": "[chapter:functional] 证据描述",
          "fix_direction": "如何修改"
        }
      ]
    }
  ],
  "generated_at": "2026-07-07T12:00:00"
}
```

### delegate_task 扩展

`delegate_task` 增加 `profile_name` 参数（默认 `"houxing"`），hourong 检验时传入 `profile_name="hourong"`。

## Out of scope

<!-- Areas the agent should not modify without explicit permission. -->
