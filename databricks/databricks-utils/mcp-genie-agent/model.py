"""
MLflow-compatible model wrapper for MCP Genie Agent.

This module provides a serializable wrapper around the SingleTurnMCPAgent
for deployment via MLflow.
"""

import mlflow
from mlflow.pyfunc import PythonModel
from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentResponse


class MCPAgentWrapper(PythonModel):
    """MLflow-compatible wrapper for SingleTurnMCPAgent."""

    def __init__(self):
        self.agent = None

    def load_context(self, context):
        """Load the agent using the model configuration."""
        # Add the code paths to sys.path
        import sys
        from pathlib import Path

        # Get the directory where this model is loaded
        model_dir = Path(context.artifacts["code"])
        if str(model_dir) not in sys.path:
            sys.path.insert(0, str(model_dir))

        # Now import the agent
        from src.agent import SingleTurnMCPAgent

        # Get configuration from the model context
        config = context.model_config

        # Create and initialize the agent
        self.agent = SingleTurnMCPAgent(
            llm_endpoint=config["llm_endpoint"],
            system_prompt=config["system_prompt"],
            server_configs=config["server_configs"]
        )

        # Initialize synchronously
        self.agent._initialize_sync()

    def predict(self, context, model_input, params=None):
        """Predict method for MLflow compatibility."""
        if isinstance(model_input, str):
            # Convert string input to ResponsesAgentRequest
            from mlflow.types.responses import ResponsesAgentRequest
            request = ResponsesAgentRequest(
                input=model_input
            )
        else:
            request = model_input

        return self.agent.predict(request)