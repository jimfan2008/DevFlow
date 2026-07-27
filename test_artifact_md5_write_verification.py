import hashlib
import os
import time
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
from datetime import datetime, timezone


class ArtifactVerificationError(Exception):
    """产出物验证异常"""
    pass


class ArtifactWriteVerifier:
    """Celery Worker 产出物写入验证器

    对命名 Agent 的产出物进行三步验证：
    1. 存在性验证 — 文件是否存在
    2. 大小验证 — 文件大小是否符合预期
    3. MD5 校验 — 文件内容 MD5 是否匹配

    失败时自动重试，最多 3 次。
    """

    MAX_RETRIES = 3

    def __init__(self, base_dir: str, max_retries: int = None):
        self.base_dir = os.path.abspath(base_dir)
        self.max_retries = max_retries or self.MAX_RETRIES

    def compute_md5(self, file_path: str) -> str:
        """计算文件的 MD5 校验和"""
        sha = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def _verify_exists(self, file_path: str) -> dict:
        """步骤 1：验证文件是否存在"""
        exists = os.path.isfile(file_path)
        return {
            "step": "existence",
            "passed": exists,
            "detail": f"文件 {'存在' if exists else '不存在'}: {file_path}",
        }

    def _verify_size(self, file_path: str, expected_size: int) -> dict:
        """步骤 2：验证文件大小是否符合预期"""
        actual_size = os.path.getsize(file_path)
        passed = actual_size == expected_size
        return {
            "step": "size",
            "passed": passed,
            "expected": expected_size,
            "actual": actual_size,
            "detail": f"文件大小：期望 {expected_size}，实际 {actual_size}",
        }

    def _verify_md5(self, file_path: str, expected_md5: str) -> dict:
        """步骤 3：验证文件 MD5 校验和"""
        actual_md5 = self.compute_md5(file_path)
        passed = actual_md5 == expected_md5
        return {
            "step": "md5",
            "passed": passed,
            "expected": expected_md5,
            "actual": actual_md5,
            "detail": f"MD5：期望 {expected_md5}，实际 {actual_md5}",
        }

    def verify_artifact(self, agent_name: str, artifact_name: str,
                        expected_size: int, expected_md5: str) -> dict:
        """执行产出物三步验证

        返回包含验证结果的字典，格式：
        {
            "agent_name": str,
            "artifact_name": str,
            "passed": bool,
            "retries": int,
            "attempts": list[dict],
            "errors": list[str],
        }
        """
        file_path = os.path.join(
            self.base_dir, agent_name, artifact_name
        )
        result = {
            "agent_name": agent_name,
            "artifact_name": artifact_name,
            "passed": False,
            "retries": 0,
            "attempts": [],
            "errors": [],
        }

        for attempt in range(1, self.max_retries + 1):
            result["retries"] = attempt
            attempt_record = {
                "attempt": attempt,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": [],
                "passed": False,
            }

            # 步骤 1：存在性验证
            exists_check = self._verify_exists(file_path)
            attempt_record["checks"].append(exists_check)
            if not exists_check["passed"]:
                result["errors"].append(
                    f"第{attempt}次尝试 - 存在性验证失败: {exists_check['detail']}"
                )
                result["attempts"].append(attempt_record)
                if attempt < self.max_retries:
                    time.sleep(0.01)  # 短等待后重试
                continue

            # 步骤 2：大小验证
            size_check = self._verify_size(file_path, expected_size)
            attempt_record["checks"].append(size_check)
            if not size_check["passed"]:
                result["errors"].append(
                    f"第{attempt}次尝试 - 大小验证失败: {size_check['detail']}"
                )
                result["attempts"].append(attempt_record)
                if attempt < self.max_retries:
                    time.sleep(0.01)
                continue

            # 步骤 3：MD5 校验
            md5_check = self._verify_md5(file_path, expected_md5)
            attempt_record["checks"].append(md5_check)
            if not md5_check["passed"]:
                result["errors"].append(
                    f"第{attempt}次尝试 - MD5 校验失败: {md5_check['detail']}"
                )
                result["attempts"].append(attempt_record)
                if attempt < self.max_retries:
                    time.sleep(0.01)
                continue

            # 全部通过
            attempt_record["passed"] = True
            result["passed"] = True
            result["attempts"].append(attempt_record)
            return result

        # 所有尝试均失败（已在循环内追加 attempt_record）
        return result


class CeleryArtifactWorker:
    """Celery Worker 模拟 — 负责验证命名 Agent 的产出物写入"""

    def __init__(self, base_dir: str, max_retries: int = 3):
        self.verifier = ArtifactWriteVerifier(base_dir, max_retries)
        self.task_log = []

    def process_artifact(self, agent_name: str, artifact_name: str,
                         expected_size: int, expected_md5: str) -> dict:
        """处理单个产出物的验证任务（模拟 Celery task）"""
        self.task_log.append({
            "action": "process_artifact",
            "agent_name": agent_name,
            "artifact_name": artifact_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        result = self.verifier.verify_artifact(
            agent_name, artifact_name, expected_size, expected_md5
        )
        self.task_log.append({
            "action": "result",
            "agent_name": agent_name,
            "artifact_name": artifact_name,
            "passed": result["passed"],
            "retries": result["retries"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return result

    def process_all_artifacts(self, artifacts: list) -> dict:
        """批量处理多个产出物的验证

        artifacts: [{"agent_name": str, "artifact_name": str,
                     "expected_size": int, "expected_md5": str}, ...]
        """
        results = []
        all_passed = True
        for item in artifacts:
            result = self.process_artifact(
                item["agent_name"],
                item["artifact_name"],
                item["expected_size"],
                item["expected_md5"],
            )
            results.append(result)
            if not result["passed"]:
                all_passed = False

        return {
            "total": len(artifacts),
            "passed": all_passed,
            "results": results,
        }


# ============================================================
# 测试用例：产出物 MD5 写入验证
# ============================================================

@pytest.fixture
def tmp_artifact_dir(tmp_path):
    """创建临时的产出物存储目录"""
    return str(tmp_path / "artifacts")


@pytest.fixture
def sample_content():
    """样本产出物内容"""
    return "DevFlow 命名 Agent 产出物测试数据 - 验证三步校验机制"


@pytest.fixture
def sample_artifact_path(tmp_artifact_dir, sample_content):
    """创建样本产出物文件并返回路径"""
    agent_dir = os.path.join(tmp_artifact_dir, "houfa")
    os.makedirs(agent_dir, exist_ok=True)
    file_path = os.path.join(agent_dir, "code_output.py")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(sample_content)
    return file_path


@pytest.fixture
def sample_artifact_metadata(sample_content):
    """样本产出物的元数据（大小 + MD5）"""
    size = len(sample_content.encode("utf-8"))
    md5 = hashlib.md5(sample_content.encode("utf-8")).hexdigest()
    return {"size": size, "md5": md5}


@pytest.fixture
def worker(tmp_artifact_dir):
    """产出物验证 Worker"""
    return CeleryArtifactWorker(tmp_artifact_dir)


@pytest.fixture
def verifier(tmp_artifact_dir):
    """产出物验证器"""
    return ArtifactWriteVerifier(tmp_artifact_dir)


class TestArtifactExistenceCheck:
    """存在性验证测试"""

    def test_verify_artifact_exists(self, sample_artifact_path):
        """验证文件存在时，存在性检查通过"""
        verifier = ArtifactWriteVerifier(os.path.dirname(sample_artifact_path))
        file_name = os.path.basename(sample_artifact_path)
        result = verifier.verify_artifact(
            "", file_name, 999, "dummy_md5"
        )
        assert result["attempts"][0]["checks"][0]["step"] == "existence"
        assert result["attempts"][0]["checks"][0]["passed"] is True

    def test_verify_artifact_not_exists(self, tmp_artifact_dir):
        """验证文件不存在时，存在性检查失败"""
        verifier = ArtifactWriteVerifier(tmp_artifact_dir)
        result = verifier.verify_artifact(
            "houfa", "nonexistent_file.py", 100, "abc123"
        )
        assert result["passed"] is False
        assert result["attempts"][0]["checks"][0]["step"] == "existence"
        assert result["attempts"][0]["checks"][0]["passed"] is False

    def test_not_exists_triggers_retry(self, tmp_artifact_dir):
        """文件不存在时应触发重试，最多 3 次"""
        verifier = ArtifactWriteVerifier(tmp_artifact_dir, max_retries=3)
        result = verifier.verify_artifact(
            "houfa", "missing.md", 50, "abc123"
        )
        assert result["retries"] == 3
        assert result["passed"] is False
        assert len(result["errors"]) == 3  # 每次尝试都产生一条错误


class TestArtifactSizeCheck:
    """大小验证测试"""

    def test_verify_size_matches(self, sample_artifact_path,
                                  sample_artifact_metadata):
        """文件大小匹配预期时通过"""
        dirpath = os.path.dirname(sample_artifact_path)
        filename = os.path.basename(sample_artifact_path)
        verifier = ArtifactWriteVerifier(dirpath)
        result = verifier.verify_artifact(
            "", filename,
            sample_artifact_metadata["size"],
            sample_artifact_metadata["md5"],
        )
        assert result["passed"] is True
        size_check = result["attempts"][0]["checks"][1]
        assert size_check["step"] == "size"
        assert size_check["passed"] is True

    def test_verify_size_mismatch(self, tmp_artifact_dir, sample_content):
        """文件大小不匹配时失败"""
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "report.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(sample_content)

        actual_size = len(sample_content.encode("utf-8"))
        wrong_size = actual_size + 100  # 故意给错误的大小
        verifier = ArtifactWriteVerifier(tmp_artifact_dir)
        result = verifier.verify_artifact(
            "houfa", "report.md",
            wrong_size,
            hashlib.md5(sample_content.encode("utf-8")).hexdigest(),
        )
        assert result["passed"] is False
        size_check = result["attempts"][0]["checks"][1]
        assert size_check["step"] == "size"
        assert size_check["passed"] is False
        assert size_check["expected"] == wrong_size
        assert size_check["actual"] == actual_size

    def test_size_mismatch_triggers_retry(self, tmp_artifact_dir,
                                           sample_content):
        """大小不匹配时应重试 3 次"""
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "report.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(sample_content)

        wrong_size = 9999
        verifier = ArtifactWriteVerifier(tmp_artifact_dir, max_retries=3)
        result = verifier.verify_artifact(
            "houfa", "report.md", wrong_size, "any_md5"
        )
        assert result["retries"] == 3
        assert result["passed"] is False


class TestArtifactMD5Check:
    """MD5 校验测试"""

    def test_compute_md5_correct(self, sample_artifact_path,
                                  sample_artifact_metadata):
        """MD5 计算结果正确"""
        verifier = ArtifactWriteVerifier("")
        md5 = verifier.compute_md5(sample_artifact_path)
        assert md5 == sample_artifact_metadata["md5"]

    def test_verify_md5_matches(self, sample_artifact_path,
                                 sample_artifact_metadata):
        """MD5 匹配时通过"""
        dirpath = os.path.dirname(sample_artifact_path)
        filename = os.path.basename(sample_artifact_path)
        verifier = ArtifactWriteVerifier(dirpath)
        result = verifier.verify_artifact(
            "", filename,
            sample_artifact_metadata["size"],
            sample_artifact_metadata["md5"],
        )
        assert result["passed"] is True
        md5_check = result["attempts"][0]["checks"][2]
        assert md5_check["step"] == "md5"
        assert md5_check["passed"] is True

    def test_verify_md5_mismatch(self, tmp_artifact_dir, sample_content):
        """MD5 不匹配时失败"""
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "report.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(sample_content)

        actual_size = len(sample_content.encode("utf-8"))
        wrong_md5 = "00000000000000000000000000000000"
        verifier = ArtifactWriteVerifier(tmp_artifact_dir)
        result = verifier.verify_artifact(
            "houfa", "report.md", actual_size, wrong_md5
        )
        assert result["passed"] is False
        md5_check = result["attempts"][0]["checks"][2]
        assert md5_check["step"] == "md5"
        assert md5_check["passed"] is False
        assert md5_check["expected"] == wrong_md5

    def test_md5_mismatch_triggers_retry(self, tmp_artifact_dir,
                                          sample_content):
        """MD5 不匹配时应重试 3 次"""
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "report.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(sample_content)

        actual_size = len(sample_content.encode("utf-8"))
        wrong_md5 = "deadbeef000000000000000000000000"
        verifier = ArtifactWriteVerifier(tmp_artifact_dir, max_retries=3)
        result = verifier.verify_artifact(
            "houfa", "report.md", actual_size, wrong_md5
        )
        assert result["retries"] == 3
        assert result["passed"] is False


class TestThreeStepVerification:
    """三步验证集成测试"""

    def test_all_three_steps_pass(self, sample_artifact_path,
                                   sample_artifact_metadata):
        """三步验证全部通过"""
        dirpath = os.path.dirname(sample_artifact_path)
        filename = os.path.basename(sample_artifact_path)
        verifier = ArtifactWriteVerifier(dirpath)
        result = verifier.verify_artifact(
            "", filename,
            sample_artifact_metadata["size"],
            sample_artifact_metadata["md5"],
        )
        assert result["passed"] is True
        checks = result["attempts"][0]["checks"]
        assert len(checks) == 3
        assert checks[0]["step"] == "existence"
        assert checks[1]["step"] == "size"
        assert checks[2]["step"] == "md5"
        assert all(c["passed"] for c in checks)
        assert result["retries"] == 1  # 首次即通过

    def test_existence_fails_skips_rest(self, tmp_artifact_dir):
        """存在性验证失败时，不会执行大小和 MD5 验证"""
        verifier = ArtifactWriteVerifier(tmp_artifact_dir, max_retries=1)
        result = verifier.verify_artifact(
            "houfa", "missing.md", 100, "abc123"
        )
        assert result["passed"] is False
        checks = result["attempts"][0]["checks"]
        assert len(checks) == 1  # 仅执行了存在性检查
        assert checks[0]["step"] == "existence"

    def test_size_fails_skips_md5(self, tmp_artifact_dir, sample_content):
        """大小验证失败时，不会执行 MD5 验证"""
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "report.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(sample_content)

        wrong_size = 9999
        verifier = ArtifactWriteVerifier(tmp_artifact_dir, max_retries=1)
        result = verifier.verify_artifact(
            "houfa", "report.md", wrong_size, "any_md5"
        )
        assert result["passed"] is False
        checks = result["attempts"][0]["checks"]
        assert len(checks) == 2  # 仅执行了存在性和大小检查
        assert checks[0]["step"] == "existence"
        assert checks[1]["step"] == "size"


class TestRetryMechanism:
    """重试机制测试"""

    def test_max_retries_is_three(self, tmp_artifact_dir):
        """最大重试次数为 3"""
        verifier = ArtifactWriteVerifier(tmp_artifact_dir, max_retries=3)
        result = verifier.verify_artifact(
            "houfa", "missing.md", 100, "abc123"
        )
        assert result["retries"] == 3

    def test_custom_max_retries(self, tmp_artifact_dir):
        """可自定义最大重试次数"""
        verifier = ArtifactWriteVerifier(tmp_artifact_dir, max_retries=5)
        result = verifier.verify_artifact(
            "houfa", "missing.md", 100, "abc123"
        )
        assert result["retries"] == 5

    def test_retry_on_file_delayed_write(self, tmp_artifact_dir,
                                          sample_content):
        """模拟文件延迟写入场景：首次失败，第 2 次通过"""
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "delayed_report.md")

        call_count = {"count": 0}
        actual_size = len(sample_content.encode("utf-8"))
        actual_md5 = hashlib.md5(sample_content.encode("utf-8")).hexdigest()

        original_isfile = os.path.isfile

        def mock_isfile(path):
            call_count["count"] += 1
            if call_count["count"] >= 2:
                # 第 2 次调用时才创建文件
                if not os.path.exists(file_path):
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(sample_content)
            return original_isfile(path)

        with patch("os.path.isfile", side_effect=mock_isfile):
            verifier = ArtifactWriteVerifier(tmp_artifact_dir, max_retries=3)
            result = verifier.verify_artifact(
                "houfa", "delayed_report.md", actual_size, actual_md5
            )

        assert result["passed"] is True
        assert result["retries"] == 2  # 第 2 次重试通过

    def test_error_log_records_each_attempt(self, tmp_artifact_dir):
        """每次失败都在 errors 列表中记录"""
        verifier = ArtifactWriteVerifier(tmp_artifact_dir, max_retries=3)
        result = verifier.verify_artifact(
            "houfa", "missing.md", 100, "abc123"
        )
        assert len(result["errors"]) == 3
        assert all("第" in err for err in result["errors"])

    def test_attempts_log_records_each_attempt(self, tmp_artifact_dir):
        """每次尝试都在 attempts 列表中记录"""
        verifier = ArtifactWriteVerifier(tmp_artifact_dir, max_retries=3)
        result = verifier.verify_artifact(
            "houfa", "missing.md", 100, "abc123"
        )
        assert len(result["attempts"]) == 3
        for i, attempt in enumerate(result["attempts"]):
            assert attempt["attempt"] == i + 1


class TestCeleryArtifactWorker:
    """Celery Worker 集成测试"""

    def test_worker_process_single_artifact_passes(
        self, tmp_artifact_dir, sample_content
    ):
        """Worker 处理单个产出物验证通过"""
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "code_output.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(sample_content)

        actual_size = len(sample_content.encode("utf-8"))
        actual_md5 = hashlib.md5(sample_content.encode("utf-8")).hexdigest()

        worker = CeleryArtifactWorker(tmp_artifact_dir)
        result = worker.process_artifact(
            "houfa", "code_output.py", actual_size, actual_md5
        )

        assert result["passed"] is True
        assert result["agent_name"] == "houfa"
        assert result["artifact_name"] == "code_output.py"

    def test_worker_process_single_artifact_fails(
        self, tmp_artifact_dir
    ):
        """Worker 处理单个产出物验证失败"""
        worker = CeleryArtifactWorker(tmp_artifact_dir)
        result = worker.process_artifact(
            "houfa", "missing.md", 100, "abc123"
        )
        assert result["passed"] is False

    def test_worker_task_log_recorded(self, tmp_artifact_dir, sample_content):
        """Worker 记录任务日志"""
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "report.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(sample_content)

        actual_size = len(sample_content.encode("utf-8"))
        actual_md5 = hashlib.md5(sample_content.encode("utf-8")).hexdigest()

        worker = CeleryArtifactWorker(tmp_artifact_dir)
        worker.process_artifact(
            "houfa", "report.md", actual_size, actual_md5
        )

        assert len(worker.task_log) == 2
        assert worker.task_log[0]["action"] == "process_artifact"
        assert worker.task_log[1]["action"] == "result"

    def test_worker_process_all_artifacts(self, tmp_artifact_dir,
                                          sample_content):
        """Worker 批量处理多个产出物"""
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "code_output.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(sample_content)

        actual_size = len(sample_content.encode("utf-8"))
        actual_md5 = hashlib.md5(sample_content.encode("utf-8")).hexdigest()

        artifacts = [
            {
                "agent_name": "houfa",
                "artifact_name": "code_output.py",
                "expected_size": actual_size,
                "expected_md5": actual_md5,
            },
            {
                "agent_name": "houfa",
                "artifact_name": "missing.md",
                "expected_size": 0,
                "expected_md5": "0000",
            },
        ]

        worker = CeleryArtifactWorker(tmp_artifact_dir)
        result = worker.process_all_artifacts(artifacts)

        assert result["total"] == 2
        assert result["passed"] is False  # 有一个失败
        assert len(result["results"]) == 2
        assert result["results"][0]["passed"] is True
        assert result["results"][1]["passed"] is False

    def test_worker_process_all_artifacts_all_pass(
        self, tmp_artifact_dir, sample_content
    ):
        """Worker 批量处理全部产出物均通过"""
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "code_output.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(sample_content)

        actual_size = len(sample_content.encode("utf-8"))
        actual_md5 = hashlib.md5(sample_content.encode("utf-8")).hexdigest()

        artifacts = [
            {
                "agent_name": "houfa",
                "artifact_name": "code_output.py",
                "expected_size": actual_size,
                "expected_md5": actual_md5,
            },
        ]

        worker = CeleryArtifactWorker(tmp_artifact_dir)
        result = worker.process_all_artifacts(artifacts)

        assert result["total"] == 1
        assert result["passed"] is True


class TestNamedAgentArtifacts:
    """命名 Agent 产出物验证场景测试"""

    def test_named_agent_houfa_code_output(
        self, tmp_artifact_dir
    ):
        """验证后发（程序员）的代码产出物"""
        code_content = """def calculate_sum(a, b):
    return a + b
"""
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "calculator.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code_content)

        actual_size = len(code_content.encode("utf-8"))
        actual_md5 = hashlib.md5(code_content.encode("utf-8")).hexdigest()

        worker = CeleryArtifactWorker(tmp_artifact_dir)
        result = worker.process_artifact(
            "houfa", "calculator.py", actual_size, actual_md5
        )
        assert result["passed"] is True
        assert result["agent_name"] == "houfa"

    def test_named_agent_hougui_doc_output(
        self, tmp_artifact_dir
    ):
        """验证后贵（文档管理员）的文档产出物"""
        doc_content = "# API 文档\n\n## 接口说明\n\n### GET /api/users\n返回用户列表"
        agent_dir = os.path.join(tmp_artifact_dir, "hougui")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "api_doc.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(doc_content)

        actual_size = len(doc_content.encode("utf-8"))
        actual_md5 = hashlib.md5(doc_content.encode("utf-8")).hexdigest()

        worker = CeleryArtifactWorker(tmp_artifact_dir)
        result = worker.process_artifact(
            "hougui", "api_doc.md", actual_size, actual_md5
        )
        assert result["passed"] is True

    def test_named_agent_houda_test_report(
        self, tmp_artifact_dir
    ):
        """验证后达（测试员）的测试报告产出物"""
        report_content = '{"test_cases": 50, "passed": 48, "failed": 2, "coverage": 92.5}'
        agent_dir = os.path.join(tmp_artifact_dir, "houda")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "test_report.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        actual_size = len(report_content.encode("utf-8"))
        actual_md5 = hashlib.md5(report_content.encode("utf-8")).hexdigest()

        worker = CeleryArtifactWorker(tmp_artifact_dir)
        result = worker.process_artifact(
            "houda", "test_report.json", actual_size, actual_md5
        )
        assert result["passed"] is True

    def test_multiple_named_agents_artifacts(
        self, tmp_artifact_dir
    ):
        """多命名 Agent 产出物批量验证"""
        artifacts_data = [
            ("houfa", "code.py", "def hello(): pass"),
            ("hougui", "doc.md", "# 文档"),
            ("houda", "report.json", '{"status": "ok"}'),
        ]

        artifacts = []
        for agent_name, filename, content in artifacts_data:
            agent_dir = os.path.join(tmp_artifact_dir, agent_name)
            os.makedirs(agent_dir, exist_ok=True)
            file_path = os.path.join(agent_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            artifacts.append({
                "agent_name": agent_name,
                "artifact_name": filename,
                "expected_size": len(content.encode("utf-8")),
                "expected_md5": hashlib.md5(
                    content.encode("utf-8")
                ).hexdigest(),
            })

        worker = CeleryArtifactWorker(tmp_artifact_dir)
        result = worker.process_all_artifacts(artifacts)

        assert result["total"] == 3
        assert result["passed"] is True
        for r in result["results"]:
            assert r["passed"] is True
            assert r["retries"] == 1


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_file(self, tmp_artifact_dir):
        """空文件（0 字节）验证"""
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "empty.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            pass  # 空文件

        actual_md5 = hashlib.md5(b"").hexdigest()
        verifier = ArtifactWriteVerifier(tmp_artifact_dir)
        result = verifier.verify_artifact(
            "houfa", "empty.txt", 0, actual_md5
        )
        assert result["passed"] is True

    def test_large_file(self, tmp_artifact_dir):
        """大文件 MD5 计算（分块读取）"""
        content = "A" * (1024 * 1024)  # 1 MB
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "large.bin")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        actual_size = len(content.encode("utf-8"))
        actual_md5 = hashlib.md5(content.encode("utf-8")).hexdigest()

        verifier = ArtifactWriteVerifier(tmp_artifact_dir)
        result = verifier.verify_artifact(
            "houfa", "large.bin", actual_size, actual_md5
        )
        assert result["passed"] is True

    def test_unicode_content(self, tmp_artifact_dir):
        """含 Unicode 字符的产出物"""
        content = "中文产出物测试 — DevFlow 命名 Agent 验证 ✅"
        agent_dir = os.path.join(tmp_artifact_dir, "hougui")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "unicode.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        actual_size = len(content.encode("utf-8"))
        actual_md5 = hashlib.md5(content.encode("utf-8")).hexdigest()

        verifier = ArtifactWriteVerifier(tmp_artifact_dir)
        result = verifier.verify_artifact(
            "hougui", "unicode.md", actual_size, actual_md5
        )
        assert result["passed"] is True

    def test_max_retries_default_is_three(self, tmp_artifact_dir):
        """默认最大重试次数为 3"""
        verifier = ArtifactWriteVerifier(tmp_artifact_dir)
        assert verifier.max_retries == 3

    def test_binary_md5_consistency(self, tmp_artifact_dir):
        """同一文件多次 MD5 计算结果一致"""
        content = b"\x00\x01\x02\xff\xfe"
        agent_dir = os.path.join(tmp_artifact_dir, "houfa")
        os.makedirs(agent_dir, exist_ok=True)
        file_path = os.path.join(agent_dir, "binary.dat")
        with open(file_path, "wb") as f:
            f.write(content)

        verifier = ArtifactWriteVerifier(tmp_artifact_dir)
        md5_1 = verifier.compute_md5(file_path)
        md5_2 = verifier.compute_md5(file_path)
        md5_3 = verifier.compute_md5(file_path)
        assert md5_1 == md5_2 == md5_3
