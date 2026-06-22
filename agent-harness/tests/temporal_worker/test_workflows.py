from backend.temporal_worker.workflows import DeployAgentWorkflow


class TestDeployAgentWorkflow:
    def test_workflow_definition_exists(self):
        wf = DeployAgentWorkflow()
        assert hasattr(wf, "run")
