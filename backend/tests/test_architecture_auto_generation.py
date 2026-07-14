"""v4.0 基于需求自动生成架构设计 - TDD测试用例
覆盖 SRS 8.1.4 (第四步 架构设计) 验收标准
"""
import pytest
from app.api.workflow.core import ARCH_DESIGN_DIMENSIONS
from app.api.workflow.step4 import (
    SUB_FLOW_CONFIGS, CHAPTER_MARKER_START, CHAPTER_MARKER_END,
    _build_inspect_prompt, _split_chapters, _build_chapter_prompt,
)
from app.services.workflow_engine import (
    WorkflowEngine, get_default_steps, QA_REQUIRED_STEPS,
)


class TestArchitectureDesignDimensions:
    """架构设计检验维度测试 (SRS 8.1.4)"""

    def test_arch_design_dimensions_count(self):
        assert len(ARCH_DESIGN_DIMENSIONS) == 4

    def test_arch_design_dimension_keys(self):
        keys = {d["key"] for d in ARCH_DESIGN_DIMENSIONS}
        expected = {"arch_reasonableness", "frontend_feasibility", "backend_feasibility", "database_design"}
        assert keys == expected

    def test_arch_reasonableness_dimension(self):
        dim = next(d for d in ARCH_DESIGN_DIMENSIONS if d["key"] == "arch_reasonableness")
        assert "架构合理性" in dim["label"]

    def test_frontend_feasibility_dimension(self):
        dim = next(d for d in ARCH_DESIGN_DIMENSIONS if d["key"] == "frontend_feasibility")
        assert "前端可行性" in dim["label"]

    def test_backend_feasibility_dimension(self):
        dim = next(d for d in ARCH_DESIGN_DIMENSIONS if d["key"] == "backend_feasibility")
        assert "后端可行性" in dim["label"]

    def test_database_design_dimension(self):
        dim = next(d for d in ARCH_DESIGN_DIMENSIONS if d["key"] == "database_design")
        assert "数据库设计" in dim["label"]

    def test_all_dimensions_have_label_and_description(self):
        for d in ARCH_DESIGN_DIMENSIONS:
            assert "key" in d
            assert "label" in d
            assert "description" in d
            assert len(d["key"]) > 0
            assert len(d["label"]) > 0
            assert len(d["description"]) > 0


class TestSubFlowConfigs:
    """Step4 子步骤配置测试"""

    def test_sub_flow_configs_count(self):
        assert len(SUB_FLOW_CONFIGS) == 4

    def test_sub_flow_config_doc_types(self):
        doc_types = [c["doc_type"] for c in SUB_FLOW_CONFIGS]
        expected = ["ARCHITECTURE", "FRONTEND", "BACKEND", "DATABASE"]
        assert doc_types == expected

    def test_sub_flow_config_labels(self):
        labels = [c["label"] for c in SUB_FLOW_CONFIGS]
        assert labels == ["架构设计文档", "前端设计文档", "后端设计文档", "数据库设计脚本"]

    def test_sub_flow_config_dim_keys(self):
        keys = [c["dim"]["key"] for c in SUB_FLOW_CONFIGS]
        expected = ["arch_reasonableness", "frontend_feasibility", "backend_feasibility", "database_design"]
        assert keys == expected

    def test_sub_flow_config_all_have_standards(self):
        for c in SUB_FLOW_CONFIGS:
            assert "standards" in c
            assert len(c["standards"]) >= 3

    def test_sub_flow_architecture_standards_weight(self):
        arch = next(c for c in SUB_FLOW_CONFIGS if c["doc_type"] == "ARCHITECTURE")
        weights = {s["name"]: s["weight"] for s in arch["standards"]}
        assert weights["完整性"] == "critical"
        assert weights["合理性"] == "critical"

    def test_sub_flow_frontend_standards(self):
        fe = next(c for c in SUB_FLOW_CONFIGS if c["doc_type"] == "FRONTEND")
        names = [s["name"] for s in fe["standards"]]
        assert "技术选型" in names
        assert "组件设计" in names
        assert "路由设计" in names
        assert "状态管理" in names
        assert "页面布局" in names

    def test_sub_flow_backend_standards(self):
        be = next(c for c in SUB_FLOW_CONFIGS if c["doc_type"] == "BACKEND")
        names = [s["name"] for s in be["standards"]]
        assert "API设计" in names
        assert "安全策略" in names

    def test_sub_flow_database_standards(self):
        db = next(c for c in SUB_FLOW_CONFIGS if c["doc_type"] == "DATABASE")
        names = [s["name"] for s in db["standards"]]
        assert "规范性" in names
        assert "完整性" in names
        assert "关系设计" in names

    def test_sub_flow_config_gen_instructions_not_empty(self):
        for c in SUB_FLOW_CONFIGS:
            assert len(c["gen_instruction"]) > 0


class TestBuildInspectPrompt:
    """QA检验提示词构建测试"""

    def test_build_inspect_prompt_basic_structure(self):
        dim = {"key": "arch_reasonableness", "label": "架构合理性", "description": "架构设计是否合理"}
        standards = [
            {"name": "完整性", "description": "是否覆盖所有功能", "weight": "critical"},
        ]
        prompt = _build_inspect_prompt(
            doc_path="/path/to/doc.md", dim=dim, standards=standards,
            dim_key="arch_reasonableness",
        )
        assert "架构合理性" in prompt
        assert "/path/to/doc.md" in prompt
        assert "JSON" in prompt
        assert "Q" in prompt

    def test_build_inspect_prompt_has_score_rule(self):
        dim = {"key": "arch_reasonableness", "label": "架构合理性", "description": "架构设计是否合理"}
        standards = [{"name": "完整性", "description": "是否覆盖所有功能", "weight": "critical"}]
        prompt = _build_inspect_prompt(
            doc_path="/path/doc.md", dim=dim, standards=standards,
            dim_key="arch_reasonableness",
        )
        assert "score≥90" in prompt

    def test_build_inspect_prompt_has_standards(self):
        dim = {"key": "arch_reasonableness", "label": "架构合理性", "description": "架构设计是否合理"}
        standards = [
            {"name": "完整性", "description": "是否覆盖所有功能", "weight": "critical"},
            {"name": "合理性", "description": "架构分层是否清晰", "weight": "major"},
        ]
        prompt = _build_inspect_prompt(
            doc_path="/path/doc.md", dim=dim, standards=standards,
            dim_key="arch_reasonableness",
        )
        assert "[CRITICAL]" in prompt
        assert "[MAJOR]" in prompt
        assert "完整性" in prompt
        assert "合理性" in prompt

    def test_build_inspect_prompt_with_prev_feedback(self):
        dim = {"key": "arch_reasonableness", "label": "架构合理性", "description": "测试"}
        standards = [{"name": "完整性", "description": "测试", "weight": "critical"}]
        prompt = _build_inspect_prompt(
            doc_path="/path/doc.md", dim=dim, standards=standards,
            dim_key="arch_reasonableness",
            prev_feedback="上次问题：缺少部署架构",
        )
        assert "收敛性检查" in prompt
        assert "上次检验报告" in prompt
        assert "缺少部署架构" in prompt

    def test_build_inspect_prompt_with_chapter_label(self):
        dim = {"key": "arch_reasonableness", "label": "架构合理性", "description": "测试"}
        standards = [{"name": "完整性", "description": "测试", "weight": "critical"}]
        prompt = _build_inspect_prompt(
            doc_path="/path/doc.md", dim=dim, standards=standards,
            dim_key="arch_reasonableness", chapter_label="functional",
        )
        assert "functional" in prompt

    def test_build_inspect_prompt_output_is_json_only(self):
        dim = {"key": "arch_reasonableness", "label": "架构合理性", "description": "测试"}
        standards = [{"name": "完整性", "description": "测试", "weight": "critical"}]
        prompt = _build_inspect_prompt(
            doc_path="/path/doc.md", dim=dim, standards=standards,
            dim_key="arch_reasonableness",
        )
        assert "只输出 JSON" in prompt
        assert "不要 markdown" in prompt

    def test_build_inspect_prompt_dim_key_in_output(self):
        dim = {"key": "arch_reasonableness", "label": "架构合理性", "description": "测试"}
        standards = [{"name": "完整性", "description": "测试", "weight": "critical"}]
        prompt = _build_inspect_prompt(
            doc_path="/path/doc.md", dim=dim, standards=standards,
            dim_key="arch_reasonableness",
        )
        assert '"key": "arch_reasonableness"' in prompt


class TestSplitChapters:
    """文档分片功能测试"""

    def test_split_chapters_empty_text(self):
        result = _split_chapters("")
        assert result == {}

    def test_split_chapters_no_markers(self):
        result = _split_chapters("普通文本没有分片标记")
        assert result == {}

    def test_split_chapters_single_chapter(self):
        text = f"{CHAPTER_MARKER_START} functional {CHAPTER_MARKER_END}\n功能描述内容"
        result = _split_chapters(text)
        assert "functional" in result
        assert result["functional"] == "功能描述内容"

    def test_split_chapters_multiple_chapters(self):
        text = (
            f"{CHAPTER_MARKER_START} functional {CHAPTER_MARKER_END}\n"
            f"功能描述内容\n"
            f"{CHAPTER_MARKER_START} technical {CHAPTER_MARKER_END}\n"
            f"技术描述内容"
        )
        result = _split_chapters(text)
        assert "functional" in result
        assert "technical" in result
        assert result["functional"] == "功能描述内容"
        assert result["technical"] == "技术描述内容"

    def test_split_chapters_ignores_empty_chapters(self):
        text = f"{CHAPTER_MARKER_START} empty {CHAPTER_MARKER_END}\n   \n"
        result = _split_chapters(text)
        assert "empty" not in result

    def test_split_chapters_preserves_whitespace(self):
        text = f"{CHAPTER_MARKER_START} api {CHAPTER_MARKER_END}\n接口定义：\n  - GET /users\n  - POST /users"
        result = _split_chapters(text)
        assert "api" in result
        assert "GET /users" in result["api"]

    def test_split_chapters_no_trailing_content_after_last(self):
        text = f"{CHAPTER_MARKER_START} intro {CHAPTER_MARKER_END}\n介绍内容"
        result = _split_chapters(text)
        assert len(result) == 1

    def test_split_chapters_consecutive_chapters(self):
        text = (
            f"{CHAPTER_MARKER_START} ch1 {CHAPTER_MARKER_END}\n内容1\n"
            f"{CHAPTER_MARKER_START} ch2 {CHAPTER_MARKER_END}\n内容2\n"
            f"{CHAPTER_MARKER_START} ch3 {CHAPTER_MARKER_END}\n内容3"
        )
        result = _split_chapters(text)
        assert len(result) == 3


class TestBuildChapterPrompt:
    """后旺章节生成提示词构建测试"""

    def test_build_chapter_prompt_has_role(self):
        prompt = _build_chapter_prompt(
            doc_type="ARCHITECTURE", label="架构设计文档",
            gen_instruction="系统整体架构图描述",
            requirement="测试需求文档",
            docs_dir="/tmp/docs", slug="test-project",
        )
        assert "后旺" in prompt
        assert "HouWang" in prompt

    def test_build_chapter_prompt_has_requirement(self):
        prompt = _build_chapter_prompt(
            doc_type="ARCHITECTURE", label="架构设计文档",
            gen_instruction="系统整体架构图描述",
            requirement="这是一个测试需求文档内容",
            docs_dir="/tmp/docs", slug="test-project",
        )
        assert "测试需求文档内容" in prompt

    def test_build_chapter_prompt_has_chapter_marker(self):
        prompt = _build_chapter_prompt(
            doc_type="ARCHITECTURE", label="架构设计文档",
            gen_instruction="系统整体架构图描述",
            requirement="测试需求",
            docs_dir="/tmp/docs", slug="test-project",
        )
        assert CHAPTER_MARKER_START in prompt

    def test_build_chapter_prompt_no_reasoning_instruction(self):
        prompt = _build_chapter_prompt(
            doc_type="ARCHITECTURE", label="架构设计文档",
            gen_instruction="系统整体架构图描述",
            requirement="测试需求",
            docs_dir="/tmp/docs", slug="test-project",
        )
        assert "不要输出推理过程" in prompt


class TestStep4WorkflowIntegration:
    """Step4 工作流集成测试（静态定义验证）"""

    def test_step_4_definition(self):
        steps = get_default_steps()
        step4 = next(s for s in steps if s.step_number == 4)
        assert step4.executor_role == "houwang"

    def test_step_4_is_qa_required(self):
        assert 4 in QA_REQUIRED_STEPS

    def test_step_4_follows_step_3_sequentially(self):
        steps = get_default_steps()
        step3 = next(s for s in steps if s.step_number == 3)
        step4 = next(s for s in steps if s.step_number == 4)
        assert step3.step_number < step4.step_number
        assert step3.executor_role == "houxing"
        assert step4.executor_role == "houwang"

    def test_step_4_engine_initialization(self):
        engine = WorkflowEngine(project_id="test-project")
        assert engine.current_step >= 1

    def test_step_4_step_names_in_default_steps(self):
        steps = get_default_steps()
        step4 = next(s for s in steps if s.step_number == 4)
        assert len(step4.name) > 0


class TestArchitectureAutoGenerationEdgeCases:
    """架构自动生成边界情况测试"""

    def test_sub_flow_config_all_have_gen_instruction(self):
        for c in SUB_FLOW_CONFIGS:
            assert len(c["gen_instruction"]) > 10

    def test_sub_flow_config_standards_have_weights(self):
        valid_weights = {"critical", "major", "minor"}
        for c in SUB_FLOW_CONFIGS:
            for s in c["standards"]:
                assert s["weight"] in valid_weights, \
                    f"Invalid weight '{s['weight']}' in {c['doc_type']}: {s['name']}"

    def test_arch_design_dimension_no_duplicates(self):
        keys = [d["key"] for d in ARCH_DESIGN_DIMENSIONS]
        assert len(keys) == len(set(keys))

    def test_sub_flow_config_no_duplicate_doc_types(self):
        doc_types = [c["doc_type"] for c in SUB_FLOW_CONFIGS]
        assert len(doc_types) == len(set(doc_types))
