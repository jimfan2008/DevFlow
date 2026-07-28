"""v4.0 - Agent 蜂群管理服务"""
import ast
import logging
import os
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
    "claude_code", "codebuddy", "opencode", "hermes",
    "pi_coding_agent", "goose", "reasonix",
    "aider-chat", "qoder_cli",
]

TESTER_AGENT_TYPES = [
    "claude_code", "codebuddy", "opencode", "hermes",
    "pi_coding_agent", "goose", "reasonix",
    "aider-chat", "qoder_cli",
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
        # Step 5: 如果仍然语法错误，强制从原始文本提取后兜底
        if result.strip():
            try:
                _parse_py(result)
            except SyntaxError:
                # 尝试提取 ```python ... ``` 块
                py_block = _re.search(r'```python\s*\n(.*?)\n```', raw, _re.DOTALL)
                if py_block:
                    result = py_block.group(1).strip()
                else:
                    any_block = _re.search(r'```\w*\n(.*?)\n```', raw, _re.DOTALL)
                    if any_block:
                        result = any_block.group(1).strip()
        # Step 6: 终极清洗 — 剔除非 Python 内容
        if result.strip():
            try:
                _parse_py(result)
            except SyntaxError:
                lines = result.split('\n')
                py_lines = []
                for line in lines:
                    stripped = line.strip()
                    # 扔掉纯中文/全角/unicode标点行（如 em dash —、全角空格等）
                    if _re.search(r'[一-鿿　-〿＀-￯‐-―‘-”…]', stripped):
                        # 除非这一行同时有 Python 关键字
                        if not _re.search(
                            r'^(import |from |def |class |@|assert |self\.|return |print |pass |if |elif |else:|try:|except |finally:|with |for |while |async |await |raise |yield |lambda |del |global |nonlocal |# )',
                            stripped,
                        ):
                            continue
                    # 扔掉纯符号/纯标点行（无字母数字）
                    if stripped and not _re.search(r'[a-zA-Z0-9_]', stripped):
                        # 除非是注释、字符串或装饰器
                        if not stripped.startswith(('#', '"', "'", '@', '"""', "'''")):
                            continue
                    py_lines.append(line)
                result = '\n'.join(py_lines).strip()
        # Step 7: 检查结果是否太短（<20字符）— 说明清洗后无有效代码
        if result.strip() and len(result.strip()) < 20:
            return ""
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
    def _detect_language(file_path: str) -> str:
        """根据文件扩展名返回语言/类型"""
        # 去掉路径中的括号注释（如 app/main.py(test config) → app/main.py）
        import re as _re_lang
        clean_path = _re_lang.sub(r'\(.*?\)', '', file_path).strip()
        ext = os.path.splitext(clean_path)[1].lower()
        base = os.path.basename(clean_path).lower()
        if ext in ('.py', '.pyw'):
            return 'python'
        if ext == '.js':
            return 'javascript'
        if ext in ('.ts', '.tsx'):
            return 'typescript'
        if ext in ('.jsx',):
            return 'jsx'
        if ext == '.vue':
            return 'vue'
        if ext == '.html':
            return 'html'
        if ext == '.css':
            return 'css'
        if ext == '.scss':
            return 'scss'
        if ext == '.java':
            return 'java'
        if ext == '.go':
            return 'go'
        if ext == '.rs':
            return 'rust'
        if ext == '.rb':
            return 'ruby'
        if ext == '.php':
            return 'php'
        if ext == '.sh':
            return 'shell_script'
        if ext == '.bat':
            return 'batch'
        if ext in ('.yaml', '.yml'):
            return 'yaml'
        if ext == '.json':
            return 'json'
        if ext == '.xml':
            return 'xml'
        if ext == '.sql':
            return 'sql'
        if ext == '.md':
            return 'markdown'
        if ext == '.dockerfile' or base == 'dockerfile':
            return 'dockerfile'
        if ext in ('.toml',):
            return 'toml'
        if ext in ('.cfg', '.ini', '.conf'):
            return 'config'
        if ext == '.env':
            return 'env'
        if ext in ('.gradle',):
            return 'gradle'
        if ext == '.properties':
            return 'properties'
        if base in ('makefile',):
            return 'makefile'
        return 'code'

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
        abs_file_path: str = "",
        docs_dir: str = "",
    ) -> str:
        """构建代码编写提示词"""
        lang = SwarmService._detect_language(file_path)

        parts = [
            "【输出格式要求】只输出纯代码内容。不要有任何对话、解释、思考过程、问候语、markdown标记。",
            "第一行直接是有效的代码。禁止输出```、<think>等标记。",
            "",
            "【任务】",
            f"文件: {file_path}",
            f"功能: {file_description}",
        ]
        if abs_file_path:
            parts.append(f"保存路径: {abs_file_path}")
        if core_goal:
            parts.append(f"核心目标: {core_goal}")
        if docs_dir:
            parts.append(f"文档目录: {docs_dir}")

        if tdd_cases:
            parts.append(f"")
            parts.append(f"【TDD测试（必须通过）】")
            parts.append(tdd_cases[:4000])

        if code_plan:
            parts.append(f"")
            parts.append(f"【编码计划】")
            parts.append(str(code_plan)[:3000])

        if dependency_codes:
            parts.append(f"")
            parts.append(f"【已有依赖代码】")
            for dep_path, dep_code in dependency_codes:
                parts.append(f"-- {dep_path} --")
                parts.append(dep_code[:2000])

        if last_feedback and attempt > 1:
            parts.append(f"")
            parts.append(f"【上一轮修复要求】")
            parts.append(last_feedback)

        parts.append(f"")
        parts.append("再次强调：只输出代码。不要对话。不要思考过程。不要markdown。")

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
        abs_file_path: str = "",
        docs_dir: str = "",
    ) -> str:
        """构建代码检验提示词"""
        import json as _j
        dims_json = _j.dumps([
            {"维度": "代码正确性", "key": "code_correctness"},
            {"维度": "需求匹配度", "key": "requirement_match"},
            {"维度": "代码规范", "key": "code_standard"},
            {"维度": "测试通过率", "key": "test_pass_rate"},
        ], ensure_ascii=False)

        code_blob = code_content[:6000] if code_content.strip() else ""
        if not code_blob and abs_file_path:
            code_blob = "(文件存在于 " + abs_file_path + ")"
        elif not code_blob:
            code_blob = file_description

        # 极简提示词 — Agent 没有上下文可以发挥
        lines = [
            'SCORE 0-100',
            'JSON: [{"key":"","label":"","passed":bool,"detail":""}]',
            '直接输出。不要对话。',
            '',
            file_path,
        ]
        if abs_file_path:
            lines.append('文件: ' + abs_file_path)
        lines.append('维度: ' + dims_json)
        if tdd_cases:
            lines.append('TDD: ' + tdd_cases[:2000])
        if last_feedback:
            lines.append('修复: ' + last_feedback)
        lines.append('')
        lines.append('---CODE---')
        lines.append(code_blob)
        lines.append('---END---')
        lines.append('SCORE + JSON. 不要其它内容。')
        return '\n'.join(lines)

        return "\n".join(parts)