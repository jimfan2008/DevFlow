# Agent Instructions

This file gives MiMo Code CLI (and any other compatible coding agent)
project-specific guidance. Edit it freely.

## Project overview

<!-- 1–2 sentences about what this project does. -->

## Build, test, lint

<!-- Common commands the agent should know about. -->

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

## Out of scope

<!-- Areas the agent should not modify without explicit permission. -->
