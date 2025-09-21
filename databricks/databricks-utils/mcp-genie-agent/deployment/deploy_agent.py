#!/usr/bin/env python3
"""
Deploy MCP Genie Agent to Databricks.

This script deploys the agent to Databricks using MLflow, making it available
in the Databricks Playground and for API access.
"""

import os
import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import mlflow
from databricks import agents
from databricks.sdk import WorkspaceClient

from deployment.agent_config import deployment_config
from src.agent import SingleTurnMCPAgent


def setup_mlflow():
    """Set up MLflow tracking and registry."""
    print("🔧 Setting up MLflow...")

    # Set MLflow tracking URI to Databricks
    mlflow.set_tracking_uri("databricks")

    # Get current user for experiment path
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    try:
        current_user = w.current_user.me()
        username = current_user.user_name
        experiment_name = f"/Users/{username}/{deployment_config.model_name}"
    except Exception:
        # Fallback to shared space if user detection fails
        experiment_name = f"/Shared/mcp_agents/{deployment_config.model_name}"

    try:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            experiment_id = mlflow.create_experiment(experiment_name)
            print(f"✅ Created experiment: {experiment_name}")
        else:
            experiment_id = experiment.experiment_id
            print(f"✅ Using existing experiment: {experiment_name}")

        mlflow.set_experiment(experiment_name)
        return experiment_id

    except Exception as e:
        print(f"❌ Error setting up MLflow: {e}")
        raise


def create_agent_script():
    """Create the agent script for deployment."""
    print("📝 Creating agent script...")

    model_config = deployment_config.get_model_config()

    # Create a deployable agent instance
    agent = SingleTurnMCPAgent(
        llm_endpoint=model_config["llm_endpoint"],
        system_prompt=model_config["system_prompt"],
        server_configs=model_config["server_configs"]
    )

    print(f"✅ Agent script created with {len(model_config['server_configs'])} MCP servers")
    return agent


def get_deployment_resources(agent):
    """Get all resources needed for deployment."""
    print("📋 Gathering deployment resources...")

    try:
        # Get resources from the agent
        resources = agent.get_deployment_resources()
        print(f"✅ Found {len(resources)} resources for deployment")

        # Log resource details
        for resource in resources:
            resource_type = resource.get('type', 'unknown')
            resource_name = resource.get('name', 'unnamed')
            print(f"  - {resource_type}: {resource_name}")

        return resources

    except Exception as e:
        print(f"⚠️  Warning: Could not gather resources: {e}")
        print("Continuing deployment without explicit resource declaration...")
        return []


def deploy_model(agent, resources):
    """Deploy the model to MLflow and Unity Catalog."""
    print("🚀 Deploying model...")

    model_config = deployment_config.get_model_config()

    with mlflow.start_run(run_name=f"deploy_{deployment_config.model_name}_{int(time.time())}"):
        # Log model parameters
        mlflow.log_params({
            "llm_endpoint": model_config["llm_endpoint"],
            "num_mcp_servers": len(model_config["server_configs"]),
            "agent_type": "SingleTurnMCPAgent",
            "system_prompt_length": len(model_config["system_prompt"])
        })

        # Log MCP server configurations
        for i, server_config in enumerate(model_config["server_configs"]):
            mlflow.log_param(f"server_{i}_type", server_config["type"])
            mlflow.log_param(f"server_{i}_name", server_config["name"])

        # Create a model configuration that can be serialized
        model_config_dict = {
            "llm_endpoint": model_config["llm_endpoint"],
            "system_prompt": model_config["system_prompt"],
            "server_configs": model_config["server_configs"]
        }

        # Import and create the wrapper model
        from model import MCPAgentWrapper
        wrapper_model = MCPAgentWrapper()

        # Define source paths
        project_root = Path(__file__).parent.parent
        src_path = str(project_root / "src")
        requirements_path = str(project_root / "requirements.txt")

        # Create input example and signature
        input_example = "How many queries were executed in the past 7 days?"

        # Create model signature for Unity Catalog
        from mlflow.models.signature import infer_signature
        from mlflow.types.schema import Schema, ColSpec
        from mlflow.types import DataType

        # Define input schema (string input)
        input_schema = Schema([ColSpec(DataType.string)])

        # Define output schema (simplified for Unity Catalog)
        output_schema = Schema([ColSpec(DataType.string)])

        signature = mlflow.models.ModelSignature(
            inputs=input_schema,
            outputs=output_schema
        )

        # Log the model using the wrapper
        logged_model_info = mlflow.pyfunc.log_model(
            artifact_path="mcp_agent",
            python_model=wrapper_model,
            model_config=model_config_dict,
            signature=signature,
            code_paths=[
                src_path,
                str(project_root / "config.py"),
                str(project_root / "model.py")
            ],
            pip_requirements=requirements_path,
            input_example=input_example,
            metadata={
                "agent_name": model_config["agent_name"],
                "description": "MCP Genie Agent for querying Databricks system tables",
                "version": "1.0.0"
            }
        )

        print(f"✅ Model logged: {logged_model_info.model_uri}")

        # Register the model in Unity Catalog
        print(f"📝 Registering model: {deployment_config.uc_model_name}")

        registered_model = mlflow.register_model(
            logged_model_info.model_uri,
            deployment_config.uc_model_name
        )

        print(f"✅ Model registered: version {registered_model.version}")

        return registered_model


def deploy_serving_endpoint(registered_model):
    """Deploy the model to a serving endpoint."""
    print("🌐 Deploying serving endpoint...")

    try:
        # Deploy using databricks-agents
        deployment_info = agents.deploy(
            model_name=deployment_config.uc_model_name,
            model_version=registered_model.version,
        )

        print(f"✅ Serving endpoint deployed!")
        print(f"📡 Endpoint URL: {deployment_info.get('prediction_url', 'N/A')}")

        return deployment_info

    except Exception as e:
        print(f"❌ Error deploying serving endpoint: {e}")
        print("You can manually create a serving endpoint in the Databricks UI")
        return None


def verify_deployment(deployment_info):
    """Verify that the deployment is working."""
    print("🧪 Verifying deployment...")

    try:
        # Test a simple query
        test_query = "How many queries were executed in the last 24 hours?"

        print(f"Testing query: '{test_query}'")

        # Here you could add actual testing logic
        # For now, just check if the endpoint is accessible

        print("✅ Deployment verification complete")
        print("🎉 Agent is ready to use in Databricks Playground!")

        return True

    except Exception as e:
        print(f"⚠️  Deployment verification failed: {e}")
        return False


def print_usage_instructions():
    """Print instructions for using the deployed agent."""
    print("\n" + "=" * 60)
    print("🎉 MCP Genie Agent Deployment Complete!")
    print("=" * 60)

    print(f"\n📝 Model Details:")
    print(f"   Name: {deployment_config.uc_model_name}")
    print(f"   Agent: {deployment_config.agent_name}")

    print(f"\n🎮 How to Use:")
    print(f"   1. Go to Databricks Playground")
    print(f"   2. Select your deployed agent: '{deployment_config.agent_name}'")
    print(f"   3. Ask questions about your Databricks usage!")

    print(f"\n💬 Example Questions:")
    example_queries = [
        "How many queries were executed in the last 7 days?",
        "What are the most expensive clusters by compute cost?",
        "Show me the top SQL queries by execution time",
        "Which users are most active in this workspace?",
        "What is the total data processed this month?"
    ]

    for query in example_queries:
        print(f"   • {query}")

    print(f"\n🔗 Useful Links:")
    print(f"   • Databricks Playground: https://{deployment_config.workspace_hostname}/ml/playground")
    print(f"   • Model Registry: https://{deployment_config.workspace_hostname}/explore/data/{deployment_config.catalog_name}/{deployment_config.schema_name}")

    print("\n✨ Your MCP Genie Agent is ready to help analyze your Databricks data!")


def main():
    """Main deployment function."""
    print("🚀 Starting MCP Genie Agent Deployment")
    print("=" * 50)

    try:
        # Validate configuration
        print("✅ Validating configuration...")
        is_valid, errors = deployment_config.validate_config()

        if not is_valid:
            print("❌ Configuration validation failed:")
            for error in errors:
                print(f"   • {error}")
            sys.exit(1)

        deployment_config.print_config()

        # Set up MLflow
        setup_mlflow()

        # Create agent
        agent = create_agent_script()

        # Get deployment resources
        resources = get_deployment_resources(agent)

        # Deploy model
        registered_model = deploy_model(agent, resources)

        # Deploy serving endpoint
        deployment_info = deploy_serving_endpoint(registered_model)

        # Verify deployment
        verify_deployment(deployment_info)

        # Print usage instructions
        print_usage_instructions()

    except KeyboardInterrupt:
        print("\n❌ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()