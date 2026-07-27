import asyncio
import json
import re
from typing import List, Dict, Callable, AsyncGenerator, Optional
from app.services.gateway_client import gateway_client


class MeetingState:
    """会议状态管理"""

    def __init__(
        self,
        group_id: str,
        topic: str,
        host_agent: str,
        participants: List[str],
        meeting_type: str = "tech_solution",
        duration_minutes: int = 45,
        pre_materials: Optional[str] = None,
        rules: Optional[List[str]] = None
    ):
        self.group_id = group_id
        self.topic = topic
        self.host_agent = host_agent
        self.participants = participants
        self.meeting_type = meeting_type
        self.duration_minutes = duration_minutes
        self.pre_materials = pre_materials or ""
        self.rules = rules or []
        self.agenda: List[Dict[str, any]] = []
        self.conversation_history: List[Dict[str, str]] = []
        self.current_speaker: Optional[str] = None
        self.is_active: bool = True
        self.meeting_minutes: str = ""
        self.decisions: List[Dict[str, str]] = []
        self.todos: List[Dict[str, str]] = []
        self.risks: List[Dict[str, str]] = []
        self.open_issues: List[Dict[str, str]] = []

    def add_to_history(self, speaker: str, content: str, role: str = "assistant"):
        self.conversation_history.append({
            "speaker": speaker,
            "role": role,
            "content": content
        })

    def get_history_as_messages(self) -> List[Dict[str, str]]:
        messages = []
        for entry in self.conversation_history:
            messages.append({
                "role": entry["role"],
                "content": f"[{entry['speaker']}]: {entry['content']}"
            })
        return messages


class ConversationCoordinator:
    """Agent 对话协调器"""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_meetings: Dict[str, MeetingState] = {}
        self._cancel_events: Dict[str, asyncio.Event] = {}

    def get_meeting_state(self, group_id: str) -> Optional[MeetingState]:
        return self.active_meetings.get(group_id)

    def cancel_meeting(self, group_id: str):
        if group_id in self._cancel_events:
            self._cancel_events[group_id].set()
        if group_id in self.active_meetings:
            self.active_meetings[group_id].is_active = False

    async def meeting_mode(
        self,
        group_id: str,
        profile_names: List[str],
        host_agent: str,
        topic: str,
        meeting_type: str = "tech_solution",
        duration_minutes: int = 45,
        pre_materials: Optional[str] = None,
        rules: Optional[List[str]] = None,
        progress_callback: Callable[[str, str], None] = None
    ) -> AsyncGenerator[Dict[str, str], None]:
        if host_agent not in profile_names:
            raise ValueError(f"Host agent '{host_agent}' not in participants")

        meeting = MeetingState(
            group_id,
            topic,
            host_agent,
            profile_names,
            meeting_type=meeting_type,
            duration_minutes=duration_minutes,
            pre_materials=pre_materials,
            rules=rules
        )
        self.active_meetings[group_id] = meeting
        self._cancel_events[group_id] = asyncio.Event()

        other_agents = [p for p in profile_names if p != host_agent]

        meeting_type_labels = {
            "requirement_review": "需求评审会",
            "tech_solution": "技术方案讨论会",
            "daily_standup": "每日站会/进度同步会",
            "incident_postmortem": "故障复盘会"
        }
        meeting_type_label = meeting_type_labels.get(meeting_type, meeting_type)
        base_rules = [
            "聚焦议题，不跑偏；不聊无关内容",
            "不临时加议题；细节争论标记为会后小会再对齐",
            "发言简明，每人限时；争议无共识由负责人当场拍板，拍板后不翻案",
            "结论当场记录：决议 / 待办+责任人+截止时间 / 风险及规避 / 遗留问题"
        ]
        effective_rules = meeting.rules if meeting.rules else base_rules

        try:
            yield {"profile": host_agent, "event": "phase", "content": "开场定调", "data": "opening"}

            if progress_callback:
                progress_callback(host_agent, "speaking")
            meeting.current_speaker = host_agent

            opening_prompt = (
                f"你是本次会议的主持人。会议类型：{meeting_type_label}。\n"
                f"会议议题：{topic}\n"
                f"预计时长：{duration_minutes} 分钟\n"
                f"参会成员：{', '.join(other_agents)}\n\n"
                f"请用不超过3分钟的开场白完成：\n"
                f"1) 明确今天只要解决哪几件事(3点以内)\n"
                f"2) 明确会议产出(必须包含: 决议, 待办(责任人+截止时间), 风险, 遗留问题)\n"
                f"3) 重申会议规则(按条列出)\n\n"
                f"会议规则建议:\n- " + "\n- ".join(effective_rules) + "\n\n"
                f"如有会前物料/前置文档,请在最后补充会前物料一节(没有就写无):\n"
                f"{meeting.pre_materials or '无'}"
            )

            opening_response = ""
            async for chunk in self._send_to_agent(host_agent, opening_prompt, []):
                if self._is_cancelled(group_id):
                    return
                opening_response += chunk
                yield {"profile": host_agent, "content": chunk, "event": "speaking"}

            meeting.add_to_history(host_agent, opening_response)

            if progress_callback:
                progress_callback(host_agent, "idle")
            meeting.current_speaker = None

            if self._is_cancelled(group_id):
                return

            yield {"profile": host_agent, "event": "phase", "content": "制订议程", "data": "agenda_planning"}

            if progress_callback:
                progress_callback(host_agent, "speaking")
            meeting.current_speaker = host_agent

            template_hints = {
                "requirement_review": "议程模板：PRD整体介绍→业务流程→边界规则→特殊场景→开发提问→疑问答疑→当场确认是否可排期→记录变更",
                "tech_solution": "议程模板：背景目标→现有问题→备选方案对比→架构&接口→风险评估→敲定方案→拆分开发任务",
                "daily_standup": "议程模板：每人3句话（昨天/今天/阻塞），总时长15分钟；阻塞当场协调资源",
                "incident_postmortem": "议程模板：时间线→影响面→根因→修复措施→预防改进→责任人&截止时间"
            }
            template_hint = template_hints.get(meeting_type, template_hints["tech_solution"])

            agenda_prompt = (
                f"你是本次会议的主持人。会议类型：{meeting_type_label}。\n"
                f"会议议题：{topic}\n"
                f"参会成员：{', '.join(other_agents)}\n"
                f"会议总时长：{duration_minutes} 分钟\n\n"
                f"{template_hint}\n\n"
                f"请输出一份「可执行」的会议议程（要求可控场、可落地）：\n"
                f"1) 总计 3-6 个议程项，必须覆盖：决策/任务/风险/遗留问题\n"
                f"2) 每个议程项要写清：目标、需要的结论、建议发言顺序、每人发言限时（分钟）\n"
                f"3) 严格控制总时长，不要超出 {duration_minutes} 分钟\n"
                f"4) 用 JSON 输出（请确保合法 JSON），格式如下：\n"
                f'```json\n'
                f'{{"agenda": [\n'
                f'  {{"title": "议程标题", "description": "目标/范围/要产出的结论", "speakers": ["成员名1","成员名2"], "timebox_min": 10, "per_speaker_min": 1, "expected_outputs": ["决议","待办","风险","遗留问题"]}},\n'
                f'  ...\n'
                f']}}\n'
                f'```\n'
                f"5) JSON 前只允许有一段 2-3 句话的议程说明，不要展开长文。"
            )

            full_response = ""
            async for chunk in self._send_to_agent(host_agent, agenda_prompt, []):
                if self._is_cancelled(group_id):
                    return
                full_response += chunk
                yield {"profile": host_agent, "content": chunk, "event": "speaking"}

            meeting.add_to_history(host_agent, full_response)

            if progress_callback:
                progress_callback(host_agent, "idle")
            meeting.current_speaker = None

            agenda = self._parse_agenda(full_response, other_agents)
            meeting.agenda = agenda

            yield {"profile": host_agent, "event": "agenda_ready", "content": "", "data": json.dumps(agenda, ensure_ascii=False)}

            if self._is_cancelled(group_id):
                return

            for idx, agenda_item in enumerate(agenda):
                if self._is_cancelled(group_id):
                    return

                item_title = agenda_item.get("title", f"议题{idx+1}")
                item_desc = agenda_item.get("description", "")
                timebox_min = int(agenda_item.get("timebox_min", 10) or 10)
                per_speaker_min = int(agenda_item.get("per_speaker_min", 1) or 1)
                speakers = agenda_item.get("speakers", other_agents)

                speakers = [s for s in speakers if s in other_agents]
                if not speakers:
                    speakers = other_agents

                yield {"profile": host_agent, "event": "agenda_item_start", "content": f"议程第{idx+1}项：{item_title}", "data": json.dumps({"index": idx, "title": item_title, "description": item_desc, "speakers": speakers}, ensure_ascii=False)}

                if progress_callback:
                    progress_callback(host_agent, "speaking")
                meeting.current_speaker = host_agent

                intro_prompt = (
                    f"你是会议主持人。当前议程第{idx+1}项：「{item_title}」。\n"
                    f"{item_desc}\n\n"
                    f"控场要求：\n"
                    f"- 本议程时间盒：{timebox_min} 分钟\n"
                    f"- 每人发言限时：{per_speaker_min} 分钟（简明：优缺点/风险/建议）\n"
                    f"- 如陷入细节争论，明确标记'会后小会对齐'并拉回主线\n"
                    f"- 如出现争议无法达成共识，需要你当场拍板（或请产品/技术负责人拍板），并宣布'拍板后不翻案'\n\n"
                    f"现在请你用 2-3 句话介绍本议题的目标与需要的结论，然后宣布开始讨论。"
                )

                intro_response = ""
                async for chunk in self._send_to_agent(host_agent, intro_prompt, meeting.get_history_as_messages()):
                    if self._is_cancelled(group_id):
                        return
                    intro_response += chunk
                    yield {"profile": host_agent, "content": chunk, "event": "speaking"}

                meeting.add_to_history(host_agent, intro_response)

                if progress_callback:
                    progress_callback(host_agent, "idle")
                meeting.current_speaker = None

                await asyncio.sleep(1)

                for speaker in speakers:
                    if self._is_cancelled(group_id):
                        return

                    yield {"profile": host_agent, "event": "grant_speak", "content": f"请{speaker}发言", "data": speaker}

                    if progress_callback:
                        progress_callback(speaker, "speaking")
                    meeting.current_speaker = speaker

                    speak_prompt = (
                        f"你正在参加一个{meeting_type_label}，总议题是「{topic}」。\n"
                        f"当前议程项：「{item_title}」\n"
                        f"{item_desc}\n\n"
                        f"主持人是 {host_agent}，你被点名发言。\n"
                        f"请在 {per_speaker_min} 分钟内给出可落地的发言（不要长篇大论）：\n"
                        f"1) 你的立场/建议（1句话）\n"
                        f"2) 关键理由（2-3点，含风险/依赖/边界）\n"
                        f"3) 若有分歧，给出你认为的取舍与拍板建议\n"
                        f"4) 若涉及行动项，写出责任人+建议截止时间（可以用相对时间如T+2天）"
                    )

                    speaker_response = ""
                    async for chunk in self._send_to_agent(speaker, speak_prompt, meeting.get_history_as_messages()):
                        if self._is_cancelled(group_id):
                            return
                        speaker_response += chunk
                        yield {"profile": speaker, "content": chunk, "event": "speaking"}

                    meeting.add_to_history(speaker, speaker_response)

                    if progress_callback:
                        progress_callback(speaker, "idle")
                    meeting.current_speaker = None

                    await asyncio.sleep(1)

                if idx < len(agenda) - 1:
                    if self._is_cancelled(group_id):
                        return

                    if progress_callback:
                        progress_callback(host_agent, "speaking")
                    meeting.current_speaker = host_agent

                    transition_prompt = (
                        f"你是会议主持人。议程第{idx+1}项「{item_title}」的讨论已结束。\n"
                        f"请用1-2句话简要总结刚才的讨论要点，然后引导进入下一个议题。"
                    )

                    transition_response = ""
                    async for chunk in self._send_to_agent(host_agent, transition_prompt, meeting.get_history_as_messages()):
                        if self._is_cancelled(group_id):
                            return
                        transition_response += chunk
                        yield {"profile": host_agent, "content": chunk, "event": "speaking"}

                    meeting.add_to_history(host_agent, transition_response)

                    if progress_callback:
                        progress_callback(host_agent, "idle")
                    meeting.current_speaker = None

                    await asyncio.sleep(1)

            if self._is_cancelled(group_id):
                return

            yield {"profile": host_agent, "event": "phase", "content": "会议总结", "data": "summarizing"}

            if progress_callback:
                progress_callback(host_agent, "speaking")
            meeting.current_speaker = host_agent

            summary_prompt = (
                f"你是会议主持人。会议类型：{meeting_type_label}。\n"
                f"会议议题「{topic}」的所有议程已结束。\n\n"
                f"请在散会后 5 分钟内可直接发出去的格式，输出会议纪要（必须结构化、可跟踪）：\n"
                f"1) 决议结论（拍板了什么/不做什么/排到哪个迭代）\n"
                f"2) 待办任务（每条必须包含：任务、责任人、截止时间）\n"
                f"3) 风险点与规避措施\n"
                f"4) 遗留问题（会后小会/下次会议再议，给出明确下一步）\n\n"
                f"另外请按议程逐项回顾要点，但不要写成流水账。\n\n"
                f"输出格式必须如下：\n"
                f"## 会议纪要\n"
                f"**会议类型**：{meeting_type_label}\n"
                f"**议题**：{topic}\n"
                f"**主持人**：{host_agent}\n"
                f"**参会成员**：{', '.join(other_agents)}\n"
                f"**时长**：{duration_minutes} 分钟\n\n"
                f"### 决议结论\n"
                f"- ...\n\n"
                f"### 待办任务（责任人/截止）\n"
                f"- [ ] ...（Owner: ...，DDL: ...）\n\n"
                f"### 风险与规避\n"
                f"- 风险：...；规避：...\n\n"
                f"### 遗留问题（会后小会/下次再议）\n"
                f"- 问题：...；下一步：...\n\n"
                f"### 按议程回顾（简要）\n"
                f"- 议程1：...\n\n"
                f"在会议纪要之后，请额外输出一份 JSON 格式的结构化数据，用于系统自动提取待办事项：\n"
                f"```json\n"
                f"{{\n"
                f'  "decisions": [{{"description": "决议描述", "owner": "负责人"}}],\n'
                f'  "todos": [{{"description": "任务描述", "assignee": "责任人", "deadline": "截止时间（如 T+2天 或 具体日期）"}}],\n'
                f'  "risks": [{{"description": "风险描述", "mitigation": "规避措施"}}],\n'
                f'  "open_issues": [{{"description": "问题描述", "next_step": "下一步行动"}}]\n'
                f"}}\n"
                f"```\n"
            )

            summary_response = ""
            async for chunk in self._send_to_agent(host_agent, summary_prompt, meeting.get_history_as_messages()):
                if self._is_cancelled(group_id):
                    return
                summary_response += chunk
                yield {"profile": host_agent, "content": chunk, "event": "speaking"}

            meeting.add_to_history(host_agent, summary_response)
            meeting.meeting_minutes = summary_response

            if progress_callback:
                progress_callback(host_agent, "idle")
            meeting.current_speaker = None

            self._parse_meeting_outcomes(meeting, summary_response)

            yield {
                "profile": host_agent,
                "event": "meeting_complete",
                "content": "",
                "data": json.dumps({
                    "minutes": summary_response,
                    "decisions": meeting.decisions,
                    "todos": meeting.todos,
                    "risks": meeting.risks,
                    "open_issues": meeting.open_issues
                }, ensure_ascii=False)
            }

        finally:
            meeting.is_active = False
            if group_id in self._cancel_events:
                del self._cancel_events[group_id]

    async def handle_intervention(
        self,
        group_id: str,
        user_content: str,
        progress_callback: Callable[[str, str], None] = None
    ) -> AsyncGenerator[Dict[str, str], None]:
        meeting = self.active_meetings.get(group_id)
        if not meeting or not meeting.is_active:
            return

        meeting.add_to_history("user", user_content, role="user")

        if progress_callback:
            progress_callback(meeting.host_agent, "speaking")
        meeting.current_speaker = meeting.host_agent

        agenda_summary = ""
        for i, item in enumerate(meeting.agenda):
            agenda_summary += f"{i+1}. {item['title']} ({item.get('description', '')})\n"

        prompt = (
            f"你是本次会议的主持人。会议正在讨论「{meeting.topic}」。\n\n"
            f"用户（你正在协助的会议组织者）在会议进行中发来了一条消息：\n\n"
            f"「{user_content}」\n\n"
            f"当前议程：\n{agenda_summary}\n\n"
            f"请处理用户的请求。你可以：\n"
            f"1. 回应用户的建议或问题\n"
            f"2. 如果你认为议程需要调整（增加、删除、修改议程项），请在回应的末尾附上完整的议程 JSON：\n"
            f"```json\n{{\"agenda_update\": true, \"agenda\": [...]}}\n```\n"
            f"议程项格式：{{\"title\": \"标题\", \"description\": \"描述\", \"speakers\": [\"成员名\"], \"timebox_min\": 10, \"per_speaker_min\": 2, \"expected_outputs\": [\"决议\",\"待办\"]}}\n\n"
            f"如果不需要修改议程，回应末尾不要带 JSON 块，直接回应用户即可。\n\n"
            f"请先用自然语言回应用户，再（如果需要）附上 JSON。"
        )

        full_response = ""
        async for chunk in self._send_to_agent(meeting.host_agent, prompt, meeting.get_history_as_messages()):
            if self._is_cancelled(group_id):
                return
            full_response += chunk
            yield {"profile": meeting.host_agent, "content": chunk, "event": "speaking"}

        meeting.add_to_history(meeting.host_agent, full_response)

        if progress_callback:
            progress_callback(meeting.host_agent, "idle")
        meeting.current_speaker = None

        json_match = re.search(r'```json\s*(.*?)\s*```', full_response, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{[\s\S]*"agenda_update"[\s\S]*\}', full_response)
        if json_match:
            try:
                data = json.loads(json_match.group(1) if json_match.lastindex else json_match.group(0))
                if data.get("agenda_update") and "agenda" in data:
                    new_agenda = data["agenda"]
                    valid_agenda = []
                    for item in new_agenda:
                        if isinstance(item, dict) and "title" in item:
                            valid_agenda.append({
                                "title": item["title"],
                                "description": item.get("description", ""),
                                "speakers": [s for s in item.get("speakers", meeting.participants) if s in meeting.participants and s != meeting.host_agent],
                                "timebox_min": item.get("timebox_min", 10),
                                "per_speaker_min": item.get("per_speaker_min", 1),
                                "expected_outputs": item.get("expected_outputs", [])
                            })
                    if valid_agenda:
                        meeting.agenda = valid_agenda
                        yield {"profile": meeting.host_agent, "event": "agenda_updated", "content": "议程已更新", "data": json.dumps(valid_agenda, ensure_ascii=False)}
            except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
                pass

    def _is_cancelled(self, group_id: str) -> bool:
        event = self._cancel_events.get(group_id)
        return event is not None and event.is_set()

    def _parse_agenda(self, response: str, available_agents: List[str]) -> List[Dict]:
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if "agenda" in data:
                    agenda = data["agenda"]
                    valid_agenda = []
                    for item in agenda:
                        if isinstance(item, dict) and "title" in item:
                            speakers = item.get("speakers", available_agents)
                            valid_speakers = [s for s in speakers if s in available_agents]
                            if not valid_speakers:
                                valid_speakers = available_agents
                            valid_agenda.append({
                                "title": item["title"],
                                "description": item.get("description", ""),
                                "speakers": valid_speakers,
                                "timebox_min": item.get("timebox_min", 10),
                                "per_speaker_min": item.get("per_speaker_min", 1),
                                "expected_outputs": item.get("expected_outputs", [])
                            })
                    if valid_agenda:
                        return valid_agenda
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        json_match = re.search(r'\{[\s\S]*"agenda"[\s\S]*\}', response)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                if "agenda" in data:
                    agenda = data["agenda"]
                    valid_agenda = []
                    for item in agenda:
                        if isinstance(item, dict) and "title" in item:
                            speakers = item.get("speakers", available_agents)
                            valid_speakers = [s for s in speakers if s in available_agents]
                            if not valid_speakers:
                                valid_speakers = available_agents
                            valid_agenda.append({
                                "title": item["title"],
                                "description": item.get("description", ""),
                                "speakers": valid_speakers,
                                "timebox_min": item.get("timebox_min", 10),
                                "per_speaker_min": item.get("per_speaker_min", 1),
                                "expected_outputs": item.get("expected_outputs", [])
                            })
                    if valid_agenda:
                        return valid_agenda
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        return [
            {
                "title": f"讨论：{response[:30]}...",
                "description": "自由讨论",
                "speakers": available_agents,
                "timebox_min": 10,
                "per_speaker_min": 1,
                "expected_outputs": ["决议", "待办", "风险", "遗留问题"]
            }
        ]

    def _parse_meeting_outcomes(self, meeting: MeetingState, summary: str):
        json_match = re.search(r'```json\s*(.*?)\s*```', summary, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{[\s\S]*"todos"[\s\S]*\}', summary)
        if json_match:
            try:
                data = json.loads(json_match.group(1) if json_match.lastindex else json_match.group(0))
                if "decisions" in data and isinstance(data["decisions"], list):
                    meeting.decisions = [
                        {"description": d.get("description", ""), "owner": d.get("owner", "")}
                        for d in data["decisions"]
                    ]
                if "todos" in data and isinstance(data["todos"], list):
                    meeting.todos = [
                        {"description": t.get("description", ""), "assignee": t.get("assignee", ""), "deadline": t.get("deadline", "")}
                        for t in data["todos"]
                    ]
                if "risks" in data and isinstance(data["risks"], list):
                    meeting.risks = [
                        {"description": r.get("description", ""), "mitigation": r.get("mitigation", "")}
                        for r in data["risks"]
                    ]
                if "open_issues" in data and isinstance(data["open_issues"], list):
                    meeting.open_issues = [
                        {"description": o.get("description", ""), "next_step": o.get("next_step", "")}
                        for o in data["open_issues"]
                    ]
            except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
                pass

    async def _send_to_agent(
        self,
        profile_name: str,
        message: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> AsyncGenerator[str, None]:
        async with self.semaphore:
            try:
                async for chunk in gateway_client.send_message(
                    profile_name, message, conversation_history
                ):
                    yield chunk
            except Exception as e:
                yield f"[发言出错: {str(e)}]"

    async def discussion_mode(
        self,
        profile_names: List[str],
        message: str,
        conversation_history: List[Dict[str, str]] = None,
        progress_callback: Callable[[str, str], None] = None
    ) -> AsyncGenerator[Dict[str, str], None]:
        async for result in self.broadcast_message(
            profile_names, message, conversation_history, progress_callback
        ):
            yield result

    async def broadcast_message(
        self,
        profile_names: List[str],
        message: str,
        conversation_history: List[Dict[str, str]] = None,
        progress_callback: Callable[[str, str], None] = None
    ) -> AsyncGenerator[Dict[str, str], None]:
        tasks = []

        for profile_name in profile_names:
            task = asyncio.create_task(
                self._collect_agent_response(profile_name, message, conversation_history, progress_callback)
            )
            tasks.append((profile_name, task))

        for profile_name, task in tasks:
            try:
                result = await task
                for chunk in result:
                    yield chunk
            except Exception as e:
                yield {"profile": profile_name, "error": str(e)}

    async def _collect_agent_response(
        self,
        profile_name: str,
        message: str,
        conversation_history: List[Dict[str, str]] = None,
        progress_callback: Callable[[str, str], None] = None
    ) -> List[Dict[str, str]]:
        chunks = []
        first_chunk_sent = False

        try:
            async for chunk in self._send_to_agent(profile_name, message, conversation_history):
                if not first_chunk_sent and progress_callback:
                    progress_callback(profile_name, "typing")
                    first_chunk_sent = True
                chunks.append({"profile": profile_name, "content": chunk})
        finally:
            if progress_callback:
                progress_callback(profile_name, "idle")

        return chunks


coordinator = ConversationCoordinator()
