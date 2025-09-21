"""
Deploy MCP Genie Agent using Databricks Agent Framework.

This creates a proper agent that can be used in Databricks Playground.
"""

import mlflow
import os
from pathlib import Path
from databricks.sdk import WorkspaceClient
import databricks.agents

# Import configuration
from config import config

# Remove any conflicting tokens
if "DATABRICKS_TOKEN" in os.environ:
    del os.environ["DATABRICKS_TOKEN"]


def deploy_mcp_agent():
    """Deploy MCP Genie Agent using Agent Framework."""
    print("🚀 Deploying MCP Genie Agent with Agent Framework")
    print("=" * 60)

    # Set MLflow tracking URI
    mlflow.set_tracking_uri("databricks")

    # Get current user
    ws = WorkspaceClient()
    current_user = ws.current_user.me()
    username = current_user.user_name

    # Create experiment
    experiment_name = f"/Users/{username}/mcp_genie_agent_framework"

    try:
        mlflow.create_experiment(experiment_name)
        print(f"✅ Created experiment: {experiment_name}")
    except Exception:
        print(f"✅ Using existing experiment: {experiment_name}")

    mlflow.set_experiment(experiment_name)

    # Log the model using MLflow
    with mlflow.start_run(run_name="mcp_genie_agent_deploy") as run:
        print("📝 Logging model to MLflow...")

        # Log parameters
        mlflow.log_param("agent_type", "mcp_genie")
        mlflow.log_param("llm_endpoint", config.llm_endpoint_name)
        mlflow.log_param("genie_space_id", config.genie_space_id)
        mlflow.log_param("workspace", config.workspace_hostname)

        # Log the agent function
        # Use Python function logging for Agent Framework compatibility
        mlflow.pyfunc.log_model(
            artifact_path="agent",
            python_model="agent_framework.py",
            code_paths=["agent_framework.py", "config.py"],
            pip_requirements=[
                "databricks-sdk[openai]",
                "databricks-mcp",
                "databricks-langchain",
                "mlflow>=3.1.0",
                "databricks-agents>=1.0.0",
                "langchain-core",
                "pydantic",
                "nest_asyncio"
            ],
            model_config={
                "llm_endpoint": config.llm_endpoint_name,
                "genie_space_id": config.genie_space_id,
                "system_prompt": config.system_prompt
            }
        )

        model_uri = f"runs:/{run.info.run_id}/agent"
        print(f"✅ Model logged: {model_uri}")

    # Register model in Unity Catalog (use the working schema)
    model_name = "users.ashwin_srikant.mcp_genie_agent_framework"

    print(f"📝 Registering model: {model_name}")
    try:
        model_version = mlflow.register_model(model_uri, model_name)
        print(f"✅ Model registered: {model_name} version {model_version.version}")

        # Deploy using Agent Framework
        print("🚀 Deploying with Agent Framework...")

        deployment = databricks.agents.deploy(
            model_name=model_name,
            model_version=int(model_version.version),
            scale_to_zero=True,
            workload_size="Small",
            environment_vars={
                "DATABRICKS_HOST": config.databricks_host,
                "DATABRICKS_CLIENT_ID": config.client_id,
                "GENIE_SPACE_ID": config.genie_space_id,
                "LLM_ENDPOINT_NAME": config.llm_endpoint_name
            }
        )

        print(f"✅ Agent deployed successfully!")
        print(f"📍 Deployment: {deployment}")

        print("\n🎉 MCP Genie Agent is now available in Databricks Playground!")
        print("\n🎮 How to Use:")
        print("1. Go to Databricks Playground")
        print("2. Look for 'MCP Genie Agent' in the model selector")
        print("3. Start asking questions about your Databricks usage!")

        print("\n💬 Example Questions:")
        examples = [
            "How many queries were executed in the last 7 days?",
            "What are the most expensive clusters by compute cost?",
            "Show me the top SQL queries by execution time",
            "Which users are most active in this workspace?",
            "What is the total data processed this month?"
        ]

        for example in examples:
            print(f"   • {example}")

        print(f"\n🔗 Links:")
        print(f"   • Playground: https://{config.workspace_hostname}/ml/playground")
        print(f"   • Model: {model_name}")

    except Exception as e:
        print(f"❌ Registration failed: {e}")
        print("🔄 You can manually register the model from the MLflow UI")
        print(f"   Model URI: {model_uri}")


if __name__ == "__main__":
    deploy_mcp_agent()