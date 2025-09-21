"""
Final deployment script for MCP Genie Agent with proper Agent Framework signatures.
"""

import mlflow
import os
from databricks.sdk import WorkspaceClient
import databricks.agents

# Import configuration
from config import config

# Remove any conflicting tokens
if "DATABRICKS_TOKEN" in os.environ:
    del os.environ["DATABRICKS_TOKEN"]


def deploy_final_agent():
    """Deploy MCP Genie Agent with proper Agent Framework compatibility."""
    print("🚀 Final MCP Genie Agent Deployment")
    print("=" * 50)

    # Set MLflow tracking URI
    mlflow.set_tracking_uri("databricks")

    # Get current user
    ws = WorkspaceClient()
    current_user = ws.current_user.me()
    username = current_user.user_name

    # Create experiment
    experiment_name = f"/Users/{username}/mcp_genie_agent_final"

    try:
        mlflow.create_experiment(experiment_name)
        print(f"✅ Created experiment: {experiment_name}")
    except Exception:
        print(f"✅ Using existing experiment: {experiment_name}")

    mlflow.set_experiment(experiment_name)

    # Log the model with proper signatures
    with mlflow.start_run(run_name="mcp_genie_final_deploy") as run:
        print("📝 Logging agent with ChatCompletion signatures...")

        # Log parameters
        mlflow.log_param("agent_type", "mcp_genie_final")
        mlflow.log_param("llm_endpoint", config.llm_endpoint_name)
        mlflow.log_param("genie_space_id", config.genie_space_id)
        mlflow.log_param("signature_type", "ChatCompletionRequest")

        # Use the agent with proper signatures
        from mlflow.types.llm import ChatCompletionRequest, ChatCompletionResponse, ChatMessage

        # Create a sample input/output for signature inference
        sample_input = [ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="test")]
        )]

        # Import the predict function to test signature
        import agent_with_signatures
        sample_output = agent_with_signatures.predict(sample_input)

        # Infer signature from sample
        signature = mlflow.models.infer_signature(sample_input, sample_output)

        # Log the model with proper signatures
        mlflow.pyfunc.log_model(
            artifact_path="agent",
            python_model="agent_with_signatures.py",
            signature=signature,
            code_paths=["agent_with_signatures.py", "config.py"],
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
        print(f"✅ Model logged with ChatCompletion signatures: {model_uri}")

    # Register model
    model_name = "users.ashwin_srikant.mcp_genie_agent_final"
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
        print("\n🎮 How to Access:")
        print("1. Go to Databricks Playground")
        print("2. Look for 'MCP Genie Agent' in the agents list")
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
        print(f"❌ Deployment error: {e}")
        print("🔄 Model was logged successfully. You can manually deploy from the UI")
        print(f"   Model URI: {model_uri}")


if __name__ == "__main__":
    deploy_final_agent()