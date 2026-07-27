import pytest
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import time


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass
class Task:
    id: str
    title: str
    status: TaskStatus
    column_id: str
    position: int = 0


@dataclass
class KanbanColumn:
    id: str
    title: str
    tasks: list = field(default_factory=list)
    max_tasks: Optional[int] = None
    allowed_statuses: Optional[list] = None


class KanbanBoard:
    def __init__(self):
        self.columns = {}
        self._observers = []
        self._sync_batch = []
        self._sync_timer = None

    def add_column(self, column):
        self.columns[column.id] = column

    def remove_column(self, column_id):
        self.columns.pop(column_id, None)

    def add_task(self, column_id, task):
        col = self.columns.get(column_id)
        if col is None:
            raise ValueError(f"Column {column_id} not found")
        if col.max_tasks is not None and len(col.tasks) >= col.max_tasks:
            raise ValueError(f"Column {column_id} at max capacity {col.max_tasks}")
        task.position = len(col.tasks)
        col.tasks.append(task)
        self._notify("task_added", task)

    def move_task(self, task_id, target_column_id, target_position=None):
        start = time.perf_counter()
        source_col, task = self._find_task(task_id)
        if source_col is None or task is None:
            raise ValueError(f"Task {task_id} not found")
        target_col = self.columns.get(target_column_id)
        if target_col is None:
            raise ValueError(f"Target column {target_column_id} not found")
        if target_col.max_tasks is not None and len(target_col.tasks) >= target_col.max_tasks:
            raise ValueError(f"Target column {target_column_id} at max capacity {target_col.max_tasks}")
        if target_col.allowed_statuses is not None and task.status not in target_col.allowed_statuses:
            raise ValueError(f"Task status not allowed in column {target_column_id}")
        source_col.tasks.remove(task)
        if target_position is not None:
            target_col.tasks.insert(min(target_position, len(target_col.tasks)), task)
        else:
            task.position = len(target_col.tasks)
            target_col.tasks.append(task)
        task.column_id = target_column_id
        self._reindex(target_col)
        self._reindex(source_col)
        self._notify("task_moved", task, source_col.id, target_col.id)
        elapsed = (time.perf_counter() - start) * 1000
        return elapsed

    def _find_task(self, task_id):
        for col in self.columns.values():
            for t in col.tasks:
                if t.id == task_id:
                    return col, t
        return None, None

    def _reindex(self, column):
        for i, t in enumerate(column.tasks):
            t.position = i

    def subscribe(self, observer):
        self._observers.append(observer)

    def _notify(self, event, task, *args):
        for observer in self._observers:
            observer.on_event(event, task, *args)

    def sync(self):
        return list(self.columns.values())

    def get_column(self, column_id):
        return self.columns.get(column_id)


class SyncObserver:
    def __init__(self):
        self.events = []

    def on_event(self, event, task, *args):
        self.events.append((event, task.id, args))

@pytest.fixture
def board():
    b = KanbanBoard()
    b.add_column(KanbanColumn(id="todo", title="待办", allowed_statuses=[TaskStatus.TODO]))
    b.add_column(KanbanColumn(id="in_progress", title="进行中", allowed_statuses=[TaskStatus.TODO, TaskStatus.IN_PROGRESS]))
    b.add_column(KanbanColumn(id="done", title="已完成", allowed_statuses=[TaskStatus.IN_PROGRESS, TaskStatus.DONE]))
    b.add_column(KanbanColumn(id="custom_review", title="评审中", allowed_statuses=[TaskStatus.IN_PROGRESS], max_tasks=5))
    return b


@pytest.fixture
def sample_tasks(board):
    tasks = [
        Task(id="t1", title="设计数据库模型", status=TaskStatus.TODO, column_id="todo"),
        Task(id="t2", title="实现用户认证", status=TaskStatus.IN_PROGRESS, column_id="in_progress"),
        Task(id="t3", title="编写API文档", status=TaskStatus.DONE, column_id="done"),
    ]
    for t in tasks:
        board.add_task(t.column_id, t)
    return tasks


class TestKanbanDragAndDrop:

    @pytest.mark.slow
    def test_drag_response_time_within_300ms(self, board, sample_tasks):
        elapsed = board.move_task("t1", "in_progress")
        assert elapsed <= 300.0, f"Drag response {elapsed:.2f}ms exceeded 300ms limit"

    @pytest.mark.slow
    def test_drag_bulk_response_time_within_300ms(self, board, sample_tasks):
        for _ in range(50):
            board.add_task("todo", Task(id=f"bulk_{_}", title=f"Task {_}", status=TaskStatus.TODO, column_id="todo"))
        times = []
        for i in range(50):
            elapsed = board.move_task(f"bulk_{i}", "in_progress")
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg <= 300.0, f"Average drag response {avg:.2f}ms exceeded 300ms limit"

    def test_status_updates_on_drag(self, board, sample_tasks):
        original_column_id = board._find_task("t2")[1].column_id
        assert original_column_id == "in_progress"
        board.move_task("t2", "done")
        task = board._find_task("t2")[1]
        assert task is not None
        assert task.column_id == "done"
        assert task.column_id != original_column_id

    def test_sync_reflects_current_state(self, board, sample_tasks):
        board.move_task("t1", "in_progress")
        snapshot_after = board.sync()
        after_map = {col.id: col for col in snapshot_after}
        assert len(after_map["todo"].tasks) == 0
        assert len(after_map["in_progress"].tasks) == 2

    def test_observer_notified_on_move(self, board, sample_tasks):
        observer = SyncObserver()
        board.subscribe(observer)
        board.move_task("t1", "in_progress")
        assert len(observer.events) >= 1
        event_name, task_id, args = observer.events[-1]
        assert event_name == "task_moved"
        assert task_id == "t1"
        assert args[0] == "todo"
        assert args[1] == "in_progress"

    def test_observer_notified_on_add(self, board):
        observer = SyncObserver()
        board.subscribe(observer)
        new_task = Task(id="t_new", title="新任务", status=TaskStatus.TODO, column_id="todo")
        board.add_task("todo", new_task)
        assert len(observer.events) >= 1
        assert observer.events[0][0] == "task_added"
        assert observer.events[0][1] == "t_new"

    def test_realtime_sync_consistency_after_moves(self, board, sample_tasks):
        moves = [("t1", "in_progress"), ("t2", "done"), ("t3", "done")]
        for task_id, target in moves:
            board.move_task(task_id, target)
        synced = board.sync()
        col_map = {col.id: col for col in synced}
        assert all(t.column_id == "in_progress" for t in col_map["in_progress"].tasks)
        assert col_map["done"].tasks[0].column_id == "done"
        assert col_map["done"].tasks[1].column_id == "done"

    def test_custom_column_accepts_task(self, board, sample_tasks):
        review_task = Task(id="t_review", title="代码审查", status=TaskStatus.IN_PROGRESS, column_id="in_progress")
        board.add_task("in_progress", review_task)
        board.move_task("t_review", "custom_review")
        col = board.get_column("custom_review")
        assert col is not None
        assert any(t.id == "t_review" for t in col.tasks)

    def test_custom_column_max_capacity(self, board):
        for i in range(5):
            t = Task(id=f"max_{i}", title=f"Max Test {i}", status=TaskStatus.IN_PROGRESS, column_id="in_progress")
            board.add_task("in_progress", t)
            board.move_task(f"max_{i}", "custom_review")
        overflow = Task(id="overflow", title="Overflow", status=TaskStatus.IN_PROGRESS, column_id="in_progress")
        board.add_task("in_progress", overflow)
        with pytest.raises(ValueError, match="at max capacity"):
            board.move_task("overflow", "custom_review")

    def test_custom_column_status_restriction(self, board):
        done_task = Task(id="t_done_restrict", title="已完成任务", status=TaskStatus.DONE, column_id="done")
        board.add_task("done", done_task)
        with pytest.raises(ValueError, match="not allowed"):
            board.move_task("t_done_restrict", "custom_review")

    def test_custom_column_add_and_remove(self, board):
        col = KanbanColumn(id="archive", title="归档", allowed_statuses=[TaskStatus.DONE])
        board.add_column(col)
        assert board.get_column("archive") is not None
        board.remove_column("archive")
        assert board.get_column("archive") is None

    def test_move_to_nonexistent_column_raises(self, board, sample_tasks):
        with pytest.raises(ValueError, match="not found"):
            board.move_task("t1", "nonexistent")

    def test_move_nonexistent_task_raises(self, board):
        with pytest.raises(ValueError, match="not found"):
            board.move_task("ghost_task", "todo")

    def test_position_ordering_on_insert(self, board, sample_tasks):
        task_mid = Task(id="t_mid", title="中间插入", status=TaskStatus.TODO, column_id="todo")
        board.add_task("todo", task_mid)
        board.move_task("t_mid", "in_progress", target_position=0)
        col = board.get_column("in_progress")
        assert col is not None
        assert col.tasks[0].id == "t_mid"
        assert col.tasks[0].position == 0
        assert col.tasks[1].position == 1

    def test_position_reindex_after_remove(self, board, sample_tasks):
        board.move_task("t1", "in_progress")
        board.move_task("t2", "done")
        col = board.get_column("in_progress")
        assert col is not None
        assert col.tasks[0].position == 0

    def test_snapshot_data_integrity(self, board, sample_tasks):
        board.move_task("t1", "in_progress")
        snapshot = board.sync()
        column_ids = {col.id for col in snapshot}
        assert "todo" in column_ids
        assert "in_progress" in column_ids
        assert "done" in column_ids
        for col in snapshot:
            if col.id == "todo":
                assert len(col.tasks) == 0
            elif col.id == "in_progress":
                assert len(col.tasks) == 2
            elif col.id == "done":
                assert len(col.tasks) == 1

    def test_drag_isolation_no_side_effects(self, board, sample_tasks):
        board.move_task("t1", "in_progress")
        assert len(board.get_column("done").tasks) == 1
        assert board.get_column("done").tasks[0].id == "t3"

    def test_move_with_empty_task_id_raises(self, board):
        with pytest.raises(ValueError, match="not found"):
            board.move_task("", "todo")

    def test_move_with_none_task_id_raises(self, board):
        with pytest.raises(ValueError, match="not found"):
            board.move_task(None, "todo")

    def test_move_to_empty_column_id_raises(self, board, sample_tasks):
        with pytest.raises(ValueError, match="not found"):
            board.move_task("t1", "")

    def test_move_to_none_column_id_raises(self, board, sample_tasks):
        with pytest.raises(ValueError, match="not found"):
            board.move_task("t1", None)

    def test_duplicate_move_same_task(self, board, sample_tasks):
        board.move_task("t1", "in_progress")
        elapsed = board.move_task("t1", "in_progress")
        assert elapsed >= 0
        col = board.get_column("in_progress")
        assert col is not None
        assert any(t.id == "t1" for t in col.tasks)

    def test_cyclic_moves_preserve_integrity(self, board, sample_tasks):
        t4 = Task(id="t4", title="循环任务", status=TaskStatus.TODO, column_id="todo")
        board.add_task("todo", t4)
        moves = [("t4", "in_progress"), ("t4", "todo"), ("t4", "in_progress"), ("t4", "todo"), ("t4", "in_progress")]
        for task_id, target in moves:
            board.move_task(task_id, target)
        col = board.get_column("in_progress")
        assert col is not None
        assert any(t.id == "t4" for t in col.tasks)

    def test_target_position_negative(self, board, sample_tasks):
        board.move_task("t1", "in_progress", target_position=-1)
        col = board.get_column("in_progress")
        assert col is not None
        assert any(t.id == "t1" for t in col.tasks)

    def test_target_position_beyond_len_clamps(self, board, sample_tasks):
        board.move_task("t1", "in_progress", target_position=9999)
        col = board.get_column("in_progress")
        assert col is not None
        assert col.tasks[-1].id == "t1"

    def test_target_position_at_end(self, board, sample_tasks):
        board.move_task("t1", "in_progress", target_position=1)
        col = board.get_column("in_progress")
        assert col is not None
        assert col.tasks[-1].id == "t1"

    def test_move_task_to_empty_column_with_position_zero(self, board, sample_tasks):
        board.move_task("t1", "in_progress", target_position=0)
        col = board.get_column("in_progress")
        assert col is not None
        assert len(col.tasks) == 2
        assert col.tasks[0].position == 0
        assert col.tasks[1].position == 1

    def test_move_nonexistent_task_from_empty_column(self, board):
        col = board.get_column("in_progress")
        assert col is not None
        assert len(col.tasks) == 0
        with pytest.raises(ValueError, match="not found"):
            board.move_task("phantom", "in_progress")

    def test_add_task_to_max_tasks_zero_column_raises(self, board):
        board.add_column(KanbanColumn(id="blocked", title="阻塞", max_tasks=0, allowed_statuses=[TaskStatus.TODO]))
        t = Task(id="blocked_t", title="阻塞任务", status=TaskStatus.TODO, column_id="blocked")
        with pytest.raises(ValueError, match="at max capacity"):
            board.add_task("blocked", t)

    def test_move_task_to_max_tasks_zero_column_raises(self, board, sample_tasks):
        board.add_column(KanbanColumn(id="blocked", title="阻塞", max_tasks=0, allowed_statuses=[TaskStatus.TODO]))
        with pytest.raises(ValueError, match="at max capacity"):
            board.move_task("t1", "blocked")

    def test_column_with_empty_allowed_statuses_rejects_all(self, board, sample_tasks):
        board.add_column(KanbanColumn(id="restricted", title="限制列", allowed_statuses=[]))
        with pytest.raises(ValueError, match="not allowed"):
            board.move_task("t1", "restricted")

    def test_column_with_none_allowed_statuses_allows_all(self, board, sample_tasks):
        board.add_column(KanbanColumn(id="open", title="开放列", allowed_statuses=None))
        t = Task(id="t_open", title="开放任务", status=TaskStatus.TODO, column_id="todo")
        board.add_task("todo", t)
        board.move_task("t_open", "open")
        col = board.get_column("open")
        assert col is not None
        assert any(t.id == "t_open" for t in col.tasks)

    def test_multiple_observers_all_notified(self, board, sample_tasks):
        obs1 = SyncObserver()
        obs2 = SyncObserver()
        board.subscribe(obs1)
        board.subscribe(obs2)
        board.move_task("t1", "in_progress")
        assert len(obs1.events) == 1
        assert len(obs2.events) == 1
        assert obs1.events[0][1] == "t1"
        assert obs2.events[0][1] == "t1"
