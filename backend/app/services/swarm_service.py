"""v4.0 - Agent 蜂群管理服务"""
import ast, logging, warnings


def _parse_py(code: str):
    """ast.parse wrapper - suppress SyntaxWarning for invalid escape sequences in generated code."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(code)


from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.models.agent import Agent

logger = logging.getLogger(__name__)

SUPPORTED_SWARM_AGENTS = [
    "claude_code", "opencode",
    "codearts", "trae", "hermes_sub_agent",
    "pi_coding_agent", "reasonix", "houfa",
    "aider-chat", "goose",
]

WRITER_AGENT_TYPES = [
    "pi_coding_agent", "opencode", "houfa", "claude_code",
    "codearts", "trae", "codebuddy", "reasonix",
    "goose",
]

TESTER_AGENT_TYPES = [
    "reasonix", "claude_code", "hermes",
    "goose",
]

WRITER_PREFERENCE = ["pi_coding_agent", "opencode"]
TESTER_PREFERENCE = ["reasonix", "claude_code"]

EXCLUDED_WRITER_NAMES = {
    "haimei", "houxing", "houwang", "houda",
    "houfu", "hougui", "hourong", "houhua",
}
EXCLUDED_TESTER_NAMES = {
    "haimei", "houxing", "houwang", "houda",
    "houfu", "hougui", "houfa", "houhua",
}

MANAGER_PURPOSE_MAP = {
    "houfa": "code_writing",
    "houda": "test_execution",
}


class SwarmService:
    def __init__(self):
        self._swarms: Dict[int, Dict[str, Any]] = {}
        self._next_swarm_id = 1
        self._assignments: Dict[int, List[Dict[str, Any]]] = {}

    def create_swarm(self, project_id: str, name: str, purpose: str,
                     step_number: int, manager_role: str) -> Dict[str, Any]:
        expected_purpose = MANAGER_PURPOSE_MAP.get(manager_role)
        if expected_purpose is None:
            raise ValueError(f"无效的管理者角色: {manager_role}")
        if manager_role == "houfa" and purpose != "code_writing":
            raise ValueError("后发只能建立代码编写蜂群")
        if manager_role == "houda" and purpose != "test_execution":
            raise ValueError("后达只能建立测试蜂群")

        swarm = {
            "id": self._next_swarm_id,
            "project_id": project_id,
            "name": name,
            "purpose": purpose,
            "step_number": step_number,
            "manager_role": manager_role,
            "members": [],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "disbanded_at": None,
        }
        self._swarms[self._next_swarm_id] = swarm
        self._assignments[self._next_swarm_id] = []
        self._next_swarm_id += 1
        return dict(swarm)

    def add_member(self, swarm_id: int, agent_type: str, agent_id: str) -> Dict[str, Any]:
        if agent_type not in SUPPORTED_SWARM_AGENTS:
            raise ValueError(f"不支持的Agent类型: {agent_type}")

        swarm = self._swarms.get(swarm_id)
        if swarm is None:
            raise ValueError(f"蜂群 {swarm_id} 不存在")

        member = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }
        swarm["members"].append(member)
        return dict(swarm)

    def remove_member(self, swarm_id: int, agent_id: str) -> Dict[str, Any]:
        swarm = self._swarms.get(swarm_id)
        if swarm is None:
            raise ValueError(f"蜂群 {swarm_id} 不存在")

        swarm["members"] = [m for m in swarm["members"] if m["agent_id"] != agent_id]
        return dict(swarm)

    def dispatch_tasks(self, swarm_id: int, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        swarm = self._swarms.get(swarm_id)
        if swarm is None:
            raise ValueError(f"蜂群 {swarm_id} 不存在")

        members = swarm["members"]
        if not members:
            raise ValueError("蜂群没有成员，无法分发任务")

        assignments = []
        round_robin_index = 0

        for task in tasks:
            task_deps = task.get("depends_on", [])

            if task_deps:
                dep_assignments = [a for a in assignments if a["task_id"] in task_deps]
                used_agents = {a["assigned_agent_id"] for a in dep_assignments}
                available = [m for m in members if m["agent_id"] not in used_agents]
                if not available:
                    available = members
                chosen = available[round_robin_index % len(available)]
            else:
                chosen = members[round_robin_index % len(members)]

            assignment = {
                "swarm_id": swarm_id,
                "task_id": task["task_id"],
                "task_name": task.get("name", ""),
                "assigned_agent_id": chosen["agent_id"],
                "assigned_agent_type": chosen["agent_type"],
                "status": "assigned",
                "assigned_at": datetime.now(timezone.utc).isoformat(),
            }
            assignments.append(assignment)
            round_robin_index += 1

        self._assignments[swarm_id].extend(assignments)
        return assignments

    def get_progress(self, swarm_id: int) -> Dict[str, Any]:
        swarm = self._swarms.get(swarm_id)
        if swarm is None:
            raise ValueError(f"蜂群 {swarm_id} 不存在")

        assignments = self._assignments.get(swarm_id, [])
        total = len(assignments)
        completed = sum(1 for a in assignments if a["status"] == "completed")

        return {
            "swarm_id": swarm_id,
            "total_tasks": total,
            "completed_tasks": completed,
            "pending_tasks": total - completed,
            "progress_percent": (completed / total * 100) if total > 0 else 0,
        }

    def disband_swarm(self, swarm_id: int) -> Dict[str, Any]:
        swarm = self._swarms.get(swarm_id)
        if swarm is None:
            raise ValueError(f"蜂群 {swarm_id} 不存在")

        swarm["status"] = "disbanded"
        swarm["disbanded_at"] = datetime.now(timezone.utc).isoformat()
        return dict(swarm)

    def get_swarm(self, swarm_id: int) -> Optional[Dict[str, Any]]:
        swarm = self._swarms.get(swarm_id)
        if swarm is None:
            return None
        result = dict(swarm)
        result["assignments"] = self._assignments.get(swarm_id, [])
        return result

    # ════════════════════════════════════════════
    # 代码质量保障方法（确保代码可编译、可执行）
    # ════════════════════════════════════════════

    @staticmethod
    def build_writer_prompt(
        sname: str,
        sdesc: str,
        sacc: str,
        writer_name: str,
        attempt: int = 1,
        last_feedback: str = "",
        agent_type: str = "",
        existing_code: str = "",
        file_path: str = "",
        report_file_path: str = "",
    ) -> str:
        parts = [
            f"你是{writer_name}，负责编写可独立运行的 TDD 测试用例代码。",
        ]
        parts.append(
            f"\n=== 测试用例 ===\n名称：{sname}\n描述：{sdesc}\n验收标准：{sacc}"
        )
        parts.append("")

        parts.append("═══════════【输出铁律】═══════════")
        parts.append("你必须严格按以下格式输出，任何违反将导致直接被拒绝：")
        parts.append("")
        parts.append("【格式要求】")
        parts.append("1. 第一行必须是 Python 代码（import/def/class 开头），不得有任何非代码内容")
        parts.append("2. 禁止在代码前后输出任何文字——包括自我介绍、签名、版本号、路径、分隔线等")
        parts.append("3. 禁止 Markdown 代码块标记（```）。只输出纯文本代码")
        parts.append("4. 禁止使用 todo()、pass（作为占位符）或任何无法执行的伪代码")
        parts.append("5. ⛔ 禁止使用任何文件读写工具！只输出代码文本，不要尝试用工具写文件或读文件")
        parts.append("")
        parts.append("【代码质量要求】")
        parts.append("1. 输出的代码必须能通过 Python 编译——包含所有必要的 import 语句，无缺失依赖")
        parts.append("2. 必须包含完整的类/函数定义，所有方法必须有实现体")
        parts.append("3. 使用 pytest 框架编写，断言清晰明确")
        parts.append("4. 测试数据在代码内自包含（mock/fixture 内联），不依赖外部文件")
        parts.append("")
        parts.append("【自我检查——在你输出之前，逐项核对】")
        parts.append("□ 第1行是 import/def/class 吗？不是 → 删掉前导行")
        parts.append("□ 代码里有没有你自身的签名/版本号/路径信息？有 → 删掉")
        parts.append("□ 有没有 ``` 围栏？有 → 删掉围栏，只保留中间的代码")
        parts.append("□ 有没有 TODO/pass 占位符？有 → 替换为完整实现")
        parts.append("□ import 是否完整？缺少 → 补上")
        parts.append("==================================")

        if last_feedback:
            parts.append(
                f"\n【⚠️ 必须在当前代码基础上修改】\n"
                f"上一轮测试未通过，以下为测试报告原文。你必须逐条修复报告中的每项问题：\n"
                f"{last_feedback}\n"
            )
            if existing_code:
                parts.append(
                    f"=== 当前代码（必须在以下代码基础上修改，禁止重写）===\n"
                    f"{existing_code}\n\n"
                    f"修改规则：\n"
                    f"1. 保留现有代码的整体结构和逻辑\n"
                    f"2. 只修改报告中指出的问题所在行\n"
                    f"3. 如果报告指出缺少某个函数/类，才添加新的函数/类\n"
                    f"4. 输出修改后的完整代码文件（包含所有现有函数和新增修改）"
                )
            else:
                parts.append(
                    f"\n注意：仅修复报告中指出的问题，不要改动无关代码。修复后的代码必须可运行！"
                )
        else:
            parts.append("\n7. 首次编写，按验收标准从零开始生成完整代码")

        return "\n".join(parts)

    @staticmethod
    def build_tester_prompt(
        sname: str,
        saved_code: str,
        tester_name: str,
        previous_report: str = "",
        file_path: str = "",
        report_file_path: str = "",
    ) -> str:
        header = (
            f"你{tester_name}，负责检验 TDD 测试代码的质量。\n\n"
            f"==========【输出格式铁律 - 必须执行】==========\n"
            f"你的输出的**前5行内**必须包含一行以下格式（二选一），不得缺失：\n"
            f"  ✅ 判定结果：通过；总分：95分\n"
            f"  ❌ 判定结果：未通过；总分：60分\n"
            f"❗ 「判定结果」只能是「通过」或「未通过」，「总分」是0~100的整数\n"
            f"❗ 输出完成前，请自行检查前5行内是否包含上述格式行。如果没有，在靠近顶部的地方补上。\n"
            f"  任何缺少此格式行的输出都将被系统自动拒绝。\n"
            f"从判定结果行的下一行开始，输出检验详情。\n"
            f"==============================================\n\n"
            f"=== 测试用例 ===\n名称：{sname}\n"
        )
        if previous_report:
            body = (
                f"【这是第2+轮收敛检验】\n"
                f"上一轮检验报告指出的问题如下，请逐项检查这些问题是否已被修复：\n"
                f"{previous_report}\n\n"
                f"收敛检验规则（必须遵守）：\n"
                f"1. 只检查上一轮报告中指出的问题，不要扩大检查范围\n"
                f"2. 如果全部问题已修复，判定「通过」\n"
                f"3. 如果有问题仍未修复，判定「未通过」并明确指出哪些问题依然存在\n"
                f"4. 禁止对代码进行全新全面检验，只做收敛检验\n"
                f"5. 禁止检查报告中未提及的新问题\n\n"
            )
        else:
            body = (
                f"请执行四项检验并按格式输出：\n"
                f"1.【语法正确性】——代码能否通过 Python 编译？有无语法错误？\n"
                f"2.【逻辑正确性】——测试逻辑是否完整覆盖验收标准？\n"
                f"3.【边界覆盖】——是否有边界值/异常场景测试？\n"
                f"4.【可独立运行】——import 是否完整？有无缺失依赖？\n\n"
            )
        footer = (
            f"=== 待检验代码（仅基于以下内容判断，禁止读取外部文件）===\n"
            f"{saved_code}\n\n"
        )
        return header + body + footer

    @staticmethod
    def clean_generated_code(raw: str) -> str:
        """清洗 Agent 生成的代码：去 Markdown 围栏、去中文裸文本、去行首中文标点"""
        if not raw or not raw.strip():
            return raw

        import re as _re

                
        code = raw.strip()

        # Step 1: 提取第一个 ``` 代码块内的内容（忽略围栏外的任何文字）
        block = _re.search(r'```\w*\n(.*?)\n```', code, _re.DOTALL)
        if block:
            code = block.group(1)

        # Step 2: 去掉可能残余的 Markdown 围栏
        code = _re.sub(r'^```\w*\n', '', code)
        code = _re.sub(r'\n```\s*$', '', code)

        # Step 3: 分行处理，滤掉纯中文/无 Python 关键字的废行
        lines = code.split('\n')
        cleaned = []
        found_python = False
        for line in lines:
            stripped = line.strip()
            cleaned_line = _re.sub(r'^[。，、：；！？\u3000-\u303f\uff00-\uffef]+', '', line)
            if not found_python:
                if stripped and not stripped.startswith('#'):
                    if _re.search(
                        r'^(import |from |def |class |@|assert |self\.|return |print |pass |if |elif |else:|try:|except |finally:|with |for |while |async |await |raise |yield |lambda |del |global |nonlocal )',
                        stripped,
                    ):
                        found_python = True
                        cleaned.append(cleaned_line)
                    else:
                        if _re.search(r'[\u4e00-\u9fff]', stripped):
                            continue
                        else:
                            cleaned.append(cleaned_line)
                else:
                    cleaned.append(cleaned_line)
            else:
                cleaned.append(cleaned_line)

        result = '\n'.join(cleaned)

        # Step 4: 如果清洗后第1行附近有语法错误（如 agent 输出含非代码元数据），
        #          尝试逐行剥离前导废行直到代码合法
        if result.strip():
            try:
                _parse_py(result)
            except SyntaxError as e:
                clines = result.split('\n')
                lineno = getattr(e, "lineno", 1)
                # 扩大剥离范围：从前导错误行往后扫描直到找到合法 Python 代码
                # 也处理 agent 输出以签名/路径/模型名开头的情况（如 "AtomCode Qwen3.6 ..."）
                for start in range(max(0, lineno - 2), len(clines)):
                    candidate = '\n'.join(clines[start:]).strip()
                    if not candidate:
                        continue
                    try:
                        _parse_py(candidate)
                        result = candidate
                        logger.info(f"[clean_generated_code] 剥离前导 {start} 行后代码合法")
                        break
                    except SyntaxError:
                        continue
                # 如果剥离到很后仍不合法，尝试检测并移除非 Python 的第一行
                if result.strip():
                    try:
                        _parse_py(result)
                    except SyntaxError as e2:
                        # 最后尝试：直接查找第一个 import/from/def/class 行
                        import re as _re2
                        for start in range(len(clines)):
                            candidate = '\n'.join(clines[start:]).strip()
                            if not candidate:
                                continue
                            if _re2.search(r'^(import |from |def |class |async def )', candidate):
                                # ⚠️ 不能递归调 clean_generated_code — 失败的代码会再次进入此分支导致无限递归爆栈
                                # 直接取 candidate（已是从合法 Python 关键字开始的代码）并尝试解析
                                try:
                                    _parse_py(candidate)
                                    result = candidate
                                    break
                                except SyntaxError:
                                    # 解析不过也认了，返回截取后的代码让上层处理
                                    result = candidate
                                    break

        # Step 5: 处理前导/后置未闭合字符串字面量
        #         策略：先剥离前导行直到合法，如果仍不合法，同时剥离前导和后置裸引号行
        if result.strip():
            try:
                _parse_py(result)
            except SyntaxError:
                import re as _re5
                clines5 = result.split('\n')
                found_valid = False
                # Phase A: 逐行剥离前导行
                for skip in range(1, min(10, len(clines5))):
                    candidate = '\n'.join(clines5[skip:]).strip()
                    if not candidate:
                        continue
                    try:
                        _parse_py(candidate)
                        result = candidate
                        logger.info(f"[clean_generated_code] Step5A: 剥离前导 {skip} 行后代码合法")
                        found_valid = True
                        break
                    except SyntaxError:
                        continue
                # Phase B: 若 A 失败，从两端剥离裸引号/空行行
                if not found_valid:
                    clines5b = list(clines5)
                    # 从尾端剥离：连续的空行或纯引号行
                    while clines5b and (not clines5b[-1].strip() or _re5.fullmatch(r'[\s\'"]+', clines5b[-1])):
                        clines5b.pop()
                    # 从前端剥离：连续的空行或纯引号行
                    while clines5b and (not clines5b[0].strip() or _re5.fullmatch(r'[\s\'"]+', clines5b[0])):
                        clines5b.pop(0)
                    # 再逐段尝试
                    for start in range(len(clines5b)):
                        candidate = '\n'.join(clines5b[start:]).strip()
                        if not candidate:
                            continue
                        try:
                            _parse_py(candidate)
                            result = candidate
                            logger.info(f"[clean_generated_code] Step5B: 两端剥离+前导 {start} 行后代码合法")
                            found_valid = True
                            break
                        except SyntaxError:
                            continue
                # Phase C: 若 B 失败，直接查找第一个 import/from/def/class/async def 行（含尾端清理）
                if not found_valid:
                    for start in range(len(clines5)):
                        if _re5.search(r'^(import |from |def |class |async def )', clines5[start].lstrip()):
                            # 找到最后一个 Python 块结束位置（遇到下一个 def/class 或文件末尾）
                            end = len(clines5)
                            for ei in range(start + 1, len(clines5)):
                                if _re5.search(r'^(def |class |async def )', clines5[ei].lstrip()):
                                    end = ei
                                    break
                            candidate = '\n'.join(clines5[start:end]).strip()
                            if candidate:
                                try:
                                    _parse_py(candidate)
                                    result = candidate
                                    logger.info(f"[clean_generated_code] Step5C: 截取 import-block [{start}:{end}] 后代码合法")
                                    found_valid = True
                                    break
                                except SyntaxError:
                                    continue
                # Phase D: 若 C 失败，移除所有裸引号行（""" 或 ''' 单独占行的行）再尝试
                if not found_valid:
                    clines5d = [l for l in clines5 if not _re5.fullmatch(r'\s*"""\s*', l) and not _re5.fullmatch(r"\s*'''\s*", l)]
                    if len(clines5d) < len(clines5):
                        for start in range(len(clines5d)):
                            candidate = '\n'.join(clines5d[start:]).strip()
                            if not candidate:
                                continue
                            try:
                                _parse_py(candidate)
                                result = candidate
                                logger.info(f"[clean_generated_code] Step5D: 移除裸引号行+前导 {start} 行后代码合法")
                                found_valid = True
                                break
                            except SyntaxError:
                                continue

        return result

    @staticmethod
    def validate_code_syntax(code: str, language: str = "python") -> tuple[bool, str]:
        """验证代码语法，返回 (是否通过, 错误信息)"""
        if not code or not code.strip():
            return False, "代码为空"
        if language == "python":
            try:
                with warnings.catch_warnings():
                                _parse_py(code)
                return True, ""
            except SyntaxError as e:
                lineno = getattr(e, "lineno", "?")
                msg = f"语法错误 (第{lineno}行): {e.msg}"
                logger.warning(f"[validate_code_syntax] {msg}")
                return False, msg
        return True, ""

    @staticmethod
    def get_online_agents_by_types(db, agent_types: list) -> list:
        from app.models.agent import Agent
        return (
            db.query(Agent)
            .filter(Agent.agent_type.in_(agent_types), Agent.status == "online")
            .all()
        )

    @staticmethod
    def get_online_writer_agents(db) -> list:
        agents = SwarmService.get_online_agents_by_types(db, WRITER_AGENT_TYPES)
        return [a for a in agents if a.name not in EXCLUDED_WRITER_NAMES]

    @staticmethod
    def get_online_tester_agents(db) -> list:
        agents = SwarmService.get_online_agents_by_types(db, TESTER_AGENT_TYPES)
        return [a for a in agents if a.name not in EXCLUDED_TESTER_NAMES]

    @staticmethod
    def get_preferred_writer_agents(db) -> list:
        agents = SwarmService.get_online_agents_by_types(db, WRITER_AGENT_TYPES)
        agents = [a for a in agents if a.name not in EXCLUDED_WRITER_NAMES]
        def _sort_key(a):
            try:
                return WRITER_PREFERENCE.index(a.agent_type)
            except ValueError:
                return len(WRITER_PREFERENCE)
        agents.sort(key=_sort_key)
        return agents

    @staticmethod
    def get_preferred_tester_agents(db) -> list:
        agents = SwarmService.get_online_agents_by_types(db, TESTER_AGENT_TYPES)
        agents = [a for a in agents if a.name not in EXCLUDED_TESTER_NAMES]
        def _sort_key(a):
            try:
                return TESTER_PREFERENCE.index(a.agent_type)
            except ValueError:
                return len(TESTER_PREFERENCE)
        agents.sort(key=_sort_key)
        return agents

    @staticmethod
    def build_code_writer_prompt(
        file_path: str,
        file_description: str,
        requirement: str,
        design_doc: str,
        tdd_cases: str,
        core_goal: str,
        writer_name: str,
        attempt: int = 1,
        last_feedback: str = "",
        existing_code: str = "",
        dependency_codes: list = None,
        dep_graph: dict = None,
        code_plan: str = "",
    ) -> str:
        """Build a prompt for generating a single source code file."""
        parts = [
            f"你是{writer_name}，资深程序员，负责编写功能代码中的一个文件。",
        ]
        parts.append(
            f"\n=== 项目上下文 ===\n"
            f"核心目标：{core_goal}\n"
        )
        if requirement:
            parts.append(f"\n=== 需求文档 ===\n{requirement[:8000]}")
        if design_doc:
            parts.append(f"\n=== 架构设计 ===\n{design_doc[:6000]}")
        if tdd_cases:
            parts.append(f"\n=== TDD测试用例 ===\n{tdd_cases[:6000]}")
        if code_plan:
            parts.append(f"\n=== 代码编写计划 ===\n{str(code_plan)[:4000]}")
        if dep_graph:
            parts.append(f"\n=== 依赖图 ===\n{str(dep_graph)[:2000]}")

        # 依赖文件代码
        if dependency_codes:
            dep_section = "\n=== 已生成的相关文件代码（依赖前置） ===\n"
            for dep_path, dep_code in dependency_codes:
                dep_section += f"--- {dep_path} ---\n{dep_code[:3000]}\n\n"
            parts.append(dep_section)

        parts.append(
            f"\n=== 当前文件 ===\n"
            f"文件路径：{file_path}\n"
            f"功能描述：{file_description}\n"
        )

        parts.append("")
        parts.append("═══════════【输出铁律】═══════════")
        parts.append("你必须严格按以下格式输出，任何违反将导致直接被拒绝：")
        parts.append("")
        parts.append("【格式要求】")
        parts.append("1. 第一行必须是 Python 代码（import/def/class 开头），不得有任何非代码内容")
        parts.append("2. 禁止在代码前后输出任何文字——包括自我介绍、签名、版本号、路径、分隔线等")
        parts.append("3. 禁止 Markdown 代码块标记（```）。只输出纯文本代码")
        parts.append("4. 禁止使用 todo()、pass（作为占位符）或任何无法执行的伪代码")
        parts.append("5. ⛔ 禁止使用任何文件读写工具！只输出代码文本，不要尝试用工具写文件或读文件")
        parts.append("")
        parts.append("【代码质量要求】")
        parts.append("1. 输出的代码必须能通过 Python 编译——包含所有必要的 import 语句，无缺失依赖")
        parts.append("2. 必须包含完整的类/函数定义，所有方法必须有实现体")
        parts.append("3. 注释清晰，类型标注完整")
        parts.append("4. 代码符合架构设计的技术选型")
        parts.append("")
        parts.append("【自我检查——在你输出之前，逐项核对】")
        parts.append("□ 第1行是 import/def/class 吗？不是 → 删掉前导行")
        parts.append("□ 代码里有没有你自身的签名/版本号/路径信息？有 → 删掉")
        parts.append("□ 有没有 ``` 围栏？有 → 删掉围栏，只保留中间的代码")
        parts.append("□ 有没有 TODO/pass 占位符？有 → 替换为完整实现")
        parts.append("□ import 是否完整？缺少 → 补上")
        parts.append("==================================")

        if last_feedback and attempt > 1:
            parts.append(
                f"\n【⚠️ 上一轮检验未通过】\n"
                f"请根据以下反馈修改当前文件：\n"
                f"{last_feedback}\n"
            )
            if existing_code:
                parts.append(
                    f"=== 当前代码（在此基础修改）===\n"
                    f"{existing_code}\n\n"
                    f"只修改报告中指出的问题，不改动无关代码。"
                )
        else:
            parts.append("\n按功能描述从零开始生成完整代码。")

        return "\n".join(parts)
