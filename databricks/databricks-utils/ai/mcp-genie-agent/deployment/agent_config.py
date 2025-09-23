"""
Configuration for MCP agent deployment to Databricks.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config


class DeploymentConfig:
    """Configuration for deploying MCP agents to Databricks."""

    def __init__(self):
        # Model and deployment settings
        self.catalog_name = os.getenv("DATABRICKS_CATALOG", "users")
        self.schema_name = os.getenv("DATABRICKS_SCHEMA", "ashwin_srikant")
        self.model_name = "mcp_genie_agent"
        self.agent_name = "MCP Genie Agent"

        # Unity Catalog model name
        self.uc_model_name = f"{self.catalog_name}.{self.schema_name}.{self.model_name}"

        # LLM and system configuration
        self.llm_endpoint = config.llm_endpoint_name
        self.system_prompt = self._get_system_prompt()

        # MCP server configurations
        self.server_configs = self._get_server_configs()

        # Deployment settings
        self.compute_config = {
            "served_model_name": self.model_name,
            "workload_size": "Small",
            "scale_to_zero_enabled": True,
            "environment_vars": self._get_environment_vars()
        }

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the deployed agent."""
        return """You are an expert data analyst assistant that can query Databricks system tables through natural language.

You have access to Genie spaces that contain structured data about Databricks usage, including:
- Query history and performance metrics
- Compute usage and cluster information
- User activity and workspace statistics
- Data processing and storage metrics

When users ask questions about their Databricks environment, use the available tools to query the relevant data and provide insightful, actionable answers. Always explain what the data shows and provide context for the results.

For complex questions, break them down into multiple queries if needed. Present results in a clear, organized format with key insights highlighted."""

    def _get_server_configs(self) -> List[Dict[str, Any]]:
        """Get MCP server configurations for deployment."""
        servers = []

        # Genie server configuration
        if config.genie_space_id and config.workspace_hostname:
            servers.append({
                "type": "genie",
                "name": "databricks_system_tables",
                "url": config.genie_server_url,
                "description": "Databricks system tables via Genie space"
            })

        # Add other MCP servers here as needed
        # Example:
        # servers.append({
        #     "type": "custom",
        #     "name": "custom_server",
        #     "url": "https://example.com/mcp",
        #     "auth": {"type": "bearer", "token": "..."}
        # })

        return servers

    def _get_environment_vars(self) -> Dict[str, str]:
        """Get environment variables for deployment."""
        env_vars = {}

        # Add Databricks configuration
        if config.databricks_host:
            env_vars["DATABRICKS_HOST"] = config.databricks_host

        if config.client_id:
            env_vars["DATABRICKS_CLIENT_ID"] = config.client_id

        # Note: Client secret should be handled securely in deployment
        # Don't include it in environment variables for security

        if config.genie_space_id:
            env_vars["GENIE_SPACE_ID"] = config.genie_space_id

        if config.llm_endpoint_name:
            env_vars["LLM_ENDPOINT_NAME"] = config.llm_endpoint_name

        return env_vars

    def get_model_config(self) -> Dict[str, Any]:
        """Get complete model configuration for deployment."""
        return {
            "llm_endpoint": self.llm_endpoint,
            "system_prompt": self.system_prompt,
            "server_configs": self.server_configs,
            "agent_name": self.agent_name,
            "model_name": self.model_name,
            "uc_model_name": self.uc_model_name
        }

    def get_serving_config(self) -> Dict[str, Any]:
        """Get serving endpoint configuration."""
        return {
            "name": self.model_name.replace("_", "-"),  # Serving endpoint names use hyphens
            "config": {
                "served_models": [{
                    "model_name": self.uc_model_name,
                    "model_version": "1",  # Will be updated during deployment
                    "workload_size": self.compute_config["workload_size"],
                    "scale_to_zero_enabled": self.compute_config["scale_to_zero_enabled"],
                    "environment_vars": self.compute_config["environment_vars"]
                }]
            }
        }

    def validate_config(self) -> tuple[bool, List[str]]:
        """Validate deployment configuration."""
        errors = []

        # Check required configuration
        if not self.llm_endpoint:
            errors.append("LLM endpoint not configured")

        if not self.server_configs:
            errors.append("No MCP servers configured")

        if not config.workspace_hostname:
            errors.append("Databricks workspace hostname not configured")

        if not config.client_id:
            errors.append("OAuth client ID not configured")

        # Check catalog and schema permissions
        try:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient()

            # Try to access the catalog and schema
            try:
                catalogs = w.catalogs.list()
                catalog_names = [c.name for c in catalogs]
                if self.catalog_name not in catalog_names:
                    errors.append(f"Catalog '{self.catalog_name}' not accessible")
            except Exception as e:
                errors.append(f"Cannot access catalogs: {e}")

        except Exception as e:
            errors.append(f"Cannot connect to Databricks: {e}")

        return len(errors) == 0, errors

    def print_config(self):
        """Print current deployment configuration."""
        print("🔧 Deployment Configuration:")
        print("=" * 50)
        print(f"Model Name: {self.uc_model_name}")
        print(f"Agent Name: {self.agent_name}")
        print(f"LLM Endpoint: {self.llm_endpoint}")
        print(f"MCP Servers: {len(self.server_configs)}")

        for i, server in enumerate(self.server_configs, 1):
            print(f"  {i}. {server['name']} ({server['type']})")

        print(f"Compute Config: {self.compute_config['workload_size']}")
        print(f"Scale to Zero: {self.compute_config['scale_to_zero_enabled']}")


# Global deployment configuration instance
deployment_config = DeploymentConfig()