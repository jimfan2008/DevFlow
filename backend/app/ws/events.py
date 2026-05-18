# WebSocket 事件类型定义与处理器注册

WS_EVENT_TYPES = {
    # SRS §6.2 标准事件
    "project.requirement.updated": "需求文档更新",
    "task.assigned": "任务分配给编程 Agent",
    "task.status.changed": "任务状态变更",
    "acceptance.result": "任务验收结果推送",
    "project.completed": "项目完成通知",
    # 内部事件
    "ping": "心跳检测",
    "subscribe": "订阅 board 消息",
}


def get_event_handler(event_type: str):
    """获取事件对应的处理器函数。"""
    handlers = {
        "ping": _handle_ping,
        "subscribe": _handle_subscribe,
        "task.status.changed": _handle_task_status,
    }
    return handlers.get(event_type, _handle_default)


async def _handle_ping(websocket, data: dict):
    """处理心跳事件。"""
    await websocket.send_json({"type": "pong"})


async def _handle_subscribe(websocket, data: dict):
    """处理订阅事件。"""
    board_id = data.get("board_id")
    if board_id:
        websocket.subscribed_board = board_id


async def _handle_task_status(websocket, data: dict):
    """处理任务状态变更事件。"""
    pass


async def _handle_default(websocket, data: dict):
    """默认事件处理器。"""
    pass