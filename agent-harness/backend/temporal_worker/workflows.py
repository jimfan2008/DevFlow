from datetime import timedelta
from temporalio import workflow
with workflow.unsafe.imports_passed_through():
    from backend.temporal_worker.activities import AgentInput, HealthCheckResult


@workflow.defn
class DeployAgentWorkflow:
    @workflow.run
    async def run(self, input: AgentInput) -> dict:
        registration = await workflow.execute_activity(
            "register_agent_activity",
            input,
            start_to_close_timeout=timedelta(seconds=30),
        )

        await workflow.execute_activity(
            "check_agent_health_activity",
            input.agent_id,
            start_to_close_timeout=timedelta(seconds=10),
        )

        return registration
