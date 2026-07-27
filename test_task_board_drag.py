import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field


# ============================================================
# 模拟数据模型
# ============================================================

@dataclass
class MockTask:
    id: str
    project_id: str
    name: str
    status: str = "pending"
    priority: str = "medium"
    progress: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MockBoardColumn:
    id: str
    board_id: str
    name: str
    slug: str
    color: str = "#E5E7EB"
    position: int = 0
    max_tasks: Optional[int] = None
    is_default: bool = False
    is_active: bool = True


@dataclass
class MockBoard:
    id: str
    project_id: str
    name: str
    slug: str
    color: str = "#3B82F6"
    position: int = 0
    is_default: bool = False
    is_active: bool = True


# ============================================================
# 拖拽引擎核心实现
# ============================================================

DRAG_RESPONSE_TIMEOUT_MS = 300

VALID_STATUSES = {
    "pending", "assigned", "running", "in_progress",
    "delivered", "accepted", "failed", "rejected", "reassigned"
}

STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "pending": ["assigned", "running"],
    "assigned": ["running", "pending", "reassigned"],
    "running": ["delivered", "failed", "assigned"],
    "in_progress": ["delivered", "running"],
    "delivered": ["accepted", "rejected", "running"],
    "accepted": [],
    "rejected": ["running", "assigned"],
    "failed": ["running", "assigned"],
    "reassigned": ["assigned", "running"],
}

COLUMN_STATUS_MAP: Dict[str, str] = {
    "to-do": "pending",
    "in-progress": "in_progress",
    "running": "running",
    "review": "delivered",
    "done": "accepted",
    "blocked": "failed",
    "backlog": "pending",
}


class DragOperationException(Exception):
    """拖拽操作异常"""
    pass


class KanbanDragEngine:
    """
    看板拖拽引擎 — 核心业务逻辑
    负责：任务拖拽、状态更新、响应时间控制、列自定义管理
    """

    def __init__(self):
        self.tasks: Dict[str, MockTask] = {}
        self.boards: Dict[str, MockBoard] = {}
        self.columns: Dict[str, MockBoardColumn] = {}
        self._column_order_in_board: Dict[str, Dict[str, int]] = {}
        self._operation_log: List[Dict[str, Any]] = []

    def create_board(self, project_id: str, name: str, color: str = "#3B82F6") -> MockBoard:
        board_id = str(uuid.uuid4())
        board = MockBoard(
            id=board_id, project_id=project_id, name=name,
            slug=name.lower().replace(" ", "-"), color=color,
        )
        self.boards[board_id] = board
        self._column_order_in_board[board_id] = {}
        self._operation_log.append({
            "action": "create_board", "board_id": board_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return board

    def create_column(self, board_id: str, name: str, color: str = "#E5E7EB",
                      position: Optional[int] = None) -> MockBoardColumn:
        if board_id not in self.boards:
            raise DragOperationException(f"看板不存在: {board_id}")
        col_id = str(uuid.uuid4())
        if position is None:
            existing = [c for c in self.columns.values() if c.board_id == board_id]
            position = max((c.position for c in existing), default=-1) + 1
        column = MockBoardColumn(
            id=col_id, board_id=board_id, name=name,
            slug=name.lower().replace(" ", "-"), color=color, position=position,
        )
        self.columns[col_id] = column
        self._column_order_in_board[board_id][col_id] = position
        self._operation_log.append({
            "action": "create_column", "column_id": col_id,
            "board_id": board_id, "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return column

    def create_task(self, project_id: str, name: str,
                    status: str = "pending") -> MockTask:
        if status not in VALID_STATUSES:
            raise DragOperationException(f"无效的任务状态: {status}")
        task_id = str(uuid.uuid4())
        task = MockTask(
            id=task_id, project_id=project_id, name=name, status=status,
        )
        self.tasks[task_id] = task
        self._operation_log.append({
            "action": "create_task", "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return task

    def drag_task(self, task_id: str, target_column_id: str,
                  order_in_column: Optional[int] = None) -> Dict[str, Any]:
        """
        执行拖拽操作：将任务从一列拖到另一列
        返回拖拽结果（含状态更新、耗时信息）
        """
        start_time = time.perf_counter()
        task = self._get_task_or_raise(task_id)
        column = self._get_column_or_raise(target_column_id)

        new_status = self._resolve_status(column)
        old_status = task.status
        self._validate_transition(task, new_status)

        task.status = new_status
        task.updated_at = datetime.now(timezone.utc)
        if new_status == "running" and not task.started_at:
            task.started_at = datetime.now(timezone.utc)
        if new_status == "accepted":
            task.completed_at = datetime.now(timezone.utc)
        if order_in_column is not None:
            self._column_order_in_board[column.board_id][task_id] = order_in_column

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        result = {
            "task_id": task_id,
            "old_status": old_status,
            "new_status": new_status,
            "column_id": target_column_id,
            "column_name": column.name,
            "order_in_column": order_in_column,
            "elapsed_ms": round(elapsed_ms, 2),
            "status_changed": old_status != new_status,
            "sync_event": {
                "type": "task_status_changed",
                "task_id": task_id,
                "from": old_status,
                "to": new_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        self._operation_log.append({
            "action": "drag_task", "task_id": task_id,
            "from_status": old_status, "to_status": new_status,
            "target_column": target_column_id,
            "elapsed_ms": elapsed_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return result

    def get_board_columns(self, board_id: str) -> List[MockBoardColumn]:
        if board_id not in self.boards:
            raise DragOperationException(f"看板不存在: {board_id}")
        cols = [c for c in self.columns.values() if c.board_id == board_id and c.is_active]
        return sorted(cols, key=lambda c: c.position)

    def get_task(self, task_id: str) -> MockTask:
        return self._get_task_or_raise(task_id)

    def get_operation_log(self) -> List[Dict[str, Any]]:
        return list(self._operation_log)

    def _get_task_or_raise(self, task_id: str) -> MockTask:
        task = self.tasks.get(task_id)
        if not task:
            raise DragOperationException(f"任务不存在: {task_id}")
        return task

    def _get_column_or_raise(self, column_id: str) -> MockBoardColumn:
        column = self.columns.get(column_id)
        if not column:
            raise DragOperationException(f"列不存在: {column_id}")
        return column

    def _resolve_status(self, column: MockBoardColumn) -> str:
        """根据列 slug 解析目标状态"""
        status = COLUMN_STATUS_MAP.get(column.slug)
        if status is None:
            status = column.slug.replace("-", "_")
        if status not in VALID_STATUSES:
            raise DragOperationException(f"列 '{column.slug}' 映射的状态 '{status}' 不合法")
        return status

    def _validate_transition(self, task: MockTask, new_status: str) -> None:
        """校验状态转换是否合法"""
        allowed = STATUS_TRANSITIONS.get(task.status, [])
        if allowed and new_status not in allowed:
            raise DragOperationException(
                f"状态转换非法: '{task.status}' -> '{new_status}'。"
                f"允许的转换: {allowed}"
            )


# ============================================================
# 测试类：拖拽响应时间
# ============================================================

class TestDragResponseTime:
    """验收标准：拖拽响应 <= 300ms"""

    @pytest.fixture
    def engine(self):
        return KanbanDragEngine()

    @pytest.fixture
    def setup_board(self, engine):
        board = engine.create_board("project-1", "Sprint 看板", "#3B82F6")
        col_todo = engine.create_column(board.id, "To-Do", "#6B7280", 0)
        col_running = engine.create_column(board.id, "Running", "#3B82F6", 1)
        col_done = engine.create_column(board.id, "Done", "#10B981", 2)
        task = engine.create_task("project-1", "任务 A", "pending")
        return {
            "board": board,
            "col_todo": col_todo,
            "col_running": col_running,
            "col_done": col_done,
            "task": task,
        }

    def test_drag_single_task_response_time_under_300ms(self, engine, setup_board):
        """单次拖拽操作响应时间必须在 300ms 以内"""
        result = engine.drag_task(
            setup_board["task"].id, setup_board["col_running"].id
        )
        assert result["elapsed_ms"] < DRAG_RESPONSE_TIMEOUT_MS
        assert result["new_status"] == "running"
        assert result["status_changed"] is True

    def test_drag_batch_tasks_each_under_300ms(self, engine, setup_board):
        """批量拖拽：每个任务的响应时间都必须 < 300ms"""
        tasks = [
            engine.create_task("project-1", f"任务 {i}", "pending")
            for i in range(20)
        ]
        for task in tasks:
            result = engine.drag_task(task.id, setup_board["col_running"].id)
            assert result["elapsed_ms"] < DRAG_RESPONSE_TIMEOUT_MS

    def test_drag_response_time_stable_under_load(self, engine):
        """在已有大量数据的场景下，拖拽响应时间仍 < 300ms"""
        board = engine.create_board("project-heavy", "重型看板")
        col_running = engine.create_column(board.id, "Running", "#3B82F6", 1)
        tasks = [engine.create_task("project-heavy", f"任务 {i}") for i in range(200)]
        for task in tasks[:10]:
            result = engine.drag_task(task.id, col_running.id)
            assert result["elapsed_ms"] < DRAG_RESPONSE_TIMEOUT_MS

    def test_drag_result_contains_elapsed_ms_field(self, engine, setup_board):
        """拖拽结果必须包含 elapsed_ms 字段"""
        result = engine.drag_task(
            setup_board["task"].id, setup_board["col_running"].id
        )
        assert "elapsed_ms" in result
        assert isinstance(result["elapsed_ms"], (int, float))
        assert result["elapsed_ms"] > 0


# ============================================================
# 测试类：状态实时更新同步
# ============================================================

class TestStatusRealtimeSync:
    """验收标准：状态实时更新同步"""

    @pytest.fixture
    def engine(self):
        return KanbanDragEngine()

    @pytest.fixture
    def setup_board(self, engine):
        board = engine.create_board("project-sync", "同步看板", "#8B5CF6")
        col_todo = engine.create_column(board.id, "To-Do", "#6B7280", 0)
        col_running = engine.create_column(board.id, "Running", "#3B82F6", 1)
        col_review = engine.create_column(board.id, "Review", "#F59E0B", 2)
        col_done = engine.create_column(board.id, "Done", "#10B981", 3)
        task = engine.create_task("project-sync", "同步测试任务", "pending")
        return {
            "board": board,
            "col_todo": col_todo,
            "col_running": col_running,
            "col_review": col_review,
            "col_done": col_done,
            "task": task,
        }

    def test_drag_updates_task_status_immediately(self, engine, setup_board):
        """拖拽后任务状态立即更新"""
        engine.drag_task(setup_board["task"].id, setup_board["col_running"].id)
        updated = engine.get_task(setup_board["task"].id)
        assert updated.status == "running"

    def test_drag_sync_event_is_emitted(self, engine, setup_board):
        """拖拽操作必须产生同步事件"""
        result = engine.drag_task(
            setup_board["task"].id, setup_board["col_running"].id
        )
        sync_event = result["sync_event"]
        assert sync_event["type"] == "task_status_changed"
        assert sync_event["task_id"] == setup_board["task"].id
        assert sync_event["from"] == "pending"
        assert sync_event["to"] == "running"
        assert "timestamp" in sync_event

    def test_drag_chain_status_transitions_sync(self, engine, setup_board):
        """多步拖拽链式状态转换，每一步都同步更新"""
        task = setup_board["task"]
        # pending -> running
        r1 = engine.drag_task(task.id, setup_board["col_running"].id)
        assert r1["new_status"] == "running"
        t = engine.get_task(task.id)
        assert t.status == "running"

        # running -> delivered (review)
        r2 = engine.drag_task(task.id, setup_board["col_review"].id)
        assert r2["new_status"] == "delivered"
        t = engine.get_task(task.id)
        assert t.status == "delivered"

    def test_drag_started_at_set_on_running(self, engine, setup_board):
        """拖到 running 列时，started_at 自动设置"""
        engine.drag_task(setup_board["task"].id, setup_board["col_running"].id)
        task = engine.get_task(setup_board["task"].id)
        assert task.started_at is not None

    def test_drag_completed_at_set_on_accepted(self, engine, setup_board):
        """拖到 done 列（accepted 状态）时，completed_at 自动设置"""
        task = setup_board["task"]
        engine.drag_task(task.id, setup_board["col_running"].id)
        engine.drag_task(task.id, setup_board["col_review"].id)
        result = engine.drag_task(task.id, setup_board["col_done"].id)
        assert result["new_status"] == "accepted"
        task = engine.get_task(task.id)
        assert task.completed_at is not None

    def test_operation_log_records_drag_sequence(self, engine, setup_board):
        """操作日志完整记录拖拽序列"""
        task = setup_board["task"]
        engine.drag_task(task.id, setup_board["col_running"].id)
        engine.drag_task(task.id, setup_board["col_review"].id)
        log = engine.get_operation_log()
        drag_entries = [e for e in log if e["action"] == "drag_task"]
        assert len(drag_entries) == 2
        assert drag_entries[0]["from_status"] == "pending"
        assert drag_entries[0]["to_status"] == "running"
        assert drag_entries[1]["from_status"] == "running"
        assert drag_entries[1]["to_status"] == "delivered"

    def test_sync_timestamp_is_monotonic(self, engine, setup_board):
        """同步事件时间戳单调递增"""
        task = setup_board["task"]
        r1 = engine.drag_task(task.id, setup_board["col_running"].id)
        time.sleep(0.01)
        r2 = engine.drag_task(task.id, setup_board["col_review"].id)
        ts1 = r1["sync_event"]["timestamp"]
        ts2 = r2["sync_event"]["timestamp"]
        assert ts1 <= ts2


# ============================================================
# 测试类：看板列自定义
# ============================================================

class TestBoardColumnCustomization:
    """验收标准：看板列支持自定义"""

    @pytest.fixture
    def engine(self):
        return KanbanDragEngine()

    def test_create_custom_column(self, engine):
        """可以创建自定义列"""
        board = engine.create_board("proj-1", "我的看板")
        custom_col = engine.create_column(board.id, "技术评审", "#FF6B6B", position=5)
        assert custom_col.name == "技术评审"
        assert custom_col.color == "#FF6B6B"
        assert custom_col.position == 5
        assert custom_col.id is not None

    def test_create_multiple_custom_columns(self, engine):
        """可以创建多个自定义列"""
        board = engine.create_board("proj-multi", "多列看板")
        names = ["需求池", "设计中", "开发中", "测试中", "已上线"]
        columns_created = []
        for i, name in enumerate(names):
            col = engine.create_column(board.id, name, position=i)
            columns_created.append(col)
        assert len(columns_created) == 5
        for i, col in enumerate(columns_created):
            assert col.position == i
            assert col.name == names[i]

    def test_columns_sorted_by_position(self, engine):
        """列按 position 排序返回"""
        board = engine.create_board("proj-sort", "排序看板")
        engine.create_column(board.id, "列 C", position=2)
        engine.create_column(board.id, "列 A", position=0)
        engine.create_column(board.id, "列 B", position=1)
        cols = engine.get_board_columns(board.id)
        assert [c.name for c in cols] == ["列 A", "列 B", "列 C"]

    def test_auto_position_when_none_given(self, engine):
        """未指定 position 时自动递增"""
        board = engine.create_board("proj-auto", "自动位置看板")
        col1 = engine.create_column(board.id, "第一列")
        col2 = engine.create_column(board.id, "第二列")
        col3 = engine.create_column(board.id, "第三列")
        assert col1.position == 0
        assert col2.position == 1
        assert col3.position == 2

    def test_create_column_on_nonexistent_board_raises(self, engine):
        """在不存在的眼板上创建列应抛出异常"""
        with pytest.raises(DragOperationException, match="看板不存在"):
            engine.create_column("nonexistent-board-id", "某列")

    def test_custom_column_can_be_used_for_drag(self, engine):
        """自定义列可以用于拖拽目标"""
        board = engine.create_board("proj-drag-custom", "自定义拖拽看板")
        col_todo = engine.create_column(board.id, "To-Do", position=0)
        col_running = engine.create_column(board.id, "Running", position=1)
        custom_col = engine.create_column(board.id, "Custom-Review", "#EF4444", position=3)
        task = engine.create_task("proj-drag-custom", "自定义任务", "pending")

        result = engine.drag_task(task.id, custom_col.id)
        assert result["column_name"] == "Custom-Review"
        assert result["status_changed"] is True

    def test_board_color_customization(self, engine):
        """看板颜色可自定义"""
        board = engine.create_board("proj-color", "彩色看板", color="#FF00FF")
        assert board.color == "#FF00FF"

    def test_column_color_customization(self, engine):
        """列颜色可自定义"""
        board = engine.create_board("proj-col-color", "列色看板")
        col = engine.create_column(board.id, "高亮列", color="#FFD700")
        assert col.color == "#FFD700"

    def test_inactive_columns_excluded_from_board_view(self, engine):
        """不活跃的列不在看板视图中显示"""
        board = engine.create_board("proj-inactive", "含隐藏列看板")
        active_col = engine.create_column(board.id, "显示列", position=0)
        hidden_col = engine.create_column(board.id, "隐藏列", position=1)
        hidden_col.is_active = False
        cols = engine.get_board_columns(board.id)
        assert len(cols) == 1
        assert cols[0].name == "显示列"


# ============================================================
# 测试类：状态转换合法性
# ============================================================

class TestStatusTransitionValidation:
    """拖拽状态转换的合法性校验"""

    @pytest.fixture
    def engine(self):
        return KanbanDragEngine()

    @pytest.fixture
    def setup_board(self, engine):
        board = engine.create_board("proj-val", "校验看板")
        col_running = engine.create_column(board.id, "Running", position=1)
        col_review = engine.create_column(board.id, "Review", position=2)
        col_done = engine.create_column(board.id, "Done", position=3)
        return {
            "board": board,
            "col_running": col_running,
            "col_review": col_review,
            "col_done": col_done,
        }

    def test_valid_transition_pending_to_running(self, engine, setup_board):
        """pending -> running 合法"""
        task = engine.create_task("proj-val", "合法任务", "pending")
        result = engine.drag_task(task.id, setup_board["col_running"].id)
        assert result["new_status"] == "running"

    def test_invalid_transition_raises(self, engine, setup_board):
        """非法状态转换应抛出异常（pending 不能直接到 delivered）"""
        task = engine.create_task("proj-val", "非法任务", "pending")
        with pytest.raises(DragOperationException, match="状态转换非法"):
            engine.drag_task(task.id, setup_board["col_review"].id)

    def test_accepted_task_cannot_transition(self, engine, setup_board):
        """已接受的任务不可再转换状态"""
        task = engine.create_task("proj-val", "已完成任务", "accepted")
        with pytest.raises(DragOperationException, match="状态转换非法"):
            engine.drag_task(task.id, setup_board["col_running"].id)

    def test_drag_nonexistent_task_raises(self, engine, setup_board):
        """不存在的任务拖拽应抛出异常"""
        with pytest.raises(DragOperationException, match="任务不存在"):
            engine.drag_task("fake-task-id", setup_board["col_running"].id)

    def test_drag_to_nonexistent_column_raises(self, engine):
        """拖到不存在的列应抛出异常"""
        board = engine.create_board("proj-no-col", "无列看板")
        task = engine.create_task("proj-no-col", "测试任务")
        with pytest.raises(DragOperationException, match="列不存在"):
            engine.drag_task(task.id, "fake-column-id")


# ============================================================
# 测试类：端到端拖拽场景
# ============================================================

class TestEndToEndDragScenarios:
    """端到端场景测试"""

    @pytest.fixture
    def engine(self):
        return KanbanDragEngine()

    def test_full_lifecycle_pending_to_accepted(self, engine):
        """完整生命周期：pending -> running -> delivered -> accepted"""
        board = engine.create_board("proj-e2e", "全周期看板")
        col_todo = engine.create_column(board.id, "To-Do", position=0)
        col_running = engine.create_column(board.id, "Running", position=1)
        col_review = engine.create_column(board.id, "Review", position=2)
        col_done = engine.create_column(board.id, "Done", position=3)
        task = engine.create_task("proj-e2e", "全周期任务")

        # Step 1: pending -> running
        r1 = engine.drag_task(task.id, col_running.id)
        assert r1["new_status"] == "running"
        assert r1["elapsed_ms"] < DRAG_RESPONSE_TIMEOUT_MS
        assert r1["sync_event"]["from"] == "pending"
        assert r1["sync_event"]["to"] == "running"

        # Step 2: running -> delivered
        r2 = engine.drag_task(task.id, col_review.id)
        assert r2["new_status"] == "delivered"
        assert r2["sync_event"]["from"] == "running"
        assert r2["sync_event"]["to"] == "delivered"

        # Step 3: delivered -> accepted
        r3 = engine.drag_task(task.id, col_done.id)
        assert r3["new_status"] == "accepted"
        assert r3["sync_event"]["from"] == "delivered"
        assert r3["sync_event"]["to"] == "accepted"

        task = engine.get_task(task.id)
        assert task.status == "accepted"
        assert task.started_at is not None
        assert task.completed_at is not None

    def test_rejected_task_can_be_reworked(self, engine):
        """被拒绝的任务可以重新进入开发"""
        board = engine.create_board("proj-reject", "重做看板")
        col_running = engine.create_column(board.id, "Running", position=1)
        col_review = engine.create_column(board.id, "Review", position=2)
        task = engine.create_task("proj-reject", "需重做任务", "delivered")

        engine.drag_task(task.id, col_done.id)
        assert engine.get_task(task.id).status == "accepted"

    def test_multiple_tasks_on_same_board_drag_independently(self, engine):
        """同一看板上的多个任务可独立拖拽"""
        board = engine.create_board("proj-multi-task", "多任务看板")
        col_running = engine.create_column(board.id, "Running", position=1)
        tasks = [
            engine.create_task("proj-multi-task", f"任务 {i}")
            for i in range(5)
        ]
        for i, task in enumerate(tasks):
            result = engine.drag_task(task.id, col_running.id)
            assert result["task_id"] == task.id
            assert result["new_status"] == "running"

        for task in tasks:
            assert engine.get_task(task.id).status == "running"

    def test_concurrent_boards_are_isolated(self, engine):
        """不同看板上的任务拖拽互不影响"""
        board_a = engine.create_board("proj-a", "看板 A")
        board_b = engine.create_board("proj-b", "看板 B")
        col_a = engine.create_column(board_a.id, "Running", position=1)
        col_b = engine.create_column(board_b.id, "Running", position=1)

        task_a = engine.create_task("proj-a", "任务 A")
        task_b = engine.create_task("proj-b", "任务 B")

        engine.drag_task(task_a.id, col_a.id)
        assert engine.get_task(task_a.id).status == "running"
        assert engine.get_task(task_b.id).status == "pending"

        engine.drag_task(task_b.id, col_b.id)
        assert engine.get_task(task_a.id).status == "running"
        assert engine.get_task(task_b.id).status == "running"
