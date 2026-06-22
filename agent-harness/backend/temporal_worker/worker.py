import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from backend.temporal_worker.workflows import DeployAgentWorkflow
from backend.temporal_worker.activities import register_agent_activity, check_agent_health_activity
from backend.shared.config import config


async def run_worker():
    client = await Client.connect(config.temporal_host)
    worker = Worker(
        client,
        task_queue="agent-harness-tasks",
        workflows=[DeployAgentWorkflow],
        activities=[register_agent_activity, check_agent_health_activity],
    )
    print("Temporal worker started, listening on queue: agent-harness-tasks")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
