"""v4.0 Hermes Service Tests - Agent对话与需求分析（SRS 3.7）"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.hermes_service import HermesService, _strip_thinking, HERMES_SYSTEM_PROMPT
from app.services.llm_client import HermesUnavailableError


class TestStripThinking:
    """思维链过滤测试"""

    def test_strip_thinking_removes_markers(self):
        text = "thinking process:\n我分析了一下\n1. **步骤**\n实际输出内容"
        result = _strip_thinking(text)
        assert "thinking process" not in result
        assert "实际输出内容" in result

    def test_strip_thinking_preserves_cjk(self):
        text = "thinking process:\nsome internal chain\n最终输出：这是一个功能"
        result = _strip_thinking(text)
        assert "最终输出" in result
        assert "这是一个功能" in result

    def test_strip_thinking_empty_input(self):
        result = _strip_thinking("")
        assert result == ""

    def test_strip_thinking_no_markers(self):
        text = "你好，这是正常回复。"
        result = _strip_thinking(text)
        assert result == "你好，这是正常回复。"

    def test_strip_thinking_with_json_start(self):
        text = "思考中...\n{\"key\": \"value\"}"
        result = _strip_thinking(text)
        assert "{" in result

    def test_strip_thinking_returns_text_if_no_cjk(self):
        text = "thinking process:\nall english\nstill thinking"
        result = _strip_thinking(text)
        assert result == text.strip()

    def test_strip_thinking_handles_section_numbers(self):
        text = "thinking process:\nlet me reason\n1. **架构**\n2. **模块**\n输出"
        result = _strip_thinking(text)
        assert "输出" in result


class TestHermesChatFallback:
    """Hermes 本地回退聊天测试"""

    def test_fallback_with_short_message(self):
        svc = HermesService(db=None)
        result = svc._local_chat_fallback("hi")
        assert result["phase"] == "initial"
        assert len(result["questions"]) == 3

    def test_fallback_with_tech_keywords(self):
        svc = HermesService(db=None)
        result = svc._local_chat_fallback("我要开发一个web应用，用python和vue")
        assert "技术栈" in result["snapshot"]
        assert "web" in result["snapshot"]["技术栈"]
        assert "python" in result["snapshot"]["技术栈"]
        assert "vue" in result["snapshot"]["技术栈"]

    def test_fallback_with_feature_keywords(self):
        svc = HermesService(db=None)
        result = svc._local_chat_fallback("需要登录注册功能和支付模块")
        assert "功能" in result["snapshot"]
        assert "登录" in result["snapshot"]["功能"]
        assert "注册" in result["snapshot"]["功能"]
        assert "支付" in result["snapshot"]["功能"]

    def test_fallback_long_message_phase_summarizing(self):
        svc = HermesService(db=None)
        long_msg = "我想要开发一个大型电商平台，前端用Vue3+ElementPlus，后端用FastAPI+PostgreSQL。"
        long_msg += "核心功能包括：用户注册登录、商品浏览搜索、购物车管理、在线支付、订单管理、"
        long_msg += "后台管理、数据分析报表。目标用户是C端消费者，预计初期1000用户。"
        long_msg += "需要支持移动端适配。部署在阿里云上。"
        result = svc._local_chat_fallback(long_msg)
        assert result["phase"] == "summarizing"

    def test_fallback_medium_message_phase_discussing(self):
        svc = HermesService(db=None)
        msg = "我想做一个任务管理应用，有用户管理、项目看板、任务分配、消息通知这些功能。技术栈用React+Node.js。"
        result = svc._local_chat_fallback(msg)
        assert result["phase"] == "discussing"

    def test_fallback_generates_questions_when_no_features(self):
        svc = HermesService(db=None)
        result = svc._local_chat_fallback("帮我做个系统")
        questions = result["questions"]
        assert any("核心功能" in q for q in questions)

    def test_fallback_with_project_context(self):
        svc = HermesService(db=None)
        result = svc._local_chat_fallback("需要用户登录功能", project_context="电商平台")
        assert "电商平台" in str(result["snapshot"])

    def test_fallback_identifies_user_mentions(self):
        svc = HermesService(db=None)
        result = svc._local_chat_fallback("目标用户是中小企业的管理人员")
        assert "用户画像" in result["reply"] or "目标用户" in result["reply"]


class TestHermesFuzzyExtraction:
    """模糊点提取测试"""

    def test_extract_questions_from_reply(self):
        svc = HermesService(db=None)
        reply = "项目的核心功能有哪些？\n目标用户是谁？\n建议使用什么技术栈？"
        points = svc._extract_fuzzy_points(reply, "做个电商")
        assert len(points) >= 2

    def test_extract_returns_defaults_for_short_message(self):
        svc = HermesService(db=None)
        points = svc._extract_fuzzy_points("你好", "hi")
        assert any("核心功能" in p for p in points)

    def test_extract_cleans_prefixes(self):
        svc = HermesService(db=None)
        reply = "- 使用什么数据库？\n* 需要什么部署方式？\n1. 用户量级是多少？"
        points = svc._extract_fuzzy_points(reply, "测试")
        for p in points:
            assert not p.startswith("- ")
            assert not p.startswith("* ")
            assert not p.startswith("1. ")


class TestHermesPhaseDetection:
    """对话阶段检测测试"""

    def test_detect_initial_phase(self):
        svc = HermesService(db=None)
        phase = svc._detect_phase("了解了", "hi")
        assert phase == "initial"

    def test_detect_discussing_phase(self):
        svc = HermesService(db=None)
        phase = svc._detect_phase("请详细描述", "help")
        assert phase == "discussing"

    def test_detect_summarizing_phase(self):
        svc = HermesService(db=None)
        phase = svc._detect_phase("信息充足，可以提交需求文档", "需要一个完整的系统")
        assert phase == "summarizing"

    def test_long_message_triggers_discussing(self):
        svc = HermesService(db=None)
        long_msg = "a" * 100
        phase = svc._detect_phase("继续", long_msg)
        assert phase == "discussing"


class TestHermesIntro:
    """自我介绍测试"""

    def test_default_intro_content(self):
        svc = HermesService(db=None)
        intro = svc._default_intro()
        assert "Hermes" in intro
        assert "项目经理" in intro
        assert "需求" in intro

    def test_chat_intro_returns_questions(self):
        svc = HermesService(db=None)
        result = svc.chat_intro()
        assert "reply" in result
        assert "questions" in result
        assert len(result["questions"]) == 3

    def test_chat_intro_fallback_on_llm_error(self):
        svc = HermesService(db=None)
        with patch.object(svc.llm, 'chat', side_effect=HermesUnavailableError("unavailable")):
            result = svc.chat_intro()
            assert result["reply"] == svc._default_intro()


class TestHermesSystemPrompt:
    """系统提示词测试"""

    def test_prompt_contains_chinese_requirement(self):
        assert "中文" in HERMES_SYSTEM_PROMPT

    def test_prompt_contains_devflow_reference(self):
        assert "DevFlow" in HERMES_SYSTEM_PROMPT

    def test_prompt_contains_role_definition(self):
        assert "项目经理" in HERMES_SYSTEM_PROMPT

    def test_prompt_forbids_thinking_output(self):
        assert "不要输出思考过程" in HERMES_SYSTEM_PROMPT
