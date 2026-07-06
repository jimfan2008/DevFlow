import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from app.api.ws.step3_qa import _run_qa_loop, _extract_json_result, _get_next_version


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

# 单维度检验结果（新4子步骤格式）
PASS_COMPLETENESS = json.dumps([{"维度": "完整性", "得分": 95, "评定": "合格", "不合格项": []}])
PASS_CONSISTENCY = json.dumps([{"维度": "一致性", "得分": 95, "评定": "合格", "不合格项": []}])
PASS_VERIFIABILITY = json.dumps([{"维度": "可验证性", "得分": 95, "评定": "合格", "不合格项": []}])
PASS_UNAMBIGUITY = json.dumps([{"维度": "无歧义性", "得分": 95, "评定": "合格", "不合格项": []}])
ALL_4_PASS = [PASS_COMPLETENESS, PASS_CONSISTENCY, PASS_VERIFIABILITY, PASS_UNAMBIGUITY]

FAIL_VERIFIABILITY = json.dumps([{"维度": "可验证性", "得分": 60, "评定": "不合格",
  "不合格项": [{"缺陷编号": "VER-001", "严重级别": "MAJOR", "问题": "响应时间指标不可验证",
                "修改方向": "补充具体的测试方法", "证据": "文档中未定义验证方式"}]}])


class MockAsyncGen:
    def __init__(self, chunks):
        self.chunks = list(chunks)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.chunks:
            raise StopAsyncIteration
        return self.chunks.pop(0)


def _make_sequential_side_effect(responses: list):
    """Returns a side_effect that returns MockAsyncGen for each sequential call."""
    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        idx = call_count % len(responses)
        call_count += 1
        return MockAsyncGen([responses[idx]])
    return side_effect


@pytest.mark.asyncio
async def test_qa_all_4_sub_steps_pass():
    """All 4 sub-steps pass on first attempt → should auto-advance to step4."""
    ws = AsyncMock()
    mock_db = MagicMock()
    mock_engine = MagicMock()
    with (
        patch("app.api.ws.step3_qa.GatewayClient") as MockGC,
        patch("builtins.open", MagicMock()),
        patch("app.api.ws.step3_qa.os.makedirs"),
        patch("app.api.ws.step3_qa._get_next_version", AsyncMock(return_value=2)),
        patch("app.services.workflow_engine.WorkflowEngine", return_value=mock_engine),
        patch("glob.glob", return_value=[]),
    ):
        instance = MockGC.return_value
        # 4 sub-steps, each returns pass on first call
        instance.chat_completions = MagicMock(
            side_effect=_make_sequential_side_effect(ALL_4_PASS)
        )

        await _run_qa_loop(ws, SAMPLE_GOOD_DOC, "test_project", "/tmp/docs", "proj-123", mock_db)

    calls = [c.args[0] for c in ws.send_json.call_args_list]
    sub_step_passed = [c for c in calls if c.get("type") == "sub_step_passed"]
    assert len(sub_step_passed) == 4, f"Expected 4 sub_step_passed, got {len(sub_step_passed)}"
    assert mock_engine.complete_step.called, "complete_step should be called"
    assert mock_engine.pass_qa.called, "pass_qa should be called"
    step_complete_msgs = [c for c in calls if c.get("type") == "step_complete"]
    assert len(step_complete_msgs) == 1, "Should have step_complete after all 4 pass"


@pytest.mark.asyncio
async def test_qa_sub_step_fail_then_fix_then_pass():
    """Sub-step 3 (verifiability) fails first, houxing fixes, then passes."""
    ws = AsyncMock()
    mock_db = MagicMock()
    mock_engine = MagicMock()
    doc_path = "/tmp/test_docs"

    with (
        patch("app.api.ws.step3_qa.GatewayClient") as MockGC,
        patch("builtins.open", MagicMock()),
        patch("app.api.ws.step3_qa.os.makedirs"),
        patch("app.api.ws.step3_qa._get_next_version", AsyncMock(return_value=2)),
        patch("app.api.ws.step3_qa.get_shard_config", return_value=[]),
        patch("app.services.workflow_engine.WorkflowEngine", return_value=mock_engine),
        patch("glob.glob", return_value=[]),
    ):
        instance = MockGC.return_value
        # 4 sub-steps: completeness pass, consistency pass,
        # verifiability fail → houxing fix → verifiability pass,
        # unambiguity pass
        instance.chat_completions = MagicMock(
            side_effect=_make_sequential_side_effect(
                [PASS_COMPLETENESS,       # sub-step 1: pass
                 PASS_CONSISTENCY,        # sub-step 2: pass
                 FAIL_VERIFIABILITY,      # sub-step 3: fail (1st attempt)
                 SAMPLE_FIXED_DOC,        # houxing fixes
                 PASS_VERIFIABILITY,      # sub-step 3: pass (2nd attempt)
                 PASS_UNAMBIGUITY]        # sub-step 4: pass
            )
        )

        await _run_qa_loop(ws, SAMPLE_GOOD_DOC, "test_project", doc_path, "proj-123", mock_db)

    calls = [c.args[0] for c in ws.send_json.call_args_list]
    sub_step_passed = [c for c in calls if c.get("type") == "sub_step_passed"]
    assert len(sub_step_passed) == 4, f"Expected 4 passes, got {len(sub_step_passed)}"
    sub_step_failed = [c for c in calls if c.get("type") == "sub_step_failed"]
    assert len(sub_step_failed) == 1, "Should have 1 failure"
    assert mock_engine.complete_step.called, "complete_step should be called"
    step_complete_msgs = [c for c in calls if c.get("type") == "step_complete"]
    assert len(step_complete_msgs) == 1, "Should auto-advance to step4"


@pytest.mark.asyncio
async def test_qa_max_attempts_exhausted():
    """Sub-step exhausts all fix attempts → flow stops."""
    ws = AsyncMock()

    ALWAYS_FAIL = json.dumps([{"维度": "完整性", "得分": 50, "评定": "不合格",
      "不合格项": [{"缺陷编号": "CMP-001", "严重级别": "CRITICAL",
                    "问题": "文档内容不完整", "修改方向": "补充内容", "证据": "全文"}]}])

    # Shared generator that always returns ALWAYS_FAIL (for both hourong inspect and houxing fix)
    _call_counter = [0]

    def _always_fail_side_effect(*args, **kwargs):
        _call_counter[0] += 1
        return MockAsyncGen([ALWAYS_FAIL])

    with (
        patch("app.api.ws.step3_qa.GatewayClient") as MockGC,
        patch("builtins.open", MagicMock()),
        patch("app.api.ws.step3_qa.os.makedirs"),
        patch("app.api.ws.step3_qa._get_next_version", AsyncMock(return_value=2)),
        patch("app.api.ws.step3_qa.get_shard_config", return_value=[]),
    ):
        instance = MockGC.return_value
        instance.chat_completions = MagicMock(side_effect=_always_fail_side_effect)

        await _run_qa_loop(ws, SAMPLE_GOOD_DOC, "test_project", "/tmp/docs")

    calls = [c.args[0] for c in ws.send_json.call_args_list]
    sub_step_passed = [c for c in calls if c.get("type") == "sub_step_passed"]
    assert len(sub_step_passed) == 0, "Should have no passes"
    progress_msgs = [c for c in calls if c.get("type") == "progress"]
    all_progress = " ".join(m.get("content", "") for m in progress_msgs)
    assert "已保存当前状态" in all_progress, "Should save state after exhausting attempts"


@pytest.mark.asyncio
async def test_qa_hourong_retry_on_incomplete():
    """hourong returns incomplete result → retry up to 3 times."""
    ws = AsyncMock()

    with (
        patch("app.api.ws.step3_qa.GatewayClient") as MockGC,
        patch("builtins.open", MagicMock()),
        patch("app.api.ws.step3_qa.os.makedirs"),
    ):
        instance = MockGC.return_value
        # First call returns invalid, second returns valid completeness pass
        incomplete = json.dumps({"维度": "完整性", "得分": 0})  # missing '评定'
        instance.chat_completions = MagicMock(
            side_effect=_make_sequential_side_effect([incomplete, PASS_COMPLETENESS,
                                                       PASS_CONSISTENCY, PASS_VERIFIABILITY,
                                                       PASS_UNAMBIGUITY])
        )

        await _run_qa_loop(ws, SAMPLE_GOOD_DOC, "test_project", "/tmp/docs")

    calls = [c.args[0] for c in ws.send_json.call_args_list]
    sub_step_passed = [c for c in calls if c.get("type") == "sub_step_passed"]
    assert len(sub_step_passed) == 4, "All 4 should eventually pass"


@pytest.mark.asyncio
async def test_qa_pass_saves_document_and_advances_workflow():
    """All 4 pass → document saved + workflow advanced."""
    ws = AsyncMock()
    mock_db = MagicMock()
    mock_engine = MagicMock()

    with (
        patch("app.api.ws.step3_qa.GatewayClient") as MockGC,
        patch("app.services.workflow_engine.WorkflowEngine", return_value=mock_engine) as MockWE,
        patch("builtins.open", MagicMock()),
        patch("app.api.ws.step3_qa.os.makedirs"),
        patch("glob.glob", return_value=[]),
        patch("app.api.ws.step3_qa._get_next_version", AsyncMock(return_value=2)),
    ):
        instance = MockGC.return_value
        instance.chat_completions = MagicMock(
            side_effect=_make_sequential_side_effect(ALL_4_PASS)
        )

        await _run_qa_loop(ws, SAMPLE_GOOD_DOC, "test_project", "/tmp/docs", "proj-123", mock_db)

    # Verify workflow was advanced
    assert mock_engine.complete_step.called, "complete_step should be called"
    assert mock_engine.pass_qa.called, "pass_qa should be called"

    calls = [c.args[0] for c in ws.send_json.call_args_list]
    step_complete_msgs = [c for c in calls if c.get("type") == "step_complete"]
    assert len(step_complete_msgs) == 1, "Should have step_complete"


@pytest.mark.asyncio
async def test_qa_loads_from_shard_index():
    """When index_path provided, load content from shard files."""
    ws = AsyncMock()

    with (
        patch("app.api.ws.step3_qa.GatewayClient") as MockGC,
        patch("builtins.open", MagicMock()),
        patch("app.api.ws.step3_qa.os.makedirs"),
        patch("app.api.ws.step3_qa.os.path.exists", return_value=True),
        patch("app.api.ws.step3_qa.load_all_chapters",
              return_value={"overview": {"content": "# Overview", "path": "/tmp/overview.md"}}),
        patch("app.api.ws.step3_qa._get_next_version", AsyncMock(return_value=2)),
    ):
        ws._current_payload = {"index_path": "/tmp/test_SRS_INDEX.md"}
        instance = MockGC.return_value
        instance.chat_completions = MagicMock(
            side_effect=_make_sequential_side_effect(ALL_4_PASS)
        )

        await _run_qa_loop(ws, "", "test_project", "/tmp/docs")

    calls = [c.args[0] for c in ws.send_json.call_args_list]
    sub_step_passed = [c for c in calls if c.get("type") == "sub_step_passed"]
    assert len(sub_step_passed) == 4, "All 4 should pass when loaded from shards"
