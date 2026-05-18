# Hermes 服务 - 使用真实 AI 进行需求分析
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.services.llm_client import get_llm_client, HermesUnavailableError
from app.services.hermes_acp_client import get_acp_client, HermesACPClient

logger = logging.getLogger("devflow.hermes")

HERMES_SYSTEM_PROMPT = """你是一个 AI 项目经理助手，名叫 Hermes。你负责帮助用户梳理、分析和完善项目需求。

你的核心能力：
1. 分析用户描述，理解项目类型和目标
2. 识别需求中的模糊点、遗漏和矛盾
3. 给出专业的具体改进建议
4. 生成标准化需求文档

响应格式：
- 自然的中文对话
- 专业但友好的语气
- 适当使用结构化列表
- 每轮对话要有实质性内容"""


class HermesService:
    def __init__(self, db: Session, user_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.llm = get_llm_client()
        self._acp_client: Optional[HermesACPClient] = None

    @property
    def acp_client(self) -> HermesACPClient:
        if self._acp_client is None:
            self._acp_client = get_acp_client()
        return self._acp_client

    # ── Sync methods (backward compatible) ─────────────────────

    def chat(self, message: str, project_context: Optional[str] = None) -> dict:
        context = ""
        if project_context:
            context = f"\n当前项目上下文：{project_context}"

        prompt = (
            f"用户消息：{message}{context}\n\n"
            f"请分析用户的需求描述，返回 JSON 格式：\n"
            f"{{\n"
            f'  "reply": "你的回复（自然的中文对话，分析需求的要点和问题）",\n'
            f'  "fuzzy_points": ["需要进一步明确的点1", "点2"],\n'
            f'  "phase": "initial|discussing|summarizing",\n'
            f'  "summary": {{"项目类型": "...", "技术栈": ["..."], "功能": ["..."]}}\n'
            f"}}\n\n"
            f"phase 说明：initial=刚开始讨论, discussing=正在分析需求细节, summarizing=信息已充足可提交"
        )

        try:
            result = self.llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=HERMES_SYSTEM_PROMPT,
                max_tokens=800,
                temperature=0.7,
            )
        except HermesUnavailableError as e:
            return self._unavailable_response(str(e))
        except Exception as e:
            logger.error(f"AI chat failed: {e}")
            return self._unavailable_response()

        reply = result.get("reply", "")
        fuzzy = result.get("fuzzy_points", [])
        phase = result.get("phase", "discussing")
        summary = result.get("summary", {})

        if not reply:
            reply = "我分析了你的需求描述。请提供更多细节，比如项目类型、目标用户、核心功能等。"

        questions = fuzzy[:5] if fuzzy else []
        if phase == "summarizing" and not questions:
            questions = ["提交需求并生成文档", "我还想补充一些细节"]

        return {
            "reply": reply,
            "questions": questions,
            "snapshot": summary,
            "phase": phase,
        }

    def chat_intro(self) -> dict:
        prompt = (
            "用户正在打开需求管理页面。请用中文写一段热情友好的自我介绍，说明你叫 Hermes，"
            "是一个 AI 项目经理，可以帮用户梳理需求、分析模糊点、生成需求文档、拆解任务。"
            "最后引导用户描述他们的项目想法。控制在 150 字以内。"
        )

        try:
            reply = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.8,
            )
            if not reply or len(reply.strip()) < 10:
                reply = self._default_intro()
        except HermesUnavailableError as e:
            return self._unavailable_response(str(e))
        except Exception as e:
            logger.error(f"Intro failed: {e}")
            return self._unavailable_response()

        questions = ["我想开发一个电商平台", "我需要一个企业管理系统", "我想做一个移动端App"]
        return {"reply": reply, "questions": questions, "snapshot": {}, "phase": "initial"}

    def _unavailable_response(self, detail: str = "") -> dict:
        msg = "Hermes AI 服务暂不可用（模型后端未连接）"
        if detail:
            msg += f"。{detail}"
        return {"reply": msg, "questions": [], "snapshot": {}, "phase": "initial"}

    def _default_intro(self) -> str:
        return (
            "你好！我是 **Hermes**，你的 AI 项目经理 🤖\n\n"
            "我可以帮你：\n"
            "• 💡 梳理和分析项目需求\n"
            "• 📋 生成标准化需求文档\n"
            "• 🔍 发现需求中的模糊点和遗漏\n"
            "• 📊 将需求拆解为可执行的任务\n\n"
            "请描述你的项目想法，我会一步步引导你完善需求！"
        )

    def generate_structured_doc(self, raw_content: str, clarification_answers: dict) -> dict:
        features = clarification_answers.get("features", [])
        tech = clarification_answers.get("tech_stack", {})
        criteria = clarification_answers.get("acceptance_criteria", [])

        prompt = (
            f"基于以下需求描述和澄清信息，生成结构化的需求文档：\n\n"
            f"原始需求：{raw_content}\n\n"
            f"功能列表：{json.dumps(features, ensure_ascii=False)}\n"
            f"技术栈：{json.dumps(tech, ensure_ascii=False)}\n"
            f"验收标准：{json.dumps(criteria, ensure_ascii=False)}\n\n"
            f"返回 JSON 格式：\n"
            f"{{\n"
            f'  "title": "...",\n'
            f'  "overview": "...",\n'
            f'  "features": ["..."],\n'
            f'  "tech_stack": {{}},\n'
            f'  "acceptance_criteria": ["..."],\n'
            f'  "constraints": ["..."],\n'
            f"}}"
        )

        try:
            result = self.llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.5,
            )
            result["generated_at"] = datetime.now(timezone.utc).isoformat()
            result["version"] = 1
            return result
        except HermesUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Generate doc failed: {e}")
            return {
                "title": clarification_answers.get("project_name", "未命名项目"),
                "overview": raw_content,
                "features": features if features else [raw_content],
                "tech_stack": tech,
                "acceptance_criteria": criteria,
                "constraints": [],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "version": 1,
            }

    # ── Async methods (use HermesACPClient) ────────────────────

    async def _ensure_acp_session(self) -> str:
        """Ensure ACP client is started and return session_id."""
        client = self.acp_client
        if not client.connection:
            await client.start()
        if not client._session_id:
            return await client.init_session()
        return client._session_id

    async def _send_acp_prompt(self, prompt: str, session_id: str) -> str:
        """Send a prompt via ACP and return the response text."""
        return await self.acp_client.send_prompt(prompt, session_id=session_id)

    async def chat_async(self, message: str, project_context: Optional[str] = None) -> dict:
        """Async chat via HermesACPClient."""
        try:
            session_id = await self._ensure_acp_session()
            context = ""
            if project_context:
                context = f"\n当前项目上下文：{project_context}"

            prompt = (
                f"用户消息：{message}{context}\n\n"
                f"请分析用户的需求描述，返回 JSON 格式：\n"
                f"{{\n"
                f'  "reply": "你的回复（自然的中文对话，分析需求的要点和问题）",\n'
                f'  "fuzzy_points": ["需要进一步明确的点1", "点2"],\n'
                f'  "phase": "initial|discussing|summarizing",\n'
                f'  "summary": {{"项目类型": "...", "技术栈": ["..."], "功能": ["..."]}}\n'
                f"}}\n\n"
                f"phase 说明：initial=刚开始讨论, discussing=正在分析需求细节, summarizing=信息已充足可提交"
            )
            resp_text = await self._send_acp_prompt(prompt, session_id=session_id)

            import json as json_mod
            try:
                result = json_mod.loads(resp_text)
            except (json_mod.JSONDecodeError, TypeError):
                return {
                    "reply": resp_text,
                    "questions": [],
                    "snapshot": {},
                    "phase": "discussing",
                }

            reply = result.get("reply", resp_text)
            fuzzy = result.get("fuzzy_points", [])
            phase = result.get("phase", "discussing")
            summary = result.get("summary", {})

            if not reply:
                reply = "我分析了你的需求描述。请提供更多细节，比如项目类型、目标用户、核心功能等。"

            questions = fuzzy[:5] if fuzzy else []
            if phase == "summarizing" and not questions:
                questions = ["提交需求并生成文档", "我还想补充一些细节"]

            return {
                "reply": reply,
                "questions": questions,
                "snapshot": summary,
                "phase": phase,
            }
        except Exception as e:
            logger.error(f"Async chat failed: {e}")
            return self._unavailable_response(str(e))

    async def chat_intro_async(self) -> dict:
        """Async intro via HermesACPClient."""
        try:
            session_id = await self._ensure_acp_session()
            prompt = (
                "用户正在打开需求管理页面。请用中文写一段热情友好的自我介绍，说明你叫 Hermes，"
                "是一个 AI 项目经理，可以帮用户梳理需求、分析模糊点、生成需求文档、拆解任务。"
                "最后引导用户描述他们的项目想法。控制在 150 字以内。"
            )
            reply = await self._send_acp_prompt(prompt, session_id=session_id)
            if not reply or len(reply.strip()) < 10:
                reply = self._default_intro()
            questions = ["我想开发一个电商平台", "我需要一个企业管理系统", "我想做一个移动端App"]
            return {"reply": reply, "questions": questions, "snapshot": {}, "phase": "initial"}
        except Exception as e:
            logger.error(f"Async intro failed: {e}")
            return self._unavailable_response(str(e))

    async def decompose_tasks_async(self, requirement: str) -> list[dict]:
        """Async task decomposition via HermesACPClient."""
        try:
            session_id = await self._ensure_acp_session()
            prompt = (
                f"请将以下项目需求拆解为可执行的原子任务，按软件开发流程：\n"
                f"1. 需求分析细化\n"
                f"2. 测试用例编写\n"
                f"3. 功能模块编码\n"
                f"4. 单元/集成测试\n"
                f"5. 部署环境搭建\n"
                f"6. 整体联调\n\n"
                f"需求：{requirement}\n\n"
                f"请返回 JSON 格式的任务列表，每个任务包含：name, description, agent_type, priority, acceptance_criteria, dependencies。"
            )
            resp_text = await self._send_acp_prompt(prompt, session_id=session_id)

            import json as json_mod
            try:
                tasks_data = json_mod.loads(resp_text)
                if isinstance(tasks_data, list):
                    return tasks_data
                if isinstance(tasks_data, dict) and "tasks" in tasks_data:
                    return tasks_data["tasks"]
            except (json_mod.JSONDecodeError, TypeError):
                pass

            return [{"name": resp_text}]
        except Exception as e:
            logger.error(f"Async decompose failed: {e}")
            return []

    async def generate_doc_async(self, raw_content: str, clarification_answers: dict) -> dict:
        """Async structured doc generation via HermesACPClient."""
        try:
            session_id = await self._ensure_acp_session()
            features = clarification_answers.get("features", [])
            tech = clarification_answers.get("tech_stack", {})
            criteria = clarification_answers.get("acceptance_criteria", [])

            prompt = (
                f"基于以下需求描述和澄清信息，生成结构化的需求文档：\n\n"
                f"原始需求：{raw_content}\n\n"
                f"功能列表：{json.dumps(features, ensure_ascii=False)}\n"
                f"技术栈：{json.dumps(tech, ensure_ascii=False)}\n"
                f"验收标准：{json.dumps(criteria, ensure_ascii=False)}\n\n"
                f"返回 JSON 格式：\n"
                f"{{\n"
                f'  "title": "...",\n'
                f'  "overview": "...",\n'
                f'  "features": ["..."],\n'
                f'  "tech_stack": {{}},\n'
                f'  "acceptance_criteria": ["..."],\n'
                f'  "constraints": ["..."],\n'
                f"}}"
            )
            resp_text = await self._send_acp_prompt(prompt, session_id=session_id)

            import json as json_mod
            try:
                doc = json_mod.loads(resp_text)
                doc["generated_at"] = datetime.now(timezone.utc).isoformat()
                doc["version"] = 1
                return doc
            except (json_mod.JSONDecodeError, TypeError):
                return self.generate_structured_doc(raw_content, clarification_answers)
        except Exception as e:
            logger.error(f"Async generate doc failed: {e}")
            return self.generate_structured_doc(raw_content, clarification_answers)

    async def check_health_async(self) -> bool:
        """Async health check via HermesACPClient."""
        try:
            client = self.acp_client
            if client.connection:
                return True
            await client.start()
            await client.init_session()
            return True
        except Exception:
            return False
