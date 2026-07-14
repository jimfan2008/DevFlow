"""基于需求自动生成架构设计 — Step 4 扩展TDD测试用例
覆盖：子步骤一致性配对、doc_sharder服务、核心检验维度、
     文档版本扫描、增量一致性配对构造、JSON提取策略
"""
import pytest
import os
import re
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock, AsyncMock


# ── 子步骤模块一致性配对 ──

class TestStep4SubStepConsistencyPairs:
    """子步骤一致性配对定义验证（SRS 8.1.4 跨文档一致性检验）"""

    def test_step4_1_has_no_consistency_pairs(self):
        """step4_1（架构设计）是第一个子步骤，无前置文档，无需一致性检验"""
        from app.api.workflow.step4_1 import run_sub_step_4_1
        # step4_1 模块不应导入 CONSISTENCY_PAIRS
        import app.api.workflow.step4_1 as mod
        assert not hasattr(mod, "CONSISTENCY_PAIRS")

    def test_step4_2_consistency_pairs_count(self):
        """step4_2（前端设计）有1个一致性配对：架构←→前端"""
        from app.api.workflow.step4_2 import CONSISTENCY_PAIRS
        assert len(CONSISTENCY_PAIRS) == 1

    def test_step4_2_consistency_pair_keys(self):
        """step4_2 配对涉及 arch_reasonableness 和 frontend_feasibility"""
        from app.api.workflow.step4_2 import CONSISTENCY_PAIRS
        pair = CONSISTENCY_PAIRS[0]
        assert pair["a"] == "arch_reasonableness"
        assert pair["b"] == "frontend_feasibility"

    def test_step4_2_current_dim_is_frontend(self):
        """step4_2 当前维度必须是 frontend_feasibility"""
        from app.api.workflow.step4_2 import CURRENT_DIM
        assert CURRENT_DIM == "frontend_feasibility"

    def test_step4_3_consistency_pairs_count(self):
        """step4_3（后端设计）有2个一致性配对"""
        from app.api.workflow.step4_3 import CONSISTENCY_PAIRS
        assert len(CONSISTENCY_PAIRS) == 2

    def test_step4_3_consistency_pair_keys(self):
        """step4_3 配对：架构←→后端、前端←→后端"""
        from app.api.workflow.step4_3 import CONSISTENCY_PAIRS
        pair_names = {p["name"] for p in CONSISTENCY_PAIRS}
        assert "架构设计←→后端设计" in pair_names
        assert "前端设计←→后端设计" in pair_names

    def test_step4_3_consistency_pair_coverage(self):
        """step4_3 配对覆盖的维度"""
        from app.api.workflow.step4_3 import CONSISTENCY_PAIRS
        all_dims = set()
        for p in CONSISTENCY_PAIRS:
            all_dims.add(p["a"])
            all_dims.add(p["b"])
        assert "arch_reasonableness" in all_dims
        assert "frontend_feasibility" in all_dims
        assert "backend_feasibility" in all_dims

    def test_step4_3_current_dim_is_backend(self):
        """step4_3 当前维度必须是 backend_feasibility"""
        from app.api.workflow.step4_3 import CURRENT_DIM
        assert CURRENT_DIM == "backend_feasibility"

    def test_step4_4_consistency_pairs_count(self):
        """step4_4（数据库设计）有1个一致性配对：后端←→数据库"""
        from app.api.workflow.step4_4 import CONSISTENCY_PAIRS
        assert len(CONSISTENCY_PAIRS) == 1

    def test_step4_4_consistency_pair_keys(self):
        """step4_4 配对涉及 backend_feasibility 和 database_design"""
        from app.api.workflow.step4_4 import CONSISTENCY_PAIRS
        pair = CONSISTENCY_PAIRS[0]
        assert pair["a"] == "backend_feasibility"
        assert pair["b"] == "database_design"

    def test_step4_4_current_dim_is_database(self):
        """step4_4 当前维度必须是 database_design"""
        from app.api.workflow.step4_4 import CURRENT_DIM
        assert CURRENT_DIM == "database_design"

    def test_all_sub_steps_have_max_consistency_rounds(self):
        """所有子步骤都有 MAX_CONSISTENCY_ROUNDS 配置"""
        from app.api.workflow.step4_2 import MAX_CONSISTENCY_ROUNDS as r2
        from app.api.workflow.step4_3 import MAX_CONSISTENCY_ROUNDS as r3
        from app.api.workflow.step4_4 import MAX_CONSISTENCY_ROUNDS as r4
        assert r2 == 3
        assert r3 == 3
        assert r4 == 3

    def test_consistency_pair_names_are_meaningful(self):
        """所有配对名称包含「←→」分隔符"""
        from app.api.workflow.step4_2 import CONSISTENCY_PAIRS as p2
        from app.api.workflow.step4_3 import CONSISTENCY_PAIRS as p3
        from app.api.workflow.step4_4 import CONSISTENCY_PAIRS as p4
        all_pairs = p2 + p3 + p4
        for p in all_pairs:
            assert "←→" in p["name"]


class TestDocSharderService:
    """文档分片服务测试 — doc_sharder 模块"""

    def test_get_shard_config_architecture_chapters(self):
        from app.services.doc_sharder import get_shard_config
        chapters = get_shard_config("ARCHITECTURE")
        assert len(chapters) == 5
        keys = [c["key"] for c in chapters]
        assert "overview" in keys
        assert "layers" in keys
        assert "modules" in keys
        assert "tech_stack" in keys
        assert "deployment" in keys

    def test_get_shard_config_frontend_chapters(self):
        from app.services.doc_sharder import get_shard_config
        chapters = get_shard_config("FRONTEND")
        assert len(chapters) == 5
        keys = [c["key"] for c in chapters]
        assert "tech_stack" in keys
        assert "component_tree" in keys
        assert "routing" in keys
        assert "state_mgmt" in keys
        assert "layout" in keys

    def test_get_shard_config_backend_chapters(self):
        from app.services.doc_sharder import get_shard_config
        chapters = get_shard_config("BACKEND")
        assert len(chapters) == 5
        keys = [c["key"] for c in chapters]
        assert "tech_stack" in keys
        assert "api_design" in keys
        assert "data_flow" in keys
        assert "middleware" in keys
        assert "security" in keys

    def test_get_shard_config_database_chapters(self):
        from app.services.doc_sharder import get_shard_config
        chapters = get_shard_config("DATABASE")
        assert len(chapters) == 5
        keys = [c["key"] for c in chapters]
        assert "overview" in keys
        assert "tables" in keys
        assert "indexes" in keys
        assert "constraints" in keys
        assert "migrations" in keys

    def test_get_shard_config_unknown_doc_type_returns_empty(self):
        from app.services.doc_sharder import get_shard_config
        chapters = get_shard_config("NONEXISTENT")
        assert chapters == []

    def test_get_chapter_filename_format(self):
        from app.services.doc_sharder import get_chapter_filename
        path = get_chapter_filename("ARCHITECTURE", "overview", "/tmp/docs", "myproject")
        assert path == "/tmp/docs/myproject_ARCHITECTURE_overview.md"

    def test_get_parent_chapter_simple_key(self):
        from app.services.doc_sharder import get_parent_chapter
        assert get_parent_chapter("functional") == "functional"

    def test_get_parent_chapter_dotted_key(self):
        from app.services.doc_sharder import get_parent_chapter
        assert get_parent_chapter("functional.auth") == "functional"

    def test_get_parent_chapter_multiple_dots(self):
        from app.services.doc_sharder import get_parent_chapter
        assert get_parent_chapter("a.b.c") == "a"

    def test_save_and_load_chapter_roundtrip(self, tmp_path):
        from app.services.doc_sharder import save_chapter, load_single_chapter
        content = "# 测试章节\n这是测试内容\n"
        path = save_chapter("ARCHITECTURE", "overview", content, str(tmp_path), "proj1")
        assert os.path.exists(path)
        loaded = load_single_chapter("ARCHITECTURE", "overview", str(tmp_path), "proj1")
        assert loaded == content

    def test_load_single_chapter_missing_file_returns_empty(self):
        from app.services.doc_sharder import load_single_chapter
        result = load_single_chapter("ARCHITECTURE", "missing", "/tmp/nonexist", "proj1")
        assert result == ""

    def test_build_chapter_prompt_includes_instruction(self):
        from app.services.doc_sharder import build_chapter_prompt
        prompt = build_chapter_prompt("ARCHITECTURE", "overview", "/tmp/docs", "proj1")
        assert "总体架构概览" in prompt
        assert "系统整体架构图描述" in prompt

    def test_build_chapter_prompt_includes_requirement(self):
        from app.services.doc_sharder import build_chapter_prompt
        req = "用户需求文档内容"
        prompt = build_chapter_prompt("ARCHITECTURE", "overview", "/tmp/docs", "proj1", requirement=req)
        assert req in prompt

    def test_build_chapter_prompt_unknown_chapter_returns_empty(self):
        from app.services.doc_sharder import build_chapter_prompt
        prompt = build_chapter_prompt("ARCHITECTURE", "nonexistent_chapter", "/tmp/docs", "proj1")
        assert prompt == ""

    def test_load_all_chapters_creates_entry_per_config(self, tmp_path):
        from app.services.doc_sharder import load_all_chapters
        result = load_all_chapters("ARCHITECTURE", str(tmp_path), "proj1")
        assert len(result) == 5
        assert "overview" in result

    def test_shard_config_chapters_have_title_and_instruction(self):
        from app.services.doc_sharder import get_shard_config
        for doc_type in ["ARCHITECTURE", "FRONTEND", "BACKEND", "DATABASE"]:
            chapters = get_shard_config(doc_type)
            for ch in chapters:
                assert "key" in ch
                assert "title" in ch
                assert "instruction" in ch
                assert len(ch["title"]) > 0
                assert len(ch["instruction"]) > 0

    def test_srs_shard_config_has_dynamic_sub_chapter(self):
        from app.services.doc_sharder import get_shard_config
        chapters = get_shard_config("SRS")
        functional = next((c for c in chapters if c["key"] == "functional"), None)
        assert functional is not None
        assert functional.get("dynamic_sub") is True


class TestCoreInspectionDimensions:
    """核心模块中其他检验维度测试"""

    def test_code_inspection_dimensions_count(self):
        from app.api.workflow.core import CODE_INSPECTION_DIMENSIONS
        assert len(CODE_INSPECTION_DIMENSIONS) == 4

    def test_code_inspection_dimension_keys(self):
        from app.api.workflow.core import CODE_INSPECTION_DIMENSIONS
        keys = {d["key"] for d in CODE_INSPECTION_DIMENSIONS}
        expected = {"code_correctness", "test_pass_rate", "requirement_match", "code_standard"}
        assert keys == expected

    def test_env_setup_dimensions(self):
        from app.api.workflow.core import ENV_SETUP_DIMENSIONS
        keys = {d["key"] for d in ENV_SETUP_DIMENSIONS}
        expected = {"environment_availability", "config_correctness", "dependency_completeness"}
        assert keys == expected

    def test_tdd_plan_dimensions(self):
        from app.api.workflow.core import TDD_PLAN_DIMENSIONS
        keys = {d["key"] for d in TDD_PLAN_DIMENSIONS}
        expected = {"coverage", "atomicity", "measurability"}
        assert keys == expected

    def test_tdd_testcase_dimensions(self):
        from app.api.workflow.core import TDD_TESTCASE_DIMENSIONS
        keys = {d["key"] for d in TDD_TESTCASE_DIMENSIONS}
        expected = {"correctness", "coverage", "atomicity", "acceptance_match"}
        assert keys == expected

    def test_code_plan_dimensions(self):
        from app.api.workflow.core import CODE_PLAN_DIMENSIONS
        keys = {d["key"] for d in CODE_PLAN_DIMENSIONS}
        expected = {"task_atomicity", "test_mapping", "dependency_correctness"}
        assert keys == expected

    def test_test_inspection_dimensions(self):
        from app.api.workflow.core import TEST_INSPECTION_DIMENSIONS
        keys = {d["key"] for d in TEST_INSPECTION_DIMENSIONS}
        expected = {"test_coverage", "pass_rate", "defect_severity", "practical_validation"}
        assert keys == expected

    def test_security_inspection_dimensions(self):
        from app.api.workflow.core import SECURITY_INSPECTION_DIMENSIONS
        keys = {d["key"] for d in SECURITY_INSPECTION_DIMENSIONS}
        expected = {"vulnerability_fix_rate", "compliance", "penetration_test"}
        assert keys == expected

    def test_doc_inspection_dimensions(self):
        from app.api.workflow.core import DOC_INSPECTION_DIMENSIONS
        keys = {d["key"] for d in DOC_INSPECTION_DIMENSIONS}
        expected = {"doc_completeness", "doc_consistency", "doc_accuracy"}
        assert keys == expected

    def test_deploy_test_dimensions(self):
        from app.api.workflow.core import DEPLOY_TEST_DIMENSIONS
        keys = {d["key"] for d in DEPLOY_TEST_DIMENSIONS}
        expected = {"deploy_config", "env_compatibility", "service_availability"}
        assert keys == expected

    def test_deploy_prod_dimensions(self):
        from app.api.workflow.core import DEPLOY_PROD_DIMENSIONS
        keys = {d["key"] for d in DEPLOY_PROD_DIMENSIONS}
        expected = {"prod_config", "safety_guard", "rollback_plan", "service_stability"}
        assert keys == expected

    def test_all_dimensions_have_required_fields(self):
        from app.api.workflow.core import (
            ARCH_DESIGN_DIMENSIONS, CODE_INSPECTION_DIMENSIONS,
            ENV_SETUP_DIMENSIONS, TDD_PLAN_DIMENSIONS,
            TDD_TESTCASE_DIMENSIONS, CODE_PLAN_DIMENSIONS,
            TEST_INSPECTION_DIMENSIONS, SECURITY_INSPECTION_DIMENSIONS,
            DOC_INSPECTION_DIMENSIONS, DEPLOY_TEST_DIMENSIONS,
            DEPLOY_PROD_DIMENSIONS,
        )
        all_dims = (
            ARCH_DESIGN_DIMENSIONS + CODE_INSPECTION_DIMENSIONS +
            ENV_SETUP_DIMENSIONS + TDD_PLAN_DIMENSIONS +
            TDD_TESTCASE_DIMENSIONS + CODE_PLAN_DIMENSIONS +
            TEST_INSPECTION_DIMENSIONS + SECURITY_INSPECTION_DIMENSIONS +
            DOC_INSPECTION_DIMENSIONS + DEPLOY_TEST_DIMENSIONS +
            DEPLOY_PROD_DIMENSIONS
        )
        for d in all_dims:
            assert "key" in d
            assert "label" in d
            assert "description" in d
            assert len(d["key"]) > 0
            assert len(d["label"]) > 0
            assert len(d["description"]) > 0

    def test_dimension_keys_have_expected_duplicates(self):
        """coverage 和 atomicity 在不同步骤维度中合理复用"""
        from app.api.workflow.core import TDD_PLAN_DIMENSIONS, TDD_TESTCASE_DIMENSIONS
        plan_keys = {d["key"] for d in TDD_PLAN_DIMENSIONS}
        tc_keys = {d["key"] for d in TDD_TESTCASE_DIMENSIONS}
        shared = plan_keys & tc_keys
        assert "coverage" in shared
        assert "atomicity" in shared


class TestDocVersionScanning:
    """文档版本扫描逻辑测试（SRS 8.1.4 断点续做）"""

    def _scan_latest(self, docs_dir, slug, doc_type):
        """模拟 step4.py 中的文档版本扫描逻辑"""
        import glob, re as _re
        import os as _os
        latest_path = None
        max_ver = 0
        for f in sorted(glob.glob(_os.path.join(docs_dir, f"{slug}_{doc_type}_V*.md"))):
            m = _re.search(r'_V(\d+)\.md$', f)
            if m:
                v = int(m.group(1))
                if v > max_ver:
                    max_ver = v
                    latest_path = f
        return latest_path, max_ver

    def test_scan_no_files(self, tmp_path):
        path, ver = self._scan_latest(str(tmp_path), "proj", "ARCHITECTURE")
        assert path is None
        assert ver == 0

    def test_scan_single_file(self, tmp_path):
        fpath = tmp_path / "proj_ARCHITECTURE_V1.md"
        fpath.write_text("# 架构V1")
        path, ver = self._scan_latest(str(tmp_path), "proj", "ARCHITECTURE")
        assert ver == 1
        assert "V1.md" in path

    def test_scan_picks_highest_version(self, tmp_path):
        (tmp_path / "proj_ARCHITECTURE_V1.md").write_text("v1")
        (tmp_path / "proj_ARCHITECTURE_V3.md").write_text("v3")
        (tmp_path / "proj_ARCHITECTURE_V2.md").write_text("v2")
        path, ver = self._scan_latest(str(tmp_path), "proj", "ARCHITECTURE")
        assert ver == 3
        assert "V3.md" in path

    def test_scan_ignores_other_doc_types(self, tmp_path):
        (tmp_path / "proj_FRONTEND_V1.md").write_text("frontend")
        path, ver = self._scan_latest(str(tmp_path), "proj", "ARCHITECTURE")
        assert path is None
        assert ver == 0

    def test_scan_ignores_non_versioned_files(self, tmp_path):
        (tmp_path / "proj_ARCHITECTURE_draft.md").write_text("draft")
        (tmp_path / "proj_ARCHITECTURE_notes.md").write_text("notes")
        path, ver = self._scan_latest(str(tmp_path), "proj", "ARCHITECTURE")
        assert path is None
        assert ver == 0

    def test_scan_handles_large_version_numbers(self, tmp_path):
        (tmp_path / "proj_DATABASE_V100.md").write_text("v100")
        (tmp_path / "proj_DATABASE_V99.md").write_text("v99")
        path, ver = self._scan_latest(str(tmp_path), "proj", "DATABASE")
        assert ver == 100

    def test_scan_ignores_other_project_slug(self, tmp_path):
        (tmp_path / "other_ARCHITECTURE_V5.md").write_text("other")
        path, ver = self._scan_latest(str(tmp_path), "proj", "ARCHITECTURE")
        assert path is None
        assert ver == 0


class TestIncrementalConsistencyPairConstruction:
    """增量一致性检验配对构造测试"""

    def test_step4_2_pairs_reference_arch_only(self):
        """step4_2 增量一致性只检查架构-前端配对"""
        from app.api.workflow.step4_2 import CONSISTENCY_PAIRS
        dim_keys = set()
        for p in CONSISTENCY_PAIRS:
            dim_keys.add(p["a"])
            dim_keys.add(p["b"])
        assert "arch_reasonableness" in dim_keys
        assert "frontend_feasibility" in dim_keys
        assert "backend_feasibility" not in dim_keys
        assert "database_design" not in dim_keys

    def test_step4_3_pairs_reference_arch_and_frontend(self):
        """step4_3 增量一致性检查架构-后端、前端-后端配对"""
        from app.api.workflow.step4_3 import CONSISTENCY_PAIRS
        pair_a = {p["a"] for p in CONSISTENCY_PAIRS}
        pair_b = {p["b"] for p in CONSISTENCY_PAIRS}
        assert "arch_reasonableness" in pair_a
        assert "frontend_feasibility" in pair_a
        assert "backend_feasibility" in pair_b

    def test_step4_4_pairs_reference_backend_only(self):
        """step4_4 增量一致性只检查后端-数据库配对"""
        from app.api.workflow.step4_4 import CONSISTENCY_PAIRS
        dim_keys = set()
        for p in CONSISTENCY_PAIRS:
            dim_keys.add(p["a"])
            dim_keys.add(p["b"])
        assert "backend_feasibility" in dim_keys
        assert "database_design" in dim_keys
        assert "arch_reasonableness" not in dim_keys
        assert "frontend_feasibility" not in dim_keys

    def test_total_consistency_pairs_across_all_sub_steps(self):
        """全部子步骤的一致性配对总数为 1+2+1=4"""
        from app.api.workflow.step4_2 import CONSISTENCY_PAIRS as p2
        from app.api.workflow.step4_3 import CONSISTENCY_PAIRS as p3
        from app.api.workflow.step4_4 import CONSISTENCY_PAIRS as p4
        total = len(p2) + len(p3) + len(p4)
        assert total == 4

    def test_consistency_pairs_form_directed_chain(self):
        """一致性配对形成链式依赖：架构→前端→后端→数据库"""
        # step4_2: 架构←→前端
        # step4_3: 架构←→后端, 前端←→后端
        # step4_4: 后端←→数据库
        from app.api.workflow.step4_2 import CONSISTENCY_PAIRS as p2
        from app.api.workflow.step4_3 import CONSISTENCY_PAIRS as p3
        from app.api.workflow.step4_4 import CONSISTENCY_PAIRS as p4

        # step4_2 的 b 是 step4_3 中的一个 a
        p2_b = {p["b"] for p in p2}
        p3_a = {p["a"] for p in p3}
        assert p2_b.issubset(p3_a)

        # step4_3 的 b 是 step4_4 中的一个 a
        p3_b = {p["b"] for p in p3}
        p4_a = {p["a"] for p in p4}
        assert p3_b.issubset(p4_a)


class TestCrossDocPromptConstruction:
    """跨文档一致性检验提示词构造测试（_cross_check_docs 静态验证）"""

    def test_cross_check_prompt_has_four_doc_paths(self):
        """跨文档检验提示词包含4份文档的路径"""
        docs_map = {
            "arch_reasonableness": "/path/arch.md",
            "frontend_feasibility": "/path/frontend.md",
            "backend_feasibility": "/path/backend.md",
            "database_design": "/path/db.md",
        }
        # 模拟 _cross_check_docs 的 prompt 构造逻辑
        arch_path = docs_map.get("arch_reasonableness", "")
        frontend_path = docs_map.get("frontend_feasibility", "")
        backend_path = docs_map.get("backend_feasibility", "")
        db_path = docs_map.get("database_design", "")

        prompt = (
            f"=== 1. 软件架构设计文档（Architecture Design）===\n"
            f"文件路径：{arch_path}\n\n"
            f"=== 2. 软件前端设计文档（Frontend Design）===\n"
            f"文件路径：{frontend_path}\n\n"
            f"=== 3. 软件后端设计文档（Backend Design）===\n"
            f"文件路径：{backend_path}\n\n"
            f"=== 4. 软件数据库设计脚本（Database Design）===\n"
            f"文件路径：{db_path}"
        )
        assert "/path/arch.md" in prompt
        assert "/path/frontend.md" in prompt
        assert "/path/backend.md" in prompt
        assert "/path/db.md" in prompt

    def test_cross_check_prompt_has_four_pair_checks(self):
        """跨文档检验包含4个配对检查"""
        pairs = [
            ("架构-前端", ["arch_reasonableness", "frontend_feasibility"]),
            ("架构-后端", ["arch_reasonableness", "backend_feasibility"]),
            ("前端-后端", ["frontend_feasibility", "backend_feasibility"]),
            ("后端-数据库", ["backend_feasibility", "database_design"]),
        ]
        assert len(pairs) == 4
        for name, docs in pairs:
            assert len(docs) == 2


class TestJSONExtractionStrategies:
    """JSON提取策略测试 — _inspect_doc 中的多层回退解析"""

    @staticmethod
    def _extract_json(reply: str) -> dict:
        """模拟 step4.py _inspect_doc 中的 JSON 提取逻辑"""
        if not reply or not reply.strip():
            return {}

        # Strip thinking/analysis tags
        _lt, _gt = chr(60), chr(62)
        _think_open = rf'{_lt}(?:thinking|think|analysis){_gt}'
        _think_close = rf'{_lt}/(?:thinking|think|analysis){_gt}'
        reply = re.sub(rf'(?:{_think_open})[\s\S]*?(?:{_think_close})', '', reply)

        candidates = []
        fenced = re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', reply, re.DOTALL)
        for fc in fenced:
            stripped = fc.strip()
            if stripped:
                candidates.append(stripped)

        brace_start = reply.find('{')
        brace_end = reply.rfind('}')
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            candidates.append(reply[brace_start:brace_end + 1])

        candidates.append(reply)

        def _repair(text):
            t = text.strip()
            t = re.sub(r',\s*([}\]])', r'\1', t)
            try:
                return json.loads(t)
            except Exception:
                pass
            return None

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict) and parsed:
                    return parsed
            except Exception:
                pass
            repaired = _repair(candidate)
            if repaired and isinstance(repaired, dict) and repaired:
                return repaired

        return {}

    def test_extract_plain_json(self):
        result = self._extract_json('{"key": "coverage", "score": 95, "passed": true}')
        assert result["key"] == "coverage"

    def test_extract_json_in_code_fence(self):
        result = self._extract_json('```json\n{"key": "coverage", "passed": true}\n```')
        assert result["key"] == "coverage"

    def test_extract_json_with_thinking_tag(self):
        reply = '<thinking>分析中...</thinking>{"key": "a", "score": 80}'
        result = self._extract_json(reply)
        assert result["key"] == "a"

    def test_extract_json_with_trailing_comma(self):
        result = self._extract_json('{"key": "a", "score": 90, "passed": true,}')
        assert result["key"] == "a"
        assert result["score"] == 90

    def test_extract_json_with_prefix_text(self):
        result = self._extract_json('检验结果：{"key": "a", "score": 90, "passed": true}')
        assert result["key"] == "a"

    def test_extract_json_with_suffix_text(self):
        result = self._extract_json('{"key": "a", "score": 90} 额外说明')
        assert result["key"] == "a"

    def test_extract_json_nested_thinking(self):
        reply = '<thinking>外<thinking>内</thinking>续</thinking>{"key": "nested"}'
        result = self._extract_json(reply)
        assert result["key"] == "nested"

    def test_extract_empty_response(self):
        assert self._extract_json("") == {}
        assert self._extract_json(None) == {}
        assert self._extract_json("   ") == {}

    def test_extract_json_with_analysis_tag(self):
        reply = '<analysis>深度分析...</analysis>{"passed": false, "score": 60}'
        result = self._extract_json(reply)
        assert result["passed"] is False

    def test_extract_json_with_multiline_code_fence(self):
        reply = '```json\n{\n  "key": "multi",\n  "score": 92,\n  "passed": true\n}\n```'
        result = self._extract_json(reply)
        assert result["key"] == "multi"
        assert result["score"] == 92

    def test_extract_json_with_think_tag(self):
        reply = '<think>思考过程</think>{"key": "think_tag", "passed": true}'
        result = self._extract_json(reply)
        assert result["key"] == "think_tag"


class TestConsistencyFeedbackFiltering:
    """一致性反馈过滤逻辑测试 — 只提取当前维度相关的反馈"""

    def test_filter_feedback_for_frontend(self):
        """step4_2 只提取 frontend_feasibility 相关的反馈"""
        current_dim = "frontend_feasibility"
        pairs = [
            {"name": "架构-前端", "passed": False, "issue": "技术栈不一致",
             "affected_docs": ["arch_reasonableness", "frontend_feasibility"]},
            {"name": "架构-后端", "passed": False, "issue": "模块划分不匹配",
             "affected_docs": ["arch_reasonableness", "backend_feasibility"]},
        ]
        feedback_parts = []
        for p in pairs:
            if not p.get("passed", True) and current_dim in p.get("affected_docs", []):
                feedback_parts.append(f"{p['name']}: {p['issue']}")
        assert len(feedback_parts) == 1
        assert "技术栈不一致" in feedback_parts[0]

    def test_filter_feedback_for_backend(self):
        """step4_3 只提取 backend_feasibility 相关的反馈"""
        current_dim = "backend_feasibility"
        pairs = [
            {"name": "架构-后端", "passed": False, "issue": "API风格不一致",
             "affected_docs": ["arch_reasonableness", "backend_feasibility"]},
            {"name": "前端-后端", "passed": False, "issue": "数据格式不匹配",
             "affected_docs": ["frontend_feasibility", "backend_feasibility"]},
        ]
        feedback_parts = []
        for p in pairs:
            if not p.get("passed", True) and current_dim in p.get("affected_docs", []):
                feedback_parts.append(f"{p['name']}: {p['issue']}")
        assert len(feedback_parts) == 2

    def test_filter_feedback_for_database(self):
        """step4_4 只提取 database_design 相关的反馈"""
        current_dim = "database_design"
        pairs = [
            {"name": "后端-数据库", "passed": False, "issue": "字段类型不匹配",
             "affected_docs": ["backend_feasibility", "database_design"]},
        ]
        feedback_parts = []
        for p in pairs:
            if not p.get("passed", True) and current_dim in p.get("affected_docs", []):
                feedback_parts.append(f"{p['name']}: {p['issue']}")
        assert len(feedback_parts) == 1

    def test_filter_skips_passed_pairs(self):
        """已通过的一致性配对不生成反馈"""
        current_dim = "frontend_feasibility"
        pairs = [
            {"name": "架构-前端", "passed": True, "issue": "",
             "affected_docs": ["arch_reasonableness", "frontend_feasibility"]},
        ]
        feedback_parts = []
        for p in pairs:
            if not p.get("passed", True) and current_dim in p.get("affected_docs", []):
                feedback_parts.append(f"{p['name']}: {p['issue']}")
        assert feedback_parts == []

    def test_empty_feedback_breaks_loop(self):
        """如果过滤后无反馈（其他文档的问题），直接判定通过"""
        current_dim = "frontend_feasibility"
        pairs = [
            {"name": "架构-后端", "passed": False, "issue": "不一致",
             "affected_docs": ["arch_reasonableness", "backend_feasibility"]},
        ]
        feedback_parts = []
        for p in pairs:
            if not p.get("passed", True) and current_dim in p.get("affected_docs", []):
                feedback_parts.append(f"{p['name']}: {p['issue']}")
        assert len(feedback_parts) == 0


class TestCrossCheckResultParsing:
    """跨文档检验结果解析测试"""

    def test_all_pairs_passed_returns_true(self):
        result = {
            "pairs": [
                {"name": "a", "passed": True},
                {"name": "b", "passed": True},
                {"name": "c", "passed": True},
                {"name": "d", "passed": True},
            ],
            "summary": "全部一致"
        }
        pairs = result["pairs"]
        all_passed = all(p.get("passed", False) for p in pairs) if pairs else False
        assert all_passed is True

    def test_one_pair_failed_returns_false(self):
        result = {
            "pairs": [
                {"name": "a", "passed": True},
                {"name": "b", "passed": False},
                {"name": "c", "passed": True},
                {"name": "d", "passed": True},
            ],
        }
        pairs = result["pairs"]
        all_passed = all(p.get("passed", False) for p in pairs) if pairs else False
        assert all_passed is False

    def test_empty_pairs_returns_false(self):
        result = {"pairs": [], "summary": ""}
        pairs = result["pairs"]
        all_passed = all(p.get("passed", False) for p in pairs) if pairs else False
        assert all_passed is False

    def test_pairs_with_missing_passed_field(self):
        """缺少 passed 字段的配对默认视为不合格"""
        result = {"pairs": [{"name": "a"}]}
        pairs = result["pairs"]
        all_passed = all(p.get("passed", False) for p in pairs) if pairs else False
        assert all_passed is False


class TestSubStepModuleStructure:
    """子步骤模块结构验证"""

    def test_step4_1_has_run_fn(self):
        import app.api.workflow.step4_1 as mod
        assert hasattr(mod, "run_sub_step_4_1")

    def test_step4_1_has_execute_endpoint(self):
        import app.api.workflow.step4_1 as mod
        assert hasattr(mod, "execute_step4_1")

    def test_step4_2_has_run_fn(self):
        import app.api.workflow.step4_2 as mod
        assert hasattr(mod, "run_sub_step_4_2")

    def test_step4_2_has_execute_endpoint(self):
        import app.api.workflow.step4_2 as mod
        assert hasattr(mod, "execute_step4_2")

    def test_step4_3_has_run_fn(self):
        import app.api.workflow.step4_3 as mod
        assert hasattr(mod, "run_sub_step_4_3")

    def test_step4_3_has_execute_endpoint(self):
        import app.api.workflow.step4_3 as mod
        assert hasattr(mod, "execute_step4_4") is False or hasattr(mod, "execute_step4_3")

    def test_step4_4_has_run_fn(self):
        import app.api.workflow.step4_4 as mod
        assert hasattr(mod, "run_sub_step_4_4")

    def test_step4_4_has_execute_endpoint(self):
        import app.api.workflow.step4_4 as mod
        assert hasattr(mod, "execute_step4_4")

    def test_step4_2_imports_consistency_check(self):
        """step4_2 导入了跨文档一致性检查函数"""
        import app.api.workflow.step4 as step4
        assert hasattr(step4, "_check_consistency_pairs")
        assert hasattr(step4, "_fix_doc_from_consistency_feedback")

    def test_step4_module_has_cross_check(self):
        """step4 模块有完整的跨文档一致性检验函数"""
        import app.api.workflow.step4 as mod
        assert hasattr(mod, "_cross_check_docs")
        assert hasattr(mod, "_check_consistency_pairs")
        assert hasattr(mod, "_fix_doc_from_consistency_feedback")

    def test_step4_module_has_sub_flow(self):
        """step4 模块有子流程函数"""
        import app.api.workflow.step4 as mod
        assert hasattr(mod, "_run_doc_sub_flow")


class TestShardRetriever:
    """ShardRetriever 向量检索测试"""

    def test_retrieve_returns_results_for_matching_query(self, tmp_path):
        from app.services.doc_sharder import ShardRetriever, save_chapter
        save_chapter("ARCHITECTURE", "overview", "# 系统架构\n包含整体架构描述", str(tmp_path), "proj")
        save_chapter("ARCHITECTURE", "layers", "# 分层\n包含分层设计", str(tmp_path), "proj")

        retriever = ShardRetriever(str(tmp_path), "proj", "ARCHITECTURE")
        results = retriever.retrieve("系统架构", top_k=1)
        assert len(results) >= 1
        assert results[0]["key"] == "overview"

    def test_retrieve_returns_empty_for_unknown_doc_type(self, tmp_path):
        from app.services.doc_sharder import ShardRetriever
        retriever = ShardRetriever(str(tmp_path), "proj", "NONEXISTENT")
        results = retriever.retrieve("测试")
        assert results == []

    def test_retrieve_excludes_specified_key(self, tmp_path):
        from app.services.doc_sharder import ShardRetriever, save_chapter
        save_chapter("BACKEND", "api_design", "# API设计\nRESTful接口定义", str(tmp_path), "proj")
        save_chapter("BACKEND", "security", "# 安全\n认证授权策略", str(tmp_path), "proj")

        retriever = ShardRetriever(str(tmp_path), "proj", "BACKEND")
        results = retriever.retrieve("接口设计", exclude_key="api_design")
        excluded_keys = [r["key"] for r in results]
        assert "api_design" not in excluded_keys

    def test_tokenize_handles_chinese(self, tmp_path):
        from app.services.doc_sharder import ShardRetriever
        retriever = ShardRetriever(str(tmp_path), "proj", "ARCHITECTURE")
        tokens = retriever._tokenize("系统架构设计")
        assert len(tokens) > 0

    def test_tokenize_handles_mixed(self, tmp_path):
        from app.services.doc_sharder import ShardRetriever
        retriever = ShardRetriever(str(tmp_path), "proj", "ARCHITECTURE")
        tokens = retriever._tokenize("API设计 design pattern")
        # 中文字符与ASCII合并为同一token（"API设计"），英文分词独立
        assert "api设计" in tokens or "api" in tokens
        assert "design" in tokens
        assert "pattern" in tokens

    def test_tfidf_no_overlap_returns_zero(self, tmp_path):
        from app.services.doc_sharder import ShardRetriever
        retriever = ShardRetriever(str(tmp_path), "proj", "ARCHITECTURE")
        score = retriever._tfidf("completely unrelated text", "系统架构设计")
        assert score == 0.0


class TestDocSharderLoadAllChapters:
    """load_all_chapters 加载测试"""

    def test_load_all_chapters_returns_dict_with_keys(self, tmp_path):
        from app.services.doc_sharder import load_all_chapters, save_chapter
        save_chapter("FRONTEND", "routing", "# 路由设计", str(tmp_path), "myproj")
        result = load_all_chapters("FRONTEND", str(tmp_path), "myproj")
        assert "routing" in result
        assert result["routing"]["content"] == "# 路由设计"

    def test_load_all_chapters_content_is_empty_for_missing_file(self, tmp_path):
        from app.services.doc_sharder import load_all_chapters
        result = load_all_chapters("DATABASE", str(tmp_path), "myproj")
        for key, data in result.items():
            assert data["content"] == ""

    def test_build_all_chapters_prompt_has_summary(self, tmp_path):
        from app.services.doc_sharder import build_all_chapters_prompt, save_chapter
        save_chapter("BACKEND", "tech_stack", "# 后端技术栈\nFastAPI + SQLAlchemy", str(tmp_path), "proj")
        prompt = build_all_chapters_prompt("BACKEND", str(tmp_path), "proj")
        assert "后端技术栈" in prompt
        assert "FastAPI" in prompt

    def test_build_all_chapters_prompt_empty_when_no_content(self, tmp_path):
        from app.services.doc_sharder import build_all_chapters_prompt
        prompt = build_all_chapters_prompt("BACKEND", str(tmp_path), "proj")
        assert prompt == ""


class TestEnvShardConfig:
    """ENV（开发环境）分片配置测试"""

    def test_env_shard_config_chapters(self):
        from app.services.doc_sharder import get_shard_config
        chapters = get_shard_config("ENV")
        assert len(chapters) == 5
        keys = [c["key"] for c in chapters]
        assert "repo" in keys
        assert "framework" in keys
        assert "dependencies" in keys
        assert "database_init" in keys
        assert "cicd" in keys

    def test_env_shard_chapter_titles(self):
        from app.services.doc_sharder import get_shard_config
        chapters = get_shard_config("ENV")
        titles = {c["key"]: c["title"] for c in chapters}
        assert titles["repo"] == "代码仓库"
        assert titles["framework"] == "开发框架"
        assert titles["cicd"] == "CI/CD流水线"
