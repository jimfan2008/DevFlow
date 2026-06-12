import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from app.api.ws.step3_qa import _run_qa_loop, _extract_json_array, _get_next_version


INSPECTION_DIMS = [
    {"key": "completeness", "label": "完整性", "description": "覆盖所有必要功能"},
    {"key": "consistency", "label": "一致性", "description": "术语定义统一"},
    {"key": "verifiability", "label": "可验证性", "description": "需求可量化"},
    {"key": "unambiguity", "label": "无歧义性", "description": "描述清晰"},
]

SAMPLE_GOOD_DOC = """# 需求文档

## 1. 功能需求
系统支持用户注册、登录、注销功能。

## 2. 非功能需求
系统响应时间不超过2秒。
"""

SAMPLE_FIXED_DOC = """# 需求文档

## 1. 功能需求
系统支持用户注册、登录、注销功能。

## 2. 非功能需求
系统响应时间不超过1秒。
"""

ALL_PASS_RESULT = json.dumps([
    {"key": "completeness", "passed": True, "detail": "覆盖了所有必要功能"},
    {"key": "consistency", "passed": True, "detail": "术语定义统一"},
    {"key": "verifiability", "passed": True, "detail": "需求可量化"},
    {"key": "unambiguity", "passed": True, "detail": "描述清晰"},
])

SOME_FAIL_RESULT = json.dumps([
    {"key": "completeness", "passed": True, "detail": "覆盖了所有必要功能"},
    {"key": "consistency", "passed": True, "detail": "术语定义统一"},
    {"key": "verifiability", "passed": False, "detail": "响应时间指标不可验证"},
    {"key": "unambiguity", "passed": True, "detail": "描述清晰"},
])


class MockAsyncGen:
    def __init__(self, chunks):
        self.chunks = list(chunks)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.chunks:
            raise StopAsyncIteration
        return self.chunks.pop(0)


def _make_chat_side_effect(*seq):
    responses = list(seq)
    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        idx = call_count % len(responses)
        call_count += 1
        return MockAsyncGen(responses[idx])
    return side_effect


@pytest.mark.asyncio
async def test_qa_all_pass_first_attempt():
    ws = AsyncMock()
    with (
        patch("app.api.ws.step3_qa.GatewayClient") as MockGC,
        patch("app.api.workflow.SRS_INSPECTION_DIMENSIONS", INSPECTION_DIMS),
        patch("builtins.open", MagicMock()),
        patch("app.api.ws.step3_qa.os.makedirs"),
    ):
        instance = MockGC.return_value
        instance.chat_completions = MagicMock(return_value=MockAsyncGen([ALL_PASS_RESULT]))

        await _run_qa_loop(ws, SAMPLE_GOOD_DOC, "test_project", "/tmp/docs")

    calls = [c.args[0] for c in ws.send_json.call_args_list]
    result_msgs = [c for c in calls if c.get("type") == "result"]
    assert len(result_msgs) == 1
    assert result_msgs[0]["all_passed"] is True
    step_complete_msgs = [c for c in calls if c.get("type") == "step_complete"]
    assert len(step_complete_msgs) == 0


@pytest.mark.asyncio
async def test_qa_fail_then_fix_then_pass():
    ws = AsyncMock()
    doc_path = "/tmp/test_docs"

    with (
        patch("app.api.ws.step3_qa.GatewayClient") as MockGC,
        patch("app.api.workflow.SRS_INSPECTION_DIMENSIONS", INSPECTION_DIMS),
        patch("app.api.ws.step3_qa._get_next_version", AsyncMock(return_value=2)),
        patch("app.api.ws.step3_qa.os.makedirs"),
        patch("builtins.open", MagicMock()),
    ):
        instance = MockGC.return_value
        instance.chat_completions = MagicMock(
            side_effect=_make_chat_side_effect(
                [SOME_FAIL_RESULT],
                [SAMPLE_FIXED_DOC],
                [ALL_PASS_RESULT],
            )
        )

        await _run_qa_loop(ws, SAMPLE_GOOD_DOC, "test_project", doc_path)

    calls = [c.args[0] for c in ws.send_json.call_args_list]
    result_msgs = [c for c in calls if c.get("type") == "result"]
    assert len(result_msgs) == 2
    assert result_msgs[0]["all_passed"] is False
    assert result_msgs[1]["all_passed"] is True


@pytest.mark.asyncio
async def test_qa_max_attempts_exhausted():
    ws = AsyncMock()

    with (
        patch("app.api.ws.step3_qa.GatewayClient") as MockGC,
        patch("app.api.workflow.SRS_INSPECTION_DIMENSIONS", INSPECTION_DIMS),
        patch("app.api.ws.step3_qa._get_next_version", AsyncMock(return_value=2)),
        patch("app.api.ws.step3_qa.os.makedirs"),
        patch("builtins.open", MagicMock()),
    ):
        instance = MockGC.return_value
        instance.chat_completions = MagicMock(
            side_effect=_make_chat_side_effect(
                [SOME_FAIL_RESULT],
                [SAMPLE_FIXED_DOC],
            )
        )

        await _run_qa_loop(ws, SAMPLE_GOOD_DOC, "test_project", "/tmp/docs")

    calls = [c.args[0] for c in ws.send_json.call_args_list]
    progress_msgs = [c for c in calls if c.get("type") == "progress"]
    all_progress = " ".join(m.get("content", "") for m in progress_msgs)
    assert "10 轮" in all_progress


@pytest.mark.asyncio
async def test_qa_hourong_retry_on_incomplete():
    ws = AsyncMock()
    incomplete = json.dumps([
        {"key": "completeness", "passed": True, "detail": "ok"},
    ])

    with (
        patch("app.api.ws.step3_qa.GatewayClient") as MockGC,
        patch("app.api.workflow.SRS_INSPECTION_DIMENSIONS", INSPECTION_DIMS),
    ):
        instance = MockGC.return_value
        instance.chat_completions = MagicMock(
            side_effect=_make_chat_side_effect(
                [incomplete],
                [ALL_PASS_RESULT],
            )
        )

        await _run_qa_loop(ws, SAMPLE_GOOD_DOC, "test_project", "/tmp/docs")

    calls = [c.args[0] for c in ws.send_json.call_args_list]
    result_msgs = [c for c in calls if c.get("type") == "result"]
    assert len(result_msgs) == 1
    assert result_msgs[0]["all_passed"] is True


@pytest.mark.asyncio
async def test_qa_houxing_generates_too_short_content():
    ws = AsyncMock()
    short_content = "短内容"

    with (
        patch("app.api.ws.step3_qa.GatewayClient") as MockGC,
        patch("app.api.workflow.SRS_INSPECTION_DIMENSIONS", INSPECTION_DIMS),
    ):
        instance = MockGC.return_value
        instance.chat_completions = MagicMock(
            side_effect=_make_chat_side_effect(
                [SOME_FAIL_RESULT],
                [short_content],
            )
        )

        await _run_qa_loop(ws, SAMPLE_GOOD_DOC, "test_project", "/tmp/docs")

    calls = [c.args[0] for c in ws.send_json.call_args_list]
    progress_msgs = [c for c in calls if c.get("type") == "progress"]
    text = " ".join(m.get("content", "") for m in progress_msgs)
    assert "过短" in text or "跳过" in text


@pytest.mark.asyncio
async def test_qa_pass_saves_document_and_advances_workflow():
    ws = AsyncMock()
    mock_db = MagicMock()
    mock_engine = MagicMock()

    with (
        patch("app.api.ws.step3_qa.GatewayClient") as MockGC,
        patch("app.api.workflow.SRS_INSPECTION_DIMENSIONS", INSPECTION_DIMS),
        patch("app.services.workflow_engine.WorkflowEngine", return_value=mock_engine) as MockWE,
        patch("builtins.open", MagicMock()),
        patch("app.api.ws.step3_qa.os.makedirs"),
        patch("glob.glob", return_value=[]),
    ):
        instance = MockGC.return_value
        instance.chat_completions = MagicMock(return_value=MockAsyncGen([ALL_PASS_RESULT]))

        await _run_qa_loop(ws, SAMPLE_GOOD_DOC, "test_project", "/tmp/docs", "proj-123", mock_db)

    assert mock_engine.pass_qa.called
    mock_engine.pass_qa.assert_called_once_with(3)

    calls = [c.args[0] for c in ws.send_json.call_args_list]
    step_complete_msgs = [c for c in calls if c.get("type") == "step_complete"]
    assert len(step_complete_msgs) == 1
    assert step_complete_msgs[0]["next_step"] == 4
    assert step_complete_msgs[0]["next_step_name"] == "后旺架构设计"


class TestExtractJsonArray:
    def test_plain_json_array(self):
        text = '[{"key": "a", "passed": true}]'
        assert _extract_json_array(text) == [{"key": "a", "passed": True}]

    def test_json_in_code_block(self):
        text = '```json\n[{"key": "a", "passed": false}]\n```'
        assert _extract_json_array(text) == [{"key": "a", "passed": False}]

    def test_json_with_leading_text(self):
        text = '以下是检验结果：\n\n[{"key": "a", "passed": true}]\n\n完毕'
        assert _extract_json_array(text) == [{"key": "a", "passed": True}]

    def test_invalid_text_returns_empty(self):
        assert _extract_json_array("无有效内容") == []

    def test_empty_string(self):
        assert _extract_json_array("") == []


class TestGetNextVersion:
    @pytest.mark.asyncio
    @patch("glob.glob")
    async def test_no_existing_files(self, mock_glob):
        mock_glob.return_value = []
        result = await _get_next_version("/tmp/docs", "test_project")
        assert result == 1

    @pytest.mark.asyncio
    @patch("glob.glob")
    async def test_existing_versions(self, mock_glob):
        mock_glob.return_value = [
            "/tmp/docs/test_project_SRS_V1.md",
            "/tmp/docs/test_project_SRS_V2.md",
            "/tmp/docs/test_project_SRS_V3.md",
        ]
        result = await _get_next_version("/tmp/docs", "test_project")
        assert result == 4

    @pytest.mark.asyncio
    @patch("glob.glob")
    async def test_non_numeric_version_ignored(self, mock_glob):
        mock_glob.return_value = [
            "/tmp/docs/test_project_SRS_V1.md",
            "/tmp/docs/test_project_SRS_Vabc.md",
        ]
        result = await _get_next_version("/tmp/docs", "test_project")
        assert result == 2
