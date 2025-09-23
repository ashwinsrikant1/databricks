"""
Simple deployment script for MCP Genie Agent using Databricks Agent Framework.

This follows the official Databricks documentation approach.
"""

import mlflow
import os
from pathlib import Path
from databricks.sdk import WorkspaceClient

# Import configuration
from config import config

# Remove any conflicting tokens
if "DATABRICKS_TOKEN" in os.environ:
    del os.environ["DATABRICKS_TOKEN"]


def deploy_simple_agent():
    """Deploy the simple MCP agent using Agent Framework."""
    print("🚀 Deploying Simple MCP Genie Agent")
    print("=" * 50)

    # Set MLflow tracking URI
    mlflow.set_tracking_uri("databricks")

    # Create or use existing experiment
    experiment_name = f"/Users/{WorkspaceClient().current_user.me().user_name}/simple_mcp_agent"

    try:
        mlflow.create_experiment(experiment_name)
        print(f"✅ Created experiment: {experiment_name}")
    except Exception:
        print(f"✅ Using existing experiment: {experiment_name}")

    mlflow.set_experiment(experiment_name)

    # Start MLflow run
    with mlflow.start_run(run_name="deploy_simple_mcp_agent"):

        # Log basic parameters
        mlflow.log_param("llm_endpoint", config.llm_endpoint_name)
        mlflow.log_param("genie_space_id", config.genie_space_id)
        mlflow.log_param("agent_type", "simple_mcp")

        # Set the model using the simple agent
        print("📝 Setting model...")
        mlflow.models.set_model(model="simple_agent.py")

        print("✅ Model set successfully!")

        # The actual deployment happens when you create the serving endpoint
        print("\n🎯 Next Steps:")
        print("1. Go to Databricks ML Model Registry")
        print("2. Find your model in the experiment")
        print("3. Create a serving endpoint")
        print("4. The agent will be available in Databricks Playground")

        print(f"\n🔗 Experiment: {experiment_name}")
        print(f"🌐 Workspace: {config.workspace_hostname}")


if __name__ == "__main__":
    deploy_simple_agent()