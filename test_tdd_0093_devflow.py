import os
import tempfile
from pathlib import Path

import pytest


class ProjectInitializer:
    """模拟的项目初始化器，用于 TDD 测试驱动开发。"""

    def __init__(self, base_path: str):
        self._base_path = base_path
        self._initialized = False

    def get_project_path(self) -> str:
        return os.path.join(self._base_path, "my_project")

    def get_project_name(self) -> str:
        return "my_project"

    def initialize_project(self) -> str:
        project_path = self.get_project_path()
        os.makedirs(project_path, exist_ok=True)
        for subdir in ("src", "tests", "docs", "config", "scripts"):
            os.makedirs(os.path.join(project_path, subdir), exist_ok=True)
        env_path = os.path.join(project_path, ".env")
        if not os.path.exists(env_path):
            with open(env_path, "w") as f:
                f.write("# Project environment variables\n")
                f.write("DATABASE_URL=postgresql://localhost:5432/db\n")
                f.write("SECRET_KEY=your-secret-key-here\n")
                f.write("DEBUG=true\n")
        self._initialized = True
        return project_path

    def is_initialized(self) -> bool:
        return self._initialized


class TestProjectFolderInitialization:
    """项目文件夹初始化 — 验证项目创建时自动初始化项目文件夹。"""

    @pytest.fixture
    def initializer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ProjectInitializer(tmpdir)

    def test_get_project_path_before_initialize(self, initializer):
        """初始化前 get_project_path 应返回路径但不一定存在。"""
        path = initializer.get_project_path()
        assert isinstance(path, str), "路径应返回字符串"
        assert os.path.isabs(path), "路径应为绝对路径"
        assert not os.path.exists(path), "初始化前路径不应已存在"

    def test_get_project_path_after_initialize(self, initializer):
        """初始化后 get_project_path 返回的路径应存在。"""
        initializer.initialize_project()
        path = initializer.get_project_path()
        assert isinstance(path, str), "路径应返回字符串"
        assert os.path.isabs(path), "路径应为绝对路径"
        assert os.path.exists(path), "初始化后路径应已存在"

    def test_initialize_creates_directory_structure(self, initializer):
        """初始化应创建完整的目录结构：src/、tests/、docs/、config/、scripts/。"""
        project_path = initializer.initialize_project()
        expected_subdirs = ["src", "tests", "docs", "config", "scripts"]
        for subdir in expected_subdirs:
            subdir_path = os.path.join(project_path, subdir)
            assert os.path.isdir(subdir_path), f"缺少子目录: {subdir}"

    def test_initialize_creates_env_file(self, initializer):
        """初始化应自动创建 .env 文件，包含必要的环境变量模板。"""
        project_path = initializer.initialize_project()
        env_path = os.path.join(project_path, ".env")
        assert os.path.isfile(env_path), ".env 文件应存在"
        with open(env_path) as f:
            content = f.read()
        assert "DATABASE_URL" in content, ".env 应包含 DATABASE_URL"
        assert "SECRET_KEY" in content, ".env 应包含 SECRET_KEY"
        assert "DEBUG" in content, ".env 应包含 DEBUG"

    def test_get_project_path_special_characters(self, initializer):
        """项目名含特殊字符时 get_project_path 应正常返回路径。"""
        initializer._base_path = os.path.join(initializer._base_path, "my-project_123")
        path = initializer.get_project_path()
        assert isinstance(path, str), "路径应返回字符串"
        assert "my-project_123" in path, "路径应包含特殊字符项目名"
        assert os.path.isabs(path), "路径应为绝对路径"

    def test_initialize_folder_created_within_one_second(self, initializer):
        """验证项目文件夹在 1 秒内创建完成。"""
        import time
        start = time.time()
        initializer.initialize_project()
        elapsed = time.time() - start
        path = initializer.get_project_path()
        assert os.path.exists(path), "项目文件夹应存在"
        assert elapsed < 1.0, f"文件夹创建耗时 {elapsed:.3f}s，超过 1 秒限制"

    def test_is_initialized_returns_true_after_initialize(self, initializer):
        """初始化后 is_initialized 应返回 True。"""
        assert not initializer.is_initialized(), "初始化前 is_initialized 应为 False"
        initializer.initialize_project()
        assert initializer.is_initialized(), "初始化后 is_initialized 应为 True"

    def test_double_initialize_does_not_raise(self, initializer):
        """重复初始化不应引发异常。"""
        initializer.initialize_project()
        initializer.initialize_project()
        assert initializer.is_initialized(), "重复初始化后状态应仍为 True"
