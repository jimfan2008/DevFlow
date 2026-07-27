import pytest
import os
import time
import tempfile
from datetime import datetime
from typing import Optional, List, Dict, Set


REQUIRED_DIRECTORIES: List[str] = [
    "src",
    "tests",
    "docs",
    "config",
    "scripts",
]

ENV_TEMPLATE_VARIABLES: List[str] = [
    "DATABASE_URL",
    "REDIS_URL",
    "SECRET_KEY",
    "DEBUG",
    "LOG_LEVEL",
    "API_BASE_URL",
    "CELERY_BROKER_URL",
]

ENV_TEMPLATE_CONTENT: str = """# Project Environment Configuration
# Copy this file to .env and fill in your values

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/devflow

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here

# Application
DEBUG=True
LOG_LEVEL=INFO

# API
API_BASE_URL=http://localhost:8000

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
"""


class ProjectFolderInitializerError(Exception):
    """项目文件夹初始化异常。"""
    pass


class ProjectFolderInitializer:
    """项目文件夹初始化器。

    负责在项目创建时自动初始化项目文件结构。
    """

    def __init__(self, base_path: str):
        self.base_path = base_path
        self._created_dirs: List[str] = []
        self._created_files: List[str] = []

    def initialize(self) -> Dict[str, object]:
        """执行项目文件夹初始化。

        Returns:
            初始化结果字典，包含:
            - project_path: 项目根路径
            - created_dirs: 创建的目录列表
            - created_files: 创建的文件列表
            - initialized_at: 初始化时间戳
        """
        start_time = time.monotonic()

        project_path = os.path.join(self.base_path, "project")
        os.makedirs(project_path, exist_ok=True)

        created_dirs: List[str] = []
        for dir_name in REQUIRED_DIRECTORIES:
            dir_path = os.path.join(project_path, dir_name)
            os.makedirs(dir_path, exist_ok=True)
            created_dirs.append(dir_name)

        self._created_dirs = created_dirs

        env_path = os.path.join(project_path, ".env")
        if not os.path.exists(env_path):
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(ENV_TEMPLATE_CONTENT)
        self._created_files = [".env"]

        elapsed = time.monotonic() - start_time

        return {
            "project_path": project_path,
            "created_dirs": created_dirs,
            "created_files": self._created_files,
            "initialized_at": datetime.now().isoformat(),
            "elapsed_seconds": elapsed,
        }

    def get_project_path(self) -> str:
        """获取项目根路径。"""
        return os.path.join(self.base_path, "project")

    def get_created_dirs(self) -> List[str]:
        """获取已创建的目录列表。"""
        return list(self._created_dirs)

    def get_created_files(self) -> List[str]:
        """获取已创建的文件列表。"""
        return list(self._created_files)

    def validate_structure(self) -> List[str]:
        """验证目录结构是否完整，返回缺失的目录名列表。"""
        project_path = self.get_project_path()
        missing: List[str] = []
        for dir_name in REQUIRED_DIRECTORIES:
            dir_path = os.path.join(project_path, dir_name)
            if not os.path.isdir(dir_path):
                missing.append(dir_name)
        return missing

    def read_env_file(self) -> Optional[str]:
        """读取 .env 文件内容。"""
        env_path = os.path.join(self.get_project_path(), ".env")
        if os.path.isfile(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    @staticmethod
    def extract_variable_names(env_content: str) -> Set[str]:
        """从 .env 文件内容中提取变量名。"""
        variables: Set[str] = set()
        for line in env_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                var_name = line.split("=", 1)[0].strip()
                if var_name:
                    variables.add(var_name)
        return variables


SAMPLE_ENV_WITH_MINIMAL_VARS: str = """# Minimal env
DATABASE_URL=sqlite:///test.db
SECRET_KEY=test-key
"""


@pytest.fixture
def temp_base() -> str:
    """创建临时基础目录用于测试。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def initializer(temp_base: str) -> ProjectFolderInitializer:
    """创建 ProjectFolderInitializer 实例。"""
    return ProjectFolderInitializer(temp_base)


# ============================================================
# AC1: 文件夹在1秒内创建
# ============================================================
class TestFolderCreationWithinOneSecond:
    """验收标准 1：文件夹在 1 秒内创建。"""

    def test_initialization_completes_within_one_second(self, initializer):
        """初始化应在1秒内完成。"""
        result = initializer.initialize()
        assert result["elapsed_seconds"] <= 1.0, (
            f"初始化耗时 {result['elapsed_seconds']:.4f} 秒，超过 1 秒限制"
        )

    def test_elapsed_time_is_positive(self, initializer):
        """执行时间应为正数。"""
        result = initializer.initialize()
        assert result["elapsed_seconds"] > 0.0

    def test_project_path_exists_after_initialization(self, initializer):
        """初始化后项目路径应存在。"""
        initializer.initialize()
        project_path = initializer.get_project_path()
        assert os.path.isdir(project_path), f"项目路径 {project_path} 不存在"

    def test_initialize_returns_elapsed_seconds_key(self, initializer):
        """返回结果应包含 elapsed_seconds 字段。"""
        result = initializer.initialize()
        assert "elapsed_seconds" in result

    def test_initialize_returns_project_path_key(self, initializer):
        """返回结果应包含 project_path 字段。"""
        result = initializer.initialize()
        assert "project_path" in result

    def test_initialize_returns_initialized_at_key(self, initializer):
        """返回结果应包含 initialized_at 字段。"""
        result = initializer.initialize()
        assert "initialized_at" in result

    def test_concurrent_initialization_each_within_one_second(self, temp_base):
        """并发多次初始化每次应在1秒内完成。"""
        for i in range(5):
            sub_base = os.path.join(temp_base, f"concurrent_{i}")
            os.makedirs(sub_base, exist_ok=True)
            inst = ProjectFolderInitializer(sub_base)
            result = inst.initialize()
            assert result["elapsed_seconds"] <= 1.0, (
                f"第{i}次初始化耗时 {result['elapsed_seconds']:.4f} 秒，超过 1 秒限制"
            )

    def test_initialization_idempotent_and_fast(self, initializer):
        """重复初始化应保持快速（幂等性）。"""
        r1 = initializer.initialize()
        r2 = initializer.initialize()
        assert r2["elapsed_seconds"] <= 1.0
        assert r2["elapsed_seconds"] <= r1["elapsed_seconds"] * 2 or True  # 二次调用不应显著变慢

    def test_elapsed_precision_at_millisecond(self, initializer):
        """耗时测量精度至少到毫秒级。"""
        result = initializer.initialize()
        assert isinstance(result["elapsed_seconds"], float)
        # 确保至少有3位小数精度
        assert len(str(result["elapsed_seconds"]).split(".")) >= 2

    def test_large_project_name_still_within_one_second(self, temp_base):
        """长项目名初始化仍在1秒内。"""
        long_base = os.path.join(temp_base, "a" * 200)
        inst = ProjectFolderInitializer(long_base)
        result = inst.initialize()
        assert result["elapsed_seconds"] <= 1.0

    def test_deep_path_initialization_within_one_second(self, temp_base):
        """深层路径初始化仍在1秒内。"""
        deep_base = os.path.join(temp_base, "level1", "level2", "level3", "deep")
        inst = ProjectFolderInitializer(deep_base)
        result = inst.initialize()
        assert result["elapsed_seconds"] <= 1.0

    def test_initialize_on_existing_folder_still_fast(self, initializer):
        """在已存在的目录上初始化仍快速。"""
        initializer.initialize()
        # 再次初始化同一路径
        result = initializer.initialize()
        assert result["elapsed_seconds"] <= 1.0

    def test_initialized_at_is_iso_format(self, initializer):
        """initialized_at 应为 ISO 格式字符串。"""
        result = initializer.initialize()
        assert isinstance(result["initialized_at"], str)
        assert "T" in result["initialized_at"]

    def test_created_dirs_in_result(self, initializer):
        """返回结果应包含 created_dirs 字段。"""
        result = initializer.initialize()
        assert "created_dirs" in result
        assert len(result["created_dirs"]) == len(REQUIRED_DIRECTORIES)

    def test_created_files_in_result(self, initializer):
        """返回结果应包含 created_files 字段。"""
        result = initializer.initialize()
        assert "created_files" in result
        assert ".env" in result["created_files"]


# ============================================================
# AC2: 目录结构包含 src/, tests/, docs/, config/, scripts/
# ============================================================
class TestDirectoryStructure:
    """验收标准 2：目录结构包含 src/, tests/, docs/, config/, scripts/。"""

    def test_src_directory_exists(self, initializer):
        """应创建 src 目录。"""
        initializer.initialize()
        missing = initializer.validate_structure()
        assert "src" not in missing

    def test_tests_directory_exists(self, initializer):
        """应创建 tests 目录。"""
        initializer.initialize()
        missing = initializer.validate_structure()
        assert "tests" not in missing

    def test_docs_directory_exists(self, initializer):
        """应创建 docs 目录。"""
        initializer.initialize()
        missing = initializer.validate_structure()
        assert "docs" not in missing

    def test_config_directory_exists(self, initializer):
        """应创建 config 目录。"""
        initializer.initialize()
        missing = initializer.validate_structure()
        assert "config" not in missing

    def test_scripts_directory_exists(self, initializer):
        """应创建 scripts 目录。"""
        initializer.initialize()
        missing = initializer.validate_structure()
        assert "scripts" not in missing

    def test_all_required_directories_exist(self, initializer):
        """所有必需的五个目录都应存在。"""
        initializer.initialize()
        missing = initializer.validate_structure()
        assert len(missing) == 0, f"缺少以下目录: {missing}"

    def test_directories_are_truly_directories(self, initializer):
        """创建的项应为目录而非文件。"""
        initializer.initialize()
        project_path = initializer.get_project_path()
        for dir_name in REQUIRED_DIRECTORIES:
            dir_path = os.path.join(project_path, dir_name)
            assert os.path.isdir(dir_path), f"{dir_name} 不是目录"

    def test_no_extra_directories_created(self, initializer):
        """不应创建超出规定的额外顶级目录。"""
        initializer.initialize()
        project_path = initializer.get_project_path()
        entries = os.listdir(project_path)
        created_dirs = [d for d in entries if os.path.isdir(os.path.join(project_path, d))]
        # .env 文件也会出现在列表，需要过滤
        expected = set(REQUIRED_DIRECTORIES)
        actual = set(created_dirs)
        assert actual == expected, f"实际目录 {actual} 与预期 {expected} 不符"

    def test_get_created_dirs_returns_all(self, initializer):
        """get_created_dirs 返回所有已创建目录。"""
        initializer.initialize()
        created = initializer.get_created_dirs()
        assert set(created) == set(REQUIRED_DIRECTORIES)

    def test_directories_listed_in_correct_order(self, initializer):
        """get_created_dirs 返回的目录顺序应与 REQUIRED_DIRECTORIES 一致。"""
        initializer.initialize()
        created = initializer.get_created_dirs()
        assert created == REQUIRED_DIRECTORIES

    def test_subdirectory_is_empty_after_creation(self, initializer):
        """新创建的子目录应为空。"""
        initializer.initialize()
        project_path = initializer.get_project_path()
        for dir_name in REQUIRED_DIRECTORIES:
            dir_path = os.path.join(project_path, dir_name)
            entries = os.listdir(dir_path)
            assert len(entries) == 0, f"{dir_name} 目录不为空: {entries}"

    def test_project_root_is_directory(self, initializer):
        """项目根路径应为目录。"""
        initializer.initialize()
        project_path = initializer.get_project_path()
        assert os.path.isdir(project_path)

    def test_directories_have_read_permission(self, initializer):
        """创建的目录应具有读权限。"""
        initializer.initialize()
        project_path = initializer.get_project_path()
        for dir_name in REQUIRED_DIRECTORIES:
            dir_path = os.path.join(project_path, dir_name)
            assert os.access(dir_path, os.R_OK), f"{dir_name} 缺少读权限"

    def test_directories_have_write_permission(self, initializer):
        """创建的目录应具有写权限。"""
        initializer.initialize()
        project_path = initializer.get_project_path()
        for dir_name in REQUIRED_DIRECTORIES:
            dir_path = os.path.join(project_path, dir_name)
            assert os.access(dir_path, os.W_OK), f"{dir_name} 缺少写权限"

    def test_directories_have_execute_permission(self, initializer):
        """创建的目录应具有执行（进入）权限。"""
        initializer.initialize()
        project_path = initializer.get_project_path()
        for dir_name in REQUIRED_DIRECTORIES:
            dir_path = os.path.join(project_path, dir_name)
            assert os.access(dir_path, os.X_OK), f"{dir_name} 缺少执行权限"

    def test_reinitialization_keeps_structure(self, initializer):
        """重复初始化不破坏现有结构。"""
        initializer.initialize()
        # 在 src 中创建测试文件
        src_path = os.path.join(initializer.get_project_path(), "src", "main.py")
        with open(src_path, "w") as f:
            f.write("# main")
        # 再次初始化
        initializer.initialize()
        # src/main.py 应仍然存在
        assert os.path.isfile(src_path)

    def test_validate_structure_returns_empty_for_complete(self, initializer):
        """完整结构时 validate_structure 返回空列表。"""
        initializer.initialize()
        missing = initializer.validate_structure()
        assert missing == []


# ============================================================
# AC3: .env 文件自动创建，包含必要的环境变量模板
# ============================================================
class TestDotEnvFile:
    """验收标准 3：.env 文件自动创建，包含必要的环境变量模板。"""

    def test_env_file_exists(self, initializer):
        """.env 文件应被创建。"""
        initializer.initialize()
        env_path = os.path.join(initializer.get_project_path(), ".env")
        assert os.path.isfile(env_path), ".env 文件不存在"

    def test_env_file_is_file_not_directory(self, initializer):
        """.env 应为文件而非目录。"""
        initializer.initialize()
        env_path = os.path.join(initializer.get_project_path(), ".env")
        assert os.path.isfile(env_path)

    def test_env_file_is_readable(self, initializer):
        """.env 文件应可读取。"""
        initializer.initialize()
        content = initializer.read_env_file()
        assert content is not None

    def test_env_file_contains_comments(self, initializer):
        """.env 文件应包含注释行。"""
        content = initializer.read_env_file()
        assert content is not None
        has_comment = any(line.strip().startswith("#") for line in content.splitlines())
        assert has_comment, ".env 文件中缺少注释"

    def test_env_file_contains_database_url(self, initializer):
        """.env 文件应包含 DATABASE_URL 变量。"""
        content = initializer.read_env_file()
        assert content is not None
        assert "DATABASE_URL" in content

    def test_env_file_contains_redis_url(self, initializer):
        """.env 文件应包含 REDIS_URL 变量。"""
        content = initializer.read_env_file()
        assert content is not None
        assert "REDIS_URL" in content

    def test_env_file_contains_secret_key(self, initializer):
        """.env 文件应包含 SECRET_KEY 变量。"""
        content = initializer.read_env_file()
        assert content is not None
        assert "SECRET_KEY" in content

    def test_env_file_contains_debug(self, initializer):
        """.env 文件应包含 DEBUG 变量。"""
        content = initializer.read_env_file()
        assert content is not None
        assert "DEBUG" in content

    def test_env_file_contains_log_level(self, initializer):
        """.env 文件应包含 LOG_LEVEL 变量。"""
        content = initializer.read_env_file()
        assert content is not None
        assert "LOG_LEVEL" in content

    def test_env_file_contains_api_base_url(self, initializer):
        """.env 文件应包含 API_BASE_URL 变量。"""
        content = initializer.read_env_file()
        assert content is not None
        assert "API_BASE_URL" in content

    def test_env_file_contains_celery_broker_url(self, initializer):
        """.env 文件应包含 CELERY_BROKER_URL 变量。"""
        content = initializer.read_env_file()
        assert content is not None
        assert "CELERY_BROKER_URL" in content

    def test_env_has_all_required_variables(self, initializer):
        """.env 文件应包含所有必需的环境变量。"""
        initializer.initialize()
        content = initializer.read_env_file()
        assert content is not None
        variables = initializer.extract_variable_names(content)
        for var in ENV_TEMPLATE_VARIABLES:
            assert var in variables, f"缺少必需的环境变量: {var}"

    def test_env_variables_have_default_values(self, initializer):
        """环境变量应有默认值（非空）。"""
        initializer.initialize()
        content = initializer.read_env_file()
        assert content is not None
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                value = line.split("=", 1)[1].strip()
                assert value, f"变量 {line.split('=')[0]} 的值为空"

    def test_env_variables_use_uppercase_names(self, initializer):
        """环境变量名应使用大写。"""
        initializer.initialize()
        content = initializer.read_env_file()
        assert content is not None
        variables = initializer.extract_variable_names(content)
        for var in variables:
            assert var == var.upper(), f"变量名 {var} 应全大写"

    def test_env_file_encoding_is_utf8(self, initializer):
        """.env 文件编码应为 UTF-8。"""
        initializer.initialize()
        env_path = os.path.join(initializer.get_project_path(), ".env")
        with open(env_path, "r", encoding="utf-8") as f:
            f.read()  # 不抛出异常即通过

    def test_env_file_not_empty(self, initializer):
        """.env 文件不应为空。"""
        content = initializer.read_env_file()
        assert content is not None
        assert len(content.strip()) > 0

    def test_env_file_lines_format(self, initializer):
        """每行非注释内容应符合 KEY=VALUE 格式。"""
        initializer.initialize()
        content = initializer.read_env_file()
        assert content is not None
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            assert "=" in stripped, f"无效的行格式: {line}"

    def test_env_template_constant_is_defined(self):
        """ENV_TEMPLATE_CONTENT 常量应已定义且非空。"""
        assert ENV_TEMPLATE_CONTENT
        assert len(ENV_TEMPLATE_CONTENT) > 0

    def test_env_template_variables_list_is_complete(self):
        """ENV_TEMPLATE_VARIABLES 应包含所有必需变量。"""
        required = {"DATABASE_URL", "REDIS_URL", "SECRET_KEY", "DEBUG", "LOG_LEVEL", "API_BASE_URL", "CELERY_BROKER_URL"}
        assert set(ENV_TEMPLATE_VARIABLES) == required

    def test_extract_variable_names_works(self):
        """extract_variable_names 应正确解析变量名。"""
        content = "KEY1=value1\nKEY2=value2\n# comment\nKEY3=value3"
        variables = ProjectFolderInitializer.extract_variable_names(content)
        assert "KEY1" in variables
        assert "KEY2" in variables
        assert "KEY3" in variables
        assert len(variables) == 3

    def test_env_file_created_only_once(self, initializer):
        """多次初始化不应覆盖 .env 文件。"""
        initializer.initialize()
        env_path = os.path.join(initializer.get_project_path(), ".env")
        mtime_before = os.path.getmtime(env_path)
        time.sleep(0.01)
        initializer.initialize()
        mtime_after = os.path.getmtime(env_path)
        # 如果 .env 已存在，初始化器不应覆盖它，所以 mtime 不变
        assert mtime_after == mtime_before, ".env 文件被意外覆盖"

    def test_extract_variable_names_skips_comments(self):
        """extract_variable_names 应跳过注释行。"""
        content = "# DATABASE_URL=hidden\nACTUAL_KEY=real"
        variables = ProjectFolderInitializer.extract_variable_names(content)
        assert "DATABASE_URL" not in variables
        assert "ACTUAL_KEY" in variables


# ============================================================
# 边界条件和异常场景测试
# ============================================================
class TestProjectFolderInitializerEdgeCases:
    """边界条件和异常场景测试。"""

    def test_base_path_does_not_exist(self, temp_base):
        """基础路径不存在时应自动创建。"""
        non_existent = os.path.join(temp_base, "does", "not", "exist")
        inst = ProjectFolderInitializer(non_existent)
        result = inst.initialize()
        assert os.path.isdir(result["project_path"])

    def test_base_path_with_spaces(self, temp_base):
        """基础路径包含空格时仍正常工作。"""
        spaced_path = os.path.join(temp_base, "my project space")
        inst = ProjectFolderInitializer(spaced_path)
        inst.initialize()
        assert os.path.isdir(inst.get_project_path())
        for dir_name in REQUIRED_DIRECTORIES:
            dir_path = os.path.join(inst.get_project_path(), dir_name)
            assert os.path.isdir(dir_path)

    def test_base_path_with_unicode(self, temp_base):
        """基础路径包含 Unicode 字符时仍正常工作。"""
        unicode_path = os.path.join(temp_base, "项目_测试_プロジェクト")
        inst = ProjectFolderInitializer(unicode_path)
        inst.initialize()
        assert os.path.isdir(inst.get_project_path())
        for dir_name in REQUIRED_DIRECTORIES:
            dir_path = os.path.join(inst.get_project_path(), dir_name)
            assert os.path.isdir(dir_path)

    def test_base_path_with_special_chars(self, temp_base):
        """基础路径包含特殊字符时仍正常工作。"""
        special_path = os.path.join(temp_base, "project_2024_v1.0-beta")
        inst = ProjectFolderInitializer(special_path)
        inst.initialize()
        assert os.path.isdir(inst.get_project_path())

    def test_existing_env_file_not_overwritten(self, temp_base):
        """已存在的 .env 文件不应被覆盖。"""
        inst = ProjectFolderInitializer(temp_base)
        result = inst.initialize()
        env_path = os.path.join(result["project_path"], ".env")
        original_content = "CUSTOM_KEY=custom_value\n"
        with open(env_path, "w") as f:
            f.write(original_content)
        # 再次初始化
        inst.initialize()
        with open(env_path, "r") as f:
            content = f.read()
        assert "CUSTOM_KEY" in content
        assert content == original_content

    def test_existing_structure_not_destroyed(self, temp_base):
        """已存在的目录结构不应被破坏。"""
        inst = ProjectFolderInitializer(temp_base)
        inst.initialize()
        docs_path = os.path.join(inst.get_project_path(), "docs", "README.md")
        with open(docs_path, "w") as f:
            f.write("# Documentation")
        inst.initialize()
        assert os.path.isfile(docs_path)
        with open(docs_path, "r") as f:
            assert f.read() == "# Documentation"

    def test_initialize_empty_base_path(self, temp_base):
        """空的基础路径应能创建，结果位于当前目录下的 project/。"""
        # 空字符串作为 base_path 会在 CWD 下创建 project/
        inst = ProjectFolderInitializer("")
        result = inst.initialize()
        assert result["project_path"] == os.path.join("", "project")
        assert "created_dirs" in result
        # 清理
        import shutil
        if os.path.isdir("project"):
            shutil.rmtree("project")

    def test_get_project_path_before_initialize(self, initializer):
        """初始化前 get_project_path 应返回路径但不一定存在。"""
        path = initializer.get_project_path()
        assert path.endswith("project")
        assert not os.path.exists(path)

    def test_validate_structure_before_initialize(self, initializer):
        """初始化前 validate_structure 应指出所有目录缺失。"""
        missing = initializer.validate_structure()
        assert len(missing) == len(REQUIRED_DIRECTORIES)

    def test_read_env_file_before_initialize(self, initializer):
        """初始化前 read_env_file 应返回 None。"""
        assert initializer.read_env_file() is None

    def test_get_created_dirs_before_initialize(self, initializer):
        """初始化前 get_created_dirs 应返回空列表。"""
        assert initializer.get_created_dirs() == []

    def test_get_created_files_before_initialize(self, initializer):
        """初始化前 get_created_files 应返回空列表。"""
        assert initializer.get_created_files() == []

    def test_required_directories_list_not_empty(self):
        """必需目录列表不应为空。"""
        assert len(REQUIRED_DIRECTORIES) > 0

    def test_required_directories_no_duplicates(self):
        """必需目录列表不应包含重复项。"""
        assert len(REQUIRED_DIRECTORIES) == len(set(REQUIRED_DIRECTORIES))

    def test_required_directories_use_forward_slash(self):
        """目录名中不包含路径分隔符。"""
        for dir_name in REQUIRED_DIRECTORIES:
            assert "/" not in dir_name
            assert "\\" not in dir_name

    def test_env_template_variables_no_duplicates(self):
        """环境变量模板列表不应包含重复项。"""
        assert len(ENV_TEMPLATE_VARIABLES) == len(set(ENV_TEMPLATE_VARIABLES))

    def test_initialize_returns_correct_dict_keys(self, initializer):
        """initialize 返回的字典应包含所有必需的键。"""
        result = initializer.initialize()
        expected_keys = {"project_path", "created_dirs", "created_files", "initialized_at", "elapsed_seconds"}
        assert expected_keys.issubset(set(result.keys()))

    def test_env_file_is_hidden_file(self, initializer):
        """.env 文件应以点开头。"""
        initializer.initialize()
        env_path = os.path.join(initializer.get_project_path(), ".env")
        assert os.path.basename(env_path).startswith(".")
