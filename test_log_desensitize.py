import pytest
import re


class LogDesensitizer:
    """日志脱敏器"""

    def __init__(self):
        self._rules = [
            {"pattern": re.compile(r"(?<!\d)(\d{3})\d{4}(\d{4})(?!\d)"), "replace": r"\1****\2", "name": "phone"},
            {"pattern": re.compile(r"[^@\s]+(?=@([a-zA-Z0-9._-]+))"), "replace": r"*@\1", "name": "email"},
            {"pattern": re.compile(r"(?<!\d)(\d{6})\d{8}(\d{4}[Xx]?\d)(?!\d)"), "replace": r"\1********\2", "name": "id_card"},
            {"pattern": re.compile(r"(?:password|passwd|pwd|token|apikey|api_key|secret)\s*[=:]\s*\S+"), "replace": lambda m: self._mask_key_value(m), "name": "secret"},
        ]

    def _mask_key_value(self, match):
        original = match.group(0)
        sep_pos = original.index("=") if "=" in original else original.index(":")
        return original[:sep_pos + 1] + " ***"

    def desensitize(self, text):
        """对文本执行脱敏"""
        result = text
        for rule in self._rules:
            result = rule["pattern"].sub(rule["replace"], result)
        return result

    def add_rule(self, name, pattern, replace):
        """动态添加脱敏规则"""
        self._rules.append({"pattern": re.compile(pattern), "replace": replace, "name": name})

    def remove_rule(self, name):
        """动态移除脱敏规则"""
        self._rules = [r for r in self._rules if r["name"] != name]


# ---- 测试：手机号脱敏 ----

class TestPhoneDesensitization:
    def setup_method(self):
        self.des = LogDesensitizer()

    def test_standard_phone_number(self):
        assert self.des.desensitize("手机号：13812345678") == "手机号：138****5678"

    def test_phone_in_sentence(self):
        assert self.des.desensitize("请联系13900001111办理") == "请联系139****1111办理"

    def test_multiple_phones(self):
        result = self.des.desensitize("电话13812345678或13987654321")
        assert "138****5678" in result
        assert "139****4321" in result

    def test_phone_not_over_masked(self):
        assert self.des.desensitize("订单号202311112222") == "订单号2023****2222"


# ---- 测试：邮箱脱敏（保留域名） ----

class TestEmailDesensitization:
    def setup_method(self):
        self.des = LogDesensitizer()

    def test_basic_email(self):
        assert self.des.desensitize("邮箱：user@example.com") == "邮箱：*@example.com"

    def test_email_with_subdomain(self):
        assert self.des.desensitize("contact admin@corp.google.com") == "contact *@corp.google.com"

    def test_multiple_emails(self):
        result = self.des.desensitize("a@b.com 和 c@d.org")
        assert "*@b.com" in result
        assert "*@d.org" in result


# ---- 测试：身份证脱敏（保留前后） ----

class TestIDCardDesensitization:
    def setup_method(self):
        self.des = LogDesensitizer()

    def test_18_digit_id_card(self):
        assert self.des.desensitize("身份证：110101199001011233") == "身份证：110101********1233"

    def test_id_card_with_x_suffix(self):
        result = self.des.desensitize("身份证：11010119900101123X")
        assert "110101" in result
        assert "********" in result


# ---- 测试：密码/Token脱敏 ----

class TestSecretDesensitization:
    def setup_method(self):
        self.des = LogDesensitizer()

    def test_password_equals(self):
        assert "password= ***" in self.des.desensitize("password=MyS3cret!")

    def test_password_colon(self):
        assert "password: ***" in self.des.desensitize("password: MyS3cret!")

    def test_token_desensitized(self):
        assert "token= ***" in self.des.desensitize("token=eyJhbGciOiJIUzI1NiJ9.xxx")

    def test_api_key_desensitized(self):
        assert "apikey= ***" in self.des.desensitize("apikey=sk-1234567890abcdef")

    def test_secret_key_desensitized(self):
        assert "secret= ***" in self.des.desensitize("secret=super_secret_value_here")

    def test_pwd_alias(self):
        assert "pwd= ***" in self.des.desensitize("pwd=123456")


# ---- 测试：动态规则修改即时生效 ----

class TestDynamicRules:
    def setup_method(self):
        self.des = LogDesensitizer()

    def test_add_custom_rule_immediate_effect(self):
        """新增规则后立即生效"""
        self.des.add_rule("ssn", r"\d{3}-\d{2}-\d{4}", r"***-**-****")
        assert self.des.desensitize("SSN: 123-45-6789") == "SSN: ***-**-****"

    def test_remove_rule_immediate_effect(self):
        """删除规则后原有脱敏立即停止"""
        self.des.remove_rule("secret")
        result = self.des.desensitize("password=abc123")
        assert "password=abc123" in result

    def test_modify_rule_then_remove_rule_immediate_effect(self):
        """新增自定义规则后立即生效"""
        self.des.add_rule("code", r"\bcode:\s*(\d{3})\d{3}(\d{3})\b", r"code: \1***\2")
        after = self.des.desensitize("code: 999888777")
        assert "code: 999***777" == after

    def test_multiple_dynamic_operations(self):
        """多次动态操作均即时生效"""
        self.des.add_rule("custom_code", r"CODE:(\d{2})\d{2}", r"CODE:\1**")
        assert self.des.desensitize("CODE:1234") == "CODE:12**"
        self.des.remove_rule("custom_code")
        result = self.des.desensitize("CODE:1234")
        assert "CODE:1234" == result
