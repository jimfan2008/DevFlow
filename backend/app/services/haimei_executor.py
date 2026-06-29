"""
Haimei Step Executor - 海梅自主执行引擎
将步骤{N}的execute逻辑从API层抽取到服务层，让海梅可以自主调度Agent执行。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional

from app.database import SessionLocal
from app.services.workflow_engine import WorkflowEngine

logger = logging.getLogger("devflow.haimei.executor")

# Step → 实际执行Agent的映射
AGENT_EXECUTOR_STEPS: Dict[int, str] = {
    3: "houxing",
    4: "houwang",
    5: "houfu",
    7: "houfa",
    9: "houfa",
    10: "houfu",
    11: "houda",
    12: "houhua",
    13: "houfu",
    14: "hougui",
}

# 海梅自己执行的步骤 (plan/report 类)
HAIMEI_EXECUTOR_STEPS: List[int] = [6, 8, 15, 16]


class HaimeiStepExecutor:
    """海梅步骤执行器 - 负责调度各Agent实际执行工作"""

    _tasks: Dict[str, asyncio.Task] = {}
    _lock = asyncio.Lock()

    @classmethod
    def get_dispatchers(cls) -> Dict[int, Callable[..., Coroutine[Any, Any, None]]]:
        """返回步骤号 → 执行函数的映射（延迟导入避免循环依赖）"""
        if not hasattr(cls, "_dispatcher_map"):
            map_: Dict[int, Callable[..., Coroutine[Any, Any, None]]] = {}
            # Step 4: 后旺架构设计
            from app.services.haimei_dispatch import dispatch_step4
            map_[4] = dispatch_step4
            # Step 5: 后富建立开发环境
            from app.services.haimei_dispatch import dispatch_step5
            map_[5] = dispatch_step5
            # Step 6: 海梅制订TDD测试用例计划
            from app.services.haimei_dispatch import dispatch_step6
            map_[6] = dispatch_step6
            # Step 7: 后发蜂群编写TDD测试用例
            from app.services.haimei_dispatch import dispatch_step7
            map_[7] = dispatch_step7
            # Step 8: 海梅制订代码编写计划
            from app.services.haimei_dispatch import dispatch_step8
            map_[8] = dispatch_step8
            # Step 9: 后发蜂群编写功能代码
            from app.services.haimei_dispatch import dispatch_step9
            map_[9] = dispatch_step9
            # Step 10: 后富部署到测试环境
            from app.services.haimei_dispatch import dispatch_step10
            map_[10] = dispatch_step10
            # Step 11: 后达蜂群全面测试
            from app.services.haimei_dispatch import dispatch_step11
            map_[11] = dispatch_step11
            # Step 12: 后华安全审计
            from app.services.haimei_dispatch import dispatch_step12
            map_[12] = dispatch_step12
            # Step 13: 后富部署到生产环境
            from app.services.haimei_dispatch import dispatch_step13
            map_[13] = dispatch_step13
            # Step 14: 后贵完善项目文档
            from app.services.haimei_dispatch import dispatch_step14
            map_[14] = dispatch_step14
            # Step 15: 海梅报告交付成果
            from app.services.haimei_dispatch import dispatch_step15
            map_[15] = dispatch_step15
            cls._dispatcher_map = map_
        return cls._dispatcher_map

    @classmethod
    async def dispatch(cls, project_id: str, step_number: int, db: Any = None) -> bool:
        """
        海梅调度步骤{N}的执行。
        返回 True 表示调度成功，False 表示没有对应的执行器或已在执行中。
        """
        dispatchers = cls.get_dispatchers()
        dispatch_fn = dispatchers.get(step_number)
        if not dispatch_fn:
            logger.warning(f"步骤{step_number}没有对应的执行器")
            return False

        task_key = f"{project_id}:step{step_number}"
        async with cls._lock:
            # 检查是否已有任务在运行
            existing = cls._tasks.get(task_key)
            if existing and not existing.done():
                logger.info(f"步骤{step_number}已在执行中，跳过重复调度")
                return False

        try:
            if db is None:
                db = SessionLocal()
                close_db = True
            else:
                close_db = False

            engine = WorkflowEngine(project_id=project_id, db=db)

            # 异步启动
            async def _run():
                try:
                    await dispatch_fn(project_id, engine)
                except Exception as e:
                    logger.error(f"步骤{step_number}执行失败: {e}", exc_info=True)
                finally:
                    if close_db:
                        db.close()
                    async with cls._lock:
                        cls._tasks.pop(task_key, None)

            task = asyncio.create_task(_run())
            async with cls._lock:
                cls._tasks[task_key] = task
            logger.info(f"海梅已调度步骤{step_number}的执行 (task={task.get_name() or 'unnamed'})")
            return True
        except Exception as e:
            logger.error(f"调度步骤{step_number}执行失败: {e}", exc_info=True)
            return False

    @classmethod
    def is_running(cls, project_id: str, step_number: int) -> bool:
        """检查步骤{N}的后台任务是否正在运行"""
        task_key = f"{project_id}:step{step_number}"
        task = cls._tasks.get(task_key)
        return task is not None and not task.done()

    @classmethod
    def register_task(cls, project_id: str, step_number: int, task: asyncio.Task) -> str:
        """注册后台任务，供 zombie 检测跟踪"""
        task_key = f"{project_id}:step{step_number}"
        cls._tasks[task_key] = task
        logger.info(f"已注册步骤{step_number}的后台任务 (key={task_key})")
        return task_key

    @classmethod
    def unregister_task(cls, project_id: str, step_number: int):
        """注销已完成的后台任务"""
        task_key = f"{project_id}:step{step_number}"
        cls._tasks.pop(task_key, None)
        logger.info(f"已注销步骤{step_number}的后台任务 (key={task_key})")

    @classmethod
    async def get_running_info(cls) -> Dict[str, Any]:
        """获取所有正在运行的任务信息"""
        info = {}
        async with cls._lock:
            for key, task in cls._tasks.items():
                if not task.done():
                    info[key] = {
                        "running": True,
                        "cancelled": task.cancelled(),
                    }
                else:
                    info[key] = {"running": False, "done": True}
        return info
