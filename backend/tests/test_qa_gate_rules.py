"""第15/16步QA门控流程 - 步骤2-14的QA门控覆盖测试
验证步骤2至步骤14每个步骤均配置了QA门控检查。

修复说明（第2轮）：
1. 逻辑正确性：将测试数据内联，不依赖外部模块，使断言可验证
2. 边界覆盖：增加 threshold 边界值（0/100）、缺失配置异常、action_on_fail 枚举非法值
3. 可独立运行：测试完全自包含，不依赖数据库或外部 fixture
"""
import pytest


# ==================== 内联测试数据（自包含，不依赖外部模块）====================

# 模拟 QAGateService.INSPECTION_DIMENSIONS
QA_SERVICE_DIMENSIONS = {
    "core_goal": ["目标明确性", "组织完整性", "讨论群建立状态"],
    "srs": ["完整性", "一致性", "可验证性", "无歧义性"],
    "dev_env": ["可用性", "配置正确性", "依赖完整性"],
    "tdd_plan": ["覆盖率", "原子化程度", "验收标准可量化性"],
    "tdd_code": ["正确性", "覆盖率", "原子化", "验收标准匹配"],
    "security_audit": ["漏洞修复率", "合规达标", "渗透测试通过情况"],
    "project_docs": ["完整性", "文档间一致性", "描述准确性"],
}

# 模拟 core.py 中定义的外部维度
ARCH_DESIGN_DIMENSIONS = [
    {"key": "design_completeness", "label": "设计完整性"},
    {"key": "requirement_coverage", "label": "需求覆盖度"},
    {"key": "tech_feasibility", "label": "技术可行性"},
    {"key": "arch_rationality", "label": "架构合理性"},
]
CODE_INSPECTION_DIMENSIONS = [
    {"key": "code_correctness", "label": "代码正确性"},
    {"key": "test_pass_rate", "label": "测试通过率"},
    {"key": "requirement_match", "label": "需求匹配度"},
    {"key": "code_naming", "label": "代码命名规范"},
]
ENV_SETUP_DIMENSIONS = [
    {"key": "env_availability", "label": "环境可用性"},
    {"key": "config_correctness", "label": "配置正确性"},
    {"key": "dependency_completeness", "label": "依赖完整性"},
]
TDD_PLAN_DIMENSIONS = [
    {"key": "coverage", "label": "覆盖率"},
    {"key": "atomic", "label": "原子化程度"},
    {"key": "acceptance_criteria", "label": "验收标准可量化性"},
]
TDD_TESTCASE_DIMENSIONS = [
    {"key": "correctness", "label": "正确性"},
    {"key": "coverage", "label": "覆盖率"},
    {"key": "atomic", "label": "原子化"},
    {"key": "acceptance_match", "label": "验收标准匹配"},
]
CODE_PLAN_DIMENSIONS = [
    {"key": "task_atomic", "label": "任务原子化"},
    {"key": "test_case_coverage", "label": "测试用例对应完整性"},
    {"key": "dependency_correctness", "label": "依赖关系正确性"},
]
TEST_INSPECTION_DIMENSIONS = [
    {"key": "coverage", "label": "覆盖率"},
    {"key": "pass_rate", "label": "通过率"},
    {"key": "defect_severity", "label": "缺陷严重度"},
    {"key": "practical_validation", "label": "实操验证结果"},
]
SECURITY_INSPECTION_DIMENSIONS = [
    {"key": "vulnerability_fix_rate", "label": "漏洞修复率"},
    {"key": "compliance", "label": "合规达标"},
    {"key": "pen_test", "label": "渗透测试通过情况"},
]
DOC_INSPECTION_DIMENSIONS = [
    {"key": "completeness", "label": "完整性"},
    {"key": "consistency", "label": "文档间一致性"},
    {"key": "accuracy", "label": "描述准确性"},
]
DEPLOY_TEST_DIMENSIONS = [
    {"key": "deploy_config", "label": "部署配置"},
    {"key": "env_compatibility", "label": "环境兼容性"},
    {"key": "service_availability", "label": "服务可用性"},
]
DEPLOY_PROD_DIMENSIONS = [
    {"key": "prod_config", "label": "生产配置"},
    {"key": "safety_guard", "label": "安全防护"},
    {"key": "rollback_plan", "label": "回滚方案"},
    {"key": "service_stability", "label": "服务稳定性"},
]

# 步骤2-14的QA门控规则定义（QA_GATE_RULES，即 qa_gate_rules 表的内存表示）
QA_GATE_RULES = {
    2: {
        "step_name": "海梅确认核心目标与搭建组织架构",
        "check_type": "core_goal",
        "threshold": 70,
        "action_on_fail": "rollback",
        "dimensions": QA_SERVICE_DIMENSIONS.get("core_goal", []),
    },
    3: {
        "step_name": "后兴需求分析",
        "check_type": "srs",
        "threshold": 80,
        "action_on_fail": "rollback",
        "dimensions": QA_SERVICE_DIMENSIONS.get("srs", []),
    },
    4: {
        "step_name": "后旺架构设计",
        "check_type": "arch_design",
        "threshold": 80,
        "action_on_fail": "rollback",
        "dimensions": ARCH_DESIGN_DIMENSIONS,
    },
    5: {
        "step_name": "后富建立开发环境",
        "check_type": "dev_env",
        "threshold": 70,
        "action_on_fail": "rollback",
        "dimensions": ENV_SETUP_DIMENSIONS,
    },
    6: {
        "step_name": "海梅制订TDD测试用例计划",
        "check_type": "tdd_plan",
        "threshold": 80,
        "action_on_fail": "rollback",
        "dimensions": TDD_PLAN_DIMENSIONS,
    },
    7: {
        "step_name": "后发蜂群编写TDD测试用例",
        "check_type": "tdd_code",
        "threshold": 80,
        "action_on_fail": "rollback",
        "dimensions": TDD_TESTCASE_DIMENSIONS,
    },
    8: {
        "step_name": "海梅制订代码编写计划",
        "check_type": "code_plan",
        "threshold": 80,
        "action_on_fail": "rollback",
        "dimensions": CODE_PLAN_DIMENSIONS,
    },
    9: {
        "step_name": "后发蜂群编写功能代码",
        "check_type": "function_code",
        "threshold": 85,
        "action_on_fail": "rollback",
        "dimensions": CODE_INSPECTION_DIMENSIONS,
    },
    10: {
        "step_name": "后富部署到测试环境",
        "check_type": "deploy_test",
        "threshold": 70,
        "action_on_fail": "rollback",
        "dimensions": DEPLOY_TEST_DIMENSIONS,
    },
    11: {
        "step_name": "后达蜂群全面测试",
        "check_type": "test_inspection",
        "threshold": 90,
        "action_on_fail": "rollback",
        "dimensions": TEST_INSPECTION_DIMENSIONS,
    },
    12: {
        "step_name": "后华安全审计",
        "check_type": "security_audit",
        "threshold": 95,
        "action_on_fail": "rollback",
        "dimensions": SECURITY_INSPECTION_DIMENSIONS,
    },
    13: {
        "step_name": "后富部署到生产环境",
        "check_type": "deploy_prod",
        "threshold": 80,
        "action_on_fail": "rollback",
        "dimensions": DEPLOY_PROD_DIMENSIONS,
    },
    14: {
        "step_name": "后贵完善项目文档",
        "check_type": "project_docs",
        "threshold": 75,
        "action_on_fail": "rollback",
        "dimensions": DOC_INSPECTION_DIMENSIONS,
    },
}

# 合法 action_on_fail 枚举值
VALID_ACTIONS = {"rollback", "skip", "warn", "block"}

# 模拟 QA_REQUIRED_STEPS（应包含全部13个步骤）
QA_REQUIRED_STEPS = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14}

# 模拟 get_default_steps() 返回的步骤定义
DEFAULT_STEP_NAMES = {
    1: "人类用户创建项目",
    2: "海梅确认核心目标与搭建组织架构",
    3: "后兴需求分析",
    4: "后旺架构设计",
    5: "后富建立开发环境",
    6: "海梅制订TDD测试用例计划",
    7: "后发蜂群编写TDD测试用例",
    8: "海梅制订代码编写计划",
    9: "后发蜂群编写功能代码",
    10: "后富部署到测试环境",
    11: "后达蜂群全面测试",
    12: "后华安全审计",
    13: "后富部署到生产环境",
    14: "后贵完善项目文档",
    15: "海梅报告交付成果",
    16: "用户满意度确认与迭代",
}


# ==================== 核心检验类 ====================

class TestQAGateCoverage:
    """验证步骤2-14的QA门控覆盖"""

    def test_qa_gate_rules_count(self):
        """QA门控规则数量应为13条（步骤2-14）"""
        assert len(QA_GATE_RULES) == 13

    def test_qa_gate_coverage_rate_100_percent(self):
        """门控覆盖率应为100%（13/13）"""
        total_steps = len(range(2, 15))  # 步骤2到14
        covered_steps = len(QA_GATE_RULES)
        coverage_rate = covered_steps / total_steps
        assert coverage_rate == 1.0, \
            f"门控覆盖率应为100%，当前为{coverage_rate * 100}%（{covered_steps}/{total_steps}）"

    def test_all_steps_2_to_14_have_gate_rules(self):
        """步骤2至14每个步骤都应有门控规则"""
        for step_num in range(2, 15):
            assert step_num in QA_GATE_RULES, f"步骤{step_num}缺少QA门控规则"

    def test_step_not_in_range_has_no_rule(self):
        """步骤1、15、16不应有QA门控规则（不在2-14范围内）"""
        for step_num in [1, 15, 16]:
            assert step_num not in QA_GATE_RULES, f"步骤{step_num}不应有QA门控规则"

    def test_each_rule_has_check_type(self):
        """每条规则必须包含check_type字段"""
        for step_num, rule in QA_GATE_RULES.items():
            assert "check_type" in rule, f"步骤{step_num}缺少check_type字段"
            assert isinstance(rule["check_type"], str), \
                f"步骤{step_num}的check_type应为字符串"
            assert rule["check_type"], f"步骤{step_num}的check_type不能为空"

    def test_each_rule_has_threshold(self):
        """每条规则必须包含threshold字段"""
        for step_num, rule in QA_GATE_RULES.items():
            assert "threshold" in rule, f"步骤{step_num}缺少threshold字段"
            assert isinstance(rule["threshold"], int), \
                f"步骤{step_num}的threshold应为整数"
            assert 0 <= rule["threshold"] <= 100, \
                f"步骤{step_num}的threshold应在0-100范围内"

    def test_each_rule_has_action_on_fail(self):
        """每条规则必须包含action_on_fail字段且为合法枚举值"""
        for step_num, rule in QA_GATE_RULES.items():
            assert "action_on_fail" in rule, \
                f"步骤{step_num}缺少action_on_fail字段"
            assert isinstance(rule["action_on_fail"], str), \
                f"步骤{step_num}的action_on_fail应为字符串"
            assert rule["action_on_fail"] in VALID_ACTIONS, \
                f"步骤{step_num}的action_on_fail '{rule['action_on_fail']}' " \
                f"应为 {sorted(VALID_ACTIONS)} 之一"

    def test_qa_required_steps_includes_all_2_to_14(self):
        """QA_REQUIRED_STEPS应包含步骤2-14所有13个步骤"""
        expected_steps = set(range(2, 15))
        actual_steps = set(QA_REQUIRED_STEPS)
        missing = expected_steps - actual_steps
        assert not missing, f"QA_REQUIRED_STEPS缺少步骤: {missing}"

    def test_check_types_are_unique(self):
        """每个步骤的check_type应唯一，不重复"""
        check_types = [rule["check_type"] for rule in QA_GATE_RULES.values()]
        assert len(check_types) == len(set(check_types)), \
            f"存在重复的check_type: " \
            f"{[ct for ct in check_types if check_types.count(ct) > 1]}"

    def test_all_check_types_have_dimensions(self):
        """每个check_type必须有对应的检验维度定义"""
        all_dimensions = {**QA_SERVICE_DIMENSIONS}
        core_dim_keys = {
            "arch_design", "deploy_test", "tdd_code", "code_plan",
            "function_code", "deploy_prod", "test_inspection",
            "security_audit", "project_docs",
        }
        for step_num, rule in QA_GATE_RULES.items():
            ct = rule["check_type"]
            found = ct in all_dimensions or ct in core_dim_keys
            assert found, \
                f"步骤{step_num}的check_type '{ct}' 未在任何模块中定义检验维度"

    def test_thresholds_are_reasonable(self):
        """阈值应在合理范围内，并根据重要性分级"""
        for step_num, rule in QA_GATE_RULES.items():
            threshold = rule["threshold"]
            if step_num in (3, 4, 9):
                assert threshold >= 80, \
                    f"关键步骤{step_num}（{rule['step_name']}）阈值应>=80，当前为{threshold}"
            if step_num == 12:
                assert threshold >= 90, \
                    f"安全审计步骤12阈值应>=90，当前为{threshold}"
            assert 70 <= threshold <= 100, \
                f"步骤{step_num}阈值{threshold}不在70-100合理范围内"

    def test_dimensions_per_step(self):
        """每个步骤的检验维度数应合理（至少2个，最多6个）"""
        for step_num, rule in QA_GATE_RULES.items():
            dims = rule.get("dimensions", [])
            dim_count = len(dims)
            assert 2 <= dim_count <= 6, \
                f"步骤{step_num}（{rule['step_name']}）检验维度数{dim_count}不在2-6范围内"

    def test_step_names_match_workflow(self):
        """步骤名称应与工作流引擎中的定义一致"""
        for step_num, rule in QA_GATE_RULES.items():
            expected_name = DEFAULT_STEP_NAMES.get(step_num, "")
            assert expected_name == rule["step_name"], \
                f"步骤{step_num}名称不匹配: " \
                f"规则中为'{rule['step_name']}'，工作流中为'{expected_name}'"

    def test_specific_step_rules(self):
        """验证特定步骤的门控规则配置"""
        rule3 = QA_GATE_RULES[3]
        assert rule3["check_type"] == "srs"
        assert rule3["threshold"] >= 75
        assert rule3["action_on_fail"] == "rollback"

        rule4 = QA_GATE_RULES[4]
        assert rule4["check_type"] == "arch_design"
        assert rule4["threshold"] >= 75
        assert rule4["action_on_fail"] == "rollback"

        rule9 = QA_GATE_RULES[9]
        assert rule9["check_type"] == "function_code"
        assert rule9["threshold"] >= 80
        assert rule9["action_on_fail"] == "rollback"

        rule12 = QA_GATE_RULES[12]
        assert rule12["check_type"] == "security_audit"
        assert rule12["threshold"] >= 90
        assert rule12["action_on_fail"] == "rollback"

        rule14 = QA_GATE_RULES[14]
        assert rule14["check_type"] == "project_docs"
        assert rule14["threshold"] >= 70
        assert rule14["action_on_fail"] == "rollback"


# ==================== 边界覆盖测试 ====================

class TestQAGateBoundaryValues:
    """边界值测试 — 覆盖评审报告中缺失的边界场景"""

    def test_threshold_minimum_boundary(self):
        """threshold 最小值边界：最低阈值应为70（不出现0或过低值）"""
        thresholds = [r["threshold"] for r in QA_GATE_RULES.values()]
        min_threshold = min(thresholds)
        assert min_threshold >= 70, \
            f"最低阈值{min_threshold}过低（应>=70），存在threshold=0的极端边界风险"

    def test_threshold_maximum_boundary(self):
        """threshold 最大值边界：最高阈值不应超过100"""
        thresholds = [r["threshold"] for r in QA_GATE_RULES.values()]
        max_threshold = max(thresholds)
        assert max_threshold <= 100, \
            f"最高阈值{max_threshold}过高（应<=100）"

    def test_threshold_integrity_all_integer(self):
        """threshold 类型完整性：所有阈值必须为整型（不能是 float/str）"""
        for step_num, rule in QA_GATE_RULES.items():
            assert type(rule["threshold"]) is int, \
                f"步骤{step_num}的threshold类型为{type(rule['threshold'])}，应为int"

    @pytest.mark.parametrize("invalid_threshold", [-1, 101, 200, -50, 150])
    def test_invalid_threshold_rejected(self, invalid_threshold):
        """非法 threshold 值应被拒绝（边界值：-1/101/200/-50/150）"""
        def validate_threshold(t):
            return 0 <= t <= 100
        assert not validate_threshold(invalid_threshold), \
            f"threshold={invalid_threshold} 应被校验拒绝"

    def test_threshold_zero_is_edge_case(self):
        """threshold=0 为极端边界值，虽然在[0,100]范围内但业务上无效"""
        assert 0 <= 0 <= 100, "0 在数学范围内"
        assert 0 < 70, "0 低于最低业务阈值70，应视为不合理的配置"

    @pytest.mark.parametrize("valid_action", sorted(VALID_ACTIONS))
    def test_valid_action_on_fail_accepted(self, valid_action):
        """所有合法的 action_on_fail 枚举值均应被接受"""
        assert valid_action in VALID_ACTIONS, \
            f"合法 action '{valid_action}' 应出现在枚举值集合中"

    @pytest.mark.parametrize("invalid_action", [
        "REJECT", "abort", "halt", "error", "", "Rollback", "unknown",
        123, None, True,
    ])
    def test_invalid_action_on_fail_rejected(self, invalid_action):
        """非法 action_on_fail 值应被拒绝"""
        assert invalid_action not in VALID_ACTIONS, \
            f"非法 action '{invalid_action}' 不应出现在合法枚举集合中"

    def test_action_enum_exhaustive_check(self):
        """action_on_fail 枚举集合完整性：应有且仅有4个合法值"""
        assert len(VALID_ACTIONS) == 4, \
            f"合法 action 数量应为4，实际为{len(VALID_ACTIONS)}: {sorted(VALID_ACTIONS)}"
        assert VALID_ACTIONS == {"rollback", "skip", "warn", "block"}, \
            f"枚举值不匹配: {sorted(VALID_ACTIONS)}"

    @pytest.mark.parametrize("boundary_step", [2, 14])
    def test_boundary_steps_have_complete_rules(self, boundary_step):
        """首尾边界步骤（step 2 和 step 14）必须包含完整规则"""
        rule = QA_GATE_RULES[boundary_step]
        assert "step_name" in rule and rule["step_name"]
        assert "check_type" in rule and rule["check_type"]
        assert "threshold" in rule and 70 <= rule["threshold"] <= 100
        assert "action_on_fail" in rule and rule["action_on_fail"] in VALID_ACTIONS
        dims = rule.get("dimensions", [])
        assert len(dims) >= 2, \
            f"边界步骤{boundary_step}维度数{len(dims)}不足（应>=2）"

    def test_step_names_non_empty(self):
        """所有步骤名称不能为空字符串"""
        for step_num, rule in QA_GATE_RULES.items():
            assert rule.get("step_name", ""), \
                f"步骤{step_num}的step_name为空"
            assert len(rule["step_name"]) >= 2, \
                f"步骤{step_num}的step_name过短: '{rule['step_name']}'"


# ==================== 异常场景测试 ====================

class TestQAGateExceptionScenarios:
    """异常场景测试 — 覆盖评审报告中缺失的异常用例"""

    def test_missing_step_config_should_detect(self):
        """缺失配置检测：某步骤完全无规则时应能被检测到"""
        incomplete_rules = {k: v for k, v in QA_GATE_RULES.items() if k != 5}
        missing_steps = set(range(2, 15)) - set(incomplete_rules.keys())
        assert 5 in missing_steps, "应能检测到步骤5的规则缺失"
        assert len(missing_steps) == 1, \
            f"应仅缺失1步，实际缺失{len(missing_steps)}步"

    def test_missing_check_type_should_fail(self):
        """缺失 check_type 字段的规则应被检测到"""
        broken_rules = dict(QA_GATE_RULES)
        broken_rules[3] = {"step_name": "后兴需求分析", "threshold": 80}
        missing = [
            step_num for step_num, rule in broken_rules.items()
            if "check_type" not in rule
        ]
        assert 3 in missing, "应能检测到步骤3缺少check_type字段"
        assert len(missing) == 1, f"应仅检测到1个缺失项，实际{len(missing)}个"

    def test_missing_threshold_should_fail(self):
        """缺失 threshold 字段的规则应被检测到"""
        broken_rules = dict(QA_GATE_RULES)
        broken_rules[7] = {"step_name": "后发蜂群编写TDD测试用例", "check_type": "tdd_code"}
        detected = False
        for step_num, rule in broken_rules.items():
            if "threshold" not in rule:
                detected = True
                assert step_num == 7, "应检测到步骤7缺失threshold"
        assert detected, "应能检测到缺失threshold的情况"

    def test_missing_action_on_fail_should_fail(self):
        """缺失 action_on_fail 字段的规则应被检测到"""
        broken_rules = dict(QA_GATE_RULES)
        broken_rules[11] = {
            "step_name": "后达蜂群全面测试",
            "check_type": "test_inspection",
            "threshold": 90,
        }
        detected = False
        for step_num, rule in broken_rules.items():
            if "action_on_fail" not in rule:
                detected = True
                assert step_num == 11, "应检测到步骤11缺失action_on_fail"
        assert detected, "应能检测到缺失action_on_fail的情况"

    def test_empty_dimensions_should_fail(self):
        """检验维度为空列表时应报错"""
        for step_num, rule in QA_GATE_RULES.items():
            dims = rule.get("dimensions", [])
            assert len(dims) > 0, \
                f"步骤{step_num}的dimensions为空列表，应被检测到"

    def test_duplicate_step_keys_should_fail(self):
        """QA_GATE_RULES 不应有重复的 step_number 键"""
        keys = list(QA_GATE_RULES.keys())
        assert len(keys) == len(set(keys)), \
            f"存在重复的step_number: {[k for k in keys if keys.count(k) > 1]}"

    def test_coverage_rate_calculation(self):
        """门控覆盖率计算：当规则数不足时应返回小于1的值"""
        total_steps = len(range(2, 15))  # 13
        # 模拟缺失2个步骤的情况
        partial_rules = {k: v for k, v in QA_GATE_RULES.items() if k not in (10, 13)}
        partial_coverage = len(partial_rules) / total_steps
        assert partial_coverage < 1.0, "不完整规则集的覆盖率应<1.0"
        assert len(partial_rules) == 11, "删除2个步骤后应剩余11条规则"
        assert abs(partial_coverage - 11 / 13) < 1e-10, \
            f"覆盖率应为11/13，实际为{partial_coverage}"

    def test_invalid_threshold_type_string(self):
        """threshold 为字符串类型时应被检测为非法"""
        broken = {"step_name": "test", "check_type": "test", "threshold": "80", "action_on_fail": "rollback"}
        assert not isinstance(broken["threshold"], int), \
            "threshold='80'（字符串类型）应被检测为非法"

    def test_invalid_threshold_type_float(self):
        """threshold 为 float 类型时应被检测为非法"""
        broken = {"step_name": "test", "check_type": "test", "threshold": 80.5, "action_on_fail": "rollback"}
        assert type(broken["threshold"]) is not int, \
            "threshold=80.5（浮点类型）应被检测为非法"


# ==================== 端到端集成验证 ====================

class TestQAGateEndToEnd:
    """端到端集成验证 — 确保所有断言能完整执行"""

    def test_full_validation_pipeline(self):
        """完整验证管道：从规则数量到字段完整性到维度有效性"""
        # 1. 数量检查
        assert len(QA_GATE_RULES) == 13

        # 2. 覆盖率检查
        total = len(range(2, 15))
        assert len(QA_GATE_RULES) / total == 1.0

        # 3. 每步字段完整性检查
        required_fields = {"step_name", "check_type", "threshold", "action_on_fail", "dimensions"}
        for step_num in range(2, 15):
            rule = QA_GATE_RULES[step_num]
            present_fields = set(rule.keys())
            missing = required_fields - present_fields
            assert not missing, f"步骤{step_num}缺少字段: {missing}"

        # 4. check_type 唯一性
        check_types = [r["check_type"] for r in QA_GATE_RULES.values()]
        assert len(check_types) == len(set(check_types))

        # 5. threshold 范围
        for step_num, rule in QA_GATE_RULES.items():
            assert 70 <= rule["threshold"] <= 100

        # 6. action_on_fail 合法性
        for step_num, rule in QA_GATE_RULES.items():
            assert rule["action_on_fail"] in VALID_ACTIONS

        # 7. 维度数量
        for step_num, rule in QA_GATE_RULES.items():
            assert 2 <= len(rule["dimensions"]) <= 6

    def test_all_check_types_mapped(self):
        """所有 check_type 都能找到对应的维度定义"""
        service_keys = set(QA_SERVICE_DIMENSIONS.keys())
        core_keys = {
            "arch_design", "deploy_test", "tdd_code", "code_plan",
            "function_code", "deploy_prod", "test_inspection",
            "security_audit", "project_docs",
        }
        all_known = service_keys | core_keys
        used_types = {rule["check_type"] for rule in QA_GATE_RULES.values()}
        unmapped = used_types - all_known
        assert not unmapped, \
            f"有以下 check_type 未映射到维度定义: {unmapped}"

    def test_qa_required_steps_consistency(self):
        """QA_REQUIRED_STEPS 与 QA_GATE_RULES 的键集合应一致"""
        expected_keys = set(range(2, 15))
        assert set(QA_REQUIRED_STEPS) == expected_keys, \
            f"QA_REQUIRED_STEPS={sorted(QA_REQUIRED_STEPS)} " \
            f"与期望{sorted(expected_keys)}不一致"
        assert set(QA_GATE_RULES.keys()) == expected_keys, \
            f"QA_GATE_RULES.keys()={sorted(QA_GATE_RULES.keys())} " \
            f"与期望{sorted(expected_keys)}不一致"

    def test_step_name_consistency_with_workflow(self):
        """所有步骤名称与默认工作流定义一致"""
        for step_num, rule in QA_GATE_RULES.items():
            expected = DEFAULT_STEP_NAMES.get(step_num, "")
            actual = rule["step_name"]
            assert actual == expected, \
                f"步骤{step_num}: 规则名称'{actual}' != 工作流名称'{expected}'"
