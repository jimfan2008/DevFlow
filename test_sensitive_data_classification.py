"""敏感数据判定标准 — TDD 测试用例

验证非功能需求 6.3 节「敏感数据判定标准」表格
验收标准：敏感数据判定标准完整，6 类数据覆盖

6 类敏感数据：
  1. 用户凭据类 (user_credentials)
  2. 个人身份信息 (pii)
  3. 项目源代码 (project_source)
  4. 通信记录 (communication_records)
  5. 系统配置 (system_config)
  6. 审计日志 (audit_logs)
"""

import pytest
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


# ============================================================
# 领域模型
# ============================================================

class DataSensitivityLevel(str, Enum):
    """敏感数据级别"""
    CRITICAL = "critical"        # 绝密
    HIGH = "high"                # 高度敏感
    MEDIUM = "medium"            # 中度敏感
    LOW = "low"                  # 低度敏感


@dataclass
class DataCategory:
    """敏感数据类别定义"""
    category_key: str           # 类别唯一标识
    category_label: str         # 类别中文名称
    examples: List[str]         # 典型数据示例
    sensitivity_level: DataSensitivityLevel  # 敏感级别
    storage_policy: str         # 存储策略
    transmission_policy: str    # 传输策略
    access_control: str         # 访问控制策略
    retention_days: int         # 保留天数（-1 表示永久）
    encryption_required: bool   # 是否必须加密


# ============================================================
# 6 类敏感数据定义
# ============================================================

SENSITIVE_DATA_CATEGORIES: List[DataCategory] = [
    DataCategory(
        category_key="user_credentials",
        category_label="用户凭据类",
        examples=[
            "用户密码哈希",
            "JWT Access Token",
            "JWT Refresh Token",
            "OAuth 授权码",
            "会话 Cookie",
        ],
        sensitivity_level=DataSensitivityLevel.CRITICAL,
        storage_policy="bcrypt 加盐哈希存储，禁止明文存储",
        transmission_policy="仅允许 HTTPS 传输，禁止出现在 URL 或日志中",
        access_control="仅限用户本人，服务端不缓存明文",
        retention_days=-1,
        encryption_required=True,
    ),
    DataCategory(
        category_key="pii",
        category_label="个人身份信息",
        examples=[
            "用户真实姓名",
            "手机号码",
            "电子邮箱地址",
            "身份证号码",
            "联系地址",
        ],
        sensitivity_level=DataSensitivityLevel.HIGH,
        storage_policy="数据库字段级加密（AES-256），日志中脱敏显示",
        transmission_policy="HTTPS 传输，API 响应中按需脱敏（如 138****5678）",
        access_control="仅用户本人和管理员（后贵/海梅），管理员查看需二次确认",
        retention_days=-1,
        encryption_required=True,
    ),
    DataCategory(
        category_key="project_source",
        category_label="项目源代码",
        examples=[
            "Agent 生成的源代码",
            "项目需求文档",
            "架构设计文档",
            "测试用例代码",
            "QA 检验报告",
        ],
        sensitivity_level=DataSensitivityLevel.HIGH,
        storage_policy="项目仓库隔离存储，基于项目权限可见",
        transmission_policy="HTTPS 传输，下载需项目成员授权",
        access_control="项目发起者完全控制，项目成员按角色访问",
        retention_days=-1,
        encryption_required=False,
    ),
    DataCategory(
        category_key="communication_records",
        category_label="通信记录",
        examples=[
            "用户与 Agent 对话记录",
            "群聊消息",
            "会议模式发言记录",
            "会议模式投票记录",
            "用户反馈内容",
        ],
        sensitivity_level=DataSensitivityLevel.MEDIUM,
        storage_policy="按项目归档存储，支持用户主动删除",
        transmission_policy="HTTPS + WebSocket 加密传输",
        access_control="项目成员可见，外部用户不可见",
        retention_days=365,
        encryption_required=False,
    ),
    DataCategory(
        category_key="system_config",
        category_label="系统配置",
        examples=[
            "数据库连接字符串",
            "Redis 连接凭证",
            "LLM API Key",
            "服务间认证密钥",
            "SMTP 邮件服务器凭据",
        ],
        sensitivity_level=DataSensitivityLevel.CRITICAL,
        storage_policy="环境变量或密钥管理系统存储，禁止写入代码仓库",
        transmission_policy="仅允许本地进程内传递，禁止网络明文传输",
        access_control="仅系统管理员（超级管理员角色）可访问",
        retention_days=-1,
        encryption_required=True,
    ),
    DataCategory(
        category_key="audit_logs",
        category_label="审计日志",
        examples=[
            "用户登录/登出记录",
            "Agent 任务执行日志",
            "权限变更操作记录",
            "数据导出记录",
            "安全事件告警日志",
        ],
        sensitivity_level=DataSensitivityLevel.MEDIUM,
        storage_policy="独立审计日志表，不可篡改（append-only）",
        transmission_policy="内部系统直连查询，不对外暴露",
        access_control="仅安全管理员（后华）和超级管理员可查询",
        retention_days=730,
        encryption_required=False,
    ),
]


# ============================================================
# 敏感数据判定引擎
# ============================================================

class SensitiveDataClassifier:
    """敏感数据判定引擎"""

    def __init__(self, categories: List[DataCategory]):
        self.categories = categories
        self._category_map = {c.category_key: c for c in categories}

    def get_category(self, key: str) -> Optional[DataCategory]:
        """按类别标识获取数据类别定义"""
        return self._category_map.get(key)

    def get_categories_by_level(self, level: DataSensitivityLevel) -> List[DataCategory]:
        """按敏感级别筛选数据类别"""
        return [c for c in self.categories if c.sensitivity_level == level]

    def classify_data(self, data_type: str) -> Optional[DataCategory]:
        """
        根据数据类型的关键词判定其所属的敏感数据类别。
        匹配规则：若 data_type 包含某类别 examples 中的任意关键词，则归类到该类别。
        """
        for category in self.categories:
            for example in category.examples:
                if example.lower() in data_type.lower():
                    return category
        return None

    def get_security_policy(self, category_key: str) -> Optional[Dict[str, Any]]:
        """获取指定类别的完整安全策略"""
        cat = self._category_map.get(category_key)
        if cat is None:
            return None
        return {
            "category_key": cat.category_key,
            "category_label": cat.category_label,
            "sensitivity_level": cat.sensitivity_level.value,
            "storage_policy": cat.storage_policy,
            "transmission_policy": cat.transmission_policy,
            "access_control": cat.access_control,
            "retention_days": cat.retention_days,
            "encryption_required": cat.encryption_required,
        }

    def is_encryption_required(self, category_key: str) -> bool:
        """判断指定类别是否必须加密"""
        cat = self._category_map.get(category_key)
        return cat.encryption_required if cat else False

    def get_all_category_keys(self) -> List[str]:
        """获取所有已定义的类别标识"""
        return [c.category_key for c in self.categories]


# ============================================================
# 测试：6 类数据覆盖验证
# ============================================================

@pytest.fixture
def classifier():
    """创建敏感数据判定引擎实例"""
    return SensitiveDataClassifier(SENSITIVE_DATA_CATEGORIES)


class TestSensitiveDataCoverage:
    """测试 6 类敏感数据的覆盖完整性"""

    def test_total_categories_is_6(self, classifier):
        """验证：敏感数据类别总数为 6 类"""
        assert len(classifier.get_all_category_keys()) == 6

    def test_category_user_credentials_exists(self, classifier):
        """验证：用户凭据类已定义"""
        cat = classifier.get_category("user_credentials")
        assert cat is not None
        assert cat.category_label == "用户凭据类"
        assert cat.sensitivity_level == DataSensitivityLevel.CRITICAL

    def test_category_pii_exists(self, classifier):
        """验证：个人身份信息已定义"""
        cat = classifier.get_category("pii")
        assert cat is not None
        assert cat.category_label == "个人身份信息"
        assert cat.sensitivity_level == DataSensitivityLevel.HIGH

    def test_category_project_source_exists(self, classifier):
        """验证：项目源代码已定义"""
        cat = classifier.get_category("project_source")
        assert cat is not None
        assert cat.category_label == "项目源代码"
        assert cat.sensitivity_level == DataSensitivityLevel.HIGH

    def test_category_communication_records_exists(self, classifier):
        """验证：通信记录已定义"""
        cat = classifier.get_category("communication_records")
        assert cat is not None
        assert cat.category_label == "通信记录"
        assert cat.sensitivity_level == DataSensitivityLevel.MEDIUM

    def test_category_system_config_exists(self, classifier):
        """验证：系统配置已定义"""
        cat = classifier.get_category("system_config")
        assert cat is not None
        assert cat.category_label == "系统配置"
        assert cat.sensitivity_level == DataSensitivityLevel.CRITICAL

    def test_category_audit_logs_exists(self, classifier):
        """验证：审计日志已定义"""
        cat = classifier.get_category("audit_logs")
        assert cat is not None
        assert cat.category_label == "审计日志"
        assert cat.sensitivity_level == DataSensitivityLevel.MEDIUM


# ============================================================
# 测试：安全策略完整性
# ============================================================

class TestSecurityPolicyCompleteness:
    """测试每类数据的安全策略字段完整性"""

    def test_user_credentials_policy_complete(self, classifier):
        """验证：用户凭据类安全策略字段完整"""
        policy = classifier.get_security_policy("user_credentials")
        assert policy is not None
        assert policy["storage_policy"] == "bcrypt 加盐哈希存储，禁止明文存储"
        assert policy["transmission_policy"] == "仅允许 HTTPS 传输，禁止出现在 URL 或日志中"
        assert policy["access_control"] == "仅限用户本人，服务端不缓存明文"
        assert policy["encryption_required"] is True
        assert policy["retention_days"] == -1

    def test_pii_policy_complete(self, classifier):
        """验证：个人身份信息安全策略字段完整"""
        policy = classifier.get_security_policy("pii")
        assert policy is not None
        assert "AES-256" in policy["storage_policy"]
        assert policy["encryption_required"] is True
        assert policy["sensitivity_level"] == "high"

    def test_project_source_policy_complete(self, classifier):
        """验证：项目源代码安全策略字段完整"""
        policy = classifier.get_security_policy("project_source")
        assert policy is not None
        assert policy["encryption_required"] is False
        assert policy["retention_days"] == -1
        assert "项目权限" in policy["storage_policy"]

    def test_communication_records_policy_complete(self, classifier):
        """验证：通信记录安全策略字段完整"""
        policy = classifier.get_security_policy("communication_records")
        assert policy is not None
        assert policy["retention_days"] == 365
        assert policy["encryption_required"] is False

    def test_system_config_policy_complete(self, classifier):
        """验证：系统配置安全策略字段完整"""
        policy = classifier.get_security_policy("system_config")
        assert policy is not None
        assert policy["sensitivity_level"] == "critical"
        assert policy["encryption_required"] is True
        assert "密钥管理" in policy["storage_policy"] or "环境变量" in policy["storage_policy"]
        assert "禁止写入代码仓库" in policy["storage_policy"]

    def test_audit_logs_policy_complete(self, classifier):
        """验证：审计日志安全策略字段完整"""
        policy = classifier.get_security_policy("audit_logs")
        assert policy is not None
        assert policy["retention_days"] == 730
        assert "append-only" in policy["storage_policy"] or "不可篡改" in policy["storage_policy"]
        assert policy["encryption_required"] is False


# ============================================================
# 测试：敏感级别分布
# ============================================================

class TestSensitivityLevelDistribution:
    """测试敏感数据级别分布"""

    def test_critical_level_count(self, classifier):
        """验证：绝密级别数据有 2 类"""
        critical = classifier.get_categories_by_level(DataSensitivityLevel.CRITICAL)
        assert len(critical) == 2
        assert "user_credentials" in [c.category_key for c in critical]
        assert "system_config" in [c.category_key for c in critical]

    def test_high_level_count(self, classifier):
        """验证：高度敏感级别数据有 2 类"""
        high = classifier.get_categories_by_level(DataSensitivityLevel.HIGH)
        assert len(high) == 2
        assert "pii" in [c.category_key for c in high]
        assert "project_source" in [c.category_key for c in high]

    def test_medium_level_count(self, classifier):
        """验证：中度敏感级别数据有 2 类"""
        medium = classifier.get_categories_by_level(DataSensitivityLevel.MEDIUM)
        assert len(medium) == 2
        assert "communication_records" in [c.category_key for c in medium]
        assert "audit_logs" in [c.category_key for c in medium]

    def test_no_low_level_categories(self, classifier):
        """验证：无低度敏感级别的数据类别"""
        low = classifier.get_categories_by_level(DataSensitivityLevel.LOW)
        assert len(low) == 0


# ============================================================
# 测试：数据分类判定
# ============================================================

class TestDataClassification:
    """测试敏感数据分类判定引擎"""

    def test_classify_password(self, classifier):
        """验证：密码哈希归类为用户凭据类"""
        result = classifier.classify_data("用户密码哈希")
        assert result is not None
        assert result.category_key == "user_credentials"

    def test_classify_jwt_token(self, classifier):
        """验证：JWT Token 归类为用户凭据类"""
        result = classifier.classify_data("JWT Access Token")
        assert result is not None
        assert result.category_key == "user_credentials"

    def test_classify_phone_number(self, classifier):
        """验证：手机号码归类为个人身份信息"""
        result = classifier.classify_data("手机号码")
        assert result is not None
        assert result.category_key == "pii"

    def test_classify_email(self, classifier):
        """验证：电子邮箱地址归类为个人身份信息"""
        result = classifier.classify_data("电子邮箱地址")
        assert result is not None
        assert result.category_key == "pii"

    def test_classify_source_code(self, classifier):
        """验证：Agent 生成的源代码归类为项目源代码"""
        result = classifier.classify_data("Agent 生成的源代码")
        assert result is not None
        assert result.category_key == "project_source"

    def test_classify_chat_record(self, classifier):
        """验证：对话记录归类为通信记录"""
        result = classifier.classify_data("用户与 Agent 对话记录")
        assert result is not None
        assert result.category_key == "communication_records"

    def test_classify_db_connection(self, classifier):
        """验证：数据库连接字符串归类为系统配置"""
        result = classifier.classify_data("数据库连接字符串")
        assert result is not None
        assert result.category_key == "system_config"

    def test_classify_llm_api_key(self, classifier):
        """验证：LLM API Key 归类为系统配置"""
        result = classifier.classify_data("LLM API Key")
        assert result is not None
        assert result.category_key == "system_config"

    def test_classify_login_log(self, classifier):
        """验证：用户登录记录归类为审计日志"""
        result = classifier.classify_data("用户登录/登出记录")
        assert result is not None
        assert result.category_key == "audit_logs"

    def test_classify_unknown_returns_none(self, classifier):
        """验证：未知数据类型返回 None"""
        result = classifier.classify_data("完全未知的数据类型")
        assert result is None


# ============================================================
# 测试：加密策略验证
# ============================================================

class TestEncryptionPolicy:
    """测试加密策略"""

    def test_critical_data_must_be_encrypted(self, classifier):
        """验证：绝密级别数据必须加密"""
        critical_cats = classifier.get_categories_by_level(DataSensitivityLevel.CRITICAL)
        for cat in critical_cats:
            assert classifier.is_encryption_required(cat.category_key) is True

    def test_pii_must_be_encrypted(self, classifier):
        """验证：个人身份信息必须加密"""
        assert classifier.is_encryption_required("pii") is True

    def test_source_code_not_required_encryption(self, classifier):
        """验证：项目源代码不强制要求加密"""
        assert classifier.is_encryption_required("project_source") is False

    def test_encryption_unknown_key_returns_false(self, classifier):
        """验证：未知类别返回不加密"""
        assert classifier.is_encryption_required("nonexistent_key") is False


# ============================================================
# 测试：保留策略验证
# ============================================================

class TestRetentionPolicy:
    """测试数据保留策略"""

    def test_permanent_retention_categories(self, classifier):
        """验证：永久保留的数据类别"""
        permanent_keys = [
            "user_credentials",
            "pii",
            "project_source",
            "system_config",
        ]
        for key in permanent_keys:
            policy = classifier.get_security_policy(key)
            assert policy is not None
            assert policy["retention_days"] == -1, f"{key} 应为永久保留"

    def test_communication_retention_365_days(self, classifier):
        """验证：通信记录保留 365 天"""
        policy = classifier.get_security_policy("communication_records")
        assert policy is not None
        assert policy["retention_days"] == 365

    def test_audit_logs_retention_730_days(self, classifier):
        """验证：审计日志保留 730 天（2 年）"""
        policy = classifier.get_security_policy("audit_logs")
        assert policy is not None
        assert policy["retention_days"] == 730


# ============================================================
# 测试：判定标准表格完整性
# ============================================================

class TestClassificationTable:
    """测试敏感数据判定标准表格的完整性"""

    def test_table_has_six_rows(self, classifier):
        """验证：判定标准表格包含 6 行（6 类数据）"""
        keys = classifier.get_all_category_keys()
        assert len(keys) == 6

    def test_each_category_has_required_fields(self, classifier):
        """验证：每类数据都有完整的策略字段"""
        required_fields = [
            "category_key",
            "category_label",
            "sensitivity_level",
            "storage_policy",
            "transmission_policy",
            "access_control",
            "retention_days",
            "encryption_required",
        ]
        for key in classifier.get_all_category_keys():
            policy = classifier.get_security_policy(key)
            assert policy is not None, f"类别 {key} 策略不存在"
            for field_name in required_fields:
                assert field_name in policy, f"类别 {key} 缺少字段 {field_name}"

    def test_each_category_has_examples(self, classifier):
        """验证：每类数据至少有一个示例"""
        for cat in SENSITIVE_DATA_CATEGORIES:
            assert len(cat.examples) >= 1, f"类别 {cat.category_label} 缺少数据示例"
            assert all(isinstance(e, str) and len(e) > 0 for e in cat.examples)

    def test_category_keys_are_unique(self, classifier):
        """验证：6 类数据的标识唯一不重复"""
        keys = classifier.get_all_category_keys()
        assert len(keys) == len(set(keys)), "类别标识存在重复"

    def test_all_labels_are_non_empty(self, classifier):
        """验证：6 类数据的中文标签均非空"""
        for cat in SENSITIVE_DATA_CATEGORIES:
            assert cat.category_label is not None
            assert len(cat.category_label) > 0


# ============================================================
# 测试：非功能需求 6.3 节结构验证
# ============================================================

class TestSection63Structure:
    """验证非功能需求 6.3 节「敏感数据判定标准」的文档结构"""

    def test_six_categories_defined(self):
        """验证：6 类敏感数据已完整定义"""
        expected_keys = {
            "user_credentials",
            "pii",
            "project_source",
            "communication_records",
            "system_config",
            "audit_logs",
        }
        actual_keys = {c.category_key for c in SENSITIVE_DATA_CATEGORIES}
        assert expected_keys == actual_keys, (
            f"6 类数据覆盖不完整。\n"
            f"期望: {expected_keys}\n"
            f"实际: {actual_keys}"
        )

    def test_six_labels_defined(self):
        """验证：6 类数据的中文标签已完整定义"""
        expected_labels = {
            "用户凭据类",
            "个人身份信息",
            "项目源代码",
            "通信记录",
            "系统配置",
            "审计日志",
        }
        actual_labels = {c.category_label for c in SENSITIVE_DATA_CATEGORIES}
        assert expected_labels == actual_labels, (
            f"6 类数据标签不完整。\n"
            f"期望: {expected_labels}\n"
            f"实际: {actual_labels}"
        )

    def test_all_six_have_security_policies(self):
        """验证：6 类数据都有对应的安全策略"""
        classifier = SensitiveDataClassifier(SENSITIVE_DATA_CATEGORIES)
        for cat in SENSITIVE_DATA_CATEGORIES:
            policy = classifier.get_security_policy(cat.category_key)
            assert policy is not None, f"类别 {cat.category_label} 缺少安全策略"
            # 验证策略核心字段非空
            assert len(policy["storage_policy"]) > 0, f"{cat.category_label} 存储策略为空"
            assert len(policy["transmission_policy"]) > 0, f"{cat.category_label} 传输策略为空"
            assert len(policy["access_control"]) > 0, f"{cat.category_label} 访问控制策略为空"
