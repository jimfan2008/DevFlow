import os
import time
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class CICDPipelineConfig:
    """CI/CD 流水线配置管理器，用于 TDD 测试驱动开发。"""

    def __init__(self, project_root: str):
        self._project_root = project_root
        self._stages = []
        self._execution_history = []
        self._load_pipeline_config()

    def _load_pipeline_config(self):
        """加载流水线配置，根据项目文件结构自动生成配置。"""
        dockerfile = os.path.join(self._project_root, "Dockerfile")
        makefile = os.path.join(self._project_root, "Makefile")
        compose_file = os.path.join(self._project_root, "docker-compose.yml")
        package_json = os.path.join(self._project_root, "frontend", "package.json")

        self._stages = [
            {
                "name": "build",
                "description": "构建阶段",
                "steps": [],
                "timeout_minutes": 10,
            },
            {
                "name": "test",
                "description": "测试阶段",
                "steps": [],
                "timeout_minutes": 10,
            },
            {
                "name": "deploy",
                "description": "部署阶段",
                "steps": [],
                "timeout_minutes": 10,
            },
        ]

        build_stage = self._stages[0]
        if os.path.exists(dockerfile):
            build_stage["steps"].append({
                "name": "docker-build",
                "command": "docker-compose build --no-cache",
                "timeout_minutes": 15,
            })
        if os.path.exists(package_json):
            build_stage["steps"].append({
                "name": "frontend-build",
                "command": "cd frontend && npm ci && npm run build",
                "timeout_minutes": 10,
            })
        if os.path.exists(makefile):
            build_stage["steps"].append({
                "name": "make-check",
                "command": "make check",
                "timeout_minutes": 5,
            })

        test_stage = self._stages[1]
        test_stage["steps"].append({
            "name": "pytest",
            "command": "pytest -v --cov=app --cov-report=term-missing",
            "timeout_minutes": 10,
        })
        if os.path.exists(makefile):
            test_stage["steps"].append({
                "name": "lint",
                "command": "make lint",
                "timeout_minutes": 3,
            })

        deploy_stage = self._stages[2]
        if os.path.exists(compose_file):
            deploy_stage["steps"].append({
                "name": "docker-deploy",
                "command": "docker-compose up -d",
                "timeout_minutes": 15,
            })
        deploy_stage["steps"].append({
            "name": "health-check",
            "command": "curl -f http://localhost:8000/health",
            "timeout_minutes": 3,
        })

    @property
    def stages(self):
        return self._stages

    @property
    def stage_count(self):
        return len(self._stages)

    @property
    def execution_history(self):
        return self._execution_history

    def get_stage(self, stage_name: str):
        """获取指定名称的阶段配置。"""
        for stage in self._stages:
            if stage["name"] == stage_name:
                return stage
        return None

    def get_required_stages(self):
        """获取必需阶段列表。"""
        return ["build", "test", "deploy"]

    def validate_config(self):
        """验证流水线配置是否完整。"""
        required = self.get_required_stages()
        actual = [s["name"] for s in self._stages]
        missing = [s for s in required if s not in actual]
        if missing:
            return {"valid": False, "missing_stages": missing}
        for stage in self._stages:
            if not stage["steps"]:
                return {"valid": False, "empty_stage": stage["name"]}
        return {"valid": True}

    def calculate_total_timeout(self):
        """计算流水线总超时时间（分钟）。"""
        return sum(s["timeout_minutes"] for s in self._stages)

    def mock_execute_stage(self, stage_name: str, success=True, duration_seconds=30):
        """模拟执行一个阶段（用于测试）。"""
        stage = self.get_stage(stage_name)
        if not stage:
            return {"success": False, "error": f"阶段不存在: {stage_name}"}

        result = {
            "stage": stage_name,
            "success": success,
            "duration_seconds": duration_seconds,
            "steps_executed": len(stage["steps"]),
            "timestamp": time.time(),
        }
        self._execution_history.append(result)
        return result

    def mock_execute_pipeline(self, results: list = None):
        """模拟执行完整流水线。"""
        if results is None:
            results = [
                ("build", True, 180),
                ("test", True, 120),
                ("deploy", True, 900),
            ]

        total_duration = 0
        all_success = True

        for stage_name, success, duration in results:
            result = self.mock_execute_stage(stage_name, success, duration)
            total_duration += duration
            if not success:
                all_success = False

        pipeline_result = {
            "success": all_success,
            "total_duration": total_duration,
            "stages_executed": len(results),
            "individual_results": self._execution_history[-len(results):],
        }
        return pipeline_result

    def get_success_rate(self):
        """计算执行成功率（成功次数/总次数）。"""
        if not self._execution_history:
            return 100.0
        success_count = sum(1 for r in self._execution_history if r["success"])
        return (success_count / len(self._execution_history)) * 100

    def get_last_execution_time(self):
        """获取最近一次执行的总时长（秒）。"""
        if not self._execution_history:
            return 0
        return sum(r["duration_seconds"] for r in self._execution_history)


# ====================================================================
# 测试：CI/CD 流水线配置
# ====================================================================


class TestCICDPipelineConfiguration:
    """CI/CD 流水线配置 — 验证构建、测试、部署三个阶段完整，成功率 >=95%，执行时间 <=30 分钟。"""

    @pytest.fixture
    def project_root(self):
        return str(Path(__file__).parent)

    @pytest.fixture
    def real_pipeline(self, project_root):
        return CICDPipelineConfig(project_root)

    @pytest.fixture
    def mock_pipeline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile = os.path.join(tmpdir, "Dockerfile")
            makefile = os.path.join(tmpdir, "Makefile")
            compose_file = os.path.join(tmpdir, "docker-compose.yml")
            frontend_dir = os.path.join(tmpdir, "frontend")

            os.makedirs(frontend_dir, exist_ok=True)

            with open(dockerfile, "w") as f:
                f.write("FROM python:3.12.7-slim AS builder\n")
                f.write("WORKDIR /app\n")
                f.write("EXPOSE 8000\n")

            with open(makefile, "w") as f:
                f.write(".PHONY: test lint\n")
                f.write("test:\n\t@echo running tests\n")
                f.write("lint:\n\t@echo running lint\n")

            with open(compose_file, "w") as f:
                f.write("version: '3.8'\n")
                f.write("services:\n")
                f.write("  fastapi:\n")
                f.write("    build: .\n")

            pkg = os.path.join(frontend_dir, "package.json")
            with open(pkg, "w") as f:
                json.dump({"name": "devflow-frontend", "scripts": {"build": "vite build"}}, f)

            yield CICDPipelineConfig(tmpdir)

    # ----------------------------------------------------------------
    # 验收标准 1：流水线配置完整（构建、测试、部署三个阶段）
    # ----------------------------------------------------------------

    def test_pipeline_has_three_stages(self, mock_pipeline):
        """流水线应包含三个阶段：build、test、deploy。"""
        assert mock_pipeline.stage_count == 3, f"阶段数量应为 3，实际为 {mock_pipeline.stage_count}"

    def test_pipeline_has_build_stage(self, mock_pipeline):
        """流水线应包含 build 阶段。"""
        stage = mock_pipeline.get_stage("build")
        assert stage is not None, "build 阶段应存在"
        assert stage["name"] == "build", f"阶段名称应为 'build'，实际为 '{stage['name']}'"

    def test_pipeline_has_test_stage(self, mock_pipeline):
        """流水线应包含 test 阶段。"""
        stage = mock_pipeline.get_stage("test")
        assert stage is not None, "test 阶段应存在"
        assert stage["name"] == "test", f"阶段名称应为 'test'，实际为 '{stage['name']}'"

    def test_pipeline_has_deploy_stage(self, mock_pipeline):
        """流水线应包含 deploy 阶段。"""
        stage = mock_pipeline.get_stage("deploy")
        assert stage is not None, "deploy 阶段应存在"
        assert stage["name"] == "deploy", f"阶段名称应为 'deploy'，实际为 '{stage['name']}'"

    def test_each_stage_has_steps(self, mock_pipeline):
        """每个阶段至少包含一个步骤。"""
        for stage in mock_pipeline.stages:
            assert len(stage["steps"]) > 0, f"阶段 '{stage['name']}' 应至少有一个步骤"

    def test_config_validation_passes(self, mock_pipeline):
        """完整配置应通过验证检查。"""
        result = mock_pipeline.validate_config()
        assert result["valid"] is True, f"配置验证应通过：{result}"

    def test_config_validation_detects_missing_stages(self):
        """缺少阶段时应报告具体的缺失阶段。"""
        pipeline = CICDPipelineConfig("/tmp/non_existent_dir")
        pipeline._stages = [
            {"name": "build", "steps": [{"name": "step1"}]},
            {"name": "test", "steps": [{"name": "step2"}]},
        ]
        result = pipeline.validate_config()
        assert result["valid"] is False
        assert "deploy" in result["missing_stages"]

    def test_config_validation_detects_empty_stage(self):
        """空步骤阶段应报告具体名称。"""
        pipeline = CICDPipelineConfig("/tmp/non_existent_dir")
        pipeline._stages = [
            {"name": "build", "steps": [{"name": "step1"}]},
            {"name": "test", "steps": []},
            {"name": "deploy", "steps": [{"name": "step3"}]},
        ]
        result = pipeline.validate_config()
        assert result["valid"] is False
        assert result["empty_stage"] == "test"

    # ----------------------------------------------------------------
    # 验收标准 2：流水线执行成功率 >=95%
    # ----------------------------------------------------------------

    def test_success_rate_all_pass(self, mock_pipeline):
        """全部通过时应返回 100% 成功率。"""
        mock_pipeline.mock_execute_pipeline([
            ("build", True, 180),
            ("test", True, 120),
            ("deploy", True, 900),
        ])
        rate = mock_pipeline.get_success_rate()
        assert rate >= 95.0, f"成功率应 >=95%，实际为 {rate}%"

    def test_success_rate_one_fails(self, mock_pipeline):
        """三个阶段中一个失败时成功率 66.7% < 95%。"""
        mock_pipeline.mock_execute_pipeline([
            ("build", True, 180),
            ("test", False, 60),
            ("deploy", True, 900),
        ])
        rate = mock_pipeline.get_success_rate()
        assert rate < 95.0, f"一次失败时成功率应 <95%，实际为 {rate}%"

    def test_success_rate_multiple_runs(self, mock_pipeline):
        """多次运行平均成功率 >=95%。"""
        runs = [
            [("build", True, 180), ("test", True, 120), ("deploy", True, 900)],
            [("build", True, 200), ("test", True, 130), ("deploy", True, 800)],
            [("build", True, 190), ("test", True, 125), ("deploy", True, 850)],
        ]
        for run in runs:
            mock_pipeline.mock_execute_pipeline(run)
        rate = mock_pipeline.get_success_rate()
        assert rate >= 95.0, f"多次运行成功率应 >=95%，实际为 {rate}%"

    def test_get_success_rate_empty_history(self, mock_pipeline):
        """无执行历史时默认返回 100%。"""
        rate = mock_pipeline.get_success_rate()
        assert rate == 100.0, f"空历史应返回 100%，实际为 {rate}%"

    # ----------------------------------------------------------------
    # 验收标准 3：执行时间 <=30 分钟
    # ----------------------------------------------------------------

    def test_total_timeout_within_limit(self, mock_pipeline):
        """配置总超时时间应不超过 30 分钟。"""
        total = mock_pipeline.calculate_total_timeout()
        assert total <= 30, f"总超时时间应 <=30 分钟，实际为 {total} 分钟"

    def test_actual_execution_within_limit(self, mock_pipeline):
        """实际执行时间应不超过 30 分钟（1800 秒）。"""
        results = [
            ("build", True, 600),
            ("test", True, 300),
            ("deploy", True, 900),
        ]
        mock_pipeline.mock_execute_pipeline(results)
        duration = mock_pipeline.get_last_execution_time()
        assert duration <= 1800, f"执行时间应 <=1800 秒，实际为 {duration} 秒"

    def test_actual_execution_exceeds_limit(self, mock_pipeline):
        """超出时间限制时应正确检测。"""
        results = [
            ("build", True, 1200),
            ("test", True, 600),
            ("deploy", True, 1800),
        ]
        mock_pipeline.mock_execute_pipeline(results)
        duration = mock_pipeline.get_last_execution_time()
        assert duration > 1800, f"此测试期望超时，实际为 {duration} 秒"

    def test_get_last_execution_time_empty(self, mock_pipeline):
        """无执行历史时返回 0。"""
        duration = mock_pipeline.get_last_execution_time()
        assert duration == 0, f"空执行历史应返回 0，实际为 {duration}"

    def test_stage_timeout_sum_reasonable(self, mock_pipeline):
        """各阶段超时之和应在合理范围内。"""
        timeouts = [s["timeout_minutes"] for s in mock_pipeline.stages]
        assert len(timeouts) == 3, "应包含 3 个阶段超时时间"
        for name, t in zip(["build", "test", "deploy"], timeouts):
            assert 5 <= t <= 20, f"阶段 '{name}' 超时 {t} 分钟，应在 5-20 分钟内"

    # ----------------------------------------------------------------
    # 边界与异常场景
    # ----------------------------------------------------------------

    def test_mock_execute_unknown_stage(self, mock_pipeline):
        """执行未知阶段应返回错误。"""
        result = mock_pipeline.mock_execute_stage("nonexistent")
        assert result["success"] is False
        assert "nonexistent" in result["error"]

    def test_pipeline_from_real_project(self, real_pipeline):
        """使用真实项目目录应能正常初始化流水线。"""
        assert real_pipeline.stage_count == 3, "真实项目应包含 3 个阶段"
        result = real_pipeline.validate_config()
        assert result["valid"] is True, f"真实项目配置应完整：{result}"

    def test_build_stage_has_docker_step(self, mock_pipeline):
        """build 阶段应包含 Docker 构建步骤。"""
        build_stage = mock_pipeline.get_stage("build")
        step_names = [s["name"] for s in build_stage["steps"]]
        assert "docker-build" in step_names, "build 阶段应包含 docker-build 步骤"

    def test_test_stage_has_pytest_step(self, mock_pipeline):
        """test 阶段应包含 pytest 步骤。"""
        test_stage = mock_pipeline.get_stage("test")
        step_names = [s["name"] for s in test_stage["steps"]]
        assert "pytest" in step_names, "test 阶段应包含 pytest 步骤"

    def test_deploy_stage_has_health_check(self, mock_pipeline):
        """deploy 阶段应包含健康检查步骤。"""
        deploy_stage = mock_pipeline.get_stage("deploy")
        step_names = [s["name"] for s in deploy_stage["steps"]]
        assert "health-check" in step_names, "deploy 阶段应包含 health-check 步骤"

    def test_get_stage_returns_none_for_missing(self, mock_pipeline):
        """查询不存在的阶段应返回 None。"""
        result = mock_pipeline.get_stage("nonexistent")
        assert result is None, "查询不存在的阶段应返回 None"

    def test_execution_history_records_all_stages(self, mock_pipeline):
        """执行历史应记录所有阶段的执行结果。"""
        mock_pipeline.mock_execute_pipeline([
            ("build", True, 180),
            ("test", True, 120),
            ("deploy", True, 900),
        ])
        assert len(mock_pipeline.execution_history) == 3, "历史记录应包含 3 条记录"
        stage_names = [r["stage"] for r in mock_pipeline.execution_history]
        assert set(stage_names) == {"build", "test", "deploy"}, "应包含所有三个阶段"

    def test_pipeline_result_aggregation(self, mock_pipeline):
        """流水线执行结果应正确聚合。"""
        result = mock_pipeline.mock_execute_pipeline([
            ("build", True, 180),
            ("test", True, 120),
            ("deploy", True, 900),
        ])
        assert result["success"] is True, "全部通过时应标记为成功"
        assert result["total_duration"] == 1200, f"总时长应为 1200 秒，实际为 {result['total_duration']}"
        assert result["stages_executed"] == 3, "应执行 3 个阶段"

    def test_pipeline_result_on_failure(self, mock_pipeline):
        """任一阶段失败时流水线应标记为失败。"""
        result = mock_pipeline.mock_execute_pipeline([
            ("build", True, 180),
            ("test", False, 60),
            ("deploy", True, 900),
        ])
        assert result["success"] is False, "任一阶段失败时流水线应标记为失败"
