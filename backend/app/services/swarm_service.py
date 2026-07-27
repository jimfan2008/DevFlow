"""v4.0 - Agent 蜂群管理服务"""
import ast
import logging
import warnings
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
    "pi_coding_agent", "opencode", "hermes", "claude_code",
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


def _parse_py(code: str):
    """ast.parse wrapper - suppress SyntaxWarning for invalid escape sequences in generated code."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(code)


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
            cleaned_line = _re.sub(r'^[。，、：；！？　-〿＀-￯]+', '', line)
            if not found_python:
                if stripped and not stripped.startswith('#'):
                    if _re.search(
                        r'^(import |from |def |class |@|assert |self\.|return |print |pass |if |elif |else:|try:|except |finally:|with |for |while |async |await |raise |yield |lambda |del |global |nonlocal )',
                        stripped,
                    ):
                        found_python = True
                        cleaned.append(cleaned_line)
                    else:
                        if _re.search(r'[一-鿿]', stripped):
                            continue  # 丢弃纯中文行
                        else:
                            cleaned.append(cleaned_line)
                else:
                    cleaned.append(cleaned_line)
            else:
                cleaned.append(cleaned_line)
        result = '\n'.join(cleaned)
        # Step 4: 如果清洗后第1行附近有语法错误，尝试逐行剥离前导废行直到代码合法
        if result.strip():
            try:
                _parse_py(result)
            except SyntaxError as e:
                clines = result.split('\n')
                lineno = getattr(e, "lineno", 1)
                for start in range(max(0, lineno - 2), len(clines)):
                    candidate = '\n'.join(clines[start:]).strip()
                    if not candidate:
                        continue
                    try:
                        _parse_py(candidate)
                        result = candidate
                        break
                    except SyntaxError:
                        continue
        return result.strip()

    @staticmethod
    def validate_code_syntax(code: str, language: str = "python") -> tuple:
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
        return (
            db.query(Agent)
            .filter(Agent.agent_type.in_(agent_types), Agent.status == "online")
            .all()
        )

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
        dependency_codes: list = None,
        dep_graph: dict = None,
        code_plan: str = "",
    ) -> str:
        """为单个源文件构建代码编写 prompt"""
        parts = [
            f"你是{writer_name}，资深程序员，负责编写功能代码中的一个文件。",
        ]
        parts.append(f"\n=== 项目上下文 ===\n核心目标：{core_goal}\n")
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
        parts.append("1. 第一行必须是 Python 代码（import/def/class 开头），不得有任何非代码内容")
        parts.append("2. 禁止在代码前后输出任何文字——包括自我介绍、签名、版本号、路径、分隔线等")
        parts.append("3. 禁止 Markdown 代码块标记（```）。只输出纯文本代码")
        parts.append("4. 禁止使用 todo()、pass（作为占位符）或任何无法执行的伪代码")
        parts.append("5. ⛔ 禁止使用任何文件读写工具！只输出代码文本")
        parts.append("【代码质量要求】")
        parts.append("1. 输出的代码必须能通过 Python 编译——包含所有必要的 import 语句")
        parts.append("2. 必须包含完整的类/函数定义，所有方法必须有实现体")
        parts.append("3. 注释清晰，类型标注完整")
        parts.append("4. 代码符合架构设计的技术选型")
        parts.append("═══════════════════════════════════")

        if last_feedback and attempt > 1:
            parts.append(
                f"\n【⚠️ 上一轮检验未通过】\n"
                f"请根据以下反馈修改当前文件：\n{last_feedback}\n"
            )
        else:
            parts.append("\n按功能描述从零开始生成完整代码。")

        return "\n".join(parts)

    @staticmethod
    def build_code_tester_prompt(
        file_path: str,
        file_description: str,
        code_content: str,
        requirement: str,
        design_doc: str,
        tdd_cases: str,
        tester_name: str,
        attempt: int = 1,
        last_feedback: str = "",
    ) -> str:
        """为单个源文件构建代码检验 prompt"""
        parts = [
            f"你是{tester_name}，资深代码审查员，负责检验功能代码的质量。",
        ]
        parts.append(
            f"\n=== 检验的文件 ===\n"
            f"文件路径：{file_path}\n"
            f"功能描述：{file_description}\n"
        )
        if requirement:
            parts.append(f"\n=== 需求文档 ===\n{requirement[:3000]}")
        if design_doc:
            parts.append(f"\n=== 架构设计 ===\n{design_doc[:3000]}")
        if tdd_cases:
            parts.append(f"\n=== 相关TDD测试用例 ===\n{tdd_cases[:3000]}")
        parts.append("")
        parts.append("═══════════【检验要求】═══════════")
        parts.append("请逐项检验以下代码：")
        parts.append("1. 代码逻辑是否正确，是否满足功能描述")
        parts.append("2. 代码是否符合架构设计的技术选型")
        parts.append("3. 代码是否能编译通过（检查 import、语法）")
        parts.append("4. 代码是否能通过对应的 TDD 测试用例")
        parts.append("5. 代码是否有安全漏洞或性能问题")
        parts.append("")
        parts.append("═══════════【输出格式】═══════════")
        parts.append("你必须输出 JSON 格式的检验结果：")
        parts.append('{"passed": true/false, "score": 0-100, "detail": "具体检验意见...", "issues": ["问题1", "问题2", ...]}')
        parts.append("passed=true 表示全部通过，score<90 视为未通过")
        parts.append("═════════════════════════════════")
        parts.append("")
        parts.append(f"=== 待检验代码 ===\n{code_content[:6000]}")

        if last_feedback and attempt > 1:
            parts.append(
                f"\n【⚠️ 上一轮检验未通过】\n"
                f"请重点检查以下问题是否已修复：\n{last_feedback}\n"
            )
        else:
            parts.append("\n请从零开始全面检验。")

        return "\n".join(parts)