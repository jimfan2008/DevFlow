"""用户错误提示组件 - TDD 测试用例

验证 8 种前端提示类型正确触发，错误文案来自 API 响应非硬编码，颜色符合规范。

对应 SRS 条款：FN-ERR-003 (用户错误提示规范)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta

import pytest


# ====================================================================
# 被测试的实现：用户错误提示服务
# ====================================================================

class PromptType(Enum):
    """8 种前端提示类型"""
    FORM_VALIDATION = "form_validation"      # FN-ERR-003a 表单校验提示
    SUCCESS_TOAST = "success_toast"           # FN-ERR-003b 操作成功提示
    ERROR_TOAST = "error_toast"              # FN-ERR-003c 操作失败提示
    CONFIRM_DIALOG = "confirm_dialog"         # FN-ERR-003d 确认对话框
    LOADING_INDICATOR = "loading_indicator"   # FN-ERR-003e 加载状态提示
    NETWORK_ERROR = "network_error"           # FN-ERR-003f 网络异常提示
    SESSION_EXPIRED = "session_expired"       # FN-ERR-003g 会话过期提示
    BATCH_RESULT = "batch_result"             # FN-ERR-003h 批量操作结果


# 设计规范颜色映射
_PROMPT_COLOR_MAP: Dict[Enum, str] = {
    PromptType.FORM_VALIDATION: "#F56C6C",   # 红色
    PromptType.SUCCESS_TOAST: "#67C23A",     # 绿色
    PromptType.ERROR_TOAST: "#F56C6C",       # 红色
    PromptType.CONFIRM_DIALOG: "#E6A23C",    # 黄色/橙色
    PromptType.LOADING_INDICATOR: "#409EFF", # 蓝色
    PromptType.NETWORK_ERROR: "#E6A23C",     # 黄色/橙色
    PromptType.SESSION_EXPIRED: "#F56C6C",   # 红色
    PromptType.BATCH_RESULT: "#409EFF",      # 蓝色
}


@dataclass
class PromptRecord:
    """单条提示记录"""
    prompt_type: PromptType
    message: str
    color: str
    auto_dismissible: bool
    timestamp: datetime = field(default_factory=datetime.now)
    dismissed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApiErrorResponse:
    """模拟 API 错误响应"""
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    status: int = 400


@dataclass
class FormFieldValidationResult:
    """表单字段校验结果"""
    field_name: str
    is_valid: bool
    error_message: str = ""


@dataclass
class BatchOperationResult:
    """批量操作结果"""
    total: int
    success_count: int
    fail_count: int
    fail_details: List[Dict[str, Any]] = field(default_factory=list)


class UserPromptService:
    """
    用户错误提示服务

    对应 SRS FN-ERR-003 用户错误提示规范。
    管理 8 种提示类型的触发、展示、颜色和自动消失逻辑。
    """

    TOAST_AUTO_DISMISS_SECONDS = 3  # 成功 Toast 3 秒自动消失
    MAX_STACK_SIZE = 5  # Toast 最大堆叠数

    def __init__(self):
        self._prompt_stack: List[PromptRecord] = []
        self._active_loading: Optional[PromptRecord] = None
        self._confirm_dialog: Optional[PromptRecord] = None
        self._session_expired_dialog: Optional[PromptRecord] = None
        self._batch_result_panel: Optional[PromptRecord] = None
        self._network_banner: Optional[PromptRecord] = None

    # ---------------------------------------------------------------
    # 公共接口：触发 8 种提示
    # ---------------------------------------------------------------

    def show_form_validation(self, field_name: str, error_message: str) -> PromptRecord:
        """
        FN-ERR-003a 表单校验提示

        字段下方内联红色文字，不自动消失，需用户修正。
        错误文案来自 API 响应，禁止硬编码。
        """
        record = PromptRecord(
            prompt_type=PromptType.FORM_VALIDATION,
            message=error_message,
            color=_PROMPT_COLOR_MAP[PromptType.FORM_VALIDATION],
            auto_dismissible=False,
            metadata={"field_name": field_name},
        )
        self._prompt_stack.append(record)
        return record

    def show_success_toast(self, message: str) -> PromptRecord:
        """
        FN-ERR-003b 操作成功提示

        顶部绿色 Toast 条，3 秒后自动消失。
        支持堆叠展示。
        """
        self._enforce_stack_limit()
        record = PromptRecord(
            prompt_type=PromptType.SUCCESS_TOAST,
            message=message,
            color=_PROMPT_COLOR_MAP[PromptType.SUCCESS_TOAST],
            auto_dismissible=True,
        )
        self._prompt_stack.append(record)
        return record

    def show_error_toast(self, api_error: ApiErrorResponse) -> PromptRecord:
        """
        FN-ERR-003c 操作失败提示

        顶部红色 Toast 条 + 错误描述，不自动消失，需用户关闭。
        错误文案必须来自 API 响应。
        """
        self._enforce_stack_limit()
        record = PromptRecord(
            prompt_type=PromptType.ERROR_TOAST,
            message=api_error.message,
            color=_PROMPT_COLOR_MAP[PromptType.ERROR_TOAST],
            auto_dismissible=False,
            metadata={"error_code": api_error.code, "status": api_error.status},
        )
        self._prompt_stack.append(record)
        return record

    def show_confirm_dialog(self, title: str, message: str) -> PromptRecord:
        """
        FN-ERR-003d 确认对话框

        模态弹窗（含取消与确认按钮），不自动消失，需用户操作。
        """
        self._confirm_dialog = PromptRecord(
            prompt_type=PromptType.CONFIRM_DIALOG,
            message=message,
            color=_PROMPT_COLOR_MAP[PromptType.CONFIRM_DIALOG],
            auto_dismissible=False,
            metadata={"title": title, "has_cancel": True, "has_confirm": True},
        )
        return self._confirm_dialog

    def show_loading(self, message: str) -> PromptRecord:
        """
        FN-ERR-003e 加载状态提示

        内联加载动画（Skeleton 或 Spinner），请求完成后消失。
        """
        self._active_loading = PromptRecord(
            prompt_type=PromptType.LOADING_INDICATOR,
            message=message,
            color=_PROMPT_COLOR_MAP[PromptType.LOADING_INDICATOR],
            auto_dismissible=True,
        )
        return self._active_loading

    def hide_loading(self) -> None:
        """隐藏加载状态"""
        if self._active_loading:
            self._active_loading.dismissed = True
            self._active_loading = None

    def show_network_error(self, message: str) -> PromptRecord:
        """
        FN-ERR-003f 网络异常提示

        页面顶部全局横幅（黄色背景），不自动消失，网络恢复后自动消失。
        """
        self._network_banner = PromptRecord(
            prompt_type=PromptType.NETWORK_ERROR,
            message=message,
            color=_PROMPT_COLOR_MAP[PromptType.NETWORK_ERROR],
            auto_dismissible=False,
        )
        return self._network_banner

    def hide_network_error(self) -> None:
        """隐藏网络异常提示（网络恢复后）"""
        if self._network_banner:
            self._network_banner.dismissed = True
            self._network_banner = None

    def show_session_expired(self, redirect_url: str = "/login") -> PromptRecord:
        """
        FN-ERR-003g 会话过期提示

        模态提示 + 自动跳转登录页，不自动消失，需用户重新登录。
        """
        self._session_expired_dialog = PromptRecord(
            prompt_type=PromptType.SESSION_EXPIRED,
            message="登录已过期，请重新登录",
            color=_PROMPT_COLOR_MAP[PromptType.SESSION_EXPIRED],
            auto_dismissible=False,
            metadata={"redirect_url": redirect_url, "auto_redirect": True},
        )
        return self._session_expired_dialog

    def show_batch_result(self, result: BatchOperationResult) -> PromptRecord:
        """
        FN-ERR-003h 批量操作结果

        详情面板（成功数/失败数/失败明细列表），不自动消失，需用户关闭。
        """
        fail_messages = [detail.get("message", "") for detail in result.fail_details]
        self._batch_result_panel = PromptRecord(
            prompt_type=PromptType.BATCH_RESULT,
            message=f"批量操作完成：成功 {result.success_count} 项，失败 {result.fail_count} 项",
            color=_PROMPT_COLOR_MAP[PromptType.BATCH_RESULT],
            auto_dismissible=False,
            metadata={
                "total": result.total,
                "success_count": result.success_count,
                "fail_count": result.fail_count,
                "fail_details": result.fail_details,
            },
        )
        return self._batch_result_panel

    # ---------------------------------------------------------------
    # 状态查询
    # ---------------------------------------------------------------

    def get_active_toasts(self) -> List[PromptRecord]:
        """获取未关闭的 Toast 列表"""
        return [r for r in self._prompt_stack if not r.dismissed]

    def get_active_confirm_dialog(self) -> Optional[PromptRecord]:
        return self._confirm_dialog if self._confirm_dialog and not self._confirm_dialog.dismissed else None

    def get_active_loading(self) -> Optional[PromptRecord]:
        return self._active_loading

    def get_network_banner(self) -> Optional[PromptRecord]:
        return self._network_banner if self._network_banner and not self._network_banner.dismissed else None

    def get_session_expired_dialog(self) -> Optional[PromptRecord]:
        return self._session_expired_dialog if self._session_expired_dialog and not self._session_expired_dialog.dismissed else None

    def get_batch_result_panel(self) -> Optional[PromptRecord]:
        return self._batch_result_panel if self._batch_result_panel and not self._batch_result_panel.dismissed else None

    def dismiss_toast(self, index: int) -> bool:
        """手动关闭 Toast"""
        if 0 <= index < len(self._prompt_stack):
            self._prompt_stack[index].dismissed = True
            return True
        return False

    def confirm_dialog_action(self, confirmed: bool) -> None:
        """确认对话框用户操作"""
        if self._confirm_dialog:
            self._confirm_dialog.dismissed = True
            self._confirm_dialog.metadata["confirmed"] = confirmed
            self._confirm_dialog = None

    def clear_all_dismissible(self) -> int:
        """清除所有可关闭的提示"""
        count = 0
        for r in self._prompt_stack:
            if r.auto_dismissible and not r.dismissed:
                r.dismissed = True
                count += 1
        return count

    # ---------------------------------------------------------------
    # 内部方法
    # ---------------------------------------------------------------

    def _enforce_stack_limit(self) -> None:
        """当 Toast 堆叠超过最大数时，关闭最早的可关闭 Toast"""
        while len(self.get_active_toasts()) >= self.MAX_STACK_SIZE:
            for r in self._prompt_stack:
                if not r.dismissed:
                    r.dismissed = True
                    break


# ====================================================================
# 测试用例：8 种提示类型正确触发和展示
# ====================================================================

@pytest.fixture
def prompt_service():
    """创建独立的提示服务实例"""
    return UserPromptService()


# ---------- 颜色规范测试 ----------

class TestPromptColorSpecification:
    """验证每种提示类型的颜色符合设计规范"""

    @pytest.mark.parametrize("prompt_type,expected_color", [
        (PromptType.FORM_VALIDATION, "#F56C6C"),   # 红色 - 表单校验
        (PromptType.SUCCESS_TOAST, "#67C23A"),      # 绿色 - 操作成功
        (PromptType.ERROR_TOAST, "#F56C6C"),        # 红色 - 操作失败
        (PromptType.CONFIRM_DIALOG, "#E6A23C"),     # 黄色/橙色 - 确认对话框
        (PromptType.LOADING_INDICATOR, "#409EFF"),  # 蓝色 - 加载状态
        (PromptType.NETWORK_ERROR, "#E6A23C"),      # 黄色/橙色 - 网络异常
        (PromptType.SESSION_EXPIRED, "#F56C6C"),    # 红色 - 会话过期
        (PromptType.BATCH_RESULT, "#409EFF"),       # 蓝色 - 批量操作结果
    ])
    def test_color_matches_design_spec(self, prompt_type, expected_color):
        """颜色标识符合设计规范"""
        assert _PROMPT_COLOR_MAP[prompt_type] == expected_color


# ---------- FN-ERR-003a 表单校验提示 ----------

class TestFormValidationPrompt:
    """FN-ERR-003a: 表单校验提示 — 字段下方内联红色文字，不自动消失"""

    def test_form_validation_shows_with_api_message(self, prompt_service):
        """表单校验提示使用 API 返回的错误文案，非硬编码"""
        api_error_message = "邮箱格式不正确，请使用 user@example.com 格式"
        record = prompt_service.show_form_validation("email", api_error_message)

        assert record.prompt_type == PromptType.FORM_VALIDATION
        assert record.message == api_error_message
        assert record.color == "#F56C6C"
        assert record.auto_dismissible is False
        assert record.metadata["field_name"] == "email"

    def test_form_validation_no_auto_dismiss(self, prompt_service):
        """表单校验提示不自动消失，需用户修正"""
        record = prompt_service.show_form_validation("username", "用户名不能为空")
        assert record.auto_dismissible is False
        toasts = prompt_service.get_active_toasts()
        assert len(toasts) == 1
        assert toasts[0].message == "用户名不能为空"

    def test_form_validation_multiple_fields(self, prompt_service):
        """多个字段校验错误可分别展示"""
        email_err = prompt_service.show_form_validation("email", "邮箱格式错误")
        phone_err = prompt_service.show_form_validation("phone", "手机号格式错误")

        assert email_err.message == "邮箱格式错误"
        assert phone_err.message == "手机号格式错误"
        assert email_err.metadata["field_name"] == "email"
        assert phone_err.metadata["field_name"] == "phone"


# ---------- FN-ERR-003b 操作成功提示 ----------

class TestSuccessToastPrompt:
    """FN-ERR-003b: 操作成功提示 — 顶部绿色 Toast 条，3 秒自动消失"""

    def test_success_toast_shows_with_message(self, prompt_service):
        """操作成功提示正确展示"""
        record = prompt_service.show_success_toast("项目创建成功")

        assert record.prompt_type == PromptType.SUCCESS_TOAST
        assert record.message == "项目创建成功"
        assert record.color == "#67C23A"
        assert record.auto_dismissible is True

    def test_success_toast_auto_dismissible(self, prompt_service):
        """成功提示标记为可自动关闭"""
        record = prompt_service.show_success_toast("数据已保存")
        assert record.auto_dismissible is True
        count = prompt_service.clear_all_dismissible()
        assert count == 1
        assert len(prompt_service.get_active_toasts()) == 0

    def test_success_toast_displays_in_stack(self, prompt_service):
        """成功提示出现在活跃 Toast 堆栈中"""
        prompt_service.show_success_toast("操作一成功")
        prompt_service.show_success_toast("操作二成功")

        toasts = prompt_service.get_active_toasts()
        assert len(toasts) == 2
        assert toasts[0].message == "操作一成功"
        assert toasts[1].message == "操作二成功"


# ---------- FN-ERR-003c 操作失败提示 ----------

class TestErrorToastPrompt:
    """FN-ERR-003c: 操作失败提示 — 顶部红色 Toast 条 + 错误描述，不自动消失"""

    def test_error_toast_uses_api_message(self, prompt_service):
        """操作失败提示的错误文案来自 API 响应，非前端硬编码"""
        api_error = ApiErrorResponse(
            code="PROJECT_NOT_FOUND",
            message="项目 ID 12345 不存在",
            status=404,
        )
        record = prompt_service.show_error_toast(api_error)

        assert record.prompt_type == PromptType.ERROR_TOAST
        assert record.message == "项目 ID 12345 不存在"
        assert record.color == "#F56C6C"
        assert record.auto_dismissible is False
        assert record.metadata["error_code"] == "PROJECT_NOT_FOUND"
        assert record.metadata["status"] == 404

    def test_error_toast_various_api_codes(self, prompt_service):
        """不同 API 错误码的文案都正确传递"""
        error_cases = [
            ApiErrorResponse(code="VALIDATION_ERROR", message="密码长度至少 8 位", status=400),
            ApiErrorResponse(code="DUPLICATE_EMAIL", message="该邮箱已被注册", status=409),
            ApiErrorResponse(code="INSUFFICIENT_PERMISSION", message="您无权执行此操作", status=403),
        ]
        for api_error in error_cases:
            record = prompt_service.show_error_toast(api_error)
            assert record.message == api_error.message
            assert record.metadata["error_code"] == api_error.code
            assert record.metadata["status"] == api_error.status

    def test_error_toast_requires_manual_dismiss(self, prompt_service):
        """错误提示不自动消失，需用户手动关闭"""
        api_error = ApiErrorResponse(code="INTERNAL_ERROR", message="服务器内部错误", status=500)
        prompt_service.show_error_toast(api_error)

        toasts = prompt_service.get_active_toasts()
        assert len(toasts) == 1
        assert toasts[0].auto_dismissible is False


# ---------- FN-ERR-003d 确认对话框 ----------

class TestConfirmDialogPrompt:
    """FN-ERR-003d: 确认对话框 — 模态弹窗（含取消与确认按钮），不自动消失"""

    def test_confirm_dialog_shows_with_buttons(self, prompt_service):
        """确认对话框正确展示，含取消与确认按钮"""
        record = prompt_service.show_confirm_dialog(
            title="确认删除",
            message="此操作不可撤销，确定要删除该项目吗？",
        )

        assert record.prompt_type == PromptType.CONFIRM_DIALOG
        assert record.color == "#E6A23C"
        assert record.auto_dismissible is False
        assert record.metadata["title"] == "确认删除"
        assert record.metadata["has_cancel"] is True
        assert record.metadata["has_confirm"] is True

    def test_confirm_dialog_user_confirms(self, prompt_service):
        """用户点击确认后对话框关闭并记录确认"""
        prompt_service.show_confirm_dialog("确认删除", "确定要删除吗？")
        dialog = prompt_service.get_active_confirm_dialog()
        assert dialog is not None

        prompt_service.confirm_dialog_action(confirmed=True)
        dialog = prompt_service.get_active_confirm_dialog()
        assert dialog is None

    def test_confirm_dialog_user_cancels(self, prompt_service):
        """用户点击取消后对话框关闭"""
        prompt_service.show_confirm_dialog("确认删除", "确定要删除吗？")
        assert prompt_service.get_active_confirm_dialog() is not None

        prompt_service.confirm_dialog_action(confirmed=False)
        assert prompt_service.get_active_confirm_dialog() is None


# ---------- FN-ERR-003e 加载状态提示 ----------

class TestLoadingIndicatorPrompt:
    """FN-ERR-003e: 加载状态提示 — 内联加载动画，请求完成后消失"""

    def test_loading_shows_with_message(self, prompt_service):
        """加载状态提示正确展示"""
        record = prompt_service.show_loading("正在保存数据，请稍候...")

        assert record.prompt_type == PromptType.LOADING_INDICATOR
        assert record.message == "正在保存数据，请稍候..."
        assert record.color == "#409EFF"
        assert record.auto_dismissible is True

    def test_loading_visible_while_active(self, prompt_service):
        """加载进行中时，获取加载状态返回记录"""
        prompt_service.show_loading("加载中...")
        loading = prompt_service.get_active_loading()

        assert loading is not None
        assert loading.dismissed is False
        assert loading.message == "加载中..."

    def test_loading_hidden_after_complete(self, prompt_service):
        """请求完成后加载状态消失"""
        prompt_service.show_loading("正在处理...")
        assert prompt_service.get_active_loading() is not None

        prompt_service.hide_loading()
        assert prompt_service.get_active_loading() is None


# ---------- FN-ERR-003f 网络异常提示 ----------

class TestNetworkErrorPrompt:
    """FN-ERR-003f: 网络异常提示 — 页面顶部全局横幅（黄色背景），不自动消失"""

    def test_network_error_shows_banner(self, prompt_service):
        """网络异常提示展示全局横幅"""
        record = prompt_service.show_network_error("网络连接已断开")

        assert record.prompt_type == PromptType.NETWORK_ERROR
        assert record.message == "网络连接已断开"
        assert record.color == "#E6A23C"
        assert record.auto_dismissible is False

    def test_network_error_banner_visible(self, prompt_service):
        """网络异常横幅在活跃状态可获取"""
        prompt_service.show_network_error("网络超时，请检查连接")
        banner = prompt_service.get_network_banner()

        assert banner is not None
        assert banner.message == "网络超时，请检查连接"
        assert banner.dismissed is False

    def test_network_error_hidden_on_recovery(self, prompt_service):
        """网络恢复后横幅消失"""
        prompt_service.show_network_error("网络断开")
        assert prompt_service.get_network_banner() is not None

        prompt_service.hide_network_error()
        assert prompt_service.get_network_banner() is None


# ---------- FN-ERR-003g 会话过期提示 ----------

class TestSessionExpiredPrompt:
    """FN-ERR-003g: 会话过期提示 — 模态提示 + 自动跳转登录页，不自动消失"""

    def test_session_expired_shows_with_redirect(self, prompt_service):
        """会话过期提示展示模态弹窗并配置跳转"""
        record = prompt_service.show_session_expired()

        assert record.prompt_type == PromptType.SESSION_EXPIRED
        assert record.color == "#F56C6C"
        assert record.auto_dismissible is False
        assert record.metadata["redirect_url"] == "/login"
        assert record.metadata["auto_redirect"] is True

    def test_session_expired_custom_redirect(self, prompt_service):
        """会话过期支持自定义跳转地址"""
        record = prompt_service.show_session_expired(redirect_url="/auth/relogin")

        assert record.metadata["redirect_url"] == "/auth/relogin"

    def test_session_expired_dialog_visible(self, prompt_service):
        """会话过期弹窗在活跃状态可获取"""
        prompt_service.show_session_expired()
        dialog = prompt_service.get_session_expired_dialog()

        assert dialog is not None
        assert dialog.dismissed is False


# ---------- FN-ERR-003h 批量操作结果 ----------

class TestBatchResultPrompt:
    """FN-ERR-003h: 批量操作结果 — 详情面板（成功数/失败数/失败明细列表），不自动消失"""

    def test_batch_result_shows_summary(self, prompt_service):
        """批量操作结果展示成功/失败汇总"""
        result = BatchOperationResult(
            total=10,
            success_count=7,
            fail_count=3,
            fail_details=[
                {"item": "任务 A", "message": "依赖缺失"},
                {"item": "任务 B", "message": "资源不足"},
                {"item": "任务 C", "message": "权限不足"},
            ],
        )
        record = prompt_service.show_batch_result(result)

        assert record.prompt_type == PromptType.BATCH_RESULT
        assert record.message == "批量操作完成：成功 7 项，失败 3 项"
        assert record.color == "#409EFF"
        assert record.auto_dismissible is False

    def test_batch_result_includes_fail_details(self, prompt_service):
        """批量操作结果包含失败明细"""
        result = BatchOperationResult(
            total=5,
            success_count=3,
            fail_count=2,
            fail_details=[
                {"item": "item1", "message": "校验失败"},
                {"item": "item2", "message": "超时"},
            ],
        )
        record = prompt_service.show_batch_result(result)

        assert record.metadata["total"] == 5
        assert record.metadata["success_count"] == 3
        assert record.metadata["fail_count"] == 2
        assert len(record.metadata["fail_details"]) == 2

    def test_batch_result_panel_visible(self, prompt_service):
        """批量结果面板在活跃状态可获取"""
        result = BatchOperationResult(total=3, success_count=3, fail_count=0)
        prompt_service.show_batch_result(result)
        panel = prompt_service.get_batch_result_panel()

        assert panel is not None
        assert panel.dismissed is False


# ---------- 错误文案来自 API 非硬编码 ----------

class TestErrorMessageFromApi:
    """验证所有错误提示的文案来自 API 响应，非前端硬编码"""

    def test_error_toast_message_not_hardcoded(self, prompt_service):
        """错误 Toast 文案直接取自 API 响应"""
        api_messages = [
            "用户名已被占用",
            "密码复杂度不足：至少包含大小写字母和数字",
            "该资源已被其他用户锁定",
            "每日请求配额已用尽，请明天再试",
        ]
        for msg in api_messages:
            api_error = ApiErrorResponse(code="API_ERR", message=msg, status=400)
            record = prompt_service.show_error_toast(api_error)
            assert record.message == msg

    def test_form_validation_message_from_api(self, prompt_service):
        """表单校验错误文案来自 API"""
        api_msg = "邀请码无效或已过期"
        record = prompt_service.show_form_validation("invite_code", api_msg)
        assert record.message == api_msg

    def test_network_error_message_from_api(self, prompt_service):
        """网络异常提示文案由外部传入"""
        api_msg = "DNS 解析失败：无法连接到 api.example.com"
        record = prompt_service.show_network_error(api_msg)
        assert record.message == api_msg

    def test_batch_result_messages_from_api(self, prompt_service):
        """批量操作失败明细来自 API 响应"""
        fail_details = [
            {"item": "record_1", "message": "数据库约束冲突"},
            {"item": "record_2", "message": "外部服务调用超时"},
        ]
        result = BatchOperationResult(total=2, success_count=0, fail_count=2, fail_details=fail_details)
        record = prompt_service.show_batch_result(result)

        stored = record.metadata["fail_details"]
        assert stored[0]["message"] == "数据库约束冲突"
        assert stored[1]["message"] == "外部服务调用超时"


# ---------- Toast 堆叠不覆盖已有提示 ----------

class TestToastStacking:
    """Toast 支持堆叠展示，不覆盖已有提示"""

    def test_toasts_stack_without_overwriting(self, prompt_service):
        """多个 Toast 按序堆叠，前一个不被覆盖"""
        prompt_service.show_success_toast("第一步完成")
        prompt_service.show_success_toast("第二步完成")
        prompt_service.show_success_toast("第三步完成")

        toasts = prompt_service.get_active_toasts()
        assert len(toasts) == 3
        assert toasts[0].message == "第一步完成"
        assert toasts[1].message == "第二步完成"
        assert toasts[2].message == "第三步完成"

    def test_mixed_toast_types_stack(self, prompt_service):
        """不同类型 Toast 可混合堆叠"""
        prompt_service.show_success_toast("创建成功")
        api_err = ApiErrorResponse(code="WARN", message="请注意检查配置", status=200)
        prompt_service.show_error_toast(api_err)

        toasts = prompt_service.get_active_toasts()
        assert len(toasts) == 2
        assert toasts[0].prompt_type == PromptType.SUCCESS_TOAST
        assert toasts[1].prompt_type == PromptType.ERROR_TOAST

    def test_toast_stack_enforces_max_limit(self, prompt_service):
        """Toast 堆叠超过最大数时自动关闭最早的"""
        for i in range(7):
            prompt_service.show_success_toast(f"操作 {i + 1}")

        toasts = prompt_service.get_active_toasts()
        assert len(toasts) <= UserPromptService.MAX_STACK_SIZE

    def test_dismiss_one_toast_does_not_affect_others(self, prompt_service):
        """关闭某个 Toast 不影响堆栈中其他 Toast"""
        prompt_service.show_success_toast("第一条")
        prompt_service.show_success_toast("第二条")
        prompt_service.show_success_toast("第三条")

        prompt_service.dismiss_toast(1)  # 关闭第二条
        toasts = prompt_service.get_active_toasts()

        assert len(toasts) == 2
        assert toasts[0].message == "第一条"
        assert toasts[1].message == "第三条"


# ---------- 自动消失规则 ----------

class TestAutoDismissRules:
    """验证各种提示的自动消失规则"""

    @pytest.mark.parametrize("prompt_type,should_be_auto_dismissible", [
        (PromptType.FORM_VALIDATION, False),
        (PromptType.SUCCESS_TOAST, True),
        (PromptType.ERROR_TOAST, False),
        (PromptType.CONFIRM_DIALOG, False),
        (PromptType.LOADING_INDICATOR, True),
        (PromptType.NETWORK_ERROR, False),
        (PromptType.SESSION_EXPIRED, False),
        (PromptType.BATCH_RESULT, False),
    ])
    def test_auto_dismiss_rule(self, prompt_type, should_be_auto_dismissible, prompt_service):
        """每种提示类型的自动消失标记符合规范"""
        if prompt_type == PromptType.FORM_VALIDATION:
            record = prompt_service.show_form_validation("field", "错误")
        elif prompt_type == PromptType.SUCCESS_TOAST:
            record = prompt_service.show_success_toast("成功")
        elif prompt_type == PromptType.ERROR_TOAST:
            record = prompt_service.show_error_toast(
                ApiErrorResponse(code="ERR", message="错误", status=400)
            )
        elif prompt_type == PromptType.CONFIRM_DIALOG:
            record = prompt_service.show_confirm_dialog("确认", "确定吗？")
        elif prompt_type == PromptType.LOADING_INDICATOR:
            record = prompt_service.show_loading("加载中")
        elif prompt_type == PromptType.NETWORK_ERROR:
            record = prompt_service.show_network_error("网络异常")
        elif prompt_type == PromptType.SESSION_EXPIRED:
            record = prompt_service.show_session_expired()
        elif prompt_type == PromptType.BATCH_RESULT:
            record = prompt_service.show_batch_result(
                BatchOperationResult(total=1, success_count=1, fail_count=0)
            )

        assert record.auto_dismissible == should_be_auto_dismissible

    def test_success_toast_clears_on_auto_dismiss(self, prompt_service):
        """成功 Toast 模拟 3 秒后可被清除"""
        prompt_service.show_success_toast("保存成功")
        prompt_service.show_success_toast("更新成功")

        count = prompt_service.clear_all_dismissible()
        assert count == 2
        assert len(prompt_service.get_active_toasts()) == 0

    def test_error_toast_not_cleared_on_auto_dismiss(self, prompt_service):
        """错误 Toast 不会被自动清除"""
        prompt_service.show_error_toast(
            ApiErrorResponse(code="ERR", message="操作失败", status=500)
        )
        prompt_service.show_success_toast("另一操作成功")

        count = prompt_service.clear_all_dismissible()
        assert count == 1  # 只清除了成功 Toast

        toasts = prompt_service.get_active_toasts()
        assert len(toasts) == 1
        assert toasts[0].prompt_type == PromptType.ERROR_TOAST


# ---------- 完整触发场景测试 ----------

class TestCompletePromptTriggerScenarios:
    """验证 8 种提示类型均可正确触发"""

    def test_all_eight_prompt_types_trigger(self, prompt_service):
        """8 种提示类型均可正确触发和展示"""
        records = []

        # 1. 表单校验
        records.append(prompt_service.show_form_validation("email", "邮箱格式不正确"))
        # 2. 操作成功
        records.append(prompt_service.show_success_toast("数据保存成功"))
        # 3. 操作失败
        records.append(prompt_service.show_error_toast(
            ApiErrorResponse(code="FAIL", message="保存失败", status=500)
        ))
        # 4. 确认对话框
        records.append(prompt_service.show_confirm_dialog("确认删除", "确定删除？"))
        # 5. 加载状态
        records.append(prompt_service.show_loading("正在处理..."))
        # 6. 网络异常
        records.append(prompt_service.show_network_error("网络连接超时"))
        # 7. 会话过期
        records.append(prompt_service.show_session_expired())
        # 8. 批量操作结果
        records.append(prompt_service.show_batch_result(
            BatchOperationResult(total=5, success_count=3, fail_count=2)
        ))

        # 验证所有 8 种提示都已触发
        assert len(records) == 8
        expected_types = [
            PromptType.FORM_VALIDATION,
            PromptType.SUCCESS_TOAST,
            PromptType.ERROR_TOAST,
            PromptType.CONFIRM_DIALOG,
            PromptType.LOADING_INDICATOR,
            PromptType.NETWORK_ERROR,
            PromptType.SESSION_EXPIRED,
            PromptType.BATCH_RESULT,
        ]
        for record, expected_type in zip(records, expected_types):
            assert record.prompt_type == expected_type
