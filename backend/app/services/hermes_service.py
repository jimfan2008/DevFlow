from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.services.llm_client import get_llm_client, HermesUnavailableError
from app.services.hermes_acp_client import get_acp_client, HermesACPClient

logger = logging.getLogger("devflow.hermes")

HERMES_SYSTEM_PROMPT = """你是 DevFlow 的 AI 项目经理助手。你必须用中文回复。

核心能力：分析需求、识别模糊点、给出改进建议、生成需求文档。

重要规则：
- 直接输出最终回复，不要输出思考过程、推理步骤或任何 Thinking 标签
- 只用中文回复，不要用英文
- 用专业但友好的语气，适当使用结构化列表"""


def _strip_thinking(text):
    lines = text.strip().split('\n')
    clean = []
    in_thinking = False
    THINKING_MARKERS = (
        "thinking process:", "here's a thinking process", "here is a thinking",
        "思考过程：", "分析过程：", "based on my understanding",
        "looking at my instructions", "let me focus on",
        "draft content", "mental refinement", "check constraints",
        "step 1:", "step 2:", "step 3:", "step 4:", "step 5:", "step 6:",
    )
    SECTION_NUM_RE = re.compile(r'^\d+\.\s+\*\*')
    for line in lines:
        s = line.strip()
        sl = s.lower()
        if any(sl.startswith(p) for p in THINKING_MARKERS):
            in_thinking = True
            continue
        if SECTION_NUM_RE.match(s):
            in_thinking = True
            continue
        if in_thinking:
            has_cjk = bool(re.search(r'[\u4e00-\u9fff]', s))
            starts_brace = s.startswith('{') or s.startswith('[')
            is_heading = s.startswith('#') or s.startswith('**一') or s.startswith('**二') or s.startswith('**三')
            if has_cjk and not sl.startswith(('*( ', '*(需求', '*(关键', '*(专业')):
                in_thinking = False
                clean.append(line)
            elif starts_brace or is_heading:
                in_thinking = False
                clean.append(line)
            continue
        if not s:
            if clean and clean[-1].strip():
                clean.append(line)
            continue
        if re.search(r'[\u4e00-\u9fff]', s) or s.startswith('{') or s.startswith('#') or s.startswith('- ') or s.startswith('* '):
            clean.append(line)
            continue
        if re.match(r'^\d+\.\s', s):
            clean.append(line)
            continue
    result = '\n'.join(clean).strip()
    if not result:
        cjk_lines = [l for l in lines if re.search(r'[\u4e00-\u9fff]', l)]
        if cjk_lines:
            idx = lines.index(cjk_lines[0])
            return '\n'.join(lines[idx:]).strip()
    return result if result else text


class HermesService:
    def __init__(self, db, user_id=None):
        self.db = db
        self.user_id = user_id
        self.llm = get_llm_client()
        self._acp_client = None

    @property
    def acp_client(self):
        if self._acp_client is None:
            self._acp_client = get_acp_client()
        return self._acp_client

    def chat(self, message, project_context=None):
        context = ""
        if project_context:
            context = f"\n当前项目上下文：{project_context}"
        prompt = (
            f"用户说：{message}{context}\n\n"
            f"请分析用户的需求，指出模糊点和需要进一步明确的地方，给出你的专业建议。\n"
            f"只用中文回复，不要输出思考过程。"
        )
        try:
            raw_reply = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=HERMES_SYSTEM_PROMPT,
                max_tokens=800,
                temperature=0.7,
            )
        except HermesUnavailableError as e:
            logger.warning(f"LLM unavailable: {e}")
            return self._local_chat_fallback(message, project_context)
        except Exception as e:
            logger.error(f"AI chat failed: {e}")
            return self._local_chat_fallback(message, project_context)
        reply = _strip_thinking(raw_reply)
        if not reply or len(reply.strip()) < 10:
            reply = "我分析了你的需求。请提供更多细节，比如项目类型、目标用户、核心功能等。"
        fuzzy = self._extract_fuzzy_points(reply, message)
        phase = self._detect_phase(reply, message)
        summary = self._extract_summary(reply, message)
        questions = fuzzy[:5] if fuzzy else []
        if phase == "summarizing" and not questions:
            questions = ["提交需求并生成文档", "我还想补充一些细节"]
        return {"reply": reply, "questions": questions, "snapshot": summary, "phase": phase}

    def _extract_fuzzy_points(self, reply, message):
        points = []
        question_patterns = [
            r'[？?]\s*$', r'是否', r'还是', r'哪种', r'多少', r'什么.*？',
            r'需要.*明确', r'需要.*确认', r'建议.*选择', r'考虑.*方面',
        ]
        for line in reply.split('\n'):
            s = line.strip()
            if s and any(re.search(p, s) for p in question_patterns):
                s = re.sub(r'^[-*•]\s*', '', s)
                s = re.sub(r'^\d+\.\s*', '', s)
                if len(s) > 5:
                    points.append(s)
        if not points and len(message) < 50:
            points.append("项目的核心功能有哪些？")
            points.append("目标用户是谁？")
        return points

    def _detect_phase(self, reply, message):
        if any(k in reply for k in ["提交", "总结", "梳理完毕", "信息充足"]):
            return "summarizing"
        if len(message) > 80 or any(k in reply for k in ["深入", "详细", "进一步"]):
            return "discussing"
        return "initial"

    def _extract_summary(self, reply, message):
        summary = {}
        tech_keywords = ["web", "api", "数据库", "前端", "后端", "微服务", "docker", "python", "java", "react", "vue", "移动端", "app"]
        found_tech = [k for k in tech_keywords if k.lower() in message.lower() or k.lower() in reply.lower()]
        if found_tech:
            summary["技术栈"] = found_tech
        feature_keywords = ["登录", "注册", "搜索", "支付", "上传", "通知", "权限", "导出", "报表", "看板", "课程", "追踪", "管理"]
        found_feature = [k for k in feature_keywords if k in message or k in reply]
        if found_feature:
            summary["功能"] = found_feature
        return summary

    def chat_intro(self):
        prompt = (
            "用户刚进入需求管理页面。请用中文简短自我介绍（150字以内），"
            "说明你能帮用户梳理需求、分析模糊点、生成文档、拆解任务。"
            "最后引导用户描述项目想法。只用中文，不要输出思考过程。"
        )
        try:
            reply = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=HERMES_SYSTEM_PROMPT,
                max_tokens=300,
                temperature=0.8,
            )
            reply = _strip_thinking(reply)
            if not reply or len(reply.strip()) < 10:
                reply = self._default_intro()
        except HermesUnavailableError as e:
            logger.warning(f"LLM unavailable for intro: {e}")
            reply = self._default_intro()
        except Exception as e:
            logger.error(f"Intro failed: {e}")
            reply = self._default_intro()
        questions = ["我想开发一个电商平台", "我需要一个企业管理系统", "我想做一个移动端App"]
        return {"reply": reply, "questions": questions, "snapshot": {}, "phase": "initial"}

    def _local_chat_fallback(self, message, project_context=None):
        text = message.strip()
        keywords_tech = ["web", "api", "数据库", "前端", "后端", "微服务", "docker", "k8s", "python", "java", "react", "vue"]
        keywords_feature = ["登录", "注册", "搜索", "支付", "上传", "通知", "权限", "导出", "报表", "看板"]
        found_tech = [k for k in keywords_tech if k.lower() in text.lower()]
        found_feature = [k for k in keywords_feature if k in text]
        if len(text) < 5:
            return {"reply": "请详细描述你的项目需求，比如：项目类型、目标用户、核心功能、技术偏好等。", "questions": ["我想开发一个Web应用", "我需要一个企业管理系统", "我想做一个移动端App"], "snapshot": {}, "phase": "initial"}
        reply_parts, fuzzy, summary = [], [], {}
        if project_context:
            summary["项目名称"] = project_context
        if found_tech:
            reply_parts.append(f"我注意到你提到了：{', '.join(found_tech)}。")
            summary["技术栈"] = found_tech
        else:
            fuzzy.append("你倾向使用什么技术栈？")
        if found_feature:
            reply_parts.append(f"功能点包括：{', '.join(found_feature)}。")
            summary["功能"] = found_feature
        else:
            fuzzy.append("项目的核心功能有哪些？")
        if "用户" in text or "客户" in text:
            reply_parts.append("目标用户方面，你能更具体地描述用户画像吗？")
        else:
            fuzzy.append("目标用户是谁？")
        if "规模" not in text and "大小" not in text:
            fuzzy.append("预期的用户规模和并发量级？")
        if len(text) > 100:
            phase = "summarizing"
            reply_parts.append("信息已经比较充分了，可以考虑提交需求文档。")
        elif len(text) > 50:
            phase = "discussing"
            reply_parts.append("你的描述比较详细，我正在梳理需求要点。")
        else:
            phase = "initial"
            reply_parts.append("请继续补充更多细节，帮助我更准确地理解你的需求。")
        if not reply_parts:
            reply_parts.append("收到你的需求描述，让我来分析关键要点。")
        reply = " ".join(reply_parts)
        questions = fuzzy[:5] if fuzzy else []
        if phase == "summarizing" and not questions:
            questions = ["提交需求并生成文档", "我还想补充一些细节"]
        return {"reply": reply, "questions": questions, "snapshot": summary, "phase": phase}

    def _default_intro(self):
        return ("你好！我是 **Hermes**，你的 AI 项目经理\n\n"
                "我可以帮你：\n"
                "- 梳理和分析项目需求\n"
                "- 生成标准化需求文档\n"
                "- 发现需求中的模糊点和遗漏\n"
                "- 将需求拆解为可执行的任务\n\n"
                "请描述你的项目想法，我会一步步引导你完善需求！")
