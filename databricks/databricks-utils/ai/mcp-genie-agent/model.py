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
        import sys
        import os
        from pathlib import Path

        # MLflow copies code_paths directly to the model directory
        # Add current directory (where model files are) to Python path
        current_dir = Path(__file__).parent.absolute()
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))

        # Try to import the agent from the src directory
        try:
            from src.agent import SingleTurnMCPAgent
        except ImportError as e:
            # Debug: print available files to understand the structure
            print(f"Import error: {e}")
            print(f"Current directory: {current_dir}")
            print(f"Files in current directory: {list(current_dir.glob('*'))}")
            if (current_dir / "src").exists():
                print(f"Files in src: {list((current_dir / 'src').glob('*'))}")
            raise

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