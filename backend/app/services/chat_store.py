import sqlite3
import json
import uuid
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path


class ChatStore:
    """内存+SQLite 聊天存储服务"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
            db_path = os.path.join(db_dir, "chat.db")

        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self.db_path = db_path
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                members TEXT DEFAULT '[]',
                host_agent TEXT,
                mode TEXT DEFAULT 'discussion',
                created_at TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                group_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                is_streaming INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_group_id ON messages(group_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meeting_outcomes (
                id TEXT PRIMARY KEY,
                group_id TEXT NOT NULL,
                meeting_topic TEXT NOT NULL,
                host_agent TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                minutes TEXT DEFAULT '',
                decisions TEXT DEFAULT '[]',
                todos TEXT DEFAULT '[]',
                risks TEXT DEFAULT '[]',
                open_issues TEXT DEFAULT '[]',
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                group_id TEXT NOT NULL,
                meeting_id TEXT,
                assignee TEXT NOT NULL,
                description TEXT NOT NULL,
                deadline TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                result TEXT DEFAULT '',
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')

        conn.commit()
        conn.close()

    # ====== 群组 CRUD ======

    def create_group(self, name: str, description: str = "", members: Optional[List[str]] = None, group_id: Optional[str] = None) -> Dict[str, Any]:
        if group_id is None:
            group_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO groups (id, name, description, members, created_at, mode)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (group_id, name, description, json.dumps(members or []), created_at, 'discussion'))

        conn.commit()
        conn.close()

        return {
            "id": group_id,
            "name": name,
            "description": description,
            "members": members or [],
            "host_agent": None,
            "mode": "discussion",
            "created_at": created_at,
            "messages": []
        }

    def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM groups WHERE id = ?', (group_id,))
        row = cursor.fetchone()

        conn.close()

        if not row:
            return None

        return self._row_to_group(row)

    def get_all_groups(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM groups ORDER BY created_at DESC')
        rows = cursor.fetchall()

        conn.close()

        return [self._row_to_group(row) for row in rows]

    def update_group(self, group_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        if not kwargs:
            return self.get_group(group_id)

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM groups WHERE id = ?', (group_id,))
        if not cursor.fetchone():
            conn.close()
            return None

        update_fields = []
        values = []

        for key, value in kwargs.items():
            if key == 'members':
                update_fields.append('members = ?')
                values.append(json.dumps(value))
            elif key == 'created_at':
                update_fields.append('created_at = ?')
                values.append(value.isoformat() if isinstance(value, datetime) else value)
            else:
                update_fields.append(f'{key} = ?')
                values.append(value)

        if update_fields:
            values.append(group_id)
            cursor.execute(f'UPDATE groups SET {", ".join(update_fields)} WHERE id = ?', values)
            conn.commit()

        conn.close()
        return self.get_group(group_id)

    def delete_group(self, group_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM messages WHERE group_id = ?', (group_id,))
        cursor.execute('DELETE FROM groups WHERE id = ?', (group_id,))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def add_member(self, group_id: str, profile_name: str) -> Optional[Dict[str, Any]]:
        group = self.get_group(group_id)
        if not group:
            return None

        if profile_name not in group["members"]:
            group["members"].append(profile_name)
            self.update_group(group_id, members=group["members"])

        return self.get_group(group_id)

    def remove_member(self, group_id: str, profile_name: str) -> Optional[Dict[str, Any]]:
        group = self.get_group(group_id)
        if not group:
            return None

        if profile_name in group["members"]:
            group["members"].remove(profile_name)
            self.update_group(group_id, members=group["members"])

        return self.get_group(group_id)

    # ====== 消息管理 ======

    def add_message(self, group_id: str, sender: str, role: str, content: str, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        if not self.get_group(group_id):
            return None

        msg_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO messages (id, group_id, sender, role, content, timestamp, is_streaming, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            msg_id,
            group_id,
            sender,
            role,
            content,
            timestamp,
            0,
            json.dumps(metadata or {}, ensure_ascii=False)
        ))

        conn.commit()
        conn.close()

        return {
            "id": msg_id,
            "group_id": group_id,
            "sender": sender,
            "role": role,
            "content": content,
            "timestamp": timestamp,
            "is_streaming": False,
            "metadata": metadata or {}
        }

    def get_messages(self, group_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM messages
            WHERE group_id = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', (group_id, limit, offset))
        rows = cursor.fetchall()

        conn.close()

        messages = []
        for row in reversed(rows):
            messages.append({
                "id": row["id"],
                "group_id": row["group_id"],
                "sender": row["sender"],
                "role": row["role"],
                "content": row["content"],
                "timestamp": row["timestamp"],
                "is_streaming": bool(row["is_streaming"]),
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
            })

        return messages

    def count_messages(self, group_id: str) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM messages WHERE group_id = ?', (group_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    # ====== 会议记录 ======

    def save_meeting_outcome(self, group_id: str, meeting_topic: str, host_agent: str,
                             started_at: datetime, minutes: str = "",
                             decisions: List[Dict] = None, todos: List[Dict] = None,
                             risks: List[Dict] = None, open_issues: List[Dict] = None) -> Dict[str, Any]:
        outcome_id = str(uuid.uuid4())
        ended_at = datetime.now().isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO meeting_outcomes (id, group_id, meeting_topic, host_agent, started_at, ended_at, minutes, decisions, todos, risks, open_issues)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            outcome_id,
            group_id,
            meeting_topic,
            host_agent,
            started_at.isoformat() if isinstance(started_at, datetime) else started_at,
            ended_at,
            minutes,
            json.dumps(decisions or [], ensure_ascii=False),
            json.dumps(todos or [], ensure_ascii=False),
            json.dumps(risks or [], ensure_ascii=False),
            json.dumps(open_issues or [], ensure_ascii=False)
        ))
        conn.commit()
        conn.close()

        return {
            "id": outcome_id,
            "group_id": group_id,
            "meeting_topic": meeting_topic,
            "host_agent": host_agent,
            "started_at": started_at.isoformat() if isinstance(started_at, datetime) else started_at,
            "ended_at": ended_at,
            "minutes": minutes,
            "decisions": decisions or [],
            "todos": todos or [],
            "risks": risks or [],
            "open_issues": open_issues or []
        }

    def get_meeting_outcomes(self, group_id: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM meeting_outcomes WHERE group_id = ? ORDER BY ended_at DESC', (group_id,))
        rows = cursor.fetchall()
        conn.close()

        outcomes = []
        for row in rows:
            outcomes.append({
                "id": row["id"],
                "group_id": row["group_id"],
                "meeting_topic": row["meeting_topic"],
                "host_agent": row["host_agent"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "minutes": row["minutes"],
                "decisions": json.loads(row["decisions"]) if row["decisions"] else [],
                "todos": json.loads(row["todos"]) if row["todos"] else [],
                "risks": json.loads(row["risks"]) if row["risks"] else [],
                "open_issues": json.loads(row["open_issues"]) if row["open_issues"] else []
            })

        return outcomes

    # ====== 待办任务 ======

    def create_task(self, group_id: str, assignee: str, description: str,
                    deadline: str = None, meeting_id: str = None) -> Dict[str, Any]:
        task_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tasks (id, group_id, meeting_id, assignee, description, deadline, status, created_at, completed_at, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_id, group_id, meeting_id, assignee, description, deadline,
            'pending', created_at, None, ''
        ))
        conn.commit()
        conn.close()

        return {
            "id": task_id,
            "group_id": group_id,
            "meeting_id": meeting_id,
            "assignee": assignee,
            "description": description,
            "deadline": deadline,
            "status": "pending",
            "created_at": created_at,
            "completed_at": None,
            "result": ""
        }

    def get_pending_tasks(self, assignee: str = None) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()

        if assignee:
            cursor.execute('SELECT * FROM tasks WHERE assignee = ? AND status != ? ORDER BY created_at DESC',
                           (assignee, 'completed'))
        else:
            cursor.execute('SELECT * FROM tasks WHERE status != ? ORDER BY created_at DESC', ('completed',))

        rows = cursor.fetchall()
        conn.close()

        tasks = []
        for row in rows:
            tasks.append(self._row_to_task(row))

        return tasks

    def update_task_status(self, task_id: str, status: str, result: str = ""):
        conn = self._get_connection()
        cursor = conn.cursor()
        completed_at = datetime.now().isoformat() if status == 'completed' else None
        cursor.execute('UPDATE tasks SET status = ?, result = ?, completed_at = ? WHERE id = ?',
                       (status, result, completed_at, task_id))
        conn.commit()
        conn.close()

    # ====== 内部方法 ======

    def _row_to_group(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"] or "",
            "members": json.loads(row["members"]) if row["members"] else [],
            "host_agent": row["host_agent"],
            "mode": row["mode"] or "discussion",
            "created_at": row["created_at"],
            "messages": self.get_messages(row["id"])
        }

    def _row_to_task(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "group_id": row["group_id"],
            "meeting_id": row["meeting_id"],
            "assignee": row["assignee"],
            "description": row["description"],
            "deadline": row["deadline"],
            "status": row["status"],
            "created_at": row["created_at"],
            "completed_at": row["completed_at"],
            "result": row["result"]
        }


chat_store = ChatStore()