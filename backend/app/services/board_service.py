#!/usr/bin/env python3
"""看板服务 - 处理看板CRUD、列管理"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
import uuid


class BoardService:
    DEFAULT_COLUMNS = [
        {"name": "To Do", "color": "#6B7280", "position": 0, "is_default": True},
        {"name": "In Progress", "color": "#3B82F6", "position": 1, "is_default": True},
        {"name": "Review", "color": "#F59E0B", "position": 2, "is_default": True},
        {"name": "Done", "color": "#10B981", "position": 3, "is_default": True},
    ]

    def __init__(self, db: Session, current_user_id: str = None):
        self.db = db
        self.current_user_id = current_user_id

    def _import_models(self):
        from app.models.board import Board, BoardColumn
        from app.models.task import Task
        return Board, BoardColumn, Task

    def _import_project_model(self):
        from app.models.project import Project
        return Project

    def create_board(self, name: str, project_id: str = None, description=None, color="#3B82F6", position=0) -> dict:
        Board, BoardColumn, Task = self._import_models()
        if not project_id:
            Project = self._import_project_model()
            existing = self.db.query(Project).first()
            if existing:
                project_id = existing.id
            else:
                p = Project(id=str(uuid.uuid4()), name="Default", slug="default")
                self.db.add(p)
                self.db.flush()
                project_id = p.id
        board = Board(
            id=str(uuid.uuid4()),
            name=name,
            slug=name.lower().replace(" ", "-"),
            project_id=project_id,
            description=description or "",
            color=color,
            position=position,
            is_default=False,
        )
        self.db.add(board)
        self.db.flush()
        for col_data in self.DEFAULT_COLUMNS:
            col = BoardColumn(
                id=str(uuid.uuid4()),
                board_id=board.id,
                name=col_data["name"],
                slug=col_data["name"].lower().replace(" ", "-"),
                color=col_data["color"],
                position=col_data["position"],
                is_default=col_data["is_default"],
            )
            self.db.add(col)
        self.db.commit()
        self.db.refresh(board)
        return self._get_board_detail(board.id)

    def get_board(self, board_id: str) -> dict:
        Board, BoardColumn, Task = self._import_models()
        board = self.db.query(Board).filter(Board.id == board_id).first()
        if not board:
            raise ValueError("看板不存在")
        columns = self.db.query(BoardColumn).filter(
            BoardColumn.board_id == board_id,
            BoardColumn.is_active == True
        ).order_by(BoardColumn.position).all()
        task_counts = {}
        if columns:
            for col in columns:
                count = self.db.query(Task).filter(
                    Task.board_id == board_id,
                    Task.column_id == col.id
                ).count()
                task_counts[col.id] = count
        return {
            "board": self._board_to_dict(board),
            "columns": [self._column_to_dict(c, task_counts.get(c.id, 0)) for c in columns]
        }

    def update_board(self, board_id: str, **kwargs) -> dict:
        Board = self._import_models()[0]
        board = self.db.query(Board).filter(Board.id == board_id).first()
        if not board:
            raise ValueError("看板不存在")
        for key, value in kwargs.items():
            if value is not None and hasattr(board, key):
                setattr(board, key, value)
        board.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(board)
        return self._board_to_dict(board)

    def delete_board(self, board_id: str) -> bool:
        Board = self._import_models()[0]
        board = self.db.query(Board).filter(Board.id == board_id).first()
        if not board:
            raise ValueError("看板不存在")
        self.db.delete(board)
        self.db.commit()
        return True

    def get_board_columns(self, board_id: str) -> list:
        Board, BoardColumn = self._import_models()[0], self._import_models()[1]
        columns = self.db.query(BoardColumn).filter(
            BoardColumn.board_id == board_id,
            BoardColumn.is_active == True
        ).order_by(BoardColumn.position).all()
        return [self._column_to_dict(c) for c in columns]

    def create_column(self, board_id: str, name: str, color="#E5E7EB", position=None) -> dict:
        Board, BoardColumn = self._import_models()[0], self._import_models()[1]
        board = self.db.query(Board).filter(Board.id == board_id).first()
        if not board:
            raise ValueError("看板不存在")
        last_pos = self.db.query(func.max(BoardColumn.position)).filter(
            BoardColumn.board_id == board_id
        ).scalar()
        if last_pos is None:
            last_pos = 0
        if position is None:
            position = last_pos + 1
        column = BoardColumn(
            id=str(uuid.uuid4()),
            board_id=board_id,
            name=name,
            slug=name.lower().replace(" ", "-"),
            color=color,
            position=position,
        )
        self.db.add(column)
        self.db.commit()
        self.db.refresh(column)
        return self._column_to_dict(column)

    def update_column(self, column_id: str, **kwargs) -> dict:
        BoardColumn = self._import_models()[1]
        column = self.db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
        if not column:
            raise ValueError("看板列不存在")
        for key, value in kwargs.items():
            if value is not None and hasattr(column, key):
                setattr(column, key, value)
        column.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(column)
        return self._column_to_dict(column)

    def delete_column(self, column_id: str) -> bool:
        BoardColumn = self._import_models()[1]
        column = self.db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
        if not column:
            raise ValueError("看板列不存在")
        self.db.delete(column)
        self.db.commit()
        return True

    def list_boards(self, project_id: str = None) -> list:
        Board, Task = self._import_models()[0], self._import_models()[2]
        q = self.db.query(Board).filter(Board.is_active == True)
        if project_id:
            q = q.filter(Board.project_id == project_id)
        boards = q.order_by(Board.position).all()
        result = []
        for board in boards:
            board_data = self._board_to_dict(board)
            task_count = self.db.query(Task).filter(Task.board_id == board.id).count()
            board_data["task_count"] = task_count
            result.append(board_data)
        return result

    def _board_to_dict(self, board) -> dict:
        return {
            "id": board.id,
            "project_id": board.project_id,
            "name": board.name,
            "slug": board.slug,
            "description": board.description,
            "position": board.position,
            "color": board.color,
            "is_default": board.is_default,
            "is_active": board.is_active,
            "created_at": board.created_at.isoformat() if board.created_at else None,
            "updated_at": board.updated_at.isoformat() if board.updated_at else None,
        }

    def _column_to_dict(self, column, task_count=0) -> dict:
        return {
            "id": column.id,
            "board_id": column.board_id,
            "name": column.name,
            "slug": column.slug,
            "color": column.color,
            "position": column.position,
            "max_tasks": column.max_tasks,
            "is_swimlane": column.is_swimlane,
            "is_default": column.is_default,
            "is_active": column.is_active,
            "task_count": task_count,
            "created_at": column.created_at.isoformat() if column.created_at else None,
            "updated_at": column.updated_at.isoformat() if column.updated_at else None,
        }

    def _get_board_detail(self, board_id: str) -> dict:
        data = self.get_board(board_id)
        return {"board": data["board"], "columns": data["columns"]}
